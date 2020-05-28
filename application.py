import os
import logging
import sys
from logging import Formatter

from datetime import datetime
#from cs50 import SQL
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

def log_to_stderr(app):
  handler = logging.StreamHandler(sys.stderr)
  handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
  ))
  handler.setLevel(logging.WARNING)
  app.logger.addHandler(handler)

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
#db = SQL("sqlite:///finance.db")

# Link to Postgres database on Heroku
DATABASE_URL = "postgres://shhdowemmmuznp:7ee8f235c605392a2c91d8c158a22518aad3362a7a07c8b942b5608c6d178753@ec2-52-207-25-133.compute-1.amazonaws.com:5432/d97g3jjeli2217"

# Create engine object to manage connections to DB, and scoped session to separate user interactions with DB
engine = create_engine(DATABASE_URL)
db = scoped_session(sessionmaker(bind=engine))

# Make sure API key is set
if not os.environ.get("API_KEY"):
    # Set API ke for the stock quote engine
    try:
        os.environ["API_KEY"] = "pk_771aa03ef26749dc9d8009662d7ee804"
    except:
        raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Create blank list called stock_data to store values for index
    stock_data = []

    # Get cash owned by user from db
    cash_row  = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"]).fetchone()
    cash = cash_row[0]["cash"]

    # Get total value of all stocks and cash owned by the user
    total_value = cash

    # Get stocks in portfolio from db
    stocks = db.execute("SELECT * FROM portfolio WHERE user_id=:user_id ORDER BY symbol", user_id=session["user_id"]).fetchall()

    # Iterate through stocks to add data to stock list
    for i in range(len(stocks)):
        new_dict = {}
        stock_data.append(new_dict)
        stock_info = lookup(stocks[i]["symbol"])
        stock_data[i].update({"shares":stocks[i]["shares"]})
        for data in stock_info:
            stock_data[i].update({data:stock_info[data]})
            if (data=="price"):
                price = float(stock_info[data])
                shares = int(stock_data[i]["shares"])
                shares_price_value = round(price*shares, 2)
                total_value += shares_price_value
                price = "{:,.2f}".format(price)
                shares_price = "{:,.2f}".format(shares_price_value)
                stock_data[i].update({"shares_price":shares_price})
                stock_data[i].update({"price":price})

    # Format value to make it standardised
    total_value = "{:,.2f}".format(total_value)
    cash = "{:,.2f}".format(cash)

    return render_template("index.html", cash=cash, stock_data=stock_data, total_value=total_value)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # error handler to make sure positive integer number of stocks is entered
    #error = None

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Store symbol and shares as variable
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        # Ensure stock symbol was submitted
        if not symbol:
            #error = "must provide stock symbol"
            return apology("must provide stock symbol", 403)

        # Ensure number of shares was submitted
        elif not shares:
            #error = "must provide shares"
            return apology("must provide shares", 403)

        # Make sure number of shares is a positive integer
        elif (shares<1):
            #error = 'must provide shares of 1 or more'
            return apology("must provide positive number for shares", 403)

        # Perform lookup on the symbol
        stock_info = lookup(symbol)

        # Make sure stock exists
        if not stock_info or stock_info["name"] == "":
            return apology("no such stock", 404)

        # Retrieve cash amount in database
        cash_row = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"]).fetchone()
        cash = float(cash_row[0]["cash"])

        # Make sure user has enough cash to buy the shares of that stock
        shares_cost = float(stock_info["price"]) * shares
        if (cash<shares_cost):
            return apology("Can't afford :(", 400)

        # Update tables with new values if user can afford the stock
        else:
            # Get time of transaction
            time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Update cash value to reflect purchase
            cash -= shares_cost

            # Update tables with relevant values
            # Update users table
            db.execute("UPDATE users SET cash=:cash WHERE id=:user_id", user_id=session["user_id"], cash=cash)

            # Update transactions table
            db.execute("INSERT INTO transactions(symbol, shares, price, transacted, user_id) VALUES(:symbol, :shares, :price, :transacted, :user_id)",
            symbol=symbol, shares=shares, price=stock_info["price"], transacted=time, user_id=session["user_id"])

            # Update portfolio table, checking if they already own shares of this stock
            # Query if they already own this stock
            rows = db.execute("SELECT * FROM portfolio WHERE user_id = :user_id AND symbol= :symbol",
                          user_id=session["user_id"], symbol=symbol)

            # If stock already exists in portfolio, update the table with new value
            if (len(rows)>0):
                shares_owned = rows[0]["shares"]
                shares += shares_owned
                db.execute("UPDATE portfolio SET shares=:shares WHERE user_id=:user_id AND symbol=:symbol", user_id=session["user_id"], symbol=symbol, shares=shares)

            # Insert new row into table if user doesn't already own the stock bought
            else:
                db.execute("INSERT INTO portfolio(symbol, shares, user_id) VALUES(:symbol, :shares, :user_id)",
            symbol=symbol, shares=shares, user_id=session["user_id"])

            # Return to homepage
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Create an empty list to store history of transactions
    transaction_history = []

    # Get history of transactions by user from database
    transactions = db.execute("SELECT symbol, shares, price, transacted FROM transactions WHERE user_id = :user_id ORDER BY transacted",
    user_id=session["user_id"]).fetchone()

    # Append each transaction to transaction_history list
    for transaction in transactions:
        transaction_history.append(transaction)

    # Show user page with history of transactions
    return render_template("history.html", transaction_history=transaction_history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username":request.form.get("username")}).fetchone()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Store symbol in variable for ease of use
        symbol = request.form.get("symbol")

        # Ensure stock symbol was submitted
        if not symbol:
            return apology("must provide stock symbol", 406)

        # Lookup stock sybol and store stock info in variable
        stock_info = lookup(symbol)

        # Check if stock actually exists
        if not stock_info or stock_info["name"] == "":
            return apology("no such stock", 404)

        # Return stock info requested as special template using stock info data if found
        return render_template("quoted.html", stock_info=stock_info)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 406)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 406)

        # Query database for username to see if it already exists
        user_exists = db.execute("SELECT username FROM users WHERE username = :username",
                          {"username":request.form.get("username")}).fetchone()

        # Check to see if username already exists and reject registration
        if user_exists:
            return apology("username already exists", 409)

        # Enter username and hashed password into database if it doesn't already exist
        else:

            # Get username to use in SQL database
            username = request.form.get("username")

            # Hash password string
            pass_hash = generate_password_hash(request.form.get("password"))

            # Insert user into users table
            db.execute("INSERT INTO users(username, hash) VALUES(:username, :hashcode)", {"username":username, "hashcode":pass_hash})

            # Redirect user to home page
            return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # error handler to make sure positive integer number of stocks is entered
    #error = None

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Store symbol and shares as variable
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        # Ensure stock symbol was submitted
        if not symbol:
            #error = "must provide stock symbol"
            return apology("must provide stock symbol", 403)

        # Ensure number of shares was submitted
        elif not shares:
            #error = "must provide shares"
            return apology("must provide shares", 403)

        # Make sure number of shares is a positive integer
        elif (shares<1):
            #error = 'must provide shares of 1 or more'
            return apology("must provide positive number for shares", 403)

        # Perform lookup on the symbol
        stock_info = lookup(symbol)

        # Make sure stock exists
        if not stock_info or stock_info["name"] == "":
            return apology("no such stock", 404)

        # Retrieve shares amount in database
        shares_row = db.execute("SELECT shares FROM portfolio WHERE user_id=:user_id AND symbol=:symbol", user_id=session["user_id"], symbol=symbol).fetchone()
        shares_owned = int(shares_row[0]["shares"])

        # Retrieve cash amount in database
        cash_row = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])
        cash = float(cash_row[0]["cash"])

        # Make sure user has enough shares owned to sell the shares of that stock
        shares_cost = float(stock_info["price"]) * shares
        if (shares>shares_owned or len(shares_row)!=1):
            return apology("You don't own those shares", 403)

        # Update tables with new values if user has the shares
        else:

            # Get time of transaction
            time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Update cash value to reflect purchase
            cash += shares_cost

            # Update number of shares
            shares_owned -= shares

            # Update tables with relevant values
            # Update users table
            db.execute("UPDATE users SET cash=:cash WHERE id=:user_id", user_id=session["user_id"], cash=cash)

            # Update transactions table
            db.execute("INSERT INTO transactions(symbol, shares, price, transacted, user_id) VALUES(:symbol, :shares, :price, :transacted, :user_id)",
            symbol=symbol, shares=-shares, price=stock_info["price"], transacted=time, user_id=session["user_id"])

            # If shares owned of the stock is now zero, delete row from table
            if (shares_owned==0):
                db.execute("DELETE FROM portfolio WHERE symbol = :symbol AND user_id = :user_id",
                symbol=symbol, user_id=session["user_id"])

            else:
                # If stock already exists in portfolio, update the table with new value
                db.execute("UPDATE portfolio SET shares=:shares WHERE user_id=:user_id AND symbol=:symbol",
                user_id=session["user_id"], symbol=symbol, shares=shares_owned)

            # Return to homepage
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Show list of symbols that user has
        # Get symbols that user has
        symbols = db.execute("SELECT symbol FROM portfolio WHERE user_id=:user_id ORDER BY symbol", user_id=session["user_id"]).fetchall()

        # Return page with list of symbols that user owns
        return render_template("sell.html", symbols=symbols)

@app.route("/cash", methods=["POST"])
@login_required
def cash():
    """Add cash to user's balance"""

    # Store amount to be added to user's balance in variable
    value = float(request.form.get("cash"))

    # Make sure that cash is a positive integer, else return apology
    if (value<1):
        return apology("cannot remove cash via that method", 400)

    # Get cash that user currently has in account
    cash_row = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"]).fetchone()
    cash = float(cash_row[0]["cash"])

    # Update cash to new value
    cash += value

    # Get time of transaction
    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Update values in database for user logged in
    # Update users table
    db.execute("UPDATE users SET cash=:cash WHERE id=:user_id", user_id=session["user_id"], cash=cash)

    # Update transactions table
    db.execute("INSERT INTO transactions(symbol, shares, price, transacted, user_id) VALUES(:symbol, :shares, :price, :transacted, :user_id)",
    symbol="CASH", shares=value, price=value, transacted=time, user_id=session["user_id"])

    # Return user to portfolio page
    return redirect("/")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
    log_to_stderr(app)
    app.run()
