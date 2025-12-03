import psycopg2
from psycopg2 import OperationalError
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")

def connect_with_retry(url, retries=10, delay=3):
    """
    Retry database connection with exponential backoff.
    Useful when database is cold-starting on Railway.
    """
    for i in range(retries):
        try:
            conn = psycopg2.connect(url, sslmode="require", connect_timeout=10)
            return conn
        except OperationalError as e:
            if i < retries - 1:
                wait_time = delay * (2 ** i)  # exponential backoff: 3s, 6s, 12s, 24s...
                print(f"Postgres connection failed ({i+1}/{retries}): {e}")
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    raise OperationalError(f"Could not connect after {retries} attempts")