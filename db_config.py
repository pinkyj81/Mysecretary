import urllib
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# MSSQL Server 연결 설정
DB_SERVER = os.getenv('DB_SERVER', 'ms1901.gabiadb.com')
DB_NAME = os.getenv('DB_NAME', 'yujincast')
DB_USER = os.getenv('DB_USER', 'pinkyj81')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'zoskek38!!')
DB_DRIVER = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')

connection_string = (
    f"DRIVER={{{DB_DRIVER}}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=yes;"
)

# URL 인코딩
params = urllib.parse.quote_plus(connection_string)

# SQLAlchemy 데이터베이스 URI
SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc:///?odbc_connect={params}"

db = SQLAlchemy()
