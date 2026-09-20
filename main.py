import os, datetime, discord, re, asyncio, json, traceback, time, aiohttp, logging
import random
import math
import signal
import sys
import shutil
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput, Select
from discord import app_commands
from flask import Flask, jsonify
from threading import Thread
from typing import Dict, List, Optional, Tuple
from datetime import datetime as dt
from datetime import timedelta

# ============ STARTUP DEBUG ============
print("=" * 60)
print("Starting 13bux Bot...")
print("=" * 60)

print(f"🐍 Python version: {sys.version}")

token = os.getenv("TOKEN")
if not token:
    print("❌ ERROR: TOKEN not found in environment variables!")
    print("Please set TOKEN environment variable in Render dashboard")
    sys.exit(1)
else:
    print(f"✅ TOKEN found (length: {len(token)})")

# ============ DATA DIRECTORY SETUP ============
DATA_DIR = os.getenv("DATA_DIR", "./data")

try:
    os.makedirs(DATA_DIR, exist_ok=True)
    test_file = os.path.join(DATA_DIR, ".write_test")
    with open(test_file, 'w') as f:
        f.write("test")
    os.remove(test_file)
    print(f"✅ DATA_DIR: {DATA_DIR} (writable)")
except Exception as e:
    print(f"❌ Cannot use DATA_DIR={DATA_DIR}: {e}")
    DATA_DIR = "."
    os.makedirs(DATA_DIR, exist_ok=True)
    test_file = os.path.join(DATA_DIR, ".write_test")
    with open(test_file, 'w') as f:
        f.write("test")
    os.remove(test_file)
    print(f"✅ Now using DATA_DIR: {DATA_DIR}")

print(f"📁 Data files will be stored in: {DATA_DIR}")

app = Flask(__name__)
start_time = time.time()
bot_status = {"online": False, "guilds": 0, "users": 0}

@app.route('/')
def home():
    uptime = time.time() - start_time
    return f"Bot is alive! Uptime: {int(uptime/3600)}h {int((uptime%3600)/60)}m"

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "bot_online": bot_status['online']}), 200

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)), debug=False, use_reloader=False), daemon=True).start()
    print(f"✅ Web server started")

logging.getLogger('werkzeug').setLevel(logging.ERROR)

try:
    import pytz
    def get_thailand_time(): return dt.now(pytz.timezone('Asia/Bangkok'))
except:
    def get_thailand_time(): return dt.utcnow() + datetime.timedelta(hours=7)

intents = discord.Intents.all()
intents.message_content = True
intents.members = True

# ============ CONSTANTS ============
SUSHI_HEART_EMOJI = "💖"
PINK_COLOR = 0xFF69B4

# Global variables
gamepass_rate = 5
gamepass_rate_high = 5
gamepass_threshold = 676767
shop_open = True
gamepass_stock = 20000

# Daily robux sales tracking
daily_robux_sold = 0
daily_sales_date = get_thailand_time().strftime("%Y%m%d")

# Channel IDs
MAIN_CHANNEL_ID = 1535664744256634921
STATUS_CHANNEL_ID = 1535992997517467738
RATE_CHANNEL_ID = 1535629577152495668
SALES_LOG_CHANNEL_ID = 1551146468251926558
CREDIT_CHANNEL_ID = 1535664959785144421
DELIVERED_CATEGORY_ID = 1551147734050938930
ARCHIVED_CATEGORY_ID = 1551147734050938930
BUYER_ROLE_ID = 1475346221605588992
WELCOME_CHANNEL_ID = 1475344769679888455
SUSHI_GAMEPASS_CATEGORY_ID = 1475342278976606228
ANONYMOUS_USER_ROLE_ID = 1486352633290821673
ADMIN_ROLE_ID = 1535667589433397348
NOTES_BUTTON_CHANNEL_ID = 1485277532088696995
NOTES_LOG_CHANNEL_ID = 1504349990460461066

# Category IDs for each button type
GAMEPASS_TICKET_CATEGORY_ID = 1551167566389452840
TOPUP_TICKET_CATEGORY_ID = 1551167716587606127
ISSUE_TICKET_CATEGORY_ID = 1551168063171199056

# Thumbnail URL
THUMBNAIL_URL = "https://media.discordapp.net/attachments/1460628263092359199/1535925883989135381/cachedMedia.png?ex=6ab04032&is=6aaeeeb2&hm=739c2b4d506db1adca5c6188257f08e376e992237abb8ca888e69faadc3d4678&=&format=webp&quality=lossless&width=1299&height=1299"

# Big image URL
MAIN_IMAGE_URL = "https://media.discordapp.net/attachments/1486683482183958568/1551167778726350848/content.png?ex=6ab0fd11&is=6aafab91&hm=1cd17fb232371815ed3ef88d4510238881096e94d231f7ef2ecca392fd8f5852&=&format=webp&quality=lossless&width=1745&height=1163"

# Topup image URL
TOPUP_IMAGE_URL = "https://media.discordapp.net/attachments/1535629996910182410/1542419322209697832/58082bd2-71f2-4132-a16d-64154fc001e5.png?ex=6ab0cd6f&is=6aaf7bef&hm=f22fb4eb2d2d2ed351bb83a23d1393c4891dc1491c8453e990e72cb2e0f15e5c&=&format=webp&quality=lossless&width=1623&height=1299"

# Topup package prices (robux -> baht) - base unit prices
TOPUP_PRICES = {
    80: 35,
    160: 66,
    240: 99,
    500: 160,
    1000: 300,
    1500: 460,
    2000: 600,
    2500: 750,
    3500: 1050,
    5000: 1490,
    10000: 2900,
    15000: 4350,
    22500: 5789,
}

# File paths
user_data_file = os.path.join(DATA_DIR, "user_data.json")
ticket_transcripts_file = os.path.join(DATA_DIR, "ticket_transcripts.json")
ticket_counter_file = os.path.join(DATA_DIR, "ticket_counter.json")
ticket_robux_data_file = os.path.join(DATA_DIR, "ticket_robux_data.json")
ticket_customer_data_file = os.path.join(DATA_DIR, "ticket_customer_data.json")
stock_file = os.path.join(DATA_DIR, "stock_values.json")
ticket_buyer_data_file = os.path.join(DATA_DIR, "ticket_buyer_data.json")
user_levels_file = os.path.join(DATA_DIR, "user_levels.json")
daily_sales_file = os.path.join(DATA_DIR, "daily_sales.json")
user_robux_balance_file = os.path.join(DATA_DIR, "user_robux_balance.json")
user_notes_file = os.path.join(DATA_DIR, "user_notes.json")
ticket_topup_price_file = os.path.join(DATA_DIR, "ticket_topup_price.json")

print(f"📄 Data files will be saved to:")
print(f"   - {user_levels_file}")
print(f"   - {stock_file}")
print(f"   - {ticket_counter_file}")
print(f"   - {daily_sales_file}")
print(f"   - {user_robux_balance_file}")
print(f"   - {user_notes_file}")
print(f"   - {ticket_topup_price_file}")

# In-memory data structures
user_data = {}
ticket_transcripts = {}
ticket_robux_data = {}
ticket_customer_data = {}
ticket_buyer_data = {}
user_levels = {}
user_notes = {}
ticket_activity = {}
ticket_removal_tasks = {}
ticket_anonymous_mode = {}
ticket_counter = {"counter": 1, "date": get_thailand_time().strftime("%d%m%y")}
ticket_archived_timers = {}
user_robux_balance = {}
daily_sales = {"robux_sold": 0, "date": get_thailand_time().strftime("%Y%m%d")}
# Store accumulated price per ticket for topup (since robux can be combined from multiple button clicks)
ticket_topup_price = {}

sp_added_tracker = {}

# ============ JSON HELPER FUNCTIONS ============
def save_json(filepath, data):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        temp_filepath = filepath + ".tmp"
        with open(temp_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_filepath, filepath)
        return True
    except Exception as e:
        print(f"❌ Error saving {filepath}: {e}")
        return False

def load_json(filepath, default=None):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default if default is not None else {}
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
        return default if default is not None else {}

# ============ STOCK FUNCTIONS ============
def save_stock_values():
    try:
        data = {
            "gamepass_stock": gamepass_stock,
            "gamepass_rate": gamepass_rate,
            "gamepass_rate_high": gamepass_rate_high,
            "gamepass_threshold": gamepass_threshold,
            "shop_open": shop_open,
            "last_updated": get_thailand_time().isoformat()
        }
        save_json(stock_file, data)
        print(f"✅ Stock values saved: stock={gamepass_stock}, rate={gamepass_rate}, shop_open={shop_open}")
        return True
    except Exception as e:
        print(f"❌ Error saving stock: {e}")
        return False

def load_stock_values():
    global gamepass_stock, gamepass_rate, gamepass_rate_high, gamepass_threshold, shop_open
    try:
        if os.path.exists(stock_file):
            data = load_json(stock_file, {})
            gamepass_stock = data.get("gamepass_stock", 20000)
            gamepass_rate = data.get("gamepass_rate", 5)
            gamepass_rate_high = data.get("gamepass_rate_high", 5)
            gamepass_threshold = data.get("gamepass_threshold", 676767)
            shop_open = data.get("shop_open", True)
            print(f"✅ Stock values loaded: stock={gamepass_stock}, rate={gamepass_rate}, shop_open={shop_open}")
        else:
            save_stock_values()
    except Exception as e:
        print(f"❌ Error loading stock: {e}")

# ============ DAILY SALES FUNCTIONS ============
def save_daily_sales():
    try:
        data = {
            "robux_sold": daily_robux_sold,
            "date": daily_sales_date,
            "last_updated": get_thailand_time().isoformat()
        }
        save_json(daily_sales_file, data)
        return True
    except Exception as e:
        print(f"❌ Error saving daily sales: {e}")
        return False

def load_daily_sales():
    global daily_robux_sold, daily_sales_date
    try:
        if os.path.exists(daily_sales_file):
            data = load_json(daily_sales_file, {})
            saved_date = data.get("date", "")
            current_date = get_thailand_time().strftime("%Y%m%d")
            
            if saved_date == current_date:
                daily_robux_sold = data.get("robux_sold", 0)
                daily_sales_date = saved_date
                print(f"✅ Daily sales loaded: {daily_robux_sold} robux")
            else:
                daily_robux_sold = 0
                daily_sales_date = current_date
                save_daily_sales()
                print(f"✅ New day - daily sales reset to 0")
        else:
            daily_robux_sold = 0
            daily_sales_date = get_thailand_time().strftime("%Y%m%d")
            save_daily_sales()
    except Exception as e:
        print(f"❌ Error loading daily sales: {e}")

async def add_daily_robux(amount):
    global daily_robux_sold, daily_sales_date
    try:
        current_date = get_thailand_time().strftime("%Y%m%d")
        if daily_sales_date != current_date:
            daily_robux_sold = 0
            daily_sales_date = current_date
        
        daily_robux_sold += amount
        save_daily_sales()
        print(f"✅ Daily robux: {daily_robux_sold}")
    except Exception as e:
        print(f"❌ Error adding daily robux: {e}")

def reset_daily_robux():
    global daily_robux_sold, daily_sales_date
    daily_robux_sold = 0
    daily_sales_date = get_thailand_time().strftime("%Y%m%d")
    save_daily_sales()
    print(f"✅ Daily robux reset to 0")

# ============ SP FUNCTIONS ============
async def add_sp(user_id, robux_amount, ticket_id=None):
    try:
        user_id_str = str(user_id)
        
        if ticket_id and ticket_id in sp_added_tracker:
            print(f"⚠️ SP already added for ticket {ticket_id}")
            return False
        
        if user_id_str not in user_levels:
            user_levels[user_id_str] = {"sp": 0, "total_robux": 0}
        
        sp_amount = robux_amount
        user_levels[user_id_str]["sp"] += sp_amount
        user_levels[user_id_str]["total_robux"] += robux_amount
        
        if ticket_id:
            sp_added_tracker[ticket_id] = True
        
        save_json(user_levels_file, user_levels)
        print(f"✅ Added {sp_amount} SP to user {user_id} (total: {user_levels[user_id_str]['sp']})")
        return True
    except Exception as e:
        print(f"❌ Error adding SP: {e}")
        return False

def backup_user_levels():
    try:
        if os.path.exists(user_levels_file):
            backup_dir = os.path.join(DATA_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = get_thailand_time().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"user_levels_backup_{timestamp}.json")
            shutil.copy2(user_levels_file, backup_file)
            print(f"✅ Backup created: {backup_file}")
            
            backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("user_levels_backup_")])
            while len(backups) > 10:
                os.remove(os.path.join(backup_dir, backups[0]))
                backups.pop(0)
        return True
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return False

# ============ LOAD/SAVE ALL DATA ============
def load_all_data():
    global user_data, ticket_transcripts, ticket_robux_data, ticket_customer_data
    global ticket_buyer_data, user_levels, user_notes, ticket_counter
    global ticket_topup_price
    
    try:
        user_data = load_json(user_data_file, {})
        ticket_transcripts = load_json(ticket_transcripts_file, {})
        ticket_robux_data = load_json(ticket_robux_data_file, {})
        ticket_customer_data = load_json(ticket_customer_data_file, {})
        ticket_buyer_data = load_json(ticket_buyer_data_file, {})
        user_levels = load_json(user_levels_file, {})
        user_notes = load_json(user_notes_file, {})
        ticket_topup_price = load_json(ticket_topup_price_file, {})
        
        ticket_counter = load_json(ticket_counter_file, {"counter": 1, "date": get_thailand_time().strftime("%d%m%y")})
        current_date = get_thailand_time().strftime("%d%m%y")
        if ticket_counter.get("date") != current_date:
            ticket_counter = {"counter": 1, "date": current_date}
        
        load_stock_values()
        load_daily_sales()
        load_robux_balance()
        load_notes()
        
        print(f"✅ All data loaded successfully")
        print(f"   - Users: {len(user_levels)}")
        print(f"   - Tickets: {len(ticket_transcripts)}")
        print(f"   - Notes: {len(user_notes)}")
        return True
    except Exception as e:
        print(f"❌ Error loading all data: {e}")
        traceback.print_exc()
        return False

async def save_all_data():
    try:
        save_json(user_data_file, user_data)
        save_json(ticket_transcripts_file, ticket_transcripts)
        save_json(ticket_robux_data_file, ticket_robux_data)
        save_json(ticket_customer_data_file, ticket_customer_data)
        save_json(ticket_buyer_data_file, ticket_buyer_data)
        save_json(user_levels_file, user_levels)
        save_json(user_notes_file, user_notes)
        save_json(ticket_counter_file, ticket_counter)
        save_json(ticket_topup_price_file, ticket_topup_price)
        save_stock_values()
        save_daily_sales()
        save_robux_balance()
        return True
    except Exception as e:
        print(f"❌ Error saving all data: {e}")
        return False

def save_all_data_sync():
    try:
        save_json(user_data_file, user_data)
        save_json(ticket_transcripts_file, ticket_transcripts)
        save_json(ticket_robux_data_file, ticket_robux_data)
        save_json(ticket_customer_data_file, ticket_customer_data)
        save_json(ticket_buyer_data_file, ticket_buyer_data)
        save_json(user_levels_file, user_levels)
        save_json(user_notes_file, user_notes)
        save_json(ticket_counter_file, ticket_counter)
        save_json(ticket_topup_price_file, ticket_topup_price)
        save_stock_values()
        save_daily_sales()
        save_robux_balance()
        print("✅ All data saved (sync)")
        return True
    except Exception as e:
        print(f"❌ Error saving all data (sync): {e}")
        return False

# ============ ROBUX BALANCE FUNCTIONS ============
def load_robux_balance():
    global user_robux_balance
    try:
        if os.path.exists(user_robux_balance_file):
            with open(user_robux_balance_file, 'r', encoding='utf-8') as f:
                user_robux_balance = json.load(f)
                for key, value in user_robux_balance.items():
                    if isinstance(value, str):
                        user_robux_balance[key] = float(value)
                print(f"✅ Loaded robux balance for {len(user_robux_balance)} users")
        else:
            user_robux_balance = {}
            save_robux_balance()
    except Exception as e:
        print(f"❌ Error loading robux balance: {e}")
        user_robux_balance = {}

def save_robux_balance():
    try:
        with open(user_robux_balance_file, 'w', encoding='utf-8') as f:
            json.dump(user_robux_balance, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving robux balance: {e}")
        return False

def get_user_robux_balance(user_id):
    user_id_str = str(user_id)
    return user_robux_balance.get(user_id_str, 0)

def set_user_robux_balance(user_id, amount):
    user_id_str = str(user_id)
    user_robux_balance[user_id_str] = amount
    save_robux_balance()
    return amount

def deduct_user_robux_balance(user_id, amount):
    user_id_str = str(user_id)
    current = user_robux_balance.get(user_id_str, 0)
    if current < amount:
        return None
    new_balance = current - amount
    user_robux_balance[user_id_str] = new_balance
    save_robux_balance()
    return new_balance

def add_user_robux_balance(user_id, amount):
    user_id_str = str(user_id)
    current = user_robux_balance.get(user_id_str, 0)
    new_balance = current + amount
    user_robux_balance[user_id_str] = new_balance
    save_robux_balance()
    return new_balance

# ============ NOTES FUNCTIONS ============
def load_notes():
    global user_notes
    try:
        if os.path.exists(user_notes_file):
            with open(user_notes_file, 'r', encoding='utf-8') as f:
                user_notes = json.load(f)
                print(f"✅ Loaded notes for {len(user_notes)} users")
        else:
            user_notes = {}
            save_notes()
    except Exception as e:
        print(f"❌ Error loading notes: {e}")
        user_notes = {}

def save_notes():
    try:
        with open(user_notes_file, 'w', encoding='utf-8') as f:
            json.dump(user_notes, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving notes: {e}")
        return False

async def update_notes_channel():
    try:
        print("ℹ️ Notes channel update called (no implementation)")
    except Exception as e:
        print(f"❌ Error updating notes channel: {e}")

# ============ HELPER FUNCTIONS ============
def get_gamepass_rate(robux_amount):
    return gamepass_rate

def calculate_wallet_price(price):
    return round_price(price * 1.05)

def format_rate_for_channel(rate):
    """
    Format rate for channel name.
    - Integer rate (5)     -> "5"
    - Decimal rate (5.5)   -> "5จุด5"
    - Decimal rate (100.0) -> "100"
    - Decimal rate (5.25)  -> "5จุด25"
    """
    try:
        rate_float = float(rate)
    except (ValueError, TypeError):
        return str(rate)
    
    # If it's a whole number, just show the integer
    if rate_float.is_integer():
        return str(int(rate_float))
    
    # Otherwise, replace the decimal point with "จุด"
    rate_str = f"{rate_float:g}"  # removes trailing zeros
    return rate_str.replace(".", "จุด")

def calculate_topup_price_from_robux(total_robux):
    """
    Calculate the total baht price for a given robux amount using TOPUP_PRICES.
    
    Strategy:
    1. If exact match in TOPUP_PRICES, return that price.
    2. Otherwise, greedily use the largest package sizes that fit, then
       fall back to per-unit pricing based on the smallest available package.
    
    This makes 160R x 2 = 320R  -> 66 x 2 = 132 baht
    and 500R + 500R = 1000R     -> 160 x 2 = 320 baht
    (which may differ from the bundle price of 1000R = 300 baht, but that's
     fine — the customer picked individual buttons.)
    """
    if total_robux <= 0:
        return 0
    
    # Exact match
    if total_robux in TOPUP_PRICES:
        return TOPUP_PRICES[total_robux]
    
    # Greedy: use largest denominations that fit
    remaining = total_robux
    total_price = 0
    sorted_amounts = sorted(TOPUP_PRICES.keys(), reverse=True)
    
    for amount in sorted_amounts:
        if remaining >= amount:
            count = remaining // amount
            total_price += count * TOPUP_PRICES[amount]
            remaining -= count * amount
    
    if remaining > 0:
        # Fallback: use base unit price derived from the smallest package
        smallest_amount = min(TOPUP_PRICES.keys())
        smallest_price = TOPUP_PRICES[smallest_amount]
        unit_price = smallest_price / smallest_amount
        total_price += remaining * unit_price
    
    return round_price(total_price)

class RateLimiter:
    def __init__(self, max_calls=1, period=1.0):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        async with self._lock:
            now = time.time()
            self.calls = [c for c in self.calls if now - c < self.period]
            if len(self.calls) >= self.max_calls:
                await asyncio.sleep(self.period - (now - self.calls[0]))
                return await self.acquire()
            self.calls.append(now)
            return True

def format_number(num: int) -> str:
    return f"{num:,}"

def round_price(value):
    return int(value + 0.5001)

def is_user_always_anonymous(user):
    if not user or not user.guild:
        return False
    anonymous_role = user.guild.get_role(ANONYMOUS_USER_ROLE_ID)
    return anonymous_role and anonymous_role in user.roles

def get_next_ticket_number():
    global ticket_counter
    current_date = get_thailand_time().strftime("%d%m%y")
    if ticket_counter["date"] != current_date:
        ticket_counter = {"counter": 1, "date": current_date}
    else:
        ticket_counter["counter"] += 1
    save_json(ticket_counter_file, ticket_counter)
    return ticket_counter["counter"]

def admin_only():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        admin_role = ctx.guild.get_role(ADMIN_ROLE_ID)
        if admin_role and admin_role in ctx.author.roles:
            return True
        await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะผู้ดูแลระบบเท่านั้น", delete_after=5)
        return False
    return commands.check(predicate)

# ============ EXPRESSION EVALUATION ============
def evaluate_expression(expr: str) -> float:
    try:
        expr = expr.replace(",", "")
        expr = expr.replace(" ", "")
        expr = expr.lower().replace("x", "*")
        expr = expr.replace("÷", "/")
        
        allowed_chars = set("0123456789+-*/().")
        if not all(c in allowed_chars for c in expr):
            raise ValueError("Expression contains invalid characters")
        
        result = eval(expr)
        
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        
        if result < 0:
            raise ValueError("Result cannot be negative")
        
        return result
    except Exception as e:
        raise ValueError(f"Invalid expression: {str(e)}")


# ============ ROBUX TOPUP PACKAGE VIEWS ============
class TopupMainMenuView(View):
    """Main menu: 3 package tiers"""
    def __init__(self):
        super().__init__(timeout=None)
        
        starter_btn = Button(label="แพ็กเริ่มต้น", style=discord.ButtonStyle.success, emoji="🌱")
        popular_btn = Button(label="แพ็กยอดนิยม", style=discord.ButtonStyle.primary, emoji="⭐")
        big_btn = Button(label="แพ็กใหญ่", style=discord.ButtonStyle.danger, emoji="💎")
        
        async def starter_cb(i):
            embed = discord.Embed(
                title="🌱 แพ็กเริ่มต้น",
                description="กรุณาเลือกจำนวนโรบัคที่ต้องการ",
                color=PINK_COLOR
            )
            embed.add_field(name="📦 แพ็กที่มีให้เลือก", value="80R • 160R • 240R • 500R", inline=False)
            embed.set_footer(text="13bux • แพ็กเริ่มต้น")
            embed.set_thumbnail(url=THUMBNAIL_URL)
            await i.response.edit_message(embed=embed, view=TopupStarterView(self))
        
        async def popular_cb(i):
            embed = discord.Embed(
                title="⭐ แพ็กยอดนิยม",
                description="กรุณาเลือกจำนวนโรบัคที่ต้องการ",
                color=PINK_COLOR
            )
            embed.add_field(name="📦 แพ็กที่มีให้เลือก", value="1000R • 1500R • 2000R • 2500R", inline=False)
            embed.set_footer(text="13bux • แพ็กยอดนิยม")
            embed.set_thumbnail(url=THUMBNAIL_URL)
            await i.response.edit_message(embed=embed, view=TopupPopularView(self))
        
        async def big_cb(i):
            embed = discord.Embed(
                title="💎 แพ็กใหญ่",
                description="กรุณาเลือกจำนวนโรบัคที่ต้องการ",
                color=PINK_COLOR
            )
            embed.add_field(name="📦 แพ็กที่มีให้เลือก", value="3500R • 5000R • 10000R • 15000R • 22500R", inline=False)
            embed.set_footer(text="13bux • แพ็กใหญ่")
            embed.set_thumbnail(url=THUMBNAIL_URL)
            await i.response.edit_message(embed=embed, view=TopupBigView(self))
        
        starter_btn.callback = starter_cb
        popular_btn.callback = popular_cb
        big_btn.callback = big_cb
        
        self.add_item(starter_btn)
        self.add_item(popular_btn)
        self.add_item(big_btn)


def _build_topup_main_menu_embed():
    """Helper to build the main menu embed (for back button)"""
    embed = discord.Embed(
        title="💎 บริการเติมโรแท้ (Robux แท้)",
        description="กรุณาเลือกแพ็กที่ต้องการด้านล่าง",
        color=PINK_COLOR
    )
    embed.add_field(name="🌱 แพ็กเริ่มต้น", value="80R • 160R • 240R • 500R", inline=False)
    embed.add_field(name="⭐ แพ็กยอดนิยม", value="1000R • 1500R • 2000R • 2500R", inline=False)
    embed.add_field(name="💎 แพ็กใหญ่", value="3500R • 5000R • 10000R • 15000R • 22500R", inline=False)
    embed.set_footer(text="13bux • เติมโรแท้")
    embed.set_thumbnail(url=THUMBNAIL_URL)
    return embed


class TopupStarterView(View):
    """80R, 160R, 240R, 500R + ย้อนกลับ"""
    def __init__(self, parent_view=None):
        super().__init__(timeout=None)
        self.parent_view = parent_view
        
        for amount in [80, 160, 240, 500]:
            price = TOPUP_PRICES.get(amount, 0)
            btn = Button(label=f"{amount}R • {price}฿", style=discord.ButtonStyle.success)
            btn.callback = self._make_amount_callback(amount)
            self.add_item(btn)
        
        back_btn = Button(label="ย้อนกลับ", style=discord.ButtonStyle.secondary, emoji="◀️")
        back_btn.callback = self._back_callback
        self.add_item(back_btn)
    
    def _make_amount_callback(self, amount):
        async def cb(i):
            await _handle_topup_amount(i, amount)
        return cb
    
    async def _back_callback(self, i):
        await i.response.edit_message(embed=_build_topup_main_menu_embed(), view=TopupMainMenuView())


class TopupPopularView(View):
    """1000R, 1500R, 2000R, 2500R + ย้อนกลับ"""
    def __init__(self, parent_view=None):
        super().__init__(timeout=None)
        self.parent_view = parent_view
        
        for amount in [1000, 1500, 2000, 2500]:
            price = TOPUP_PRICES.get(amount, 0)
            btn = Button(label=f"{amount}R • {price}฿", style=discord.ButtonStyle.primary)
            btn.callback = self._make_amount_callback(amount)
            self.add_item(btn)
        
        back_btn = Button(label="ย้อนกลับ", style=discord.ButtonStyle.secondary, emoji="◀️")
        back_btn.callback = self._back_callback
        self.add_item(back_btn)
    
    def _make_amount_callback(self, amount):
        async def cb(i):
            await _handle_topup_amount(i, amount)
        return cb
    
    async def _back_callback(self, i):
        await i.response.edit_message(embed=_build_topup_main_menu_embed(), view=TopupMainMenuView())


class TopupBigView(View):
    """3500R, 5000R, 10000R, 15000R, 22500R + ย้อนกลับ"""
    def __init__(self, parent_view=None):
        super().__init__(timeout=None)
        self.parent_view = parent_view
        
        for amount in [3500, 5000, 10000, 15000, 22500]:
            price = TOPUP_PRICES.get(amount, 0)
            btn = Button(label=f"{amount}R • {price}฿", style=discord.ButtonStyle.danger)
            btn.callback = self._make_amount_callback(amount)
            self.add_item(btn)
        
        back_btn = Button(label="ย้อนกลับ", style=discord.ButtonStyle.secondary, emoji="◀️")
        back_btn.callback = self._back_callback
        self.add_item(back_btn)
    
    def _make_amount_callback(self, amount):
        async def cb(i):
            await _handle_topup_amount(i, amount)
        return cb
    
    async def _back_callback(self, i):
        await i.response.edit_message(embed=_build_topup_main_menu_embed(), view=TopupMainMenuView())


async def _handle_topup_amount(interaction, robux_amount):
    """Handle when customer clicks a specific robux amount button.
    
    If the same button is clicked multiple times, accumulate the robux and
    the baht price so the ticket tracks the customer's full order.
    """
    admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
    admin_mention = admin_role.mention if admin_role else f"<@&{ADMIN_ROLE_ID}>"
    
    ticket_id = str(interaction.channel.id)
    
    # Accumulate robux for this ticket
    existing_robux = 0
    try:
        existing_robux = int(float(ticket_robux_data.get(ticket_id, 0)))
    except (ValueError, TypeError):
        existing_robux = 0
    new_total_robux = existing_robux + robux_amount
    ticket_robux_data[ticket_id] = str(new_total_robux)
    save_json(ticket_robux_data_file, ticket_robux_data)
    
    # Accumulate price for this ticket
    unit_price = TOPUP_PRICES.get(robux_amount, robux_amount)
    existing_price = 0
    try:
        existing_price = int(float(ticket_topup_price.get(ticket_id, 0)))
    except (ValueError, TypeError):
        existing_price = 0
    new_total_price = existing_price + unit_price
    ticket_topup_price[ticket_id] = str(new_total_price)
    save_json(ticket_topup_price_file, ticket_topup_price)
    
    embed = discord.Embed(
        title="📦 รับออร์เดอร์เติมโรแท้",
        description=f"คุณเลือกแพ็ก **{format_number(robux_amount)} Robux**",
        color=PINK_COLOR
    )
    embed.add_field(name="👤 ผู้ซื้อ", value=interaction.user.mention, inline=False)
    embed.add_field(name="💎 จำนวนโรบัคที่เลือก", value=f"**{format_number(robux_amount)} R** (+{format_number(existing_robux)} R ก่อนหน้า)", inline=False)
    embed.add_field(name="💰 ราคาแพ็กนี้", value=f"**{format_number(unit_price)} บาท**", inline=False)
    embed.add_field(name="🧾 ยอดรวมในตั๋วนี้", value=f"**{format_number(new_total_robux)} R • {format_number(new_total_price)} บาท**", inline=False)
    embed.set_footer(text=f"13bux • {get_thailand_time().strftime('%d/%m/%y %H:%M')}")
    embed.set_thumbnail(url=THUMBNAIL_URL)
    
    await interaction.response.send_message(
        content=f"รับออร์เดอร์ค่ะ รอแอดมินตอบกลับนะคะ {admin_mention}",
        embed=embed
    )


# ============ ISSUE TICKET MODAL ============
class IssueReportModal(Modal, title="⚠️ แจ้งปัญหา"):
    issue_description = TextInput(
        label="อธิบายปัญหาที่พบ",
        placeholder="กรุณาอธิบายปัญหาที่พบ...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    async def on_submit(self, i):
        try:
            admin_role = i.guild.get_role(ADMIN_ROLE_ID)
            admin_mention = admin_role.mention if admin_role else f"<@&{ADMIN_ROLE_ID}>"
            
            embed = discord.Embed(
                title="⚠️ รายงานปัญหาใหม่",
                description=self.issue_description.value,
                color=PINK_COLOR
            )
            embed.add_field(name="👤 ผู้แจ้ง", value=i.user.mention, inline=False)
            embed.set_footer(text=f"แจ้งเมื่อ {get_thailand_time().strftime('%d/%m/%y %H:%M')}")
            
            await i.response.send_message(
                f"✅ รับเรื่องแล้วค่ะ รอแอดมินตอบกลับนะคะ {admin_mention}",
                embed=embed
            )
        except Exception as e:
            await i.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)


class CalculatorView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        gamepass_btn = Button(label="คำนวณเกมพาส", style=discord.ButtonStyle.primary, emoji="🎮")
        gpb_btn = Button(label="คำนวนเงินบาท (เกมพาส)", style=discord.ButtonStyle.secondary, emoji="💰")
        
        gamepass_btn.callback = self.gamepass_callback
        gpb_btn.callback = self.gpb_callback
        
        self.add_item(gamepass_btn)
        self.add_item(gpb_btn)
    
    async def gamepass_callback(self, interaction: discord.Interaction):
        modal = GamepassCalculatorModal()
        await interaction.response.send_modal(modal)
    
    async def gpb_callback(self, interaction: discord.Interaction):
        modal = GamepassBahtCalculatorModal()
        await interaction.response.send_modal(modal)

class GamepassCalculatorModal(Modal, title="🌸 คำนวณเกมพาส"):
    robux_amount = TextInput(
        label="จำนวนโรบัค",
        placeholder="พิมพ์ตัวเลขเช่น 500, 100+200, 1000x2",
        required=True,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            robux = evaluate_expression(self.robux_amount.value)
            robux = int(robux)
            
            if robux <= 0:
                await interaction.response.send_message("❌ กรุณากรอกจำนวนที่มากกว่า 0", ephemeral=True)
                return
            
            rate = get_gamepass_rate(robux)
            price = robux / rate
            price_int = round_price(price)
            
            embed = discord.Embed(
                title=f"🎮 Gamepass {format_number(robux)} Robux = {format_number(price_int)} บาท (เรท {rate})",
                color=PINK_COLOR
            )
            embed.set_footer(text="13bux 🌸")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError as e:
            await interaction.response.send_message(f"❌ {str(e)}\nกรุณาพิมพ์ตัวเลขหรือสมการที่ถูกต้อง เช่น 1000 หรือ 500+500", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

class GamepassBahtCalculatorModal(Modal, title="🌸 คำนวณเงินบาท (เกมพาส)"):
    baht_amount = TextInput(
        label="จำนวนเงิน (บาท)",
        placeholder="พิมพ์ตัวเลขเช่น 500, 100+200, 1000x2",
        required=True,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            baht = evaluate_expression(self.baht_amount.value)
            baht = float(baht)
            
            if baht <= 0:
                await interaction.response.send_message("❌ กรุณากรอกจำนวนที่มากกว่า 0", ephemeral=True)
                return
            
            robux_amount = int(baht * gamepass_rate)
            
            embed = discord.Embed(
                title=f"🎮 {format_number(int(baht))} บาท",
                color=PINK_COLOR
            )
            embed.add_field(name=f"เรท {gamepass_rate}", value=f"{format_number(robux_amount)} Robux", inline=True)
            embed.set_footer(text="13bux 🌸")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError as e:
            await interaction.response.send_message(f"❌ {str(e)}\nกรุณาพิมพ์ตัวเลขหรือสมการที่ถูกต้อง เช่น 500 หรือ 100+200", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)


# ============ EMBED SHOP VIEW ============
class EmbedShopView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.update_buttons()
    
    def update_buttons(self):
        self.clear_items()
        
        gamepass_disabled = (not shop_open) or (gamepass_stock <= 0)
        gamepass_style = discord.ButtonStyle.danger if gamepass_disabled else discord.ButtonStyle.success
        
        gamepass_btn = Button(
            label="กดเกมพาส",
            style=gamepass_style,
            emoji="🎮",
            disabled=gamepass_disabled
        )
        
        topup_btn = Button(
            label="เติมโรแท้",
            style=discord.ButtonStyle.success,
            emoji="💎",
            disabled=not shop_open
        )
        
        issue_btn = Button(
            label="แจ้งปัญหา",
            style=discord.ButtonStyle.secondary,
            emoji="⚠️"
        )
        
        async def gamepass_cb(i):
            if not shop_open:
                await i.response.send_message("❌ ร้านปิดชั่วคราว กรุณารอเปิดให้บริการ", ephemeral=True)
                return
            if gamepass_stock <= 0:
                await i.response.send_message("❌ เกมพาสสต็อกหมด กรุณารอเติมสต็อก", ephemeral=True)
                return
            await handle_open_gamepass_ticket(i)
        
        async def topup_cb(i):
            if not shop_open:
                await i.response.send_message("❌ ร้านปิดชั่วคราว กรุณารอเปิดให้บริการ", ephemeral=True)
                return
            await handle_open_topup_ticket(i)
        
        async def issue_cb(i):
            await handle_open_issue_ticket(i)
        
        gamepass_btn.callback = gamepass_cb
        topup_btn.callback = topup_cb
        issue_btn.callback = issue_cb
        
        self.add_item(gamepass_btn)
        self.add_item(topup_btn)
        self.add_item(issue_btn)


# ============ GAMEPASS TICKET HANDLER ============
async def handle_open_gamepass_ticket(interaction):
    """Open a gamepass ticket in category GAMEPASS_TICKET_CATEGORY_ID"""
    global gamepass_stock
    
    try:
        if gamepass_stock <= 0:
            await interaction.response.send_message("❌ โรบัคหมดชั่วคราว", ephemeral=True)
            return
        
        if not shop_open:
            await interaction.response.send_message("❌ ปิดชั่วคราว กรุณารอร้านเปิด", ephemeral=True)
            return
        
        existing = discord.utils.get(
            interaction.guild.text_channels, 
            name=f"ticket-{interaction.user.name}-{interaction.user.id}".lower()
        )
        
        if existing:
            view = View()
            view.add_item(discord.ui.Button(
                label="📩 ไปที่ตั๋ว", 
                url=f"https://discord.com/channels/{existing.guild.id}/{existing.id}", 
                style=discord.ButtonStyle.link
            ))
            await interaction.response.send_message(
                "📌 คุณมีตั๋วเปิดอยู่แล้ว กดปุ่มด้านล่างเพื่อไปที่ตั๋ว", 
                view=view, 
                ephemeral=True
            )
            return
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        category = discord.utils.get(interaction.guild.categories, id=GAMEPASS_TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("❌ ไม่พบหมวดหมู่สำหรับตั๋วเกมพาส", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}-{interaction.user.id}".lower(),
            overwrites=overwrites,
            category=category
        )
        
        ticket_activity[channel.id] = {
            'last_activity': get_thailand_time(), 
            'ty_used': False,
            'buyer_id': interaction.user.id
        }
        
        ticket_buyer_data[str(channel.id)] = {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "user_display": interaction.user.display_name,
            "created_at": get_thailand_time().isoformat()
        }
        save_json(ticket_buyer_data_file, ticket_buyer_data)
        
        if is_user_always_anonymous(interaction.user):
            ticket_anonymous_mode[str(channel.id)] = True
            ticket_customer_data[str(channel.id)] = "ไม่ระบุตัวตน"
        else:
            ticket_customer_data[str(channel.id)] = interaction.user.name
        
        save_json(ticket_customer_data_file, ticket_customer_data)
        
        async with bot.stock_lock:
            gamepass_stock -= 1
        
        save_stock_values()
        await update_main_channel()
        
        view = View()
        view.add_item(discord.ui.Button(
            label="📩 ไปที่ตั๋ว", 
            url=f"https://discord.com/channels/{channel.guild.id}/{channel.id}", 
            style=discord.ButtonStyle.link
        ))
        await interaction.followup.send("📩 เปิดตั๋วเรียบร้อย", view=view, ephemeral=True)
        
        # ===== Gamepass ticket embed: ผู้ซื้อ + rate =====
        embed = discord.Embed(
            title="🌸13bux🌸", 
            color=PINK_COLOR
        )
        embed.add_field(name="👤 ผู้ซื้อ", value=interaction.user.mention, inline=False)
        embed.add_field(name=f"💰 กดเกมพาสเรท ({gamepass_rate})", value="\u200b", inline=False)
        embed.set_footer(text="13bux")
        embed.set_thumbnail(url=THUMBNAIL_URL)
        
        await channel.send(embed=embed)
        print(f"✅ ส่ง embed ต้อนรับในตั๋ว {channel.name} เรียบร้อย")

        if admin_role:
            admin_mention = admin_role.mention
            await channel.send(content=f"{admin_role.mention} มีตั๋วใหม่!", delete_after=10)
        else:
            admin_mention = ""

        await channel.send(f"# สนใจซื้ออะไรแจ้งแอดมินได้เลยค่ะ {SUSHI_HEART_EMOJI} {admin_mention}")
        print(f"✅ ส่งข้อความต้อนรับในตั๋ว {channel.name}")
        
    except Exception as e:
        print(f"❌ Error opening gamepass ticket: {e}")
        traceback.print_exc()
        try:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)
        except:
            pass


# ============ TOPUP TICKET HANDLER ============
async def handle_open_topup_ticket(interaction):
    """Open a robux topup ticket in category TOPUP_TICKET_CATEGORY_ID"""
    try:
        if not shop_open:
            await interaction.response.send_message("❌ ปิดชั่วคราว กรุณารอร้านเปิด", ephemeral=True)
            return
        
        existing = discord.utils.get(
            interaction.guild.text_channels, 
            name=f"topup-{interaction.user.name}-{interaction.user.id}".lower()
        )
        
        if existing:
            view = View()
            view.add_item(discord.ui.Button(
                label="📩 ไปที่ตั๋ว", 
                url=f"https://discord.com/channels/{existing.guild.id}/{existing.id}", 
                style=discord.ButtonStyle.link
            ))
            await interaction.response.send_message(
                "📌 คุณมีตั๋วเติมโรแท้เปิดอยู่แล้ว กดปุ่มด้านล่างเพื่อไปที่ตั๋ว", 
                view=view, 
                ephemeral=True
            )
            return
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        category = discord.utils.get(interaction.guild.categories, id=TOPUP_TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("❌ ไม่พบหมวดหมู่สำหรับตั๋วเติมโรแท้", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        channel = await interaction.guild.create_text_channel(
            name=f"topup-{interaction.user.name}-{interaction.user.id}".lower(),
            overwrites=overwrites,
            category=category
        )
        
        ticket_activity[channel.id] = {
            'last_activity': get_thailand_time(), 
            'ty_used': False,
            'buyer_id': interaction.user.id
        }
        
        ticket_buyer_data[str(channel.id)] = {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "user_display": interaction.user.display_name,
            "created_at": get_thailand_time().isoformat()
        }
        save_json(ticket_buyer_data_file, ticket_buyer_data)
        
        if is_user_always_anonymous(interaction.user):
            ticket_anonymous_mode[str(channel.id)] = True
            ticket_customer_data[str(channel.id)] = "ไม่ระบุตัวตน"
        else:
            ticket_customer_data[str(channel.id)] = interaction.user.name
        
        save_json(ticket_customer_data_file, ticket_customer_data)
        
        view = View()
        view.add_item(discord.ui.Button(
            label="📩 ไปที่ตั๋ว", 
            url=f"https://discord.com/channels/{channel.guild.id}/{channel.id}", 
            style=discord.ButtonStyle.link
        ))
        await interaction.followup.send("📩 เปิดตั๋วเติมโรแท้เรียบร้อย", view=view, ephemeral=True)
        
        # ===== First embed: only ผู้ซื้อ + image =====
        image_embed = discord.Embed(
            title="💎 บริการเติมโรแท้ (Robux แท้)",
            description="ยินดีต้อนรับ! กรุณาเลือกแพ็กที่ต้องการด้านล่างนี้",
            color=PINK_COLOR
        )
        image_embed.add_field(name="👤 ผู้ซื้อ", value=interaction.user.mention, inline=False)
        image_embed.set_image(url=TOPUP_IMAGE_URL)
        image_embed.set_footer(text="13bux • เติมโรแท้")
        
        await channel.send(embed=image_embed)
        print(f"✅ ส่งรูปภาพเติมโรแท้ในตั๋ว {channel.name}")
        
        # ===== Second: send the package selection embed with buttons =====
        menu_embed = discord.Embed(
            title="📦 เลือกแพ็กที่ต้องการ",
            description="กรุณาเลือกแพ็กที่คุณต้องการด้านล่าง",
            color=PINK_COLOR
        )
        menu_embed.add_field(
            name="🌱 แพ็กเริ่มต้น", 
            value="80R • 160R • 240R • 500R", 
            inline=False
        )
        menu_embed.add_field(
            name="⭐ แพ็กยอดนิยม", 
            value="1000R • 1500R • 2000R • 2500R", 
            inline=False
        )
        menu_embed.add_field(
            name="💎 แพ็กใหญ่", 
            value="3500R • 5000R • 10000R • 15000R • 22500R", 
            inline=False
        )
        menu_embed.set_footer(text="13bux • เลือกแพ็กเพื่อดูรายละเอียด")
        menu_embed.set_thumbnail(url=THUMBNAIL_URL)
        
        await channel.send(embed=menu_embed, view=TopupMainMenuView())
        print(f"✅ ส่งเมนูแพ็กเติมโรแท้ในตั๋ว {channel.name}")

        if admin_role:
            await channel.send(content=f"{admin_role.mention} มีตั๋วเติมโรแท้ใหม่!", delete_after=10)
        
        await channel.send(f"# เลือกแพ็กด้านบนได้เลยค่ะ {SUSHI_HEART_EMOJI}")
        
    except Exception as e:
        print(f"❌ Error opening topup ticket: {e}")
        traceback.print_exc()
        try:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)
        except:
            pass


# ============ ISSUE TICKET HANDLER ============
async def handle_open_issue_ticket(interaction):
    """Open an issue report ticket in category ISSUE_TICKET_CATEGORY_ID"""
    try:
        existing = discord.utils.get(
            interaction.guild.text_channels, 
            name=f"issue-{interaction.user.name}-{interaction.user.id}".lower()
        )
        
        if existing:
            view = View()
            view.add_item(discord.ui.Button(
                label="📩 ไปที่ตั๋ว", 
                url=f"https://discord.com/channels/{existing.guild.id}/{existing.id}", 
                style=discord.ButtonStyle.link
            ))
            await interaction.response.send_message(
                "📌 คุณมีตั๋วแจ้งปัญหาเปิดอยู่แล้ว กดปุ่มด้านล่างเพื่อไปที่ตั๋ว", 
                view=view, 
                ephemeral=True
            )
            return
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        category = discord.utils.get(interaction.guild.categories, id=ISSUE_TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("❌ ไม่พบหมวดหมู่สำหรับตั๋วแจ้งปัญหา", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        channel = await interaction.guild.create_text_channel(
            name=f"issue-{interaction.user.name}-{interaction.user.id}".lower(),
            overwrites=overwrites,
            category=category
        )
        
        ticket_activity[channel.id] = {
            'last_activity': get_thailand_time(), 
            'ty_used': False,
            'buyer_id': interaction.user.id
        }
        
        ticket_buyer_data[str(channel.id)] = {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "user_display": interaction.user.display_name,
            "created_at": get_thailand_time().isoformat()
        }
        save_json(ticket_buyer_data_file, ticket_buyer_data)
        
        if is_user_always_anonymous(interaction.user):
            ticket_anonymous_mode[str(channel.id)] = True
            ticket_customer_data[str(channel.id)] = "ไม่ระบุตัวตน"
        else:
            ticket_customer_data[str(channel.id)] = interaction.user.name
        
        save_json(ticket_customer_data_file, ticket_customer_data)
        
        view = View()
        view.add_item(discord.ui.Button(
            label="📩 ไปที่ตั๋ว", 
            url=f"https://discord.com/channels/{channel.guild.id}/{channel.id}", 
            style=discord.ButtonStyle.link
        ))
        await interaction.followup.send("📩 เปิดตั๋วแจ้งปัญหาเรียบร้อย", view=view, ephemeral=True)
        
        embed = discord.Embed(
            title="⚠️ แจ้งปัญหา", 
            description="กรุณาพิมพ์รายละเอียดปัญหาที่คุณพบในช่องนี้ได้เลย",
            color=PINK_COLOR
        )
        embed.add_field(name="👤 ผู้แจ้ง", value=interaction.user.mention, inline=False)
        embed.set_footer(text="13bux • แจ้งปัญหา")
        embed.set_thumbnail(url=THUMBNAIL_URL)
        
        await channel.send(embed=embed)
        print(f"✅ ส่ง embed แจ้งปัญหาในตั๋ว {channel.name}")

        if admin_role:
            await channel.send(content=f"{admin_role.mention} มีตั๋วแจ้งปัญหาใหม่!", delete_after=10)
        
        await channel.send(f"# กรุณาพิมพ์รายละเอียดปัญหาที่คุณพบได้เลยค่ะ {SUSHI_HEART_EMOJI}")
        
    except Exception as e:
        print(f"❌ Error opening issue ticket: {e}")
        traceback.print_exc()
        try:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)
        except:
            pass



class DeliveryView(View):
    def __init__(self, channel, product_type, robux_amount, price, buyer, is_reorder=False):
        super().__init__(timeout=None)
        self.channel = channel
        self.product_type = product_type
        self.robux_amount = robux_amount
        self.price = price
        self.buyer = buyer
        self.delivered = False
        self.is_reorder = is_reorder
        self.receipt_sent = False
        
        deliver_btn = Button(label="ส่งสินค้าแล้ว ✅", style=discord.ButtonStyle.success, emoji="✅")
        cancel_btn = Button(label="ยกเลิก ❌", style=discord.ButtonStyle.danger, emoji="❌")
        
        async def deliver_cb(i):
            if i.channel.id != self.channel.id:
                return
            
            admin_role = i.guild.get_role(ADMIN_ROLE_ID)
            if not i.user.guild_permissions.administrator and (not admin_role or admin_role not in i.user.roles):
                await i.response.send_message("❌ คุณไม่มีสิทธิ์ใช้ปุ่มนี้", ephemeral=True)
                return
            
            if self.delivered:
                await i.response.edit_message(content="✅ สินค้าถูกส่งเรียบร้อยแล้ว", embed=None, view=None)
                return
            
            delivery_image = None
            async for msg in self.channel.history(limit=10):
                if msg.author == i.user and msg.attachments:
                    for att in msg.attachments:
                        if any(att.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                            delivery_image = att.url
                            break
                    if delivery_image:
                        break
            
            try:
                self.delivered = True
                
                if self.buyer:
                    ticket_customer_data[str(self.channel.id)] = self.buyer.name
                    save_json(ticket_customer_data_file, ticket_customer_data)

                    if self.robux_amount:
                        ticket_id = str(self.channel.id)
                        await add_sp(self.buyer.id, self.robux_amount, ticket_id)
                        await add_daily_robux(self.robux_amount)
                        print(f"✅ Added {self.robux_amount} SP (x1) to {self.buyer.name} via DeliveryView")
                
                receipt_color = PINK_COLOR
                
                anonymous_mode = ticket_anonymous_mode.get(str(self.channel.id), False)
                buyer_display = "ไม่ระบุตัวตน" if anonymous_mode else (self.buyer.mention if self.buyer else "ไม่ทราบ")
                
                if not self.receipt_sent:
                    self.receipt_sent = True
                    
                    log_channel = bot.get_channel(SALES_LOG_CHANNEL_ID)
                    if log_channel:
                        log_embed = discord.Embed(
                            title=f"🌸 ใบเสร็จการสั่งซื้อ ({self.product_type}) 🌸", 
                            color=receipt_color
                        )
                        log_embed.add_field(name="😊 ผู้ซื้อ", value=buyer_display, inline=False)
                        log_embed.add_field(name="💸 จำนวน Robux", value=f"{format_number(self.robux_amount)}", inline=True)
                        price_int = round_price(self.price)
                        log_embed.add_field(name="💰 ราคาตามเรท", value=f"{format_number(price_int)} บาท", inline=True)
                        
                        if delivery_image:
                            log_embed.set_image(url=delivery_image)
                        
                        log_embed.set_footer(text=f"จัดส่งสินค้าสำเร็จ 🤗 • {get_thailand_time().strftime('%d/%m/%y, %H:%M')}")
                        
                        await log_channel.send(embed=log_embed)
                        print(f"✅ ส่งใบเสร็จไปยัง sales log channel เรียบร้อย")
                    
                    if self.buyer and not anonymous_mode and not self.is_reorder:
                        try:
                            dm_embed = discord.Embed(
                                title=f"🧾 ใบเสร็จการซื้อสินค้า ({self.product_type})",
                                description="ขอบคุณที่ใช้บริการ 13bux นะคะ 🌸",
                                color=receipt_color
                            )
                            dm_embed.add_field(name="📦 สินค้า", value=self.product_type, inline=True)
                            dm_embed.add_field(name="💸 จำนวน Robux", value=f"{format_number(self.robux_amount)}", inline=True)
                            
                            if self.product_type != "เติมโรแท้":
                                price_int = round_price(self.price)
                                dm_embed.add_field(name="💰 ราคา", value=f"{format_number(price_int)} บาท", inline=True)
                            
                            if delivery_image:
                                dm_embed.set_image(url=delivery_image)
                            
                            dm_embed.add_field(name="📝 หมายเหตุ", value="หากมีปัญหากรุณาติดต่อแอดมินในเซิร์ฟ", inline=False)
                            dm_embed.set_footer(text="13bux • ขอบคุณที่ใช้บริการ💖")
                            
                            await self.buyer.send(embed=dm_embed)
                            print(f"✅ ส่งใบเสร็จไปยัง DM ของ {self.buyer.name} เรียบร้อย")
                        except Exception as e:
                            print(f"⚠️ ไม่สามารถส่ง DM ถึง {self.buyer.name}: {e}")
                
                try:
                    await i.response.edit_message(
                        content="✅ บันทึกการส่งสินค้าเรียบร้อย", 
                        embed=None, 
                        view=None
                    )
                except:
                    try:
                        await i.response.send_message("✅ บันทึกการส่งสินค้าเรียบร้อย", ephemeral=True)
                    except:
                        pass
                        
            except Exception as e:
                print(f"Error in deliver_cb: {e}")
                try:
                    await i.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)
                except:
                    pass
        
        async def cancel_cb(i):
            if i.channel.id != self.channel.id:
                return
            await i.response.send_message("❌ คำสั่งซื้อถูกยกเลิก", ephemeral=True)
            await i.message.delete()
        
        deliver_btn.callback = deliver_cb
        cancel_btn.callback = cancel_cb
        
        self.add_item(deliver_btn)
        self.add_item(cancel_btn)

# ============ BOT CLASS ============
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.last_update_time = 0
        self.is_reacting_to_credit_channel = False
        self.commands_synced = False
        self.stock_lock = asyncio.Lock()
        self.api_rate_limiter = RateLimiter(1, 1.0)
        self.react_rate_limiter = RateLimiter(1, 0.5)
        self.channel_edit_rate_limiter = RateLimiter(1, 5)
        self.command_rate_limiter = RateLimiter(1, 2)
        self.stock_message = None
        self.main_channel_message = None
        self._shutdown_flag = False
        self._shutdown_event = asyncio.Event()
        
        load_all_data()
        backup_user_levels()
    
    async def setup_hook(self):
        print(f"✅ Setup hook completed")
        await self.tree.sync()
        print(f"✅ Slash commands synced")
    
    async def close(self):
        print("\n⚠️ กำลังปิดระบบอย่างปลอดภัย...")
        print("💾 กำลังบันทึกข้อมูลทั้งหมด...")
        
        for i in range(3):
            save_all_data_sync()
            await asyncio.sleep(0.5)
        
        backup_user_levels()
        print("✅ บันทึกข้อมูลเรียบร้อย!")
        print("👋 ลาก่อน!")
        
        await super().close()

bot = MyBot()

# ============ TICKET HELPER FUNCTIONS ============
def cancel_removal(channel_id):
    if str(channel_id) in ticket_removal_tasks:
        ticket_removal_tasks[str(channel_id)].cancel()
        del ticket_removal_tasks[str(channel_id)]
        print(f"✅ Cancelled removal timer for channel {channel_id}")
        return True
    return False

async def reset_timer(channel, buyer):
    print(f"🔄 Cancelling timer for channel {channel.name} (customer wants to order more)")
    cancel_removal(channel.id)
    print(f"✅ Timer cancelled for {channel.name} - customer will not lose access")

async def schedule_auto_delete_after_delivered(channel, delay_seconds):
    if str(channel.id) in ticket_archived_timers:
        try:
            ticket_archived_timers[str(channel.id)].cancel()
        except:
            pass
    
    task = asyncio.create_task(auto_delete_ticket_after_delay(channel, delay_seconds))
    ticket_archived_timers[str(channel.id)] = task
    
    try:
        await task
    except asyncio.CancelledError:
        print(f"ℹ️ Auto-delete task cancelled for {channel.name}")
    finally:
        if str(channel.id) in ticket_archived_timers:
            del ticket_archived_timers[str(channel.id)]

async def auto_delete_ticket_after_delay(channel, delay_seconds):
    try:
        print(f"⏳ Ticket {channel.name} will be deleted in {delay_seconds/3600} hours")
        await asyncio.sleep(delay_seconds)
        
        if not channel or channel not in channel.guild.channels:
            print(f"❌ Ticket {channel.name} no longer exists")
            return
        
        await save_ticket_transcript(channel, "ระบบอัตโนมัติ (1 ชั่วโมง)")
        await asyncio.sleep(2)
        
        print(f"🗑️ Auto-deleting ticket {channel.name} after {delay_seconds/3600} hours")
        await channel.delete()
        
    except Exception as e:
        print(f"❌ Error in auto_delete_ticket_after_delay: {e}")

async def update_channel_name():
    try:
        channel = bot.get_channel(STATUS_CHANNEL_ID)
        if not channel:
            print(f"❌ Status channel not found: {STATUS_CHANNEL_ID}")
            return
        
        new_name = "🟢 เปิด" if shop_open else "🔴 ปิด"
        
        if channel.name != new_name:
            await bot.channel_edit_rate_limiter.acquire()
            await channel.edit(name=new_name)
            print(f"✅ เปลี่ยนชื่อช่องสถานะเป็น: {new_name}")
        else:
            print(f"ℹ️ ชื่อช่องสถานะคงเดิม: {channel.name}")
    except Exception as e:
        print(f"❌ Error updating status channel name: {e}")

async def update_rate_channel_name():
    try:
        channel = bot.get_channel(RATE_CHANNEL_ID)
        if not channel:
            print(f"❌ Rate channel not found: {RATE_CHANNEL_ID}")
            return
        
        rate_str = format_rate_for_channel(gamepass_rate)
        new_name = f"⋆˚🐷ㆍเรท{rate_str}"
        
        if channel.name != new_name:
            await bot.channel_edit_rate_limiter.acquire()
            await channel.edit(name=new_name)
            print(f"✅ เปลี่ยนชื่อช่องเรทเป็น: {new_name}")
        else:
            print(f"ℹ️ ชื่อช่องเรทคงเดิม: {channel.name}")
    except Exception as e:
        print(f"❌ Error updating rate channel name: {e}")

async def update_main_channel():
    try:
        channel = bot.get_channel(MAIN_CHANNEL_ID)
        if not channel:
            print(f"❌ Main channel not found: {MAIN_CHANNEL_ID}")
            return
        
        if not shop_open:
            status_text = "🌸13bux🌸 ปิดให้บริการ"
            color = PINK_COLOR
        elif shop_open and gamepass_stock > 0:
            status_text = "🌸13bux🌸 เปิดให้บริการ"
            color = PINK_COLOR
        else:
            status_text = "🌸13bux🌸 ปิดให้บริการ (สินค้าหมด)"
            color = PINK_COLOR
        
        embed = discord.Embed(title=status_text, color=color)
        
        embed.add_field(
            name=f"🎮 กดเกมพาสเรท ({gamepass_rate})",
            value="\u200b",
            inline=False
        )
        
        embed.set_thumbnail(url=THUMBNAIL_URL)
        embed.set_image(url=MAIN_IMAGE_URL)
        embed.set_footer(
            text=f"13bux กดเกมพาส |: {get_thailand_time().strftime('%d/%m/%y %H:%M')}",
            icon_url=THUMBNAIL_URL
        )
        
        view = EmbedShopView()
        
        if bot.main_channel_message:
            try:
                await bot.main_channel_message.edit(embed=embed, view=view)
                print("✅ Updated main channel message")
                return
            except Exception as e:
                print(f"⚠️ Failed to edit cached main message: {e}")
                bot.main_channel_message = None
        
        async for msg in channel.history(limit=20):
            if msg.author == bot.user and len(msg.embeds) > 0:
                if "13bux" in msg.embeds[0].title:
                    bot.main_channel_message = msg
                    await msg.edit(embed=embed, view=view)
                    print("✅ Found and updated existing main channel message")
                    return
        
        bot.main_channel_message = await channel.send(embed=embed, view=view)
        print("✅ Sent new main channel message")
        
    except Exception as e:
        print(f"❌ Error updating main channel: {e}")
        traceback.print_exc()
        

async def handle_open_ticket(interaction, category_name, stock_type):
    """Legacy handler - routes to gamepass ticket"""
    await handle_open_gamepass_ticket(interaction)

async def save_ticket_transcript(channel, action_by=None, robux_amount=None, customer_name=None):
    try:
        print(f"📝 กำลังบันทึกประวัติตั๋ว: {channel.name}")
        ticket_number = get_next_ticket_number()
        now = get_thailand_time()
        date_str = now.strftime("%d%m%y")
        time_str = now.strftime("%H%M")
        
        if robux_amount:
            robux_str = str(robux_amount)
        else:
            robux_str = ticket_robux_data.get(str(channel.id), "1099")
        
        if customer_name:
            customer_str = customer_name
        else:
            customer_str = ticket_customer_data.get(
                str(channel.id), 
                channel.name.split('-')[1] if channel.name.startswith("ticket-") else "wforr"
            )
        
        filename = f"{date_str}{time_str}-{robux_str}-{customer_str}"
        
        ticket_transcripts[str(channel.id)] = {
            "filename": filename,
            "channel_name": channel.name,
            "channel_id": channel.id,
            "ticket_number": ticket_number,
            "date": date_str,
            "time": time_str,
            "timestamp": f"{date_str}{time_str}",
            "robux_amount": str(robux_str),
            "customer_name": customer_str,
            "category": channel.category.name if channel.category else "ไม่มีหมวดหมู่",
            "created_at": now.isoformat(),
            "closed_by": str(action_by) if action_by else "ระบบอัตโนมัติ",
            "messages_count": 0
        }
        
        save_json(ticket_transcripts_file, ticket_transcripts)
        print(f"✅ บันทึกประวัติตั๋วเรียบร้อย: {filename}")
        return True, filename
        
    except Exception as e:
        print(f"❌ Error saving transcript: {e}")
        return False, str(e)

async def move_to_delivered_category(channel):
    try:
        if not channel:
            return False
            
        guild = channel.guild
        
        delivered_category = guild.get_channel(DELIVERED_CATEGORY_ID)
        if not delivered_category or not isinstance(delivered_category, discord.CategoryChannel):
            delivered_category = discord.utils.get(guild.categories, id=DELIVERED_CATEGORY_ID)
            if not delivered_category:
                print(f"❌ ไม่พบ category ส่งของแล้ว (ID: {DELIVERED_CATEGORY_ID})")
                return False
        
        if channel.category and channel.category.id == DELIVERED_CATEGORY_ID:
            print(f"ℹ️ ตั๋ว {channel.name} อยู่ใน category ส่งของแล้วแล้ว")
            return True
        
        await channel.edit(category=delivered_category)
        print(f"✅ ย้ายตั๋ว {channel.name} ไปยัง category ส่งของแล้ว")
        
        await schedule_auto_delete_after_delivered(channel, 3600)
        print(f"⏰ Ticket {channel.name} will be auto-deleted in 1 hour")
        
        return True
        
    except Exception as e:
        print(f"❌ Error moving to delivered category: {e}")
        return False

async def move_to_original_category(channel, product_type):
    try:
        if not channel:
            return False
            
        guild = channel.guild
        target_category = guild.get_channel(GAMEPASS_TICKET_CATEGORY_ID)
        if not target_category:
            target_category = discord.utils.get(guild.categories, id=GAMEPASS_TICKET_CATEGORY_ID)
        
        if not target_category:
            print(f"❌ ไม่พบ category สำหรับ {product_type}")
            return False
        
        buyer_id = None
        if str(channel.id) in ticket_buyer_data:
            buyer_id = ticket_buyer_data[str(channel.id)].get("user_id")
        
        if buyer_id:
            buyer = guild.get_member(buyer_id)
            if buyer:
                overwrites = channel.overwrites
                if buyer in overwrites:
                    overwrites[buyer].update(read_messages=True)
                else:
                    overwrites[buyer] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                await channel.edit(overwrites=overwrites)
                print(f"✅ Restored view permission for {buyer.name}")
        
        await channel.edit(category=target_category)
        print(f"✅ ย้ายตั๋ว {channel.name} กลับไปยัง category {target_category.name}")
        return True
        
    except Exception as e:
        print(f"❌ Error moving to original category: {e}")
        return False

async def reset_channel_name(channel, user_id, product_type):
    try:
        user = None
        for member in channel.guild.members:
            if member.id == user_id:
                user = member
                break
        
        if not user:
            channel_name = channel.name
            if '-' in channel_name:
                parts = channel_name.split('-')
                if len(parts) >= 2:
                    potential_name = parts[-1].lower()
                    for member in channel.guild.members:
                        if member.name.lower() == potential_name or member.display_name.lower() == potential_name:
                            user = member
                            break
        
        if user:
            new_name = f"ticket-{user.name}-{user.id}".lower()
            await channel.edit(name=new_name)
            print(f"✅ เปลี่ยนชื่อตั๋วเป็น: {new_name}")
            return True
        else:
            print(f"❌ ไม่พบผู้ใช้สำหรับ channel {channel.name}")
            return False
            
    except Exception as e:
        print(f"❌ Error resetting channel name: {e}")
        return False

async def add_buyer_role(buyer, guild):
    try:
        if not buyer:
            return False
        
        buyer_role = guild.get_role(BUYER_ROLE_ID)
        if not buyer_role:
            print(f"❌ ไม่พบ role ID: {BUYER_ROLE_ID}")
            return False
        
        if buyer_role not in buyer.roles:
            await buyer.add_roles(buyer_role)
            print(f"✅ เพิ่ม role ให้ {buyer.name} เรียบร้อย")
            return True
        else:
            print(f"ℹ️ {buyer.name} มี role อยู่แล้ว")
            return False
            
    except Exception as e:
        print(f"❌ Error adding buyer role: {e}")
        return False

# ============ CREDIT CHANNEL FUNCTIONS ============
async def update_credit_channel_name():
    try:
        credit_channel = bot.get_channel(CREDIT_CHANNEL_ID)
        if not credit_channel:
            print(f"❌ Credit channel not found with ID: {CREDIT_CHANNEL_ID}")
            return
        
        message_count = 0
        try:
            async for _ in credit_channel.history(limit=None):
                message_count += 1
                if message_count >= 10000:
                    break
            print(f"📊 Credit channel has {message_count} messages")
        except Exception as e:
            print(f"⚠️ Error counting messages: {e}")
            return
        
        new_name = f"〔✅〕ให้เครดิต--{message_count}"
        
        if credit_channel.name != new_name:
            try:
                await credit_channel.edit(name=new_name)
                print(f"✅ Credit channel name updated to: {new_name}")
            except Exception as e:
                print(f"❌ Error updating channel name: {e}")
        else:
            print(f"ℹ️ Credit channel name already correct: {new_name}")
            
    except Exception as e:
        print(f"❌ Error in update_credit_channel_name: {e}")
        traceback.print_exc()

@tasks.loop(minutes=5)
async def update_credit_channel_task():
    print("🔄 Running credit channel update task...")
    await update_credit_channel_name()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.channel.id == CREDIT_CHANNEL_ID:
        if message.author != bot.user:
            await asyncio.sleep(1)
            for emoji in ["❤️"]:
                try:
                    await message.add_reaction(emoji)
                    await asyncio.sleep(0.5)
                except:
                    pass
            
            await update_credit_channel_name()
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.channel.id == CREDIT_CHANNEL_ID:
        await asyncio.sleep(1)
        await update_credit_channel_name()

@bot.event
async def on_bulk_message_delete(messages):
    if messages and messages[0].channel.id == CREDIT_CHANNEL_ID:
        await asyncio.sleep(1)
        await update_credit_channel_name()


# ============ BASIC COMMANDS ============
@bot.command(name="open")
@admin_only()
async def open_cmd(ctx):
    global shop_open
    shop_open = True
    
    try:
        await ctx.message.delete()
    except:
        pass
    
    save_stock_values()
    bot.main_channel_message = None
    
    await update_channel_name()
    await update_main_channel()
    
    embed = discord.Embed(title="✅ เปิดร้าน", description="ร้าน 13bux เปิดให้บริการ", color=PINK_COLOR)
    embed.set_footer(text=f"เวลา: {get_thailand_time().strftime('%d/%m/%y %H:%M')}")
    await ctx.send(embed=embed)
    print(f"✅ Shop opened by {ctx.author.name}, shop_open={shop_open}")

@bot.command(name="close")
@admin_only()
async def close_cmd(ctx):
    global shop_open
    shop_open = False
    
    try:
        await ctx.message.delete()
    except:
        pass
    
    save_stock_values()
    bot.main_channel_message = None
    
    await update_channel_name()
    await update_main_channel()
    
    embed = discord.Embed(title="🔴 ปิดร้าน", description="ร้าน 13bux ปิดให้บริการชั่วคราว", color=PINK_COLOR)
    embed.set_footer(text=f"เวลา: {get_thailand_time().strftime('%d/%m/%y %H:%M')}")
    await ctx.send(embed=embed)
    print(f"✅ Shop closed by {ctx.author.name}, shop_open={shop_open}")

# ============ RATE COMMAND ============
@bot.command()
@admin_only()
async def rate(ctx, normal_rate=None):
    """
    !rate               → show current rate
    !rate <normal_rate> → set new rate (also renames RATE_CHANNEL_ID)
    """
    global gamepass_rate, gamepass_rate_high
    
    try:
        await ctx.message.delete()
    except:
        pass
    
    if normal_rate is None:
        embed = discord.Embed(title="🌸 เรทโรบัคปัจจุบัน", color=PINK_COLOR)
        embed.add_field(name="🎮 Gamepass Rate", value=f"**{gamepass_rate}**", inline=True)
        await ctx.send(embed=embed)
        return
    
    try:
        new_rate = float(normal_rate)
        if new_rate <= 0:
            await ctx.send("❌ เรทต้องมากกว่า 0", delete_after=5)
            return
        
        gamepass_rate = new_rate
        gamepass_rate_high = new_rate
        save_stock_values()
        
        await update_rate_channel_name()
        
        embed = discord.Embed(
            title="✅ เปลี่ยนเรทเกมพาสเรียบร้อย",
            description=f"ตั้งค่าเรทเกมพาสเป็น **{gamepass_rate}** เรียบร้อยแล้ว",
            color=PINK_COLOR
        )
        await ctx.send(embed=embed)
        await update_main_channel()
    except ValueError:
        await ctx.send("❌ กรุณากรอกตัวเลขให้ถูกต้อง เช่น `!rate 5`", delete_after=5)


# ============ ORDER COMMANDS ============
@bot.command()
@admin_only()
async def od(ctx, *, expr):
    global gamepass_stock, gamepass_rate
    
    if not ctx.channel.name.startswith("ticket-") and not re.match(r'^\d{10}-\d+-[\w\u0E00-\u0E7F]+$', ctx.channel.name):
        await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะในตั๋วเท่านั้น", delete_after=5)
        return
    
    try:
        expr_clean = expr.replace(",", "").lower().replace("x", "*").replace("÷", "/").replace(" ", "")
        robux = int(eval(expr_clean))
        
        rate = get_gamepass_rate(robux)
        price = robux / rate
        price_int = round_price(price)
        
        buyer = None
        if str(ctx.channel.id) in ticket_buyer_data:
            buyer_id = ticket_buyer_data[str(ctx.channel.id)].get("user_id")
            if buyer_id:
                buyer = ctx.guild.get_member(buyer_id)
        
        if not buyer:
            parts = ctx.channel.name.split('-')
            if len(parts) >= 3:
                try:
                    buyer = ctx.guild.get_member(int(parts[-1]))
                except:
                    pass
        
        if not buyer:
            async for msg in ctx.channel.history(limit=20):
                if not msg.author.bot and msg.author != ctx.guild.me:
                    buyer = msg.author
                    break
        
        balance_message = None
        if buyer:
            current_balance = get_user_robux_balance(buyer.id)
            if current_balance > 0:
                if current_balance >= price_int:
                    new_balance = deduct_user_robux_balance(buyer.id, price_int)
                    balance_message = f"\n\n💰 **{buyer.mention} เหลือ {new_balance:.2f} บาท**"
                else:
                    balance_message = f"\n\n⚠️ **{buyer.mention} มีเงินบาทเหลือไม่พอ!** (มี {current_balance:.2f} บาท ต้องการ {price_int} บาท)"
        
        if buyer:
            await add_buyer_role(buyer, ctx.guild)
        
        async with bot.stock_lock:
            gamepass_stock = max(0, gamepass_stock - robux)
        
        save_stock_values()
        
        ticket_robux_data[str(ctx.channel.id)] = str(robux)
        save_json(ticket_robux_data_file, ticket_robux_data)
        
        embed = discord.Embed(title="🌸คำสั่งซื้อสินค้า🌸", color=PINK_COLOR)
        embed.add_field(name="📦 ประเภทสินค้า", value="Gamepass", inline=False)
        embed.add_field(name="💸 จำนวน Robux", value=f"{format_number(robux)}", inline=True)
        embed.add_field(name="💰 ราคาตามเรท", value=f"{format_number(price_int)} บาท", inline=True)
        
        if balance_message:
            embed.add_field(name="💵 เงินคงเหลือ", value=balance_message, inline=False)
        
        embed.set_footer(text=f"รับออร์เดอร์แล้ว 🤗 • {get_thailand_time().strftime('%d/%m/%y, %H:%M')}")
        
        await ctx.send(embed=embed, view=DeliveryView(ctx.channel, "Gamepass", robux, price, buyer, is_reorder=False))
        await update_main_channel()
        
    except Exception as e:
        print(f"❌ Error in !od: {e}")
        traceback.print_exc()
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")


# ============ !odt COMMAND FOR TOPUP TICKETS ============
@bot.command(name="odt")
@admin_only()
async def odt(ctx, *, expr=None):
    """Order command for topup tickets (topup-...).
    
    Usage:
      !odt        -> use accumulated robux+price from button clicks
      !odt 1000   -> override with explicit robux amount (price computed from TOPUP_PRICES)
    """
    
    if not ctx.channel.name.startswith("topup-"):
        await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะในตั๋วเติมโรแท้ (topup-...) เท่านั้น", delete_after=5)
        return
    
    ticket_id = str(ctx.channel.id)
    
    # Determine robux and price
    if expr is None:
        stored_robux = ticket_robux_data.get(ticket_id)
        if not stored_robux:
            await ctx.send("❌ กรุณาระบุจำนวนโรบัค เช่น `!odt 1000` หรือกดเลือกแพ็กก่อน", delete_after=5)
            return
        try:
            robux = int(float(stored_robux))
        except (ValueError, TypeError):
            await ctx.send("❌ ไม่พบจำนวนโรบัคในตั๋วนี้ กรุณาระบุ เช่น `!odt 1000`", delete_after=5)
            return
        
        # Use accumulated price from button clicks if available
        stored_price = ticket_topup_price.get(ticket_id)
        if stored_price is not None:
            try:
                price = int(float(stored_price))
            except (ValueError, TypeError):
                price = calculate_topup_price_from_robux(robux)
        else:
            price = calculate_topup_price_from_robux(robux)
    else:
        try:
            expr_clean = expr.replace(",", "").lower().replace("x", "*").replace("÷", "/").replace(" ", "")
            robux = int(eval(expr_clean))
        except Exception as e:
            await ctx.send(f"❌ ตัวเลขไม่ถูกต้อง: {e}", delete_after=5)
            return
        
        # For manual amount, compute price from TOPUP_PRICES (greedy combination)
        price = calculate_topup_price_from_robux(robux)
    
    try:
        buyer = None
        if str(ctx.channel.id) in ticket_buyer_data:
            buyer_id = ticket_buyer_data[str(ctx.channel.id)].get("user_id")
            if buyer_id:
                buyer = ctx.guild.get_member(buyer_id)
        
        if not buyer:
            parts = ctx.channel.name.split('-')
            if len(parts) >= 3:
                try:
                    buyer = ctx.guild.get_member(int(parts[-1]))
                except:
                    pass
        
        if not buyer:
            async for msg in ctx.channel.history(limit=30):
                if not msg.author.bot and msg.author != ctx.guild.me:
                    buyer = msg.author
                    break
        
        # Store final robux + price
        ticket_robux_data[ticket_id] = str(robux)
        save_json(ticket_robux_data_file, ticket_robux_data)
        ticket_topup_price[ticket_id] = str(price)
        save_json(ticket_topup_price_file, ticket_topup_price)
        
        if buyer:
            await add_buyer_role(buyer, ctx.guild)
        
        price_int = round_price(price)
        
        balance_message = None
        if buyer:
            current_balance = get_user_robux_balance(buyer.id)
            if current_balance > 0:
                if current_balance >= price_int:
                    new_balance = deduct_user_robux_balance(buyer.id, price_int)
                    balance_message = f"\n\n💰 **{buyer.mention} เหลือ {new_balance:.2f} บาท**"
                else:
                    balance_message = f"\n\n⚠️ **{buyer.mention} มีเงินบาทเหลือไม่พอ!** (มี {current_balance:.2f} บาท ต้องการ {price_int} บาท)"
        
        embed = discord.Embed(title="🌸คำสั่งซื้อเติมโรแท้🌸", color=PINK_COLOR)
        embed.add_field(name="📦 ประเภทสินค้า", value="เติมโรแท้ (Robux แท้)", inline=False)
        embed.add_field(name="💎 จำนวน Robux", value=f"{format_number(robux)}", inline=True)
        embed.add_field(name="💰 ราคา", value=f"{format_number(price_int)} บาท", inline=True)
        
        if balance_message:
            embed.add_field(name="💵 เงินคงเหลือ", value=balance_message, inline=False)
        
        embed.set_footer(text=f"รับออร์เดอร์แล้ว 🤗 • {get_thailand_time().strftime('%d/%m/%y, %H:%M')}")
        embed.set_thumbnail(url=THUMBNAIL_URL)
        
        await ctx.send(embed=embed, view=DeliveryView(ctx.channel, "เติมโรแท้", robux, price, buyer, is_reorder=False))
        
    except Exception as e:
        print(f"❌ Error in !odt: {e}")
        traceback.print_exc()
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")


@bot.command(name="tkd")
@admin_only()
async def tkd_cmd(ctx):
    channel = ctx.channel
    channel_name = channel.name
    
    valid_formats = False
    
    if channel_name.startswith("ticket-") or channel_name.startswith("topup-") or channel_name.startswith("issue-"):
        valid_formats = True
    
    pattern = r'^\d{10}-\d+-[\w\u0E00-\u0E7F]+$'
    if re.match(pattern, channel_name):
        valid_formats = True
    
    if not valid_formats:
        await ctx.send(f"❌ คำสั่งนี้ใช้ได้เฉพาะในช่องตั๋วเท่านั้น\nรูปแบบที่ใช้ได้: ticket-... หรือ [ddmmyytime-amount-user]\nตัวอย่าง: 0703262106-4-eurrai", delete_after=10)
        return
    
    try:
        msg = await ctx.send("🗑️ กำลังลบตั๋วนี้...")
        await save_ticket_transcript(channel, ctx.author)
        await asyncio.sleep(2)
        await channel.delete()
        print(f"✅ ลบตั๋ว {channel_name} โดย {ctx.author.name}")
        
    except Exception as e:
        print(f"❌ Error in tkd: {e}")
        traceback.print_exc()
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")

# ============ TY COMMAND ============
@bot.command()
@admin_only()
async def ty(ctx):
    global gamepass_stock
    
    if not (ctx.channel.name.startswith("ticket-") 
            or ctx.channel.name.startswith("topup-") 
            or re.match(r'^\d{10}-\d+-[\w\u0E00-\u0E7F]+$', ctx.channel.name)):
        await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะในตั๋วเท่านั้น", delete_after=5)
        return
    
    try:
        buyer = None
        channel_name = ctx.channel.name
        ticket_id = str(ctx.channel.id)
        
        if ticket_id in ticket_buyer_data:
            buyer_id = ticket_buyer_data[ticket_id].get("user_id")
            if buyer_id:
                buyer = ctx.guild.get_member(buyer_id)
        
        if not buyer and (channel_name.startswith("ticket-") or channel_name.startswith("topup-")):
            parts = channel_name.split('-')
            if len(parts) >= 3:
                try:
                    user_id = int(parts[-1])
                    buyer = ctx.guild.get_member(user_id)
                except ValueError:
                    pass
        
        if not buyer:
            async for msg in ctx.channel.history(limit=50):
                if not msg.author.bot and msg.author != ctx.guild.me:
                    buyer = msg.author
                    break
        
        is_topup = channel_name.startswith("topup-")
        product_type = "เติมโรแท้" if is_topup else "Gamepass"
        
        # Determine robux amount and price
        robux_amount = ticket_robux_data.get(ticket_id, "0")
        try:
            robux_int = int(float(robux_amount))
        except (ValueError, TypeError):
            robux_int = 0
        
        price_int = 0
        if is_topup:
            stored_price = ticket_topup_price.get(ticket_id)
            if stored_price is not None:
                try:
                    price_int = int(float(stored_price))
                except (ValueError, TypeError):
                    price_int = calculate_topup_price_from_robux(robux_int)
            else:
                price_int = calculate_topup_price_from_robux(robux_int)
        else:
            # Gamepass: price = robux / rate
            if robux_int > 0:
                price_int = round_price(robux_int / gamepass_rate)
        
        asyncio.create_task(save_ticket_transcript_background(ctx.channel, buyer, robux_int))
        
        if not is_topup:
            if ctx.channel.category:
                category_name = ctx.channel.category.name.lower()
                if "gamepass" in category_name:
                    async with bot.stock_lock:
                        gamepass_stock += 1
            save_stock_values()
        
        # ===== Send receipt to SALES_LOG_CHANNEL_ID =====
        # (This is now sent here too, so it works even if admin never clicked "ส่งสินค้าแล้ว")
        try:
            log_channel = bot.get_channel(SALES_LOG_CHANNEL_ID)
            if log_channel:
                anonymous_mode = ticket_anonymous_mode.get(ticket_id, False)
                buyer_display = "ไม่ระบุตัวตน" if anonymous_mode else (buyer.mention if buyer else "ไม่ทราบ")
                
                log_embed = discord.Embed(
                    title=f"🌸 ใบเสร็จการสั่งซื้อ ({product_type}) 🌸",
                    color=PINK_COLOR
                )
                log_embed.add_field(name="😊 ผู้ซื้อ", value=buyer_display, inline=False)
                log_embed.add_field(name="💸 จำนวน Robux", value=f"{format_number(robux_int)}", inline=True)
                log_embed.add_field(name="💰 ราคาตามเรท", value=f"{format_number(price_int)} บาท", inline=True)
                log_embed.set_footer(text=f"จัดส่งสินค้าสำเร็จ 🤗 • {get_thailand_time().strftime('%d/%m/%y, %H:%M')}")
                
                await log_channel.send(embed=log_embed)
                print(f"✅ ส่งใบเสร็จไปยัง sales log channel เรียบร้อย (จาก !ty)")
            else:
                print(f"❌ Sales log channel not found: {SALES_LOG_CHANNEL_ID}")
        except Exception as e:
            print(f"⚠️ Error sending receipt to sales log channel: {e}")
        
        embed = discord.Embed(
            title="✅ ส่งของเรียบร้อย",
            description=(
                "**ขอบคุณที่ใช้บริการ 13bux** 🌸\n"
                "ฝากให้เครดิต +1 ด้วยนะคะ ❤️\n\n"
                "⚠️ **หมายเหตุ:** ตั๋วนี้จะถูกลบใน 1 ชั่วโมง"
            ),
            color=PINK_COLOR
        )
        embed.set_footer(text="13bux 🌸❤️")
        embed.set_thumbnail(url=THUMBNAIL_URL)
        
        view = View(timeout=None)
        credit_button = Button(
            label="ให้เครดิต🌸", 
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{ctx.guild.id}/{CREDIT_CHANNEL_ID}",
            emoji="☑️"
        )
        view.add_item(credit_button)
        
        await ctx.send(embed=embed, view=view)
        
        if product_type == "Gamepass" and buyer:
            order_more_view = View(timeout=None)
            order_more_btn = Button(label="สั่งของต่อ 📝", style=discord.ButtonStyle.success, emoji="🔄")
            
            async def order_more_cb(interaction):
                if interaction.channel.id != ctx.channel.id:
                    await interaction.response.send_message("❌ คุณไม่สามารถใช้ปุ่มนี้ในช่องอื่นได้", ephemeral=True)
                    return
                
                await interaction.response.defer(ephemeral=True)
                await process_order_more_fixed(ctx.channel, buyer, interaction)
            
            order_more_btn.callback = order_more_cb
            order_more_view.add_item(order_more_btn)
            await ctx.send("📝 ต้องการสั่งของเพิ่มมั้ยคะ?", view=order_more_view)
        
        if ticket_id in ticket_robux_data:
            del ticket_robux_data[ticket_id]
            save_json(ticket_robux_data_file, ticket_robux_data)
        
        if ticket_id in ticket_customer_data:
            del ticket_customer_data[ticket_id]
            save_json(ticket_customer_data_file, ticket_customer_data)
        
        if ticket_id in ticket_topup_price:
            del ticket_topup_price[ticket_id]
            save_json(ticket_topup_price_file, ticket_topup_price)
        
        asyncio.create_task(move_to_delivered_category_with_cleanup(ctx.channel, buyer))
        await update_main_channel()
        
        print(f"✅ คำสั่ง !ty ดำเนินการสำเร็จสำหรับห้อง {ctx.channel.name}")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดใน !ty: {e}")
        traceback.print_exc()
        try:
            await ctx.send(f"✅ ให้เครดิตเรียบร้อยแล้ว")
        except:
            pass

async def process_order_more_fixed(channel, buyer, interaction):
    try:
        await reset_timer(channel, buyer)
        
        if buyer:
            await reset_channel_name(channel, buyer.id, "gamepass")
        
        await move_to_original_category(channel, "gamepass")
        
        admin_role = channel.guild.get_role(ADMIN_ROLE_ID)
        admin_mention = admin_role.mention if admin_role else "@ADMIN"
        
        order_embed = discord.Embed(
            title="🌸13bux🌸", 
            color=PINK_COLOR
        )
        order_embed.add_field(name="👤 ผู้ซื้อ", value=buyer.mention if buyer else "ไม่ระบุ", inline=False)
        order_embed.add_field(name=f"💰 กดเกมพาสเรท ({gamepass_rate})", value="\u200b", inline=False)
        order_embed.set_footer(text="13bux")
        order_embed.set_thumbnail(url=THUMBNAIL_URL)
        
        await channel.send(embed=order_embed)
        await interaction.followup.send("✅ รีเซ็ตระบบเรียบร้อย! กรุณาสั่งของเพิ่มได้เลยค่ะ", ephemeral=True)
        
        print(f"✅ Order more processed for {channel.name} - Timer cancelled")
        
    except Exception as e:
        print(f"❌ Error processing order more: {e}")
        try:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)
        except:
            pass
            
async def save_ticket_transcript_background(channel, buyer, robux_int):
    try:
        save_success, filename = await save_ticket_transcript(channel, buyer, robux_int, None)
        if save_success and filename:
            try:
                await channel.edit(name=filename[:100])
                print(f"✅ Channel renamed to: {filename[:100]}")
            except Exception as e:
                print(f"⚠️ Failed to rename channel: {e}")
    except Exception as e:
        print(f"❌ Error in background transcript save: {e}")

async def move_to_delivered_category_with_cleanup(channel, buyer):
    try:
        if channel.category and channel.category.id != DELIVERED_CATEGORY_ID:
            await move_to_delivered_category(channel)
            print(f"✅ Moved {channel.name} to delivered category")
        else:
            print(f"ℹ️ Channel {channel.name} already in delivered category or category not found")
        
    except Exception as e:
        print(f"❌ Error moving to delivered category: {e}")

# ============ DM COMMAND ============
@bot.command(name="dm")
@admin_only()
async def dm_cmd(ctx, user: discord.Member, *, message: str):
    try:
        await user.send(message)
        await ctx.send(f"✅ ส่งข้อความไปยัง {user.mention} เรียบร้อยแล้ว", delete_after=5)
        print(f"✅ Sent DM to {user.name}: {message}")
    except discord.Forbidden:
        await ctx.send(f"❌ ไม่สามารถส่ง DM ไปยัง {user.mention} ได้ (ปิดการรับ DM)", delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}", delete_after=5)
        print(f"❌ Error sending DM: {e}")

# ============ PAYMENT COMMANDS ============
class PaymentView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        qr_btn = Button(label="สแกน QR ชำระเงิน", style=discord.ButtonStyle.success, emoji="📲")
        account_btn = Button(label="โอนผ่านเลขบัญชี", style=discord.ButtonStyle.primary, emoji="🏦")
        
        qr_btn.callback = self.qr_callback
        account_btn.callback = self.account_callback
        
        self.add_item(qr_btn)
        self.add_item(account_btn)
    
    async def qr_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💳 ชำระเงินผ่าน QR",
            description="**ธนาคารกรุงไทย (Krung Thai)**",
            color=PINK_COLOR
        )
        embed.add_field(name="🏦 ชื่อบัญชี", value="กฤติกา ตุล", inline=False)
        embed.set_image(url="https://media.discordapp.net/attachments/1486683482183958568/1551169408049872986/image.png?ex=6ab0fe96&is=6aafad16&hm=80656856521a1474f12fdd6b755a4d9957d05a9fb4d78a66dc88261dea891e71&=&format=webp&quality=lossless&width=1001&height=1299")
        embed.set_footer(text="13bux 🌸 • สแกน QR เพื่อชำระเงิน")
        
        await interaction.response.edit_message(embed=embed, view=PaymentView())
    
    async def account_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏦 ธนาคารกรุงศรี Krungsri",
            color=PINK_COLOR
        )
        embed.add_field(name="🏦 ชื่อบัญชี", value="กฤติกา ตุล", inline=False)
        embed.add_field(name="🔢 เลขบัญชี", value="**952-057409-3 **", inline=False)
        embed.set_footer(text="13bux 🌸")
        
        view = PaymentView()
        copy_btn = Button(label="📋 คัดลอกเลขบัญชี", style=discord.ButtonStyle.secondary, emoji="📋")
        
        async def copy_cb(i):
            await i.response.send_message("```9520574093```", ephemeral=True)
        
        copy_btn.callback = copy_cb
        view.add_item(copy_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)

@bot.command(name="qr")
async def payment_cmd(ctx):
    embed = discord.Embed(
        title="🌸 เลือกช่องทางชำระเงิน",
        description="กรุณาเลือกช่องทางการชำระเงินด้านล่าง",
        color=PINK_COLOR
    )
    embed.set_footer(text="13bux 🌸")
    embed.set_thumbnail(url=THUMBNAIL_URL)
    
    view = PaymentView()
    await ctx.send(embed=embed, view=view)
    
    try:
        await ctx.message.delete()
    except:
        pass
        

# ============ SIMPLE CALCULATOR COMMANDS ============
@bot.command()
async def gp(ctx, *, expr):
    global gamepass_rate
    try:
        expr_clean = expr.replace(",", "").lower().replace("x", "*").replace("÷", "/").replace(" ", "")
        robux = int(eval(expr_clean))
        
        rate = get_gamepass_rate(robux)
        price = robux / rate
        price_int = round_price(price)
        
        await ctx.send(f"🎮 Gamepass {format_number(robux)} Robux = **{format_number(price_int)} บาท** (เรท {rate})")
    except:
        await ctx.send("❌ กรุณากรอกตัวเลขให้ถูกต้อง เช่น 500 หรือ 100+200", delete_after=5)

@bot.command()
async def gpb(ctx, *, expr):
    global gamepass_rate
    try:
        expr_clean = expr.replace(",", "").replace(" ", "")
        baht = float(eval(expr_clean))
        
        robux_amount = int(baht * gamepass_rate)
        
        await ctx.send(f"🎮 {format_number(int(baht))} บาท = **{format_number(robux_amount)} Robux** (Gamepass เรท {gamepass_rate})")
    except:
        await ctx.send("❌ กรุณากรอกตัวเลขให้ถูกต้อง เช่น 500 หรือ 100+200", delete_after=5)

    
# ============ BACKGROUND TASKS ============
@tasks.loop(minutes=1)
async def update_presence():
    await bot.change_presence(activity=discord.Game(name="🌸13bux รับกดเกมพาส🌸"))

@tasks.loop(minutes=5)
async def save_data():
    await save_all_data()

@tasks.loop(seconds=15)
async def save_data_frequent():
    await save_all_data()
    print(f"✅ Auto-save at {get_thailand_time().strftime('%H:%M:%S')}")

@tasks.loop(hours=1)
async def hourly_backup():
    backup_user_levels()
    print(f"✅ Hourly backup created at {get_thailand_time().strftime('%H:%M:%S')}")

# ============ SIGNAL HANDLERS ============
def signal_handler(signum, frame):
    print(f"\n⚠️ Received signal {signum}, saving data...")
    save_all_data_sync()
    backup_user_levels()
    print("✅ Data saved! Exiting...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ============ EVENT HANDLERS ============
@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user} (ID: {bot.user.id})")
    
    await bot.change_presence(activity=discord.Game(name="🌸13bux รับกดเกมพาส🌸"))
    
    print("\n📝 Registered prefix commands:")
    for cmd in bot.commands:
        print(f"   - !{cmd.name}")
    
    print("\n🔧 Slash commands will be synced...")
    
    print(f"\n📁 DATA_DIR: {DATA_DIR}")
    print(f"📁 Directory exists: {os.path.exists(DATA_DIR)}")
    
    if os.path.exists(user_levels_file):
        file_size = os.path.getsize(user_levels_file)
        print(f"📊 user_levels.json exists, size: {file_size} bytes")
    else:
        print(f"📊 user_levels.json does not exist yet")
    
    notes_channel = bot.get_channel(NOTES_LOG_CHANNEL_ID)
    if notes_channel:
        print(f"✅ Notes log channel found: {notes_channel.name} (ID: {NOTES_LOG_CHANNEL_ID})")
    else:
        print(f"⚠️ Notes log channel not found with ID: {NOTES_LOG_CHANNEL_ID}")
    
    notes_button_channel = bot.get_channel(NOTES_BUTTON_CHANNEL_ID)
    if notes_button_channel:
        print(f"✅ Notes button channel found: {notes_button_channel.name} (ID: {NOTES_BUTTON_CHANNEL_ID})")
    else:
        print(f"⚠️ Notes button channel not found with ID: {NOTES_BUTTON_CHANNEL_ID}")
    
    # Verify sales log channel
    sales_log = bot.get_channel(SALES_LOG_CHANNEL_ID)
    if sales_log:
        print(f"✅ Sales log channel found: {sales_log.name} (ID: {SALES_LOG_CHANNEL_ID})")
    else:
        print(f"❌ Sales log channel NOT found with ID: {SALES_LOG_CHANNEL_ID}")
    
    try:
        print("🔄 กำลัง sync slash commands...")
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
        for cmd in synced:
            print(f"   - /{cmd.name}")
        bot.commands_synced = True
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
    
    update_presence.start()
    save_data.start()
    save_data_frequent.start()
    hourly_backup.start()
    update_credit_channel_task.start()
    
    await update_credit_channel_name()
    await update_channel_name()
    await update_rate_channel_name()
    await update_main_channel()
    await update_notes_channel()
    
    total_sp = sum(data["sp"] for data in user_levels.values())
    print(f"\n📊 Loaded SP data: {len(user_levels)} users, total {format_number(total_sp)} SP")
    print("\n🎯 บอทพร้อมใช้งาน!")

@bot.event
async def on_member_join(member):
    try:
        welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if welcome_channel:
            welcome_text = random.choice(WELCOME_MESSAGES)
            welcome_message = welcome_text.format(member.mention)
            await welcome_channel.send(welcome_message)
            print(f"✅ Sent welcome message for {member.name}")
            
            if str(member.id) not in user_levels:
                user_levels[str(member.id)] = {"sp": 0, "total_robux": 0}
                save_json(user_levels_file, user_levels)
    except Exception as e:
        print(f"❌ Error sending welcome message: {e}")

# ============ MAIN ============
if __name__ == "__main__":
    keep_alive()
    
    print("⏳ รอ 30 วินาทีก่อนเริ่มบอท...")
    time.sleep(30)
    
    token = os.getenv("TOKEN")
    if not token:
        print("❌ ไม่พบ TOKEN ใน environment variables")
        exit(1)
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        traceback.print_exc()
