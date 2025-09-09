import logging
import os
import requests
import traceback
import pyodbc
import pandas as pd
import json
import re
from decimal import Decimal
from flask import Flask, request, jsonify, send_from_directory, url_for
from config import configure_cors
from logging.handlers import RotatingFileHandler
from werkzeug.exceptions import HTTPException
from db import run_sql_query
from prompt_helper import get_sql_and_text_response
from chart_generator import generate_chart

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(CustomJSONEncoder, self).default(obj)

app = Flask(__name__, static_url_path='', static_folder='static')

app.json_provider_class.JSONEncoder = CustomJSONEncoder

os.environ["CORS_ENV"] = "prod"
configure_cors(app)

LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/app.log")
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=1_000_000, backupCount=3)
handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


AUTH_API_URL = "http://posapi.iconnectgroup.com/Api/GetAuthToken"
WMS_LOGIN_API_URL = "http://posapi.iconnectgroup.com/Api/Wms/UserLogin"
SAVE_CHAT_API_URL = "http://posapi.iconnectgroup.com/Api/Chat/saveChatMessageInfo"
GET_CHAT_API_URL = "http://posapi.iconnectgroup.com/Api/Chat/getChatMessageInfo"
AUTH_CODE_MAP = { "tnr": "turNER", "act": "AshleYcT", "act1": "Ashleyct1", "act2":"afhstXDev" }
SQL_COL_Generated = ""

@app.route('/api/token', methods=['GET'])
def get_login_token():
    code = request.args.get("Code")
    if not code: return jsonify({"error": "Missing 'Code' parameter"}), 400
    auth_code = AUTH_CODE_MAP.get(code.strip().lower())
    logger.info(f"Auth code resolved for {code}: {auth_code}")
    if not auth_code: return jsonify({"error": f"Invalid code '{code}'"}), 400
    try:
        response = requests.post(AUTH_API_URL, data={"grant_type": "password", "AuthCode": auth_code})
        response.raise_for_status()
        data = response.json()
        return jsonify({ "access_token": data.get("access_token"), "token_type": data.get("token_type", "Bearer"), "expires": data.get(".expires") }), 200
    except requests.exceptions.RequestException as e:
        logger.error("Token API Error: %s", str(e))
        return jsonify({"error": "Failed to get token"}), 502

@app.route('/api/login', methods=['POST'])
def login_proxy():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Authorization token required"}), 401
    token = auth_header.split(" ")[1]

    content_type = request.headers.get("Content-Type", "")
    if "application/json" in content_type:
        data = request.get_json()
    else:
        data = request.form

    login_type = data.get("LoginType", "").lower()
    if login_type == "pos":
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return jsonify({"error": "Username and Password are required for POS login"}), 400

        login_url = WMS_LOGIN_API_URL
        payload = {
            "UserName": username,
            "Password": password
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        post_kwargs = {"data": payload}

    else:
        encrypted = data.get("EncryptedCred")
        if not encrypted:
            return jsonify({"error": "EncryptedCred is required for WMS login"}), 400

        login_url = WMS_LOGIN_API_URL
        payload = {"EncryptedCred": encrypted}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        post_kwargs = {"json": payload}

    try:
        response = requests.post(login_url, headers=headers, **post_kwargs)
        response.raise_for_status()
        response_data = response.json()

        contact_id = response_data.get("ContactID")
        if contact_id:
            response_data["UserId"] = str(contact_id)
            logger.info(f"Successfully mapped ContactID {contact_id} to UserId.")
        else:
            logger.warning("ContactID not found in login response.")

        return jsonify(response_data), 200

    except requests.exceptions.RequestException as e:
        logger.error(f"{login_type.upper()} Login API Error: %s", str(e))
        return jsonify({"error": e.response.text if e.response else "Unknown error"}), 502


@app.route('/api/query', methods=['POST'])
def query():
    auth_header = request.headers.get("Authorization")
    SQL_COL_Generated = ""

    if not auth_header:
        return jsonify({"error": "Authorization token required"}), 401

    data = request.json
    if not data or "question" not in data:
        return jsonify({"error": "Question is required."}), 400
    
    question = data["question"].strip()
    if not question:
        return jsonify({"error": "Question is required."}), 400

    sql = ""
    try:
        sql, explanation, chart_title = get_sql_and_text_response(question)

        if sql == "SENSITIVE_QUERY_ERROR":
            return jsonify({"error": explanation}), 403

        if sql == "SQL_PARSE_ERROR":
            return jsonify({"error": "The AI response was not in the correct format."}), 500

        if not sql.lower().strip().startswith("select"):
            return jsonify({
                "text": explanation,
                "table": [],
                "columns": [],
                "chart_url": None,
                "chart_title": None
            })

        print(f"\nExecuting SQL Query:\n---\n{sql}\n---\n")

        try:
            columnName = extract_base_columns(sql)
            SQL_COL_Generated = ", ".join(columnName)
        except Exception as e:
            logger.warning(f"Column extraction failed for SQL: {sql} | Error: {str(e)}")
            SQL_COL_Generated = ""

        df = run_sql_query(sql)
        if df.empty:
            return jsonify({"error": "No record found"}), 404

        chart_url = None
        chart_filename = generate_chart(df, title=chart_title)
        if chart_filename:
            chart_url = url_for('serve_chart', filename=chart_filename, _external=True)
            print(f"Generated Chart URL: {chart_url}")

        table_data = json.loads(df.to_json(orient="records", date_format="iso"))

        return jsonify({
            "sql": sql,
            "table": table_data,
            "columns": list(df.columns),
            "chart_url": chart_url,
            "text": explanation,
            "chart_title": chart_title,
            "sql_query_columns": SQL_COL_Generated
        })

    except pyodbc.Error as db_error:
        error_message = str(db_error)
        logger.error(f"Database error for SQL: {sql} | Error: {error_message}")

        if "Invalid column name" in error_message or "Invalid object name" in error_message:
            return jsonify({"error": "I couldn't find the data you asked for. Please try rephrasing your question."}), 400
        else:
            return jsonify({"error": "An error occurred while querying the database."}), 500

    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"A critical error occurred in /api/query:\n{error_traceback}")

        if isinstance(e, UnboundLocalError):
            return jsonify({"error": "The data is not available, please provide data"}), 500
        else:
            return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500


@app.route('/api/chat/save', methods=['POST'])
def save_chat_message():
    auth_header = request.headers.get("Authorization")
    if not auth_header: return jsonify({"error": "Authorization token required"}), 401
    
    data = request.json
    chat_id = data.get("chatId")
    user_id = data.get("userId")
    chat_content = data.get("chatContent", "")
    message_content = data.get("messageContent")
    sql_query_attributes = data.get("sqlAttributes", "")
    if not user_id or not message_content:
        return jsonify({"error": "userId and messageContent are required."}), 400

    payload = {
        "chatId": chat_id if chat_id else "0",
        "userId": user_id,
        "chatContent": chat_content,
        "messageContent": message_content,
       "attributes": sql_query_attributes
    }
    
    print(f"Payload for saving chat message: {payload}")
    headers = { "Content-Type": "application/json", "Authorization": auth_header }

    try:
        logger.info(f"Saving chat message for user {user_id}: {payload}")
        response = requests.post(SAVE_CHAT_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Save chat API successful. Status: {response.status_code}, Response: {response.text}")
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Save Chat API Request failed. Error: {str(e)}")
        if e.response is not None:
            logger.error(f"--> Status Code: {e.response.status_code}")
            logger.error(f"--> Response Body: {e.response.text}")
        return jsonify({"error": "Failed to save chat message."}), 502

@app.route('/api/chat/history/<int:user_id>', methods=['GET'])
def get_chat_history(user_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Authorization token required"}), 401
    
    headers = {"Authorization": auth_header}

    try:
        full_url = f"{GET_CHAT_API_URL}?userId={user_id}"
        logger.info(f"Requesting chat history from: {full_url}")
        
        response = requests.get(full_url, headers=headers)
        response.raise_for_status()
        
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Get Chat History API Error: {e}")
        return jsonify({"error": "Failed to fetch chat history."}), 502

@app.route("/static/charts/<path:filename>")
def serve_chart(filename):
    return send_from_directory("static/charts", filename)

def extract_base_columns(sql_query):
    # Extract all words inside square brackets (column references)
    all_bracketed = re.findall(r'\[([^\]]+)\]', sql_query, re.IGNORECASE)
    
    # Exclude SQL keywords, table names, and aliases
    sql_keywords = {'SELECT', 'FROM', 'WHERE', 'TOP', 'ORDER BY', 'GROUP BY', 
                    'HAVING', 'JOIN', 'ON', 'AS', 'END', 'CASE', 'WHEN', 
                    'THEN', 'ELSE', 'ISNULL', 'LTRIM', 'RTRIM', 'OFFSET', 
                    'ROWS', 'FETCH', 'NEXT', 'ONLY', 'DESC', 'ASC'}
    
    # Table name is usually after FROM or JOIN
    table_names = set(re.findall(r'(?:FROM|JOIN)\s+\[([^\]]+)\]', sql_query, re.IGNORECASE))
    
    # Aliases are after AS [...]
    aliases = set(re.findall(r'AS\s+\[([^\]]+)\]', sql_query, re.IGNORECASE))
    
    # Filter out keywords, table names, and aliases
    base_columns = [
        col for col in set(all_bracketed) 
        if (col.upper() not in sql_keywords and 
            col not in table_names and 
            col not in aliases)
    ]
    
    return base_columns

@app.errorhandler(Exception)
def handle_exception(e):
    code = 500
    if isinstance(e, HTTPException): code = e.code
    logger.error(f"Unhandled Exception: {traceback.format_exc()}")
    return jsonify({"error": "An internal server error occurred"}), code

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5000)