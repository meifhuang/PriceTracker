import sqlite3
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    item_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    url TEXT,
    company TEXT NOT NULL,
    item_type TEXT CHECK (item_type IN ('food','litter','toys','snacks')),
    total_before_tax NUMERIC(10,2),
    cashback_pct NUMERIC(5,2) DEFAULT 0,
    cashback_engine TEXT,
    total_after_cashback NUMERIC(10,2),
    date_purchased DATE,              
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

try:
    with psycopg2.connect(url, sslmode="require") as pg_conn:
        with pg_conn.cursor() as pg_cursor:
            pg_cursor.execute(CREATE_TABLE_SQL)
            pg_conn.commit()
            print("expenses table created or already exists.")
except psycopg2.OperationalError as e:
    print(f"Error connecting to PostgreSQL: {e}")
    raise
except Exception as e:
    print(f"Error creating expenses table: {e}")
    raise