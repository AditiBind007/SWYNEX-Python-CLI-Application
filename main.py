from contextlib import asynccontextmanager
from pathlib import Path
from datetime import date
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


# CONFIGURATION
DATABASE = Path(__file__).resolve().parent / "expenses.db"

CATEGORIES = {"Food", "Transport", "Shopping", "Bills", "Health", "Education", "Entertainment", "Other",}

# DATABASE SETUP AND INITIALIZATION
def initialize_database():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER NOT NULL
                    CHECK(amount > 0),
                category TEXT NOT NULL,
                expense_date TEXT NOT NULL,
                description TEXT NOT NULL)
        """)

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield

app = FastAPI(title="Expense Tracker API", description="REST API for managing personal expenses", version="1.0.0", lifespan=lifespan,)

# DATABASE CONNECTION AND UTILITY FUNCTIONS
def connect_db():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn

def get_expense_or_404(expense_id: int):
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,),).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Expense not found",)
    return row

def format_expense(row):
    return {"id": row["id"], "amount": row["amount"] / 100, "category": row["category"], "expense_date": row["expense_date"],"description": row["description"],}

# REQUEST MODEL

class Expense(BaseModel):
    amount: float = Field(gt=0, allow_inf_nan=False)
    category: str = Field(min_length=1, max_length=50)
    expense_date: date
    description: str = Field(min_length=1, max_length=500)


def validate_expense(expense: Expense):
    if expense.category.strip() not in CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Category must be one of: {', '.join(sorted(CATEGORIES))}",)

    if not expense.description.strip():
        raise HTTPException(status_code=422, detail="Description cannot be empty",)

    # Store money in integer paise.
    paise = round(expense.amount * 100)

    if paise <= 0 or abs(expense.amount * 100 - paise) > 0.000001:
        raise HTTPException(status_code=422, detail="Amount must be at least ₹0.01 and use at most two decimal places",)

    return (paise, expense.category.strip(), expense.expense_date.isoformat(), expense.description.strip(),)

#HOME
@app.get("/")
def home():
    return {"message": "Expense Tracker API is running", "documentation": "/docs",}

# GET ALL EXPENSES AND FILTERS
@app.get("/expenses")
def get_expenses(category: str | None = None, start_date: date | None = None, end_date: date | None = None,):
    if category and category not in CATEGORIES:
        raise HTTPException(400, "Invalid category")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(400, "Start date must not be after end date")

    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if start_date:
        query += " AND expense_date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        query += " AND expense_date <= ?"
        params.append(end_date.isoformat())

    query += " ORDER BY expense_date DESC, id DESC"

    with connect_db() as conn:
        rows = conn.execute(query, params).fetchall()

    return [format_expense(row) for row in rows]

# GET ONE EXPENSE
@app.get("/expenses/{expense_id}")
def get_expense(expense_id: int):
    return format_expense(get_expense_or_404(expense_id))

#POST CREATE EXPENSE
@app.post("/expenses", status_code=201)
def create_expense(expense: Expense):
    values = validate_expense(expense)
    with connect_db() as conn:
        cursor = conn.execute("""INSERT INTO expenses (amount, category, expense_date, description) VALUES (?, ?, ?, ?)""", values,)
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return format_expense(row)


# PUT UPDATE EXPENSE
@app.put("/expenses/{expense_id}")
def update_expense(expense_id: int, expense: Expense):
    values = validate_expense(expense)
    with connect_db() as conn:
        existing = conn.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        if existing is None:
            raise HTTPException(404, "Expense not found")

        conn.execute("""UPDATE expenses SET amount = ?, category = ?, expense_date = ?, description = ? WHERE id = ? """, (*values, expense_id),)
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,),).fetchone()
    return format_expense(row)


# DELETE EXPENSE
@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int):
    with connect_db() as conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,),)
        if cursor.rowcount == 0:
            raise HTTPException(404, "Expense not found")
    return {"message": "Expense deleted successfully"}


# SPENDING SUMMARY
@app.get("/summary")
def spending_summary():
    with connect_db() as conn:
        total = conn.execute("""SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS amount FROM expenses""").fetchone()
        categories = conn.execute("""SELECT category, COUNT(*) AS count, SUM(amount) AS amount FROM expenses GROUP BY category ORDER BY amount DESC""").fetchall()
    return {
        "total_expenses": total["count"],
        "total_spending": total["amount"] / 100,
        "by_category": [
            {"category": row["category"], "expense_count": row["count"], "total_spending": row["amount"] / 100,}
            for row in categories
        ],
    }
