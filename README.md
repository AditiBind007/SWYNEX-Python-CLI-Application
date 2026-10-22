# SWYNEX-Python-Application-Project
Expense Tracker REST API

A RESTful API built with Python, FastAPI, and SQLite for managing personal expenses.

Features

- Create, read, update, and delete expenses
- Filter expenses by category and date
- View total spending and category summaries
- Validate incoming request data
- Interactive API documentation with Swagger UI

Tech Stack

- Python
- FastAPI
- SQLite
- SQL
- Uvicorn

Setup

Install dependencies:

python -m pip install -r requirements.txt

Initialize the database by running your existing expense tracker once, or create the required "expenses" table using the schema documented in the project.

Start the API:

python -m uvicorn api:app --reload

Open the API documentation:

http://127.0.0.1:8000/docs

Endpoints

Method| Endpoint| Description
GET| "/expenses"| List expenses
GET| "/expenses/{expense_id}"| Retrieve one expense
POST| "/expenses"| Create an expense
PUT| "/expenses/{expense_id}"| Update an expense
DELETE| "/expenses/{expense_id}"| Delete an expense
GET| "/summary"| Spending summary

Database

SQLite stores expenses locally. The database file is excluded from version control.

Security

This project is intended for local development. Authentication and production security should be added before public deployment.
