from cs50 import SQL
from helpers import lookup

db = SQL("sqlite:///finance.db")
stock_data = []

# Create an empty list to store history of transactions
transaction_history = []

# Get history of transactions by user from database
transactions = db.execute("SELECT symbol, shares, price, transacted FROM transactions WHERE user_id = :user_id ORDER BY transacted",
user_id=14)

# Append each transaction to transaction_history list
for transaction in transactions:
    transaction_history.append(transaction)

print(transaction_history)