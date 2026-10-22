from datetime import date
from decimal import Decimal
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator

from automation import DATABASE

BASE_DIR = Path(__file__).resolve().parent
DATABASE_NAME = BASE_DIR / "expenses.db"

CATEGORIES = {"Food", "Transport", "Shopping", "Bills","Health", "Education", "Entertainment", "Other"}

app = FastAPI(title="Expense Tracker REST API", description="Manage expenses using Python and SQLite.", version="1.0.0",)

class ExpenseInput(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    category: str = Field(min_length=1, max_length=50)
    expense_date: date
    description: str = Field(min_length=1, max_length=200)

    @field_validator("category", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError(
                f"Category must be one of: {', '.join(sorted(CATEGORIES))}"
            )
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount_precision(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value.as_tuple().exponent < -2:
            raise ValueError("Amount must have at most 2 decimal places")
        return value


def get_connection():
    if not DATABASE.exists():
        raise HTTPException(
            status_code=500,
            detail="Database not found. Run expense_tracker.py first.",
        )

    conn = sqlite3.connect(str(DATABASE, encoding="utf-8"))
    conn.row_factory = sqlite3.Row
    return conn


def to_dict(row):
    return {
        "id": row["id"],
        "amount": f"{row['amount_paise'] / 100:.2f}",
        "category": row["category"],
        "expense_date": row["expense_date"],
        "description": row["description"],
    }


def get_expense_or_404(conn, expense_id: int):
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ?", (expense_id,)
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    return row


@app.get("/")
def home():
    return {"message": "Expense Tracker REST API is running"}


@app.get("/expenses")
def list_expenses(
    category: str | None = Query(default=None, max_length=50),
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date cannot be after end_date",
        )

    conditions = []
    params = []

    if category:
        if category not in CATEGORIES:
            raise HTTPException(status_code=422, detail="Invalid category")
        conditions.append("category = ?")
        params.append(category)

    if start_date:
        conditions.append("expense_date >= ?")
        params.append(start_date.isoformat())

    if end_date:
        conditions.append("expense_date <= ?")
        params.append(end_date.isoformat())

    sql = "SELECT * FROM expenses"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY expense_date DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [to_dict(row) for row in rows]


@app.get("/expenses/{expense_id}")
def get_expense(expense_id: int):
    with get_connection() as conn:
        row = get_expense_or_404(conn, expense_id)
        return to_dict(row)


@app.post("/expenses", status_code=201)
def create_expense(expense: ExpenseInput):
    amount_paise = int(expense.amount * 100)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO expenses
                (amount_paise, category, expense_date, description)
            VALUES (?, ?, ?, ?)
            """,
            (
                amount_paise,
                expense.category,
                expense.expense_date.isoformat(),
                expense.description,
            ),
        )
        row = get_expense_or_404(conn, cursor.lastrowid)
        return to_dict(row)


@app.put("/expenses/{expense_id}")
def update_expense(expense_id: int, expense: ExpenseInput):
    amount_paise = int(expense.amount * 100)

    with get_connection() as conn:
        get_expense_or_404(conn, expense_id)

        conn.execute(
            """
            UPDATE expenses
            SET amount_paise = ?,
                category = ?,
                expense_date = ?,
                description = ?
            WHERE id = ?
            """,
            (
                amount_paise,
                expense.category,
                expense.expense_date.isoformat(),
                expense.description,
                expense_id,
            ),
        )

        row = get_expense_or_404(conn, expense_id)
        return to_dict(row)


@app.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int):
    with get_connection() as conn:
        get_expense_or_404(conn, expense_id)
        conn.execute(
            "DELETE FROM expenses WHERE id = ?", (expense_id,)
        )

    return Response(status_code=204)


@app.get("/summary")
def expense_summary():
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COALESCE(SUM(amount_paise), 0) FROM expenses"
        ).fetchone()[0]

        categories = conn.execute(
            """
            SELECT category, SUM(amount_paise) AS total_paise
            FROM expenses
            GROUP BY category
            ORDER BY total_paise DESC
            """
        ).fetchall()

    return {
        "total_expenses": f"{total / 100:.2f}",
        "currency": "INR",
        "by_category": [
            {
                "category": row["category"],
                "total": f"{row['total_paise'] / 100:.2f}",
            }
            for row in categories
        ],
    }
