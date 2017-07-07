from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
import time
from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    id=session['user_id']
    new = db.execute("SELECT * from users WHERE id= :id", id=id)
    username=new[0]['username']
    cash = usd(new[0]['cash'])
    rows=db.execute("SELECT * FROM transactions WHERE username=:username", username=username)
    if rows:
        symbol = []
        name = []
        shares = []
        price=[]
        stock_price = []
        totalvalue = []
        grand = 0
        for row in rows:
            symbol.append(row['stock'])
            name.append(row['stock_name'])
            shares.append(row['amount_of_shares'])
            quote=lookup(row['stock'])
            stock_price.append(usd(row['price']))
            totalvalue.append(usd(row['amount_of_shares'] * row['price']))
            grand = grand + (row['amount_of_shares'] * row['price'])
        grand = grand + new[0]['cash']
        length=len(rows)
        return render_template("index.html",length=length, symbol=symbol, name=name, shares=shares, stock_price=stock_price, 
        totalvalue=totalvalue, cash=cash, grand=usd(grand))  
    else:
        return render_template("index.html",length=0, symbol=[], name=[], shares=[], stock_price=[], 
        totalvalue=[], cash=cash, grand=cash)
    
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    # """Buy shares of stock."""
   
    if request.method == "POST":
        if not request.form.get("input"):
            return apology("must enter symbol")
        elif int(request.form.get("shares"))<0:
            return apology("enter a positive number")
        id=session['user_id']
        symbol= (request.form.get("input")).upper()
        quote = lookup(symbol)
        price= quote['price']
        name=quote['name']
        shares= int(request.form.get("shares"))
        row = db.execute("SELECT * from users WHERE id=:id", id=id)
        cash= int(row[0]['cash'])
        amount = price * shares
        total= cash-amount
        grand=total+amount
        username=row[0]['username']
        current_time= time.strftime("%H:%M:%S %d/%m/%Y")
        if (total<0):
            return apology("can't afford")
        else:
            db.execute("UPDATE users SET cash=:total WHERE id=:id", total=total, id=id)
            new = db.execute("SELECT stock from history WHERE username= :username", username=username)
            db.execute("INSERT INTO history (stock, amount_of_shares, price, username, time) VALUES (:symbol, :shares, :amount, :username, :current_time)", 
                symbol=symbol, shares=shares, amount=amount,username=username, current_time=current_time)
            more=db.execute("SELECT * from transactions WHERE stock=:symbol AND username=:username", symbol=symbol, username=username)
            if more:
                amount_of_shares=shares+more[0]['amount_of_shares']
                db.execute("UPDATE transactions SET amount_of_shares=:amount_of_shares, cash=:cash, grand=:grand WHERE stock=:symbol AND username=:username", amount_of_shares=amount_of_shares, cash=total, grand=grand, symbol=symbol, username=username)
            else:
                db.execute("INSERT INTO transactions (username, stock_name, stock, amount_of_shares, price, cash, grand) VALUES (:username, :stock_name, :symbol, :amount_of_shares, :price, :cash, :grand)", 
                username=username, stock_name=name, symbol=symbol, amount_of_shares=shares, price=price, cash=total, grand=grand)
            
        return redirect(url_for("index")) 
        
    else:
        return render_template("buy.html")   

@app.route("/history")
@login_required
def history():
    id=session['user_id']
    new = db.execute("SELECT * from users WHERE id= :id", id=id)
    username=new[0]['username']
    cash = usd(new[0]['cash'])
    rows=db.execute("SELECT * FROM history WHERE username=:username", username=username)
    if rows:
        name = []
        symbol = []
        shares = []
        price=[]
        time = []
        for row in rows:
            symbol.append(row['stock'])
            quote=lookup(row['stock'])
            name.append(quote['name'])
            shares.append(row['amount_of_shares'])
            price.append(usd(row['price']))
            time.append(row['time'])
        length=len(rows)
        return render_template("history.html",length=length, symbol=symbol, name=name, shares=shares, price=price, time=time)  
    else:
        return render_template("index.html",length=0, symbol=[], name=[], shares=[], stock_price=[], 
        totalvalue=[], cash=cash, grand=cash)
    

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("register"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must type in symbol")
        elif request.form.get("symbol"):
            symbol= request.form.get("symbol")
            quote = lookup(symbol)
            return render_template("quoted.html",symbol=symbol, name= quote['name'], price= quote['price'])
    else: 
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "POST":
        if not request.form.get("user"):
            return apology("must create username")
        elif not request.form.get("password"):
            return apology("must create password")
        elif not request.form.get("repeat"):
            return apology("must re-enter password")  
        
        if not request.form.get("password")==request.form.get("repeat"):
            return apology("Passwords don't match") 
        else:
            hash= pwd_context.encrypt(request.form.get("repeat"))
        result= db.execute("INSERT INTO users (username, hash) VALUES (:user, :hash)", user= request.form.get("user"), hash=pwd_context.encrypt(request.form.get("repeat")))
        if result:
            return redirect(url_for("index", length=0))
        else:
            return apology("Username already exists")
    else:
        return render_template("register.html")   
    
    

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must enter symbol")
        elif not request.form.get("shares"):
            return apology("must enter shares")
        else:
            symbol=(request.form.get("symbol")).upper()
            shares=int(request.form.get("shares"))
        row=db.execute("SELECT * from users WHERE id= :id", id=session['user_id'])
        username = row[0]['username']
        cash=row[0]['cash']
        new = db.execute("SELECT * from transactions WHERE stock=:symbol AND username=:username", symbol=symbol, username=username)
        if not new:
            return apology("enter a stock you own")
        stockamount=int(new[0]['amount_of_shares'])
        if stockamount<shares:
            return apology("you don't own enough stocks")
        else:
            amount_of_shares= stockamount-shares
        if amount_of_shares==0:
            db.execute("DELETE FROM transactions where stock=:symbol", symbol=symbol)
        else:
            quote=lookup(symbol)
            price=quote['price']
            cash=(amount_of_shares*price)+cash
            grand=cash
            ttime=time.strftime("%H:%M:%S %d/%m/%Y")
            db.execute("UPDATE transactions SET amount_of_shares=:amount_of_shares, price=:price, cash=:cash, grand=:grand  WHERE stock=:symbol", amount_of_shares=amount_of_shares, price=price, cash=cash, grand=grand, symbol=symbol)
            db.execute("INSERT INTO history (stock, amount_of_shares, price, username, time) VALUES (:symbol, :shares, :amount, :username, :current_time)",                     symbol=symbol, shares=0-shares, amount=price,username=username, current_time=ttime)
        return redirect(url_for("index")) 
    else:
        return render_template("sell.html")   

            