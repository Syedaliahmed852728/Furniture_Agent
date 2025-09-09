@app.route('/api/login', methods=['POST'])
def login_proxy():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Authorization token required"}), 401

    token = auth_header.split(" ")[1]

    # Get form data, not JSON
    username = request.form.get("UserName")
    password = request.form.get("Password")

    if not username or not password:
        return jsonify({"error": "UserName and Password are required"}), 400

    # Prepare request to external WMS login API
    login_url = WMS_LOGIN_API_URL
    payload = {
        "UserName": username,
        "Password": password
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(login_url, headers=headers, data=payload)
        response.raise_for_status()
        response_data = response.json()

        # Optional mapping
        contact_id = response_data.get("ContactID")
        if contact_id:
            response_data["UserId"] = str(contact_id)
            logger.info(f"Successfully mapped ContactID {contact_id} to UserId.")
        else:
            logger.warning("ContactID not found in login response.")

        return jsonify(response_data), 200

    except requests.exceptions.RequestException as e:
        logger.error(f"Login API Error: {str(e)}")
        return jsonify({"error": e.response.text if e.response else "Unknown error"}), 502