import os
import asyncio
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN not set in environment variables!")

OWNER_ID = 123456789  # <-- replace with your numeric Telegram ID

DATA_FILE = "users.json"
ALERT_FILE = "alerts.json"

# ================= DATABASE =================
def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_alerts():
    try:
        with open(ALERT_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_alerts(data):
    with open(ALERT_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= API =================
def get_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum,solana,binancecoin",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
    r = requests.get(url, timeout=10)
    return r.json()

def get_news():
    url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
    r = requests.get(url, timeout=10)
    data = r.json()
    headlines = []
    for item in data["Data"][:5]:
        headlines.append(f"📰 {item['title']}")
    return "\n\n".join(headlines)

# ================= MENU =================
def main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
        [InlineKeyboardButton("💼 Portfolio", callback_data="portfolio")],
        [InlineKeyboardButton("🚨 Alerts", callback_data="alerts")],
        [InlineKeyboardButton("📡 Signals", callback_data="signals")],
        [InlineKeyboardButton("📰 News", callback_data="news")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    user_id = str(update.effective_user.id)
    if user_id not in users:
        users[user_id] = {"portfolio": {}}
        save_users(users)
    await update.message.reply_text(
        "🚀 GLOBAL CRYPTO HUB\n\nSelect option:",
        reply_markup=main_menu()
    )

# ================= BUTTON HANDLER =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    users = load_users()
    user_id = str(query.from_user.id)

    if query.data == "dashboard":
        prices = get_prices()
        text = "📊 LIVE MARKET\n\n"
        for coin, data in prices.items():
            text += f"{coin.upper()} - ${data['usd']} ({data['usd_24h_change']:.2f}%)\n"
        await query.edit_message_text(text, reply_markup=main_menu())

    elif query.data == "portfolio":
        portfolio = users[user_id]["portfolio"]
        if not portfolio:
            text = "💼 Portfolio empty."
        else:
            prices = get_prices()
            total = 0
            text = "💼 YOUR PORTFOLIO\n\n"
            for coin, amount in portfolio.items():
                value = amount * prices[coin]["usd"]
                total += value
                text += f"{coin.upper()}: {amount} = ${value:.2f}\n"
            text += f"\nTotal Value: ${total:.2f}"
        await query.edit_message_text(text, reply_markup=main_menu())

    elif query.data == "alerts":
        text = "🚨 Global alerts active.\nYou will be notified automatically."
        await query.edit_message_text(text, reply_markup=main_menu())

    elif query.data == "signals":
        prices = get_prices()
        text = "📡 SIGNALS\n\n"
        for coin, data in prices.items():
            change = data["usd_24h_change"]
            if change > 3:
                signal = "BUY"
            elif change < -3:
                signal = "SELL"
            else:
                signal = "HOLD"
            text += f"{coin.upper()}: {signal}\n"
        await query.edit_message_text(text, reply_markup=main_menu())

    elif query.data == "news":
        headlines = get_news()
        await query.edit_message_text(f"📰 LATEST NEWS\n\n{headlines}", reply_markup=main_menu())

# ================= GLOBAL ALERT CHECKER =================
async def check_alerts(app):
    while True:
        alerts = load_alerts()
        prices = get_prices()
        users = load_users()
        for alert in alerts[:]:
            coin = alert["coin"]
            target = alert["target"]
            current = prices[coin]["usd"]
            if current >= target:
                for user_id in users:
                    try:
                        await app.bot.send_message(
                            chat_id=int(user_id),
                            text=f"🚨 ALERT: {coin.upper()} reached ${current}"
                        )
                    except:
                        pass
                alerts.remove(alert)
        save_alerts(alerts)
        await asyncio.sleep(60)

# ================= ADMIN BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    users = load_users()
    message = " ".join(context.args)
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"📢 BROADCAST:\n{message}"
            )
        except:
            pass

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button_handler))
    asyncio.create_task(check_alerts(app))
    print("Bot running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
