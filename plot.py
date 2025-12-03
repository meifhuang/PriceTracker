import psycopg2
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
from dotenv import load_dotenv
import json
import time
from datetime import datetime
from database.connect_db import connect_with_retry


load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    raise RuntimeError("DATABASE_URL not set in environment")
BASE_DIR = os.path.dirname(__file__)
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates"),
)
print(f"Flask static_folder={app.static_folder}, template_folder={app.template_folder}")
# ...existing code...

#helper to insert an expense
# new: helper to insert an expense
def insert_expense(conn, data):
    sql = """
    INSERT INTO expenses
    (item_name, brand, url, company, item_type, total_before_tax, cashback_pct, cashback_engine, total_after_cashback, date_purchased, notes)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            data.get("item_name"),
            data.get("brand"),
            data.get("url"),
            data.get("company"),
            data.get("item_type"),
            data.get("total_before_tax"),
            data.get("cashback_pct"),
            data.get("cashback_engine"),
            data.get("total_after_cashback"),
            data.get("date_purchased"),
            data.get("notes"),
        ))
        inserted_id = cur.fetchone()[0]
        conn.commit()
        return inserted_id

@app.route("/expenses/new", methods=["GET"])
def new_expense_form():
    # simple HTML form to add an expense; returns template
    return render_template("new_expense.html")

@app.route("/api/expenses", methods=["POST"])
def create_expense():
    """
    Accepts JSON or form data:
    Required: item_name, company
    Fields: brand, url, item_type (food|litter|toys|snacks), total_before_tax, cashback_pct, cashback_engine, total_after_cashback, date_purchased (YYYY-MM-DD), notes
    If cashback_pct + total_before_tax provided, cashback_amount and total_after_cashback will be computed server-side.
    """
    payload = {}
    if request.is_json:
        payload = request.get_json()
    else:
        payload = request.form.to_dict()

    # basic required validation
    item_name = payload.get("item_name")
    company = payload.get("company")
    if not item_name or not company:
        return jsonify({"error": "item_name and company are required"}), 400

    # parse numeric fields
    def to_float(v):
        try:
            return float(v) if v is not None and v != "" else None
        except Exception:
            return None

    total_before_tax = to_float(payload.get("total_before_tax"))
    cashback_pct = to_float(payload.get("cashback_pct"))
    total_after_cashback = to_float(payload.get("total_after_cashback"))

    # parse date_purchased (optional)
    date_str = payload.get("date_purchased")
    date_purchased = None
    if date_str:
        try:
            date_purchased = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "date_purchased must be YYYY-MM-DD"}), 400

    expense = {
        "item_name": item_name,
        "brand": payload.get("brand"),
        "url": payload.get("url"),
        "company": company,
        "item_type": payload.get("item_type"),
        "total_before_tax": total_before_tax,
        "cashback_pct": cashback_pct,
        "cashback_engine": payload.get("cashback_engine"),
        "total_after_cashback": total_after_cashback,
        "date_purchased": date_purchased,
        "notes": payload.get("notes"),
    }

    try:
        with connect_with_retry(url) as conn:
            new_id = insert_expense(conn, expense)
        if request.is_json:
            return jsonify({"status": "ok", "id": new_id}), 201
        else:
            return redirect(url_for("list_expenses"))
    except Exception as e:
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        else:
            # could flash message; simple fallback: redirect back to form
            return redirect(url_for("new_expense_form"))

@app.route("/expenses", methods=["GET"])
def list_expenses():
    sql = """
    SELECT id, item_name, brand, company, item_type,
           total_before_tax, cashback_pct, cashback_engine,
           total_after_cashback, date_purchased, notes, created_at
    FROM expenses
    ORDER BY COALESCE(date_purchased, created_at) DESC
    """
    try:
        with connect_with_retry(url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                cols = [d[0] for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        rows = []
        app.logger.error(f"Failed to fetch expenses: {e}")

    return render_template("expenses.html", expenses=rows)

@app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def delete_expense(expense_id):
    """Delete an expense and redirect back to the transactions list."""
    sql = "DELETE FROM expenses WHERE id = %s"
    try:
        with connect_with_retry(url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (expense_id,))
            conn.commit()
    except Exception as e:
        app.logger.error(f"Failed to delete expense {expense_id}: {e}")
        # simple UX: still redirect back to list so user isn't stuck
    return redirect(url_for("list_expenses"))

@app.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
def edit_expense(expense_id):
    """Show edit form (GET) and apply updates (POST) for an expense."""
    if request.method == "GET":
        sql = """
        SELECT id, item_name, brand, url, company, item_type,
               total_before_tax, cashback_pct, cashback_engine,
               total_after_cashback, date_purchased, notes, created_at
        FROM expenses
        WHERE id = %s
        """
        try:
            with connect_with_retry(url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (expense_id,))
                    row = cur.fetchone()
                    if not row:
                        return redirect(url_for("list_expenses"))
                    cols = [d[0] for d in cur.description]
                    expense = dict(zip(cols, row))
        except Exception as e:
            app.logger.error(f"Failed loading expense {expense_id}: {e}")
            return redirect(url_for("list_expenses"))
        return render_template("edit_expense.html", expense=expense)

    # POST -> apply update
    payload = request.form.to_dict()
    def to_float(v):
        try:
            return float(v) if v is not None and v != "" else None
        except Exception:
            return None

    total_before_tax = to_float(payload.get("total_before_tax"))
    cashback_pct = to_float(payload.get("cashback_pct"))
    total_after_cashback = to_float(payload.get("total_after_cashback"))

    # compute total_after_cashback if possible (we don't store cashback_amount separately)
    if total_after_cashback is None and cashback_pct is not None and total_before_tax is not None:
        cashback_amount = round(total_before_tax * (cashback_pct / 100.0), 2)
        total_after_cashback = round(total_before_tax - cashback_amount, 2)

    # parse date
    date_str = payload.get("date_purchased")
    date_purchased = None
    if date_str:
        try:
            date_purchased = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return redirect(url_for("edit_expense", expense_id=expense_id))

    update_sql = """
    UPDATE expenses
    SET item_name=%s, brand=%s, url=%s, company=%s, item_type=%s,
        total_before_tax=%s, cashback_pct=%s, cashback_engine=%s,
        total_after_cashback=%s, date_purchased=%s, notes=%s
    WHERE id=%s
    """
    params = (
        payload.get("item_name"),
        payload.get("brand"),
        payload.get("url"),
        payload.get("company"),
        payload.get("item_type") or "food",
        total_before_tax,
        cashback_pct,
        payload.get("cashback_engine"),
        total_after_cashback,
        date_purchased,
        payload.get("notes"),
        expense_id,
    )
    try:
        with connect_with_retry(url) as conn:
            with conn.cursor() as cur:
                cur.execute(update_sql, params)
            conn.commit()
    except Exception as e:
        app.logger.error(f"Failed updating expense {expense_id}: {e}")
        return redirect(url_for("edit_expense", expense_id=expense_id))

    return redirect(url_for("list_expenses"))


@app.route("/dashboard")
def dashboard():
    query = """
        SELECT date, company, price_per_oz
        FROM prices
        ORDER BY date
    """
    # try to connect up to 5 times before failing
    with connect_with_retry(url) as pg_conn:
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)