# ═══════════════════════════════════════════════════════════════════
# 🤖 Worm GPT — Complete Edition v3
# 📦 pip install -r requirements.txt
# ⚠️ الجزء 1/8 — البنية التحتية
# ═══════════════════════════════════════════════════════════════════

import os
import logging
import asyncio
import json
import secrets
import threading
import random
import csv
import io
import shutil
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
# ⚙️ الإعدادات الأساسية
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
BACKUP_INTERVAL = int(os.environ.get("BACKUP_INTERVAL", "86400"))
MONITORING_INTERVAL = int(os.environ.get("MONITORING_INTERVAL", "300"))

# مسارات
if os.path.exists("/data"):
    DB_PATH = "/data/bot_data.db"
    BACKUP_DIR = "/data/backups"
else:
    DB_PATH = os.environ.get("DB_PATH", "bot_data.db")
    BACKUP_DIR = "backups"

# ═══════════════════════════════════════════════════════════════════
# 💎 الخطط
# ═══════════════════════════════════════════════════════════════════

SUBSCRIPTION_TYPES = {
    "plus": {
        "name": "⭐ بلس", "emoji": "⭐", "api_plan": "plus",
        "description": "اشتراك أساسي — مناسب للاستخدام الشخصي",
        "prices": {7: 5, 30: 15, 90: 40, 365: 120},
    },
    "pro": {
        "name": "💎 برو", "emoji": "💎", "api_plan": "pro",
        "description": "اشتراك متقدم — ميزات إضافية",
        "prices": {7: 8, 30: 25, 90: 65, 365: 200},
    },
    "premium": {
        "name": "👑 بريميوم", "emoji": "👑", "api_plan": "premium",
        "description": "اشتراك كامل — كل الميزات",
        "prices": {7: 15, 30: 45, 90: 120, 365: 380},
    },
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

# ═══════════════════════════════════════════════════════════════════
# 🎮 إعدادات الألعاب
# ═══════════════════════════════════════════════════════════════════

GAME_COSTS = {
    "box": 20,          # اختر صندوقك
    "odd_even": 10,     # زوجي/فردي
    "cards": 15,        # البطاقات
    "black_market": 10, # السوق السوداء
    "wheel": 25,        # عجلة الحظ
    "time_chase": 20,   # مطاردة الوقت
    "treasure": 30,     # الكنز المخفي
    "dice_duel": 15,    # تحدي الأصدقاء
}

GAME_DAILY_LIMIT = 20
GAME_COOLDOWN_SECONDS = 15

# ═══════════════════════════════════════════════════════════════════
# 📝 Logging
# ═══════════════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ═══════════════════════════════════════════════════════════════════
# 🌐 HTTP Server (للـ Web Service على Render)
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
    thread = threading.Thread(target=run_http_server, daemon=True)
    thread.start()

# ═══════════════════════════════════════════════════════════════════
# 💾 قاعدة البيانات — كل الجداول
# ═══════════════════════════════════════════════════════════════════

class Database:
    def __init__(self, path=DB_PATH):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
                -- ═══ المستخدمون ═══
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    points INTEGER DEFAULT 0,
                    total_points_earned INTEGER DEFAULT 0,
                    total_points_spent INTEGER DEFAULT 0,
                    invited_by INTEGER,
                    invite_code TEXT UNIQUE,
                    last_daily_bonus TEXT,
                    daily_streak INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'ar',
                    theme TEXT DEFAULT 'auto',
                    notifications TEXT DEFAULT '{}',
                    vip_tier TEXT DEFAULT 'bronze',
                    partner_id INTEGER,
                    last_seen TEXT,
                    joined_at TEXT
                );
                
                -- ═══ مفاتيح API ═══
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_value TEXT NOT NULL,
                    label TEXT,
                    is_active INTEGER DEFAULT 0,
                    created_at TEXT,
                    created_by INTEGER,
                    last_used TEXT,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0
                );
                
                -- ═══ الاشتراكات ═══
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    code TEXT,
                    plan TEXT,
                    actual_plan TEXT,
                    days INTEGER,
                    max_uses INTEGER,
                    uses INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TEXT,
                    expires_at TEXT,
                    points_spent INTEGER DEFAULT 0,
                    api_response TEXT,
                    source TEXT DEFAULT 'purchase'
                );
                
                -- ═══ القنوات ═══
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER UNIQUE NOT NULL,
                    title TEXT,
                    username TEXT,
                    chat_type TEXT,
                    added_by INTEGER,
                    added_at TEXT,
                    is_active INTEGER DEFAULT 1,
                    is_primary INTEGER DEFAULT 0,
                    can_post INTEGER DEFAULT 0,
                    can_edit INTEGER DEFAULT 0,
                    last_used TEXT,
                    total_drops INTEGER DEFAULT 0,
                    total_claims INTEGER DEFAULT 0
                );
                
                -- ═══ الدروبات ═══
                CREATE TABLE IF NOT EXISTS drops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT UNIQUE NOT NULL,
                    plan TEXT NOT NULL,
                    days INTEGER NOT NULL,
                    drop_type TEXT DEFAULT 'normal',
                    conditions TEXT DEFAULT '{}',
                    next_drop_id INTEGER,
                    parent_drop_id INTEGER,
                    max_winners INTEGER DEFAULT 1,
                    current_winners INTEGER DEFAULT 0,
                    created_by INTEGER,
                    created_at TEXT,
                    expires_at TEXT,
                    claimed_by INTEGER,
                    claimed_at TEXT,
                    claim_code TEXT,
                    chat_id INTEGER,
                    message_id INTEGER,
                    last_refreshed TEXT,
                    retry_count INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    is_deleted INTEGER DEFAULT 0,
                    total_views INTEGER DEFAULT 0,
                    total_clicks INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                );
                
                CREATE TABLE IF NOT EXISTS drop_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drop_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    created_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS drop_winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drop_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    rank INTEGER,
                    code TEXT,
                    won_at TEXT
                );
                
                -- ═══ البيضاوي ═══
                CREATE TABLE IF NOT EXISTS egg_contents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drop_id INTEGER NOT NULL,
                    prize_type TEXT NOT NULL,
                    prize_value TEXT,
                    probability REAL DEFAULT 0,
                    is_won INTEGER DEFAULT 0,
                    won_by INTEGER,
                    won_at TEXT
                );
                
                -- ═══ التصويت ═══
                CREATE TABLE IF NOT EXISTS vote_options (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drop_id INTEGER NOT NULL,
                    option_key TEXT NOT NULL,
                    option_name TEXT,
                    votes_count INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drop_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    choice TEXT NOT NULL,
                    voted_at TEXT,
                    UNIQUE(drop_id, user_id)
                );
                
                -- ═══ المزاد ═══
                CREATE TABLE IF NOT EXISTS auctions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drop_id INTEGER NOT NULL UNIQUE,
                    start_price INTEGER DEFAULT 0,
                    min_increment INTEGER DEFAULT 5,
                    current_bid INTEGER DEFAULT 0,
                    current_bidder INTEGER,
                    ends_at TEXT,
                    is_closed INTEGER DEFAULT 0,
                    created_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS bids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    auction_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    bid_at TEXT
                );
                
                -- ═══ السوق ═══
                CREATE TABLE IF NOT EXISTS market_listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seller_id INTEGER NOT NULL,
                    subscription_id INTEGER NOT NULL,
                    code TEXT,
                    plan TEXT,
                    days INTEGER,
                    price INTEGER,
                    status TEXT DEFAULT 'active',
                    buyer_id INTEGER,
                    created_at TEXT,
                    sold_at TEXT,
                    expires_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS market_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id INTEGER NOT NULL,
                    seller_id INTEGER,
                    buyer_id INTEGER,
                    price INTEGER,
                    fee INTEGER,
                    created_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS market_complaints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id INTEGER,
                    user_id INTEGER,
                    reason TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    resolved_at TEXT
                );
                
                -- ═══ دروبات النقاط ═══
                CREATE TABLE IF NOT EXISTS points_drops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT UNIQUE NOT NULL,
                    points INTEGER NOT NULL,
                    created_by INTEGER,
                    created_at TEXT,
                    claimed_by INTEGER,
                    claimed_at TEXT,
                    is_active INTEGER DEFAULT 1
                );
                
                -- ═══ Force Join Cache ═══
                CREATE TABLE IF NOT EXISTS force_join_cache (
                    user_id INTEGER PRIMARY KEY,
                    checked_at TEXT,
                    is_member INTEGER
                );
                
                -- ═══ الدروبات المجدولة ═══
                CREATE TABLE IF NOT EXISTS scheduled_drops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan TEXT NOT NULL,
                    days INTEGER NOT NULL,
                    interval_minutes INTEGER NOT NULL,
                    next_run TEXT,
                    last_run TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_by INTEGER,
                    created_at TEXT
                );
                
                -- ═══ الألعاب ═══
                CREATE TABLE IF NOT EXISTS game_plays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    game_type TEXT NOT NULL,
                    cost INTEGER DEFAULT 0,
                    prize INTEGER DEFAULT 0,
                    result TEXT,
                    played_at TEXT
                );
                
                -- ═══ المهام اليومية ═══
                CREATE TABLE IF NOT EXISTS daily_missions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    mission_key TEXT,
                    progress INTEGER DEFAULT 0,
                    target INTEGER DEFAULT 1,
                    reward INTEGER,
                    completed_at TEXT,
                    claimed_at TEXT,
                    date TEXT,
                    UNIQUE(user_id, mission_key, date)
                );
                
                -- ═══ الإنجازات/الشارات ═══
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    achievement_key TEXT,
                    unlocked_at TEXT,
                    UNIQUE(user_id, achievement_key)
                );
                
                CREATE TABLE IF NOT EXISTS achievement_definitions (
                    key TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    icon TEXT,
                    target INTEGER,
                    reward INTEGER,
                    category TEXT
                );
                
                -- ═══ الترتيب الأسبوعي ═══
                CREATE TABLE IF NOT EXISTS weekly_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    week_key TEXT,
                    points_earned INTEGER DEFAULT 0,
                    invites INTEGER DEFAULT 0,
                    purchases INTEGER DEFAULT 0,
                    UNIQUE(user_id, week_key)
                );
                
                -- ═══ الشراكة ═══
                CREATE TABLE IF NOT EXISTS partnerships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id INTEGER,
                    user2_id INTEGER,
                    created_at TEXT,
                    is_active INTEGER DEFAULT 1,
                    total_earned INTEGER DEFAULT 0,
                    UNIQUE(user1_id, user2_id)
                );
                
                -- ═══ التحديات ═══
                CREATE TABLE IF NOT EXISTS challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    challenger_id INTEGER,
                    opponent_id INTEGER,
                    amount INTEGER,
                    game_type TEXT DEFAULT 'dice',
                    status TEXT DEFAULT 'pending',
                    winner_id INTEGER,
                    created_at TEXT,
                    completed_at TEXT
                );
                
                -- ═══ الفرق ═══
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_key TEXT UNIQUE,
                    name TEXT,
                    emoji TEXT,
                    total_points INTEGER DEFAULT 0,
                    members_count INTEGER DEFAULT 0,
                    created_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS team_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_key TEXT,
                    user_id INTEGER,
                    joined_at TEXT,
                    UNIQUE(team_key, user_id)
                );
                
                -- ═══ حقائب المستخدمين ═══
                CREATE TABLE IF NOT EXISTS user_backpack (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    item_type TEXT,
                    item_value TEXT,
                    item_data TEXT,
                    is_used INTEGER DEFAULT 0,
                    added_at TEXT
                );
                
                -- ═══ السجل ═══
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT,
                    details TEXT,
                    created_at TEXT
                );
                
                -- ═══ سجل المراقبة ═══
                CREATE TABLE IF NOT EXISTS monitoring_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_type TEXT,
                    status TEXT,
                    details TEXT,
                    checked_at TEXT
                );
            """)
            await db.commit()

    # ═══════════════════════════════════════════════════════════════
    # المستخدمون
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # المفاتيح
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # الاشتراكات
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # القنوات
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # الدروبات
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # دروبات النقاط
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # البيضاوي
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # التصويت
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # المزاد
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # السوق
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # Force Join
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # المجدولة
    # ═══════════════════════════════════════════════════════════════
    
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

    # ═══════════════════════════════════════════════════════════════
    # السجلات
    # ═══════════════════════════════════════════════════════════════
    
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
    if not isinstance(resp, dict):
        return None
    data = resp.get("data")
    if isinstance(data, dict):
        code = data.get("code")
        if code:
            return str(code)
    return None


class ApiClient:
    async def _headers(self):
        active = await db.get_active_key()
        if not active:
            return None, None
        return {
            "Authorization": f"Bearer {active['key_value'].strip()}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }, active

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
            if active:
                await db.record_key_result(active["id"], True)
            return {"ok": True, "data": data}
        except requests.exceptions.HTTPError as e:
            if active:
                await db.record_key_result(active["id"], False)
            code = e.response.status_code if e.response is not None else 0
            body = ""
            if e.response is not None:
                try:
                    body = e.response.text[:300]
                except Exception:
                    pass
            if code == 401:
                return {"ok": False, "error": "unauthorized", "message": "🔴 المفتاح غير صالح"}
            if code == 404:
                return {"ok": False, "error": "not_found", "message": "❌ الكود غير موجود (404)"}
            if code == 400:
                return {"ok": False, "error": "bad_request", "message": f"❌ طلب خاطئ: {body}"}
            return {"ok": False, "error": f"http_{code}", "message": f"❌ خطأ HTTP {code}"}
        except requests.exceptions.Timeout:
            if active:
                await db.record_key_result(active["id"], False)
            return {"ok": False, "error": "timeout", "message": "⏱️ انتهت المهلة"}
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
            if r.status_code == 401:
                return False, "🔴 غير صالح"
            if r.status_code in (200, 204):
                return True, "🟢 صالح"
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

# القائمة الرئيسية
BTN_SHOP      = "🛒 المتجر"
BTN_SUBS      = "📦 اشتراكاتي"
BTN_WALLET    = "💎 محفظتي"
BTN_EARN      = "🎁 اكسب نقاط"
BTN_MARKET    = "🛒 السوق"
BTN_TOP       = "🏆 الصدارة"
BTN_GAMES     = "🎮 الألعاب"
BTN_GUIDE     = "📖 كيف أفعّل"
BTN_CHECK     = "🔍 فحص كود"
BTN_STATUS    = "📊 حالتي"
BTN_CALC      = "🧮 حاسبة"
BTN_ARCHIVE   = "📚 الأرشيف"
BTN_BACKPACK  = "🎒 حقيبتي"
BTN_ACHIEVEMENTS = "🏅 إنجازاتي"
BTN_SETTINGS  = "⚙️ الإعدادات"
BTN_ABOUT     = "ℹ️ عن البوت"
BTN_ADMIN     = "🛡️ لوحة المشرف"
BTN_HOME      = "🏠 القائمة الرئيسية"
BTN_BACK      = "🔙 رجوع"
BTN_CANCEL    = "❌ إلغاء"

# الشراء
BTN_PLUS      = "⭐ بلس"
BTN_PRO       = "💎 برو"
BTN_PREMIUM   = "👑 بريميوم"
BTN_QTY_1     = "1 كود"
BTN_QTY_2     = "2 كود"
BTN_QTY_3     = "3 أكواد"
BTN_QTY_5     = "5 أكواد"
BTN_QTY_10    = "10 أكواد"
BTN_QTY_CUSTOM = "✏️ عدد مخصص"
BTN_CONFIRM   = "✅ تأكيد الطلب"
BTN_EDIT_QTY  = "✏️ تعديل العدد"

# المحفظة
BTN_TRANSFER  = "💸 تحويل نقاط"
BTN_DAILY     = "🎁 المكافأة اليومية"
BTN_INVITE    = "🔗 دعوة أصدقاء"
BTN_MY_ID     = "🆔 معرفي"

# الإعدادات
BTN_LANG      = "🌍 اللغة"
BTN_THEME     = "🌙 المظهر"
BTN_NOTIF     = "🔔 الإشعارات"

# الألعاب
BTN_GAME_BOX  = "📦 اختر صندوقك"
BTN_GAME_ODD_EVEN = "🎲 زوجي/فردي"
BTN_GAME_CARDS = "🃏 البطاقات"
BTN_GAME_BLACK = "🎭 السوق السوداء"
BTN_GAME_WHEEL = "🎡 عجلة الحظ"
BTN_GAME_CHASE = "⏱️ مطاردة الوقت"
BTN_GAME_TREASURE = "🗺️ الكنز المخفي"
BTN_GAME_DICE_DUEL = "🤼 تحدي الأصدقاء"

# المشرف
BTN_KEYS      = "🔑 إدارة المفاتيح"
BTN_CHANNELS  = "📢 إدارة القنوات"
BTN_DROPS     = "🎁 دروب اشتراكات"
BTN_PDROPS    = "💎 دروب نقاط"
BTN_STATS     = "📊 إحصائيات"
BTN_DASHBOARD = "📊 لوحة التحكم"
BTN_ANALYTICS = "📈 التحليلات"
BTN_MONITORING = "🔍 المراقبة"
BTN_BACKUP    = "💾 النسخ الاحتياطي"
BTN_LOGS      = "📜 السجل"
BTN_BROADCAST = "📢 بث"
BTN_ADD_KEY   = "➕ إضافة مفتاح"
BTN_CREATE_DROP = "➕ إنشاء دروب"
BTN_CREATE_PDROP = "➕ دروب نقاط"

# أنواع الدروبات
BTN_DROP_EGG = "🥚 بيضاوي"
BTN_DROP_COND = "🔒 بشرط"
BTN_DROP_CHAIN = "🔗 تسلسلي"
BTN_DROP_VOTE = "🗳️ تصويت"
BTN_DROP_AUCTION = "🔨 مزاد"
BTN_ALL_DROPS = "📋 كل الدروبات"
BTN_SCHEDULED = "⏰ مجدولة"
BTN_SCHEDULED_ADD = "➕ إضافة مجدول"

def is_admin(uid):
    return uid == SUPER_ADMIN_ID

# ═══════════════════════════════════════════════════════════════════
# ⚠️ نهاية الجزء 1/8 — انتظر الجزء 2/8
# ⚠️ لا تشغّل البوت الآن
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# ⌨️ لوحات المفاتيح
# ═══════════════════════════════════════════════════════════════════

def kb_main(admin=False):
    rows = [
        [KeyboardButton(BTN_SHOP), KeyboardButton(BTN_SUBS)],
        [KeyboardButton(BTN_WALLET), KeyboardButton(BTN_EARN)],
        [KeyboardButton(BTN_MARKET), KeyboardButton(BTN_GAMES)],
        [KeyboardButton(BTN_TOP), KeyboardButton(BTN_CHECK)],
        [KeyboardButton(BTN_STATUS), KeyboardButton(BTN_CALC)],
        [KeyboardButton(BTN_GUIDE), KeyboardButton(BTN_ARCHIVE)],
        [KeyboardButton(BTN_BACKPACK), KeyboardButton(BTN_ACHIEVEMENTS)],
        [KeyboardButton(BTN_SETTINGS), KeyboardButton(BTN_ABOUT)],
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
    if len(days) >= 2:
        rows.append([KeyboardButton(f"{d} يوم") for d in days[:2]])
    if len(days) > 2:
        rows.append([KeyboardButton(f"{d} يوم") for d in days[2:]])
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

def kb_games():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_GAME_BOX), KeyboardButton(BTN_GAME_ODD_EVEN)],
        [KeyboardButton(BTN_GAME_CARDS), KeyboardButton(BTN_GAME_BLACK)],
        [KeyboardButton(BTN_GAME_WHEEL), KeyboardButton(BTN_GAME_CHASE)],
        [KeyboardButton(BTN_GAME_TREASURE), KeyboardButton(BTN_GAME_DICE_DUEL)],
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
        [KeyboardButton(BTN_DASHBOARD), KeyboardButton(BTN_ANALYTICS)],
        [KeyboardButton(BTN_KEYS), KeyboardButton(BTN_CHANNELS)],
        [KeyboardButton(BTN_DROPS), KeyboardButton(BTN_PDROPS)],
        [KeyboardButton(BTN_STATS), KeyboardButton(BTN_LOGS)],
        [KeyboardButton(BTN_SCHEDULED), KeyboardButton(BTN_ALL_DROPS)],
        [KeyboardButton(BTN_MONITORING), KeyboardButton(BTN_BACKUP)],
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
    if not iso_str:
        return "غير محدد"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "").split(".")[0])
        diff = datetime.now() - dt
        s = int(diff.total_seconds())
        if s < 60:
            return f"منذ {s} ثانية"
        if s < 3600:
            return f"منذ {s // 60} دقيقة"
        if s < 86400:
            return f"منذ {s // 3600} ساعة"
        return f"منذ {s // 86400} يوم"
    except Exception:
        return str(iso_str)[:16]

def format_date(iso_str):
    if not iso_str:
        return "غير محدد"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "").split(".")[0])
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(iso_str)[:16]

def format_duration(seconds):
    """يحول الثواني إلى صيغة مقروءة"""
    if seconds < 60:
        return f"{seconds} ثانية"
    elif seconds < 3600:
        return f"{seconds // 60} دقيقة"
    elif seconds < 86400:
        return f"{seconds // 3600} ساعة"
    else:
        return f"{seconds // 86400} يوم"

def get_week_key():
    """مفتاح الأسبوع الحالي (YYYY-Www)"""
    now = datetime.now()
    week = now.isocalendar()[1]
    return f"{now.year}-W{week:02d}"

def get_today_key():
    return datetime.now().strftime("%Y-%m-%d")

# ═══════════════════════════════════════════════════════════════════
# 🔒 Force Join
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
# 🎁 بناء بطاقات الدروب (كل الأنواع)
# ═══════════════════════════════════════════════════════════════════

def build_drop_card_text(drop):
    plan_info = SUBSCRIPTION_TYPES.get(drop["plan"], {"emoji": "📦", "name": drop["plan"]})
    drop_type = drop.get("drop_type", "normal")
    winners_so_far = drop.get("current_winners", 0)
    max_winners = drop.get("max_winners", 1)

    type_emoji = {
        "normal": "🎁", "egg": "🥚", "conditional": "🔒",
        "chain": "🔗", "vote": "🗳️", "auction": "🔨"
    }.get(drop_type, "🎁")
    
    type_name = {
        "normal": "دروب", "egg": "دروب بيضاوي", "conditional": "دروب بشرط",
        "chain": "دروب تسلسلي", "vote": "دروب بتصويت", "auction": "مزاد"
    }.get(drop_type, "دروب")

    if drop_type == "auction":
        return _build_auction_text(drop, plan_info)

    is_claimed = bool(drop.get("claimed_by")) or (winners_so_far >= max_winners)

    if is_claimed and drop_type != "vote":
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

    conditions_line = ""
    if drop_type == "conditional":
        try:
            conds = json.loads(drop.get("conditions", "{}")) if drop.get("conditions") else {}
        except Exception:
            conds = {}
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
        vote_line = "\n\n🗳️ *انقر لتصويت* (الأكثر تصويتاً يفوز)"

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
# 🔄 تحديث فوري للدروب
# ═══════════════════════════════════════════════════════════════════

async def refresh_drop_immediately(context, drop_id):
    drop = await db.get_drop_by_id(drop_id)
    if not drop:
        return

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
# 🎮 أدوات الألعاب المشتركة
# ═══════════════════════════════════════════════════════════════════

_game_cache = {}

def can_play_game(user_id):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    cache = _game_cache.get(user_id, {})
    
    if cache.get("date") != today:
        cache = {"date": today, "plays_today": 0, "last_played": None}
        _game_cache[user_id] = cache
    
    if cache.get("plays_today", 0) >= GAME_DAILY_LIMIT:
        return False, f"🔒 وصلت للحد اليومي ({GAME_DAILY_LIMIT} ألعاب)"
    
    last = cache.get("last_played")
    if last:
        diff = (now - last).total_seconds()
        if diff < GAME_COOLDOWN_SECONDS:
            remaining = int(GAME_COOLDOWN_SECONDS - diff)
            return False, f"⏳ انتظر {remaining} ثانية"
    
    return True, ""

def register_play(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    cache = _game_cache.get(user_id, {})
    if cache.get("date") != today:
        cache = {"date": today, "plays_today": 0, "last_played": None}
    cache["plays_today"] = cache.get("plays_today", 0) + 1
    cache["last_played"] = datetime.now()
    _game_cache[user_id] = cache

async def check_play_ready(update, user_id, game_key):
    ok, msg = can_play_game(user_id)
    if not ok:
        await update.message.reply_text(msg, reply_markup=kb_main(is_admin(user_id)))
        return False
    
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(is_admin(user_id)))
        return False
    
    cost = GAME_COSTS.get(game_key, 10)
    if user["points"] < cost:
        await update.message.reply_text(
            f"❌ *نقاطك غير كافية*\n\n"
            f"💰 تحتاج: `{cost}` نقطة\n"
            f"💎 رصيدك: `{user['points']}`",
            parse_mode="Markdown", reply_markup=kb_main(is_admin(user_id)))
        return False
    
    return True

async def log_game_play(user_id, game_type, cost, prize, result):
    async with aiosqlite.connect(DB_PATH) as db_conn:
        await db_conn.execute("""INSERT INTO game_plays 
            (user_id, game_type, cost, prize, result, played_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, game_type, cost, prize, result, datetime.now().isoformat()))
        await db_conn.commit()

# ═══════════════════════════════════════════════════════════════════
# 📊 دوال الإحصائيات المساعدة
# ═══════════════════════════════════════════════════════════════════

async def get_system_stats():
    """إحصائيات النظام الشاملة"""
    users = await db.count_users()
    subs = await db.count_subscriptions()
    keys = await db.list_api_keys()
    channels = await db.list_channels()
    total_drops = await db.count_drops()
    claimed_drops = await db.count_claimed_drops()
    
    async with aiosqlite.connect(DB_PATH) as db_conn:
        async with db_conn.execute("SELECT SUM(total_points_spent) FROM users") as cur:
            total_spent = (await cur.fetchone())[0] or 0
        async with db_conn.execute("SELECT SUM(total_points_earned) FROM users") as cur:
            total_earned = (await cur.fetchone())[0] or 0
        async with db_conn.execute("SELECT COUNT(*) FROM game_plays") as cur:
            total_games = (await cur.fetchone())[0]
        async with db_conn.execute("SELECT COUNT(*) FROM market_listings WHERE status='active'") as cur:
            active_listings = (await cur.fetchone())[0]
    
    return {
        "users": users,
        "subscriptions": subs,
        "keys": len(keys),
        "channels": len(channels),
        "total_drops": total_drops,
        "claimed_drops": claimed_drops,
        "active_drops": total_drops - claimed_drops,
        "total_points_spent": total_spent,
        "total_points_earned": total_earned,
        "total_games": total_games,
        "active_listings": active_listings,
    }

async def get_channel_stats():
    """إحصائيات القنوات"""
    async with aiosqlite.connect(DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        async with db_conn.execute("""
            SELECT c.*, 
                   (SELECT COUNT(*) FROM drop_messages dm WHERE dm.chat_id = c.chat_id) as drops_count
            FROM channels c WHERE c.is_active = 1
            ORDER BY drops_count DESC
        """) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def get_top_weekly(limit=10):
    """أفضل المستخدمين هذا الأسبوع"""
    week_key = get_week_key()
    async with aiosqlite.connect(DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        async with db_conn.execute("""
            SELECT ws.*, u.first_name, u.username 
            FROM weekly_scores ws
            JOIN users u ON u.user_id = ws.user_id
            WHERE ws.week_key = ?
            ORDER BY ws.points_earned DESC
            LIMIT ?
        """, (week_key, limit)) as cur:
            return [dict(r) for r in await cur.fetchall()]

# ═══════════════════════════════════════════════════════════════════
# 🎬 Chat member handler (إضافة/إزالة البوت من قنوات)
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

# ═══════════════════════════════════════════════════════════════════
# ⚠️ نهاية الجزء 2/8 — انتظر الجزء 3/8
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# 🎬 start + معالجة الروابط
# ═══════════════════════════════════════════════════════════════════

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

    txt = f"👋 أهلاً *{user.first_name}*!\n\n"
    txt += "🤖 *Worm GPT* — بوت إدارة الاشتراكات\n\n"
    
    if is_new:
        txt += "🎉 تم تسجيلك بنجاح!\n"
        if invited_by:
            txt += "🎁 حصل داعيك على نقطة!\n"
        txt += "\n"
    
    # تحديث VIP
    await db.update_vip_tier(user.id)
    u = await db.get_user(user.id)
    tier = get_vip_tier(u["points"])
    tier_info = VIP_TIERS[tier]
    
    txt += f"💎 رصيدك: `{u['points']}`\n"
    txt += f"🏅 مستواك: {tier_info['name']}\n\n"
    txt += "استخدم الأزرار بالأسفل 👇"
    
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb_main(admin))

async def handle_drop_entry(update, context, token):
    """معالج فتح الدروب من رابط"""
    user = update.effective_user
    await db.register_user(user.id, user.username, user.first_name)
    admin = is_admin(user.id)

    drop = await db.get_drop(token)
    if not drop or not isinstance(drop, dict):
        await update.message.reply_text(
            "❌ *الدروب غير موجود*",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return

    drop_type = drop.get("drop_type", "normal")

    if drop_type == "egg":
        await handle_egg_open(update, context, drop)
        return
    if drop_type == "conditional":
        await handle_conditional_open(update, context, drop)
        return
    if drop_type == "chain":
        await handle_chain_open(update, context, drop)
        return
    if drop_type == "vote":
        await handle_vote_open(update, context, drop)
        return
    if drop_type == "auction":
        await handle_auction_open(update, context, drop)
        return

    # دروب عادي
    if not drop["is_active"] or drop["claimed_by"]:
        await update.message.reply_text(
            "😔 *حظاً أوفر!*\n\nهذا الدروب مُستخدم أو منتهي.",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return

    drop_info = SUBSCRIPTION_TYPES.get(drop["plan"], {})
    api_plan = drop_info.get("api_plan", drop["plan"])
    
    await update.message.reply_text("🎁 جاري إنشاء كودك...", reply_markup=kb_main(admin))
    
    result = await api.create(api_plan, drop["days"], 1)
    if not result["ok"]:
        await update.message.reply_text(
            f"❌ فشل: {result.get('message')}",
            reply_markup=kb_main(admin)
        )
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
        f"{info['emoji']} {info['name']}\n"
        f"📅 {drop['days']} يوم\n"
        f"🔑 *كودك:* `{code}`\n\n"
        f"📖 فعّله في: {SITE_URL}",
        parse_mode="Markdown", reply_markup=kb_main(admin),
        disable_web_page_preview=True
    )
    
    try:
        await context.bot.send_message(
            SUPER_ADMIN_ID,
            f"🔔 *دروب استُخدم!*\n\n"
            f"🎁 #{drop['token']}\n"
            f"👤 `{user.id}`\n"
            f"🔑 `{code}`",
            parse_mode="Markdown"
        )
    except Exception:
        pass

async def handle_points_drop_entry(update, context, token):
    """معالج دروب النقاط"""
    user = update.effective_user
    await db.register_user(user.id, user.username, user.first_name)
    admin = is_admin(user.id)
    
    pd = await db.get_points_drop(token)
    if not pd or not pd["is_active"] or pd["claimed_by"]:
        await update.message.reply_text(
            "😔 *حظاً أوفر!*",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return
    
    await db.claim_points_drop(token, user.id)
    await db.add_points(user.id, pd["points"], "points_drop_claim", pd["id"])
    await db.update_vip_tier(user.id)
    
    await update.message.reply_text(
        f"🎉 *مبروك!*\n\n"
        f"💰 حصلت على `{pd['points']}` نقطة!\n\n"
        f"💎 رصيدك: `{(await db.get_user(user.id))['points']}`",
        parse_mode="Markdown", reply_markup=kb_main(admin)
    )

# ═══════════════════════════════════════════════════════════════════
# 🏠 القوائم الأساسية
# ═══════════════════════════════════════════════════════════════════

async def show_home(update, context):
    user_id = update.effective_user.id
    admin = is_admin(user_id)
    context.user_data["state"] = "main"
    
    u = await db.get_user(user_id)
    if u:
        await db.update_vip_tier(user_id)
        u = await db.get_user(user_id)
        tier = get_vip_tier(u["points"])
        tier_info = VIP_TIERS[tier]
        
        await update.message.reply_text(
            f"🏠 *القائمة الرئيسية*\n\n"
            f"💎 رصيدك: `{u['points']}`\n"
            f"🏅 مستواك: {tier_info['name']}\n\n"
            f"اختر من الأزرار:",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
    else:
        await update.message.reply_text(
            "🏠 *القائمة الرئيسية*\n\nأرسل /start للتسجيل",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )

async def show_shop(update, context):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(False))
        return
    
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
        parse_mode="Markdown", reply_markup=kb_shop()
    )

async def show_subs(update, context):
    user_id = update.effective_user.id
    admin = is_admin(user_id)
    subs = await db.get_user_subs(user_id)
    
    if not subs:
        await update.message.reply_text(
            "📭 *لا يوجد اشتراكات*\n\n"
            "🛒 اذهب للمتجر للشراء",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return
    
    lines = [f"📋 *اشتراكاتك* ({len(subs)}):\n"]
    for i, s in enumerate(subs[:10], 1):
        info = SUBSCRIPTION_TYPES.get(s["plan"], {"emoji": "📦", "name": s["plan"]})
        status_emoji = "✅" if s["status"] == "active" else "⏰"
        date = s["created_at"][:10] if s["created_at"] else "?"
        lines.append(f"{i}. {status_emoji} {info['emoji']} {info['name']}")
        lines.append(f"   📅 {s['days']}ي — {date}")
    
    if len(subs) > 10:
        lines.append(f"\n... و {len(subs) - 10} أخرى (📚 الأرشيف)")
    
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown", reply_markup=kb_main(admin)
    )

async def show_wallet(update, context):
    user_id = update.effective_user.id
    u = await db.get_user(user_id)
    if not u:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(False))
        return
    
    rank, total = await db.get_user_rank(user_id)
    tier = get_vip_tier(u["points"])
    tier_info = VIP_TIERS[tier]
    context.user_data["state"] = "wallet"
    
    await update.message.reply_text(
        f"💎 *محفظتي*\n\n"
        f"💰 الرصيد: `{u['points']}`\n"
        f"🏅 المستوى: {tier_info['name']}\n"
        f"🏆 الترتيب: `{rank}` من `{total}`\n\n"
        f"📈 إجمالي كسبت: `{u['total_points_earned']}`\n"
        f"📉 إجمالي صرفت: `{u['total_points_spent']}`\n"
        f"🔥 سلسلة يومية: `{u.get('daily_streak', 0)}` يوم",
        parse_mode="Markdown", reply_markup=kb_wallet()
    )

async def show_earn(update, context):
    context.user_data["state"] = "earn"
    await update.message.reply_text(
        "🎁 *كسب النقاط*\n\n"
        "1️⃣ المكافأة اليومية (مع سلسلة)\n"
        "2️⃣ دعوة الأصدقاء\n"
        "3️⃣ استلام تحويلات\n\nاختر:",
        parse_mode="Markdown", reply_markup=kb_earn()
    )

async def show_games_menu(update, context):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(False))
        return
    
    context.user_data["state"] = "games"
    
    # عدد الألعاب اليوم
    cache = _game_cache.get(user_id, {})
    today = datetime.now().strftime("%Y-%m-%d")
    plays_today = cache.get("plays_today", 0) if cache.get("date") == today else 0
    
    await update.message.reply_text(
        f"🎮 *الألعاب*\n\n"
        f"💎 رصيدك: `{user['points']}`\n"
        f"🎯 العب اليوم: `{plays_today}/{GAME_DAILY_LIMIT}`\n\n"
        f"💰 *الأسعار:*\n"
        f"📦 صندوقك: `{GAME_COSTS['box']}` نقطة\n"
        f"🎲 زوجي/فردي: `{GAME_COSTS['odd_even']}` نقطة\n"
        f"🃏 البطاقات: `{GAME_COSTS['cards']}` نقطة\n"
        f"🎭 السوق السوداء: `{GAME_COSTS['black_market']}` نقطة\n"
        f"🎡 عجلة الحظ: `{GAME_COSTS['wheel']}` نقطة\n"
        f"⏱️ مطاردة الوقت: `{GAME_COSTS['time_chase']}` نقطة\n"
        f"🗺️ الكنز: `{GAME_COSTS['treasure']}` نقطة\n"
        f"🤼 تحدي: `{GAME_COSTS['dice_duel']}` نقطة\n\n"
        f"اختر لعبة:",
        parse_mode="Markdown", reply_markup=kb_games()
    )

async def show_top(update, context):
    top = await db.top_users(10)
    user_id = update.effective_user.id
    my_rank, total = await db.get_user_rank(user_id)
    me = await db.get_user(user_id)
    
    lines = ["🏆 *أفضل 10 مستخدمين:*\n"]
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, u in enumerate(top, 1):
        medal = medals[i-1] if i <= 10 else f"{i}."
        name = u.get("first_name") or "مستخدم"
        username = u.get("username")
        ref = f"@{username}" if username else f"`{u['user_id']}`"
        tier = VIP_TIERS.get(u.get("vip_tier", "bronze"), {})
        tier_emoji = tier.get("emoji", "")
        marker = " ← *أنت*" if u["user_id"] == user_id else ""
        lines.append(f"{medal} {tier_emoji} *{name}* — {ref}")
        lines.append(f"   💎 {u['points']}{marker}")
    
    lines.append("\n" + "─" * 20)
    
    if my_rank <= 10:
        lines.append(f"🎯 *ترتيبك:* {my_rank} (ضمن أفضل 10!)")
    elif my_rank > 0 and me:
        if top:
            diff = top[-1]["points"] - me["points"]
            lines.append(f"🎯 *ترتيبك:* `{my_rank}` من `{total}`")
            lines.append(f"💎 نقاطك: `{me['points']}`")
            lines.append(f"⬆️ تحتاج `{max(1, diff+1)}` نقطة للدخول")
        else:
            lines.append(f"🎯 *ترتيبك:* `{my_rank}` من `{total}`")
    
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown", reply_markup=kb_main(is_admin(user_id))
    )

async def show_guide(update, context):
    user_id = update.effective_user.id
    last_sub = await db.get_last_sub_code(user_id)
    
    guide = (
        "📖 *دليل التفعيل*\n\n"
        "1️⃣ افتح الموقع\n"
        "2️⃣ سجّل الدخول\n"
        "3️⃣ القائمة الجانبية (☰)\n"
        "4️⃣ قسم الخطط\n"
        "5️⃣ انزل → \"كود التفعيل\"\n"
        "6️⃣ الصق الكود → تفعيل ✅\n\n"
    )
    
    if last_sub:
        guide += f"─────────────────\n"
        guide += f"🔑 *آخر كود:*\n`{last_sub['code']}`\n\n"
        guide += f"📦 {last_sub['plan']} — {last_sub['days']}ي"
    else:
        guide += "─────────────────\n⚠️ لا تملك كوداً بعد."
    
    guide += f"\n\n🌐 {SITE_URL}"
    
    await update.message.reply_text(
        guide,
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(user_id)),
        disable_web_page_preview=True
    )

async def show_about(update, context):
    user_id = update.effective_user.id
    types = "\n".join([
        f"{i['emoji']} *{i['name']}* — {i['description']}"
        for i in SUBSCRIPTION_TYPES.values()
    ])
    
    await update.message.reply_text(
        f"🤖 *Worm GPT*\n\n"
        f"بوت إدارة اشتراكات احترافي\n\n"
        f"📦 *الباقات:*\n{types}\n\n"
        f"✨ *الميزات:*\n"
        f"• شراء اشتراكات بالنقاط\n"
        f"• دروبات متعددة\n"
        f"• ألعاب تفاعلية\n"
        f"• سوق مستخدمين\n"
        f"• نظام VIP\n"
        f"• دعوات وأصدقاء\n\n"
        f"📢 *القناة:* @{CHANNEL_USERNAME}\n"
        f"🌐 {SITE_URL}",
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(user_id)),
        disable_web_page_preview=True
    )

async def show_status(update, context):
    user_id = update.effective_user.id
    u = await db.get_user(user_id)
    if not u:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(False))
        return
    
    subs = await db.get_user_subs(user_id)
    rank, total = await db.get_user_rank(user_id)
    tier = get_vip_tier(u["points"])
    tier_info = VIP_TIERS[tier]
    active_subs = sum(1 for s in subs if s["status"] == "active")
    
    # حالة المكافأة اليومية
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
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(False))
        return
    
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
    user_id = update.effective_user.id
    admin = is_admin(user_id)
    subs = await db.get_all_user_subs(user_id)
    
    if not subs:
        await update.message.reply_text(
            "📭 *لا يوجد اشتراكات في الأرشيف*",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return
    
    lines = [f"📚 *أرشيف اشتراكاتك* ({len(subs)})\n"]
    for i, s in enumerate(subs[:30], 1):
        info = SUBSCRIPTION_TYPES.get(s["plan"], {"emoji": "📦", "name": s["plan"]})
        status = "✅" if s["status"] == "active" else "⏰"
        date = s["created_at"][:10] if s["created_at"] else "?"
        lines.append(f"{i}. {status} {info['emoji']} {info['name']} — {s['days']}ي — {date}")
    
    if len(subs) > 30:
        lines.append(f"\n... و {len(subs) - 30} أخرى")
    
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown", reply_markup=kb_main(admin)
    )

async def show_backpack(update, context):
    """حقيبة المستخدم"""
    user_id = update.effective_user.id
    admin = is_admin(user_id)
    
    async with aiosqlite.connect(DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        async with db_conn.execute(
            "SELECT * FROM user_backpack WHERE user_id=? AND is_used=0 ORDER BY id DESC LIMIT 20",
            (user_id,)
        ) as cur:
            items = [dict(r) for r in await cur.fetchall()]
    
    if not items:
        await update.message.reply_text(
            "🎒 *حقيبتك فارغة*\n\n"
            "💡 اكسب جوائز من الدروبات والألعاب",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return
    
    lines = [f"🎒 *حقيبتك* ({len(items)} عنصر)\n"]
    for i, item in enumerate(items[:15], 1):
        icon = {"code": "🔑", "points": "💎", "coupon": "🎟️"}.get(item["item_type"], "🎁")
        lines.append(f"{i}. {icon} {item['item_value'][:50]}")
    
    if len(items) > 15:
        lines.append(f"\n... و {len(items) - 15} أخرى")
    
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown", reply_markup=kb_main(admin)
    )

async def show_achievements(update, context):
    """إنجازات المستخدم"""
    user_id = update.effective_user.id
    admin = is_admin(user_id)
    
    async with aiosqlite.connect(DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        async with db_conn.execute(
            "SELECT achievement_key, unlocked_at FROM achievements WHERE user_id=? ORDER BY unlocked_at DESC",
            (user_id,)
        ) as cur:
            achievements = [dict(r) for r in await cur.fetchall()]
    
    if not achievements:
        await update.message.reply_text(
            "🏅 *لا توجد إنجازات بعد*\n\n"
            "💡 اشترِ، ادعُ أصدقاء، العب لتحصل على شارات",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return
    
    lines = [f"🏅 *إنجازاتك* ({len(achievements)})\n"]
    for a in achievements[:20]:
        lines.append(f"✅ {a['achievement_key']}")
        lines.append(f"   📅 {a['unlocked_at'][:10]}")
    
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown", reply_markup=kb_main(admin)
    )

async def show_settings(update, context):
    context.user_data["state"] = "settings"
    await update.message.reply_text(
        "⚙️ *الإعدادات*\n\nاختر:",
        parse_mode="Markdown", reply_markup=kb_settings()
    )

async def show_language(update, context):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="settings_back")],
    ])
    await update.message.reply_text(
        "🌍 *اختر اللغة:*",
        parse_mode="Markdown", reply_markup=kb
    )

async def lang_callback(update, context):
    query = update.callback_query
    lang = query.data.replace("lang_", "")
    if lang in ("ar", "en"):
        await db.set_language(update.effective_user.id, lang)
        await query.answer(f"✅ {'العربية' if lang == 'ar' else 'English'}")
        await query.edit_message_text(
            f"✅ *تم تغيير اللغة!*\n\nاللغة: {'🇸🇦 العربية' if lang == 'ar' else '🇬🇧 English'}",
            parse_mode="Markdown"
        )
    else:
        await query.answer("❌ غير مدعومة", show_alert=True)

async def show_theme(update, context):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("☀️ نهاري", callback_data="theme_day")],
        [InlineKeyboardButton("🌙 ليلي", callback_data="theme_night")],
        [InlineKeyboardButton("🔄 تلقائي", callback_data="theme_auto")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="settings_back")],
    ])
    await update.message.reply_text(
        "🌙 *اختر المظهر:*",
        parse_mode="Markdown", reply_markup=kb
    )

async def theme_callback(update, context):
    query = update.callback_query
    theme = query.data.replace("theme_", "")
    if theme in ("day", "night", "auto"):
        await db.set_theme(update.effective_user.id, theme)
        names = {"day": "☀️ نهاري", "night": "🌙 ليلي", "auto": "🔄 تلقائي"}
        await query.answer(f"✅ {names[theme]}")
        await query.edit_message_text(
            f"✅ *تم تغيير المظهر!*\n\n{names[theme]}",
            parse_mode="Markdown"
        )
    else:
        await query.answer("❌", show_alert=True)

async def show_notifications(update, context):
    user = await db.get_user(update.effective_user.id)
    if not user:
        return
    
    try:
        notif = json.loads(user.get("notifications") or "{}")
    except Exception:
        notif = {}
    
    drops = notif.get("drops", True)
    daily = notif.get("daily", True)
    promos = notif.get("promos", False)
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'✅' if drops else '☐'} دروبات جديدة", callback_data="notif_drops")],
        [InlineKeyboardButton(f"{'✅' if daily else '☐'} مكافأة يومية", callback_data="notif_daily")],
        [InlineKeyboardButton(f"{'✅' if promos else '☐'} عروض خاصة", callback_data="notif_promos")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="settings_back")],
    ])
    
    await update.message.reply_text(
        "🔔 *الإشعارات*\n\nاضغط لتفعيل/إلغاء:",
        parse_mode="Markdown", reply_markup=kb
    )

async def notif_callback(update, context):
    query = update.callback_query
    key = query.data.replace("notif_", "")
    user = await db.get_user(update.effective_user.id)
    if not user:
        return
    
    try:
        notif = json.loads(user.get("notifications") or "{}")
    except Exception:
        notif = {}
    
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
        "⚙️ *الإعدادات*",
        parse_mode="Markdown", reply_markup=kb_settings()
    )

# ═══════════════════════════════════════════════════════════════════
# 🔍 فحص كود
# ═══════════════════════════════════════════════════════════════════

async def check_code_begin(update, context):
    context.user_data["state"] = "check_code"
    await update.message.reply_text(
        "🔍 *فحص كود*\n\n"
        "أرسل الكود الذي تريد فحصه:\n\n"
        "❌ للإلغاء",
        parse_mode="Markdown", reply_markup=kb_cancel()
    )

async def check_code_receive(update, context, code):
    code = code.strip()
    if len(code) < 3:
        await update.message.reply_text("❌ الكود قصير جداً:", reply_markup=kb_cancel())
        return
    
    admin = is_admin(update.effective_user.id)
    wait_msg = await update.message.reply_text("🔍 جاري الفحص...")
    
    result = await api.check_code(code)
    
    if not result["ok"]:
        try:
            await wait_msg.edit_text(
                f"❌ *فشل الفحص*\n\n`{result.get('message', '')[:200]}`",
                parse_mode="Markdown"
            )
        except Exception:
            await wait_msg.edit_text(f"❌ {result.get('message', '')[:200]}")
        
        context.user_data["state"] = "main"
        await update.message.reply_text("استخدم الأزرار:", reply_markup=kb_main(admin))
        return
    
    data = result["data"]
    info = data.get("data") if isinstance(data, dict) and "data" in data else data
    
    if not isinstance(info, dict):
        info = {}
    
    code_val = info.get("code", code)
    plan = info.get("plan", "?")
    days = info.get("days", "?")
    max_uses = info.get("max_uses", "?")
    uses = info.get("uses", 0)
    status = info.get("status", "?")
    created_at = info.get("created_at")
    expires_at = info.get("expires_at")
    
    plan_info = SUBSCRIPTION_TYPES.get(plan, {"emoji": "📦", "name": plan})
    status_map = {
        "active": "🟢 نشط",
        "used": "🔴 مستخدم",
        "expired": "⏰ منتهي",
        "disabled": "🚫 معطّل"
    }
    status_display = status_map.get(status, f"ℹ️ {status}")
    
    if isinstance(uses, int) and isinstance(max_uses, int):
        uses_display = f"`{uses}/{max_uses}`"
        if uses >= max_uses:
            uses_display += " ⚠️"
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
        f"✅ *نتيجة الفحص*\n\n"
        f"🔑 *الكود:*\n`{code_val}`\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"{plan_info['emoji']} *النوع:* {plan_info['name']}\n"
        f"📅 *المدة:* `{days}` يوم\n"
        f"🔢 *الاستخدامات:* {uses_display}\n"
        f"📊 *الحالة:* {status_display}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📆 *أُنشئ:* {fmt(created_at)}\n"
        f"⏰ *ينتهي:* {fmt(expires_at)}"
    )
    
    try:
        await wait_msg.edit_text(report, parse_mode="Markdown")
    except Exception:
        await wait_msg.edit_text(report)
    
    context.user_data["state"] = "main"
    await update.message.reply_text(
        "💡 افحص كوداً آخر أو استخدم الأزرار:",
        reply_markup=kb_main(admin)
    )

# ═══════════════════════════════════════════════════════════════════
# 💰 مكافأة + دعوة + معرف
# ═══════════════════════════════════════════════════════════════════

async def do_daily(update, context):
    user_id = update.effective_user.id
    ok, msg = await db.claim_daily_bonus(user_id)
    await db.update_vip_tier(user_id)
    
    await update.message.reply_text(
        msg,
        reply_markup=kb_main(is_admin(user_id))
    )

async def show_invite(update, context):
    user_id = update.effective_user.id
    u = await db.get_user(user_id)
    if not u:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(False))
        return
    
    link = f"https://t.me/{context.bot.username}?start=ref_{u['user_id']}"
    
    await update.message.reply_text(
        f"🔗 *رابط دعوتك:*\n`{link}`\n\n"
        f"💰 *مكافآتك:*\n"
        f"• {POINTS_INVITE} نقطة لكل صديق\n"
        f"• نقاط إضافية عند شرائه",
        parse_mode="Markdown", reply_markup=kb_main(is_admin(user_id))
    )

async def show_my_id(update, context):
    user_id = update.effective_user.id
    u = await db.get_user(user_id)
    if not u:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(False))
        return
    
    await update.message.reply_text(
        f"🆔 *معرفك:*\n`{u['user_id']}`\n\n"
        f"💡 أعطه لمن يريد تحويل نقاط لك.",
        parse_mode="Markdown", reply_markup=kb_main(is_admin(user_id))
    )

# ═══════════════════════════════════════════════════════════════════
# ⚠️ نهاية الجزء 3/8 — انتظر الجزء 4/8
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# 💸 التحويل
# ═══════════════════════════════════════════════════════════════════

async def transfer_begin(update, context):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(False))
        return
    
    context.user_data["state"] = "transfer_id"
    context.user_data.pop("transfer_to", None)
    context.user_data.pop("transfer_amount", None)
    
    await update.message.reply_text(
        f"💸 *تحويل نقاط*\n\n"
        f"💎 رصيدك: `{user['points']}`\n\n"
        f"أرسل *معرف (ID)* المستخدم:\n"
        f"_(من @userinfobot)_\n\n"
        f"❌ للإلغاء",
        parse_mode="Markdown", reply_markup=kb_cancel()
    )

async def transfer_get_id(update, context, text):
    try:
        target_id = int(text)
    except ValueError:
        await update.message.reply_text("❌ معرف غير صالح. أرسل رقماً:",
                                          reply_markup=kb_cancel())
        return
    
    if target_id == update.effective_user.id:
        await update.message.reply_text("❌ لا يمكن التحويل لنفسك:",
                                          reply_markup=kb_cancel())
        return
    
    target = await db.get_user(target_id)
    if not target:
        await update.message.reply_text("❌ غير مسجل. أرسل معرفاً آخر:",
                                          reply_markup=kb_cancel())
        return
    
    context.user_data["transfer_to"] = target_id
    context.user_data["state"] = "transfer_amount"
    name = target.get("first_name") or target.get("username") or str(target_id)
    
    await update.message.reply_text(
        f"👤 *{name}*\n\n💎 أرسل عدد النقاط:",
        parse_mode="Markdown", reply_markup=kb_cancel()
    )

async def transfer_get_amount(update, context, text):
    try:
        amount = int(text)
        if amount < MIN_TRANSFER:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            f"❌ الحد الأدنى {MIN_TRANSFER}. أرسل رقماً:",
            reply_markup=kb_cancel()
        )
        return
    
    user = await db.get_user(update.effective_user.id)
    if not user or user["points"] < amount:
        await update.message.reply_text(
            f"🔒 رصيدك `{user['points'] if user else 0}`. أرسل أقل:",
            parse_mode="Markdown", reply_markup=kb_cancel()
        )
        return
    
    context.user_data["transfer_amount"] = amount
    context.user_data["state"] = "transfer_confirm"
    
    target = await db.get_user(context.user_data.get("transfer_to"))
    name = target.get("first_name") if target else "المستخدم"
    
    await update.message.reply_text(
        f"📋 *تأكيد:*\n\n"
        f"👤 *{name}*\n"
        f"💎 `{amount}` نقطة\n\n"
        f"أرسل `تأكيد` للمتابعة:",
        parse_mode="Markdown", reply_markup=kb_cancel()
    )

async def transfer_do_confirm(update, context, text):
    if text.strip().lower() not in ("تأكيد", "confirm", "نعم"):
        await update.message.reply_text(
            "❌ أرسل `تأكيد` أو ❌ إلغاء:",
            parse_mode="Markdown", reply_markup=kb_cancel()
        )
        return
    
    target_id = context.user_data.get("transfer_to")
    amount = context.user_data.get("transfer_amount")
    
    if not target_id or not amount:
        await show_home(update, context)
        return
    
    ok, msg = await db.transfer_points(update.effective_user.id, target_id, amount)
    
    if ok:
        target = await db.get_user(target_id)
        name = target.get("first_name") if target else "المستخدم"
        await update.message.reply_text(
            f"✅ *تم التحويل!*\n\n"
            f"👤 *{name}*\n"
            f"💎 `{amount}` نقطة",
            parse_mode="Markdown",
            reply_markup=kb_main(is_admin(update.effective_user.id))
        )
        try:
            await context.bot.send_message(
                target_id,
                f"🎁 *وصلك تحويل!*\n\n"
                f"💎 `{amount}` نقطة من مستخدم",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    else:
        await update.message.reply_text(
            f"❌ {msg}",
            reply_markup=kb_main(is_admin(update.effective_user.id))
        )
    
    context.user_data["state"] = "main"
    context.user_data.pop("transfer_to", None)
    context.user_data.pop("transfer_amount", None)

# ═══════════════════════════════════════════════════════════════════
# 🛒 الشراء
# ═══════════════════════════════════════════════════════════════════

async def buy_choose_type(update, context, sub_type):
    user_id = update.effective_user.id
    info = SUBSCRIPTION_TYPES[sub_type]
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(False))
        return
    
    tier = get_vip_tier(user["points"])
    vip_discount = VIP_TIERS[tier]["discount"]
    
    context.user_data["buy"] = {"type": sub_type}
    context.user_data["state"] = "buy_days"
    
    prices_text = "\n".join([f"  • {d} يوم = {p} 💎" for d, p in info["prices"].items()])
    
    await update.message.reply_text(
        f"{info['emoji']} *{info['name']}*\n\n"
        f"{info['description']}\n\n"
        f"💰 *الأسعار:*\n{prices_text}\n\n"
        f"💎 رصيدك: `{user['points']}`\n"
        f"🎁 خصم VIP: `{vip_discount}%`\n\n"
        f"📅 اختر المدة:",
        parse_mode="Markdown", reply_markup=kb_days(sub_type)
    )

async def buy_choose_days(update, context, days):
    ctx = context.user_data.get("buy", {})
    sub_type = ctx.get("type")
    
    if not sub_type:
        await show_shop(update, context)
        return
    
    info = SUBSCRIPTION_TYPES[sub_type]
    if days not in info["prices"]:
        await update.message.reply_text(
            "❌ مدة غير صحيحة",
            reply_markup=kb_days(sub_type)
        )
        return
    
    ctx["days"] = days
    ctx["unit_price"] = info["prices"][days]
    
    user = await db.get_user(update.effective_user.id)
    context.user_data["state"] = "buy_qty"
    
    await update.message.reply_text(
        f"{info['emoji']} *{info['name']}* — {days} يوم\n\n"
        f"💰 سعر الوحدة: `{info['prices'][days]}`\n"
        f"💎 رصيدك: `{user['points'] if user else 0}`\n\n"
        f"🔢 اختر عدد الأكواد:\n"
        f"_(خصم تلقائي للكميات)_",
        parse_mode="Markdown", reply_markup=kb_quantity()
    )

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
    if not user:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(False))
        return
    
    tier = get_vip_tier(user["points"])
    vip_discount = VIP_TIERS[tier]["discount"]
    if vip_discount > 0:
        vip_saving = total * vip_discount // 100
        total -= vip_saving
    
    if user["points"] < total:
        await update.message.reply_text(
            f"🔒 *نقاطك غير كافية*\n\n"
            f"المطلوب: `{total}` 💎\n"
            f"لديك: `{user['points']}` 💎",
            parse_mode="Markdown", reply_markup=kb_quantity()
        )
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
        f"{info['emoji']} *{info['name']}*\n"
        f"📅 {days} يوم\n"
        f"🔢 {qty} كود\n\n"
        f"─────────────────\n"
        f"سعر الوحدة: `{unit_price}` 💎\n"
        f"المجموع: `{subtotal}` 💎{discount_line}{vip_line}\n"
        f"─────────────────\n"
        f"✅ *الإجمالي: `{total}` 💎*\n"
        f"💎 رصيدك: `{user['points']}`\n"
        f"💵 المتبقي: `{user['points'] - total}`",
        parse_mode="Markdown", reply_markup=kb_confirm()
    )

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
            await update.message.reply_text(
                "❌ بيانات ناقصة. ابدأ من جديد.",
                reply_markup=kb_shop()
            )
            context.user_data["state"] = "shop"
            return
        
        user = await db.get_user(user_id)
        if not user or user["points"] < total:
            await update.message.reply_text(
                "🔒 نقاط غير كافية.",
                reply_markup=kb_main(admin)
            )
            return
        
        info = SUBSCRIPTION_TYPES[sub_type]
        api_plan = info["api_plan"]
        
        await update.message.reply_text(
            f"⏳ *جاري إنشاء {quantity} كود...*\n\n"
            f"📦 {info['name']} — {days} يوم",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        
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
                            first_error = "لا كود في الاستجابة"
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
                    f"❌ *عذراً، بريميوم غير متوفر حالياً*\n\n"
                    f"`{first_error[:200]}`\n\n"
                    f"💡 جرّب بلس أو برو",
                    parse_mode="Markdown", reply_markup=kb_main(admin)
                )
            else:
                await update.message.reply_text(
                    f"❌ *فشل الإنشاء*\n\n`{first_error[:200]}`",
                    parse_mode="Markdown", reply_markup=kb_main(admin)
                )
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
            await update.message.reply_text(
                "⚠️ فشل خصم النقاط.",
                reply_markup=kb_main(admin)
            )
            return
        
        await db.update_vip_tier(user_id)
        
        codes_text = "\n".join([f"`{c}`" for c in codes])
        warning = f"\n\n⚠️ فشل {failed} كود." if failed > 0 else ""
        
        await update.message.reply_text(
            f"✅ *تم إنشاء {len(codes)} كود!*\n\n"
            f"{info['emoji']} {info['name']} — {days} يوم\n"
            f"💎 خُصم: `{actual_total}` نقطة\n\n"
            f"🔑 *أكوادك:*\n{codes_text}"
            f"{warning}\n\n"
            f"📖 فعّلها في: {SITE_URL}",
            parse_mode="Markdown", reply_markup=kb_main(admin),
            disable_web_page_preview=True
        )
        
        context.user_data.pop("buy", None)
        context.user_data["state"] = "main"
    
    except Exception as e:
        logger.exception(f"[BUY] خطأ: {e}")
        try:
            await update.message.reply_text(
                f"❌ خطأ: `{str(e)[:150]}`",
                parse_mode="Markdown", reply_markup=kb_main(admin)
            )
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
    
    keys = await db.list_api_keys() or []
    active = next((k for k in keys if k["is_active"]), None)
    
    lines = ["🔑 *المفاتيح*\n"]
    if not keys:
        lines.append("لا توجد مفاتيح.")
    else:
        lines.append(f"🟢 النشط: `{active['label'] if active else '—'}`\n")
        lines.append(f"📊 المجموع: {len(keys)}\n")
        for k in keys[:10]:
            s = "🟢" if k["is_active"] else "⚪"
            label = k.get("label") or "—"
            success = k.get("success_count", 0)
            fail = k.get("fail_count", 0)
            lines.append(f"{s} #{k['id']} {label}")
            lines.append(f"   ✅ {success} ❌ {fail}")
    
    context.user_data["state"] = "keys"
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown", reply_markup=kb_keys()
    )

async def key_add_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "key_add_value"
    await update.message.reply_text(
        "🔐 *إضافة مفتاح*\n\n"
        "أرسل قيمة المفتاح:\n\n"
        "❌ للإلغاء",
        parse_mode="Markdown", reply_markup=kb_cancel()
    )

async def key_add_value(update, context, text):
    if len(text) < 5:
        await update.message.reply_text(
            "❌ المفتاح قصير جداً. أعد المحاولة:",
            reply_markup=kb_cancel()
        )
        return
    
    context.user_data["new_key_value"] = text
    context.user_data["state"] = "key_add_label"
    
    await update.message.reply_text(
        "✏️ أرسل اسماً وصفياً (مثلاً: `production`):",
        parse_mode="Markdown", reply_markup=kb_cancel()
    )

async def key_add_label(update, context, text):
    label = text[:50]
    value = context.user_data.pop("new_key_value", None)
    
    if not value:
        await show_admin(update, context)
        return
    
    await db.add_api_key(value, label, update.effective_user.id)
    
    ok, msg = await api.test_key(value)
    await update.message.reply_text(
        f"✅ *تم حفظ المفتاح*\n\n"
        f"🏷️ `{label}`\n"
        f"{msg}",
        parse_mode="Markdown", reply_markup=kb_keys()
    )
    context.user_data["state"] = "keys"

# ═══════════════════════════════════════════════════════════════════
# 🛒 السوق
# ═══════════════════════════════════════════════════════════════════

async def show_market(update, context):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ أرسل /start أولاً",
                                          reply_markup=kb_main(False))
        return
    
    context.user_data["state"] = "market"
    
    listings = await db.get_active_listings(15) or []
    
    lines = ["🛒 *السوق*\n"]
    lines.append(f"💡 عمولة البوت: {MARKETPLACE_FEE}%\n")
    
    if not listings:
        lines.append("📭 لا توجد منتجات حالياً.")
    else:
        lines.append(f"📊 المنتجات المتاحة: {len(listings)}\n")
        for l in listings[:10]:
            info = SUBSCRIPTION_TYPES.get(l["plan"], {"emoji": "📦", "name": l["plan"]})
            lines.append(f"• {info['emoji']} {info['name']} — {l['days']}ي — 💎 `{l['price']}`")
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 تصفح المنتجات", callback_data="market_browse")],
        [InlineKeyboardButton("📤 بيع كود", callback_data="market_sell")],
        [InlineKeyboardButton("📋 منتجاتي", callback_data="market_mine")],
    ])
    
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown", reply_markup=kb
    )

async def market_browse_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    listings = await db.get_active_listings(20) or []
    
    if not listings:
        await query.edit_message_text(
            "📭 لا توجد منتجات حالياً.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="market_back")
            ]])
        )
        return
    
    kb_rows = []
    for l in listings[:10]:
        info = SUBSCRIPTION_TYPES.get(l["plan"], {"emoji": "📦", "name": l["plan"]})
        kb_rows.append([InlineKeyboardButton(
            f"{info['emoji']} {info['name']} — {l['days']}ي — 💎{l['price']}",
            callback_data=f"market_view_{l['id']}"
        )])
    kb_rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="market_back")])
    
    await query.edit_message_text(
        "🛒 *المنتجات المتاحة:*\n\nاختر منتجاً لعرض التفاصيل:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb_rows)
    )

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
    seller_name = seller.get("first_name") if seller else "بائع"
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"🛒 اشترِ بـ {listing['price']} 💎",
            callback_data=f"market_buy_{listing['id']}"
        )],
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
        parse_mode="Markdown", reply_markup=kb
    )

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
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    else:
        await query.answer(f"❌ {result}", show_alert=True)

async def market_sell_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    subs = await db.get_user_subs(user_id, limit=20) or []
    sellable = [s for s in subs if s["status"] == "active"]
    
    if not sellable:
        await query.edit_message_text(
            "📭 لا تملك أكواداً للبيع.\n\n"
            "💡 اشترِ من المتجر أولاً.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="market_back")
            ]])
        )
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
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb_rows)
    )

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
        f"💰 *أرسل سعر البيع بالنقاط*\n\n"
        f"📝 الحد الأدنى: 1\n"
        f"💡 سيأخذ البوت عمولة {MARKETPLACE_FEE}%\n\n"
        f"❌ للإلغاء",
        parse_mode="Markdown"
    )

async def market_sell_receive_price(update, context, text):
    try:
        price = int(text)
        if price < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ رقم صحيح ≥ 1:",
            reply_markup=kb_cancel()
        )
        return
    
    sub_id = context.user_data.get("market_sell_sub_id")
    if not sub_id:
        await show_market(update, context)
        return
    
    async with aiosqlite.connect(DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        async with db_conn.execute(
            "SELECT * FROM subscriptions WHERE id=?", (sub_id,)
        ) as cur:
            sub = await cur.fetchone()
    
    if not sub:
        await update.message.reply_text(
            "❌ الكود غير موجود.",
            reply_markup=kb_main(is_admin(update.effective_user.id))
        )
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
        parse_mode="Markdown", reply_markup=kb_main(is_admin(update.effective_user.id))
    )
    
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
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="market_back")
            ]])
        )
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
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb_rows)
    )

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
# ⚠️ نهاية الجزء 4/8 — انتظر الجزء 5/8
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# 🎁 الدروبات — كل الأنواع
# ═══════════════════════════════════════════════════════════════════

# ─── أزرار البطاقة ───
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

# ═══════════════════════════════════════════════════════════════════
# 🥚 دروب بيضاوي
# ═══════════════════════════════════════════════════════════════════

async def handle_egg_open(update, context, drop):
    user = update.effective_user
    admin = is_admin(user.id)
    
    if not drop["is_active"] or drop.get("claimed_by"):
        await update.message.reply_text(
            "😔 *حظاً أوفر!*",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return
    
    contents = await db.get_egg_contents(drop["id"])
    
    if not contents:
        await update.message.reply_text(
            "⚠️ *البيضة فارغة!*\n\nأبلغ المشرف.",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
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
    
    await update.message.reply_text(
        f"🥚 *جاري فتح البيضة...*\n\n"
        f"🎲 اللحظة الحاسمة...",
        parse_mode="Markdown", reply_markup=kb_main(admin)
    )
    
    await asyncio.sleep(1.5)
    
    prize_type = chosen["prize_type"]
    prize_value = chosen["prize_value"]
    
    await db.claim_egg_content(chosen["id"], user.id)
    await db.claim_drop(drop["token"], user.id, prize_value or "")
    await db.add_drop_winner(drop["id"], user.id, 1, prize_value or "")
    
    if prize_type == "points":
        amount = int(prize_value) if prize_value else 0
        await db.add_points(user.id, amount, "egg_prize", drop["id"])
        await db.update_vip_tier(user.id)
        await update.message.reply_text(
            f"🎉 *مبروك!*\n\n"
            f"💰 فزت بـ `{amount}` نقطة!\n\n"
            f"💎 رصيدك الآن: `{(await db.get_user(user.id))['points']}`",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
    
    elif prize_type == "subscription":
        try:
            plan, days = prize_value.split(":")
            days = int(days)
        except Exception:
            await update.message.reply_text("⚠️ جائزة غير صالحة",
                                              reply_markup=kb_main(admin))
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
                    f"{info['emoji']} *{info['name']}*\n"
                    f"📅 {days} يوم\n"
                    f"🔑 *كودك:* `{code}`\n\n"
                    f"📖 فعّله في: {SITE_URL}",
                    parse_mode="Markdown", reply_markup=kb_main(admin),
                    disable_web_page_preview=True
                )
            else:
                await update.message.reply_text("⚠️ فشل إنشاء الكود",
                                                  reply_markup=kb_main(admin))
        else:
            await update.message.reply_text(
                f"⚠️ {result.get('message')}",
                reply_markup=kb_main(admin)
            )
    
    else:
        await update.message.reply_text(
            f"😔 *حظاً أوفر!*\n\n"
            f"البيضة كانت فارغة هذه المرة.\n"
            f"💡 جرّب مرة أخرى!",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
    
    await refresh_drop_immediately(context, drop["id"])

# ═══════════════════════════════════════════════════════════════════
# 🔒 دروب بشرط
# ═══════════════════════════════════════════════════════════════════

async def check_drop_conditions(user_id, conditions):
    user = await db.get_user(user_id)
    if not user:
        return False, "المستخدم غير موجود"
    
    results = []
    
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
    
    if conditions.get("min_points"):
        if user["points"] < conditions["min_points"]:
            results.append(f"❌ تحتاج {conditions['min_points']} نقطة (لديك: {user['points']})")
        else:
            results.append(f"✅ النقاط: {user['points']}/{conditions['min_points']}")
    
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
    
    has_failure = any(r.startswith("❌") for r in results)
    details = "\n".join(results) if results else "✅ لا شروط"
    return not has_failure, details

async def handle_conditional_open(update, context, drop):
    user = update.effective_user
    admin = is_admin(user.id)
    
    if not drop["is_active"] or drop.get("claimed_by"):
        await update.message.reply_text(
            "😔 *حظاً أوفر!*",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return
    
    try:
        conditions = json.loads(drop.get("conditions") or "{}")
        if not isinstance(conditions, dict):
            conditions = {}
    except Exception:
        conditions = {}
    
    passed, details = await check_drop_conditions(user.id, conditions)
    
    if not passed:
        await update.message.reply_text(
            f"🔒 *لا تستوفي الشروط*\n\n"
            f"📋 *تفاصيل:*\n{details}\n\n"
            f"💡 أكمل الشروط ثم حاول مجدداً.",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return
    
    drop_info = SUBSCRIPTION_TYPES.get(drop["plan"], {})
    api_plan = drop_info.get("api_plan", drop["plan"])
    
    await update.message.reply_text("🎁 جاري إنشاء كودك...", reply_markup=kb_main(admin))
    
    result = await api.create(api_plan, drop["days"], 1)
    if not result["ok"]:
        await update.message.reply_text(
            f"❌ فشل: {result.get('message')}",
            reply_markup=kb_main(admin)
        )
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
        f"{info['emoji']} {info['name']}\n"
        f"📅 {drop['days']} يوم\n"
        f"🔑 *كودك:* `{code}`\n\n"
        f"📖 فعّله في: {SITE_URL}",
        parse_mode="Markdown", reply_markup=kb_main(admin),
        disable_web_page_preview=True
    )

# ═══════════════════════════════════════════════════════════════════
# 🔗 دروب تسلسلي
# ═══════════════════════════════════════════════════════════════════

async def handle_chain_open(update, context, drop):
    user = update.effective_user
    admin = is_admin(user.id)
    
    if not drop["is_active"] or drop.get("claimed_by"):
        await update.message.reply_text(
            "😔 *حظاً أوفر!*",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return
    
    drop_info = SUBSCRIPTION_TYPES.get(drop["plan"], {})
    api_plan = drop_info.get("api_plan", drop["plan"])
    
    await update.message.reply_text("🎁 جاري إنشاء كودك...", reply_markup=kb_main(admin))
    
    result = await api.create(api_plan, drop["days"], 1)
    if not result["ok"]:
        await update.message.reply_text(
            f"❌ فشل: {result.get('message')}",
            reply_markup=kb_main(admin)
        )
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
    
    # فتح الدروب التالي
    next_drop_id = drop.get("next_drop_id")
    next_drop_token = None
    
    if next_drop_id:
        next_drop = await db.get_drop_by_id(next_drop_id)
        if next_drop and next_drop["is_active"]:
            next_drop_token = next_drop["token"]
            try:
                channels = await db.list_channels()
                for ch in channels:
                    sent = await context.bot.send_message(
                        chat_id=ch["chat_id"],
                        text=build_drop_card_text(next_drop),
                        reply_markup=build_drop_card_kb(next_drop, context.bot.username),
                        parse_mode="Markdown"
                    )
                    await db.save_drop_message(next_drop["id"], ch["chat_id"], sent.message_id)
            except Exception as e:
                logger.error(f"فشل نشر الدروب التالي: {e}")
    
    await refresh_drop_immediately(context, drop["id"])
    info = SUBSCRIPTION_TYPES.get(drop["plan"], {"emoji": "📦", "name": drop["plan"]})
    
    message = (
        f"🎉 *مبروك!*\n\n"
        f"{info['emoji']} {info['name']}\n"
        f"📅 {drop['days']} يوم\n"
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
    
    await update.message.reply_text(
        message,
        parse_mode="Markdown", reply_markup=kb_main(admin),
        disable_web_page_preview=True
    )

# ═══════════════════════════════════════════════════════════════════
# 🗳️ دروب بتصويت
# ═══════════════════════════════════════════════════════════════════

async def handle_vote_open(update, context, drop):
    user = update.effective_user
    admin = is_admin(user.id)
    
    if not drop["is_active"]:
        await update.message.reply_text(
            "😔 *التصويت انتهى*",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return
    
    if await db.has_voted(drop["id"], user.id):
        await update.message.reply_text(
            "✅ *لقد صوّت مسبقاً!*",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
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
        reply_markup=InlineKeyboardMarkup(kb_rows)
    )

async def cast_vote_callback(update, context):
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
# 🔨 دروب بمزاد
# ═══════════════════════════════════════════════════════════════════

async def handle_auction_open(update, context, drop):
    user = update.effective_user
    admin = is_admin(user.id)
    
    auction = await db.get_auction_by_drop(drop["id"])
    if not auction:
        await update.message.reply_text(
            "⚠️ المزاد غير موجود.",
            reply_markup=kb_main(admin)
        )
        return
    
    if auction["is_closed"]:
        winner = auction.get("current_bidder")
        await update.message.reply_text(
            f"🔨 *المزاد انتهى*\n\n"
            f"👤 الفائز: `{winner}`\n"
            f"💰 السعر: `{auction['current_bid']}` نقطة",
            parse_mode="Markdown", reply_markup=kb_main(admin)
        )
        return
    
    try:
        end_dt = datetime.fromisoformat(auction["ends_at"])
        remaining = end_dt - datetime.now()
        if remaining.total_seconds() <= 0:
            await update.message.reply_text(
                "⏰ *انتهى وقت المزاد*",
                parse_mode="Markdown", reply_markup=kb_main(admin)
            )
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
        parse_mode="Markdown", reply_markup=kb
    )

async def bid_callback(update, context):
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
        parse_mode="Markdown", reply_markup=kb_cancel()
    )

async def auction_bid_receive(update, context, text):
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
        await update.message.reply_text(
            "❌ المزاد مغلق.",
            reply_markup=kb_main(is_admin(update.effective_user.id))
        )
        context.user_data["state"] = "main"
        return
    
    min_bid = auction["current_bid"] + auction["min_increment"]
    if amount < min_bid:
        await update.message.reply_text(
            f"❌ *مزايدة منخفضة*\n\nالحد الأدنى: `{min_bid}` 💎",
            parse_mode="Markdown", reply_markup=kb_cancel()
        )
        return
    
    user = await db.get_user(update.effective_user.id)
    if not user or user["points"] < amount:
        await update.message.reply_text(
            f"❌ *نقاطك غير كافية*\n\nرصيدك: `{user['points'] if user else 0}` 💎",
            parse_mode="Markdown", reply_markup=kb_cancel()
        )
        return
    
    # استرداد مزايدة المستخدم نفسه
    if auction["current_bidder"] == update.effective_user.id and auction["current_bid"] > 0:
        await db.add_points(update.effective_user.id, auction["current_bid"], "auction_refund", drop_id)
    
    if not await db.deduct_points(update.effective_user.id, amount):
        await update.message.reply_text("❌ فشل الخصم.",
                                          reply_markup=kb_main(False))
        return
    
    await db.place_bid(auction["id"], update.effective_user.id, amount)
    
    await update.message.reply_text(
        f"✅ *تم تسجيل مزايدتك!*\n\n"
        f"💰 `{amount}` نقطة\n\n"
        f"⚠️ *تنبيه:* إذا زايدك شخص آخر، تُرجع نقاطك تلقائياً.",
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(update.effective_user.id))
    )
    
    context.user_data.pop("auction_bid_drop_id", None)
    context.user_data["state"] = "main"
    
    await refresh_drop_immediately(context, drop_id)

async def auto_close_auctions(context):
    """يُغلق المزادات المنتهية تلقائياً"""
    try:
        auctions = await db.get_active_auctions()
        now = datetime.now()
        
        for auction in auctions:
            try:
                end_dt = datetime.fromisoformat(auction["ends_at"])
                if now >= end_dt:
                    await db.close_auction(auction["id"])
                    
                    drop = await db.get_drop_by_id(auction["drop_id"])
                    if not drop:
                        continue
                    
                    winner_id = auction["current_bidder"]
                    if not winner_id:
                        logger.info(f"⚠️ مزاد #{drop['token']} انتهى بدون مزايدات")
                        await refresh_drop_immediately(context, drop["id"])
                        continue
                    
                    drop_info = SUBSCRIPTION_TYPES.get(drop["plan"], {})
                    api_plan = drop_info.get("api_plan", drop["plan"])
                    result = await api.create(api_plan, drop["days"], 1)
                    
                    if result["ok"]:
                        code = extract_code(result["data"])
                        if code:
                            await db.claim_drop(drop["token"], winner_id, code)
                            await db.save_subscription(winner_id, {
                                "code": code, "plan": drop["plan"], "actual_plan": api_plan,
                                "days": drop["days"], "max_uses": 1,
                                "points_spent": auction["current_bid"],
                                "response": result["data"], "source": "auction"
                            })
                            await db.add_drop_winner(drop["id"], winner_id, 1, code)
                            
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
# 💎 دروبات النقاط
# ═══════════════════════════════════════════════════════════════════

async def pdrop_create_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "pdrop_points"
    await update.message.reply_text(
        "💎 *دروب النقاط*\n\n"
        "أرسل عدد النقاط:\n\n"
        "❌ للإلغاء",
        parse_mode="Markdown", reply_markup=kb_cancel()
    )

async def pdrop_receive(update, context, text):
    try:
        points = int(text)
        if points < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ رقم صحيح ≥ 1:",
            reply_markup=kb_cancel()
        )
        return
    
    token = await db.create_points_drop(points, update.effective_user.id)
    link = f"https://t.me/{context.bot.username}?start=pdrop_{token}"
    
    await update.message.reply_text(
        f"✅ *أُنشئ!*\n\n"
        f"💰 {points} نقطة\n\n"
        f"🔗 `{link}`\n\n"
        f"📢 أول شخص يفوز!",
        parse_mode="Markdown", reply_markup=kb_pdrops(),
        disable_web_page_preview=True
    )
    context.user_data["state"] = "pdrops"

# ═══════════════════════════════════════════════════════════════════
# ⏰ الدروبات المجدولة
# ═══════════════════════════════════════════════════════════════════

async def check_scheduled_drops(context):
    """يفحص الدروبات المجدولة وينشر المستحق"""
    try:
        due = await db.get_due_scheduled_drops()
        for sched in due:
            try:
                token = await db.create_drop(
                    sched["plan"], sched["days"], sched["created_by"]
                )
                drop = await db.get_drop(token)
                
                channels = await db.list_channels()
                for ch in channels:
                    try:
                        sent = await context.bot.send_message(
                            chat_id=ch["chat_id"],
                            text=build_drop_card_text(drop),
                            reply_markup=build_drop_card_kb(drop, context.bot.username),
                            parse_mode="Markdown"
                        )
                        await db.save_drop_message(drop["id"], ch["chat_id"], sent.message_id)
                    except Exception as e:
                        logger.error(f"فشل نشر مجدول في {ch['title']}: {e}")
                
                next_run = (datetime.now() + timedelta(minutes=sched["interval_minutes"])).isoformat()
                await db.update_scheduled_next_run(sched["id"], next_run)
                
                logger.info(f"✅ دروب مجدول نُشر: #{token}")
            except Exception as e:
                logger.error(f"فشل دروب مجدول {sched['id']}: {e}")
    except Exception as e:
        logger.error(f"فشل فحص المجدولة: {e}")

# ═══════════════════════════════════════════════════════════════════
# 🔄 التحديث الدوري للبطاقات
# ═══════════════════════════════════════════════════════════════════

async def periodic_refresh(context):
    """تحديث البطاقات كل X ثانية"""
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
            logger.info(f"⏱️ تحديث دوري: {updated} بطاقة")
    except Exception as e:
        logger.error(f"فشل التحديث الدوري: {e}")

# ═══════════════════════════════════════════════════════════════════
# ⚠️ نهاية الجزء 5/8 — انتظر الجزء 6/8
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# 🎮 اللعبة 1: اختر صندوقك
# ═══════════════════════════════════════════════════════════════════

async def box_game_begin(update, context):
    user_id = update.effective_user.id
    if not await check_play_ready(update, user_id, "box"):
        return
    
    cost = GAME_COSTS["box"]
    await update.message.reply_text(
        f"📦 *اختر صندوقك*\n\n"
        f"🎁 3 صناديق — واحد فيه جائزة!\n"
        f"💰 التكلفة: `{cost}` نقطة\n"
        f"🏆 الجوائز: 20-100 نقطة\n\n"
        f"اختر صندوقاً:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 صندوق 1", callback_data="box_pick_1"),
             InlineKeyboardButton("📦 صندوق 2", callback_data="box_pick_2"),
             InlineKeyboardButton("📦 صندوق 3", callback_data="box_pick_3")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="box_cancel")],
        ])
    )

async def box_pick_callback(update, context):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query.data == "box_cancel":
        await query.message.delete()
        return
    
    try:
        choice = int(query.data.replace("box_pick_", ""))
    except ValueError:
        return
    
    ok, msg = can_play_game(user_id)
    if not ok:
        await query.answer(msg, show_alert=True)
        return
    
    user = await db.get_user(user_id)
    cost = GAME_COSTS["box"]
    if not user or user["points"] < cost:
        await query.answer("❌ نقاطك غير كافية", show_alert=True)
        return
    
    if not await db.deduct_points(user_id, cost):
        await query.answer("❌ فشل الخصم", show_alert=True)
        return
    
    register_play(user_id)
    
    winning_box = random.randint(1, 3)
    prize = 0
    
    if choice == winning_box:
        prize = random.choice([20, 30, 50, 75, 100])
        await db.add_points(user_id, prize, "box_win", None)
        await db.update_vip_tier(user_id)
        
        result_text = (
            f"🎉 *مبروك! فزت!*\n\n"
            f"📦 الصندوق الفائز: صندوق {winning_box}\n"
            f"✅ اخترت: صندوق {choice}\n\n"
            f"🎁 *الجائزة:* `{prize}` نقطة\n"
            f"💰 التكلفة: `{cost}` نقطة\n"
            f"📊 صافي الربح: `+{prize - cost}` نقطة"
        )
    else:
        result_text = (
            f"😔 *حظاً أوفر!*\n\n"
            f"📦 الصندوق الفائز: صندوق {winning_box}\n"
            f"❌ اخترت: صندوق {choice}\n\n"
            f"💰 خسرت: `{cost}` نقطة\n\n"
            f"💡 جرّب مرة أخرى!"
        )
    
    await log_game_play(user_id, "box", cost, prize, "win" if choice == winning_box else "lose")
    
    await query.message.edit_text(result_text, parse_mode="Markdown")
    
    boxes_display = []
    for i in range(1, 4):
        if i == winning_box:
            boxes_display.append(f"📦{i}: 🎁")
        elif i == choice:
            boxes_display.append(f"📦{i}: ❌")
        else:
            boxes_display.append(f"📦{i}: ⬜")
    
    await query.message.reply_text(
        " | ".join(boxes_display) + "\n\n"
        f"💎 رصيدك: `{(await db.get_user(user_id))['points']}`",
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(user_id))
    )

# ═══════════════════════════════════════════════════════════════════
# 🎲 اللعبة 2: زوجي/فردي
# ═══════════════════════════════════════════════════════════════════

async def oddeven_game_begin(update, context):
    user_id = update.effective_user.id
    if not await check_play_ready(update, user_id, "odd_even"):
        return
    
    cost = GAME_COSTS["odd_even"]
    await update.message.reply_text(
        f"🎲 *زوجي أو فردي*\n\n"
        f"🎯 الرهان: `{cost}` نقطة\n"
        f"🏆 الفوز: `{cost * 2}` نقطة (×2)\n\n"
        f"اختر:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 زوجي", callback_data="oe_even"),
             InlineKeyboardButton("🔴 فردي", callback_data="oe_odd")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="oe_cancel")],
        ])
    )

async def oddeven_callback(update, context):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query.data == "oe_cancel":
        await query.message.delete()
        return
    
    choice = "even" if query.data == "oe_even" else "odd"
    
    ok, msg = can_play_game(user_id)
    if not ok:
        await query.answer(msg, show_alert=True)
        return
    
    user = await db.get_user(user_id)
    cost = GAME_COSTS["odd_even"]
    if not user or user["points"] < cost:
        await query.answer("❌ نقاطك غير كافية", show_alert=True)
        return
    
    if not await db.deduct_points(user_id, cost):
        await query.answer("❌ فشل الخصم", show_alert=True)
        return
    
    register_play(user_id)
    
    dice = random.randint(1, 6)
    dice_parity = "even" if dice % 2 == 0 else "odd"
    dice_emoji = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"][dice - 1]
    prize = 0
    
    if choice == dice_parity:
        prize = cost * 2
        await db.add_points(user_id, prize, "oddeven_win", None)
        await db.update_vip_tier(user_id)
        result = (
            f"🎲 *النتيجة:* {dice_emoji} ({dice})\n\n"
            f"✅ *فزت!*\n\n"
            f"🎯 اخترت: {'زوجي' if choice == 'even' else 'فردي'}\n"
            f"📊 النتيجة: {dice} ({'زوجي' if dice_parity == 'even' else 'فردي'})\n\n"
            f"🏆 الجائزة: `{prize}` نقطة\n"
            f"💰 صافي الربح: `+{prize - cost}` نقطة"
        )
    else:
        result = (
            f"🎲 *النتيجة:* {dice_emoji} ({dice})\n\n"
            f"😔 *حظاً أوفر!*\n\n"
            f"🎯 اخترت: {'زوجي' if choice == 'even' else 'فردي'}\n"
            f"📊 النتيجة: {dice} ({'زوجي' if dice_parity == 'even' else 'فردي'})\n\n"
            f"❌ خسرت: `{cost}` نقطة"
        )
    
    await log_game_play(user_id, "odd_even", cost, prize, "win" if choice == dice_parity else "lose")
    
    await query.message.edit_text(result, parse_mode="Markdown")
    await query.message.reply_text(
        f"💎 رصيدك: `{(await db.get_user(user_id))['points']}`",
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(user_id))
    )

# ═══════════════════════════════════════════════════════════════════
# 🃏 اللعبة 3: البطاقات
# ═══════════════════════════════════════════════════════════════════

async def cards_game_begin(update, context):
    user_id = update.effective_user.id
    if not await check_play_ready(update, user_id, "cards"):
        return
    
    cost = GAME_COSTS["cards"]
    await update.message.reply_text(
        f"🃏 *البطاقات*\n\n"
        f"🎴 5 بطاقات — كل بطاقة بجائزة مختلفة\n"
        f"💰 التكلفة: `{cost}` نقطة\n\n"
        f"🎁 *الجوائز:*\n"
        f"• 💎 50 نقطة (10%)\n"
        f"• 💎 30 نقطة (20%)\n"
        f"• 💎 15 نقطة (30%)\n"
        f"• 😔 لا شيء (40%)\n\n"
        f"اختر بطاقة:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🃏 A", callback_data="card_pick_A"),
             InlineKeyboardButton("🃏 B", callback_data="card_pick_B"),
             InlineKeyboardButton("🃏 C", callback_data="card_pick_C")],
            [InlineKeyboardButton("🃏 D", callback_data="card_pick_D"),
             InlineKeyboardButton("🃏 E", callback_data="card_pick_E")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="card_cancel")],
        ])
    )

async def cards_callback(update, context):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query.data == "card_cancel":
        await query.message.delete()
        return
    
    card = query.data.replace("card_pick_", "")
    
    ok, msg = can_play_game(user_id)
    if not ok:
        await query.answer(msg, show_alert=True)
        return
    
    user = await db.get_user(user_id)
    cost = GAME_COSTS["cards"]
    if not user or user["points"] < cost:
        await query.answer("❌ نقاطك غير كافية", show_alert=True)
        return
    
    if not await db.deduct_points(user_id, cost):
        await query.answer("❌ فشل الخصم", show_alert=True)
        return
    
    register_play(user_id)
    
    # احتمالات
    rand = random.random()
    if rand < 0.10:
        prize = 50
    elif rand < 0.30:
        prize = 30
    elif rand < 0.60:
        prize = 15
    else:
        prize = 0
    
    if prize > 0:
        await db.add_points(user_id, prize, "card_win", None)
        await db.update_vip_tier(user_id)
        result = (
            f"🃏 *البطاقة: {card}*\n\n"
            f"🎉 *مبروك!*\n\n"
            f"🎁 *الجائزة:* `{prize}` نقطة\n"
            f"💰 التكلفة: `{cost}` نقطة\n"
            f"📊 صافي الربح: `{'+' if prize > cost else ''}{prize - cost}` نقطة"
        )
    else:
        result = (
            f"🃏 *البطاقة: {card}*\n\n"
            f"😔 *حظاً أوفر!*\n\n"
            f"البطاقة كانت فارغة.\n"
            f"❌ خسرت: `{cost}` نقطة"
        )
    
    await log_game_play(user_id, "cards", cost, prize, "win" if prize > 0 else "lose")
    
    await query.message.edit_text(result, parse_mode="Markdown")
    await query.message.reply_text(
        f"💎 رصيدك: `{(await db.get_user(user_id))['points']}`",
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(user_id))
    )

# ═══════════════════════════════════════════════════════════════════
# 🎭 اللعبة 4: السوق السوداء
# ═══════════════════════════════════════════════════════════════════

async def black_market_begin(update, context):
    user_id = update.effective_user.id
    if not await check_play_ready(update, user_id, "black_market"):
        return
    
    cost = GAME_COSTS["black_market"]
    await update.message.reply_text(
        f"🎭 *السوق السوداء*\n\n"
        f"📦 كود مجهول بخصم كبير!\n"
        f"💰 السعر: `{cost}` نقطة\n\n"
        f"🎲 *قد تحصل على:*\n"
        f"• ⭐ بلس 7ي (50%)\n"
        f"• 💎 برو 7ي (30%)\n"
        f"• 💎 برو 30ي (15%)\n"
        f"• 👑 بريميوم 30ي (5%)\n\n"
        f"⚠️ *لا استرجاع!*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 اشترِ الآن", callback_data="bm_buy")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="bm_cancel")],
        ])
    )

async def black_market_callback(update, context):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query.data == "bm_cancel":
        await query.message.delete()
        return
    
    ok, msg = can_play_game(user_id)
    if not ok:
        await query.answer(msg, show_alert=True)
        return
    
    user = await db.get_user(user_id)
    cost = GAME_COSTS["black_market"]
    if not user or user["points"] < cost:
        await query.answer("❌ نقاطك غير كافية", show_alert=True)
        return
    
    if not await db.deduct_points(user_id, cost):
        await query.answer("❌ فشل الخصم", show_alert=True)
        return
    
    register_play(user_id)
    
    # اختيار عشوائي
    rand = random.random()
    if rand < 0.50:
        plan, days = "plus", 7
    elif rand < 0.80:
        plan, days = "pro", 7
    elif rand < 0.95:
        plan, days = "pro", 30
    else:
        plan, days = "premium", 30
    
    info = SUBSCRIPTION_TYPES[plan]
    api_plan = info["api_plan"]
    
    result = await api.create(api_plan, days, 1)
    if not result["ok"]:
        await db.add_points(user_id, cost, "black_market_refund", None)
        await query.answer("⚠️ فشل الإنشاء - استرجاع النقاط", show_alert=True)
        return
    
    code = extract_code(result["data"])
    if not code:
        await db.add_points(user_id, cost, "black_market_refund", None)
        await query.answer("⚠️ فشل الإنشاء - استرجاع النقاط", show_alert=True)
        return
    
    await db.save_subscription(user_id, {
        "code": code, "plan": plan, "actual_plan": api_plan,
        "days": days, "max_uses": 1, "points_spent": cost,
        "response": result["data"], "source": "black_market"
    })
    
    original_price = info["prices"][days]
    savings = original_price - cost
    
    await log_game_play(user_id, "black_market", cost, original_price, "win")
    
    await query.message.edit_text(
        f"🎭 *السوق السوداء*\n\n"
        f"🎉 *مبروك!*\n\n"
        f"{info['emoji']} *{info['name']}*\n"
        f"📅 {days} يوم\n"
        f"🔑 *كودك:* `{code}`\n\n"
        f"💰 سعرك: `{cost}` 💎\n"
        f"💵 السعر الأصلي: `{original_price}` 💎\n"
        f"📊 وفرت: `{savings}` 💎\n\n"
        f"📖 فعّله في: {SITE_URL}",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await query.message.reply_text(
        f"💎 رصيدك: `{(await db.get_user(user_id))['points']}`",
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(user_id))
    )

# ═══════════════════════════════════════════════════════════════════
# 🎡 اللعبة 5: عجلة الحظ
# ═══════════════════════════════════════════════════════════════════

async def wheel_begin(update, context):
    user_id = update.effective_user.id
    if not await check_play_ready(update, user_id, "wheel"):
        return
    
    cost = GAME_COSTS["wheel"]
    await update.message.reply_text(
        f"🎡 *عجلة الحظ*\n\n"
        f"💰 التكلفة: `{cost}` نقطة\n\n"
        f"🎁 *الجوائز:*\n"
        f"• 💎 100 نقطة (5%)\n"
        f"• 💎 50 نقطة (15%)\n"
        f"• 💎 30 نقطة (25%)\n"
        f"• 💎 20 نقطة (25%)\n"
        f"• 😔 لا شيء (30%)\n\n"
        f"🎰 أدر العجلة!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎡 أدر العجلة", callback_data="wheel_spin")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="wheel_cancel")],
        ])
    )

async def wheel_callback(update, context):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query.data == "wheel_cancel":
        await query.message.delete()
        return
    
    ok, msg = can_play_game(user_id)
    if not ok:
        await query.answer(msg, show_alert=True)
        return
    
    user = await db.get_user(user_id)
    cost = GAME_COSTS["wheel"]
    if not user or user["points"] < cost:
        await query.answer("❌ نقاطك غير كافية", show_alert=True)
        return
    
    if not await db.deduct_points(user_id, cost):
        await query.answer("❌ فشل الخصم", show_alert=True)
        return
    
    register_play(user_id)
    
    # animation
    wheel_frames = ["🎡 ⬅️", "🎡 ⬆️", "🎡 ➡️", "🎡 ⬇️"]
    spin_msg = await query.message.edit_text(
        f"🎡 *العجلة تدور...*\n\n{wheel_frames[0]}",
        parse_mode="Markdown"
    )
    
    for i in range(8):
        await asyncio.sleep(0.3)
        try:
            await spin_msg.edit_text(
                f"🎡 *العجلة تدور...*\n\n{wheel_frames[i % 4]}",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    
    # النتيجة
    rand = random.random()
    if rand < 0.05:
        prize = 100
    elif rand < 0.20:
        prize = 50
    elif rand < 0.45:
        prize = 30
    elif rand < 0.70:
        prize = 20
    else:
        prize = 0
    
    if prize > 0:
        await db.add_points(user_id, prize, "wheel_win", None)
        await db.update_vip_tier(user_id)
        result = (
            f"🎡 *النتيجة*\n\n"
            f"🎉 *مبروك!*\n\n"
            f"🎁 *الجائزة:* `{prize}` نقطة\n"
            f"💰 التكلفة: `{cost}` نقطة\n"
            f"📊 صافي الربح: `{'+' if prize > cost else ''}{prize - cost}` نقطة"
        )
    else:
        result = (
            f"🎡 *النتيجة*\n\n"
            f"😔 *حظاً أوفر!*\n\n"
            f"❌ خسرت: `{cost}` نقطة"
        )
    
    await log_game_play(user_id, "wheel", cost, prize, "win" if prize > 0 else "lose")
    
    try:
        await spin_msg.edit_text(result, parse_mode="Markdown")
    except Exception:
        await query.message.reply_text(result, parse_mode="Markdown")
    
    await query.message.reply_text(
        f"💎 رصيدك: `{(await db.get_user(user_id))['points']}`",
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(user_id))
    )

# ═══════════════════════════════════════════════════════════════════
# ⏱️ اللعبة 6: مطاردة الوقت
# ═══════════════════════════════════════════════════════════════════

async def time_chase_begin(update, context):
    user_id = update.effective_user.id
    if not await check_play_ready(update, user_id, "time_chase"):
        return
    
    cost = GAME_COSTS["time_chase"]
    await update.message.reply_text(
        f"⏱️ *مطاردة الوقت*\n\n"
        f"💰 التكلفة: `{cost}` نقطة\n\n"
        f"🎯 *كيف تلعب:*\n"
        f"• سترى رقماً يتناقص من 10\n"
        f"• يجب أن تضغط `أوقفه!` عندما يصل إلى 5 بالضبط\n"
        f"• دقة عالية = جائزة كبيرة\n\n"
        f"🎁 *الجوائز:*\n"
        f"• 5 بالضبط: 60 نقطة\n"
        f"• 4-6: 30 نقطة\n"
        f"• 3-7: 10 نقاط\n"
        f"• غير ذلك: لا شيء",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 ابدأ", callback_data="tc_start")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="tc_cancel")],
        ])
    )

async def time_chase_callback(update, context):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query.data == "tc_cancel":
        await query.message.delete()
        return
    
    if query.data == "tc_start":
        ok, msg = can_play_game(user_id)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        
        user = await db.get_user(user_id)
        cost = GAME_COSTS["time_chase"]
        if not user or user["points"] < cost:
            await query.answer("❌ نقاطك غير كافية", show_alert=True)
            return
        
        if not await db.deduct_points(user_id, cost):
            await query.answer("❌ فشل الخصم", show_alert=True)
            return
        
        register_play(user_id)
        
        # بدء العد
        context.user_data["tc_running"] = True
        context.user_data["tc_value"] = 10
        
        await query.message.edit_text(
            f"⏱️ *استعد...*\n\n"
            f"🔢 العداد: `10`\n\n"
            f"🎯 أوقفه عند 5!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 أوقفه!", callback_data="tc_stop")],
            ])
        )
        
        # عداد تنازلي في الخلفية (بدون تحديث الرسالة)
        for i in range(9, 0, -1):
            await asyncio.sleep(0.4)
            context.user_data["tc_value"] = i
            if not context.user_data.get("tc_running"):
                return  # تم الإيقاف
    
    elif query.data == "tc_stop":
        if not context.user_data.get("tc_running"):
            await query.answer("❌ لم تبدأ", show_alert=True)
            return
        
        context.user_data["tc_running"] = False
        stopped_at = context.user_data.get("tc_value", 0)
        
        cost = GAME_COSTS["time_chase"]
        
        if stopped_at == 5:
            prize = 60
        elif 4 <= stopped_at <= 6:
            prize = 30
        elif 3 <= stopped_at <= 7:
            prize = 10
        else:
            prize = 0
        
        if prize > 0:
            await db.add_points(user_id, prize, "time_chase_win", None)
            await db.update_vip_tier(user_id)
            result = (
                f"⏱️ *النتيجة*\n\n"
                f"🔢 أوقفت عند: `{stopped_at}`\n\n"
                f"🎉 *مبروك!*\n\n"
                f"🎁 *الجائزة:* `{prize}` نقطة\n"
                f"💰 التكلفة: `{cost}` نقطة"
            )
        else:
            result = (
                f"⏱️ *النتيجة*\n\n"
                f"🔢 أوقفت عند: `{stopped_at}`\n\n"
                f"😔 *حظاً أوفر!*\n"
                f"الهدف كان 5.\n\n"
                f"❌ خسرت: `{cost}` نقطة"
            )
        
        await log_game_play(user_id, "time_chase", cost, prize, "win" if prize > 0 else "lose")
        
        try:
            await query.message.edit_text(result, parse_mode="Markdown")
        except Exception:
            await query.message.reply_text(result, parse_mode="Markdown")
        
        await query.message.reply_text(
            f"💎 رصيدك: `{(await db.get_user(user_id))['points']}`",
            parse_mode="Markdown",
            reply_markup=kb_main(is_admin(user_id))
        )

# ═══════════════════════════════════════════════════════════════════
# 🗺️ اللعبة 7: الكنز المخفي
# ═══════════════════════════════════════════════════════════════════

async def treasure_begin(update, context):
    user_id = update.effective_user.id
    if not await check_play_ready(update, user_id, "treasure"):
        return
    
    cost = GAME_COSTS["treasure"]
    await update.message.reply_text(
        f"🗺️ *الكنز المخفي*\n\n"
        f"💰 التكلفة: `{cost}` نقطة\n\n"
        f"🎯 *اللعبة:*\n"
        f"• خريطة 3×3 (9 خانات)\n"
        f"• الكنز في مكان عشوائي\n"
        f"• اختر خانة للبحث\n\n"
        f"🎁 *الجوائز:*\n"
        f"• وجدت الكنز: 90 نقطة\n"
        f"• قريب جداً: 20 نقطة\n"
        f"• بعيد: لا شيء\n\n"
        f"اختر موقعاً:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔲 1", callback_data="tr_pick_1"),
             InlineKeyboardButton("🔲 2", callback_data="tr_pick_2"),
             InlineKeyboardButton("🔲 3", callback_data="tr_pick_3")],
            [InlineKeyboardButton("🔲 4", callback_data="tr_pick_4"),
             InlineKeyboardButton("🔲 5", callback_data="tr_pick_5"),
             InlineKeyboardButton("🔲 6", callback_data="tr_pick_6")],
            [InlineKeyboardButton("🔲 7", callback_data="tr_pick_7"),
             InlineKeyboardButton("🔲 8", callback_data="tr_pick_8"),
             InlineKeyboardButton("🔲 9", callback_data="tr_pick_9")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="tr_cancel")],
        ])
    )

async def treasure_callback(update, context):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query.data == "tr_cancel":
        await query.message.delete()
        return
    
    try:
        choice = int(query.data.replace("tr_pick_", ""))
    except ValueError:
        return
    
    ok, msg = can_play_game(user_id)
    if not ok:
        await query.answer(msg, show_alert=True)
        return
    
    user = await db.get_user(user_id)
    cost = GAME_COSTS["treasure"]
    if not user or user["points"] < cost:
        await query.answer("❌ نقاطك غير كافية", show_alert=True)
        return
    
    if not await db.deduct_points(user_id, cost):
        await query.answer("❌ فشل الخصم", show_alert=True)
        return
    
    register_play(user_id)
    
    # الكنز في مكان عشوائي
    treasure_pos = random.randint(1, 9)
    
    # حساب المسافة (شبكة 3×3)
    row_c = (choice - 1) // 3
    col_c = (choice - 1) % 3
    row_t = (treasure_pos - 1) // 3
    col_t = (treasure_pos - 1) % 3
    distance = abs(row_c - row_t) + abs(col_c - col_t)
    
    prize = 0
    hint = ""
    
    if choice == treasure_pos:
        prize = 90
        await db.add_points(user_id, prize, "treasure_win", None)
        await db.update_vip_tier(user_id)
        hint = "💰 وجدت الكنز!"
    elif distance == 1:
        prize = 20
        await db.add_points(user_id, prize, "treasure_near", None)
        await db.update_vip_tier(user_id)
        hint = "🔥 قريب جداً!"
    else:
        hint = "❄️ بعيد..."
    
    # عرض الخريطة
    grid_display = []
    for i in range(1, 10):
        if i == choice:
            if choice == treasure_pos:
                grid_display.append("💎")
            else:
                grid_display.append("❌")
        elif i == treasure_pos:
            grid_display.append("💎")
        else:
            grid_display.append("🔲")
    
    grid_rows = [
        " ".join(grid_display[0:3]),
        " ".join(grid_display[3:6]),
        " ".join(grid_display[6:9])
    ]
    
    if prize > 0:
        result = (
            f"🗺️ *الخريطة*\n\n" +
            "\n".join(grid_rows) + "\n\n" +
            f"{hint}\n\n"
            f"🎉 *مبروك!*\n\n"
            f"🎁 *الجائزة:* `{prize}` نقطة\n"
            f"💰 التكلفة: `{cost}` نقطة"
        )
    else:
        result = (
            f"🗺️ *الخريطة*\n\n" +
            "\n".join(grid_rows) + "\n\n" +
            f"{hint}\n\n"
            f"😔 *حظاً أوفر!*\n\n"
            f"❌ خسرت: `{cost}` نقطة"
        )
    
    await log_game_play(user_id, "treasure", cost, prize, "win" if prize > 0 else "lose")
    
    await query.message.edit_text(result, parse_mode="Markdown")
    await query.message.reply_text(
        f"💎 رصيدك: `{(await db.get_user(user_id))['points']}`",
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(user_id))
    )

# ═══════════════════════════════════════════════════════════════════
# 🤼 اللعبة 8: تحدي الأصدقاء (نرد)
# ═══════════════════════════════════════════════════════════════════

async def dice_duel_begin(update, context):
    user_id = update.effective_user.id
    if not await check_play_ready(update, user_id, "dice_duel"):
        return
    
    cost = GAME_COSTS["dice_duel"]
    await update.message.reply_text(
        f"🤼 *تحدي النرد*\n\n"
        f"🎲 تحدي ضد البوت!\n"
        f"💰 التكلفة: `{cost}` نقطة\n\n"
        f"🎯 *كيف تلعب:*\n"
        f"• سترمي نردك\n"
        f"• البوت يرمي نرده\n"
        f"• من يحصل على رقم أعلى يفوز\n"
        f"• تعادل = استرجاع\n\n"
        f"🏆 *الجائزة:* `{cost * 2}` نقطة",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 ارم النرد", callback_data="dd_roll")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="dd_cancel")],
        ])
    )

async def dice_duel_callback(update, context):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query.data == "dd_cancel":
        await query.message.delete()
        return
    
    ok, msg = can_play_game(user_id)
    if not ok:
        await query.answer(msg, show_alert=True)
        return
    
    user = await db.get_user(user_id)
    cost = GAME_COSTS["dice_duel"]
    if not user or user["points"] < cost:
        await query.answer("❌ نقاطك غير كافية", show_alert=True)
        return
    
    if not await db.deduct_points(user_id, cost):
        await query.answer("❌ فشل الخصم", show_alert=True)
        return
    
    register_play(user_id)
    
    # animation
    dice_frames = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    for i in range(6):
        await asyncio.sleep(0.2)
        try:
            await query.message.edit_text(
                f"🎲 *جاري الرمي...*\n\n"
                f"👤 أنت: {dice_frames[i % 6]}\n"
                f"🤖 البوت: {dice_frames[(i+3) % 6]}",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    
    # النتائج
    user_dice = random.randint(1, 6)
    bot_dice = random.randint(1, 6)
    
    user_emoji = dice_frames[user_dice - 1]
    bot_emoji = dice_frames[bot_dice - 1]
    
    prize = 0
    
    if user_dice > bot_dice:
        prize = cost * 2
        await db.add_points(user_id, prize, "dice_win", None)
        await db.update_vip_tier(user_id)
        result_text = (
            f"🎲 *النتيجة النهائية*\n\n"
            f"👤 أنت: {user_emoji} ({user_dice})\n"
            f"🤖 البوت: {bot_emoji} ({bot_dice})\n\n"
            f"🎉 *مبروك! فزت!*\n\n"
            f"🏆 *الجائزة:* `{prize}` نقطة\n"
            f"📊 صافي الربح: `+{prize - cost}` نقطة"
        )
    elif user_dice < bot_dice:
        result_text = (
            f"🎲 *النتيجة النهائية*\n\n"
            f"👤 أنت: {user_emoji} ({user_dice})\n"
            f"🤖 البوت: {bot_emoji} ({bot_dice})\n\n"
            f"😔 *حظاً أوفر!*\n\n"
            f"❌ خسرت: `{cost}` نقطة"
        )
    else:
        # تعادل - استرجاع
        await db.add_points(user_id, cost, "dice_tie", None)
        result_text = (
            f"🎲 *النتيجة النهائية*\n\n"
            f"👤 أنت: {user_emoji} ({user_dice})\n"
            f"🤖 البوت: {bot_emoji} ({bot_dice})\n\n"
            f"⚖️ *تعادل!*\n\n"
            f"✅ تم استرجاع `{cost}` نقطة"
        )
    
    await log_game_play(user_id, "dice_duel", cost, prize, "win" if user_dice > bot_dice else ("tie" if user_dice == bot_dice else "lose"))
    
    try:
        await query.message.edit_text(result_text, parse_mode="Markdown")
    except Exception:
        await query.message.reply_text(result_text, parse_mode="Markdown")
    
    await query.message.reply_text(
        f"💎 رصيدك: `{(await db.get_user(user_id))['points']}`",
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(user_id))
    )

# ═══════════════════════════════════════════════════════════════════
# ⚠️ نهاية الجزء 6/8 — انتظر الجزء 7/8
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# 🛡️ لوحة المشرف — Dashboard
# ═══════════════════════════════════════════════════════════════════

async def show_admin(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 للمشرفين فقط",
                                          reply_markup=kb_main(False))
        return
    context.user_data["state"] = "admin"
    await update.message.reply_text(
        "🛡️ *لوحة المشرف*\n\nاختر من الأزرار:",
        parse_mode="Markdown", reply_markup=kb_admin()
    )

async def show_dashboard(update, context):
    """لوحة التحكم المركزية"""
    if not is_admin(update.effective_user.id):
        return
    
    stats = await get_system_stats()
    
    # حالة النظام
    db_ok = "🟢"
    api_ok = "🟢"
    active_key = await db.get_active_key()
    if not active_key:
        api_ok = "🔴"
    else:
        ok, _ = await api.test_key(active_key["key_value"])
        api_ok = "🟢" if ok else "🔴"
    
    text = (
        f"📊 *لوحة التحكم*\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"👥 المستخدمون: `{stats['users']}`\n"
        f"📦 الاشتراكات: `{stats['subscriptions']}`\n"
        f"🔑 المفاتيح: `{stats['keys']}`\n"
        f"📢 القنوات: `{stats['channels']}`\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🎁 *الدروبات:*\n"
        f"  🟢 نشطة: `{stats['active_drops']}`\n"
        f"  🔴 مُستخدمة: `{stats['claimed_drops']}`\n"
        f"  📊 المجموع: `{stats['total_drops']}`\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"💎 *النقاط:*\n"
        f"  📈 كُسبت: `{stats['total_points_earned']}`\n"
        f"  📉 صُرفت: `{stats['total_points_spent']}`\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🎮 الألعاب: `{stats['total_games']}`\n"
        f"🛒 السوق: `{stats['active_listings']}` نشط\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"*حالة النظام:*\n"
        f"  {db_ok} قاعدة البيانات\n"
        f"  {api_ok} API"
    )
    
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=kb_admin()
    )

async def show_analytics(update, context):
    """التحليلات المتقدمة"""
    if not is_admin(update.effective_user.id):
        return
    
    stats = await get_system_stats()
    
    # أعلى المستخدمين
    top = await db.top_users(5)
    top_lines = []
    for i, u in enumerate(top, 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
        name = u.get("first_name") or "مستخدم"
        top_lines.append(f"{medal} {name} — {u['points']} 💎")
    
    # تحليل الدروبات
    async with aiosqlite.connect(DB_PATH) as db_conn:
        async with db_conn.execute("SELECT COUNT(*) FROM drops WHERE is_active=1") as cur:
            active_drops = (await cur.fetchone())[0]
        async with db_conn.execute("SELECT COUNT(*) FROM drops WHERE claimed_by IS NOT NULL") as cur:
            claimed = (await cur.fetchone())[0]
        async with db_conn.execute("SELECT SUM(price) FROM market_transactions") as cur:
            market_volume = (await cur.fetchone())[0] or 0
        async with db_conn.execute("SELECT SUM(fee) FROM market_transactions") as cur:
            market_fees = (await cur.fetchone())[0] or 0
    
    # نسبة التحويل
    total_drops = active_drops + claimed
    conversion = (claimed * 100 // total_drops) if total_drops > 0 else 0
    
    # أفضل القنوات
    channels = await get_channel_stats()
    channel_lines = []
    for ch in channels[:5]:
        name = ch.get("title") or ch.get("username") or "قناة"
        drops_count = ch.get("drops_count", 0)
        channel_lines.append(f"• {name}: {drops_count} دروب")
    
    text = (
        f"📈 *التحليلات المتقدمة*\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"👥 *المستخدمون:*\n"
        f"  📊 الإجمالي: `{stats['users']}`\n"
        f"  💎 متوسط النقاط: `{(stats['total_points_earned'] // max(1, stats['users']))}`\n\n"
        f"💰 *الإيرادات:*\n"
        f"  📉 نقاط مستهلكة: `{stats['total_points_spent']}`\n"
        f"  🛒 حجم السوق: `{market_volume}` نقطة\n"
        f"  💵 عمولات: `{market_fees}` نقطة\n\n"
        f"🎁 *الدروبات:*\n"
        f"  🟢 نشطة: `{active_drops}`\n"
        f"  🔴 مُستخدمة: `{claimed}`\n"
        f"  📊 معدل الاستخدام: `{conversion}%`\n\n"
        f"🏆 *أفضل 5:*\n" + "\n".join(top_lines) + "\n\n"
        f"📢 *أفضل القنوات:*\n" + ("\n".join(channel_lines) if channel_lines else "لا قنوات")
    )
    
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=kb_admin()
    )

async def show_monitoring(update, context):
    """المراقبة التلقائية"""
    if not is_admin(update.effective_user.id):
        return
    
    # فحوصات
    checks = []
    
    # 1. قاعدة البيانات
    try:
        await db.count_users()
        checks.append("✅ قاعدة البيانات: تعمل")
    except Exception as e:
        checks.append(f"❌ قاعدة البيانات: {e}")
    
    # 2. API
    active = await db.get_active_key()
    if active:
        ok, msg = await api.test_key(active["key_value"])
        checks.append(f"{'✅' if ok else '❌'} API: {msg}")
    else:
        checks.append("❌ لا مفتاح نشط")
    
    # 3. القنوات
    channels = await db.list_channels()
    active_channels = sum(1 for c in channels if c["is_active"])
    checks.append(f"✅ القنوات النشطة: {active_channels}/{len(channels)}")
    
    # 4. الدروبات العالقة
    async with aiosqlite.connect(DB_PATH) as db_conn:
        async with db_conn.execute(
            "SELECT COUNT(*) FROM drops WHERE is_active=1 AND retry_count >= 3"
        ) as cur:
            stuck_drops = (await cur.fetchone())[0]
    if stuck_drops > 0:
        checks.append(f"⚠️ دروبات عالقة: {stuck_drops}")
    else:
        checks.append("✅ لا دروبات عالقة")
    
    # 5. المزادات المفتوحة
    auctions = await db.get_active_auctions()
    now = datetime.now()
    overdue = 0
    for a in auctions:
        try:
            end_dt = datetime.fromisoformat(a["ends_at"])
            if now > end_dt:
                overdue += 1
        except Exception:
            pass
    
    if overdue > 0:
        checks.append(f"⚠️ مزادات متأخرة: {overdue}")
    else:
        checks.append(f"✅ المزادات: {len(auctions)} نشط")
    
    text = (
        f"🔍 *المراقبة*\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        + "\n".join(checks) +
        f"\n━━━━━━━━━━━━━━━━━\n"
        f"⏱️ آخر فحص: {datetime.now().strftime('%H:%M:%S')}"
    )
    
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=kb_admin()
    )

async def show_backup(update, context):
    """النسخ الاحتياطي"""
    if not is_admin(update.effective_user.id):
        return
    
    # إنشاء نسخة
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"bot_data_{timestamp}.db")
        
        shutil.copy2(DB_PATH, backup_path)
        file_size = os.path.getsize(backup_path) / 1024  # KB
        
        # حذف النسخ القديمة (نحتفظ بآخر 7)
        backups = sorted([
            f for f in os.listdir(BACKUP_DIR) if f.startswith("bot_data_")
        ], reverse=True)
        for old in backups[7:]:
            try:
                os.remove(os.path.join(BACKUP_DIR, old))
            except Exception:
                pass
        
        text = (
            f"💾 *النسخ الاحتياطي*\n\n"
            f"✅ *تم إنشاء نسخة!*\n\n"
            f"📁 الملف: `{os.path.basename(backup_path)}`\n"
            f"📊 الحجم: `{file_size:.1f} KB`\n"
            f"📅 التاريخ: `{datetime.now().strftime('%Y-%m-%d %H:%M')}`\n\n"
            f"💡 النسخ السابقة: {len(backups)} نسخة"
        )
        
        # إرسال الملف
        await update.message.reply_document(
            document=open(backup_path, "rb"),
            filename=os.path.basename(backup_path),
            caption=text,
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ *فشل النسخ*\n\n`{str(e)[:200]}`",
            parse_mode="Markdown", reply_markup=kb_admin()
        )

# ═══════════════════════════════════════════════════════════════════
# 📢 إدارة القنوات
# ═══════════════════════════════════════════════════════════════════

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
            lines.append(f"{status} *{name}*{primary}")
            lines.append(f"   🎁 {ch.get('total_drops', 0)} دروب")
    
    lines.append("\n💡 أضف البوت كأدمن في أي قناة/مجموعة")
    
    context.user_data["state"] = "channels"
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=kb_admin()
    )

# ═══════════════════════════════════════════════════════════════════
# 🎁 إدارة الدروبات — عرض
# ═══════════════════════════════════════════════════════════════════

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
            type_emoji = {"normal": "🎁", "egg": "🥚", "conditional": "🔒",
                          "chain": "🔗", "vote": "🗳️", "auction": "🔨"}.get(drop_type, "🎁")
            lines.append(f"{status} {type_emoji} #{d['token']} — {info['emoji']} {info['name']} — {d['days']}ي")
    
    lines.append("\n💡 اختر نوع الدروب من الأزرار")
    
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=kb_drops()
    )

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
    
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=kb_drops()
    )

async def show_pdrops(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "pdrops"
    await update.message.reply_text(
        "💎 *دروب النقاط*\n\nأنشئ رابطاً يفتح لأول شخص فقط.",
        parse_mode="Markdown", reply_markup=kb_pdrops()
    )

async def show_scheduled(update, context):
    """عرض الدروبات المجدولة"""
    if not is_admin(update.effective_user.id):
        return
    
    async with aiosqlite.connect(DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        async with db_conn.execute(
            "SELECT * FROM scheduled_drops ORDER BY id DESC LIMIT 10"
        ) as cur:
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
            lines.append(f"   كل {s['interval_minutes']} دقيقة")
            lines.append(f"   التالي: {next_run}")
    
    kb = ReplyKeyboardMarkup([
        [KeyboardButton(BTN_SCHEDULED_ADD)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)
    
    context.user_data["state"] = "scheduled"
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=kb
    )

# ═══════════════════════════════════════════════════════════════════
# 🎁 إنشاء الدروبات — كل الأنواع
# ═══════════════════════════════════════════════════════════════════

async def drop_create_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    
    channels = await db.list_channels()
    if not channels:
        await update.message.reply_text(
            "⚠️ *لا توجد قنوات*\n\n"
            "أضف البوت كأدمن في قناة/مجموعة أولاً.",
            parse_mode="Markdown", reply_markup=kb_drops()
        )
        return
    
    context.user_data["drop_type"] = "normal"
    context.user_data["state"] = "drop_choose_plan"
    
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    
    await update.message.reply_text(
        "🎁 *دروب عادي*\n\nاختر النوع:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True)
    )

async def egg_drop_create_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["drop_type"] = "egg"
    context.user_data["state"] = "drop_choose_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text(
        "🥚 *دروب بيضاوي*\n\nاختر نوع الباقة:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True)
    )

async def conditional_drop_create_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["drop_type"] = "conditional"
    context.user_data["state"] = "drop_choose_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text(
        "🔒 *دروب بشرط*\n\nاختر نوع الباقة:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True)
    )

async def chain_drop_create_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["drop_type"] = "chain"
    context.user_data["state"] = "drop_choose_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text(
        "🔗 *دروب تسلسلي*\n\nاختر نوع الباقة:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True)
    )

async def vote_drop_create_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["drop_type"] = "vote"
    context.user_data["state"] = "drop_choose_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text(
        "🗳️ *دروب بتصويت*\n\nاختر نوع الباقة:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True)
    )

async def auction_drop_create_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["drop_type"] = "auction"
    context.user_data["state"] = "drop_choose_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text(
        "🔨 *دروب بمزاد*\n\nاختر نوع الباقة:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True)
    )

async def drop_choose_type(update, context, text):
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
    
    await update.message.reply_text(
        f"{info['emoji']} {info['name']}\n\nاختر المدة:",
        reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True)
    )

async def drop_choose_days(update, context, text):
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
            parse_mode="Markdown", reply_markup=kb_cancel()
        )
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
            parse_mode="Markdown", reply_markup=kb_cancel()
        )
    elif drop_type == "chain":
        context.user_data["state"] = "chain_setup_next"
        await update.message.reply_text(
            f"🔗 *إعداد السلسلة*\n\n"
            f"📦 {SUBSCRIPTION_TYPES[plan]['name']} — {days}ي\n\n"
            f"كم عدد الدروبات في السلسلة؟\n\n"
            f"أرسل رقماً (1-10):\n\n"
            f"💡 كل دروب يفتح التالي عند استخدامه",
            parse_mode="Markdown", reply_markup=kb_cancel()
        )
    elif drop_type == "vote":
        context.user_data["state"] = "vote_setup"
        await update.message.reply_text(
            f"🗳️ *إعداد التصويت*\n\n"
            f"📦 {SUBSCRIPTION_TYPES[plan]['name']} — {days}ي\n\n"
            f"أرسل خيارات التصويت (كل سطر خيار):\n\n"
            f"*مثال:*\n"
            f"`plus:30:بلس 30 يوم`\n"
            f"`pro:30:برو 30 يوم`\n\n"
            f"*الصيغة:* `plan:days:name`",
            parse_mode="Markdown", reply_markup=kb_cancel()
        )
    elif drop_type == "auction":
        context.user_data["state"] = "auction_setup"
        await update.message.reply_text(
            f"🔨 *إعداد المزاد*\n\n"
            f"📦 {SUBSCRIPTION_TYPES[plan]['name']} — {days}ي\n\n"
            f"أرسل بيانات المزاد:\n\n"
            f"*الصيغة:*\n"
            f"`start_price:min_increment:duration_minutes`\n\n"
            f"*مثال:*\n"
            f"`10:5:60`",
            parse_mode="Markdown", reply_markup=kb_cancel()
        )

async def create_normal_drop(update, context, plan, days):
    user_id = update.effective_user.id
    token = await db.create_drop(plan, days, user_id, drop_type="normal")
    drop = await db.get_drop(token)
    
    channels = await db.list_channels()
    published = 0
    failed = 0
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(drop),
                reply_markup=build_drop_card_kb(drop, context.bot.username),
                parse_mode="Markdown"
            )
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
        disable_web_page_preview=True
    )
    
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_type", None)

async def receive_egg_setup(update, context, text):
    plan = context.user_data.get("drop_plan")
    days = context.user_data.get("drop_days")
    if not plan or not days:
        await show_admin(update, context)
        return
    
    lines = text.strip().split("\n")
    contents = []
    total_prob = 0
    
    for line in lines:
        parts = line.strip().split(":")
        if len(parts) < 3:
            continue
        try:
            if parts[0] == "subscription":
                prize_type = "subscription"
                prize_value = f"{parts[1]}:{parts[2]}"
                prob = float(parts[3])
            elif parts[0] == "none":
                prize_type = "none"
                prize_value = ""
                prob = float(parts[1])
            else:
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
            parse_mode="Markdown", reply_markup=kb_cancel()
        )
        return
    
    user_id = update.effective_user.id
    token = await db.create_drop(plan, days, user_id, drop_type="egg")
    drop = await db.get_drop(token)
    
    for prize_type, prize_value, prob in contents:
        await db.add_egg_content(drop["id"], prize_type, prize_value, prob)
    
    channels = await db.list_channels()
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(drop),
                reply_markup=build_drop_card_kb(drop, context.bot.username),
                parse_mode="Markdown"
            )
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
        disable_web_page_preview=True
    )
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_days", None)
    context.user_data.pop("drop_type", None)

async def receive_conditional_setup(update, context, text):
    plan = context.user_data.get("drop_plan")
    days = context.user_data.get("drop_days")
    if not plan or not days:
        await show_admin(update, context)
        return
    
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
        await update.message.reply_text(
            "❌ لا شروط صالحة. أرسل مجدداً:",
            reply_markup=kb_cancel()
        )
        return
    
    user_id = update.effective_user.id
    token = await db.create_drop(plan, days, user_id, drop_type="conditional",
                                   conditions=conditions)
    drop = await db.get_drop(token)
    
    channels = await db.list_channels()
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(drop),
                reply_markup=build_drop_card_kb(drop, context.bot.username),
                parse_mode="Markdown"
            )
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
        disable_web_page_preview=True
    )
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_days", None)
    context.user_data.pop("drop_type", None)

async def receive_chain_setup(update, context, text):
    try:
        count = int(text)
        if count < 1 or count > 10:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ رقم بين 1 و 10:",
            reply_markup=kb_cancel()
        )
        return
    
    plan = context.user_data.get("drop_plan")
    days = context.user_data.get("drop_days")
    if not plan or not days:
        await show_admin(update, context)
        return
    
    user_id = update.effective_user.id
    tokens = []
    prev_id = None
    
    for i in range(count):
        token = await db.create_drop(plan, days, user_id, drop_type="chain")
        drop = await db.get_drop(token)
        tokens.append(token)
        
        if prev_id:
            async with aiosqlite.connect(DB_PATH) as db_conn:
                await db_conn.execute("UPDATE drops SET next_drop_id=? WHERE id=?",
                                       (drop["id"], prev_id))
                await db_conn.execute("UPDATE drops SET parent_drop_id=? WHERE id=?",
                                       (prev_id, drop["id"]))
                await db_conn.commit()
        
        prev_id = drop["id"]
    
    first_token = tokens[0]
    first_drop = await db.get_drop(first_token)
    channels = await db.list_channels()
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(first_drop),
                reply_markup=build_drop_card_kb(first_drop, context.bot.username),
                parse_mode="Markdown"
            )
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
        disable_web_page_preview=True
    )
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_days", None)
    context.user_data.pop("drop_type", None)

async def receive_vote_setup(update, context, text):
    plan = context.user_data.get("drop_plan")
    days = context.user_data.get("drop_days")
    if not plan or not days:
        await show_admin(update, context)
        return
    
    options = []
    for line in text.strip().split("\n"):
        parts = line.strip().split(":")
        if len(parts) == 3:
            try:
                options.append((parts[0], int(parts[1]), parts[2]))
            except ValueError:
                pass
    
    if not options:
        await update.message.reply_text(
            "❌ لا خيارات صالحة.",
            reply_markup=kb_cancel()
        )
        return
    
    user_id = update.effective_user.id
    token = await db.create_drop(plan, days, user_id, drop_type="vote")
    drop = await db.get_drop(token)
    
    for opt_plan, opt_days, opt_name in options:
        await db.create_vote_option(drop["id"], f"{opt_plan}:{opt_days}", opt_name)
    
    channels = await db.list_channels()
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(drop),
                reply_markup=build_drop_card_kb(drop, context.bot.username),
                parse_mode="Markdown"
            )
            await db.save_drop_message(drop["id"], ch["chat_id"], sent.message_id)
        except Exception:
            pass
    
    await update.message.reply_text(
        f"✅ *تم إنشاء التصويت!*\n\n"
        f"🗳️ {len(options)} خيارات\n\n"
        f"🔗 `https://t.me/{context.bot.username}?start=drop_{token}`",
        parse_mode="Markdown", reply_markup=kb_drops(),
        disable_web_page_preview=True
    )
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_days", None)
    context.user_data.pop("drop_type", None)

async def receive_auction_setup(update, context, text):
    try:
        parts = text.strip().split(":")
        start_price = int(parts[0])
        min_increment = int(parts[1])
        duration_min = int(parts[2])
    except Exception:
        await update.message.reply_text(
            "❌ صيغة خاطئة. جرب: `10:5:60`",
            parse_mode="Markdown", reply_markup=kb_cancel()
        )
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
    
    drop["_auction"] = await db.get_auction_by_drop(drop["id"])
    channels = await db.list_channels()
    for ch in channels:
        try:
            sent = await context.bot.send_message(
                chat_id=ch["chat_id"],
                text=build_drop_card_text(drop),
                reply_markup=build_drop_card_kb(drop, context.bot.username),
                parse_mode="Markdown"
            )
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
        disable_web_page_preview=True
    )
    context.user_data["state"] = "drops"
    context.user_data.pop("drop_plan", None)
    context.user_data.pop("drop_days", None)
    context.user_data.pop("drop_type", None)

# ═══════════════════════════════════════════════════════════════════
# ⏰ إضافة دروب مجدول
# ═══════════════════════════════════════════════════════════════════

async def scheduled_create_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "sched_plan"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text(
        "⏰ *دروب مجدول*\n\nاختر نوع الباقة:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True)
    )

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
    
    await update.message.reply_text(
        "اختر المدة:",
        reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True)
    )

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
        parse_mode="Markdown", reply_markup=kb_cancel()
    )

async def sched_receive_interval(update, context, text):
    try:
        interval = int(text)
        if interval < 5:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ رقم ≥ 5 دقائق:",
            reply_markup=kb_cancel()
        )
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
        parse_mode="Markdown", reply_markup=kb_admin()
    )
    
    context.user_data["state"] = "admin"
    context.user_data.pop("sched_plan", None)
    context.user_data.pop("sched_days", None)

# ═══════════════════════════════════════════════════════════════════
# 📊 إحصائيات + سجل + بث
# ═══════════════════════════════════════════════════════════════════

async def show_stats(update, context):
    if not is_admin(update.effective_user.id):
        return
    
    stats = await get_system_stats()
    
    txt = (
        f"📊 *إحصائيات شاملة*\n\n"
        f"👥 المستخدمون: `{stats['users']}`\n"
        f"📦 الاشتراكات: `{stats['subscriptions']}`\n"
        f"🔑 المفاتيح: `{stats['keys']}`\n"
        f"📢 القنوات: `{stats['channels']}`\n"
        f"💎 النقاط المستهلكة: `{stats['total_points_spent']}`\n\n"
        f"🎁 *الدروبات:*\n"
        f"  🟢 نشطة: `{stats['active_drops']}`\n"
        f"  🔴 مُستخدمة: `{stats['claimed_drops']}`\n"
        f"  📊 المجموع: `{stats['total_drops']}`"
    )
    
    await update.message.reply_text(
        txt, parse_mode="Markdown", reply_markup=kb_admin()
    )

async def show_logs(update, context):
    if not is_admin(update.effective_user.id):
        return
    
    logs = await db.recent_logs(15)
    lines = ["📜 *السجل:*\n"]
    for l in logs:
        lines.append(f"`{l['created_at'][11:19]}` {l['action']}")
    
    await update.message.reply_text(
        "\n".join(lines) or "لا سجلات",
        parse_mode="Markdown", reply_markup=kb_admin()
    )

async def show_broadcast_begin(update, context):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "broadcast_message"
    await update.message.reply_text(
        "📢 *البث الجماعي*\n\n"
        "أرسل الرسالة التي تريد إرسالها لكل المستخدمين:\n\n"
        "❌ للإلغاء",
        parse_mode="Markdown", reply_markup=kb_cancel()
    )

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
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    
    await wait_msg.edit_text(
        f"✅ *اكتمل البث*\n\n"
        f"✅ نجح: `{sent}`\n"
        f"❌ فشل: `{failed}`\n"
        f"📊 المجموع: `{len(user_ids)}`",
        parse_mode="Markdown"
    )
    context.user_data["state"] = "admin"

# ═══════════════════════════════════════════════════════════════════
# ⚠️ نهاية الجزء 7/8 — انتظر الجزء 8/8 (الأخير)
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# 🎯 الراوتر الرئيسي (text_router)
# ═══════════════════════════════════════════════════════════════════

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    user_id = update.effective_user.id
    admin = is_admin(user_id)
    state = context.user_data.get("state", "main")

    # 🆕 حماية: تأكد من وجود المستخدم
    try:
        user = await db.get_user(user_id)
        if not user:
            await db.register_user(
                user_id,
                update.effective_user.username or "",
                update.effective_user.first_name or ""
            )
            logger.info(f"🆕 سجل تلقائياً: {user_id}")
    except Exception as e:
        logger.error(f"فشل التسجيل: {e}")

    try:
        # ═══ حالات المحادثات (أولوية عالية) ═══

        # فحص الكود
        if state == "check_code":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context)
                return
            await check_code_receive(update, context, text)
            return

        # التحويل
        if state == "transfer_id":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context)
                return
            await transfer_get_id(update, context, text)
            return

        if state == "transfer_amount":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context)
                return
            await transfer_get_amount(update, context, text)
            return

        if state == "transfer_confirm":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context)
                return
            await transfer_do_confirm(update, context, text)
            return

        # إضافة مفتاح
        if state == "key_add_value":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await key_add_value(update, context, text)
            return

        if state == "key_add_label":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await key_add_label(update, context, text)
            return

        # السوق - بيع
        if state == "market_sell_price":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context)
                return
            await market_sell_receive_price(update, context, text)
            return

        # المزاد
        if state == "auction_bid_amount":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context)
                return
            await auction_bid_receive(update, context, text)
            return

        # البث
        if state == "broadcast_message":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await broadcast_send(update, context, text)
            return

        # دروب نقاط
        if state == "pdrop_points":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await pdrop_receive(update, context, text)
            return

        # إنشاء دروب - اختيار النوع
        if state == "drop_choose_plan":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            if text.startswith("drop:"):
                await drop_choose_type(update, context, text)
                return
            return

        if state == "drop_choose_days":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await drop_choose_days(update, context, text)
            return

        # إعدادات الدروبات
        if state == "egg_setup":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await receive_egg_setup(update, context, text)
            return

        if state == "conditional_setup":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await receive_conditional_setup(update, context, text)
            return

        if state == "chain_setup_next":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await receive_chain_setup(update, context, text)
            return

        if state == "vote_setup":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await receive_vote_setup(update, context, text)
            return

        if state == "auction_setup":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await receive_auction_setup(update, context, text)
            return

        # المجدولة
        if state == "sched_plan":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            if text.startswith("drop:"):
                await sched_choose_plan(update, context, text)
                return
            return

        if state == "sched_days":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await sched_choose_days(update, context, text)
            return

        if state == "sched_interval":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context)
                return
            await sched_receive_interval(update, context, text)
            return

        # حاسبة النقاط
        if state == "calc_type":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context)
                return
            calc_type = None
            if text == BTN_PLUS:
                calc_type = "plus"
            elif text == BTN_PRO:
                calc_type = "pro"
            elif text == BTN_PREMIUM:
                calc_type = "premium"
            
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
                    reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True)
                )
                return
            await show_calculator(update, context)
            return

        if state == "calc_days":
            if text == BTN_CANCEL:
                context.user_data["state"] = "main"
                await show_home(update, context)
                return
            try:
                days = int(text.replace("يوم", "").replace("أيام", "").strip())
            except ValueError:
                return
            ctx = context.user_data.get("calc", {})
            sub_type = ctx.get("type")
            if not sub_type:
                await show_calculator(update, context)
                return
            info = SUBSCRIPTION_TYPES[sub_type]
            if days not in info["prices"]:
                return
            unit_price = info["prices"][days]
            user = await db.get_user(user_id)
            if not user:
                await update.message.reply_text("❌ أرسل /start أولاً",
                                                  reply_markup=kb_main(admin))
                return
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
                parse_mode="Markdown", reply_markup=kb_main(admin)
            )
            context.user_data["state"] = "main"
            return

        # شراء - عدد مخصص
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
                await update.message.reply_text(
                    "❌ رقم بين 1 و 100:",
                    reply_markup=kb_cancel()
                )
                return
            await buy_choose_qty(update, context, qty)
            return

        # تأكيد الشراء
        if state == "buy_confirm":
            if text == BTN_CONFIRM:
                await buy_confirm(update, context)
                return
            if text == BTN_EDIT_QTY:
                if context.user_data.get("buy", {}).get("type"):
                    context.user_data["state"] = "buy_qty"
                    await update.message.reply_text(
                        "🔢 اختر عدداً جديداً:",
                        reply_markup=kb_quantity()
                    )
                return
            if text == BTN_CANCEL:
                await show_home(update, context)
                return

        # شراء - عدد
        if state == "buy_qty":
            if text == BTN_QTY_1:
                await buy_choose_qty(update, context, 1)
                return
            if text == BTN_QTY_2:
                await buy_choose_qty(update, context, 2)
                return
            if text == BTN_QTY_3:
                await buy_choose_qty(update, context, 3)
                return
            if text == BTN_QTY_5:
                await buy_choose_qty(update, context, 5)
                return
            if text == BTN_QTY_10:
                await buy_choose_qty(update, context, 10)
                return
            if text == BTN_QTY_CUSTOM:
                context.user_data["state"] = "buy_custom_qty"
                await update.message.reply_text(
                    "✏️ أرسل عدد الأكواد (1-100):",
                    reply_markup=kb_cancel()
                )
                return

        # شراء - مدة
        if state == "buy_days":
            try:
                days = int(text.replace("يوم", "").replace("أيام", "").strip())
                await buy_choose_days(update, context, days)
                return
            except ValueError:
                pass

        # شراء - نوع
        if state in ("shop", "buy_days"):
            if text == BTN_PLUS:
                await buy_choose_type(update, context, "plus")
                return
            if text == BTN_PRO:
                await buy_choose_type(update, context, "pro")
                return
            if text == BTN_PREMIUM:
                await buy_choose_type(update, context, "premium")
                return

        # محفظة / اكسب
        if state in ("wallet", "earn"):
            if text == BTN_DAILY:
                await do_daily(update, context)
                return
            if text == BTN_INVITE:
                await show_invite(update, context)
                return
            if text == BTN_MY_ID:
                await show_my_id(update, context)
                return
            if text == BTN_TRANSFER:
                await transfer_begin(update, context)
                return

        # إعدادات
        if state == "settings":
            if text == BTN_LANG:
                await show_language(update, context)
                return
            if text == BTN_THEME:
                await show_theme(update, context)
                return
            if text == BTN_NOTIF:
                await show_notifications(update, context)
                return

        # إدارة
        if state == "admin" and admin:
            if text == BTN_DASHBOARD:
                await show_dashboard(update, context)
                return
            if text == BTN_ANALYTICS:
                await show_analytics(update, context)
                return
            if text == BTN_KEYS:
                await show_keys(update, context)
                return
            if text == BTN_CHANNELS:
                await show_channels(update, context)
                return
            if text == BTN_DROPS:
                await show_drops(update, context)
                return
            if text == BTN_PDROPS:
                await show_pdrops(update, context)
                return
            if text == BTN_STATS:
                await show_stats(update, context)
                return
            if text == BTN_LOGS:
                await show_logs(update, context)
                return
            if text == BTN_SCHEDULED:
                await show_scheduled(update, context)
                return
            if text == BTN_ALL_DROPS:
                await show_all_drops(update, context)
                return
            if text == BTN_MONITORING:
                await show_monitoring(update, context)
                return
            if text == BTN_BACKUP:
                await show_backup(update, context)
                return
            if text == BTN_BROADCAST:
                await show_broadcast_begin(update, context)
                return

        if state == "keys" and admin:
            if text == BTN_ADD_KEY:
                await key_add_begin(update, context)
                return

        if state == "drops" and admin:
            if text == BTN_CREATE_DROP:
                await drop_create_begin(update, context)
                return
            if text == BTN_DROP_EGG:
                await egg_drop_create_begin(update, context)
                return
            if text == BTN_DROP_COND:
                await conditional_drop_create_begin(update, context)
                return
            if text == BTN_DROP_CHAIN:
                await chain_drop_create_begin(update, context)
                return
            if text == BTN_DROP_VOTE:
                await vote_drop_create_begin(update, context)
                return
            if text == BTN_DROP_AUCTION:
                await auction_drop_create_begin(update, context)
                return
            if text == BTN_ALL_DROPS:
                await show_all_drops(update, context)
                return
            if text == BTN_SCHEDULED:
                await show_scheduled(update, context)
                return

        if state == "pdrops" and admin:
            if text == BTN_CREATE_PDROP:
                await pdrop_create_begin(update, context)
                return

        if state == "scheduled" and admin:
            if text == BTN_SCHEDULED_ADD:
                await scheduled_create_begin(update, context)
                return

        # الألعاب
        if text == BTN_GAME_BOX:
            await box_game_begin(update, context)
            return
        if text == BTN_GAME_ODD_EVEN:
            await oddeven_game_begin(update, context)
            return
        if text == BTN_GAME_CARDS:
            await cards_game_begin(update, context)
            return
        if text == BTN_GAME_BLACK:
            await black_market_begin(update, context)
            return
        if text == BTN_GAME_WHEEL:
            await wheel_begin(update, context)
            return
        if text == BTN_GAME_CHASE:
            await time_chase_begin(update, context)
            return
        if text == BTN_GAME_TREASURE:
            await treasure_begin(update, context)
            return
        if text == BTN_GAME_DICE_DUEL:
            await dice_duel_begin(update, context)
            return

        # ═══ الأزرار الرئيسية ═══
        if text == BTN_HOME:
            await show_home(update, context)
            return
        if text == BTN_SHOP:
            await show_shop(update, context)
            return
        if text == BTN_SUBS:
            await show_subs(update, context)
            return
        if text == BTN_WALLET:
            await show_wallet(update, context)
            return
        if text == BTN_EARN:
            await show_earn(update, context)
            return
        if text == BTN_MARKET:
            await show_market(update, context)
            return
        if text == BTN_GAMES:
            await show_games_menu(update, context)
            return
        if text == BTN_TOP:
            await show_top(update, context)
            return
        if text == BTN_GUIDE:
            await show_guide(update, context)
            return
        if text == BTN_CHECK:
            await check_code_begin(update, context)
            return
        if text == BTN_STATUS:
            await show_status(update, context)
            return
        if text == BTN_CALC:
            await show_calculator(update, context)
            return
        if text == BTN_ARCHIVE:
            await show_archive(update, context)
            return
        if text == BTN_BACKPACK:
            await show_backpack(update, context)
            return
        if text == BTN_ACHIEVEMENTS:
            await show_achievements(update, context)
            return
        if text == BTN_SETTINGS:
            await show_settings(update, context)
            return
        if text == BTN_ABOUT:
            await show_about(update, context)
            return
        if text == BTN_ADMIN:
            await show_admin(update, context)
            return

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
            elif state == "games":
                await show_games_menu(update, context)
            elif state in ("admin", "keys", "channels", "drops", "pdrops", "scheduled"):
                await show_admin(update, context)
            else:
                await show_home(update, context)
            return

        # افتراضي
        await update.message.reply_text(
            "🤔 استخدم الأزرار بالأسفل.",
            reply_markup=kb_main(admin)
        )

    except Exception as e:
        logger.exception(f"[TEXT] خطأ: {e}")
        try:
            await update.message.reply_text(
                f"❌ خطأ: `{str(e)[:150]}`",
                parse_mode="Markdown", reply_markup=kb_main(admin)
            )
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════════
# 🛡️ أوامر الأدمِن
# ═══════════════════════════════════════════════════════════════════

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_admin(update, context)

async def addchannel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إضافة قناة يدوياً — /addchannel @username أو -100xxx"""
    if not is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 *إضافة قناة*\n\n"
            "الاستخدام:\n"
            "`/addchannel @engtopwln`\n"
            "أو\n"
            "`/addchannel -1001234567890`\n\n"
            "⚠️ البوت يجب أن يكون أدمن في القناة",
            parse_mode="Markdown"
        )
        return
    
    arg = context.args[0]
    
    try:
        # تحويل إلى chat_id
        if arg.startswith("-100") or (arg.startswith("-") and arg[1:].isdigit()):
            chat_id = int(arg)
        else:
            # @username
            if not arg.startswith("@"):
                arg = "@" + arg
            chat_id = arg
        
        # جلب معلومات القناة
        chat = await context.bot.get_chat(chat_id)
        
        # تحقق أن البوت أدمن
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        
        if bot_member.status not in ("administrator", "creator"):
            await update.message.reply_text(
                f"❌ *البوت ليس أدمن!*\n\n"
                f"📢 {chat.title}\n\n"
                f"💡 أضف البوت كأدمن أولاً:\n"
                f"• Post Messages (نشر)\n"
                f"• Edit Messages (تعديل)",
                parse_mode="Markdown"
            )
            return
        
        # احفظ
        can_post = getattr(bot_member, "can_post_messages", False) or False
        can_edit = getattr(bot_member, "can_edit_messages", False) or False
        
        await db.add_channel(
            chat_id=chat.id,
            title=chat.title,
            username=chat.username,
            chat_type=chat.type,
            added_by=update.effective_user.id,
            can_post=1 if can_post else 0,
            can_edit=1 if can_edit else 0
        )
        
        await update.message.reply_text(
            f"✅ *تم إضافة القناة!*\n\n"
            f"📢 *{chat.title}*\n"
            f"🆔 `{chat.id}`\n"
            f"📝 نشر: {'✅' if can_post else '❌'}\n"
            f"✏️ تعديل: {'✅' if can_edit else '❌'}\n\n"
            f"🎁 يمكنك الآن نشر الدروبات فيها.",
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ قناة مضافة يدوياً: {chat.title} ({chat.id})")
    
    except Exception as e:
        await update.message.reply_text(
            f"❌ *فشل الإضافة*\n\n"
            f"`{str(e)[:200]}`\n\n"
            f"💡 تأكد من:\n"
            f"• البوت أدمن في القناة\n"
            f"• معرف القناة صحيح",
            parse_mode="Markdown"
        )
        
async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("`/ban <id>`", parse_mode="Markdown")
        return
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
        app.job_queue.run_repeating(
            periodic_refresh,
            interval=DROPS_REFRESH_INTERVAL,
            first=60
        )
        logger.info(f"⏱️ تحديث الدروبات كل {DROPS_REFRESH_INTERVAL // 60} دقيقة")
        
        app.job_queue.run_repeating(
            auto_close_auctions,
            interval=60,
            first=30
        )
        logger.info("🔨 فحص المزادات كل دقيقة")
        
        app.job_queue.run_repeating(
            check_scheduled_drops,
            interval=60,
            first=45
        )
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
    app.add_handler(CommandHandler("addchannel", addchannel_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    
    # Chat member
    app.add_handler(ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # Callbacks — الدروبات
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern="^verify_join$"))
    app.add_handler(CallbackQueryHandler(drop_status_callback, pattern="^drop_status_"))
    app.add_handler(CallbackQueryHandler(drop_refresh_callback, pattern="^drop_refresh_"))
    app.add_handler(CallbackQueryHandler(cast_vote_callback, pattern="^cast_vote_"))
    app.add_handler(CallbackQueryHandler(bid_callback, pattern="^bid_"))
    
    # Callbacks — الإعدادات
    app.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(theme_callback, pattern="^theme_"))
    app.add_handler(CallbackQueryHandler(notif_callback, pattern="^notif_"))
    app.add_handler(CallbackQueryHandler(settings_back_callback, pattern="^settings_back$"))
    
    # Callbacks — السوق
    app.add_handler(CallbackQueryHandler(market_browse_callback, pattern="^market_browse$"))
    app.add_handler(CallbackQueryHandler(market_view_callback, pattern="^market_view_"))
    app.add_handler(CallbackQueryHandler(market_buy_callback, pattern="^market_buy_"))
    app.add_handler(CallbackQueryHandler(market_sell_callback, pattern="^market_sell$"))
    app.add_handler(CallbackQueryHandler(market_sell_pick_callback, pattern="^market_sell_pick_"))
    app.add_handler(CallbackQueryHandler(market_mine_callback, pattern="^market_mine$"))
    app.add_handler(CallbackQueryHandler(market_cancel_callback, pattern="^market_cancel_"))
    app.add_handler(CallbackQueryHandler(market_back_callback, pattern="^market_back$"))
    
    # Callbacks — الألعاب
    app.add_handler(CallbackQueryHandler(box_pick_callback, pattern="^box_"))
    app.add_handler(CallbackQueryHandler(oddeven_callback, pattern="^oe_"))
    app.add_handler(CallbackQueryHandler(cards_callback, pattern="^card_"))
    app.add_handler(CallbackQueryHandler(black_market_callback, pattern="^bm_"))
    app.add_handler(CallbackQueryHandler(wheel_callback, pattern="^wheel_"))
    app.add_handler(CallbackQueryHandler(time_chase_callback, pattern="^tc_"))
    app.add_handler(CallbackQueryHandler(treasure_callback, pattern="^tr_"))
    app.add_handler(CallbackQueryHandler(dice_duel_callback, pattern="^dd_"))
    
    # Router
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    
    logger.info("🚀 بدء التشغيل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
