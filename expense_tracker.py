import sqlite3
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

BASE_DIR = Path(__file__).resolve().parent
BASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_NAME = BASE_DIR / "expenses.db"

def connect_db():
    """Connect to SQLite and create the table if needed."""
    try:
        print("Database path:", DATABASE_NAME)

        conn = sqlite3.connect(str(DATABASE_NAME))

        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER NOT NULL CHECK (amount >= 0),
                category TEXT NOT NULL,
                expense_date TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)

        conn.commit()
        print("Database connected successfully!")

        return conn

    except sqlite3.Error as error:
        print("Database connection error:", error)
        raise

#INPUT VALIDATION
def get_amount():
    """Accept a valid positive amount with at most 2 decimal places."""
    value = input("Enter amount in INR: ").strip()

    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        if amount.as_tuple().exponent < -2:
            raise ValueError("Enter at most 2 decimal places.")

        paise = amount*100
        if paise != paise.to_integral_value():
            raise ValueError("Invalid amount.")

        return int(paise)

    except InvalidOperation as error:
            raise ValueError("Enter a valid amount, e.g. 250.50") from error

def get_category():
    """Validate the expense category."""
    categories = ["Food", "Transport", "Shopping", "Bills", "Health", "Education", "Entertainment", "Other"]

    print("\nAvailable categories:")
    for category in categories:
        print("-", category)

    category = input("Enter category: ").strip()

    for valid_category in categories:
        if category.lower() == valid_category.lower():
            return valid_category

    raise ValueError("Invalid category. Please choose from the available categories.")

def get_date():
    """Accept a date in YYYY-MM-DD format or use today's date."""
    value = input("Enter date (YYYY-MM-DD), blank for today: ").strip()

    if not value:
        return date.today().isoformat()

    try:
        parsed_date = datetime.strptime(value, "%Y-%m-%d").date()
        if parsed_date.isoformat() != value:
            raise ValueError
        return value

    except ValueError as error:
        raise ValueError("Invalid date format. Please use YYYY-MM-DD.") from error

def get_description():
    description = input("Enter description: ").strip()
    if not description:
        raise ValueError("Description cannot be empty.")
    if len(description) > 200:
        raise ValueError("Description cannot exceed 200 characters.")
    return description

def format_money(paise):
    """Convert integer paise into a rupee amount."""
    rupees, remaining_paise = divmod(paise, 100)
    return f"₹{rupees}.{remaining_paise:02d}"

# ADD EXPENSE
def add_expense(conn):
    try:
        amount = get_amount()
        category = get_category()
        expense_date = get_date()
        description = get_description()

        conn.execute('''
            INSERT INTO expenses (amount, category, expense_date, description)
            VALUES (?, ?, ?, ?)
        ''', (amount, category, expense_date, description))
        
        conn.commit()
        print(f"\nExpense added successfully!")
    
    except ValueError as error:
        print("\nInput Error:", error)

    except sqlite3.Error as error:
        conn.rollback()
        print("\nDatabase Error:", error)

#VIEW ALL EXPENSES
def view_expenses(conn):
    try:
        cursor = conn.execute("""SELECT id, amount, category, expense_date, description FROM expenses ORDER BY expense_date DESC, id DESC""")
        expenses = cursor.fetchall()

        if not expenses:
            print("\nNo expenses found.")
            return

        print("\n" + "=" * 85)
        print(f"{'ID':<5} {'Amount':<15} {'Category':<18}" f"{'Date':<14}Description")
        print("=" * 85)

        for expense in expenses:
            expense_id, amount, category, expense_date, description = expense
            print(f"{expense_id:<5} {format_money(amount):<15} {category:<18} {expense_date:<14} {description}")
            print("=" * 85)
    
    except sqlite3.Error as error:
        print("\nDatabase Error:", error)

#TOTAL EXPENSES
def show_total(conn):
    try:
        cursor = conn.execute("""SELECT category, SUM(amount), COUNT(*) FROM expenses GROUP BY category ORDER BY SUM(amount) DESC""")
        
        results = cursor.fetchall()
        if not results:
            print("\nTotal Expenses: ₹0.00")
            return
        print("\n--- CATEGORY SUMMARY ---") 
        
        for category, total, count in results:
            print(f"{category:<18}, {format_money(total):>12}, {count} transaction(s)")
            
    except sqlite3.Error as error:
        print("\nDatabase Error:", error)

#CATERY-WISE SUMMARY
def category_summary(conn):
    try:
        cursor = conn.execute("""SELECT category, SUM(amount), COUNT(*) FROM expenses GROUP BY category ORDER BY SUM(amount) DESC""")
        
        results = cursor.fetchall()
        if not results:
            print("\nNo expenses available for summary.")
            return
        print("\n--- CATEGORY SUMMARY ---") 
        
        for category, total, count in results:
            print(f"{category:<18}, {format_money(total):>12}, {count} transaction(s)")
            
    except sqlite3.Error as error:
        print("\nDatabase Error:", error)

#SEARCH EXPENSES BY CATEGORY
def search_by_category(conn):
    try:
        category = get_category()

        cursor = conn.execute("""SELECT id, amount, expense_date, description FROM expenses WHERE category = ? ORDER BY expense_date DESC, id DESC""", (category,))
        
        results = cursor.fetchall()

        if not results:
            print(f"\nNo expenses found in {category}.")
            return

        print(f"\n--- {category.upper()} EXPENSES ---")

        for expense_id, amount, expense_date, description in results:
            print(f"ID: {expense_id} | {format_money(amount)} | {expense_date} | {description}")
                
    except ValueError as error:
        print("\nInput Error:", error)

    except sqlite3.Error as error:
        print("\nDatabase Error:", error)

#DELETE AN EXPENSE
def delete_expense(conn):
    try:
        value = input("Enter expense ID to delete: ").strip()
        expense_id = int(value)
        if expense_id <= 0:
            raise ValueError("ID must be a positive integer.")

        cursor = conn.execute("SELECT id, amount, category, description FROM expenses WHERE id = ?", (expense_id,))

        expense = cursor.fetchone()
        
        if expense is None:
            print("\nNo expenses found with that ID.")
            return
        print(f"\nID: {expense[0]} | Amount: {format_money(expense[1])} | Category: {expense[2]} | Description: {expense[3]}")
        confirm = input("Delete this expense? (y/n):").strip().lower()
        if confirm != 'y':
            print("Deletion cancelled.")
            return
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        print("Expense deleted successfully.")
    except ValueError as error:
        print("\nInput Error:", error)
    except sqlite3.Error as error:
        conn.rollback()
        print("\nDatabase Error:", error)

#MAIN MENU
def main():
    try:
        conn = connect_db()
    except sqlite3.Error as error:
        print("Could not open the database:", error)
        return
    
    print("=" * 40)
    print("PYTHON EXPENSE TRACKER")
    print("=" * 40)

    try:
        while True:
            print("\n--- EXPENSE TRACKER ---")
            print("1. Add Expense")
            print("2. View All Expenses")
            print("3. Show Total Expenses")
            print("4. Category-wise Summary")
            print("5. Search by Category")
            print("6. Delete Expense")
            print("7. Exit")
            print("-------------------------------------------")

            choice = input("Enter your choice (1-7): ").strip()
            if choice == "1":
                add_expense(conn)
            elif choice == "2":
                view_expenses(conn)
            elif choice == "3":
                show_total(conn)
            elif choice == "4":
                category_summary(conn)
            elif choice == "5":
                search_by_category(conn)
            elif choice == "6":
                delete_expense(conn)
            elif choice == "7":
                print("\nThank you for using Expense Tracker!")
                break
            else:
                print("Invalid choice. Please choose a number from 1 and 7.")
    except (KeyboardInterrupt, EOFError):
        print("\nApplication stopped safely.")
    finally:
        conn.close()

#PROGRAM ENTRY POINT
if __name__ == "__main__":
    main()
