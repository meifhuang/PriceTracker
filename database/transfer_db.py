import sqlite3
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
DB_CONFIG = {
    "hostname": os.getenv("hostname"),
    "database": os.getenv("database"),
    "port": os.getenv("port"),
    "username": os.getenv("username"),
    "password": os.getenv("password"),
}

url = os.getenv("db_url")

# SQLite connection
try:
    with sqlite3.connect("pricetracker.db") as sqlite_conn:
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT * FROM prices")
        rows = sqlite_cursor.fetchall()
except sqlite3.Error as e:
    print(f"Error connecting to SQLite: {e}")
    raise  

# PostgreSQL connection
try:
    with psycopg2.connect(url, sslmode="require") as pg_conn:
        with pg_conn.cursor() as pg_cursor:
            for row in rows:
                pg_cursor.execute('''
                    INSERT INTO "PriceTracker" (product, company, url, date, price, price_per_oz, pack_size)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', row[1:])
            pg_conn.commit() 
            print("Data migrated successfully!")
        
     
except psycopg2.OperationalError as e:
    print(f"Error connecting to PostgreSQL: {e}")
    raise

            
except Exception as e:
    print(f"Error migrating data: {e}")
