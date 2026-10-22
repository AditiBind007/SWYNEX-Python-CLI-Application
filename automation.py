import csv
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "expenses.db"
EXPORT_DIR = BASE_DIR / "exports"
BACKUP_DIR = BASE_DIR / "backups"

def export_expenses():
    """Export all expenses to a CSV file."""
    if not DATABASE.exists():
        print("Database does not exist. Run expense_tracker.py first.")
        return

    EXPORT_DIR.mkdir(exist_ok=True)

    file = (EXPORT_DIR / f"expenses_{datetime.now(): %Y%m%d_%H%M%S}.csv")
    with sqlite3.connect(str(DATABASE)) as conn:
        rows = conn.execute("""SELECT id, amount, category, expense_date, description FROM expenses ORDER BY expense_date DESC""").fetchall()
    with file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Amount(INR)", "Category", "Date", "Description"])
        for row in rows:
            writer.writerow([row[0], f"₹{row[1] / 100:.2f}", row[2], row[3], row[4]])
            print(f"Export completed: {file}")

def backup_database():
    """Create a timestamped backup of the SQLite database."""
    if not DATABASE.exists():
        print("Database does not exist. Run expense_tracker.py first.")
        return

    BACKUP_DIR.mkdir(exist_ok=True)

    file = (BACKUP_DIR / f"expenses_backup_{datetime.now(): %Y%m%d_%H%M%S}.db")

    with sqlite3.connect(str(DATABASE)) as source:
        with sqlite3.connect(str(file)) as destination:
            source.backup(destination)
    print(f"Backup created: {file}")

def monthly_report():
    """Show spending totals for the current month."""
    if not DATABASE.exists():
        print("Database does not exist. Run expense_tracker.py first.")
        return

    today = datetime.now()
    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    month_end = next_month.strftime("%Y-%m-%d")

    with sqlite3.connect(str(DATABASE)) as conn:
        total = conn.execute("""SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE expense_date >= ? AND expense_date < ? """, (month_start, month_end)).fetchone()[0]
        categories = conn.execute("""SELECT category, SUM(amount) FROM expenses WHERE expense_date >= ? AND expense_date < ? GROUP BY category ORDER BY SUM(amount) DESC""", (month_start, month_end)).fetchall()
    print(f"\nMonthly Report : {today.strftime('%B %Y')}")
    print("-" * 35)
    print(f"Total Spending: ₹ {total / 100:.2f}")

    print("\nSpending by Category:")
    if not categories:
        print("No expenses recorded for this month.")
    else:
        for category, amount in categories:
            print(f"{category}: ₹ {amount / 100:.2f}")

def main():
    while True:
        print("\n--- Expense Automation Tool ---")
        print("1. Export Expenses to CSV")
        print("2. Back up Database")
        print("3. Generate Monthly Report")
        print("4. Exit")

        choice = input("Enter your choice: ").strip()

        if choice == '1':
            export_expenses()
        elif choice == '2':
            backup_database()
        elif choice == '3':
            monthly_report()
        elif choice == '4':
            print("Automation tool closed.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
