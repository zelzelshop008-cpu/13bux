import os, datetime, discord, re, asyncio, json, traceback, time, aiohttp, logging
import random
import math
import signal
import sys
import shutil
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput, Select
from discord import app_commands
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
    sys.exit(1)
else:
    print(f"✅ TOKEN found (length: {len(token)})")

logging.getLogger('werkzeug').setLevel(logging.ERROR)

try:
    import pytz
    def get_thailand_time(): return dt.now(pytz.timezone('Asia/Bangkok'))
except:
    def get_thailand_time(): return dt.utcnow() + datetime.timedelta(hours=7)

intents = discord.Intents.all()
intents.message_content = True
intents.members = True

# Global variables
gamepass_rate = 7
gamepass_rate_high = 7
gamepass_threshold = 3999
shop_open = True
gamepass_stock = 20000

daily_robux_sold = 0
daily_sales_date = get_thailand_time().strftime("%Y%m%d")

# Channel IDs
MAIN_CHANNEL_ID = 1475342278976606229
SALES_LOG_CHANNEL_ID = 1475344141419417612
CREDIT_CHANNEL_ID = 1475343873684406353
DELIVERED_CATEGORY_ID = 1475345768037482662
ARCHIVED_CATEGORY_ID = 1485235427500753059
BUYER_ROLE_ID = 1475346221605588992
WELCOME_CHANNEL_ID = 1475344769679888455
SUSHI_GAMEPASS_CATEGORY_ID = 1475342278976606228
ANONYMOUS_USER_ROLE_ID = 1486352633290821673
ADMIN_ROLE_ID = 1486330338539077713

THUMBNAIL_URL = "https://media.discordapp.net/attachments/1535881071403601970/1551140774773530755/Screenshot_2026-09-20_143848.png?ex=6ab0e3eb&is=6aaf926b&hm=c2dd13e974250458a77299eda0bb56a8fd7ae491c19683307863e6f89da94dd4&=&format=webp&quality=lossless&width=1299&height=1299"

WELCOME_MESSAGES = [
    "ยินดีต้อนรับ {} สู่ร้าน 13bux 🌸",
    "สวัสดีค่ะ {} ยินดีต้อนรับนะคะ 🌸",
    "ยินดีต้อนรับนะคะ {} 🌸",
    "สวัสดีค่ะ ยินดีต้อนรับ {} ค่า 🌸"
]

# File paths
DATA_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)

user_data_file = os.path.join(DATA_DIR, "user_data.json")
ticket_transcripts_file = os.path.join(DATA_DIR, "ticket_transcripts.json")
ticket_counter_file = os.path.join(DATA_DIR, "ticket_counter.json")
ticket_robux_data_file = os.path.join(DATA_DIR, "ticket_robux_data.json")
ticket_customer_data_file = os.path.join(DATA_DIR, "ticket_customer_data.json")
stock_file = os.path.join(DATA_DIR, "stock_values.json")
ticket_buyer_data_file = os.path.join(DATA_DIR, "ticket_buyer_data.json")
daily_sales_file = os.path.join(DATA_DIR, "daily_sales.json")

# In-memory data structures
user_data = {}
ticket_transcripts = {}
ticket_robux_data = {}
ticket_customer_data = {}
ticket_buyer_data = {}
ticket_activity = {}
ticket_removal_tasks = {}
ticket_anonymous_mode = {}
ticket_counter = {"counter": 1, "date": get_thailand_time().strftime("%d%m%y")}
ticket_archived_timers = {}

# ============ DAILY SALES FUNCTIONS ============
def load_daily_sales():
    global daily_robux_sold, daily_sales_date
    try:
        if os.path.exists(daily_sales_file):
            with open(daily_sales_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                daily_robux_sold = data.get("robux_sold", 0)
                daily_sales_date = data.get("date", get_thailand_time().strftime("%Y%m%d"))
        else:
            daily_robux_sold = 0
            daily_sales_date = get_thailand_time().strftime("%Y%m%d")
            save_daily_sales()
    except Exception as e:
        print(f"❌ Error loading daily sales: {e}")
        daily_robux_sold = 0
        daily_sales_date = get_thailand_time().strftime("%Y%m%d")

def save_daily_sales():
    try:
        data = {"robux_sold": daily_robux_sold, "date": daily_sales_date}
        save_json(daily_sales_file, data)
    except Exception as e:
        print(f"❌ Error saving daily sales: {e}")

async def add_daily_robux(amount):
    global daily_robux_sold, daily_sales_date
    daily_robux_sold += amount
    save_daily_sales()

def reset_daily_robux():
    global daily_robux_sold, daily_sales_date
    daily_robux_sold = 0
    daily_sales_date = get_thailand_time().strftime("%Y%m%d")
    save_daily_sales()

# ============ JSON FUNCTIONS ============
def load_json(file, default):
    try:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    except Exception as e:
        print(f"❌ Error loading {file}: {e}")
        return default

def save_json(file, data):
    try:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving {file}: {e}")
        return False

def load_stock_values():
    global gamepass_stock, gamepass_rate, gamepass_rate_high, gamepass_threshold, shop_open
    stock_data = load_json(stock_file, {})
    if stock_data:
        gamepass_stock = stock_data.get("gamepass_stock", 20000)
        gamepass_rate = stock_data.get("gamepass_rate", 6.5)
        gamepass_rate_high = stock_data.get("gamepass_rate_high", 6.7)
        gamepass_threshold = stock_data.get("gamepass_threshold", 4000)
        shop_open = stock_data.get("shop_open", True)

def save_stock_values():
    stock_data = {
        "gamepass_stock": gamepass_stock,
        "gamepass_rate": gamepass_rate,
        "gamepass_rate_high": gamepass_rate_high,
        "gamepass_threshold": gamepass_threshold,
        "shop_open": shop_open,
    }
    save_json(stock_file, stock_data)

async def save_all_data():
    save_json(user_data_file, user_data)
    save_json(ticket_transcripts_file, ticket_transcripts)
    save_json(ticket_robux_data_file, ticket_robux_data)
    save_json(ticket_customer_data_file, ticket_customer_data)
    save_json(ticket_buyer_data_file, ticket_buyer_data)
    save_stock_values()
    return True

def load_all_data():
    global user_data, ticket_transcripts, ticket_robux_data, ticket_customer_data, ticket_buyer_data, ticket_counter
    user_data = load_json(user_data_file, {})
    ticket_transcripts = load_json(ticket_transcripts_file, {})
    ticket_robux_data = load_json(ticket_robux_data_file, {})
    ticket_customer_data = load_json(ticket_customer_data_file, {})
    ticket_buyer_data = load_json(ticket_buyer_data_file, {})
    ticket_counter = load_json(ticket_counter_file, {"counter": 1, "date": get_thailand_time().strftime("%d%m%y")})
    load_stock_values()
    load_daily_sales()

# ============ HELPER FUNCTIONS ============
def get_gamepass_rate(robux_amount):
    if robux_amount > gamepass_threshold:
        return gamepass_rate_high
    return gamepass_rate

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

# ============ VIEW CLASSES ============
class GamepassTicketModal(Modal, title="📋 แบบฟอร์มกดเกมพาส"):
    map_name = TextInput(label="🗺 ชื่อแมพที่จะกด?", placeholder="ชื่อแมพ เช่น Sushi Fruits", required=True)
    gamepass_name = TextInput(label="💸 ชื่อเกมพาส?", placeholder="ชื่อเกมพาส เช่น VIP + x2 เงิน", required=True)
    robux_amount = TextInput(label="🎟 ราคาของเกมพาสเท่าไหร่บ้าง?", placeholder="เช่น 300 / 100+100+100 / 100x3", required=True)
    async def on_submit(self, i):
        try:
            if is_user_always_anonymous(i.user):
                ticket_anonymous_mode[str(i.channel.id)] = True
                ticket_customer_data[str(i.channel.id)] = "ไม่ระบุตัวตน"
                save_json(ticket_customer_data_file, ticket_customer_data)
            else:
                ticket_anonymous_mode[str(i.channel.id)] = False
            expr = self.robux_amount.value.lower().replace("x", "*").replace("÷", "/").replace(" ", "")
            if not re.match(r"^[\d\s\+\-\*\/\(\)]+$", expr):
                await i.response.send_message("❌ กรุณาใส่เฉพาะตัวเลข และเครื่องหมาย + - * / x ÷ ()", ephemeral=True)
                return
            robux = int(eval(expr))
            rate = get_gamepass_rate(robux)
            price = robux / rate
            price_int = round_price(price)
            embed = discord.Embed(title="📨 รายละเอียดการสั่งซื้อ", color=0x00FF99)
            embed.add_field(name="🗺️ ชื่อแมพ", value=self.map_name.value, inline=False)
            embed.add_field(name="🎟 เกมพาส", value=self.gamepass_name.value, inline=False)
            embed.add_field(name="💸 ราคาโรบัค", value=f"{format_number(robux)}", inline=True)
            embed.add_field(name="💰 ราคา", value=f"{format_number(price_int)} บาท", inline=True)
            if robux > gamepass_threshold:
                embed.add_field(name="⚡ เรท", value=f"{rate} (มากกว่า {gamepass_threshold} โรบัค)", inline=True)
            embed.set_footer(text="แอดมินจะตอบกลับเร็วๆนี้")
            view = View(timeout=300)
            cancel_btn = Button(label="❌ ยกเลิกสินค้า", style=discord.ButtonStyle.danger)
            async def cancel_cb(interaction):
                await interaction.response.send_message("❌ คำสั่งซื้อถูกยกเลิก")
                await interaction.message.delete()
            cancel_btn.callback = cancel_cb
            view.add_item(cancel_btn)
            await i.response.send_message(embed=embed, view=view)
        except Exception as e:
            await i.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

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
            if not delivery_image:
                await i.response.send_message("❌ ผู้ส่งสินค้าต้องแนบหลักฐานการส่งสินค้าก่อน !", ephemeral=True)
                return
            confirm_view = View(timeout=300)
            confirm_btn = Button(label="ยืนยัน", style=discord.ButtonStyle.success, emoji="✅")
            edit_btn = Button(label="แก้ไข", style=discord.ButtonStyle.secondary, emoji="✏️")
            async def confirm_cb(interaction):
                try:
                    self.delivered = True
                    if self.buyer:
                        ticket_customer_data[str(self.channel.id)] = self.buyer.name
                        save_json(ticket_customer_data_file, ticket_customer_data)
                        if self.robux_amount:
                            await add_daily_robux(self.robux_amount)
                    receipt_color = 0xFFA500
                    anonymous_mode = ticket_anonymous_mode.get(str(self.channel.id), False)
                    buyer_display = "ไม่ระบุตัวตน" if anonymous_mode else (self.buyer.mention if self.buyer else "ไม่ทราบ")
                    if not self.receipt_sent:
                        self.receipt_sent = True
                        log_channel = bot.get_channel(SALES_LOG_CHANNEL_ID)
                        if log_channel:
                            log_embed = discord.Embed(title=f"🌸 ใบเสร็จการสั่งซื้อ ({self.product_type}) 🌸", color=receipt_color)
                            log_embed.add_field(name="😊 ผู้ซื้อ", value=buyer_display, inline=False)
                            log_embed.add_field(name="💸 จำนวนโรบัค", value=f"{format_number(self.robux_amount)}", inline=True)
                            price_int = round_price(self.price)
                            log_embed.add_field(name="💰 ราคาตามเรท", value=f"{format_number(price_int)} บาท", inline=True)
                            if delivery_image:
                                log_embed.set_image(url=delivery_image)
                            log_embed.set_footer(text=f"จัดส่งสินค้าสำเร็จ 🤗 • {get_thailand_time().strftime('%d/%m/%y, %H:%M')}")
                            await log_channel.send(embed=log_embed)
                        if self.buyer and not anonymous_mode and not self.is_reorder:
                            try:
                                dm_embed = discord.Embed(
                                    title=f"🧾 ใบเสร็จการซื้อสินค้า ({self.product_type})",
                                    description="ขอบคุณที่ใช้บริการ 13bux นะคะ 🌸",
                                    color=receipt_color
                                )
                                dm_embed.add_field(name="📦 สินค้า", value=self.product_type, inline=True)
                                dm_embed.add_field(name="💸 จำนวนโรบัค", value=f"{format_number(self.robux_amount)}", inline=True)
                                price_int = round_price(self.price)
                                dm_embed.add_field(name="💰 ราคา", value=f"{format_number(price_int)} บาท", inline=True)
                                if delivery_image:
                                    dm_embed.set_image(url=delivery_image)
                                dm_embed.add_field(name="📝 หมายเหตุ", value="หากมีปัญหากรุณาติดต่อแอดมินในเซิร์ฟ", inline=False)
                                dm_embed.set_footer(text="13bux • ขอบคุณที่ใช้บริการ💖")
                                await self.buyer.send(embed=dm_embed)
                            except Exception as e:
                                print(f"⚠️ ไม่สามารถส่ง DM ถึง {self.buyer.name}: {e}")
                    try:
                        await interaction.response.edit_message(content="✅ บันทึกการส่งสินค้าเรียบร้อย", embed=None, view=None)
                    except:
                        pass
                except Exception as e:
                    print(f"Error in confirm_cb: {e}")
                    try:
                        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)
                    except:
                        pass
            async def edit_cb(interaction):
                await interaction.response.send_message("📝 กรุณาแนบหลักฐานการส่งสินค้า แล้วกดปุ่ม 'ส่งสินค้าแล้ว ✅' อีกครั้ง", ephemeral=True)
            confirm_btn.callback = confirm_cb
            edit_btn.callback = edit_cb
            confirm_view.add_item(confirm_btn)
            confirm_view.add_item(edit_btn)
            embed = discord.Embed(title="📦 ยืนยันการส่งสินค้า", description="ยืนยันหลักฐานการส่งสินค้านี้หรือไม่?", color=0x00FF00)
            embed.set_image(url=delivery_image)
            await i.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
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
    async def setup_hook(self):
        await self.tree.sync()
    async def close(self):
        print("\n⚠️ กำลังปิดระบบอย่างปลอดภัย...")
        await save_all_data()
        print("👋 ลาก่อน!")
        await super().close()

bot = MyBot()

# ============ TICKET HELPER FUNCTIONS ============
def cancel_removal(channel_id):
    if str(channel_id) in ticket_removal_tasks:
        ticket_removal_tasks[str(channel_id)].cancel()
        del ticket_removal_tasks[str(channel_id)]
        return True
    return False

async def reset_timer(channel, buyer):
    cancel_removal(channel.id)

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
        pass
    finally:
        if str(channel.id) in ticket_archived_timers:
            del ticket_archived_timers[str(channel.id)]

async def auto_delete_ticket_after_delay(channel, delay_seconds):
    try:
        await asyncio.sleep(delay_seconds)
        if not channel or channel not in channel.guild.channels:
            return
        await save_ticket_transcript(channel, "ระบบอัตโนมัติ (1 ชั่วโมง)")
        await asyncio.sleep(2)
        await channel.delete()
    except Exception as e:
        print(f"❌ Error in auto_delete_ticket_after_delay: {e}")

async def update_channel_name():
    try:
        channel = bot.get_channel(MAIN_CHANNEL_ID)
        if channel:
            if shop_open:
                new_name = "〔🟢เปิด〕กดสั่งซื้อห้องนี้"
            else:
                new_name = "〔🔴ปิดชั่วคราว〕"
            if channel.name != new_name:
                await bot.channel_edit_rate_limiter.acquire()
                await channel.edit(name=new_name)
    except Exception as e:
        print(f"❌ Error updating channel name: {e}")

async def update_main_channel():
    """Update channel name only (shop embed status removed)."""
    try:
        await update_channel_name()
    except Exception as e:
        print(f"❌ Error updating main channel: {e}")
        traceback.print_exc()

async def handle_open_ticket(interaction, category_name, stock_type):
    global gamepass_stock
    try:
        if stock_type == "gamepass" and gamepass_stock <= 0:
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
        if stock_type == "gamepass":
            category = discord.utils.get(interaction.guild.categories, id=SUSHI_GAMEPASS_CATEGORY_ID)
            if not category:
                category = discord.utils.get(interaction.guild.categories, name=category_name)
        if not category:
            await interaction.response.send_message(f"❌ ไม่พบหมวดหมู่ {category_name}", ephemeral=True)
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
        if stock_type == "gamepass":
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
        embed = discord.Embed(
            title="🌸13bux🌸",
            color=0x00FF99
        )
        embed.description = ""
        embed.add_field(name="👤 ผู้ซื้อ", value=interaction.user.mention, inline=False)
        if stock_type == "gamepass":
            embed.add_field(
                name="🎮 บริการกดเกมพาส",
                value=f"📦 โรบัคคงเหลือ: **{format_number(gamepass_stock)}**\n💰 เรท: {gamepass_rate} (ปกติ) | {gamepass_rate_high} (>{gamepass_threshold} โรบัค)",
                inline=False
            )
        embed.set_footer(text="13bux")
        embed.set_thumbnail(url=THUMBNAIL_URL)
        ticket_view = View(timeout=None)
        if stock_type == "gamepass":
            form_btn = Button(label="📝 กรอกแบบฟอร์มเกมพาส", style=discord.ButtonStyle.primary, emoji="📝")
            async def form_callback(i):
                if i.channel.id == channel.id:
                    modal = GamepassTicketModal()
                    await i.response.send_modal(modal)
                else:
                    await i.response.send_message("❌ คุณไม่สามารถใช้ปุ่มนี้ในช่องอื่นได้", ephemeral=True)
            form_btn.callback = form_callback
        ticket_view.add_item(form_btn)
        await channel.send(embed=embed, view=ticket_view)
        if admin_role:
            admin_mention = admin_role.mention
            await channel.send(content=f"{admin_role.mention} มีตั๋วใหม่!", delete_after=10)
        else:
            admin_mention = ""
        await channel.send(f"# สนใจซื้ออะไรแจ้งแอดมินได้เลยค่ะ 💖 {admin_mention}")
    except Exception as e:
        print(f"❌ Error opening ticket: {e}")
        traceback.print_exc()
        try:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)
        except:
            pass

async def save_ticket_transcript(channel, action_by=None, robux_amount=None, customer_name=None):
    try:
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
                return False
        if channel.category and channel.category.id == DELIVERED_CATEGORY_ID:
            return True
        await channel.edit(category=delivered_category)
        await schedule_auto_delete_after_delivered(channel, 3600)
        return True
    except Exception as e:
        print(f"❌ Error moving to delivered category: {e}")
        return False

async def move_to_original_category(channel, product_type):
    try:
        if not channel:
            return False
        guild = channel.guild
        target_category = None
        if product_type == "gamepass":
            target_category = guild.get_channel(SUSHI_GAMEPASS_CATEGORY_ID)
            if not target_category:
                target_category = discord.utils.get(guild.categories, id=SUSHI_GAMEPASS_CATEGORY_ID)
        if not target_category:
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
        await channel.edit(category=target_category)
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
            return True
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
            return False
        if buyer_role not in buyer.roles:
            await buyer.add_roles(buyer_role)
            return True
        return False
    except Exception as e:
        print(f"❌ Error adding buyer role: {e}")
        return False

# ============ CREDIT CHANNEL FUNCTIONS ============
async def update_credit_channel_name():
    try:
        credit_channel = bot.get_channel(CREDIT_CHANNEL_ID)
        if not credit_channel:
            return
