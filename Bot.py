# ═══════════════════════════════════════════════════════════════════
# 🤖 Worm GPT — Final Complete Edition
# 📦 pip install -r requirements.txt
# ═══════════════════════════════════════════════════════════════════

import os
import logging
import asyncio
import json
import secrets
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

import aiosqlite
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

# ═══════════════════════════════════════════════════════════════════
# ⚙️ الإعدادات
# ═══════════════════════════════════════════════════════════════════

BOT_TOKEN       = os.environ.get("BOT_TOKEN", "8860603341:AAHepgQUJh32nSz1aXlZotL9H182HeqNWmw")
SUPER_ADMIN_ID  = int(os.environ.get("SUPER_ADMIN_ID", "6207431030"))
API_URL         = os.environ.get("API_URL", "https://w0rmgpt.lovable.app/api/public/subscriptions")
SITE_URL        = os.environ.get("SITE_URL", "https://w0rmgpt.lovable.app/")

INITIAL_API_KEY       = os.environ.get("INITIAL_API_KEY", "wsk_0c4d9994396f4b27a464dfc1c43e244be0fb58c6")
INITIAL_API_KEY_LABEL = os.environ.get("INITIAL_API_KEY_LABEL", "المفتاح الأساسي")

POINTS_INVITE = int(os.environ.get("POINTS_INVITE", "1"))
POINTS_DAILY  = int(os.environ.get("POINTS_DAILY", "1"))
MIN_TRANSFER  = int(os.environ.get("MIN_TRANSFER", "1"))

if os.path.exists("/data"):
    DB_PATH = "/data/bot_data.db"
else:
    DB_PATH = os.environ.get("DB_PATH", "bot_data.db")

# ═══════════════════════════════════════════════════════════════════
# 💎 3 خطط
# ═══════════════════════════════════════════════════════════════════

SUBSCRIPTION_TYPES = {
    "plus": {
        "name": "⭐ بلس",
        "emoji": "⭐",
        "api_plan": "plus",
        "description": "اشتراك أساسي — مناسب للاستخدام الشخصي",
        "prices": {7: 5, 30: 15, 90: 40, 365: 120},
    },
    "pro": {
        "name": "💎 برو",
        "emoji": "💎",
        "api_plan": "pro",
        "description": "اشتراك متقدم — ميزات إضافية",
        "prices": {7: 8, 30: 25, 90: 65, 365: 200},
    },
    "premium": {
        "name": "👑 بريميوم",
        "emoji": "👑",
        "api_plan": "premium",
        "description": "اشتراك كامل — كل الميزات",
        "prices": {7: 15, 30: 45, 90: 120, 365: 380},
    },
}

QUANTITY_DISCOUNTS = {1: 0, 2: 5, 3: 10, 5: 15, 10: 20, 20: 25}

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
    thread = threading.Thread(target=run_http_server, daemon=True)
    thread.start()

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
                    invited_by INTEGER, invite_code TEXT UNIQUE,
                    last_daily_bonus TEXT, is_banned INTEGER DEFAULT 0, joined_at TEXT
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
                    points_spent INTEGER DEFAULT 0, api_response TEXT
                );
                CREATE TABLE IF NOT EXISTS drops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT UNIQUE NOT NULL,
                    plan TEXT NOT NULL, days INTEGER NOT NULL, created_by INTEGER,
                    created_at TEXT, claimed_by INTEGER, claimed_at TEXT,
                    claim_code TEXT, is_active INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS points_drops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT UNIQUE NOT NULL,
                    points INTEGER NOT NULL, created_by INTEGER, created_at TEXT,
                    claimed_by INTEGER, claimed_at TEXT, is_active INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER,
                    action TEXT, details TEXT, created_at TEXT
                );
            """)
            await db.commit()

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
            await db.execute("UPDATE users SET points = points - ? WHERE user_id=?", (amount, user_id))
            await db.commit()
        return True

    async def claim_daily_bonus(self, user_id):
        user = await self.get_user(user_id)
        if not user:
            return False, "المستخدم غير موجود"
        last = user.get("last_daily_bonus")
        if last:
            last_dt = datetime.fromisoformat(last)
            diff = datetime.now() - last_dt
            if diff < timedelta(hours=24):
                remaining = timedelta(hours=24) - diff
                h = remaining.seconds // 3600
                m = (remaining.seconds % 3600) // 60
                return False, f"⏳ متبقٍ: {h}س {m}د"
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET last_daily_bonus=? WHERE user_id=?",
                             (datetime.now().isoformat(), user_id))
            await db.commit()
        await self.add_points(user_id, POINTS_DAILY, "daily_bonus")
        return True, f"✅ حصلت على {POINTS_DAILY} نقطة!"

    async def set_ban(self, user_id, banned):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET is_banned=? WHERE user_id=?", (banned, user_id))
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
            async with db.execute("SELECT user_id, username, first_name, points FROM users ORDER BY points DESC LIMIT ?",
                                   (limit,)) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_user_rank(self, user_id):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT points FROM users WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
                if not row:
                    return 0, 0
                pts = row[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE points > ?", (pts,)) as cur:
                rank = (await cur.fetchone())[0] + 1
            async with db.execute("SELECT COUNT(*) FROM users") as cur:
                total = (await cur.fetchone())[0]
            return rank, total

    async def transfer_points(self, from_user, to_user, amount):
        from_u = await self.get_user(from_user)
        to_u = await self.get_user(to_user)
        if not from_u or not to_u:
            return False, "أحد المستخدمين غير موجود"
        if from_user == to_user:
            return False, "لا يمكن التحويل لنفسك"
        if from_u["points"] < amount:
            return False, "نقاطك غير كافية"
        ok = await self.deduct_points(from_user, amount)
        if not ok:
            return False, "فشل الخصم"
        await self.add_points(to_user, amount, "transfer_in", from_user)
        return True, "✅ تم التحويل"

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

    async def get_key(self, key_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM api_keys WHERE id=?", (key_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

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

    async def save_subscription(self, user_id, data):
        async with aiosqlite.connect(self.path) as db:
            expires = (datetime.now() + timedelta(days=data["days"])).isoformat()
            await db.execute("""INSERT INTO subscriptions
                (user_id, code, plan, actual_plan, days, max_uses, status, created_at, expires_at, points_spent, api_response)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)""",
                (user_id, data.get("code", ""), data["plan"], data.get("actual_plan", data["plan"]),
                 data["days"], data.get("max_uses", 1),
                 datetime.now().isoformat(), expires, data.get("points_spent", 0),
                 json.dumps(data.get("response", {}), ensure_ascii=False)))
            await db.commit()

    async def get_user_subs(self, user_id, limit=20):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM subscriptions WHERE user_id=? ORDER BY id DESC LIMIT ?",
                                   (user_id, limit)) as cur:
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

    async def create_drop(self, plan, days, admin_id):
        token = secrets.token_urlsafe(10)[:12]
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO drops (token, plan, days, created_by, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, 1)""",
                (token, plan, days, admin_id, datetime.now().isoformat()))
            await db.commit()
        return token

    async def get_drop(self, token):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM drops WHERE token=?", (token,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def claim_drop(self, token, user_id, code):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""UPDATE drops SET claimed_by=?, claimed_at=?, claim_code=?, is_active=0
                WHERE token=? AND is_active=1 AND claimed_by IS NULL""",
                (user_id, datetime.now().isoformat(), code, token))
            await db.commit()

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
                return {"ok": False, "error": "unauthorized", "message": "🔴 المفتاح غير صالح (401)"}
            if code == 403:
                return {"ok": False, "error": "forbidden", "message": "🟡 محظور (403)"}
            if code == 429:
                return {"ok": False, "error": "rate_limit", "message": "⏳ تجاوزت الحد (429)"}
            if code == 400:
                return {"ok": False, "error": "bad_request", "message": f"❌ طلب خاطئ (400): {body}"}
            if code == 404:
                return {"ok": False, "error": "not_found", "message": f"❌ الكود غير موجود (404)"}
            return {"ok": False, "error": f"http_{code}", "message": f"❌ خطأ HTTP {code}: {body}"}
        except requests.exceptions.Timeout:
            if active:
                await db.record_key_result(active["id"], False)
            return {"ok": False, "error": "timeout", "message": "⏱️ انتهت المهلة"}
        except requests.exceptions.ConnectionError:
            if active:
                await db.record_key_result(active["id"], False)
            return {"ok": False, "error": "connection", "message": "🌐 تعذر الاتصال"}
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
            if r.status_code == 401: return False, "🔴 غير صالح (401)"
            if r.status_code in (200, 204): return True, "🟢 صالح"
            if r.status_code == 403: return False, "🟡 محظور (403)"
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

BTN_SHOP      = "🛒 المتجر"
BTN_SUBS      = "📦 اشتراكاتي"
BTN_WALLET    = "💎 محفظتي"
BTN_EARN      = "🎁 اكسب نقاط"
BTN_TOP       = "🏆 الصدارة"
BTN_GUIDE     = "📖 كيف أفعّل"
BTN_CHECK     = "🔍 فحص كود"
BTN_ABOUT     = "ℹ️ عن البوت"
BTN_ADMIN     = "🛡️ لوحة المشرف"
BTN_HOME      = "🏠 القائمة الرئيسية"
BTN_BACK      = "🔙 رجوع"

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
BTN_CANCEL    = "❌ إلغاء"

BTN_TRANSFER  = "💸 تحويل نقاط"
BTN_DAILY     = "🎁 المكافأة اليومية"
BTN_INVITE    = "🔗 دعوة أصدقاء"
BTN_MY_ID     = "🆔 معرفي"

BTN_KEYS      = "🔑 إدارة المفاتيح"
BTN_DROPS     = "🎁 دروب اشتراكات"
BTN_PDROPS    = "💎 دروب نقاط"
BTN_STATS     = "📊 إحصائيات"
BTN_LOGS      = "📜 السجل"
BTN_ADD_KEY   = "➕ إضافة مفتاح"
BTN_CREATE_DROP = "➕ إنشاء دروب"
BTN_CREATE_PDROP = "➕ دروب نقاط"

def is_admin(uid):
    return uid == SUPER_ADMIN_ID

# ═══════════════════════════════════════════════════════════════════
# ⌨️ لوحات المفاتيح
# ═══════════════════════════════════════════════════════════════════

def kb_main(admin=False):
    rows = [
        [KeyboardButton(BTN_SHOP), KeyboardButton(BTN_SUBS)],
        [KeyboardButton(BTN_WALLET), KeyboardButton(BTN_EARN)],
        [KeyboardButton(BTN_TOP), KeyboardButton(BTN_GUIDE)],
        [KeyboardButton(BTN_CHECK), KeyboardButton(BTN_ABOUT)],
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

def kb_admin():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_KEYS), KeyboardButton(BTN_DROPS)],
        [KeyboardButton(BTN_PDROPS), KeyboardButton(BTN_STATS)],
        [KeyboardButton(BTN_LOGS)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_keys():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_ADD_KEY)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_drops():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_CREATE_DROP)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_pdrops():
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_CREATE_PDROP)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ], resize_keyboard=True, is_persistent=True)

def kb_cancel():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_CANCEL)]], resize_keyboard=True)

# ═══════════════════════════════════════════════════════════════════
# 🚀 start + Drops
# ═══════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
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
        txt += "🎉 تم تسجيلك بنجاح!\n"
        if invited_by:
            txt += "🎁 حصل داعيك على نقطة!\n"
        txt += "\n"
    txt += "استخدم الأزرار بالأسفل:"
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb_main(admin))

async def handle_drop_entry(update, context, token):
    user = update.effective_user
    await db.register_user(user.id, user.username, user.first_name)
    admin = is_admin(user.id)
    drop = await db.get_drop(token)
    if not drop or not drop["is_active"] or drop["claimed_by"]:
        await update.message.reply_text("😔 *حظاً أوفر!* الكود مأخوذ مسبقاً.",
                                          parse_mode="Markdown", reply_markup=kb_main(admin))
        return
    drop_info = SUBSCRIPTION_TYPES.get(drop["plan"], {})
    api_plan = drop_info.get("api_plan", drop["plan"])
    await update.message.reply_text("🎁 جاري إنشاء كودك...", reply_markup=kb_main(admin))
    result = await api.create(api_plan, drop["days"], 1)
    if not result["ok"]:
        await update.message.reply_text(f"❌ فشل: {result.get('message', 'غير معروف')}",
                                          reply_markup=kb_main(admin))
        return
    code = extract_code(result["data"])
    if not code:
        await update.message.reply_text("⚠️ الكود مفقود، أبلغ المشرف.", reply_markup=kb_main(admin))
        return
    await db.claim_drop(token, user.id, code)
    await db.save_subscription(user.id, {"code": code, "plan": drop["plan"],
        "actual_plan": api_plan, "days": drop["days"],
        "max_uses": 1, "points_spent": 0, "response": result["data"]})
    info = SUBSCRIPTION_TYPES.get(drop["plan"], {"emoji": "📦", "name": drop["plan"]})
    await update.message.reply_text(
        f"🎉 *مبروك!*\n\n{info['emoji']} {info['name']}\n📅 {drop['days']} يوم\n🔑 `{code}`\n\n📖 {SITE_URL}",
        parse_mode="Markdown", reply_markup=kb_main(admin))

async def handle_points_drop_entry(update, context, token):
    user = update.effective_user
    await db.register_user(user.id, user.username, user.first_name)
    admin = is_admin(user.id)
    pd = await db.get_points_drop(token)
    if not pd or not pd["is_active"] or pd["claimed_by"]:
        await update.message.reply_text("😔 *حظاً أوفر!*", parse_mode="Markdown",
                                          reply_markup=kb_main(admin))
        return
    await db.claim_points_drop(token, user.id)
    await db.add_points(user.id, pd["points"], "points_drop_claim", pd["id"])
    await update.message.reply_text(f"🎉 *مبروك!* حصلت على {pd['points']} نقطة!",
                                      parse_mode="Markdown", reply_markup=kb_main(admin))

# ═══════════════════════════════════════════════════════════════════
# 🏠 القوائم
# ═══════════════════════════════════════════════════════════════════

async def show_home(update, context):
    admin = is_admin(update.effective_user.id)
    context.user_data["state"] = "main"
    await update.message.reply_text("🏠 *القائمة الرئيسية*", parse_mode="Markdown",
                                      reply_markup=kb_main(admin))

async def show_shop(update, context):
    user = await db.get_user(update.effective_user.id)
    context.user_data["state"] = "shop"
    context.user_data.pop("buy", None)
    await update.message.reply_text(
        f"🛒 *المتجر*\n\n💎 رصيدك: `{user['points']}`\n\n"
        f"📦 *الخطط المتاحة:*\n"
        f"⭐ بلس — من 5 نقاط\n"
        f"💎 برو — من 8 نقاط\n"
        f"👑 بريميوم — من 15 نقطة\n\n"
        f"اختر نوع الاشتراك:",
        parse_mode="Markdown", reply_markup=kb_shop())

async def show_subs(update, context):
    subs = await db.get_user_subs(update.effective_user.id)
    admin = is_admin(update.effective_user.id)
    if not subs:
        await update.message.reply_text("📭 لا يوجد اشتراكات بعد.",
                                          reply_markup=kb_main(admin)); return
    lines = ["📋 *اشتراكاتك:*\n"]
    for i, s in enumerate(subs[:15], 1):
        info = SUBSCRIPTION_TYPES.get(s["plan"], {"emoji": "📦", "name": s["plan"]})
        lines.append(f"{i}. {info['emoji']} {info['name']} — {s['days']}ي — {s['created_at'][:10]}")
    if len(subs) > 15:
        lines.append(f"\n... و {len(subs) - 15} أخرى")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown",
                                      reply_markup=kb_main(admin))

async def show_wallet(update, context):
    u = await db.get_user(update.effective_user.id)
    rank, total = await db.get_user_rank(update.effective_user.id)
    context.user_data["state"] = "wallet"
    await update.message.reply_text(
        f"💎 *محفظتي*\n\n💰 الرصيد: `{u['points']}`\n"
        f"🏆 الترتيب: `{rank}` من `{total}`\n📈 إجمالي: `{u['total_points_earned']}`",
        parse_mode="Markdown", reply_markup=kb_wallet())

async def show_earn(update, context):
    context.user_data["state"] = "earn"
    await update.message.reply_text(
        "🎁 *كسب النقاط*\n\n"
        "1️⃣ المكافأة اليومية\n2️⃣ دعوة الأصدقاء\n"
        "3️⃣ استلام تحويلات\n4️⃣ دروب النقاط\n\nاختر:",
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
        marker = " ← *أنت*" if u["user_id"] == user_id else ""
        lines.append(f"{medal} *{name}* — {ref}\n   💎 {u['points']}{marker}")
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
        guide += "─────────────────\n⚠️ لا تملك كوداً بعد."
    guide += f"\n\n🌐 {SITE_URL}"
    await update.message.reply_text(guide, parse_mode="Markdown",
                                      reply_markup=kb_main(is_admin(update.effective_user.id)),
                                      disable_web_page_preview=True)

async def show_about(update, context):
    types = "\n".join([f"{i['emoji']} *{i['name']}* — {i['description']}"
                       for i in SUBSCRIPTION_TYPES.values()])
    await update.message.reply_text(
        f"🤖 *Worm GPT*\n\nبوت إدارة اشتراكات احترافي\n\n"
        f"📦 *الباقات:*\n{types}\n\n🌐 {SITE_URL}",
        parse_mode="Markdown",
        reply_markup=kb_main(is_admin(update.effective_user.id)),
        disable_web_page_preview=True)

# ═══════════════════════════════════════════════════════════════════
# 🔍 فحص كود اشتراك
# ═══════════════════════════════════════════════════════════════════

async def check_code_begin(update, context):
    context.user_data["state"] = "check_code"
    await update.message.reply_text(
        "🔍 *فحص كود اشتراك*\n\n"
        "أرسل الكود الذي تريد فحصه.\n\n"
        "💡 سيظهر:\n"
        "📦 *نوع الاشتراك* (بلس / برو / بريميوم)\n"
        "📅 *المدة* (7 / 30 / 90 / 365 يوم)\n"
        "🔢 *عدد الاستخدامات*\n"
        "📊 *الحالة* (نشط / مستخدم / منتهي)\n"
        "📆 *التواريخ*\n\n"
        "📌 يعمل مع أي كود — جديد، مستخدم، أو منتهي\n\n"
        "❌ للإلغاء",
        parse_mode="Markdown",
        reply_markup=kb_cancel()
    )

async def check_code_receive(update, context, code):
    code = code.strip()
    if len(code) < 3:
        await update.message.reply_text(
            "❌ الكود قصير جداً. أعد المحاولة:", reply_markup=kb_cancel())
        return

    admin = is_admin(update.effective_user.id)
    wait_msg = await update.message.reply_text("🔍 جاري الفحص...")

    result = await api.check_code(code)

    if not result["ok"]:
        error_msg = result.get("message", "غير معروف")
        try:
            await wait_msg.edit_text(
                f"❌ *فشل الفحص*\n\n"
                f"🔍 *السبب:* `{error_msg[:250]}`\n\n"
                f"💡 *تأكد من:*\n"
                f"• الكود صحيح\n"
                f"• الكود موجود\n"
                f"• المفتاح نشط",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        context.user_data["state"] = "main"
        await update.message.reply_text("استخدم الأزرار:", reply_markup=kb_main(admin))
        return

    data = result["data"]
    logger.info(f"[CHECK] code={code} response={str(data)[:400]}")
    info = data.get("data") if isinstance(data, dict) and "data" in data else data

    if not isinstance(info, dict):
        try:
            await wait_msg.edit_text(
                f"📋 *النتيجة:*\n```\n{str(data)[:500]}\n```",
                parse_mode="Markdown"
            )
        except Exception:
            await wait_msg.edit_text(f"📋 النتيجة:\n{str(data)[:500]}")
        context.user_data["state"] = "main"
        await update.message.reply_text("استخدم الأزرار:", reply_markup=kb_main(admin))
        return

    code_val   = info.get("code", code)
    plan       = info.get("plan", "غير معروف")
    days       = info.get("days", "?")
    max_uses   = info.get("max_uses", "?")
    uses       = info.get("uses", 0)
    status     = info.get("status", "?")
    created_at = info.get("created_at")
    expires_at = info.get("expires_at")

    plan_info = SUBSCRIPTION_TYPES.get(plan, {"emoji": "📦", "name": plan})

    status_map = {
        "active":   "🟢 نشط",
        "used":     "🔴 مستخدم بالكامل",
        "expired":  "⏰ منتهي الصلاحية",
        "disabled": "🚫 معطّل",
        "valid":    "🟢 صالح",
    }
    status_display = status_map.get(status, f"ℹ️ {status}")

    if isinstance(uses, int) and isinstance(max_uses, int):
        if max_uses == 0:
            uses_display = f"`{uses}` (غير محدود)"
        elif uses >= max_uses:
            uses_display = f"`{uses} / {max_uses}` ⚠️ مستنفد"
        else:
            uses_display = f"`{uses} / {max_uses}`"
    else:
        uses_display = f"`{uses} / {max_uses}`"

    def fmt_date(d):
        if not d: return "غير محدد"
        try:
            dt = datetime.fromisoformat(str(d).replace("Z", "").split(".")[0])
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(d)[:16]

    report = (
        f"✅ *نتيجة الفحص*\n\n"
        f"🔑 *الكود:*\n`{code_val}`\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"{plan_info['emoji']} *نوع الاشتراك:* {plan_info['name']}\n"
        f"📅 *المدة:* `{days}` يوم\n"
        f"🔢 *عدد الاستخدامات:* {uses_display}\n"
        f"📊 *الحالة:* {status_display}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📆 *أُنشئ:* {fmt_date(created_at)}\n"
        f"⏰ *ينتهي:* {fmt_date(expires_at)}"
    )

    try:
        await wait_msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"فشل عرض: {e}")
        await wait_msg.edit_text(
            f"✅ نتيجة الفحص\n\n"
            f"الكود: {code_val}\n"
            f"النوع: {plan}\n"
            f"المدة: {days} يوم\n"
            f"الاستخدامات: {uses}/{max_uses}\n"
            f"الحالة: {status}"
        )

    context.user_data["state"] = "main"
    await update.message.reply_text("💡 افحص كوداً آخر أو استخدم الأزرار:",
                                      reply_markup=kb_main(admin))

# ═══════════════════════════════════════════════════════════════════
# 💰 المكافأة + الدعوة + المعرف
# ═══════════════════════════════════════════════════════════════════

async def do_daily(update, context):
    ok, msg = await db.claim_daily_bonus(update.effective_user.id)
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
        await update.message.reply_text("❌ معرف غير صالح. أرسل رقماً:", reply_markup=kb_cancel())
        return
    if target_id == update.effective_user.id:
        await update.message.reply_text("❌ لا يمكن التحويل لنفسك:", reply_markup=kb_cancel())
        return
    target = await db.get_user(target_id)
    if not target:
        await update.message.reply_text("❌ غير مسجل. أرسل معرفاً آخر:", reply_markup=kb_cancel())
        return
    context.user_data["transfer_to"] = target_id
    context.user_data["state"] = "transfer_amount"
    name = target.get("first_name") or target.get("username") or str(target_id)
    await update.message.reply_text(f"👤 *{name}*\n\n💎 أرسل عدد النقاط:",
                                      parse_mode="Markdown", reply_markup=kb_cancel())

async def transfer_get_amount(update, context, text):
    try:
        amount = int(text)
        if amount < MIN_TRANSFER:
            raise ValueError
    except ValueError:
        await update.message.reply_text(f"❌ الحد الأدنى {MIN_TRANSFER}. أرسل رقماً:",
                                          reply_markup=kb_cancel()); return
    user = await db.get_user(update.effective_user.id)
    if user["points"] < amount:
        await update.message.reply_text(f"🔒 رصيدك `{user['points']}`. أرسل أقل:",
                                          parse_mode="Markdown", reply_markup=kb_cancel()); return
    context.user_data["transfer_amount"] = amount
    context.user_data["state"] = "transfer_confirm"
    target_id = context.user_data.get("transfer_to")
    target = await db.get_user(target_id)
    name = target.get("first_name") or target.get("username") or str(target_id)
    await update.message.reply_text(
        f"📋 *تأكيد:*\n\n👤 *{name}*\n💎 `{amount}`\n\nأرسل `تأكيد` للمتابعة:",
        parse_mode="Markdown", reply_markup=kb_cancel())

async def transfer_do_confirm(update, context, text):
    if text.strip().lower() not in ("تأكيد", "confirm", "نعم"):
        await update.message.reply_text("❌ أرسل `تأكيد` أو ❌ إلغاء:",
                                          parse_mode="Markdown", reply_markup=kb_cancel()); return
    target_id = context.user_data.get("transfer_to")
    amount = context.user_data.get("transfer_amount")
    if not target_id or not amount:
        await show_home(update, context); return
    ok, msg = await db.transfer_points(update.effective_user.id, target_id, amount)
    if ok:
        target = await db.get_user(target_id)
        name = target.get("first_name") or target.get("username") or str(target_id)
        await update.message.reply_text(
            f"✅ *تم التحويل!*\n\n👤 *{name}*\n💎 `{amount}`",
            parse_mode="Markdown", reply_markup=kb_main(is_admin(update.effective_user.id)))
        try:
            await context.bot.send_message(target_id,
                f"🎁 *وصلك تحويل!*\n\nمن: {update.effective_user.first_name}\n💎 `{amount}`",
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
    context.user_data["buy"] = {"type": sub_type}
    context.user_data["state"] = "buy_days"
    prices_text = "\n".join([f"  • {d} يوم = {p} 💎" for d, p in info["prices"].items()])
    await update.message.reply_text(
        f"{info['emoji']} *{info['name']}*\n\n{info['description']}\n\n"
        f"💰 *الأسعار:*\n{prices_text}\n\n"
        f"💎 رصيدك: `{user['points']}`\n\n📅 اختر المدة:",
        parse_mode="Markdown", reply_markup=kb_days(sub_type))

async def buy_choose_days(update, context, days):
    ctx = context.user_data.get("buy", {})
    sub_type = ctx.get("type")
    if not sub_type:
        await show_shop(update, context); return
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
        f"💎 رصيدك: `{user['points']}`\n\n"
        f"🔢 اختر عدد الأكواد:\n_(خصم تلقائي للكميات)_",
        parse_mode="Markdown", reply_markup=kb_quantity())

async def buy_choose_qty(update, context, qty):
    ctx = context.user_data.get("buy", {})
    sub_type = ctx.get("type")
    days = ctx.get("days")
    if not sub_type or not days:
        await show_shop(update, context); return

    info = SUBSCRIPTION_TYPES[sub_type]
    unit_price = info["prices"][days]
    total, subtotal, discount = calculate_price(unit_price, qty)
    user = await db.get_user(update.effective_user.id)

    if user["points"] < total:
        await update.message.reply_text(
            f"🔒 *نقاطك غير كافية*\n\nالمطلوب: `{total}` 💎\nلديك: `{user['points']}` 💎\n"
            f"ينقصك: `{total - user['points']}` 💎",
            parse_mode="Markdown", reply_markup=kb_quantity())
        return

    ctx["quantity"] = qty
    ctx["subtotal"] = subtotal
    ctx["discount"] = discount
    ctx["total"] = total
    context.user_data["state"] = "buy_confirm"

    discount_line = f"\n🎁 خصم: `{discount}%` (`-{subtotal - total}` 💎)" if discount > 0 else ""
    await update.message.reply_text(
        f"📋 *ملخص الطلب*\n\n"
        f"{info['emoji']} *{info['name']}*\n📅 {days} يوم\n🔢 {qty} كود\n\n"
        f"─────────────────\n"
        f"سعر الوحدة: `{unit_price}` 💎\n"
        f"المجموع: `{subtotal}` 💎{discount_line}\n"
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

        logger.info(f"[BUY] user={user_id} type={sub_type} days={days} qty={quantity} total={total}")

        if not all([sub_type, days, quantity, total]):
            await update.message.reply_text("❌ بيانات الطلب ناقصة. ابدأ من جديد.",
                                              reply_markup=kb_shop())
            context.user_data["state"] = "shop"
            return

        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ المستخدم غير موجود.", reply_markup=kb_main(admin))
            return

        if user["points"] < total:
            await update.message.reply_text(
                f"🔒 نقاطك غير كافية\n\nالمطلوب: {total}\nلديك: {user['points']}",
                reply_markup=kb_main(admin))
            return

        info = SUBSCRIPTION_TYPES[sub_type]
        api_plan = info["api_plan"]

        await update.message.reply_text(
            f"⏳ *جاري إنشاء {quantity} كود...*\n\n"
            f"📦 {info['name']} — {days} يوم\n"
            f"🔑 نوع API: `{api_plan}`\n\n"
            f"⏱️ قد يستغرق {quantity * 3} ثانية تقريباً.",
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
                        try:
                            await db.save_subscription(user_id, {
                                "code": code, "plan": sub_type, "actual_plan": api_plan,
                                "days": days, "max_uses": 1, "points_spent": 0,
                                "response": result.get("data", {})
                            })
                        except Exception as e:
                            logger.error(f"[BUY] فشل حفظ DB: {e}")
                    else:
                        failed += 1
                        if not first_error:
                            first_error = f"لا كود في الاستجابة: {str(result.get('data'))[:150]}"
                else:
                    failed += 1
                    if not first_error:
                        first_error = result.get("message", "خطأ غير معروف")
            except Exception as e:
                failed += 1
                if not first_error:
                    first_error = str(e)

        if not codes:
            if sub_type == "premium":
                await update.message.reply_text(
                    f"❌ *عذراً، اشتراك بريميوم غير متوفر حالياً*\n\n"
                    f"🔍 *السبب:* `{first_error[:200]}`\n\n"
                    f"💡 *الخطتان المتاحتان:*\n\n"
                    f"⭐ *بلس* — من 5 نقاط\n"
                    f"💎 *برو* — من 8 نقاط",
                    parse_mode="Markdown", reply_markup=kb_main(admin))
            else:
                await update.message.reply_text(
                    f"❌ *فشل إنشاء الأكواد*\n\n"
                    f"📦 {info['name']}\n"
                    f"🔍 *السبب:* `{first_error[:200]}`",
                    parse_mode="Markdown", reply_markup=kb_main(admin))
            context.user_data.pop("buy", None)
            context.user_data["state"] = "main"
            return

        unit_price = info["prices"][days]
        actual_total, _, _ = calculate_price(unit_price, len(codes))

        if not await db.deduct_points(user_id, actual_total):
            await update.message.reply_text("⚠️ فشل خصم النقاط.",
                                              reply_markup=kb_main(admin))
            return

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
            disable_web_page_preview=True)

        context.user_data.pop("buy", None)
        context.user_data["state"] = "main"

    except Exception as e:
        logger.exception(f"[BUY] خطأ فادح: {e}")
        try:
            await update.message.reply_text(
                f"❌ *خطأ*\n\n`{str(e)[:200]}`",
                parse_mode="Markdown", reply_markup=kb_main(admin))
        except Exception:
            pass
        context.user_data.pop("buy", None)
        context.user_data["state"] = "main"

# ═══════════════════════════════════════════════════════════════════
# 🛡️ لوحة المشرف
# ═══════════════════════════════════════════════════════════════════

async def show_admin(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 للمشرفين فقط", reply_markup=kb_main(False)); return
    context.user_data["state"] = "admin"
    await update.message.reply_text("🛡️ *لوحة المشرف*", parse_mode="Markdown",
                                      reply_markup=kb_admin())

async def show_keys(update, context):
    if not is_admin(update.effective_user.id): return
    keys = await db.list_api_keys()
    active = next((k for k in keys if k["is_active"]), None)
    lines = ["🔑 *المفاتيح*\n"]
    if not keys:
        lines.append("لا توجد مفاتيح.")
    else:
        lines.append(f"🟢 النشط: `{active['label'] if active else '—'}`\n📊 المجموع: {len(keys)}\n")
        for k in keys[:10]:
            s = "🟢" if k["is_active"] else "⚪"
            lines.append(f"{s} #{k['id']} {k.get('label') or '—'} (✅{k['success_count']} ❌{k['fail_count']})")
    context.user_data["state"] = "keys"
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown",
                                      reply_markup=kb_keys())

async def key_add_begin(update, context):
    context.user_data["state"] = "key_add_value"
    await update.message.reply_text("🔐 أرسل قيمة المفتاح:", reply_markup=kb_cancel())

async def key_add_value(update, context, text):
    if len(text) < 5:
        await update.message.reply_text("❌ قصير:", reply_markup=kb_cancel()); return
    context.user_data["new_key_value"] = text
    context.user_data["state"] = "key_add_label"
    await update.message.reply_text("✏️ اسم وصفي:", reply_markup=kb_cancel())

async def key_add_label(update, context, text):
    label = text[:50]
    value = context.user_data.pop("new_key_value", None)
    if not value:
        await show_admin(update, context); return
    await db.add_api_key(value, label, update.effective_user.id)
    ok, msg = await api.test_key(value)
    await update.message.reply_text(f"✅ حُفظ `{label}`\n{msg}",
                                      parse_mode="Markdown", reply_markup=kb_keys())
    context.user_data["state"] = "keys"

async def show_drops(update, context):
    if not is_admin(update.effective_user.id): return
    context.user_data["state"] = "drops"
    await update.message.reply_text(
        "🎁 *دروب الاشتراكات*\n\nأنشئ رابطاً يفتح لأول شخص فقط.",
        parse_mode="Markdown", reply_markup=kb_drops())

async def show_pdrops(update, context):
    if not is_admin(update.effective_user.id): return
    context.user_data["state"] = "pdrops"
    await update.message.reply_text(
        "💎 *دروب النقاط*\n\nأنشئ رابطاً يفتح لأول شخص فقط.",
        parse_mode="Markdown", reply_markup=kb_pdrops())

async def drop_create_begin(update, context):
    context.user_data["state"] = "drop_type"
    rows = [[KeyboardButton(f"drop:{k}") for k in SUBSCRIPTION_TYPES.keys()]]
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text("🎁 اختر النوع:",
                                      reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))

async def drop_choose_type(update, context, text):
    sub_type = text.replace("drop:", "")
    if sub_type not in SUBSCRIPTION_TYPES: return
    context.user_data["drop_plan"] = sub_type
    context.user_data["state"] = "drop_days"
    info = SUBSCRIPTION_TYPES[sub_type]
    days = list(info["prices"].keys())
    rows = []
    if len(days) >= 2: rows.append([KeyboardButton(f"{d} يوم") for d in days[:2]])
    if len(days) > 2: rows.append([KeyboardButton(f"{d} يوم") for d in days[2:]])
    rows.append([KeyboardButton(BTN_CANCEL)])
    await update.message.reply_text(f"{info['emoji']} {info['name']}\n\nاختر المدة:",
                                      reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))

async def drop_choose_days(update, context, text):
    try:
        days = int(text.replace("يوم", "").replace("أيام", "").strip())
    except ValueError:
        return
    plan = context.user_data.pop("drop_plan", None)
    if not plan:
        await show_admin(update, context); return
    token = await db.create_drop(plan, days, update.effective_user.id)
    link = f"https://t.me/{context.bot.username}?start=drop_{token}"
    info = SUBSCRIPTION_TYPES[plan]
    await update.message.reply_text(
        f"✅ *أُنشئ!*\n\n{info['emoji']} {info['name']} — {days}ي\n\n"
        f"🔗 `{link}`\n\n📢 أول شخص يفوز!",
        parse_mode="Markdown", reply_markup=kb_drops())
    context.user_data["state"] = "drops"

async def pdrop_create_begin(update, context):
    context.user_data["state"] = "pdrop_points"
    await update.message.reply_text("💎 أرسل عدد النقاط:", reply_markup=kb_cancel())

async def pdrop_receive(update, context, text):
    try:
        points = int(text)
        if points < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ رقم صحيح ≥ 1:", reply_markup=kb_cancel()); return
    token = await db.create_points_drop(points, update.effective_user.id)
    link = f"https://t.me/{context.bot.username}?start=pdrop_{token}"
    await update.message.reply_text(
        f"✅ *أُنشئ!*\n\n💰 {points} نقطة\n\n🔗 `{link}`\n\n📢 أول شخص يفوز!",
        parse_mode="Markdown", reply_markup=kb_pdrops())
    context.user_data["state"] = "pdrops"

async def show_stats(update, context):
    if not is_admin(update.effective_user.id): return
    users = await db.count_users()
    subs = await db.count_subscriptions()
    keys = await db.list_api_keys()
    txt = f"📊 *إحصائيات*\n\n👥 `{users}`\n📦 `{subs}`\n🔑 `{len(keys)}`"
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb_admin())

async def show_logs(update, context):
    if not is_admin(update.effective_user.id): return
    logs = await db.recent_logs(15)
    lines = ["📜 *السجل:*\n"]
    for l in logs:
        lines.append(f"`{l['created_at'][11:19]}` {l['action']}")
    await update.message.reply_text("\n".join(lines) or "لا سجلات",
                                      parse_mode="Markdown", reply_markup=kb_admin())

# ═══════════════════════════════════════════════════════════════════
# 🎯 الراوتر
# ═══════════════════════════════════════════════════════════════════

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    user_id = update.effective_user.id
    admin = is_admin(user_id)
    state = context.user_data.get("state", "main")

    logger.info(f"[TEXT] user={user_id} state={state} text={text[:40]}")

    try:
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

        if state == "drop_type":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            if text.startswith("drop:"):
                await drop_choose_type(update, context, text); return
            return

        if state == "drop_days":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await drop_choose_days(update, context, text); return

        if state == "pdrop_points":
            if text == BTN_CANCEL:
                context.user_data["state"] = "admin"
                await show_admin(update, context); return
            await pdrop_receive(update, context, text); return

        if text == BTN_HOME:    await show_home(update, context); return
        if text == BTN_SHOP:    await show_shop(update, context); return
        if text == BTN_SUBS:    await show_subs(update, context); return
        if text == BTN_WALLET:  await show_wallet(update, context); return
        if text == BTN_EARN:    await show_earn(update, context); return
        if text == BTN_TOP:     await show_top(update, context); return
        if text == BTN_GUIDE:   await show_guide(update, context); return
        if text == BTN_CHECK:   await check_code_begin(update, context); return
        if text == BTN_ABOUT:   await show_about(update, context); return
        if text == BTN_ADMIN:   await show_admin(update, context); return

        if text == BTN_BACK:
            if state in ("shop", "buy_days", "buy_qty", "buy_confirm"):
                await show_shop(update, context)
            elif state == "wallet":
                await show_wallet(update, context)
            elif state == "earn":
                await show_earn(update, context)
            elif state in ("admin", "keys", "drops", "pdrops"):
                await show_admin(update, context)
            else:
                await show_home(update, context)
            return

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
                sub_type = ctx.get("type")
                if sub_type:
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
                await update.message.reply_text("❌ رقم بين 1 و 100:", reply_markup=kb_cancel())
                return
            await buy_choose_qty(update, context, qty); return

        if state == "buy_confirm":
            if text == BTN_CONFIRM:
                await buy_confirm(update, context); return
            if text == BTN_EDIT_QTY:
                ctx = context.user_data.get("buy", {})
                sub_type = ctx.get("type")
                if sub_type:
                    context.user_data["state"] = "buy_qty"
                    await update.message.reply_text("🔢 اختر عدداً جديداً:", reply_markup=kb_quantity())
                return
            if text == BTN_CANCEL:
                await show_home(update, context); return

        if state in ("wallet", "earn"):
            if text == BTN_DAILY:    await do_daily(update, context); return
            if text == BTN_INVITE:   await show_invite(update, context); return
            if text == BTN_MY_ID:    await show_my_id(update, context); return
            if text == BTN_TRANSFER: await transfer_begin(update, context); return

        if state == "admin" and admin:
            if text == BTN_KEYS:    await show_keys(update, context); return
            if text == BTN_DROPS:   await show_drops(update, context); return
            if text == BTN_PDROPS:  await show_pdrops(update, context); return
            if text == BTN_STATS:   await show_stats(update, context); return
            if text == BTN_LOGS:    await show_logs(update, context); return

        if state == "keys" and admin:
            if text == BTN_ADD_KEY:
                await key_add_begin(update, context); return

        if state == "drops" and admin:
            if text == BTN_CREATE_DROP:
                await drop_create_begin(update, context); return

        if state == "pdrops" and admin:
            if text == BTN_CREATE_PDROP:
                await pdrop_create_begin(update, context); return

        await update.message.reply_text("🤔 استخدم الأزرار بالأسفل.", reply_markup=kb_main(admin))

    except Exception as e:
        logger.exception(f"[TEXT] خطأ: {e}")
        try:
            await update.message.reply_text(
                f"❌ خطأ: `{str(e)[:150]}`",
                parse_mode="Markdown", reply_markup=kb_main(admin))
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════════
# 🛡️ أوامر
# ═══════════════════════════════════════════════════════════════════

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_admin(update, context)

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("`/ban <id>`", parse_mode="Markdown"); return
    try: uid = int(context.args[0])
    except: return
    await db.set_ban(uid, 1)
    await update.message.reply_text(f"✅ حُظر {uid}")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args: return
    try: uid = int(context.args[0])
    except: return
    await db.set_ban(uid, 0)
    await update.message.reply_text(f"✅ رُفع الحظر")

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = "main"
    for k in ("buy", "transfer_to", "transfer_amount", "new_key_value", "drop_plan"):
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
            logger.info(f"📁 أُنشئ مجلد: {db_dir}")
        except Exception as e:
            logger.error(f"❌ فشل إنشاء: {e}")

    logger.info(f"💾 DB_PATH = {DB_PATH}")
    logger.info(f"🔑 SUPER_ADMIN_ID = {SUPER_ADMIN_ID}")

    await db.init()

    # 🆕 حذف المفتاح القديم إن وُجد
    keys = await db.list_api_keys()
    for k in keys:
        if k["key_value"] == "Obeida0595440227@":
            await db.delete_api_key(k["id"])
            logger.info("🗑️ حُذف المفتاح القديم (Obeida...)")
            keys = await db.list_api_keys()
            break

    # إضافة/تفعيل المفتاح الجديد
    existing_new = next((k for k in keys if k["key_value"] == INITIAL_API_KEY), None)
    if not existing_new:
        await db.add_api_key(INITIAL_API_KEY, INITIAL_API_KEY_LABEL, SUPER_ADMIN_ID)
        keys = await db.list_api_keys()
        existing_new = next((k for k in keys if k["key_value"] == INITIAL_API_KEY), None)
        logger.info("✅ أُضيف المفتاح الجديد")

    if existing_new and not existing_new["is_active"]:
        await db.set_active_key(existing_new["id"])
        logger.info("✅ فُعّل المفتاح الجديد")

    active = await db.get_active_key()
    if active:
        ok, msg = await api.test_key(active["key_value"])
        logger.info(f"🔑 {msg}")
    else:
        logger.warning("⚠️ لا مفتاح نشط")

    logger.info("✅ Worm GPT جاهز!")


def main():
    if "ضع_التوكن" in BOT_TOKEN:
        print("❌ ضع BOT_TOKEN")
        return

    # 🔧 حل مشكلة Python 3.14
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    # 🌐 HTTP server
    start_http_server()

    logger.info(f"🚀 بدء Worm GPT... (DB: {DB_PATH})")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    logger.info("🚀 بدء التشغيل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
