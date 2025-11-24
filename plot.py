import psycopg2
import pandas as pd
from flask import Flask, render_template
import os
from dotenv import load_dotenv
import json
import time

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    raise RuntimeError("DATABASE_URL not set in environment")


app = Flask(__name__)

def connect_with_retries(dsn, max_retries=5, initial_delay=1):
    """Try to connect up to max_retries times, with exponential backoff."""
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            return psycopg2.connect(dsn, sslmode="require")
        except Exception as e:
            if attempt == max_retries:
                raise
            time.sleep(delay)
            delay *= 2

@app.route("/dashboard")
def dashboard():
    query = """
        SELECT date, company, price_per_oz
        FROM prices
        ORDER BY date
    """
    # try to connect up to 5 times before failing
    with connect_with_retries(url) as pg_conn:
        df = pd.read_sql(query, pg_conn)

    # ensure date is datetime and sorted
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["company", "date"])

    traces = []
    for company, g in df.groupby("company"):
        traces.append({
            "x": g["date"].dt.strftime("%Y-%m-%d").tolist(),
            "y": g["price_per_oz"].tolist(),
            "mode": "lines+markers",
            "name": str(company)
        })
    return render_template("index.html", traces=json.dumps(traces))
if __name__ == "__main__":
    app.run(debug=True)