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

# Handle inline queries for searching stocks or viewing profile
@app.on_inline_query()
async def answer_inline_query(client, inline_query):
    query = inline_query.query.strip().lower()
    user_id = inline_query.from_user.id

    # If the query is empty, don't return any results
    if not query:
        return

    results = []

    # If the query contains "profile", show the user's profile
    if "profile" in query:
        user = get_user(user_id)

        if not user:
            results.append(
                pyrogram.types.InlineQueryResultArticle(
                    title="Profile Not Found",
                    description="Start the bot by sending /start.",
                    input_message_content=pyrogram.types.InputTextMessageContent(
                        message_text="Please start the bot by using /start to view your profile."
                    )
                )
            )
        else:
            # Prepare profile information
            user_name = inline_query.from_user.first_name
            current_balance = user[1]
            initial_balance = user[3]
            portfolio = eval(user[2])
            total_stocks = sum(portfolio.values())
            profit_loss_percentage = calculate_profit_loss(initial_balance, current_balance)

            profile_message = (
                f"**Profile Information**\n\n"
                f"**Name:** {user_name}\n"
                f"**Telegram ID:** {user_id}\n\n"
                f"**Total Balance:** ${current_balance:.2f}\n"
                f"**Total Stocks Owned:** {total_stocks}\n\n"
                f"**Profit/Loss Percentage:** {profit_loss_percentage:.2f}%"
            )

            results.append(
                pyrogram.types.InlineQueryResultArticle(
                    title=f"{user_name}'s Profile",
                    description=f"Balance: ${current_balance:.2f}, Total Stocks: {total_stocks}",
                    input_message_content=pyrogram.types.InputTextMessageContent(
                        message_text=profile_message
                    )
                )
            )
    
    # Search for stocks if the query isn't "profile"
    else:
        for stock_symbol, stock in stock_market.items():
            if query in stock_symbol.lower() or query in stock.name.lower():
                stock_info = f"{stock.name} ({stock_symbol})\nPrice: ${stock.price:.2f}"
                results.append(
                    pyrogram.types.InlineQueryResultArticle(
                        title=f"{stock.name} ({stock_symbol})",
                        description=f"Price: ${stock.price:.2f}",
                        input_message_content=pyrogram.types.InputTextMessageContent(
                            message_text=stock_info
                        )
                    )
                )

    # Answer the inline query with the matching results
    await inline_query.answer(results, cache_time=1)

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
@app.on_message(filters.command("sell"))
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
            await message.reply(f"You don't own enough shares of {stock.name}.")
    else:
        await message.reply("Stock not found in the market.")

# Function to calculate profit or loss percentage
def calculate_profit_loss(initial_balance, current_balance):
    profit_loss = current_balance - initial_balance
    return (profit_loss / initial_balance) * 100

# Handle the /account command
@app.on_message(filters.command("account"))
async def account_info(_, message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.reply("Please start the bot by using /start.")
        return

    # Fetch user information
    current_balance = user[1]
    initial_balance = user[3]
    portfolio = eval(user[2])
    total_stocks = sum(portfolio.values())
    profit_loss_percentage = calculate_profit_loss(initial_balance, current_balance)

    portfolio_details = "\n".join([f"{stock_symbol}: {quantity}" for stock_symbol, quantity in portfolio.items()])

    if not portfolio_details:
        portfolio_details = "You don't own any stocks yet."

    account_message = (
        f"**Account Information**\n\n"
        f"**Balance:** ${current_balance:.2f}\n"
        f"**Portfolio:**\n{portfolio_details}\n\n"
        f"**Profit/Loss Percentage:** {profit_loss_percentage:.2f}%"
    )

    await message.reply(account_message)

# Handle the /market command to view current stock prices
@app.on_message(filters.command("market"))
async def market_info(_, message: Message):
    market_status = "**Current Stock Prices**\n\n"
    for stock_symbol, stock in stock_market.items():
        market_status += f"{stock.name} ({stock_symbol}): ${stock.price:.2f}\n"
    
    await message.reply(market_status)

# Handle unknown commands
@app.on_message(filters.command(["help", "settings", "info"]))
async def unknown_command(_, message: Message):
    await message.reply("Invalid command. Use /start to view the available commands.")

# Run the bot
app.run()
