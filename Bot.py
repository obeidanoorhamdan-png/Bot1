# ═══════════════════════════════════════════════════════════════════
# 🤖 Worm GPT — الكود الكامل (الجزء 1/2)
# 📦 pip install -r requirements.txt
# ⚠️ لا تشغّل الآن — انسخ الجزء 2 بعده
# ═══════════════════════════════════════════════════════════════════

import os
import logging
import asyncio
import json
import secrets
import threading
import random
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

import aiosqlite
import requests
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes
)

# ═══════════════════════════════════════════════════════════════════
# ⚙️ الإعدادات
# ═══════════════════════════════════════════════════════════════════

BOT_TOKEN       = os.environ.get("BOT_TOKEN", "8860603341:AAG3eTZlDPA5TPIT0S25lAOWcXhb2s9NWag")
SUPER_ADMIN_ID  = int(os.environ.get("SUPER_ADMIN_ID", "6207431030"))
API_URL         = os.environ.get("API_URL", "https://w0rmgpt.lovable.app/api/public/subscriptions")
SITE_URL        = os.environ.get("SITE_URL", "https://w0rmgpt.lovable.app/")

CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "engtopwln")
CHANNEL_URL      = f"https://t.me/{CHANNEL_USERNAME}"

INITIAL_API_KEY       = os.environ.get("INITIAL_API_KEY", "wsk_0c4d9994396f4b27a464dfc1c43e244be0fb58c6")
INITIAL_API_KEY_LABEL = os.environ.get("INITIAL_API_KEY_LABEL", "المفتاح الأساسي")

POINTS_INVITE = int(os.environ.get("POINTS_INVITE", "1"))
POINTS_DAILY  = int(os.environ.get("POINTS_DAILY", "1"))
MIN_TRANSFER  = int(os.environ.get("MIN_TRANSFER", "1"))

DROPS_REFRESH_INTERVAL = int(os.environ.get("DROPS_REFRESH_INTERVAL", "900"))
MARKETPLACE_FEE = int(os.environ.get("MARKETPLACE_FEE", "5"))

if os.path.exists("/data"):
    DB_PATH = "/data/bot_data.db"
else:
    DB_PATH = os.environ.get("DB_PATH", "bot_data.db")

# ═══════════════════════════════════════════════════════════════════
# 💎 الخطط
# ═══════════════════════════════════════════════════════════════════

SUBSCRIPTION_TYPES = {
    "plus": {"name": "⭐ بلس", "emoji": "⭐", "api_plan": "plus",
             "description": "اشتراك أساسي", "prices": {7: 5, 30: 15, 90: 40, 365: 120}},
    "pro": {"name": "💎 برو", "emoji": "💎", "api_plan": "pro",
            "description": "اشتراك متقدم", "prices": {7: 8, 30: 25, 90: 65, 365: 200}},
    "premium": {"name": "👑 بريميوم", "emoji": "👑", "api_plan": "premium",
                "description": "اشتراك كامل", "prices": {7: 15, 30: 45, 90: 120, 365: 380}},
}

QUANTITY_DISCOUNTS = {1: 0, 2: 5, 3: 10, 5: 15, 10: 20, 20: 25}

VIP_TIERS = {
    "bronze":   {"name": "🥉 برونزي", "min_points": 0,    "discount": 0,  "emoji": "🥉"},
    "silver":   {"name": "🥈 فضي",    "min_points": 100,  "discount": 10, "emoji": "🥈"},
    "gold":     {"name": "🥇 ذهبي",   "min_points": 500,  "discount": 20, "emoji": "🥇"},
    "platinum": {"name": "💎 بلاتيني", "min_points": 2000, "discount": 30, "emoji": "💎"},
}

def get_vip_tier(points):
    tier = "bronze"
    for key, info in VIP_TIERS.items():
        if points >= info["min_points"]:
            tier = key
    return tier

def calculate_price(unit_price, quantity):
    subtotal = unit_price * quantity
    discount_pct = 0
    for threshold, pct in sorted(QUANTITY_DISCOUNTS.items()):
        if quantity >= threshold:
            discount_pct = pct
    total = subtotal * (100 - discount_pct) // 100 if discount_pct > 0 else subtotal
    return total, subtotal, discount_pct

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ═══════════════════════════════════════════════════════════════════
# 🌐 HTTP Server
# ═══════════════════════════════════════════════════════════════════

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health", "/ping"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("Worm GPT is alive!".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
    def log_message(self, format, *args):
        pass

def run_http_server():
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"🌐 HTTP server على المنفذ {port}")
    server.serve_forever()

def start_http_server():
    threading.Thread(target=run_http_server, daemon=True).start()

# ═══════════════════════════════════════════════════════════════════
# 💾 قاعدة البيانات
# ═══════════════════════════════════════════════════════════════════

class Database:
    def __init__(self, path=DB_PATH):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
                    points INTEGER DEFAULT 0, total_points_earned INTEGER DEFAULT 0,
                    total_points_spent INTEGER DEFAULT 0,
                    invited_by INTEGER, invite_code TEXT UNIQUE,
                    last_daily_bonus TEXT, daily_streak INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'ar',
                    theme TEXT DEFAULT 'auto',
                    notifications TEXT DEFAULT '{}',
                    vip_tier TEXT DEFAULT 'bronze',
                    joined_at TEXT
                );
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, key_value TEXT NOT NULL,
                    label TEXT, is_active INTEGER DEFAULT 0, created_at TEXT,
                    created_by INTEGER, last_used TEXT,
                    success_count INTEGER DEFAULT 0, fail_count INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                    code TEXT, plan TEXT, actual_plan TEXT, days INTEGER, max_uses INTEGER,
                    uses INTEGER DEFAULT 0, status TEXT DEFAULT 'active',
                    created_at TEXT, expires_at TEXT,
                    points_spent INTEGER DEFAULT 0, api_response TEXT,
                    source TEXT DEFAULT 'purchase'
                );
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER UNIQUE NOT NULL, title TEXT, username TEXT,
                    chat_type TEXT, added_by INTEGER, added_at TEXT,
                    is_active INTEGER DEFAULT 1, is_primary INTEGER DEFAULT 0,
                    can_post INTEGER DEFAULT 0, can_edit INTEGER DEFAULT 0,
                    last_used TEXT, total_drops INTEGER DEFAULT 0,
                    total_claims INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS drops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT UNIQUE NOT NULL, plan TEXT NOT NULL, days INTEGER NOT NULL,
                    drop_type TEXT DEFAULT 'normal',
                    conditions TEXT DEFAULT '{}',
                    next_drop_id INTEGER, parent_drop_id INTEGER,
                    max_winners INTEGER DEFAULT 1, current_winners INTEGER DEFAULT 0,
                    created_by INTEGER, created_at TEXT, expires_at TEXT,
                    claimed_by INTEGER, claimed_at TEXT, claim_code TEXT,
                    chat_id INTEGER, message_id INTEGER,
                    last_refreshed TEXT, retry_count INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1, is_deleted INTEGER DEFAULT 0,
                    total_views INTEGER DEFAULT 0, total_clicks INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS drop_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drop_id INTEGER NOT NULL, chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS drop_winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, drop_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL, rank INTEGER, code TEXT, won_at TEXT
                );
                CREATE TABLE IF NOT EXISTS egg_contents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, drop_id INTEGER NOT NULL,
                    prize_type TEXT NOT NULL, prize_value TEXT,
                    probability REAL DEFAULT 0,
                    is_won INTEGER DEFAULT 0, won_by INTEGER, won_at TEXT
                );
                CREATE TABLE IF NOT EXISTS vote_options (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, drop_id INTEGER NOT NULL,
                    option_key TEXT NOT NULL, option_name TEXT, votes_count INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, drop_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL, choice TEXT NOT NULL, voted_at TEXT,
                    UNIQUE(drop_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS auctions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drop_id INTEGER NOT NULL UNIQUE,
                    start_price INTEGER DEFAULT 0, min_increment INTEGER DEFAULT 5,
                    current_bid INTEGER DEFAULT 0, current_bidder INTEGER,
                    ends_at TEXT, is_closed INTEGER DEFAULT 0, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS bids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, auction_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL, amount INTEGER NOT NULL, bid_at TEXT
                );
                CREATE TABLE IF NOT EXISTS market_listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER NOT NULL,
                    subscription_id INTEGER NOT NULL, code TEXT, plan TEXT, days INTEGER,
                    price INTEGER, status TEXT DEFAULT 'active',
                    buyer_id INTEGER, created_at TEXT, sold_at TEXT, expires_at TEXT
                );
                CREATE TABLE IF NOT EXISTS market_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER NOT NULL,
                    seller_id INTEGER, buyer_id INTEGER, price INTEGER, fee INTEGER,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS points_drops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT UNIQUE NOT NULL, points INTEGER NOT NULL,
                    created_by INTEGER, created_at TEXT,
                    claimed_by INTEGER, claimed_at TEXT, is_active INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS force_join_cache (
                    user_id INTEGER PRIMARY KEY, checked_at TEXT, is_member INTEGER
                );
                CREATE TABLE IF NOT EXISTS scheduled_drops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan TEXT NOT NULL, days INTEGER NOT NULL,
                    interval_minutes INTEGER NOT NULL,
                    next_run TEXT, last_run TEXT,
                    is_active INTEGER DEFAULT 1, created_by INTEGER, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER,
                    action TEXT, details TEXT, created_at TEXT
                );
            """)
            await db.commit()

    # ─── المستخدمون ───
    async def get_user(self, user_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def register_user(self, user_id, username, first_name, invited_by=None):
        existing = await self.get_user(user_id)
        if existing:
            return existing, False
        async with aiosqlite.connect(self.path) as db:
            while True:
                code = secrets.token_urlsafe(6)[:8].upper()
                async with db.execute("SELECT 1 FROM users WHERE invite_code=?", (code,)) as cur:
                    if not await cur.fetchone():
                        break
            await db.execute("""INSERT INTO users (user_id, username, first_name, invited_by, invite_code, joined_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, username, first_name, invited_by, code, datetime.now().isoformat()))
            await db.commit()
        if invited_by:
            inviter = await self.get_user(invited_by)
            if inviter:
                await self.add_points(invited_by, POINTS_INVITE, "invite_reward", user_id)
        return await self.get_user(user_id), True

    async def add_points(self, user_id, amount, reason, ref_id=None):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""UPDATE users SET points = points + ?, total_points_earned = total_points_earned + ?
                WHERE user_id=?""", (amount, max(0, amount), user_id))
            await db.commit()

    async def deduct_points(self, user_id, amount):
        user = await self.get_user(user_id)
        if not user or user["points"] < amount:
            return False
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""UPDATE users SET points = points - ?, total_points_spent = total_points_spent + ?
                WHERE user_id=?""", (amount, amount, user_id))
            await db.commit()
        return True

    async def claim_daily_bonus(self, user_id):
        user = await self.get_user(user_id)
        if not user:
            return False, "المستخدم غير موجود"
        last = user.get("last_daily_bonus")
        streak = user.get("daily_streak", 0)
        if last:
            last_dt = datetime.fromisoformat(last)
            diff = datetime.now() - last_dt
            if diff < timedelta(hours=24):
                remaining = timedelta(hours=24) - diff
                return False, f"⏳ متبقٍ: {remaining.seconds // 3600}س {(remaining.seconds % 3600) // 60}د"
            streak = streak + 1 if diff < timedelta(hours=48) else 1
        else:
            streak = 1
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""UPDATE users SET last_daily_bonus=?, daily_streak=? WHERE user_id=?""",
                              (datetime.now().isoformat(), streak, user_id))
            await db.commit()
        bonus = POINTS_DAILY + min(streak - 1, 10)
        await self.add_points(user_id, bonus, "daily_bonus")
        return True, f"✅ حصلت على {bonus} نقطة! (سلسلة: {streak} 🔥)"

    async def set_ban(self, user_id, banned):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET is_banned=? WHERE user_id=?", (banned, user_id))
            await db.commit()

    async def set_language(self, user_id, lang):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
            await db.commit()

    async def set_theme(self, user_id, theme):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET theme=? WHERE user_id=?", (theme, user_id))
            await db.commit()

    async def set_notifications(self, user_id, notif_json):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET notifications=? WHERE user_id=?", (notif_json, user_id))
            await db.commit()

    async def update_vip_tier(self, user_id):
        user = await self.get_user(user_id)
        if user:
            new_tier = get_vip_tier(user["points"])
            if user.get("vip_tier") != new_tier:
                async with aiosqlite.connect(self.path) as db:
                    await db.execute("UPDATE users SET vip_tier=? WHERE user_id=?", (new_tier, user_id))
                    await db.commit()

    async def count_users(self):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cur:
                return (await cur.fetchone())[0]

    async def all_user_ids(self):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT user_id FROM users WHERE is_banned=0") as cur:
                return [r[0] for r in await cur.fetchall()]

    async def top_users(self, limit=10):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""SELECT user_id, username, first_name, points, vip_tier 
                FROM users ORDER BY points DESC LIMIT ?""", (limit,)) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_user_rank(self, user_id):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT points FROM users WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
                if not row: return 0, 0
                pts = row[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE points > ?", (pts,)) as cur:
                rank = (await cur.fetchone())[0] + 1
            async with db.execute("SELECT COUNT(*) FROM users") as cur:
                total = (await cur.fetchone())[0]
            return rank, total

    async def transfer_points(self, from_user, to_user, amount):
        from_u = await self.get_user(from_user)
        to_u = await self.get_user(to_user)
        if not from_u or not to_u: return False, "أحد المستخدمين غير موجود"
        if from_user == to_user: return False, "لا يمكن التحويل لنفسك"
        if from_u["points"] < amount: return False, "نقاطك غير كافية"
        if not await self.deduct_points(from_user, amount):
            return False, "فشل الخصم"
        await self.add_points(to_user, amount, "transfer_in", from_user)
        return True, "✅ تم التحويل"

    # ─── مفاتيح ───
    async def add_api_key(self, value, label, admin_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO api_keys (key_value, label, is_active, created_at, created_by)
                VALUES (?, ?, 0, ?, ?)""",
                (value, label, datetime.now().isoformat(), admin_id))
            await db.commit()

    async def get_active_key(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM api_keys WHERE is_active=1 LIMIT 1") as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def list_api_keys(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM api_keys ORDER BY id DESC") as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def set_active_key(self, key_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE api_keys SET is_active=0")
            await db.execute("UPDATE api_keys SET is_active=1 WHERE id=?", (key_id,))
            await db.commit()

    async def delete_api_key(self, key_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM api_keys WHERE id=?", (key_id,))
            await db.commit()

    async def record_key_result(self, key_id, success):
        async with aiosqlite.connect(self.path) as db:
            if success:
                await db.execute("UPDATE api_keys SET success_count=success_count+1, last_used=? WHERE id=?",
                                  (datetime.now().isoformat(), key_id))
            else:
                await db.execute("UPDATE api_keys SET fail_count=fail_count+1 WHERE id=?", (key_id,))
            await db.commit()

    # ─── اشتراكات ───
    async def save_subscription(self, user_id, data):
        async with aiosqlite.connect(self.path) as db:
            expires = (datetime.now() + timedelta(days=data["days"])).isoformat()
            await db.execute("""INSERT INTO subscriptions
                (user_id, code, plan, actual_plan, days, max_uses, status, created_at, expires_at, points_spent, api_response, source)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)""",
                (user_id, data.get("code", ""), data["plan"], data.get("actual_plan", data["plan"]),
                 data["days"], data.get("max_uses", 1),
                 datetime.now().isoformat(), expires, data.get("points_spent", 0),
                 json.dumps(data.get("response", {}), ensure_ascii=False),
                 data.get("source", "purchase")))
            await db.commit()

    async def get_user_subs(self, user_id, limit=20):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM subscriptions WHERE user_id=? ORDER BY id DESC LIMIT ?",
                                   (user_id, limit)) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_all_user_subs(self, user_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM subscriptions WHERE user_id=? ORDER BY id DESC",
                                   (user_id,)) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_last_sub_code(self, user_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT code, plan, days FROM subscriptions WHERE user_id=? ORDER BY id DESC LIMIT 1",
                                   (user_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def count_subscriptions(self):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT COUNT(*) FROM subscriptions") as cur:
                return (await cur.fetchone())[0]

    # ─── قنوات ───
    async def add_channel(self, chat_id, title, username, chat_type, added_by, can_post=0, can_edit=0):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT OR REPLACE INTO channels
                (chat_id, title, username, chat_type, added_by, added_at, is_active, can_post, can_edit)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (chat_id, title, username, chat_type, added_by,
                 datetime.now().isoformat(), can_post, can_edit))
            await db.commit()

    async def remove_channel(self, chat_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE channels SET is_active=0 WHERE chat_id=?", (chat_id,))
            await db.commit()

    async def list_channels(self, only_active=True):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            q = "SELECT * FROM channels"
            if only_active: q += " WHERE is_active=1"
            q += " ORDER BY is_primary DESC, added_at DESC"
            async with db.execute(q) as cur:
                return [dict(r) for r in await cur.fetchall()]

    # ─── دروبات ───
    async def create_drop(self, plan, days, admin_id, drop_type="normal",
                           conditions=None, max_winners=1, expires_at=None, metadata=None):
        token = secrets.token_urlsafe(10)[:12]
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO drops
                (token, plan, days, drop_type, conditions, max_winners, created_by, created_at, expires_at, is_active, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (token, plan, days, drop_type,
                 json.dumps(conditions or {}), max_winners,
                 admin_id, datetime.now().isoformat(), expires_at,
                 json.dumps(metadata or {})))
            await db.commit()
        return token

    async def get_drop(self, token):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM drops WHERE token=?", (token,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def get_drop_by_id(self, drop_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM drops WHERE id=?", (drop_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def claim_drop(self, token, user_id, code):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""UPDATE drops SET claimed_by=?, claimed_at=?, claim_code=?, is_active=0
                WHERE token=? AND is_active=1 AND claimed_by IS NULL""",
                (user_id, datetime.now().isoformat(), code, token))
            await db.commit()

    async def add_drop_winner(self, drop_id, user_id, rank, code):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO drop_winners (drop_id, user_id, rank, code, won_at)
                VALUES (?, ?, ?, ?, ?)""",
                (drop_id, user_id, rank, code, datetime.now().isoformat()))
            await db.execute("UPDATE drops SET current_winners = current_winners + 1 WHERE id=?",
                             (drop_id,))
            await db.commit()

    async def save_drop_message(self, drop_id, chat_id, message_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO drop_messages (drop_id, chat_id, message_id, created_at)
                VALUES (?, ?, ?, ?)""",
                (drop_id, chat_id, message_id, datetime.now().isoformat()))
            await db.commit()

    async def get_drop_messages(self, drop_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM drop_messages WHERE drop_id=?", (drop_id,)) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_drops_for_refresh(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM drops WHERE is_deleted=0 AND is_active=1") as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_admin_drops(self, limit=20):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM drops ORDER BY id DESC LIMIT ?", (limit,)) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def count_drops(self):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT COUNT(*) FROM drops") as cur:
                return (await cur.fetchone())[0]

    async def count_claimed_drops(self):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT COUNT(*) FROM drops WHERE claimed_by IS NOT NULL") as cur:
                return (await cur.fetchone())[0]

    # ─── دروبات نقاط ───
    async def create_points_drop(self, points, admin_id):
        token = secrets.token_urlsafe(10)[:12]
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO points_drops (token, points, created_by, created_at, is_active)
                VALUES (?, ?, ?, ?, 1)""",
                (token, points, admin_id, datetime.now().isoformat()))
            await db.commit()
        return token

    async def get_points_drop(self, token):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM points_drops WHERE token=?", (token,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def claim_points_drop(self, token, user_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""UPDATE points_drops SET claimed_by=?, claimed_at=?, is_active=0
                WHERE token=? AND is_active=1 AND claimed_by IS NULL""",
                (user_id, datetime.now().isoformat(), token))
            await db.commit()

    # ─── بيضاوي ───
    async def add_egg_content(self, drop_id, prize_type, prize_value, probability):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO egg_contents (drop_id, prize_type, prize_value, probability)
                VALUES (?, ?, ?, ?)""",
                (drop_id, prize_type, prize_value, probability))
            await db.commit()

    async def get_egg_contents(self, drop_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM egg_contents WHERE drop_id=? AND is_won=0", (drop_id,)) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def claim_egg_content(self, content_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""UPDATE egg_contents SET is_won=1, won_by=?, won_at=? WHERE id=?""",
                (user_id, datetime.now().isoformat(), content_id))
            await db.commit()

    # ─── تصويت ───
    async def create_vote_option(self, drop_id, option_key, option_name):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO vote_options (drop_id, option_key, option_name)
                VALUES (?, ?, ?)""", (drop_id, option_key, option_name))
            await db.commit()

    async def get_vote_options(self, drop_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM vote_options WHERE drop_id=?", (drop_id,)) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def cast_vote(self, drop_id, user_id, choice):
        async with aiosqlite.connect(self.path) as db:
            try:
                await db.execute("""INSERT INTO votes (drop_id, user_id, choice, voted_at)
                    VALUES (?, ?, ?, ?)""",
                    (drop_id, user_id, choice, datetime.now().isoformat()))
                await db.execute("""UPDATE vote_options SET votes_count = votes_count + 1
                    WHERE drop_id=? AND option_key=?""", (drop_id, choice))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def has_voted(self, drop_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT 1 FROM votes WHERE drop_id=? AND user_id=?",
                                   (drop_id, user_id)) as cur:
                return bool(await cur.fetchone())

    # ─── مزاد ───
    async def create_auction(self, drop_id, start_price, min_increment, ends_at):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO auctions
                (drop_id, start_price, min_increment, ends_at, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (drop_id, start_price, min_increment, ends_at, datetime.now().isoformat()))
            await db.commit()

    async def get_auction_by_drop(self, drop_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM auctions WHERE drop_id=?", (drop_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def place_bid(self, auction_id, user_id, amount):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO bids (auction_id, user_id, amount, bid_at)
                VALUES (?, ?, ?, ?)""",
                (auction_id, user_id, amount, datetime.now().isoformat()))
            await db.execute("""UPDATE auctions SET current_bid=?, current_bidder=?
                WHERE id=?""", (amount, user_id, auction_id))
            await db.commit()

    async def get_active_auctions(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM auctions WHERE is_closed=0") as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def close_auction(self, auction_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE auctions SET is_closed=1 WHERE id=?", (auction_id,))
            await db.commit()

    # ─── سوق ───
    async def create_listing(self, seller_id, subscription_id, code, plan, days, price):
        async with aiosqlite.connect(self.path) as db:
            expires = (datetime.now() + timedelta(days=7)).isoformat()
            cursor = await db.execute("""INSERT INTO market_listings
                (seller_id, subscription_id, code, plan, days, price, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (seller_id, subscription_id, code, plan, days, price,
                 datetime.now().isoformat(), expires))
            await db.commit()
            return cursor.lastrowid

    async def get_active_listings(self, limit=20):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""SELECT * FROM market_listings WHERE status='active'
                ORDER BY id DESC LIMIT ?""", (limit,)) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_listing(self, listing_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM market_listings WHERE id=?", (listing_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def buy_listing(self, listing_id, buyer_id):
        listing = await self.get_listing(listing_id)
        if not listing or listing["status"] != "active":
            return False, "غير متاح"
        if listing["seller_id"] == buyer_id:
            return False, "لا يمكنك شراء منتجك"
        buyer = await self.get_user(buyer_id)
        if not buyer or buyer["points"] < listing["price"]:
            return False, "نقاطك غير كافية"
        if not await self.deduct_points(buyer_id, listing["price"]):
            return False, "فشل الخصم"
        fee = listing["price"] * MARKETPLACE_FEE // 100
        seller_amount = listing["price"] - fee
        await self.add_points(listing["seller_id"], seller_amount, "market_sale", listing_id)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""UPDATE market_listings SET status='sold', buyer_id=?, sold_at=?
                WHERE id=?""", (buyer_id, datetime.now().isoformat(), listing_id))
            await db.execute("""INSERT INTO market_transactions
                (listing_id, seller_id, buyer_id, price, fee, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (listing_id, listing["seller_id"], buyer_id, listing["price"],
                 fee, datetime.now().isoformat()))
            await db.commit()
        return True, listing["code"]

    async def cancel_listing(self, listing_id, seller_id):
        listing = await self.get_listing(listing_id)
        if not listing or listing["seller_id"] != seller_id:
            return False, "غير موجود"
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE market_listings SET status='cancelled' WHERE id=?", (listing_id,))
            await db.commit()
        return True, "✅ أُلغي"

    # ─── مجدولة ───
    async def create_scheduled_drop(self, plan, days, interval_minutes, admin_id):
        async with aiosqlite.connect(self.path) as db:
            next_run = (datetime.now() + timedelta(minutes=interval_minutes)).isoformat()
            cursor = await db.execute("""INSERT INTO scheduled_drops
                (plan, days, interval_minutes, next_run, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (plan, days, interval_minutes, next_run, admin_id, datetime.now().isoformat()))
            await db.commit()
            return cursor.lastrowid

    async def get_due_scheduled_drops(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            now = datetime.now().isoformat()
            async with db.execute("""SELECT * FROM scheduled_drops
                WHERE is_active=1 AND next_run <= ?""", (now,)) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def update_scheduled_next_run(self, sched_id, next_run):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""UPDATE scheduled_drops SET next_run=?, last_run=?
                WHERE id=?""", (next_run, datetime.now().isoformat(), sched_id))
            await db.commit()

    # ─── force join ───
    async def get_force_join_cache(self, user_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM force_join_cache WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def save_force_join_cache(self, user_id, is_member):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT OR REPLACE INTO force_join_cache
                (user_id, checked_at, is_member) VALUES (?, ?, ?)""",
                (user_id, datetime.now().isoformat(), 1 if is_member else 0))
            await db.commit()

    async def delete_force_join_cache(self, user_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM force_join_cache WHERE user_id=?", (user_id,))
            await db.commit()

    # ─── سجلات ───
    async def log_admin(self, admin_id, action, details):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO admin_logs (admin_id, action, details, created_at)
                VALUES (?, ?, ?, ?)""", (admin_id, action, details, datetime.now().isoformat()))
            await db.commit()

    async def recent_logs(self, limit=20):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM admin_logs ORDER BY id DESC LIMIT ?", (limit,)) as cur:
                return [dict(r) for r in await cur.fetchall()]

db = Database()

# ═══════════════════════════════════════════════════════════════════
# 🌐 عميل API
# ═══════════════════════════════════════════════════════════════════

def extract_code(resp):
    if not isinstance(resp, dict): return None
    data = resp.get("data")
    if isinstance(data, dict):
        code = data.get("code")
        if code: return str(code)
    return None

class ApiClient:
    async def _headers(self):
        active = await db.get_active_key()
        if not active: return None, None
        return {"Authorization": f"Bearer {active['key_value'].strip()}",
                "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}, active

    def _sync_call(self, method, headers, **kwargs):
        response = requests.request(method, API_URL, headers=headers, timeout=30, **kwargs)
        response.raise_for_status()
        if response.status_code == 204 or not response.content:
            return {"success": True}
        return response.json()

    async def _call(self, method, **kwargs):
        headers, active = await self._headers()
        if not headers:
            return {"ok": False, "error": "no_key", "message": "❌ لا مفتاح نشط"}
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self._sync_call(method, headers, **kwargs))
            if active: await db.record_key_result(active["id"], True)
            return {"ok": True, "data": data}
        except requests.exceptions.HTTPError as e:
            if active: await db.record_key_result(active["id"], False)
            code = e.response.status_code if e.response is not None else 0
            body = ""
            if e.response is not None:
                try: body = e.response.text[:300]
                except Exception: pass
            if code == 401: return {"ok": False, "error": "unauthorized", "message": "🔴 المفتاح غير صالح"}
            if code == 404: return {"ok": False, "error": "not_found", "message": "❌ غير موجود (404)"}
            if code == 400: return {"ok": False, "error": "bad_request", "message": f"❌ طلب خاطئ: {body}"}
            return {"ok": False, "error": f"http_{code}", "message": f"❌ HTTP {code}"}
        except Exception as e:
            return {"ok": False, "error": "unknown", "message": f"⚠️ {e}"}

    async def create(self, plan, days, max_uses=1):
        return await self._call("POST", json={"plan": plan, "days": days, "max_uses": max_uses})

    async def check_code(self, code):
        return await self._call("GET", params={"code": code})

    def _test_key_sync(self, key_value):
        headers = {"Authorization": f"Bearer {key_value.strip()}", "User-Agent": "Mozilla/5.0"}
        try:
            r = requests.get(API_URL, headers=headers, timeout=15)
            if r.status_code == 401: return False, "🔴 غير صالح"
            if r.status_code in (200, 204): return True, "🟢 صالح"
            return True, f"🟢 {r.status_code}"
        except Exception as e:
            return False, f"⚠️ {e}"

    async def test_key(self, key_value):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._test_key_sync(key_value))

api = ApiClient()

# ═══════════════════════════════════════════════════════════════════
# ⌨️ نصوص الأزرار
# ═══════════════════════════════════════════════════════════════════

BTN_SHOP, BTN_SUBS, BTN_WALLET = "🛒 المتجر", "📦 اشتراكاتي", "💎 محفظتي"
BTN_EARN, BTN_TOP, BTN_GUIDE = "🎁 اكسب نقاط", "🏆 الصدارة", "📖 كيف أفعّل"
BTN_CHECK, BTN_STATUS, BTN_CALC = "🔍 فحص كود", "📊 حالتي", "🧮 حاسبة"
BTN_ARCHIVE, BTN_SETTINGS, BTN_ABOUT = "📚 الأرشيف", "⚙️ الإعدادات", "ℹ️ عن البوت"
BTN_MARKET, BTN_ADMIN = "🛒 السوق", "🛡️ لوحة المشرف"
BTN_HOME, BTN_BACK = "🏠 القائمة الرئيسية", "🔙 رجوع"

BTN_PLUS, BTN_PRO, BTN_PREMIUM = "⭐ بلس", "💎 برو", "👑 بريميوم"

BTN_QTY_1, BTN_QTY_2, BTN_QTY_3 = "1 كود", "2 كود", "3 أكواد"
BTN_QTY_5, BTN_QTY_10, BTN_QTY_CUSTOM = "5 أكواد", "10 أكواد", "✏️ عدد مخصص"
BTN_CONFIRM, BTN_EDIT_QTY, BTN_CANCEL = "✅ تأكيد الطلب", "✏️ تعديل العدد", "❌ إلغاء"

BTN_TRANSFER, BTN_DAILY, BTN_INVITE, BTN_MY_ID = "💸 تحويل", "🎁 يومية", "🔗 دعوة", "🆔 معرفي"
BTN_LANG, BTN_THEME, BTN_NOTIF = "🌍 اللغة", "🌙 المظهر", "🔔 الإشعارات"

BTN_KEYS, BTN_CHANNELS = "🔑 المفاتيح", "📢 القنوات"
BTN_DROPS, BTN_PDROPS = "🎁 دروبات", "💎 دروب نقاط"
BTN_STATS, BTN_LOGS = "📊 إحصائيات", "📜 السجل"
BTN_ADD_KEY, BTN_CREATE_DROP, BTN_CREATE_PDROP = "➕ مفتاح", "➕ دروب", "➕ دروب نقاط"

BTN_DROP_EGG, BTN_DROP_COND, BTN_DROP_CHAIN = "🥚 بيضاوي", "🔒 بشرط", "🔗 تسلسلي"
BTN_DROP_VOTE, BTN_DROP_AUCTION = "🗳️ تصويت", "🔨 مزاد"
BTN_ALL_DROPS, BTN_SCHEDULED, BTN_BROADCAST = "📋 كل الدروبات", "⏰ مجدولة", "📢 بث"
BTN_SCHEDULED_ADD = "➕ إضافة مجدول"

def is_admin(uid):
    return uid == SUPER_ADMIN_ID

# ═══════════════════════════════════════════════════════════════════
# ⌨️ لوحات المفاتيح
# ═══════════════════════════════════════════════════════════════════

def kb_main(admin=False):
    rows = [
        [KeyboardButton(BTN_SHOP), KeyboardButton(BTN_SUBS)],
        [KeyboardButton(BTN_WALLET), KeyboardButton(BTN_EARN)],
        [KeyboardButton(BTN_MARKET), KeyboardButton(BTN_TOP)],
        [KeyboardButton(BTN_GUIDE), KeyboardButton(BTN_CHECK)],
        [KeyboardButton(BTN_STATUS), KeyboardButton(BTN_CALC)],
        [KeyboardButton(BTN_ARCHIVE), KeyboardButton(BTN_SETTINGS)],
        [KeyboardButton(BTN_ABOUT)],
    ]
    if admin:
        rows.append([KeyboardButton(BTN_ADMIN)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True,
                                input_field_placeholder="اختر...")

def kb_shop():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_PLUS), KeyboardButton(BTN_PRO), KeyboardButton(BTN_PREMIUM)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_days(sub_type):
    info = SUBSCRIPTION_TYPES[sub_type]
    days = list(info["prices"].keys())
    rows = []
    if len(days) >= 2: rows.append([KeyboardButton(f"{d} يوم") for d in days[:2]])
    if len(days) > 2: rows.append([KeyboardButton(f"{d} يوم") for d in days[2:]])
    rows.append([KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)

def kb_quantity():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_QTY_1), KeyboardButton(BTN_QTY_2)],
        [KeyboardButton(BTN_QTY_3), KeyboardButton(BTN_QTY_5)],
        [KeyboardButton(BTN_QTY_10), KeyboardButton(BTN_QTY_CUSTOM)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_confirm():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_CONFIRM)],
        [KeyboardButton(BTN_EDIT_QTY)],
        [KeyboardButton(BTN_CANCEL), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_wallet():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_TRANSFER), KeyboardButton(BTN_DAILY)],
        [KeyboardButton(BTN_INVITE), KeyboardButton(BTN_MY_ID)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_earn():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_DAILY), KeyboardButton(BTN_INVITE)],
        [KeyboardButton(BTN_MY_ID)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_settings():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_LANG), KeyboardButton(BTN_THEME)],
        [KeyboardButton(BTN_NOTIF)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_admin():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_KEYS), KeyboardButton(BTN_CHANNELS)],
        [KeyboardButton(BTN_DROPS), KeyboardButton(BTN_PDROPS)],
        [KeyboardButton(BTN_STATS), KeyboardButton(BTN_LOGS)],
        [KeyboardButton(BTN_SCHEDULED), KeyboardButton(BTN_ALL_DROPS)],
        [KeyboardButton(BTN_BROADCAST)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_keys():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_ADD_KEY)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_drops():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_CREATE_DROP), KeyboardButton(BTN_DROP_EGG)],
        [KeyboardButton(BTN_DROP_COND), KeyboardButton(BTN_DROP_CHAIN)],
        [KeyboardButton(BTN_DROP_VOTE), KeyboardButton(BTN_DROP_AUCTION)],
        [KeyboardButton(BTN_ALL_DROPS), KeyboardButton(BTN_SCHEDULED)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_pdrops():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_CREATE_PDROP)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_cancel():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_CANCEL)]], resize_keyboard=True)

def kb_force_join():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 انضم للقناة", url=CHANNEL_URL)],
        [InlineKeyboardButton("✅ تحقق", callback_data="verify_join")],
    ])

# ═══════════════════════════════════════════════════════════════════
# 🕐 أدوات الوقت
# ═══════════════════════════════════════════════════════════════════

def format_relative_time(iso_str):
    if not iso_str: return "غير محدد"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "").split(".")[0])
        diff = datetime.now() - dt
        s = int(diff.total_seconds())
        if s < 60: return f"منذ {s} ثانية"
        if s < 3600: return f"منذ {s // 60} دقيقة"
        if s < 86400: return f"منذ {s // 3600} ساعة"
        return f"منذ {s // 86400} يوم"
    except Exception: return str(iso_str)[:16]

def format_date(iso_str):
    if not iso_str: return "غير محدد"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "").split(".")[0])
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception: return str(iso_str)[:16]

# ═══════════════════════════════════════════════════════════════════
# 🔒 Force Join Check
# ═══════════════════════════════════════════════════════════════════

async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE, use_cache=True):
    user_id = update.effective_user.id
    if use_cache:
        cache = await db.get_force_join_cache(user_id)
        if cache:
            try:
                cache_time = datetime.fromisoformat(cache["checked_at"])
                if (datetime.now() - cache_time).total_seconds() < 3600:
                    return cache["is_member"] == 1
            except Exception:
                pass
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        is_member = member.status in ("member", "administrator", "creator")
        await db.save_force_join_cache(user_id, is_member)
        return is_member
    except Exception:
        return True

async def force_join_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_force_join(update, context):
        return True
    await update.message.reply_text(
        f"🔒 *مرحباً بك في Worm GPT*\n\n"
        f"يجب الانضمام لقناتنا أولاً:\n\n"
        f"📢 *@{CHANNEL_USERNAME}*\n\n"
        f"بعد الانضمام، اضغط ✅ تحقق",
        parse_mode="Markdown", reply_markup=kb_force_join()
    )
    return False

async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ جاري التحقق...")
    await db.delete_force_join_cache(update.effective_user.id)
    if await check_force_join(update, context, use_cache=False):
        try:
            await query.message.delete()
        except Exception:
            pass
        admin = is_admin(update.effective_user.id)
        await query.message.reply_text(
            "✅ *تم التحقق!*\n\nمرحباً بك 🎉",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
    else:
        await query.answer("❌ لم نتمكن من التحقق. تأكد من انضمامك.", show_alert=True)

# ═══════════════════════════════════════════════════════════════════
# 🎁 بناء بطاقة الدروب (مع دعم كل الأنواع)
# ═══════════════════════════════════════════════════════════════════

def build_drop_card_text(drop):
    plan_info = SUBSCRIPTION_TYPES.get(drop["plan"], {"emoji": "📦", "name": drop["plan"]})
    drop_type = drop.get("drop_type", "normal")
    winners_so_far = drop.get("current_winners", 0)
    max_winners = drop.get("max_winners", 1)

    # رأس مخصص حسب النوع
    type_emoji = {
        "normal": "🎁", "egg": "🥚", "conditional": "🔒",
        "chain": "🔗", "vote": "🗳️", "auction": "🔨"
    }.get(drop_type, "🎁")
    type_name = {
        "normal": "دروب", "egg": "دروب بيضاوي", "conditional": "دروب بشرط",
        "chain": "دروب تسلسلي", "vote": "دروب بتصويت", "auction": "مزاد"
    }.get(drop_type, "دروب")

    # حالة
    if drop_type == "auction":
        return _build_auction_text(drop, plan_info)

    # حالة عادية / بيضاوي / شرط / تسلسلي / تصويت
    is_claimed = bool(drop.get("claimed_by")) or (winners_so_far >= max_winners)

    if is_claimed and drop_type != "vote":
        # مكتمل
        winner_line = ""
        if max_winners == 1:
            winner_line = f"👤 الفائز: `{drop['claimed_by']}`"
        else:
            winner_line = f"👥 فاز: `{winners_so_far}/{max_winners}`"

        extra = ""
        if drop_type == "chain":
            next_id = drop.get("next_drop_id")
            if next_id:
                extra = "\n🔗 *يفتح الدروب التالي تلقائياً*"

        return (
            f"{type_emoji} *{type_name} #{drop['token']}* ✅\n\n"
            f"{plan_info['emoji']} *{plan_info['name']}*\n"
            f"📅 `{drop['days']}` يوم\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🔴 *مكتمل*\n{winner_line}\n"
            f"⏰ {format_relative_time(drop.get('claimed_at'))}\n"
            f"━━━━━━━━━━━━━━━━━{extra}\n\n"
            f"💡 تابع @{CHANNEL_USERNAME} للقادم!"
        )

    # متاح
    conditions_line = ""
    if drop_type == "conditional":
        conds = json.loads(drop.get("conditions", "{}"))
        cond_lines = []
        if conds.get("min_invites"):
            cond_lines.append(f"  • {conds['min_invites']} دعوة")
        if conds.get("min_purchases"):
            cond_lines.append(f"  • {conds['min_purchases']} شراء")
        if conds.get("min_points"):
            cond_lines.append(f"  • {conds['min_points']} نقطة")
        if conds.get("vip_tier"):
            tier_name = VIP_TIERS.get(conds["vip_tier"], {}).get("name", conds["vip_tier"])
            cond_lines.append(f"  • مستوى {tier_name}+")
        if cond_lines:
            conditions_line = f"\n\n🔒 *الشروط:*\n" + "\n".join(cond_lines)

    egg_line = ""
    if drop_type == "egg":
        egg_line = "\n🎲 *جائزة مخفية — افتح لتعرف!*"

    vote_line = ""
    if drop_type == "vote":
        vote_line = f"\n\n🗳️ *انقر لتصويت* (الأكثر تصويتاً يفوز)"

    winners_line = ""
    if max_winners > 1:
        winners_line = f"\n👥 `{winners_so_far}/{max_winners}` فائز حتى الآن"

    return (
        f"{type_emoji} *{type_name} #{drop['token']}*\n\n"
        f"{plan_info['emoji']} *{plan_info['name']}*\n"
        f"📅 `{drop['days']}` يوم\n"
        f"💎 القيمة: `{plan_info['prices'].get(drop['days'], '?')}` نقطة"
        f"{conditions_line}{egg_line}{vote_line}{winners_line}\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🟢 *متاح — أول شخص يفوز!*\n"
        f"⏰ {format_relative_time(drop.get('created_at'))}\n"
        f"━━━━━━━━━━━━━━━━━"
    )

def _build_auction_text(drop, plan_info):
    """بطاقة المزاد"""
    auction = drop.get("_auction")
    if not auction:
        return (
            f"🔨 *مزاد #{drop['token']}*\n\n"
            f"{plan_info['emoji']} *{plan_info['name']}*\n"
            f"📅 `{drop['days']}` يوم\n\n"
            f"⚠️ *لم يبدأ المزاد بعد*"
        )

    ends_at = auction.get("ends_at", "")
    try:
        end_dt = datetime.fromisoformat(ends_at)
        remaining = end_dt - datetime.now()
        if remaining.total_seconds() > 0:
            h = remaining.seconds // 3600
            m = (remaining.seconds % 3600) // 60
            time_str = f"{h}س {m}د"
        else:
            time_str = "انتهى"
    except Exception:
        time_str = "غير محدد"

    if auction.get("is_closed"):
        winner = auction.get("current_bidder")
        return (
            f"🔨 *مزاد #{drop['token']}* ✅\n\n"
            f"{plan_info['emoji']} *{plan_info['name']}*\n"
            f"📅 `{drop['days']}` يوم\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🔴 *المزاد انتهى*\n"
            f"👤 الفائز: `{winner}`\n"
            f"💰 السعر: `{auction.get('current_bid', 0)}` نقطة\n"
            f"━━━━━━━━━━━━━━━━━"
        )

    current_bid = auction.get("current_bid", 0)
    current_bidder = auction.get("current_bidder")
    bid_line = ""
    if current_bid > 0:
        bid_line = f"\n💰 *أعلى مزايدة:* `{current_bid}` نقطة\n👤 من: `{current_bidder}`"

    return (
        f"🔨 *مزاد #{drop['token']}*\n\n"
        f"{plan_info['emoji']} *{plan_info['name']}*\n"
        f"📅 `{drop['days']}` يوم\n"
        f"💎 القيمة: `{plan_info['prices'].get(drop['days'], '?')}` نقطة\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"💰 سعر البداية: `{auction.get('start_price', 0)}` نقطة\n"
        f"📈 الحد الأدنى للزيادة: `{auction.get('min_increment', 5)}` نقطة{bid_line}\n"
        f"⏱️ *ينتهي:* {time_str}\n"
        f"━━━━━━━━━━━━━━━━━"
    )

def build_drop_card_kb(drop, bot_username):
    """أزرار البطاقة حسب النوع"""
    kb = []
    drop_type = drop.get("drop_type", "normal")
    is_claimed = bool(drop.get("claimed_by"))
    winners = drop.get("current_winners", 0)
    max_winners = drop.get("max_winners", 1)

    if drop_type == "auction":
        auction = drop.get("_auction")
        if auction and not auction.get("is_closed"):
            kb.append([InlineKeyboardButton(
                "💰 زايد الآن",
                callback_data=f"bid_{drop['id']}"
            )])

    elif drop_type == "vote":
        kb.append([InlineKeyboardButton(
            "🗳️ صوّت الآن",
            callback_data=f"vote_{drop['id']}"
        )])

    elif not is_claimed and winners < max_winners and drop.get("is_active"):
        kb.append([InlineKeyboardButton(
            "🔗 افتح الدروب",
            url=f"https://t.me/{bot_username}?start=drop_{drop['token']}"
        )])

    kb.append([
        InlineKeyboardButton("📊 الحالة", callback_data=f"drop_status_{drop['id']}"),
        InlineKeyboardButton("🔄 تحديث", callback_data=f"drop_refresh_{drop['id']}"),
    ])
    kb.append([InlineKeyboardButton("📢 تابع القناة", url=CHANNEL_URL)])
    return InlineKeyboardMarkup(kb)

# ═══════════════════════════════════════════════════════════════════
# 🎬 start + chat member + drop entry
# ═══════════════════════════════════════════════════════════════════

async def on_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result:
        return
    chat = result.chat
    new_status = result.new_chat_member.status
    old_status = result.old_chat_member.status

    if new_status == "administrator" and old_status in ("left", "member"):
        can_post = getattr(result.new_chat_member, "can_post_messages", False) or False
        can_edit = getattr(result.new_chat_member, "can_edit_messages", False) or False
        await db.add_channel(
            chat_id=chat.id, title=chat.title, username=chat.username,
            chat_type=chat.type, added_by=result.from_user.id,
            can_post=1 if can_post else 0, can_edit=1 if can_edit else 0
        )
        logger.info(f"✅ البوت أُضيف: {chat.title}")
        try:
            await context.bot.send_message(
                result.from_user.id,
                f"✅ *تم إضافة البوت!*\n\n📢 *{chat.title}*\n🎁 يمكنك الآن نشر الدروبات فيه.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    elif new_status in ("left", "kicked") and old_status in ("administrator", "member"):
        await db.remove_channel(chat.id)
        logger.info(f"❌ البوت أُزيل: {chat.title}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if not await force_join_gate(update, context):
        return
    invited_by = None
    if args and args[0].startswith("drop_"):
        await handle_drop_entry(update, context, args[0].replace("drop_", ""))
        return
    if args and args[0].startswith("pdrop_"):
        await handle_points_drop_entry(update, context, args[0].replace("pdrop_", ""))
        return
    if args and args[0].startswith("ref_"):
        try:
            invited_by = int(args[0].replace("ref_", ""))
            if invited_by == user.id:
                invited_by = None
        except ValueError:
            pass

    _, is_new = await db.register_user(user.id, user.username, user.first_name, invited_by)
    admin = is_admin(user.id)
    context.user_data["state"] = "main"

    txt = f"👋 أهلاً *{user.first_name}*!\n\n🤖 *Worm GPT* — بوت إدارة الاشتراكات\n\n"
    if is_new:
        txt += "🎉 تم تسجيلك!\n"
        if invited_by:
            txt += "🎁 حصل داعيك على نقطة!\n"
        txt += "\n"
    txt += "استخدم الأزرار:"
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb_main(admin))

async def handle_drop_entry(update, context, token):
    """معالج فتح الدروب من الرابط"""
    user = update.effective_user
    await db.register_user(user.id, user.username, user.first_name)
    admin = is_admin(user.id)

    drop = await db.get_drop(token)
    if not drop:
        await update.message.reply_text("❌ *الدروب غير موجود*",
                                          parse_mode="Markdown", reply_markup=kb_main(admin))
        return

    drop_type = drop.get("drop_type", "normal")

    # ═══ دروب بيضاوي ═══
    if drop_type == "egg":
        await handle_egg_open(update, context, drop)
        return

    # ═══ دروب بشرط ═══
    if drop_type == "conditional":
        await handle_conditional_open(update, context, drop)
        return

    # ═══ دروب تسلسلي ═══
    if drop_type == "chain":
        await handle_chain_open(update, context, drop)
        return

    # ═══ دروب تصويت ═══
    if drop_type == "vote":
        await handle_vote_open(update, context, drop)
        return

    # ═══ مزاد ═══
    if drop_type == "auction":
        await handle_auction_open(update, context, drop)
        return

    # ═══ دروب عادي ═══
    if not drop["is_active"] or drop["claimed_by"]:
        await update.message.reply_text("😔 *حظاً أوفر!*",
                                          parse_mode="Markdown", reply_markup=kb_main(admin))
        return

    drop_info = SUBSCRIPTION_TYPES.get(drop["plan"], {})
    api_plan = drop_info.get("api_plan", drop["plan"])
    await update.message.reply_text("🎁 جاري إنشاء كودك...", reply_markup=kb_main(admin))
    result = await api.create(api_plan, drop["days"], 1)
    if not result["ok"]:
        await update.message.reply_text(f"❌ فشل: {result.get('message')}",
                                          reply_markup=kb_main(admin))
        return
    code = extract_code(result["data"])
    if not code:
        await update.message.reply_text("⚠️ الكود مفقود.", reply_markup=kb_main(admin))
        return
    await db.claim_drop(token, user.id, code)
    await db.add_drop_winner(drop["id"], user.id, 1, code)
    await db.save_subscription(user.id, {
        "code": code, "plan": drop["plan"], "actual_plan": api_plan,
        "days": drop["days"], "max_uses": 1, "points_spent": 0,
        "response": result["data"], "source": "drop"
    })
    await refresh_drop_immediately(context, drop["id"])
    info = SUBSCRIPTION_TYPES.get(drop["plan"], {"emoji": "📦", "name": drop["plan"]})
    await update.message.reply_text(
        f"🎉 *مبروك! أنت أول من فتح الدروب!*\n\n"
        f"{info['emoji']} {info['name']}\n📅 {drop['days']} يوم\n"
        f"🔑 *كودك:* `{code}`\n\n📖 فعّله في: {SITE_URL}",
        parse_mode="Markdown", reply_markup=kb_main(admin),
        disable_web_page_preview=True
    )
    try:
        await context.bot.send_message(SUPER_ADMIN_ID,
            f"🔔 *دروب استُخدم!*\n\n🎁 #{drop['token']}\n👤 `{user.id}`\n🔑 `{code}`",
            parse_mode="Markdown")
    except Exception:
        pass

async def handle_points_drop_entry(update, context, token):
    user = update.effective_user
    await db.register_user(user.id, user.username, user.first_name)
    admin = is_admin(user.id)
    pd = await db.get_points_drop(token)
    if not pd or not pd["is_active"] or pd["claimed_by"]:
        await update.message.reply_text("😔 *حظاً أوفر!*",
                                          parse_mode="Markdown", reply_markup=kb_main(admin))
        return
    await db.claim_points_drop(token, user.id)
    await db.add_points(user.id, pd["points"], "points_drop_claim", pd["id"])
    await db.update_vip_tier(user.id)
    await update.message.reply_text(
        f"🎉 *مبروك!* حصلت على {pd['points']} نقطة!",
        parse_mode="Markdown", reply_markup=kb_main(admin)
    )

# ═══════════════════════════════════════════════════════════════════
# 🔄 تحديث فوري للدروب
# ═══════════════════════════════════════════════════════════════════

async def refresh_drop_immediately(context, drop_id):
    drop = await db.get_drop_by_id(drop_id)
    if not drop:
        return

    # إضافة معلومات المزاد إذا لزم
    if drop.get("drop_type") == "auction":
        auction = await db.get_auction_by_drop(drop_id)
        drop["_auction"] = auction

    msgs = await db.get_drop_messages(drop_id)
    for m in msgs:
        try:
            await context.bot.edit_message_text(
                chat_id=m["chat_id"], message_id=m["message_id"],
                text=build_drop_card_text(drop),
                reply_markup=build_drop_card_kb(drop, context.bot.username)
            )
        except Exception as e:
            if "not modified" not in str(e).lower():
                logger.warning(f"فشل تحديث: {e}")

# ═══════════════════════════════════════════════════════════════════
# 📊 أزرار البطاقة
# ═══════════════════════════════════════════════════════════════════

async def drop_status_callback(update, context):
    query = update.callback_query
    try:
        drop_id = int(query.data.replace("drop_status_", ""))
    except ValueError:
        await query.answer("❌ خطأ", show_alert=True)
        return
    drop = await db.get_drop_by_id(drop_id)
    if not drop:
        await query.answer("❌ غير موجود", show_alert=True)
        return
    if drop.get("claimed_by"):
        await query.answer(
            f"🔴 مُستخدم\n\n👤 ID: {drop['claimed_by']}\n⏰ {format_relative_time(drop.get('claimed_at'))}",
            show_alert=True
        )
    else:
        await query.answer(
            f"🟢 متاح!\n\n⏰ {format_relative_time(drop.get('created_at'))}",
            show_alert=True
        )
    if drop.get("drop_type") == "auction":
        drop["_auction"] = await db.get_auction_by_drop(drop_id)
    try:
        await query.edit_message_text(
            text=build_drop_card_text(drop),
            reply_markup=build_drop_card_kb(drop, context.bot.username)
        )
    except Exception:
        pass

async def drop_refresh_callback(update, context):
    query = update.callback_query
    await query.answer("⏳")
    try:
        drop_id = int(query.data.replace("drop_refresh_", ""))
    except ValueError:
        return
    drop = await db.get_drop_by_id(drop_id)
    if not drop:
        return
    if drop.get("drop_type") == "auction":
        drop["_auction"] = await db.get_auction_by_drop(drop_id)
    try:
        await query.edit_message_text(
            text=build_drop_card_text(drop),
            reply_markup=build_drop_card_kb(drop, context.bot.username)
        )
    except Exception as e:
        if "not modified" in str(e).lower():
            await query.answer("ℹ️ لا تغيير", show_alert=False)

async def periodic_refresh(context):
    try:
        drops = await db.get_drops_for_refresh()
        if not drops:
            return
        updated = 0
        for drop in drops:
            if drop.get("drop_type") == "auction":
                drop["_auction"] = await db.get_auction_by_drop(drop["id"])
            msgs = await db.get_drop_messages(drop["id"])
            for m in msgs:
                try:
                    await context.bot.edit_message_text(
                        chat_id=m["chat_id"], message_id=m["message_id"],
                        text=build_drop_card_text(drop),
                        reply_markup=build_drop_card_kb(drop, context.bot.username)
                    )
                    updated += 1
                    await asyncio.sleep(0.3)
                except Exception:
                    pass
        if updated:
            logger.info(f"⏱️ تحديث دوري: {updated}")
    except Exception as e:
        logger.error(f"فشل: {e}")

# ═══════════════════════════════════════════════════════════════════
# 🏠 القوائم الرئيسية
# ═══════════════════════════════════════════════════════════════════

async def show_home(update, context):
    admin = is_admin(update.effective_user.id)
    context.user_data["state"] = "main"
    await update.message.reply_text("🏠 *القائمة الرئيسية*",
                                      parse_mode="Markdown", reply_markup=kb_main(admin))

async def show_shop(update, context):
    user = await db.get_user(update.effective_user.id)
    context.user_data["state"] = "shop"
    context.user_data.pop("buy", None)
    tier = get_vip_tier(user["points"])
    tier_info = VIP_TIERS[tier]
    discount = tier_info["discount"]
    discount_line = f"\n🎁 خصم VIP: `{discount}%`" if discount > 0 else ""
    await update.message.reply_text(
        f"🛒 *المتجر*\n\n"
        f"💎 رصيدك: `{user['points']}`\n"
        f"🏅 مستواك: {tier_info['name']}{discount_line}\n\n"
        f"📦 *الخطط:*\n"
        f"⭐ بلس — من 5 نقاط\n"
        f"💎 برو — من 8 نقاط\n"
        f"👑 بريميوم — من 15 نقطة\n\n"
        f"اختر النوع:",
        parse_mode="Markdown", reply_markup=kb_shop())

async def show_subs(update, context):
    subs = await db.get_user_subs(update.effective_user.id)
    admin = is_admin(update.effective_user.id)
    if not subs:
        await update.message.reply_text("📭 لا يوجد اشتراكات.",
                                          reply_markup=kb_main(admin))
        return
    lines = ["📋 *اشتراكاتك:*\n"]
    for i, s in enumerate(subs[:10], 1):
        info = SUBSCRIPTION_TYPES.get(s["plan"], {"emoji": "📦", "name": s["plan"]})
        lines.append(f"{i}. {info['emoji']} {info['name']} — {s['days']}ي — {s['created_at'][:10]}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown",
                                      reply_markup=kb_main(admin))

async def show_wallet(update, context):
    u = await db.get_user(update.effective_user.id)
    rank, total = await db.get_user_rank(update.effective_user.id)
    tier = get_vip_tier(u["points"])
    tier_info = VIP_TIERS[tier]
    context.user_data["state"] = "wallet"
    await update.message.reply_text(
        f"💎 *محفظتي*\n\n"
        f"💰 الرصيد: `{u['points']}`\n"
        f"🏅 المستوى: {tier_info['name']}\n"
        f"🏆 الترتيب: `{rank}` من `{total}`\n"
        f"📈 إجمالي كسبت: `{u['total_points_earned']}`\n"
        f"📉 إجمالي صرفت: `{u['total_points_spent']}`\n"
        f"🔥 سلسلة يومية: `{u.get('daily_streak', 0)}` يوم",
        parse_mode="Markdown", reply_markup=kb_wallet())

async def show_earn(update, context):
    context.user_data["state"] = "earn"
    await update.message.reply_text(
        "🎁 *كسب النقاط*\n\n"
        "1️⃣ المكافأة اليومية (مع سلسلة)\n"
        "2️⃣ دعوة الأصدقاء\n"
        "3️⃣ استلام تحويلات\n\nاختر:",
        parse_mode="Markdown", reply_markup=kb_earn())

async def show_top(update, context):
    top = await db.top_users(5)
    user_id = update.effective_user.id
    my_rank, total = await db.get_user_rank(user_id)
    me = await db.get_user(user_id)
    lines = ["🏆 *أفضل 5:*\n"]
    for i, u in enumerate(top, 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
        name = u.get("first_name") or "مستخدم"
        username = u.get("username")
        ref = f"@{username}" if username else f"`{u['user_id']}`"
        tier = VIP_TIERS.get(u.get("vip_tier", "bronze"), {})
        tier_emoji = tier.get("emoji", "")
        marker = " ← *أنت*" if u["user_id"] == user_id else ""
        lines.append(f"{medal} {tier_emoji} *{name}* — {ref}\n   💎 {u['points']}{marker}")
    lines.append("\n" + "─" * 15)
    if my_rank <= 5:
        lines.append(f"🎯 *ترتيبك:* {my_rank}")
    elif my_rank > 0:
        diff = top[-1]["points"] - me["points"] if top else 0
        lines.append(f"🎯 *ترتيبك:* `{my_rank}` من `{total}`\n"
                     f"💎 `{me['points']}`\n⬆️ تحتاج `{max(1, diff+1)}` نقطة")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown",
                                      reply_markup=kb_main(is_admin(user_id)))

async def show_guide(update, context):
    last_sub = await db.get_last_sub_code(update.effective_user.id)
    guide = (
        "📖 *دليل التفعيل*\n\n"
        "1️⃣ افتح الموقع\n2️⃣ سجّل الدخول\n"
        "3️⃣ القائمة الجانبية (☰)\n4️⃣ قسم الخطط\n"
        "5️⃣ انزل → \"كود التفعيل\"\n6️⃣ الصق → تفعيل ✅\n\n"
    )
    if last_sub:
        guide += f"─────────────────\n🔑 *آخر كود:*\n`{last_sub['code']}`\n\n📦 {last_sub['plan']} — {last_sub['days']}ي"
    else:
        guide += "─────────────────\n⚠️ لا تملك كوداً."
    guide += f"\n\n🌐 {SITE_URL}"
    await update.message.reply_text(guide, parse_mode="Markdown",
                                      reply_markup=kb_main(is_admin(update.effective_user.id)),
                                      disable_web_page_preview=True)

async def show_about(update, context):
    types = "\n".join([f"{i['emoji']} *{i['name']}* — {i['description']}"
                       for i in SUBSCRIPTION_TYPES.values()])
    await update.message.reply_text(
        f"🤖 *Worm GPT*\n\nبوت إدارة اشتراكات احترافي\n\n"
        f"📦 *الباقات:*\n{types}\n\n"
        f"📢 *القناة:* @{CHANNEL_USERNAME}\n"
        f"🌐 {SITE_URL}",
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(update.effective_user.id)),
        disable_web_page_preview=True)

async def show_status(update, context):
    user_id = update.effective_user.id
    u = await db.get_user(user_id)
    subs = await db.get_user_subs(user_id)
    rank, total = await db.get_user_rank(user_id)
    tier = get_vip_tier(u["points"])
    tier_info = VIP_TIERS[tier]
    active_subs = sum(1 for s in subs if s["status"] == "active")
    last = u.get("last_daily_bonus")
    if last:
        last_dt = datetime.fromisoformat(last)
        diff = datetime.now() - last_dt
        if diff < timedelta(hours=24):
            remaining = timedelta(hours=24) - diff
            daily_status = f"⏳ {remaining.seconds // 3600}س {(remaining.seconds % 3600) // 60}د"
        else:
            daily_status = "✅ متاحة"
    else:
        daily_status = "✅ متاحة"
    await update.message.reply_text(
        f"📊 *حالتي*\n\n"
        f"💰 النقاط: `{u['points']}`\n"
        f"🏅 المستوى: {tier_info['name']}\n"
        f"🏆 الترتيب: `{rank}` من `{total}`\n"
        f"📦 اشتراكات نشطة: `{active_subs}`\n"
        f"🔥 السلسلة: `{u.get('daily_streak', 0)}` يوم\n"
        f"🎁 مكافأة يومية: {daily_status}\n\n"
        f"💎 خصم VIP: `{tier_info['discount']}%`",
        parse_mode="Markdown", reply_markup=kb_main(is_admin(user_id))
    )

async def show_calculator(update, context):
    user = await db.get_user(update.effective_user.id)
    tier = get_vip_tier(user["points"])
    vip_discount = VIP_TIERS[tier]["discount"]
    context.user_data["calc"] = {}
    context.user_data["state"] = "calc_type"
    await update.message.reply_text(
        f"🧮 *حاسبة النقاط*\n\n"
        f"💎 رصيدك: `{user['points']}`\n"
        f"🎁 خصم VIP: `{vip_discount}%`\n\n"
        f"اختر نوع الباقة:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton(BTN_PLUS), KeyboardButton(BTN_PRO), KeyboardButton(BTN_PREMIUM)],
            [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
        ], resize_keyboard=True)
    )

async def show_archive(update, context):
    subs = await db.get_all_user_subs(update.effective_user.id)
    admin = is_admin(update.effective_user.id)
    if not subs:
        await update.message.reply_text("📭 لا يوجد اشتراكات في الأرشيف.",
                                          reply_markup=kb_main(admin))
        return
    lines = [f"📚 *أرشيف اشتراكاتك* ({len(subs)})\n"]
    for i, s in enumerate(subs[:30], 1):
        info = SUBSCRIPTION_TYPES.get(s["plan"], {"emoji": "📦", "name": s["plan"]})
        lines.append(f"{i}. {info['emoji']} {info['name']} — {s['days']}ي — {s['created_at'][:10]}")
    if len(subs) > 30:
        lines.append(f"\n... و {len(subs) - 30} أخرى")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown",
                                      reply_markup=kb_main(admin))

async def show_settings(update, context):
    context.user_data["state"] = "settings"
    await update.message.reply_text("⚙️ *الإعدادات*\n\nاختر:",
                                      parse_mode="Markdown", reply_markup=kb_settings())

async def show_language(update, context):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="settings_back")],
    ])
    await update.message.reply_text("🌍 *اختر اللغة:*",
                                      parse_mode="Markdown", reply_markup=kb)

async def lang_callback(update, context):
    query = update.callback_query
    lang = query.data.replace("lang_", "")
    if lang in ("ar", "en"):
        await db.set_language(update.effective_user.id, lang)
        await query.answer(f"✅ {'العربية' if lang == 'ar' else 'English'}")
        await query.edit_message_text(
            f"✅ *تم تغيير اللغة!*\n\nاللغة: {'🇸🇦 العربية' if lang == 'ar' else '🇬🇧 English'}",
            parse_mode="Markdown")
    else:
        await query.answer("❌ غير مدعومة", show_alert=True)

async def show_theme(update, context):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("☀️ نهاري", callback_data="theme_day")],
        [InlineKeyboardButton("🌙 ليلي", callback_data="theme_night")],
        [InlineKeyboardButton("🔄 تلقائي", callback_data="theme_auto")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="settings_back")],
    ])
    await update.message.reply_text("🌙 *اختر المظهر:*",
                                      parse_mode="Markdown", reply_markup=kb)

async def theme_callback(update, context):
    query = update.callback_query
    theme = query.data.replace("theme_", "")
    if theme in ("day", "night", "auto"):
        await db.set_theme(update.effective_user.id, theme)
        names = {"day": "☀️ نهاري", "night": "🌙 ليلي", "auto": "🔄 تلقائي"}
        await query.answer(f"✅ {names[theme]}")
        await query.edit_message_text(
            f"✅ *تم تغيير المظهر!*\n\n{names[theme]}",
            parse_mode="Markdown")
    else:
        await query.answer("❌", show_alert=True)

async def show_notifications(update, context):
    user = await db.get_user(update.effective_user.id)
    notif = json.loads(user.get("notifications", "{}"))
    drops = notif.get("drops", True)
    daily = notif.get("daily", True)
    promos = notif.get("promos", False)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'✅' if drops else '☐'} دروبات جديدة", callback_data="notif_drops")],
        [InlineKeyboardButton(f"{'✅' if daily else '☐'} مكافأة يومية", callback_data="notif_daily")],
        [InlineKeyboardButton(f"{'✅' if promos else '☐'} عروض خاصة", callback_data="notif_promos")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="settings_back")],
    ])
    await update.message.reply_text("🔔 *الإشعارات*\n\nاضغط لتفعيل/إلغاء:",
                                      parse_mode="Markdown", reply_markup=kb)

async def notif_callback(update, context):
    query = update.callback_query
    key = query.data.replace("notif_", "")
    user = await db.get_user(update.effective_user.id)
    notif = json.loads(user.get("notifications", "{}"))
    default = True if key != "promos" else False
    notif[key] = not notif.get(key, default)
    await db.set_notifications(update.effective_user.id, json.dumps(notif))
    await query.answer("✅ محدّث")
    await show_notifications(update, context)

async def settings_back_callback(update, context):
    query = update.callback_query
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        pass
    await update.effective_message.reply_text(
        "⚙️ *الإعدادات*", parse_mode="Markdown", reply_markup=kb_settings())

# ═══════════════════════════════════════════════════════════════════
# 🔍 فحص كود
# ═══════════════════════════════════════════════════════════════════

async def check_code_begin(update, context):
    context.user_data["state"] = "check_code"
    await update.message.reply_text(
        "🔍 *فحص كود*\n\nأرسل الكود:\n\n❌ للإلغاء",
        parse_mode="Markdown", reply_markup=kb_cancel())

async def check_code_receive(update, context, code):
    code = code.strip()
    if len(code) < 3:
        await update.message.reply_text("❌ قصير:", reply_markup=kb_cancel())
        return
    admin = is_admin(update.effective_user.id)
    wait_msg = await update.message.reply_text("🔍 جاري الفحص...")
    result = await api.check_code(code)
    if not result["ok"]:
        try:
            await wait_msg.edit_text(
                f"❌ *فشل*\n\n`{result.get('message', '')[:200]}`",
                parse_mode="Markdown")
        except Exception:
            pass
        context.user_data["state"] = "main"
        await update.message.reply_text("استخدم الأزرار:",
                                          reply_markup=kb_main(admin))
        return
    data = result["data"]
    info = data.get("data") if isinstance(data, dict) and "data" in data else data
    if not isinstance(info, dict):
        try:
            await wait_msg.edit_text(f"```\n{str(data)[:500]}\n```", parse_mode="Markdown")
        except Exception:
            await wait_msg.edit_text(str(data)[:500])
        context.user_data["state"] = "main"
        await update.message.reply_text("استخدم الأزرار:",
                                          reply_markup=kb_main(admin))
        return
    code_val = info.get("code", code)
    plan = info.get("plan", "?")
    days = info.get("days", "?")
    max_uses = info.get("max_uses", "?")
    uses = info.get("uses", 0)
    status = info.get("status", "?")
    created_at = info.get("created_at")
    expires_at = info.get("expires_at")
    plan_info = SUBSCRIPTION_TYPES.get(plan, {"emoji": "📦", "name": plan})
    status_map = {"active": "🟢 نشط", "used": "🔴 مستخدم", "expired": "⏰ منتهي"}
    status_display = status_map.get(status, f"ℹ️ {status}")
    if isinstance(uses, int) and isinstance(max_uses, int):
        uses_display = f"`{uses}/{max_uses}`" + (" ⚠️" if uses >= max_uses else "")
    else:
        uses_display = f"`{uses}/{max_uses}`"

    def fmt(d):
        if not d:
            return "غير محدد"
        try:
            return datetime.fromisoformat(str(d).replace("Z", "").split(".")[0]).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(d)[:16]

    report = (
        f"✅ *نتيجة الفحص*\n\n🔑 *الكود:*\n`{code_val}`\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"{plan_info['emoji']} *النوع:* {plan_info['name']}\n"
        f"📅 *المدة:* `{days}` يوم\n"
        f"🔢 *الاستخدامات:* {uses_display}\n"
        f"📊 *الحالة:* {status_display}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📆 *أُنشئ:* {fmt(created_at)}\n"
        f"⏰ *ينتهي:* {fmt(expires_at)}")
    try:
        await wait_msg.edit_text(report, parse_mode="Markdown")
    except Exception:
        await wait_msg.edit_text(report)
    context.user_data["state"] = "main"
    await update.message.reply_text("💡 افحص آخر أو استخدم الأزرار:",
                                      reply_markup=kb_main(admin))

# ═══════════════════════════════════════════════════════════════════
# 💰 مكافأة + دعوة + معرف
# ═══════════════════════════════════════════════════════════════════

async def do_daily(update, context):
    ok, msg = await db.claim_daily_bonus(update.effective_user.id)
    await db.update_vip_tier(update.effective_user.id)
    await update.message.reply_text(msg, reply_markup=kb_main(is_admin(update.effective_user.id)))

async def show_invite(update, context):
    u = await db.get_user(update.effective_user.id)
    link = f"https://t.me/{context.bot.username}?start=ref_{u['user_id']}"
    await update.message.reply_text(
        f"🔗 *رابط دعوتك:*\n`{link}`\n\n💰 {POINTS_INVITE} نقطة لكل صديق!",
        parse_mode="Markdown", reply_markup=kb_main(is_admin(update.effective_user.id)))

async def show_my_id(update, context):
    u = await db.get_user(update.effective_user.id)
    await update.message.reply_text(
        f"🆔 *معرفك:*\n`{u['user_id']}`\n\nأعطه لمن يريد تحويل نقاط لك.",
        parse_mode="Markdown", reply_markup=kb_main(is_admin(update.effective_user.id)))

# ═══════════════════════════════════════════════════════════════════
# 💸 التحويل
# ═══════════════════════════════════════════════════════════════════

async def transfer_begin(update, context):
    user = await db.get_user(update.effective_user.id)
    context.user_data["state"] = "transfer_id"
    context.user_data.pop("transfer_to", None)
    context.user_data.pop("transfer_amount", None)
    await update.message.reply_text(
        f"💸 *تحويل نقاط*\n\n💎 رصيدك: `{user['points']}`\n\n"
        f"أرسل *معرف (ID)* المستخدم:\n_(من @userinfobot)_\n\n❌ للإلغاء",
        parse_mode="Markdown", reply_markup=kb_cancel())

async def transfer_get_id(update, context, text):
    try:
        target_id = int(text)
    except ValueError:
        await update.message.reply_text("❌ معرف غير صالح:", reply_markup=kb_cancel())
        return
    if target_id == update.effective_user.id:
        await update.message.reply_text("❌ لا يمكن التحويل لنفسك:", reply_markup=kb_cancel())
        return
    target = await db.get_user(target_id)
    if not target:
        await update.message.reply_text("❌ غير مسجل:", reply_markup=kb_cancel())
        return
    context.user_data["transfer_to"] = target_id
    context.user_data["state"] = "transfer_amount"
    name = target.get("first_name") or target.get("username") or str(target_id)
    await update.message.reply_text(f"👤 *{name}*\n\n💎 عدد النقاط:",
                                      parse_mode="Markdown", reply_markup=kb_cancel())

async def transfer_get_amount(update, context, text):
    try:
        amount = int(text)
        if amount < MIN_TRANSFER:
            raise ValueError
    except ValueError:
        await update.message.reply_text(f"❌ الحد الأدنى {MIN_TRANSFER}:",
                                          reply_markup=kb_cancel())
        return
    user = await db.get_user(update.effective_user.id)
    if user["points"] < amount:
        await update.message.reply_text(f"🔒 رصيدك `{user['points']}`. أرسل أقل:",
                                          parse_mode="Markdown", reply_markup=kb_cancel())
        return
    context.user_data["transfer_amount"] = amount
    context.user_data["state"] = "transfer_confirm"
    target = await db.get_user(context.user_data.get("transfer_to"))
    name = target.get("first_name") or target.get("username") or "المستخدم"
    await update.message.reply_text(
        f"📋 *تأكيد:*\n\n👤 *{name}*\n💎 `{amount}`\n\nأرسل `تأكيد`:",
        parse_mode="Markdown", reply_markup=kb_cancel())

async def transfer_do_confirm(update, context, text):
    if text.strip().lower() not in ("تأكيد", "confirm", "نعم"):
        await update.message.reply_text("❌ أرسل `تأكيد` أو ❌ إلغاء:",
                                          parse_mode="Markdown", reply_markup=kb_cancel())
        return
    target_id = context.user_data.get("transfer_to")
    amount = context.user_data.get("transfer_amount")
    if not target_id or not amount:
        await show_home(update, context)
        return
    ok, msg = await db.transfer_points(update.effective_user.id, target_id, amount)
    if ok:
        target = await db.get_user(target_id)
        name = target.get("first_name") or "المستخدم"
        await update.message.reply_text(
            f"✅ *تم التحويل!*\n\n👤 *{name}*\n💎 `{amount}`",
            parse_mode="Markdown",
            reply_markup=kb_main(is_admin(update.effective_user.id)))
        try:
            await context.bot.send_message(target_id,
                f"🎁 *وصلك تحويل!*\n\n💎 `{amount}` نقطة",
                parse_mode="Markdown")
        except Exception:
            pass
    else:
        await update.message.reply_text(f"❌ {msg}",
                                          reply_markup=kb_main(is_admin(update.effective_user.id)))
    context.user_data["state"] = "main"
    context.user_data.pop("transfer_to", None)
    context.user_data.pop("transfer_amount", None)

# ═══════════════════════════════════════════════════════════════════
# 🛒 الشراء
# ═══════════════════════════════════════════════════════════════════

async def buy_choose_type(update, context, sub_type):
    info = SUBSCRIPTION_TYPES[sub_type]
    user = await db.get_user(update.effective_user.id)
    tier = get_vip_tier(user["points"])
    vip_discount = VIP_TIERS[tier]["discount"]
    context.user_data["buy"] = {"type": sub_type}
    context.user_data["state"] = "buy_days"
    prices_text = "\n".join([f"  • {d} يوم = {p} 💎" for d, p in info["prices"].items()])
    await update.message.reply_text(
        f"{info['emoji']} *{info['name']}*\n\n{info['description']}\n\n"
        f"💰 *الأسعار:*\n{prices_text}\n\n"
        f"💎 رصيدك: `{user['points']}`\n"
        f"🎁 خصم VIP: `{vip_discount}%`\n\n📅 اختر المدة:",
        parse_mode="Markdown", reply_markup=kb_days(sub_type))

async def buy_choose_days(update, context, days):
    ctx = context.user_data.get("buy", {})
    sub_type = ctx.get("type")
    if not sub_type:
        await show_shop(update, context)
        return
    info = SUBSCRIPTION_TYPES[sub_type]
    if days not in info["prices"]:
        await update.message.reply_text("❌ مدة غير صحيحة", reply_markup=kb_days(sub_type))
        return
    ctx["days"] = days
    ctx["unit_price"] = info["prices"][days]
    user = await db.get_user(update.effective_user.id)
    context.user_data["state"] = "buy_qty"
    await update.message.reply_text(
        f"{info['emoji']} *{info['name']}* — {days} يوم\n\n"
        f"💰 سعر الوحدة: `{info['prices'][days]}`\n"
        f"💎 رصيدك: `{user['points']}`\n\n🔢 اختر عدد الأكواد:",
        parse_mode="Markdown", reply_markup=kb_quantity())

async def buy_choose_qty(update, context, qty):
    ctx = context.user_data.get("buy", {})
    sub_type = ctx.get("type")
    days = ctx.get("days")
    if not sub_type or not days:
        await show_shop(update, context)
        return
    info = SUBSCRIPTION_TYPES[sub_type]
    unit_price = info["prices"][days]
    total, subtotal, discount = calculate_price(unit_price, qty)
    user = await db.get_user(update.effective_user.id)
    tier = get_vip_tier(user["points"])
    vip_discount = VIP_TIERS[tier]["discount"]
    if vip_discount > 0:
        vip_saving = total * vip_discount // 100
        total -= vip_saving
    if user["points"] < total:
        await update.message.reply_text(
            f"🔒 *نقاطك غير كافية*\n\nالمطلوب: `{total}` 💎\nلديك: `{user['points']}` 💎",
            parse_mode="Markdown", reply_markup=kb_quantity())
        return
    ctx["quantity"] = qty
    ctx["subtotal"] = subtotal
    ctx["discount"] = discount
    ctx["total"] = total
    context.user_data["state"] = "buy_confirm"
    discount_line = f"\n🎁 خصم كمية: `{discount}%`" if discount > 0 else ""
    vip_line = f"\n🏅 خصم VIP: `{vip_discount}%`" if vip_discount > 0 else ""
    await update.message.reply_text(
        f"📋 *ملخص الطلب*\n\n"
        f"{info['emoji']} *{info['name']}*\n📅 {days} يوم\n🔢 {qty} كود\n\n"
        f"─────────────────\n"
        f"سعر الوحدة: `{unit_price}` 💎\n"
        f"المجموع: `{subtotal}` 💎{discount_line}{vip_line}\n"
        f"─────────────────\n"
        f"✅ *الإجمالي: `{total}` 💎*\n"
        f"💎 رصيدك: `{user['points']}`\n💵 المتبقي: `{user['points'] - total}`",
        parse_mode="Markdown", reply_markup=kb_confirm())

async def buy_confirm(update, context):
    user_id = update.effective_user.id
    admin = is_admin(user_id)
    try:
        ctx = context.user_data.get("buy", {})
        sub_type = ctx.get("type")
        days = ctx.get("days")
        quantity = ctx.get("quantity")
        total = ctx.get("total")
        if not all([sub_type, days, quantity, total]):
            await update.message.reply_text("❌ بيانات ناقصة.", reply_markup=kb_shop())
            context.user_data["state"] = "shop"
            return
        user = await db.get_user(user_id)
        if not user or user["points"] < total:
            await update.message.reply_text("🔒 نقاط غير كافية.", reply_markup=kb_main(admin))
            return
        info = SUBSCRIPTION_TYPES[sub_type]
        api_plan = info["api_plan"]
        await update.message.reply_text(
            f"⏳ *جاري إنشاء {quantity} كود...*\n\n📦 {info['name']} — {days} يوم",
            parse_mode="Markdown", reply_markup=kb_main(admin))
        codes = []
        failed = 0
        first_error = ""
        for i in range(quantity):
            try:
                result = await api.create(api_plan, days, 1)
                if result.get("ok"):
                    code = extract_code(result.get("data", {}))
                    if code:
                        codes.append(code)
                        await db.save_subscription(user_id, {
                            "code": code, "plan": sub_type, "actual_plan": api_plan,
                            "days": days, "max_uses": 1, "points_spent": 0,
                            "response": result.get("data", {}), "source": "purchase"
                        })
                    else:
                        failed += 1
                        if not first_error:
                            first_error = "لا كود"
                else:
                    failed += 1
                    if not first_error:
                        first_error = result.get("message", "")
            except Exception as e:
                failed += 1
                if not first_error:
                    first_error = str(e)
        if not codes:
            if sub_type == "premium":
                await update.message.reply_text(
                    f"❌ *عذراً، بريميوم غير متوفر حالياً*\n\n`{first_error[:200]}`\n\n💡 جرّب بلس أو برو",
                    parse_mode="Markdown", reply_markup=kb_main(admin))
            else:
                await update.message.reply_text(
                    f"❌ *فشل الإنشاء*\n\n`{first_error[:200]}`",
                    parse_mode="Markdown", reply_markup=kb_main(admin))
            context.user_data.pop("buy", None)
            context.user_data["state"] = "main"
            return
        unit_price = info["prices"][days]
        actual_total, _, _ = calculate_price(unit_price, len(codes))
        tier = get_vip_tier(user["points"])
        vip_discount = VIP_TIERS[tier]["discount"]
        if vip_discount > 0:
            actual_total -= actual_total * vip_discount // 100
        if not await db.deduct_points(user_id, actual_total):
            await update.message.reply_text("⚠️ فشل خصم النقاط.", reply_markup=kb_main(admin))
            return
        await db.update_vip_tier(user_id)
        codes_text = "\n".join([f"`{c}`" for c in codes])
        warning = f"\n\n⚠️ فشل {failed} كود." if failed > 0 else ""
        await update.message.reply_text(
            f"✅ *تم إنشاء {len(codes)} كود!*\n\n"
            f"{info['emoji']} {info['name']} — {days} يوم\n"
            f"💎 خُصم: `{actual_total}` نقطة\n\n"
            f"🔑 *أكوادك:*\n{codes_text}"
            f"{warning}\n\n📖 فعّلها في: {SITE_URL}",
            parse_mode="Markdown", reply_markup=kb_main(admin),
            disable_web_page_preview=True)
        context.user_data.pop("buy", None)
        context.user_data["state"] = "main"
    except Exception as e:
        logger.exception(f"[BUY] خطأ: {e}")
        try:
            await update.message.reply_text(f"❌ خطأ: `{str(e)[:150]}`",
                                              parse_mode="Markdown", reply_markup=kb_main(admin))
        except Exception:
            pass
        context.user_data.pop("buy", None)
        context.user_data["state"] = "main"

# ═══════════════════════════════════════════════════════════════════
# 🔑 إدارة المفاتيح
# ═══════════════════════════════════════════════════════════════════

async def show_keys(update, context):
    if not is_admin(update.effective_user.id):
        return
    keys = await db.list_api_keys()
    active = next((k for k in keys if k["is_active"]), None)
    lines = ["🔑 *المفاتيح*\n"]
    if not keys:
        lines.append("لا توجد مفاتيح.")
    else:
        lines.append(f"🟢 النشط: `{active['label'] if active else '—'}`\n📊 المجموع: {len(keys)}\n")
        for k in keys[:10]:
            s = "🟢" if k["is_active"] else "⚪"
            lines.append(f"{s} #{k['id']} {k.get('label') or '—'}")
    context.user_data["state"] = "keys"
    await update.message.reply_text("\n".join(lines),
                                      parse_mode="Markdown", reply_markup=kb_keys())

async def key_add_begin(update, context):
    context.user_data["state"] = "key_add_value"
    await update.message.reply_text("🔐 أرسل قيمة المفتاح:", reply_markup=kb_cancel())

async def key_add_value(update, context, text):
    if len(text) < 5:
        await update.message.reply_text("❌ قصير:", reply_markup=kb_cancel())
        return
    context.user_data["new_key_value"] = text
    context.user_data["state"] = "key_add_label"
    await update.message.reply_text("✏️ اسم وصفي:", reply_markup=kb_cancel())

async def key_add_label(update, context, text):
    label = text[:50]
    value = context.user_data.pop("new_key_value", None)
    if not value:
        await show_admin(update, context)
        return
    await db.add_api_key(value, label, update.effective_user.id)
    ok, msg = await api.test_key(value)
    await update.message.reply_text(f"✅ حُفظ `{label}`\n{msg}",
                                      parse_mode="Markdown", reply_markup=kb_keys())
    context.user_data["state"] = "keys"

# ═══════════════════════════════════════════════════════════════════
# 🛒 السوق
# ═══════════════════════════════════════════════════════════════════

async def show_market(update, context):
    """عرض السوق"""
    listings = await db.get_active_listings(15)
    context.user_data["state"] = "market"
    
    lines = ["🛒 *السوق*\n"]
    lines.append(f"💡 عمولة البوت: {MARKETPLACE_FEE}%\n")
    
    if not listings:
        lines.append("\n📭 لا توجد منتجات حالياً.")
    else:
        for i, l in enumerate(listings[:10], 1):
            info = SUBSCRIPTION_TYPES.get(l["plan"], {"emoji": "📦", "name": l["plan"]})
            lines.append(f"{i}. {info['emoji']} {info['name']} — {l['days']}ي — 💎 `{l['price']}`")
        if len(listings) > 10:
            lines.append(f"\n... و {len(listings) - 10} أخرى")
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 تصفح المنتجات", callback_data="market_browse")],
        [InlineKeyboardButton("📤 بيع كود", callback_data="market_sell")],
        [InlineKeyboardButton("📋 منتجاتي", callback_data="market_mine")],
    ])
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown",
                                      reply_markup=kb)

async def market_browse_callback(update, context):
    query = update.callback_query
    await query.answer()
    listings = await db.get_active_listings(20)
    
    if not listings:
        await query.edit_message_text("📭 لا توجد منتجات حالياً.",
                                        parse_mode="Markdown")
        return
    
    # عرض 5 منتجات مع أزرار شراء
    kb_rows = []
    for l in listings[:5]:
        info = SUBSCRIPTION_TYPES.get(l["plan"], {"emoji": "📦", "name": l["plan"]})
        kb_rows.append([InlineKeyboardButton(
            f"{info['emoji']} {info['name']} — {l['days']}ي — 💎{l['price']}",
            callback_data=f"market_view_{l['id']}"
        )])
    kb_rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="market_back")])
    
    await query.edit_message_text(
        "🛒 *المنتجات المتاحة:*\n\nاختر منتجاً لعرض التفاصيل:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb_rows))

async def market_view_callback(update, context):
    query = update.callback_query
    await query.answer()
    try:
        listing_id = int(query.data.replace("market_view_", ""))
    except ValueError:
        return
    
    listing = await db.get_listing(listing_id)
    if not listing or listing["status"] != "active":
        await query.edit_message_text("❌ المنتج غير متاح.", parse_mode="Markdown")
        return
    
    info = SUBSCRIPTION_TYPES.get(listing["plan"], {"emoji": "📦", "name": listing["plan"]})
    seller = await db.get_user(listing["seller_id"])
    seller_name = seller.get("first_name") or "بائع" if seller else "بائع"
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🛒 اشترِ بـ {listing['price']} 💎", callback_data=f"market_buy_{listing['id']}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="market_browse")],
    ])
    
    await query.edit_message_text(
        f"🛒 *تفاصيل المنتج*\n\n"
        f"{info['emoji']} *{info['name']}*\n"
        f"📅 {listing['days']} يوم\n"
        f"💰 السعر: `{listing['price']}` 💎\n"
        f"👤 البائع: {seller_name}\n"
        f"⏰ {format_relative_time(listing.get('created_at'))}\n\n"
        f"💡 عند الشراء، تُخصم النقاط ويُسلم الكود فوراً.",
        parse_mode="Markdown", reply_markup=kb)

async def market_buy_callback(update, context):
    query = update.callback_query
    try:
        listing_id = int(query.data.replace("market_buy_", ""))
    except ValueError:
        return
    
    user_id = update.effective_user.id
    ok, result = await db.buy_listing(listing_id, user_id)
    
    if ok:
        await query.answer("✅ تم الشراء!", show_alert=True)
        await query.edit_message_text(
            f"✅ *تم الشراء!*\n\n"
            f"🔑 *كودك:*\n`{result}`\n\n"
            f"📖 فعّله في: {SITE_URL}",
            parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await query.answer(f"❌ {result}", show_alert=True)

async def market_sell_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    subs = await db.get_user_subs(user_id, limit=20)
    
    # الأكواد القابلة للبيع (نشطة، غير مبيعة)
    sellable = [s for s in subs if s["status"] == "active"]
    
    if not sellable:
        await query.edit_message_text(
            "📭 لا تملك أكواداً للبيع.\n\n💡 اشترِ من المتجر أولاً.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="market_back")]]))
        return
    
    kb_rows = []
    for s in sellable[:10]:
        info = SUBSCRIPTION_TYPES.get(s["plan"], {"emoji": "📦", "name": s["plan"]})
        kb_rows.append([InlineKeyboardButton(
            f"{info['emoji']} {info['name']} — {s['days']}ي",
            callback_data=f"market_sell_pick_{s['id']}"
        )])
    kb_rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="market_back")])
    
    await query.edit_message_text(
        "📤 *اختر الكود للبيع:*",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb_rows))

async def market_sell_pick_callback(update, context):
    query = update.callback_query
    await query.answer()
    try:
        sub_id = int(query.data.replace("market_sell_pick_", ""))
    except ValueError:
        return
    
    context.user_data["market_sell_sub_id"] = sub_id
    context.user_data["state"] = "market_sell_price"
    
    await query.edit_message_text(
        "💰 *أرسل سعر البيع بالنقاط*\n\n"
        "📝 الحد الأدنى: 1\n"
        "💡 سيأخذ البوت عمولة 5%\n\n"
        "❌ للإلغاء",
        parse_mode="Markdown")

async def market_sell_receive_price(update, context, text):
    try:
        price = int(text)
        if price < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ رقم صحيح ≥ 1:", reply_markup=kb_cancel())
        return
    
    sub_id = context.user_data.get("market_sell_sub_id")
    if not sub_id:
        await show_market(update, context)
        return
    
    # جلب الاشتراك
    async with aiosqlite.connect(DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        async with db_conn.execute("SELECT * FROM subscriptions WHERE id=?", (sub_id,)) as cur:
            sub = await cur.fetchone()
    
    if not sub:
        await update.message.reply_text("❌ الكود غير موجود.", reply_markup=kb_main(False))
        return
    
    listing_id = await db.create_listing(
        update.effective_user.id, sub_id, sub["code"],
        sub["plan"], sub["days"], price
    )
    
    fee = price * MARKETPLACE_FEE // 100
    net = price - fee
    
    await update.message.reply_text(
        f"✅ *تم النشر!*\n\n"
        f"💰 السعر: `{price}` 💎\n"
        f"💸 العمولة: `{fee}` 💎\n"
        f"💵 صافي الربح: `{net}` 💎\n\n"
        f"📋 رقم المنتج: `#{listing_id}`\n\n"
        f"⏰ ينتهي الإعلان بعد 7 أيام",
        parse_mode="Markdown", reply_markup=kb_main(is_admin(update.effective_user.id)))
    
    context.user_data.pop("market_sell_sub_id", None)
    context.user_data["state"] = "main"

async def market_mine_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    async with aiosqlite.connect(DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        async with db_conn.execute(
            "SELECT * FROM market_listings WHERE seller_id=? AND status='active' ORDER BY id DESC",
            (update.effective_user.id,)
        ) as cur:
            listings = [dict(r) for r in await cur.fetchall()]
    
    if not listings:
        await query.edit_message_text(
            "📭 لا توجد منتجات نشطة.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="market_back")]]))
        return
    
    kb_rows = []
    for l in listings[:10]:
        info = SUBSCRIPTION_TYPES.get(l["plan"], {"emoji": "📦", "name": l["plan"]})
        kb_rows.append([InlineKeyboardButton(
            f"{info['emoji']} {info['name']} — 💎{l['price']}",
            callback_data=f"market_cancel_{l['id']}"
        )])
    kb_rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="market_back")])
    
    await query.edit_message_text(
        "📋 *منتجاتك النشطة:*\n\nاضغط لإلغاء إعلان:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb_rows))

async def market_cancel_callback(update, context):
    query = update.callback_query
    try:
        listing_id = int(query.data.replace("market_cancel_", ""))
    except ValueError:
        return
    
    ok, msg = await db.cancel_listing(listing_id, update.effective_user.id)
    if ok:
        await query.answer("✅ تم الإلغاء", show_alert=True)
        await market_mine_callback(update, context)
    else:
        await query.answer(f"❌ {msg}", show_alert=True)

async def market_back_callback(update, context):
    query = update.callback_query
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        pass
    await show_market(update, context)

# ═══════════════════════════════════════════════════════════════════
# 🥚 دروب بيضاوي (Egg Drop)
# ═══════════════════════════════════════════════════════════════════

async def handle_egg_open(update, context, drop):
    """فتح دروب بيضاوي - يختار جائزة عشوائية"""
    user = update.effective_user
    admin = is_admin(user.id)
    
    if not drop["is_active"] or drop.get("claimed_by"):
        await update.message.reply_text("😔 *حظاً أوفر!*",
                                          parse_mode="Markdown", reply_markup=kb_main(admin))
        return
    
    # جلب محتويات البيضة المتاحة
    contents = await db.get_egg_contents(drop["id"])
    
    if not contents:
        await update.message.reply_text("⚠️ *البيضة فارغة!*\n\nأبلغ المشرف.",
                                          parse_mode="Markdown", reply_markup=kb_main(admin))
        return
    
    # اختيار عشوائي حسب الاحتمالات
    total_prob = sum(c["probability"] for c in contents)
    rand = random.uniform(0, total_prob)
    cumulative = 0
    chosen = contents[0]
    for c in contents:
        cumulative += c["probability"]
        if rand <= cumulative:
            chosen = c
            break
    
    # تنفيذ الجائزة
    await update.message.reply_text(
        f"🥚 *جاري فتح البيضة...*\n\n"
        f"🎲 اللحظة الحاسمة...",
        parse_mode="Markdown", reply_markup=kb_main(admin))
    
    await asyncio.sleep(1.5)
    
    prize_type = chosen["prize_type"]
    prize_value = chosen["prize_value"]
    
    # تسجيل الجائزة كمستخدمة
    await db.claim_egg_content(chosen["id"], user.id)
    await db.claim_drop(drop["token"], user.id, prize_value or "")
    await db.add_drop_winner(drop["id"], user.id, 1, prize_value or "")
    
    # نفيذ الجائزة
    if prize_type == "points":
        amount = int(prize_value) if prize_value else 0
        await db.add_points(user.id, amount, "egg_prize", drop["id"])
        await db.update_vip_tier(user.id)
        await update.message.reply_text(
            f"🎉 *مبروك!*\n\n"
            f"💰 فزت بـ `{amount}` نقطة!\n\n"
            f"💎 رصيدك الآن: `{(await db.get_user(user.id))['points']}`",
            parse_mode="Markdown", reply_markup=kb_main(admin))
    
    elif prize_type == "subscription":
        # prize_value = "plan:days" مثل "plus:30"
        try:
            plan, days = prize_value.split(":")
            days = int(days)
        except Exception:
            await update.message.reply_text("⚠️ جائزة غير صالحة", reply_markup=kb_main(admin))
            return
        
        drop_info = SUBSCRIPTION_TYPES.get(plan, {})
        api_plan = drop_info.get("api_plan", plan)
        result = await api.create(api_plan, days, 1)
        if result["ok"]:
            code = extract_code(result["data"])
            if code:
                await db.save_subscription(user.id, {
                    "code": code, "plan": plan, "actual_plan": api_plan,
                    "days": days, "max_uses": 1, "points_spent": 0,
                    "response": result["data"], "source": "egg"
                })
                info = SUBSCRIPTION_TYPES.get(plan, {"emoji": "📦", "name": plan})
                await update.message.reply_text(
                    f"🎉 *مبروك!*\n\n"
                    f"{info['emoji']} *{info['name']}*\n📅 {days} يوم\n"
                    f"🔑 *كودك:* `{code}`\n\n"
                    f"📖 فعّله في: {SITE_URL}",
                    parse_mode="Markdown", reply_markup=kb_main(admin),
                    disable_web_page_preview=True)
            else:
                await update.message.reply_text("⚠️ فشل إنشاء الكود", reply_markup=kb_main(admin))
        else:
            await update.message.reply_text(f"⚠️ {result.get('message')}", reply_markup=kb_main(admin))
    
    else:
        # حظاً أوفر
        await update.message.reply_text(
            f"😔 *حظاً أوفر!*\n\n"
            f"البيضة كانت فارغة هذه المرة.\n"
            f"💡 جرّب مرة أخرى!",
            parse_mode="Markdown", reply_markup=kb_main(admin))
    
    # تحديث البطاقة
    await refresh_drop_immediately(context, drop["id"])

# ═══════════════════════════════════════════════════════════════════
# 🔒 دروب بشرط (Conditional Drop)
# ═══════════════════════════════════════════════════════════════════

async def check_drop_conditions(user_id, conditions):
    """يفحص إذا المستخدم يستوفي الشروط"""
    user = await db.get_user(user_id)
    if not user:
        return False, "المستخدم غير موجود"
    
    results = []
    
    # شرط: عدد الدعوات
    if conditions.get("min_invites"):
        async with aiosqlite.connect(DB_PATH) as db_conn:
            async with db_conn.execute(
                "SELECT COUNT(*) FROM users WHERE invited_by=?", (user_id,)
            ) as cur:
                invites_count = (await cur.fetchone())[0]
        if invites_count < conditions["min_invites"]:
            results.append(f"❌ تحتاج {conditions['min_invites']} دعوة (لديك: {invites_count})")
        else:
            results.append(f"✅ الدعوات: {invites_count}/{conditions['min_invites']}")
    
    # شرط: عدد الشراءات
    if conditions.get("min_purchases"):
        async with aiosqlite.connect(DB_PATH) as db_conn:
            async with db_conn.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE user_id=? AND source='purchase'",
                (user_id,)
            ) as cur:
                purchases = (await cur.fetchone())[0]
        if purchases < conditions["min_purchases"]:
            results.append(f"❌ تحتاج {conditions['min_purchases']} شراء (لديك: {purchases})")
        else:
            results.append(f"✅ الشراءات: {purchases}/{conditions['min_purchases']}")
    
    # شرط: النقاط
    if conditions.get("min_points"):
        if user["points"] < conditions["min_points"]:
            results.append(f"❌ تحتاج {conditions['min_points']} نقطة (لديك: {user['points']})")
        else:
            results.append(f"✅ النقاط: {user['points']}/{conditions['min_points']}")
    
    # شرط: مستوى VIP
    if conditions.get("vip_tier"):
        current_tier = get_vip_tier(user["points"])
        tier_order = ["bronze", "silver", "gold", "platinum"]
        required_idx = tier_order.index(conditions["vip_tier"]) if conditions["vip_tier"] in tier_order else 0
        current_idx = tier_order.index(current_tier)
        if current_idx < required_idx:
            tier_name = VIP_TIERS.get(conditions["vip_tier"], {}).get("name", conditions["vip_tier"])
            current_name = VIP_TIERS.get(current_tier, {}).get("name", current_tier)
            results.append(f"❌ تحتاج مستوى {tier_name} (لديك: {current_name})")
        else:
            results.append(f"✅ مستوى VIP: {VIP_TIERS[current_tier]['name']}")
    
    # التحقق النهائي
    has_failure = any(r.startswith("❌") for r in results)
    details = "\n".join(results) if results else "✅ لا شروط"
    return not has_failure, details

async def handle_conditional_open(update, context, drop):
    """فتح دروب بشرط"""
    user = update.effective_user
    admin = is_admin(user.id)
    
    if not drop["is_active"] or drop.get("claimed_by"):
        await update.message.reply_text("😔 *حظاً أوفر!*",
                                          parse_mode="Markdown", reply_markup=kb_main(admin))
        return
    
    conditions = json.loads(drop.get("conditions", "{}"))
    passed, details = await check_drop_conditions(user.id, conditions)
    
    if not passed:
        await update.message.reply_text(
            f"🔒 *لا تستوفي الشروط*\n\n"
            f"📋 *تفاصيل:*\n{details}\n\n"
            f"💡 أكمل الشروط ثم حاول مجدداً.",
            parse_mode="Markdown", reply_markup=kb_main(admin))
        return
    
    # اجتاز الشروط - إنشاء كود
    drop_info = SUBSCRIPTION_TYPES.get(drop["plan"], {})
    api_plan = drop_info.get("api_plan", drop["plan"])
    await update.message.reply_text("🎁 جاري إنشاء كودك...", reply_markup=kb_main(admin))
    result = await api.create(api_plan, drop["days"], 1)
    if not result["ok"]:
        await update.message.reply_text(f"❌ فشل: {result.get('message')}",
                                          reply_markup=kb_main(admin))
        return
    code = extract_code(result["data"])
    if not code:
        await update.message.reply_text("⚠️ الكود مفقود.", reply_markup=kb_main(admin))
        return
    await db.claim_drop(drop["token"], user.id, code)
    await db.add_drop_winner(drop["id"], user.id, 1, code)
    await db.save_subscription(user.id, {
        "code": code, "plan": drop["plan"], "actual_plan": api_plan,
        "days": drop["days"], "max_uses": 1, "points_spent": 0,
        "response": result["data"], "source": "conditional"
    })
    await refresh_drop_immediately(context, drop["id"])
    info = SUBSCRIPTION_TYPES.get(drop["plan"], {"emoji": "📦", "name": drop["plan"]})
    await update.message.reply_text(
        f"🎉 *مبروك! استوفيت الشروط!*\n\n"
        f"{info['emoji']} {info['name']}\n📅 {drop['days']} يوم\n"
        f"🔑 *كودك:* `{code}`\n\n📖 فعّله في: {SITE_URL}",
        parse_mode="Markdown", reply_markup=kb_main(admin),
        disable_web_page_preview=True)

# ═══════════════════════════════════════════════════════════════════
# 🔗 دروب تسلسلي (Chain Drop)
# ═══════════════════════════════════════════════════════════════════

async def handle_chain_open(update, context, drop):
    """فتح دروب تسلسلي - ينشئ الدروب التالي تلقائياً"""
    user = update.effective_user
    admin = is_admin(user.id)
    
    if not drop["is_active"] or drop.get("claimed_by"):
        await update.message.reply_text("😔 *حظاً أوفر!*",
                                          parse_mode="Markdown", reply_markup=kb_main(admin))
        return
    
    drop_info = SUBSCRIPTION_TYPES.get(drop["plan"], {})
    api_plan = drop_info.get("api_plan", drop["plan"])
    await update.message.reply_text("🎁 جاري إنشاء كودك...", reply_markup=kb_main(admin))
    result = await api.create(api_plan, drop["days"], 1)
    if not result["ok"]:
        await update.message.reply_text(f"❌ فشل: {result.get('message')}",
                                          reply_markup=kb_main(admin))
        return
    code = extract_code(result["data"])
    if not code:
        await update.message.reply_text("⚠️ الكود مفقود.", reply_markup=kb_main(admin))
        return
    await db.claim_drop(drop["token"], user.id, code)
    await db.add_drop_winner(drop["id"], user.id, 1, code)
    await db.save_subscription(user.id, {
        "code": code, "plan": drop["plan"], "actual_plan": api_plan,
        "days": drop["days"], "max_uses": 1, "points_spent": 0,
        "response": result["data"], "source": "chain"
    })
    
    # فتح الدروب التالي إن وُجد
    next_drop_id = drop.get("next_drop_id")
    next_drop_token = None
    
    if next_drop_id:
        next_drop = await db.get_drop_by_id(next_drop_id)
        if next_drop and next_drop["is_active"]:
            next_drop_token = next_drop["token"]
            # تفعيل الدروب التالي (نشره)
            try:
                channels = await db.list_channels()
                for ch in channels:
                    sent = await context.bot.send_message(
                        chat_id=ch["chat_id"],
                        text=build_drop_card_text(next_drop),
                        reply_markup=build_drop_card_kb(next_drop, context.bot.username),
                        parse_mode="Markdown")
                    await db.save_drop_message(next_drop["id"], ch["chat_id"], sent.message_id)
            except Exception as e:
                logger.error(f"فشل نشر الدروب التالي: {e}")
    
    await refresh_drop_immediately(context, drop["id"])
    info = SUBSCRIPTION_TYPES.get(drop["plan"], {"emoji": "📦", "name": drop["plan"]})
    
    message = (
        f"🎉 *مبروك!*\n\n"
        f"{info['emoji']} {info['name']}\n📅 {drop['days']} يوم\n"
        f"🔑 *كودك:* `{code}`\n\n"
    )
    
    if next_drop_token:
        next_link = f"https://t.me/{context.bot.username}?start=drop_{next_drop_token}"
        message += (
            f"━━━━━━━━━━━━━━━━━\n"
            f"🔗 *الدروب التالي فُتح!*\n"
            f"🎁 سارع بفتحه:\n`{next_link}`\n"
            f"━━━━━━━━━━━━━━━━━"
        )
    
    message += f"\n\n📖 فعّل كودك في: {SITE_URL}"
    await update.message.reply_text(message, parse_mode="Markdown",
                                      reply_markup=kb_main(admin),
                                      disable_web_page_preview=True)

# ═══════════════════════════════════════════════════════════════════
# 🗳️ دروب بتصويت (Vote Drop)
# ═══════════════════════════════════════════════════════════════════

async def handle_vote_open(update, context, drop):
    """عرض خيارات التصويت"""
    user = update.effective_user
    admin = is_admin(user.id)
    
    if not drop["is_active"]:
        await update.message.reply_text("😔 *التصويت انتهى*",
                                          parse_mode="Markdown", reply_markup=kb_main(admin))
        return
    
    # هل صوّت من قبل؟
    if await db.has_voted(drop["id"], user.id):
        await update.message.reply_text("✅ *لقد صوّت مسبقاً!*",
                                          parse_mode="Markdown", reply_markup=kb_main(admin))
        return
    
    options = await db.get_vote_options(drop["id"])
    if not options:
        await update.message.reply_text("⚠️ لا توجد خيارات تصويت.",
                                          reply_markup=kb_main(admin))
        return
    
    kb_rows = []
    total_votes = sum(o["votes_count"] for o in options) or 1
    for opt in options:
        pct = opt["votes_count"] * 100 // total_votes
        kb_rows.append([InlineKeyboardButton(
            f"{opt['option_name']} — {opt['votes_count']} صوت ({pct}%)",
            callback_data=f"cast_vote_{drop['id']}_{opt['option_key']}"
        )])
    
    await update.message.reply_text(
        f"🗳️ *دروب بتصويت*\n\n"
        f"📦 {SUBSCRIPTION_TYPES.get(drop['plan'], {}).get('name', drop['plan'])}\n"
        f"📅 {drop['days']} يوم\n\n"
        f"💡 *صوّت على نوع الباقة الذي تريده*\n"
        f"الأكثر تصويتاً يفوز!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_rows))

async def cast_vote_callback(update, context):
    """تنفيذ التصويت"""
    query = update.callback_query
    parts = query.data.replace("cast_vote_", "").split("_")
    try:
        drop_id = int(parts[0])
        option_key = "_".join(parts[1:])
    except Exception:
        await query.answer("❌ خطأ", show_alert=True)
        return
    
    ok = await db.cast_vote(drop_id, update.effective_user.id, option_key)
    if ok:
        await query.answer("✅ تم تسجيل صوتك!", show_alert=True)
        # تحديث الخيارات
        options = await db.get_vote_options(drop_id)
        total_votes = sum(o["votes_count"] for o in options) or 1
        kb_rows = []
        for opt in options:
            pct = opt["votes_count"] * 100 // total_votes
            kb_rows.append([InlineKeyboardButton(
                f"{opt['option_name']} — {opt['votes_count']} صوت ({pct}%)",
                callback_data=f"cast_vote_{drop_id}_{opt['option_key']}"
            )])
        try:
            await query.edit_message_reply_markup(InlineKeyboardMarkup(kb_rows))
        except Exception:
            pass
    else:
        await query.answer("❌ صوّت مسبقاً", show_alert=True)

# ═══════════════════════════════════════════════════════════════════
# 🔨 دروب بمزاد (Auction Drop)
# ═══════════════════════════════════════════════════════════════════

async def handle_auction_open(update, context, drop):
    """عرض تفاصيل المزاد"""
    user = update.effective_user
    admin = is_admin(user.id)
    
    auction = await db.get_auction_by_drop(drop["id"])
    if not auction:
        await update.message.reply_text("⚠️ المزاد غير موجود.",
                                          reply_markup=kb_main(admin))
        return
    
    if auction["is_closed"]:
        winner = auction.get("current_bidder")
        await update.message.reply_text(
            f"🔨 *المزاد انتهى*\n\n"
            f"👤 الفائز: `{winner}`\n"
            f"💰 السعر: `{auction['current_bid']}` نقطة",
            parse_mode="Markdown", reply_markup=kb_main(admin))
        return
    
    # تحقق من الوقت
    try:
        end_dt = datetime.fromisoformat(auction["ends_at"])
        remaining = end_dt - datetime.now()
        if remaining.total_seconds() <= 0:
            await update.message.reply_text("⏰ *انتهى وقت المزاد*",
                                              parse_mode="Markdown", reply_markup=kb_main(admin))
            return
        time_str = f"{remaining.seconds // 3600}س {(remaining.seconds % 3600) // 60}د"
    except Exception:
        time_str = "?"
    
    drop["_auction"] = auction
    plan_info = SUBSCRIPTION_TYPES.get(drop["plan"], {"emoji": "📦", "name": drop["plan"]})
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 زايد الآن", callback_data=f"bid_{drop['id']}")],
    ])
    
    await update.message.reply_text(
        f"🔨 *مزاد #{drop['token']}*\n\n"
        f"{plan_info['emoji']} {plan_info['name']}\n"
        f"📅 {drop['days']} يوم\n"
        f"💎 القيمة: `{plan_info['prices'].get(drop['days'], '?')}`\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"💰 السعر الحالي: `{auction['current_bid']}` نقطة\n"
        f"👤 أعلى مزايد: `{auction.get('current_bidder') or '—'}`\n"
        f"📈 الحد الأدنى للزيادة: `{auction['min_increment']}`\n"
        f"⏱️ متبقٍ: {time_str}\n"
        f"━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown", reply_markup=kb)

async def bid_callback(update, context):
    """بدء مزايدة"""
    query = update.callback_query
    try:
        drop_id = int(query.data.replace("bid_", ""))
    except ValueError:
        return
    
    drop = await db.get_drop_by_id(drop_id)
    if not drop:
        await query.answer("❌ غير موجود", show_alert=True)
        return
    
    auction = await db.get_auction_by_drop(drop_id)
    if not auction or auction["is_closed"]:
        await query.answer("❌ المزاد مغلق", show_alert=True)
        return
    
    # تحقق من الوقت
    try:
        end_dt = datetime.fromisoformat(auction["ends_at"])
        if datetime.now() > end_dt:
            await query.answer("⏰ انتهى المزاد", show_alert=True)
            return
    except Exception:
        pass
    
    context.user_data["auction_bid_drop_id"] = drop_id
    context.user_data["state"] = "auction_bid_amount"
    
    min_bid = auction["current_bid"] + auction["min_increment"]
    
    await query.message.reply_text(
        f"💰 *المزايدة*\n\n"
        f"📊 السعر الحالي: `{auction['current_bid']}` 💎\n"
        f"📈 الحد الأدنى لمزايدتك: `{min_bid}` 💎\n\n"
        f"أرسل مبلغ مزايدتك:\n\n❌ للإلغاء",
        parse_mode="Markdown", reply_markup=kb_cancel())

async def auction_bid_receive(update, context, text):
    """استقبال مبلغ المزايدة"""
    try:
        amount = int(text)
    except ValueError:
        await update.message.reply_text("❌ رقم غير صالح:", reply_markup=kb_cancel())
        return
    
    drop_id = context.user_data.get("auction_bid_drop_id")
    if not drop_id:
        await show_home(update, context)
        return
    
    drop = await db.get_drop_by_id(drop_id)
    auction = await db.get_auction_by_drop(drop_id)
    if not auction or auction["is_closed"]:
        await update.message.reply_text("❌ المزاد مغلق.",
                                          reply_markup=kb_main(is_admin(update.effective_user.id)))
        context.user_data["state"] = "main"
        return
    
    min_bid = auction["current_bid"] + auction["min_increment"]
    if amount < min_bid:
        await update.message.reply_text(
            f"❌ *مزايدة منخفضة*\n\nالحد الأدنى: `{min_bid}` 💎",
            parse_mode="Markdown", reply_markup=kb_cancel())
        return
    
    user = await db.get_user(update.effective_user.id)
    if user["points"] < amount:
        await update.message.reply_text(
            f"❌ *نقاطك غير كافية*\n\nرصيدك: `{user['points']}` 💎",
            parse_mode="Markdown", reply_markup=kb_cancel())
        return
    
    # خصم المزايدة السابقة إذا كان المستخدم نفسه
    if auction["current_bidder"] == update.effective_user.id and auction["current_bid"] > 0:
        await db.add_points(update.effective_user.id, auction["current_bid"], "auction_refund", drop_id)
    
    # خصم المبلغ الجديد
    if not await db.deduct_points(update.effective_user.id, amount):
        await update.message.reply_text("❌ فشل الخصم.", reply_markup=kb_main(False))
        return
    
    await db.place_bid(auction["id"], update.effective_user.id, amount)
    
    await update.message.reply_text(
        f"✅ *تم تسجيل مزايدتك!*\n\n"
        f"💰 `{amount}` نقطة\n\n"
        f"⚠️ *تنبيه:* إذا زايدك شخص آخر، تُرجع نقاطك تلقائياً.",
        parse_mode="Markdown", reply_markup=kb_main(is_admin(update.effective_user.id)))
    
    context.user_data.pop("auction_bid_drop_id", None)
    context.user_data["state"] = "main"
    
    # تحديث البطاقة
    await refresh_drop_immediately(context, drop_id)

# ═══════════════════════════════════════════════════════════════════
# ⏰ إغلاق المزادات المنتهية تلقائياً
# ═══════════════════════════════════════════════════════════════════

async def auto_close_auctions(context):
    """يُغلق المزادات المنتهية تلقائياً"""
    try:
        auctions = await db.get_active_auctions()
        now = datetime.now()
        
        for auction in auctions:
            try:
                end_dt = datetime.fromisoformat(auction["ends_at"])
                if now >= end_dt:
                    # إغلاق المزاد
                    await db.close_auction(auction["id"])
                    
                    drop = await db.get_drop_by_id(auction["drop_id"])
                    if not drop:
                        continue
                    
                    winner_id = auction["current_bidder"]
                    if not winner_id:
                        # لا مزايد - المزاد فشل
                        logger.info(f"⚠️ مزاد #{drop['token']} انتهى بدون مزايدات")
                        await refresh_drop_immediately(context, drop["id"])
                        continue
                    
                    # توليد الكود للفائز
                    drop_info = SUBSCRIPTION_TYPES.get(drop["plan"], {})
                    api_plan = drop_info.get("api_plan", drop["plan"])
                    result = await api.create(api_plan, drop["days"], 1)
                    
                    if result["ok"]:
                        code = extract_code(result["data"])
                        if code:
                            await db.claim_drop(drop["token"], winner_id, code)
                            await db.save_subscription(winner_id, {
                                "code": code, "plan": drop["plan"], "actual_plan": api_plan,
                                "days": drop["days"], "max_uses": 1, "points_spent": auction["current_bid"],
                                "response": result["data"], "source": "auction"
                            })
                            await db.add_drop_winner(drop["id"], winner_id, 1, code)
                            
                            # إشعار الفائز
                            try:
                                await context.bot.send_message(
                                    winner_id,
                                    f"🔨 *مبروك! فزت بالمزاد!*\n\n"
                                    f"🔑 *كودك:* `{code}`\n"
                                    f"💰 المبلغ المدفوع: `{auction['current_bid']}` نقطة\n\n"
                                    f"📖 فعّله في: {SITE_URL}",
                                    parse_mode="Markdown",
                                    disable_web_page_preview=True
                                )
                            except Exception:
                                pass
                            
                            logger.info(f"✅ مزاد #{drop['token']} انتهى - الفائز: {winner_id}")
                    
                    await refresh_drop_immediately(context, drop["id"])
            except Exception as e:
                logger.error(f"خطأ في إغلاق مزاد {auction['id']}: {e}")
    except Exception as e:
        logger.error(f"فشل فحص المزادات: {e}")

# ═══════════════════════════════════════════════════════════════════
# ⏰ الدروبات المجدولة
# ═══════════════════════════════════════════════════════════════════

async def check_scheduled_drops(context):
    """يفحص الدروبات المجدولة وينشر المستحق منها"""
    try:
        due = await db.get_due_scheduled_drops()
        for sched in due:
            try:
                # إنشاء دروب
                token = await db.create_drop(
                    sched["plan"], sched["days"], sched["created_by"]
                )
                drop = await db.get_drop(token)
                
                # نشر في كل القنوات
                channels = await db.list_channels()
                for ch in channels:
                    try:
                        sent = await context.bot.send_message(
                            chat_id=ch["chat_id"],
                            text=build_drop_card_text(drop),
                            reply_markup=build_drop_card_kb(drop, context.bot.username),
                            parse_mode="Markdown")
                        await db.save_drop_message(drop["id"], ch["chat_id"], sent.message_id)
                    except Exception as e:
                        logger.error(f"فشل نشر مجدول في {ch['title']}: {e}")
                
                # تحديث next_run
                next_run = (datetime.now() + timedelta(minutes=sched["interval_minutes"])).isoformat()
                await db.update_scheduled_next_run(sched["id"], next_run)
                
                logger.info(f"✅ دروب مجدول نُشر: #{token}")
            except Exception as e:
                logger.error(f"فشل دروب مجدول {sched['id']}: {e}")
    except Exception as e:
        logger.error(f"فشل فحص المجدولة: {e}")

# ═══════════════════════════════════════════════════════════════════
# 🛡️ لوحة المشرف
# ═══════════════════════════════════════════════════════════════════

async def show_admin(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 للمشرفين فقط", reply_markup=kb_main(False))
        return
    context.user_data["state"] = "admin"
    await update.message.reply_text("🛡️ *لوحة المشرف*",
                                      parse_mode="Markdown", reply_markup=kb_admin())

async def show_channels(update, context):
    if not is_admin(update.effective_user.id):
        return
    channels = await db.list_channels(only_active=False)
    lines = ["📢 *إدارة القنوات*\n"]
    if not channels:
        lines.append("لا توجد قنوات بعد.")
        lines.append("\n💡 أضف البوت كأدمن في أي قناة/مجموعة")
    else:
        lines.append(f"📊 الإجمالي: {len(channels)}\n")
        for ch in channels[:15]:
            status = "✅" if ch["is_active"] else "❌"
            primary = " ⭐" if ch["is_primary"] else ""
            name = ch["title"] or (f"@{ch['username']}" if ch["username"] else str(ch["chat_id"]))
            lines.append(f"{status} *{name}*{primary}\n   🎁 {ch.get('total_drops', 0)} دروب")
    lines.append("\n💡 أضف البوت كأدمن في أي قناة/مجموعة لينشر تلقائياً")
    context.user_data["state"] = "channels"
    await update.message.reply_text("\n".join(lines),
                                      parse_mode="Markdown", reply_markup=kb_admin())

async def show_drops(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "drops"
    drops = await db.get_admin_drops(10)
    lines = ["🎁 *دروب الاشتراكات*\n"]
    if not drops:
        lines.append("لا توجد دروبات.")
    else:
        for d in drops[:10]:
            info = SUBSCRIPTION_TYPES.get(d["plan"], {"emoji": "📦", "name": d["plan"]})
            status = "🟢" if (d["is_active"] and not d["claimed_by"]) else "🔴"
            drop_type = d.get("drop_type", "normal")
            type_emoji = {"normal": "", "egg": "🥚", "conditional": "🔒",
                          "chain": "🔗", "vote": "🗳️", "auction": "🔨"}.get(drop_type, "")
            lines.append(f"{status} {type_emoji} #{d['token']} — {info['emoji']} {info['name']} — {d['days']}ي")
    lines.append("\n💡 اختر نوع الدروب من الأزرار")
    await update.message.reply_text("\n".join(lines),
                                      parse_mode="Markdown", reply_markup=kb_drops())

async def show_all_drops(update, context):
    """كل الدروبات مع تفاصيل"""
    if not is_admin(update.effective_user.id):
        return
    drops = await db.get_admin_drops(50)
    lines = [f"📋 *كل الدروبات* ({len(drops)})\n"]
    if not drops:
        lines.append("لا توجد دروبات.")
    else:
        for d in drops[:20]:
            info = SUBSCRIPTION_TYPES.get(d["plan"], {"emoji": "📦", "name": d["plan"]})
            status = "🟢" if (d["is_active"] and not d["claimed_by"]) else "🔴"
            drop_type = d.get("drop_type", "normal")
            type_emoji = {"normal": "🎁", "egg": "🥚", "conditional": "🔒",
                          "chain": "🔗", "vote": "🗳️", "auction": "🔨"}.get(drop_type, "🎁")
            lines.append(f"{status} {type_emoji} #{d['token']}")
            lines.append(f"   {info['emoji']} {info['name']} — {d['days']}ي")
            lines.append(f"   ⏰ {format_relative_time(d['created_at'])}")
        if len(drops) > 20:
            lines.append(f"\n... و {len(drops) - 20} أخرى")
    await update.message.reply_text("\n".join(lines),
                                      parse_mode="Markdown", reply_markup=kb_drops())

async def show_pdrops(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "pdrops"
    await update.message.reply_text(
        "💎 *دروب النقاط*\n\nأنشئ رابطاً يفتح لأول شخص فقط.",
        parse_mode="Markdown", reply_markup=kb_pdrops())

async def show_scheduled(update, context):
    """عرض الدروبات المجدولة"""
    if not is_admin(update.effective_user.id):
        return
    async with aiosqlite.connect(DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        async with db_conn.execute("SELECT * FROM scheduled_drops ORDER BY id DESC LIMIT 10") as cur:
            scheds = [dict(r) for r in await cur.fetchall()]
    
    lines = ["⏰ *الدروبات المجدولة*\n"]
    if not scheds:
        lines.append("لا توجد دروبات مجدولة.")
        lines.append("\n💡 اضغط ➕ لإضافة")
    else:
        for s in scheds[:10]:
            info = SUBSCRIPTION_TYPES.get(s["plan"], {"emoji": "📦", "name": s["plan"]})
            status = "🟢" if s["is_active"] else "🔴"
            next_run = format_date(s.get("next_run"))
            lines.append(f"{status} {info['emoji']} {info['name']} — {s['days']}ي")
            lines.append(f"   كل {s['interval_minutes']} دقيقة | التالي: {next_run}")
    kb = ReplyKeyboardMarkup([
        [KeyboardButton(BTN_SCHEDULED_ADD)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)
    context.user_data["state"] = "scheduled"
    await update.message.reply_text("\n".join(lines),
                                      parse_mode="Markdown", reply_markup=kb)

async def show_stats(update, context):
    if not is_admin(update.effective_user.id):
        return
    users = await db.count_users()
    subs = await db.count_subscriptions()
    keys = await db.list_api_keys()
    channels = await db.list_channels()
    total_drops = await db.count_drops()
    claimed_drops = await db.count_claimed_drops()
    
    # إيرادات (نقاط مستهلكة)
    async with aiosqlite.connect(DB_PATH) as db_conn:
        async with db_conn.execute("SELECT SUM(total_points_spent) FROM users") as cur:
            total_spent = (await cur.fetchone())[0] or 0
    
    active_drops = total_drops - claimed_drops
    
    txt = (
        f"📊 *إحصائيات شاملة*\n\n"
        f"👥 *المستخدمون:* `{users}`\n"
        f"📦 *الاشتراكات:* `{subs}`\n"
        f"🔑 *المفاتيح:* `{len(keys)}`\n"
        f"📢 *القنوات:* `{len(channels)}`\n"
        f"💎 *النقاط المستهلكة:* `{total_spent}`\n\n"
        f"🎁 *الدروبات:*\n"
        f"  🟢 نشطة: `{active_drops}`\n"
        f"  🔴 مُستخدمة: `{claimed_drops}`\n"
        f"  📊 المجموع: `{total_drops}`"
    )
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb_admin())

async def show_logs(update, context):
    if not is_admin(update.effective_user.id):
        return
    logs = await db.recent_logs(15)
    lines = ["📜 *السجل:*\n"]
    for l in logs:
        lines.append(f"`{l['created_at'][11:19]}` {l['action']}")
    await update.message.reply_text("\n".join(lines) or "لا سجلات",
                                      parse_mode="Markdown", reply_markup=kb_admin())

async def show_broadcast_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "broadcast_message"
    await update.message.reply_text(
        "📢 *البث الجماعي*\n\nأرسل الرسالة التي تريد إرسالها لكل المستخدمين:\n\n❌ للإلغاء",
        parse_mode="Markdown", reply_markup=kb_cancel())

async def broadcast_send(update, context, message):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    wait_msg = await update.message.reply_text("📢 جاري البث...")
    user_ids = await db.all_user_ids()
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, message)
            sent += 1
            await asyncio.sleep(0.05)  # تجنب rate limit
        except Exception:
            failed += 1
    await wait_msg.edit_text(
        f"✅ *اكتمل البث*\n\n"
        f"✅ نجح: `{sent}`\n"
        f"❌ فشل: `{failed}`\n"
        f"📊 المجموع: `{len(user_ids)}`",
        parse_mode="Markdown")
    context.user_data["state"] = "admin"

# ═══════════════════════════════════════════════════════════════════
# 🎁 إنشاء الدروبات (كل الأنواع)
# ═══════════════════════════════════════════════════════════════════

async def drop_create_begin(update, context):
    """إنشاء دروب عادي"""
    if not is_admin(update.effective_user.id):
        return
    channels = await db.list_channels()
    if not channels:
        await update.message.reply_text(
            "⚠️ *لا توجد قنوات*\n\n"
            "أضف البوت كأدمن في قناة/مجموعة أولاً.",
            parse_mode="Markdown", reply_markup=kb_drops())
        return
    context.user_data["drop_type"] = "normal"
    context.user_data["state"] = "drop_choose_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text("🎁 اختر النوع:",
                                      reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))

async def egg_drop_create_begin(update, context):
    """إنشاء دروب بيضاوي"""
    if not is_admin(update.effective_user.id):
        return
    context.user_data["drop_type"] = "egg"
    context.user_data["state"] = "drop_choose_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text("🥚 *دروب بيضاوي*\n\nاختر نوع الباقة للجائزة:",
                                      parse_mode="Markdown",
                                      reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))

async def conditional_drop_create_begin(update, context):
    """إنشاء دروب بشرط"""
    if not is_admin(update.effective_user.id):
        return
    context.user_data["drop_type"] = "conditional"
    context.user_data["state"] = "drop_choose_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text("🔒 *دروب بشرط*\n\nاختر نوع الباقة:",
                                      parse_mode="Markdown",
                                      reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))

async def chain_drop_create_begin(update, context):
    """إنشاء دروب تسلسلي"""
    if not is_admin(update.effective_user.id):
        return
    context.user_data["drop_type"] = "chain"
    context.user_data["state"] = "drop_choose_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text("🔗 *دروب تسلسلي*\n\nاختر نوع الباقة:",
                                      parse_mode="Markdown",
                                      reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))

async def vote_drop_create_begin(update, context):
    """إنشاء دروب بتصويت"""
    if not is_admin(update.effective_user.id):
        return
    context.user_data["drop_type"] = "vote"
    context.user_data["state"] = "drop_choose_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text("🗳️ *دروب بتصويت*\n\nاختر نوع الباقة:",
                                      parse_mode="Markdown",
                                      reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))

async def auction_drop_create_begin(update, context):
    """إنشاء دروب بمزاد"""
    if not is_admin(update.effective_user.id):
        return
    context.user_data["drop_type"] = "auction"
    context.user_data["state"] = "drop_choose_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text("🔨 *دروب بمزاد*\n\nاختر نوع الباقة:",
                                      parse_mode="Markdown",
                                      reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))

async def drop_choose_type(update, context, text):
    """عند اختيار نوع الباقة للدروب"""
    sub_type = text.replace("drop:", "")
    if sub_type not in SUBSCRIPTION_TYPES:
        return
    context.user_data["drop_plan"] = sub_type
    context.user_data["state"] = "drop_choose_days"
    info = SUBSCRIPTION_TYPES[sub_type]
    days = list(info["prices"].keys())
    rows = []
    if len(days) >= 2:
        rows.append([KeyboardButton(f"{d} يوم") for d in days[:2]])
    if len(days) > 2:
        rows.append([KeyboardButton(f"{d} يوم") for d in days[2:]])
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text(f"{info['emoji']} {info['name']}\n\nاختر المدة:",
                                      reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))

async def drop_choose_days(update, context, text):
    """بعد اختيار المدة - ينفذ حسب نوع الدروب"""
    try:
        days = int(text.replace("يوم", "").replace("أيام", "").strip())
    except ValueError:
        return
    plan = context.user_data.get("drop_plan")
    if not plan:
        await show_admin(update, context)
        return
    
    drop_type = context.user_data.get("drop_type", "normal")
    context.user_data["drop_days"] = days
    
    # حسب النوع
    if drop_type == "normal":
        await create_normal_drop(update, context, plan, days)
    elif drop_type == "egg":
        context.user_data["state"] = "egg_setup"
        await update.message.reply_text(
            f"🥚 *إعداد البيضة*\n\n"
            f"📦 {SUBSCRIPTION_TYPES[plan]['name']} — {days}ي\n\n"
            f"أرسل محتويات البيضة (كل سطر جائزة):\n\n"
            f"*الصيغة:*\n"
            f"`prize_type:value:probability`\n\n"
            f"*أمثلة:*\n"
            f"`points:50:40` (50 نقطة - 40%)\n"
            f"`points:100:20` (100 نقطة - 20%)\n"
            f"`subscription:plus:30:30` (بلس 30ي - 30%)\n"
            f"`none::10` (لا شيء - 10%)\n\n"
            f"⚠️ المجموع يجب أن يكون 100",
            parse_mode="Markdown", reply_markup=kb_cancel())
    elif drop_type == "conditional":
        context.user_data["state"] = "conditional_setup"
        await update.message.reply_text(
            f"🔒 *إعداد الشروط*\n\n"
            f"📦 {SUBSCRIPTION_TYPES[plan]['name']} — {days}ي\n\n"
            f"أرسل الشروط:\n\n"
            f"*الصيغة:*\n"
            f"`min_invites:5,min_points:100,vip_tier:silver`\n\n"
            f"*المتاح:*\n"
            f"• `min_invites` — عدد الدعوات\n"
            f"• `min_purchases` — عدد الشراءات\n"
            f"• `min_points` — النقاط\n"
            f"• `vip_tier` — bronze/silver/gold/platinum\n\n"
            f"❌ للإلغاء",
            parse_mode="Markdown", reply_markup=kb_cancel())
    elif drop_type == "chain":
        await create_chain_drop(update, context, plan, days)
    elif drop_type == "vote":
        context.user_data["state"] = "vote_setup"
        await update.message.reply_text(
            f"🗳️ *إعداد التصويت*\n\n"
            f"📦 {SUBSCRIPTION_TYPES[plan]['name']} — {days}ي\n\n"
            f"أرسل خيارات التصويت (كل سطر خيار):\n\n"
            f"*مثال:*\n"
            f"`plus:30:بلس 30 يوم`\n"
            f"`pro:30:برو 30 يوم`\n"
            f"`premium:30:بريميوم 30 يوم`\n\n"
            f"*الصيغة:* `plan:days:name`\n\n"
            f"❌ للإلغاء",
            parse_mode="Markdown", reply_markup=kb_cancel())
    elif drop_type == "auction":
        context.user_data["state"] = "auction_setup"
        await update.message.reply_text(
            f"🔨 *إعداد المزاد*\n\n"
            f"📦 {SUBSCRIPTION_TYPES[plan]['name']} — {days}ي\n\n"
            f"أرسل بيانات المزاد:\n\n"
            f"*الصيغة:*\n"
            f"`start_price:min_increment:duration_minutes`\n\n"
            f"*مثال:*\n"
            f"`10:5:60` (سعر بداية 10، زيادة 5، مدة 60 دقيقة)\n\n"
            f"❌ للإلغاء",
            parse_mode="Markdown", reply_markup=kb_cancel())

async def create_normal_drop(update, context, plan, days):
    """ينشئ دروب عادي"""
    user_id = update.effective_user.id
    token = await db.create_drop(plan, days, user_id, drop_type="normal")
    drop = await db.get_drop(token)
    
    # نشر في كل القنوات
    channels = await db.list_channels()
    published = 0
    failed = 0
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(drop),
                reply_markup=build_drop_card_kb(drop, context.bot.username),
                parse_mode="Markdown")
            await db.save_drop_message(drop["id"], ch["chat_id"], sent.message_id)
            published += 1
        except Exception as e:
            logger.warning(f"فشل النشر في {ch['title']}: {e}")
            failed += 1
    
    info = SUBSCRIPTION_TYPES[plan]
    link = f"https://t.me/{context.bot.username}?start=drop_{token}"
    await update.message.reply_text(
        f"✅ *تم إنشاء الدروب!*\n\n"
        f"{info['emoji']} {info['name']} — {days}ي\n"
        f"🆔 #{token}\n\n"
        f"📢 نُشر في: `{published}` قناة" + (f"\n❌ فشل: `{failed}`" if failed else "") + "\n\n"
        f"🔗 `{link}`",
        parse_mode="Markdown", reply_markup=kb_drops(),
        disable_web_page_preview=True)
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_type", None)

async def create_chain_drop(update, context, plan, days):
    """ينشئ دروب تسلسلي (يحتاج إعداد الدروب التالي)"""
    context.user_data["state"] = "chain_setup_next"
    await update.message.reply_text(
        f"🔗 *إعداد السلسلة*\n\n"
        f"📦 {SUBSCRIPTION_TYPES[plan]['name']} — {days}ي\n\n"
        f"كم عدد الدروبات في السلسلة؟\n\n"
        f"أرسل رقماً (1-10):\n\n"
        f"💡 كل دروب يفتح التالي عند استخدامه",
        parse_mode="Markdown", reply_markup=kb_cancel())

async def receive_egg_setup(update, context, text):
    """إعداد محتويات البيضة"""
    plan = context.user_data.get("drop_plan")
    days = context.user_data.get("drop_days")
    if not plan or not days:
        await show_admin(update, context)
        return
    
    # تحليل السطور
    lines = text.strip().split("\n")
    contents = []
    total_prob = 0
    for line in lines:
        parts = line.strip().split(":")
        if len(parts) < 3:
            continue
        try:
            if parts[0] == "subscription":
                # subscription:plan:days:prob
                prize_type = "subscription"
                prize_value = f"{parts[1]}:{parts[2]}"
                prob = float(parts[3])
            elif parts[0] == "none":
                prize_type = "none"
                prize_value = ""
                prob = float(parts[1])
            else:
                # points:value:prob
                prize_type = parts[0]
                prize_value = parts[1]
                prob = float(parts[2])
            contents.append((prize_type, prize_value, prob))
            total_prob += prob
        except Exception as e:
            logger.error(f"خطأ في تحليل {line}: {e}")
    
    if not contents or abs(total_prob - 100) > 1:
        await update.message.reply_text(
            f"❌ *خطأ*\n\nالمجموع = {total_prob}% (يجب 100%)\n\nأرسل مجدداً:",
            parse_mode="Markdown", reply_markup=kb_cancel())
        return
    
    # إنشاء الدروب
    user_id = update.effective_user.id
    token = await db.create_drop(plan, days, user_id, drop_type="egg")
    drop = await db.get_drop(token)
    
    for prize_type, prize_value, prob in contents:
        await db.add_egg_content(drop["id"], prize_type, prize_value, prob)
    
    # نشر
    channels = await db.list_channels()
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(drop),
                reply_markup=build_drop_card_kb(drop, context.bot.username),
                parse_mode="Markdown")
            await db.save_drop_message(drop["id"], ch["chat_id"], sent.message_id)
        except Exception:
            pass
    
    info = SUBSCRIPTION_TYPES[plan]
    await update.message.reply_text(
        f"✅ *تم إنشاء البيضة!*\n\n"
        f"🥚 {info['emoji']} {info['name']} — {days}ي\n"
        f"🎁 محتويات: {len(contents)}\n\n"
        f"🔗 `https://t.me/{context.bot.username}?start=drop_{token}`",
        parse_mode="Markdown", reply_markup=kb_drops(),
        disable_web_page_preview=True)
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_days", None)
    context.user_data.pop("drop_type", None)

async def receive_conditional_setup(update, context, text):
    """إعداد شروط الدروب"""
    plan = context.user_data.get("drop_plan")
    days = context.user_data.get("drop_days")
    if not plan or not days:
        await show_admin(update, context)
        return
    
    # تحليل الشروط
    conditions = {}
    for part in text.split(","):
        if ":" in part:
            key, val = part.strip().split(":", 1)
            key = key.strip()
            val = val.strip()
            if key in ("min_invites", "min_purchases", "min_points"):
                try:
                    conditions[key] = int(val)
                except ValueError:
                    pass
            elif key == "vip_tier":
                if val in VIP_TIERS:
                    conditions[key] = val
    
    if not conditions:
        await update.message.reply_text("❌ لا شروط صالحة. أرسل مجدداً:",
                                          reply_markup=kb_cancel())
        return
    
    # إنشاء
    user_id = update.effective_user.id
    token = await db.create_drop(plan, days, user_id, drop_type="conditional",
                                   conditions=conditions)
    drop = await db.get_drop(token)
    
    # نشر
    channels = await db.list_channels()
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(drop),
                reply_markup=build_drop_card_kb(drop, context.bot.username),
                parse_mode="Markdown")
            await db.save_drop_message(drop["id"], ch["chat_id"], sent.message_id)
        except Exception:
            pass
    
    info = SUBSCRIPTION_TYPES[plan]
    await update.message.reply_text(
        f"✅ *تم إنشاء الدروب!*\n\n"
        f"🔒 {info['emoji']} {info['name']} — {days}ي\n"
        f"📋 شروط: {len(conditions)}\n\n"
        f"🔗 `https://t.me/{context.bot.username}?start=drop_{token}`",
        parse_mode="Markdown", reply_markup=kb_drops(),
        disable_web_page_preview=True)
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_days", None)
    context.user_data.pop("drop_type", None)

async def receive_chain_setup(update, context, text):
    """إعداد السلسلة"""
    try:
        count = int(text)
        if count < 1 or count > 10:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ رقم بين 1 و 10:", reply_markup=kb_cancel())
        return
    
    plan = context.user_data.get("drop_plan")
    days = context.user_data.get("drop_days")
    if not plan or not days:
        await show_admin(update, context)
        return
    
    user_id = update.effective_user.id
    
    # إنشاء دروبات السلسلة
    tokens = []
    prev_id = None
    for i in range(count):
        token = await db.create_drop(plan, days, user_id, drop_type="chain")
        drop = await db.get_drop(token)
        tokens.append(token)
        
        if prev_id:
            # ربط السابق بالحالي
            async with aiosqlite.connect(DB_PATH) as db_conn:
                await db_conn.execute("UPDATE drops SET next_drop_id=? WHERE id=?", (drop["id"], prev_id))
                await db_conn.execute("UPDATE drops SET parent_drop_id=? WHERE id=?", (prev_id, drop["id"]))
                await db_conn.commit()
        
        prev_id = drop["id"]
    
    # نشر الأول فقط
    first_token = tokens[0]
    first_drop = await db.get_drop(first_token)
    channels = await db.list_channels()
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(first_drop),
                reply_markup=build_drop_card_kb(first_drop, context.bot.username),
                parse_mode="Markdown")
            await db.save_drop_message(first_drop["id"], ch["chat_id"], sent.message_id)
        except Exception:
            pass
    
    info = SUBSCRIPTION_TYPES[plan]
    await update.message.reply_text(
        f"✅ *تم إنشاء السلسلة!*\n\n"
        f"🔗 {info['emoji']} {info['name']} — {days}ي\n"
        f"📊 {count} دروبات متسلسلة\n\n"
        f"🔗 `https://t.me/{context.bot.username}?start=drop_{first_token}`",
        parse_mode="Markdown", reply_markup=kb_drops(),
        disable_web_page_preview=True)
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_days", None)
    context.user_data.pop("drop_type", None)

async def receive_vote_setup(update, context, text):
    """إعداد خيارات التصويت"""
    plan = context.user_data.get("drop_plan")
    days = context.user_data.get("drop_days")
    if not plan or not days:
        await show_admin(update, context)
        return
    
    options = []
    for line in text.strip().split("\n"):
        parts = line.strip().split(":")
        if len(parts) == 3:
            options.append((parts[0], int(parts[1]), parts[2]))
    
    if not options:
        await update.message.reply_text("❌ لا خيارات صالحة.", reply_markup=kb_cancel())
        return
    
    user_id = update.effective_user.id
    token = await db.create_drop(plan, days, user_id, drop_type="vote")
    drop = await db.get_drop(token)
    
    for opt_plan, opt_days, opt_name in options:
        await db.create_vote_option(drop["id"], f"{opt_plan}:{opt_days}", opt_name)
    
    # نشر
    channels = await db.list_channels()
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(drop),
                reply_markup=build_drop_card_kb(drop, context.bot.username),
                parse_mode="Markdown")
            await db.save_drop_message(drop["id"], ch["chat_id"], sent.message_id)
        except Exception:
            pass
    
    await update.message.reply_text(
        f"✅ *تم إنشاء التصويت!*\n\n"
        f"🗳️ {len(options)} خيارات\n\n"
        f"🔗 `https://t.me/{context.bot.username}?start=drop_{token}`",
        parse_mode="Markdown", reply_markup=kb_drops(),
        disable_web_page_preview=True)
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_days", None)
    context.user_data.pop("drop_type", None)

async def receive_auction_setup(update, context, text):
    """إعداد المزاد"""
    try:
        parts = text.strip().split(":")
        start_price = int(parts[0])
        min_increment = int(parts[1])
        duration_min = int(parts[2])
    except Exception:
        await update.message.reply_text("❌ صيغة خاطئة. جرب: `10:5:60`",
                                          parse_mode="Markdown", reply_markup=kb_cancel())
        return
    
    plan = context.user_data.get("drop_plan")
    days = context.user_data.get("drop_days")
    if not plan or not days:
        await show_admin(update, context)
        return
    
    user_id = update.effective_user.id
    token = await db.create_drop(plan, days, user_id, drop_type="auction")
    drop = await db.get_drop(token)
    
    ends_at = (datetime.now() + timedelta(minutes=duration_min)).isoformat()
    await db.create_auction(drop["id"], start_price, min_increment, ends_at)
    
    # نشر
    drop["_auction"] = await db.get_auction_by_drop(drop["id"])
    channels = await db.list_channels()
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(drop),
                reply_markup=build_drop_card_kb(drop, context.bot.username),
                parse_mode="Markdown")
            await db.save_drop_message(drop["id"], ch["chat_id"], sent.message_id)
        except Exception:
            pass
    
    await update.message.reply_text(
        f"✅ *تم إنشاء المزاد!*\n\n"
        f"🔨 {SUBSCRIPTION_TYPES[plan]['name']} — {days}ي\n"
        f"💰 بداية: `{start_price}`\n"
        f"⏱️ مدة: `{duration_min}` دقيقة\n\n"
        f"🔗 `https://t.me/{context.bot.username}?start=drop_{token}`",
        parse_mode="Markdown", reply_markup=kb_drops(),
        disable_web_page_preview=True)
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_days", None)
    context.user_data.pop("drop_type", None)

async def pdrop_create_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "pdrop_points"
    await update.message.reply_text("💎 أرسل عدد النقاط:", reply_markup=kb_cancel())

async def pdrop_receive(update, context, text):
    try:
        points = int(text)
        if points < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ رقم صحيح ≥ 1:", reply_markup=kb_cancel())
        return
    token = await db.create_points_drop(points, update.effective_user.id)
    link = f"https://t.me/{context.bot.username}?start=pdrop_{token}"
    await update.message.reply_text(
        f"✅ *أُنشئ!*\n\n💰 {points} نقطة\n\n🔗 `{link}`\n\n📢 أول شخص يفوز!",
        parse_mode="Markdown", reply_markup=kb_pdrops(),
        disable_web_page_preview=True)
    context.user_data["state"] = "pdrops"

async def scheduled_create_begin(update, context):
    """إضافة دروب مجدول"""
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "sched_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text("⏰ *دروب مجدول*\n\nاختر نوع الباقة:",
                                      parse_mode="Markdown",
                                      reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))

async def sched_choose_plan(update, context, text):
    sub_type = text.replace("drop:", "")
    if sub_type not in SUBSCRIPTION_TYPES:
        return
    context.user_data["sched_plan"] = sub_type
    context.user_data["state"] = "sched_days"
    info = SUBSCRIPTION_TYPES[sub_type]
    days = list(info["prices"].keys())
    rows = []
    if len(days) >= 2:
        rows.append([KeyboardButton(f"{d} يوم") for d in days[:2]])
    if len(days) > 2:
        rows.append([KeyboardButton(f"{d} يوم") for d in days[2:]])
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text(f"اختر المدة:",
                                      reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))

async def sched_choose_days(update, context, text):
    try:
        days = int(text.replace("يوم", "").replace("أيام", "").strip())
    except ValueError:
        return
    context.user_data["sched_days"] = days
    context.user_data["state"] = "sched_interval"
    await update.message.reply_text(
        "⏱️ *كل كم دقيقة ينشر؟*\n\n"
        "أرسل عدد الدقائق (مثلاً 60 = كل ساعة):\n\n❌ للإلغاء",
        parse_mode="Markdown", reply_markup=kb_cancel())

async def sched_receive_interval(update, context, text):
    try:
        interval = int(text)
        if interval < 5:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ رقم ≥ 5 دقائق:", reply_markup=kb_cancel())
        return
    
    plan = context.user_data.get("sched_plan")
    days = context.user_data.get("sched_days")
    if not plan or not days:
        await show_admin(update, context)
        return
    
    sched_id = await db.create_scheduled_drop(plan, days, interval, update.effective_user.id)
    info = SUBSCRIPTION_TYPES[plan]
    await update.message.reply_text(
        f"✅ *تم إنشاء الدروب المجدول!*\n\n"
        f"⏰ {info['emoji']} {info['name']} — {days}ي\n"
        f"📅 كل `{interval}` دقيقة\n\n"
        f"🆔 #{sched_id}",
        parse_mode="Markdown", reply_markup=kb_admin())
    context.user_data["state"] = "admin"
    context.user_data.pop("sched_plan", None)
    context.user_data.pop("sched_days", None)

# ═══════════════════════════════════════════════════════════════════
# 🎯 الراوتر الرئيسي
# ═══════════════════════════════════════════════════════════════════

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    user_id = update.effective_user.id
    admin = is_admin(user_id)
    state = context.user_data.get("state", "main")

    try:
        # ═══ حالات المحادثات (لها أولوية) ═══
        if state == "check_code":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context); return
            await check_code_receive(update, context, text); return

        if state == "transfer_id":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context); return
            await transfer_get_id(update, context, text); return

        if state == "transfer_amount":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context); return
            await transfer_get_amount(update, context, text); return

        if state == "transfer_confirm":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context); return
            await transfer_do_confirm(update, context, text); return

        if state == "key_add_value":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await key_add_value(update, context, text); return

        if state == "key_add_label":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await key_add_label(update, context, text); return

        if state == "market_sell_price":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context); return
            await market_sell_receive_price(update, context, text); return

        if state == "auction_bid_amount":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context); return
            await auction_bid_receive(update, context, text); return

        if state == "broadcast_message":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await broadcast_send(update, context, text); return

        if state == "pdrop_points":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await pdrop_receive(update, context, text); return

        if state == "drop_choose_plan":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            if text.startswith("drop:"):
                await drop_choose_type(update, context, text); return
            return

        if state == "drop_choose_days":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await drop_choose_days(update, context, text); return

        if state == "egg_setup":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await receive_egg_setup(update, context, text); return

        if state == "conditional_setup":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await receive_conditional_setup(update, context, text); return

        if state == "chain_setup_next":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await receive_chain_setup(update, context, text); return

        if state == "vote_setup":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await receive_vote_setup(update, context, text); return

        if state == "auction_setup":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await receive_auction_setup(update, context, text); return

        if state == "sched_plan":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            if text.startswith("drop:"):
                await sched_choose_plan(update, context, text); return
            return

        if state == "sched_days":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await sched_choose_days(update, context, text); return

        if state == "sched_interval":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await sched_receive_interval(update, context, text); return

        if state == "calc_type":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context); return
            calc_type = None
            if text == BTN_PLUS: calc_type = "plus"
            elif text == BTN_PRO: calc_type = "pro"
            elif text == BTN_PREMIUM: calc_type = "premium"
            if calc_type:
                context.user_data["calc"] = {"type": calc_type}
                context.user_data["state"] = "calc_days"
                info = SUBSCRIPTION_TYPES[calc_type]
                days = list(info["prices"].keys())
                rows = []
                if len(days) >= 2:
                    rows.append([KeyboardButton(f"{d} يوم") for d in days[:2]])
                if len(days) > 2:
                    rows.append([KeyboardButton(f"{d} يوم") for d in days[2:]])
                rows.append([KeyboardButton(BTN_CANCEL)])
                await update.message.reply_text(
                    f"{info['emoji']} *{info['name']}*\n\nاختر المدة:",
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))
                return
            await show_calculator(update, context); return

        if state == "calc_days":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context); return
            try:
                days = int(text.replace("يوم", "").replace("أيام", "").strip())
            except ValueError:
                return
            ctx = context.user_data.get("calc", {})
            sub_type = ctx.get("type")
            if not sub_type:
                await show_calculator(update, context); return
            info = SUBSCRIPTION_TYPES[sub_type]
            if days not in info["prices"]:
                return
            unit_price = info["prices"][days]
            user = await db.get_user(user_id)
            tier = get_vip_tier(user["points"])
            vip_discount = VIP_TIERS[tier]["discount"]
            one_total = unit_price
            if vip_discount > 0:
                one_total -= one_total * vip_discount // 100
            await update.message.reply_text(
                f"🧮 *نتيجة الحساب*\n\n"
                f"{info['emoji']} {info['name']} — {days} يوم\n\n"
                f"💰 سعر الوحدة: `{unit_price}` 💎\n"
                f"🏅 خصم VIP: `{vip_discount}%`\n"
                f"✅ سعر كود واحد: `{one_total}` 💎\n\n"
                f"💎 رصيدك: `{user['points']}`\n"
                f"{'✅ يكفي' if user['points'] >= one_total else '❌ لا يكفي'}",
                parse_mode="Markdown", reply_markup=kb_main(admin))
            context.user_data["state"] = "main"; return

        # ═══ الأزرار الرئيسية ═══
        if text == BTN_HOME:    await show_home(update, context); return
        if text == BTN_SHOP:    await show_shop(update, context); return
        if text == BTN_SUBS:    await show_subs(update, context); return
        if text == BTN_WALLET:  await show_wallet(update, context); return
        if text == BTN_EARN:    await show_earn(update, context); return
        if text == BTN_MARKET:  await show_market(update, context); return
        if text == BTN_TOP:     await show_top(update, context); return
        if text == BTN_GUIDE:   await show_guide(update, context); return
        if text == BTN_CHECK:   await check_code_begin(update, context); return
        if text == BTN_STATUS:  await show_status(update, context); return
        if text == BTN_CALC:    await show_calculator(update, context); return
        if text == BTN_ARCHIVE: await show_archive(update, context); return
        if text == BTN_SETTINGS: await show_settings(update, context); return
        if text == BTN_ABOUT:   await show_about(update, context); return
        if text == BTN_ADMIN:   await show_admin(update, context); return

        # ═══ الرجوع ═══
        if text == BTN_BACK:
            if state in ("shop", "buy_days", "buy_qty", "buy_confirm"):
                await show_shop(update, context)
            elif state == "wallet":
                await show_wallet(update, context)
            elif state == "earn":
                await show_earn(update, context)
            elif state == "settings":
                await show_settings(update, context)
            elif state == "market":
                await show_market(update, context)
            elif state in ("admin", "keys", "channels", "drops", "pdrops", "scheduled"):
                await show_admin(update, context)
            else:
                await show_home(update, context)
            return

        # ═══ شراء ═══
        if state in ("shop", "buy_days"):
            if text == BTN_PLUS:    await buy_choose_type(update, context, "plus"); return
            if text == BTN_PRO:     await buy_choose_type(update, context, "pro"); return
            if text == BTN_PREMIUM: await buy_choose_type(update, context, "premium"); return

        if state == "buy_days":
            try:
                days = int(text.replace("يوم", "").replace("أيام", "").strip())
                await buy_choose_days(update, context, days); return
            except ValueError:
                pass

        if state == "buy_qty":
            if text == BTN_QTY_1:    await buy_choose_qty(update, context, 1); return
            if text == BTN_QTY_2:    await buy_choose_qty(update, context, 2); return
            if text == BTN_QTY_3:    await buy_choose_qty(update, context, 3); return
            if text == BTN_QTY_5:    await buy_choose_qty(update, context, 5); return
            if text == BTN_QTY_10:   await buy_choose_qty(update, context, 10); return
            if text == BTN_QTY_CUSTOM:
                context.user_data["state"] = "buy_custom_qty"
                await update.message.reply_text("✏️ أرسل عدد الأكواد (1-100):",
                                                  reply_markup=kb_cancel()); return

        if state == "buy_custom_qty":
            if text == BTN_CANCEL:
                ctx = context.user_data.get("buy", {})
                if ctx.get("type"):
                    context.user_data["state"] = "buy_qty"
                    await update.message.reply_text("🔢 اختر عدداً:", reply_markup=kb_quantity())
                else:
                    await show_shop(update, context)
                return
            try:
                qty = int(text)
                if qty < 1 or qty > 100:
                    raise ValueError
            except ValueError:
                await update.message.reply_text("❌ رقم بين 1 و 100:", reply_markup=kb_cancel()); return
            await buy_choose_qty(update, context, qty); return

        if state == "buy_confirm":
            if text == BTN_CONFIRM:
                await buy_confirm(update, context); return
            if text == BTN_EDIT_QTY:
                if context.user_data.get("buy", {}).get("type"):
                    context.user_data["state"] = "buy_qty"
                    await update.message.reply_text("🔢 اختر عدداً جديداً:", reply_markup=kb_quantity())
                return
            if text == BTN_CANCEL:
                await show_home(update, context); return

        # ═══ محفظة / اكسب / إعدادات ═══
        if state in ("wallet", "earn"):
            if text == BTN_DAILY:    await do_daily(update, context); return
            if text == BTN_INVITE:   await show_invite(update, context); return
            if text == BTN_MY_ID:    await show_my_id(update, context); return
            if text == BTN_TRANSFER: await transfer_begin(update, context); return

        if state == "settings":
            if text == BTN_LANG:   await show_language(update, context); return
            if text == BTN_THEME:  await show_theme(update, context); return
            if text == BTN_NOTIF:  await show_notifications(update, context); return

        # ═══ لوحة المشرف ═══
        if state == "admin" and admin:
            if text == BTN_KEYS:         await show_keys(update, context); return
            if text == BTN_CHANNELS:     await show_channels(update, context); return
            if text == BTN_DROPS:        await show_drops(update, context); return
            if text == BTN_PDROPS:       await show_pdrops(update, context); return
            if text == BTN_STATS:        await show_stats(update, context); return
            if text == BTN_LOGS:         await show_logs(update, context); return
            if text == BTN_SCHEDULED:    await show_scheduled(update, context); return
            if text == BTN_ALL_DROPS:    await show_all_drops(update, context); return
            if text == BTN_BROADCAST:    await show_broadcast_begin(update, context); return

        if state == "keys" and admin:
            if text == BTN_ADD_KEY:
                await key_add_begin(update, context); return

        if state == "drops" and admin:
            if text == BTN_CREATE_DROP:      await drop_create_begin(update, context); return
            if text == BTN_DROP_EGG:         await egg_drop_create_begin(update, context); return
            if text == BTN_DROP_COND:        await conditional_drop_create_begin(update, context); return
            if text == BTN_DROP_CHAIN:       await chain_drop_create_begin(update, context); return
            if text == BTN_DROP_VOTE:        await vote_drop_create_begin(update, context); return
            if text == BTN_DROP_AUCTION:     await auction_drop_create_begin(update, context); return
            if text == BTN_ALL_DROPS:        await show_all_drops(update, context); return
            if text == BTN_SCHEDULED:        await show_scheduled(update, context); return

        if state == "pdrops" and admin:
            if text == BTN_CREATE_PDROP:
                await pdrop_create_begin(update, context); return

        if state == "scheduled" and admin:
            if text == BTN_SCHEDULED_ADD:
                await scheduled_create_begin(update, context); return

        # ═══ افتراضي ═══
        await update.message.reply_text("🤔 استخدم الأزرار بالأسفل.", reply_markup=kb_main(admin))

    except Exception as e:
        logger.exception(f"[TEXT] خطأ: {e}")
        try:
            await update.message.reply_text(f"❌ خطأ: `{str(e)[:150]}`",
                                              parse_mode="Markdown", reply_markup=kb_main(admin))
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════════
# 🛡️ أوامر
# ═══════════════════════════════════════════════════════════════════

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_admin(update, context)

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("`/ban <id>`", parse_mode="Markdown"); return
    try:
        uid = int(context.args[0])
    except:
        return
    await db.set_ban(uid, 1)
    await update.message.reply_text(f"✅ حُظر {uid}")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return
    try:
        uid = int(context.args[0])
    except:
        return
    await db.set_ban(uid, 0)
    await update.message.reply_text(f"✅ رُفع الحظر")

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = "main"
    for k in ("buy", "transfer_to", "transfer_amount", "new_key_value",
              "drop_plan", "drop_type", "drop_days", "calc", "sched_plan",
              "sched_days", "market_sell_sub_id", "auction_bid_drop_id"):
        context.user_data.pop(k, None)
    await show_home(update, context)

# ═══════════════════════════════════════════════════════════════════
# 🎬 التشغيل
# ═══════════════════════════════════════════════════════════════════

async def post_init(app):
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"📁 مجلد DB: {db_dir}")
        except Exception as e:
            logger.error(f"فشل إنشاء: {e}")
    
    logger.info(f"💾 DB_PATH = {DB_PATH}")
    logger.info(f"🔑 SUPER_ADMIN_ID = {SUPER_ADMIN_ID}")
    logger.info(f"📢 القناة = @{CHANNEL_USERNAME}")
    
    await db.init()
    
    # ترحيل المفتاح القديم
    keys = await db.list_api_keys()
    for k in keys:
        if k["key_value"] == "Obeida0595440227@":
            await db.delete_api_key(k["id"])
            logger.info("🗑️ حُذف المفتاح القديم")
            keys = await db.list_api_keys()
            break
    
    existing_new = next((k for k in keys if k["key_value"] == INITIAL_API_KEY), None)
    if not existing_new:
        await db.add_api_key(INITIAL_API_KEY, INITIAL_API_KEY_LABEL, SUPER_ADMIN_ID)
        keys = await db.list_api_keys()
        existing_new = next((k for k in keys if k["key_value"] == INITIAL_API_KEY), None)
        logger.info("✅ أُضيف المفتاح الجديد")
    
    if existing_new and not existing_new["is_active"]:
        await db.set_active_key(existing_new["id"])
        logger.info("✅ فُعّل المفتاح")
    
    active = await db.get_active_key()
    if active:
        ok, msg = await api.test_key(active["key_value"])
        logger.info(f"🔑 {msg}")
    
    # JobQueue
    if app.job_queue is not None:
        app.job_queue.run_repeating(periodic_refresh,
                                      interval=DROPS_REFRESH_INTERVAL, first=60)
        logger.info(f"⏱️ تحديث الدروبات كل {DROPS_REFRESH_INTERVAL // 60} دقيقة")
        
        app.job_queue.run_repeating(auto_close_auctions,
                                      interval=60, first=30)
        logger.info("🔨 فحص المزادات كل دقيقة")
        
        app.job_queue.run_repeating(check_scheduled_drops,
                                      interval=60, first=45)
        logger.info("⏰ فحص الدروبات المجدولة كل دقيقة")
    else:
        logger.warning("⚠️ JobQueue غير متوفر — ثبّت python-telegram-bot[job-queue]")
    
    logger.info("✅ Worm GPT جاهز!")

def main():
    if "ضع_التوكن" in BOT_TOKEN:
        print("❌ ضع BOT_TOKEN في Environment")
        return
    
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    
    start_http_server()
    logger.info(f"🚀 بدء Worm GPT... (DB: {DB_PATH})")
    
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    
    # Chat member
    app.add_handler(ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern="^verify_join$"))
    app.add_handler(CallbackQueryHandler(drop_status_callback, pattern="^drop_status_"))
    app.add_handler(CallbackQueryHandler(drop_refresh_callback, pattern="^drop_refresh_"))
    app.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(theme_callback, pattern="^theme_"))
    app.add_handler(CallbackQueryHandler(notif_callback, pattern="^notif_"))
    app.add_handler(CallbackQueryHandler(settings_back_callback, pattern="^settings_back$"))
    app.add_handler(CallbackQueryHandler(cast_vote_callback, pattern="^cast_vote_"))
    app.add_handler(CallbackQueryHandler(bid_callback, pattern="^bid_"))
    
    # Market callbacks
    app.add_handler(CallbackQueryHandler(market_browse_callback, pattern="^market_browse$"))
    app.add_handler(CallbackQueryHandler(market_view_callback, pattern="^market_view_"))
    app.add_handler(CallbackQueryHandler(market_buy_callback, pattern="^market_buy_"))
    app.add_handler(CallbackQueryHandler(market_sell_callback, pattern="^market_sell$"))
    app.add_handler(CallbackQueryHandler(market_sell_pick_callback, pattern="^market_sell_pick_"))
    app.add_handler(CallbackQueryHandler(market_mine_callback, pattern="^market_mine$"))
    app.add_handler(CallbackQueryHandler(market_cancel_callback, pattern="^market_cancel_"))
    app.add_handler(CallbackQueryHandler(market_back_callback, pattern="^market_back$"))
    
    # Router
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    
    logger.info("🚀 بدء التشغيل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
