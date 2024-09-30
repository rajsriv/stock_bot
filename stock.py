import random
import pyrogram
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
import threading
import time
import sqlite3
from pyrogram import enums
from datetime import datetime

# Initialize the Pyrogram client
api_id = "2208722"
api_hash = "1d6e03d89eab1c53223d40fc154999e0"
bot_token = '6537996760:AAGQ5CPd2p4Jlk_DD2h8pIeJz0647cbHT30'

app = Client("stockManiaBot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Initialize SQLite3 database
conn = sqlite3.connect("stock_market.db", check_same_thread=False)
cursor = conn.cursor()

# Create tables if not exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 5000,
    portfolio TEXT DEFAULT '{}',
    initial_balance REAL DEFAULT 5000
)
""")
conn.commit()

# Add initial_balance column to existing table if it doesn't exist
try:
    cursor.execute("""
    ALTER TABLE users ADD COLUMN initial_balance REAL DEFAULT 5000
    """)
    conn.commit()
except sqlite3.OperationalError:
    # The column might already exist
    pass

# Define the stock class
class Stock:
    def __init__(self, name, price):
        self.name = name
        self.price = price

    def update_price(self):
        self.price += random.uniform(-5, 5)

# Create a dictionary to store stocks
stock_market = {
    "ASHCL": Stock("Ashirwad Capital Ltd", 5),
    "SPCL": Stock("Speedage Commercials Ltd", 10),
    "UCOB": Stock("UCO Bank", 50),
    "AAPL": Stock("Apple Inc.", 150),
    "TSTL": Stock("Tata Steel", 250),
    "NSTLE": Stock("Nestle India", 2745),
    "GOOGL": Stock("Alphabet Inc.", 2800),
    "AMZN": Stock("Amazon.com Inc.", 3300),
    "HAIL": Stock("Honeywell Automation India Ltd", 49540),
    "MRF": Stock("MRF Ltd", 139156),
}


# Function to periodically update stock prices
def update_stock_prices():
    while True:
        for stock_symbol, stock in stock_market.items():
            stock.update_price()
        time.sleep(3 * 60 * 60)  # Update every 3 hours

# Create and start a thread to update stock prices
update_thread = threading.Thread(target=update_stock_prices)
update_thread.daemon = True
update_thread.start()

# Function to get user data from the database
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

# Function to create a new user
def create_user(user_id):
    cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

# Handle the /start command in DM
@app.on_message(filters.command("start") & filters.private)
async def start_dm(_, message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        create_user(user_id)

    welcome = "**Welcome to the Stock Market Bot!**\n\n▸ Use /buy or /sell to trade stocks.\n▸ Use /account to check your balance and stocks."
    stock_status = (
        "**Current Stocks**\n\n"
        "▸ Apple Inc. : AAPL\n"
        "▸ Alphabet Inc. : GOOGL\n"
        "▸ Amazon Inc. : AMZN\n\n"
        "Use /buy or /sell to trade Stocks.\n"
        "Use /account to check your balance and stocks.\n"
        "Use /market to view current stock prices."
    )

    await app.send_message(message.chat.id, welcome, parse_mode=enums.ParseMode.MARKDOWN)
    await app.send_message(message.chat.id, stock_status, parse_mode=enums.ParseMode.MARKDOWN)

# Handle the /buy command
@app.on_message(filters.command("buy") & filters.private)
async def buy_stock(_, message: Message):
    # Rest of your code
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.reply("Please start the bot by using /start.")
        return

    text = message.text.split(" ")
    if len(text) != 3:
        await message.reply("Usage: /buy [stock_symbol] [quantity]")
        return

    stock_symbol = text[1].upper()
    quantity = int(text[2])

    if stock_symbol in stock_market:
        stock = stock_market[stock_symbol]
        cost = stock.price * quantity

        if user[1] >= cost:  # Check if the user has enough balance
            new_balance = user[1] - cost
            portfolio = eval(user[2])
            portfolio[stock_symbol] = portfolio.get(stock_symbol, 0) + quantity

            # Update the user's balance and portfolio in the database
            cursor.execute("UPDATE users SET balance=?, portfolio=? WHERE user_id=?", (new_balance, str(portfolio), user_id))
            conn.commit()

            await message.reply(f"You have purchased {quantity} shares of {stock.name}.")
        else:
            await message.reply("Not enough funds in your wallet to buy.")
    else:
        await message.reply("Stock not found in the market.")

# Handle the /sell command
@app.on_message(filters.command("sell") & filters.private)
async def sell_stock(_, message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.reply("Please start the bot by using /start.")
        return

    text = message.text.split(" ")
    if len(text) != 3:
        await message.reply("Usage: /sell [stock_symbol] [quantity]")
        return

    stock_symbol = text[1].upper()
    quantity = int(text[2])

    if stock_symbol in stock_market:
        stock = stock_market[stock_symbol]
        portfolio = eval(user[2])

        if portfolio.get(stock_symbol, 0) >= quantity:  # Check if the user owns enough shares
            earnings = stock.price * quantity
            new_balance = user[1] + earnings
            portfolio[stock_symbol] -= quantity

            if portfolio[stock_symbol] == 0:
                del portfolio[stock_symbol]  # Remove stock from portfolio if all shares are sold

            # Update the user's balance and portfolio in the database
            cursor.execute("UPDATE users SET balance=?, portfolio=? WHERE user_id=?", (new_balance, str(portfolio), user_id))
            conn.commit()

            await message.reply(f"You have sold {quantity} shares of {stock.name}.")
        else:
            await message.reply("You don't have enough shares to sell.")
    else:
        await message.reply("Stock not found in the market.")

# Handle the /account command to show user's stocks and compare with current prices
@app.on_message(filters.command("account") & filters.private)
async def check_account(_, message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.reply("Use in DM")
        return

    portfolio = eval(user[2])
    message_text = f"Your balance: ${user[1]:.2f}\n\nYour Stocks:\n"

    total_value = 0
    for stock_symbol, quantity in portfolio.items():
        stock = stock_market.get(stock_symbol)
        if stock:
            current_value = stock.price * quantity
            total_value += current_value
            message_text += f"{stock.name} ({stock_symbol}): {quantity} shares\n"
            message_text += f"  Current Price: ${stock.price:.2f}\n"
            message_text += f"  Total Value: ${current_value:.2f}\n\n"

    message_text += f"Total Value of Stocks: ${total_value:.2f}"

    await message.reply(message_text, parse_mode=enums.ParseMode.MARKDOWN)

# Handle the /market command to display one stock at a time with Next/Prev buttons
@app.on_message(filters.command("market") & filters.private)
async def market_status(_, message: Message):
    stock_symbols = list(stock_market.keys())  # Get the list of all stock symbols
    current_stock_index = 0  # Start with the first stock

    # Function to generate inline buttons for navigating stock list
    def generate_market_buttons(stock_index):
        prev_button = InlineKeyboardButton("⬅️ Previous", callback_data=f"prev_{stock_index}")
        next_button = InlineKeyboardButton("➡️ Next", callback_data=f"next_{stock_index}")
        buttons = []

        if stock_index > 0:
            buttons.append(prev_button)
        if stock_index < len(stock_symbols) - 1:
            buttons.append(next_button)

        return InlineKeyboardMarkup([buttons])

    # Send the initial stock details message with navigation buttons
    stock_symbol = stock_symbols[current_stock_index]
    stock = stock_market[stock_symbol]
    stock_text = f"**{stock.name} ({stock_symbol})**\n\nPrice: ${stock.price:.2f}"

    await message.reply(
        stock_text,
        reply_markup=generate_market_buttons(current_stock_index),
        parse_mode=enums.ParseMode.MARKDOWN
    )

# Handle the callback queries for navigating stock details
@app.on_callback_query(filters.regex(r"^(prev|next)_\d+"))
async def navigate_stocks(_, query):
    _, stock_index = query.data.split("_")
    stock_index = int(stock_index)

    stock_symbols = list(stock_market.keys())

    if "prev" in query.data:
        stock_index -= 1
    elif "next" in query.data:
        stock_index += 1

    stock_symbol = stock_symbols[stock_index]
    stock = stock_market[stock_symbol]
    stock_text = f"**{stock.name} ({stock_symbol})**\n\nPrice: ${stock.price:.2f}"

    await query.message.edit_text(
        stock_text,
        reply_markup=generate_market_buttons(stock_index),
        parse_mode=enums.ParseMode.MARKDOWN
    )

# Function to generate buttons (kept outside of both functions for reusability)
def generate_market_buttons(stock_index):
    stock_symbols = list(stock_market.keys())
    prev_button = InlineKeyboardButton("⬅️ Previous", callback_data=f"prev_{stock_index}")
    next_button = InlineKeyboardButton("➡️ Next", callback_data=f"next_{stock_index}")
    buttons = []

    if stock_index > 0:
        buttons.append(prev_button)
    if stock_index < len(stock_symbols) - 1:
        buttons.append(next_button)

    return InlineKeyboardMarkup([buttons])


# Function to calculate profit or loss percentage
def calculate_profit_loss(initial_balance, current_balance):
    difference = current_balance - initial_balance
    percentage = (difference / initial_balance) * 100
    return percentage

# Handle the /profile command to show user's profile
@app.on_message(filters.command("profile") & filters.private)
async def show_profile(_, message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.reply("Use in DM")
        return
        
    # Get user's name and Telegram ID
    user_name = message.from_user.first_name
    telegram_id = message.from_user.id
    
    # Get user's balance and portfolio
    current_balance = user[1]
    initial_balance = user[3]  # Assuming the initial balance is stored in the 4th column
    portfolio = eval(user[2])

    # Calculate total stocks owned
    total_stocks = sum(portfolio.values())

    # Calculate profit or loss percentage
    profit_loss_percentage = calculate_profit_loss(initial_balance, current_balance)

    # Prepare the profile message
    profile_message = (
        f"**Profile Information**\n\n"
        f"**Name:** {user_name}\n"
        f"**Telegram ID:** {telegram_id}\n\n"
        f"**Total Balance:** ${current_balance:.2f}\n"
        f"**Total Stocks Owned:** {total_stocks}\n\n"
        f"**Profit/Loss Percentage:** {profit_loss_percentage:.2f}%"
    )

    # Add the "Stocks Hold" button to view the user's portfolio
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Stocks Hold", callback_data="stocks_hold")]]
    )

    await message.reply(profile_message, reply_markup=keyboard, parse_mode=enums.ParseMode.MARKDOWN)


# Handle the callback from the "Stocks Hold" button
@app.on_callback_query(filters.regex("stocks_hold"))
async def show_stocks_hold(_, callback_query):
    user_id = callback_query.from_user.id
    user = get_user(user_id)

    if not user:
        await callback_query.message.reply("Please start the bot by using /start.")
        return

    portfolio = eval(user[2])
    if portfolio:
        message_text = "You are holding the following stocks:\n\n"
        for stock_symbol, quantity in portfolio.items():
            stock = stock_market.get(stock_symbol)
            if stock:
                message_text += f"{stock.name} ({stock_symbol}): {quantity} shares\n"
    else:
        message_text = "You do not hold any stocks at the moment."

    await callback_query.message.edit_text(message_text, parse_mode=enums.ParseMode.MARKDOWN)


# Handle the /achievement command to give titles based on balance
@app.on_message(filters.command("achievement"))
async def achievement(_, message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.reply("Please start the bot by using /start.")
        return

    balance = user[1]
    titles = [
        (10000, "Small Business Owner"),
        (20000, "Entrepreneur"),
        (40000, "Business Tycoon"),
        (80000, "Market Giant"),
    ]

    # Determine the title based on the user's balance
    user_title = "Beginner"
    for threshold, title in titles:
        if balance >= threshold:
            user_title = title
        else:
            break

    await message.reply(f"Your current business title: **{user_title}**", parse_mode=enums.ParseMode.MARKDOWN)

# Run the bot
app.run()  # Listen on port 5000

