import os
import re
from flask_cors import CORS

def configure_cors(app):
    """
    Cleaned-up CORS config for Flask behind IIS reverse proxy.
    Mimics Django-style corsheaders settings.
    """

    PROD_ORIGINS = [
        "https://ai.iconnectgroup.com",
        "https://www.ai.iconnectgroup.com",
        "http://ai.iconnectgroup.com",
        "http://www.ai.iconnectgroup.com",
        "https://apiai.iconnectgroup.com",
        "http://apiai.iconnectgroup.com",
    ]

    DEV_REGEX_ORIGINS = [
        re.compile(r"^http://localhost(:\d+)?$"),
        re.compile(r"^http://127\.0\.0\.1(:\d+)?$"),
        re.compile(r"^http://192\.168\.\d+\.\d+(:\d+)?$"),
    ]

    env = os.getenv("CORS_ENV", "").lower()
    is_production = env in {"prod", "production", "live"}

    allowed_origins = PROD_ORIGINS if is_production else DEV_REGEX_ORIGINS

    CORS(app, resources={r"/**": {
        "origins": allowed_origins,
        "supports_credentials": True,
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": [
            "Content-Type", "Authorization", "X-Requested-With",
            "X-CSRF-Token", "Accept", "Origin"
        ],
        "expose_headers": ["Set-Cookie", "X-Request-Id", "Access-Control-Allow-Credentials"],
        "max_age": 86400 if is_production else 10,
    }})

    @app.after_request
    def add_env_header(resp):
        resp.headers["X-Environment"] = "production" if is_production else "development"
        return resp
