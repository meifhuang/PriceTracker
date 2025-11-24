import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")

def connect_with_retry(url, retries=5, delay=5):
    for i in range(retries):
        try:
            conn = psycopg2.connect(url, sslmode="require")
            return conn
        except OperationalError as e:
            print(f"Postgres connection failed ({i+1}/{retries}): {e}")
            time.sleep(delay)
    raise OperationalError(f"Could not connect after {retries} attempts")