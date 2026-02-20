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

# FreeTDS 드라이버 사용 (Render 환경 호환성)
password_encoded = urllib.parse.quote_plus(DB_PASSWORD)
SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc://{DB_USER}:{password_encoded}@{DB_SERVER}/{DB_NAME}?driver=FreeTDS"

db = SQLAlchemy()
