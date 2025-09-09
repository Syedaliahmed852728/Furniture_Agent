import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_NAME = 'TurnerDB.db'
    TABLE_NAME = 'TurnerTable'
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MAX_TOKENS= 6000




