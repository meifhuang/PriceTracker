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
    (item_name, brand, url, company, item_type, qty, total_before_tax, cashback_pct, cashback_engine, total_after_cashback, date_purchased, notes)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            data.get("item_name"),
            data.get("brand"),
            data.get("url"),
            data.get("company"),
            data.get("item_type"),
            data.get("qty") or 1,
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

@app.route("/health")
def health():
    """Health check endpoint for Railway"""
    return jsonify({"status": "ok"}), 200

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
        
    def to_int(v):
        try:
            return int(v) if v is not None and v != "" else None
        except Exception:
            return None

    total_before_tax = to_float(payload.get("total_before_tax"))
    cashback_pct = to_float(payload.get("cashback_pct"))
    total_after_cashback = to_float(payload.get("total_after_cashback"))
    qty = to_int(payload.get("qty")) or 1

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
        "qty": qty, 
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
            print(new_id, "CREATED")
        app.logger.info(f"Successfully created expense {new_id}")
        if request.is_json:
            return jsonify({"status": "ok", "id": new_id}), 201
        else:
            return redirect(url_for("list_expenses"))
    except Exception as e:
        app.logger.exception(f"Failed to create expense: {e}")
        print('FAILED')
        if request.is_json:
             return jsonify({"error": str(e)}), 500
        else:
             return redirect(url_for("list_expenses"))

@app.route("/expenses", methods=["GET"])
def list_expenses():
    sql = """
    SELECT id, item_name, brand, qty, company, item_type,
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
        SELECT id, item_name, brand, qty, url, company, item_type,
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
    def to_int(v):
        try:
            return int(v) if v is not None and v != "" else None
        except Exception:
            return None

    total_before_tax = to_float(payload.get("total_before_tax"))
    cashback_pct = to_float(payload.get("cashback_pct"))
    total_after_cashback = to_float(payload.get("total_after_cashback"))
    qty = to_int(payload.get("qty")) or 1

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
    SET item_name=%s, brand=%s, url=%s, company=%s, item_type=%s, qty=%s,
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
        qty,
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

@app.route("/savings")
def calculate_savings():
    """
    Calculate total savings by comparing market average vs. purchase average.
    """
    try:
        with connect_with_retry(url) as conn:
            with conn.cursor() as cur:
                # Get average market price per oz from price scraping history
                cur.execute("""
                    SELECT AVG(price_per_oz) as market_avg
                    FROM prices
                    WHERE price_per_oz IS NOT NULL
                """)
                market_result = cur.fetchone()
                market_avg = market_result[0] if market_result and market_result[0] else 0

               # Get your actual purchases for cat food items
                # SUM(qty) gives total packs purchased
                cur.execute("""
                    SELECT 
                        COUNT(*) as purchase_count,
                        SUM(total_after_cashback) as total_spent,
                        AVG(total_after_cashback) as avg_purchase_price,
                        SUM(qty) as total_packs
                    FROM expenses
                    WHERE item_type = 'food' 
                      AND item_name ILIKE '%nulo%'
                      AND total_after_cashback IS NOT NULL
                """)
                expense_result = cur.fetchone()
                
                purchase_count = int(expense_result[0]) if expense_result and expense_result[0] else 0
                total_spent = float(expense_result[1]) if expense_result and expense_result[1] is not None else 0.0
                avg_purchase_price = float(expense_result[2]) if expense_result and expense_result[2] is not None else 0.0
                total_packs = int(expense_result[3]) if expense_result and expense_result[3] else 0

                # assumptions: each pack = 12 cans, each can = 12.5 oz
                cans_per_pack = 12.0
                oz_per_can = 12.5

                total_cans = total_packs * cans_per_pack
                total_oz = total_cans * oz_per_can

                # user's average price per oz across purchases
                avg_price_per_oz = (total_spent / total_oz) if total_oz > 0 else 0.0
                
                # What you WOULD have paid at market average
                market_cost = total_oz * market_avg
                
                # Savings = what you would have paid - what you actually paid
                savings = market_cost - total_spent
                savings_pct = (savings / market_cost * 100.0) if market_cost > 0 else 0.0

        return render_template("savings.html", 
            market_avg=round(market_avg, 3),
            avg_purchase_price=round(avg_purchase_price, 2),
            avg_price_per_oz=round(avg_price_per_oz, 3),
            total_spent=round(total_spent, 2),
            market_cost=round(market_cost, 2),
            savings=round(savings, 2),
            savings_pct=round(savings_pct, 1),
            purchase_count=purchase_count,
            total_oz=round(total_oz, 1),
            total_packs=total_packs
        )
    except Exception as e:
        app.logger.error(f"Failed to calculate savings: {e}")
        return render_template("error.html", message="Could not load savings data", code=500), 500

@app.route("/")
@app.route("/dashboard")
def dashboard():
    query = """
        SELECT date, company, price_per_oz
        FROM prices
        ORDER BY date
    """
    try:
        # try to connect with retries built into connect_with_retry
        with connect_with_retry(url) as pg_conn:
            df = pd.read_sql(query, pg_conn)
    except Exception as e:
        app.logger.error(f"Database connection failed: {e}")
        return render_template("error.html", 
                             message="Database is starting up, please wait...", 
                             code=503), 503

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

# Custom error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", message="Page not found", code=404), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", message="Server error — we're working on it!", code=500), 500

@app.errorhandler(503)
def service_unavailable(e):
    return render_template("error.html", message="Service starting up, please wait...", code=503), 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)