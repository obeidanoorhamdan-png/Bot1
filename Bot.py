import logging
import requests
import asyncio
from playwright.async_api import async_playwright
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import time
from datetime import datetime
import json
from collections import deque
import os
import sys
import signal
from threading import Thread
import http.server
import socketserver

# --- الإعدادات للاستضافة ---
TWELVE_DATA_KEY = "587f9b72ac4343bca95745b85ac24dbc"
TELEGRAM_TOKEN = "8797849454:AAH3Uk6OcfPjwjPVcG7VPTxuZ06e_9l89Go"
ADMIN_ID = 6207431030
CHANNEL_ID = "@ObeidaTrading"
PORT = int(os.environ.get('PORT', 10000))  # يستخدم PORT

# إعداد متقدم للتسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- نظام ذكي للحفاظ على الاتصال ---
class ConnectionKeeper:
    def __init__(self):
        self.last_heartbeat = time.time()
        self.connection_errors = 0
        self.max_errors = 10
        self.is_healthy = True
        
    def heartbeat(self):
        self.last_heartbeat = time.time()
        self.connection_errors = 0
        
    def report_error(self):
        self.connection_errors += 1
        if self.connection_errors >= self.max_errors:
            self.is_healthy = False
            logger.critical("كثرة الأخطاء - إعادة تشغيل النظام...")
            os._exit(1)  # إجبار على إعادة التشغيل

# --- نظام ذكي للتداول ---
class SmartTradingSystem:
    def __init__(self):
        self.sent_news_ids = set()
        self.active_trades = {}
        self.price_history = deque(maxlen=100)
        self.volatility_level = "متوسطة"
        self.market_condition = "عادية"
        self.success_rate = 0.85
        self.total_trades = 0
        self.winning_trades = 0
        self.last_save = time.time()
        self.load_state()  # تحميل الحالة السابقة
        
    def save_state(self):
        """حفظ الحالة لاستعادتها عند إعادة التشغيل"""
        try:
            state = {
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'success_rate': self.success_rate,
                'sent_news': list(self.sent_news_ids)[-500:]  # آخر 500 خبر فقط
            }
            with open('bot_state.json', 'w') as f:
                json.dump(state, f)
            logger.info("تم حفظ حالة البوت")
        except Exception as e:
            logger.error(f"خطأ في حفظ الحالة: {e}")
    
    def load_state(self):
        """تحميل الحالة السابقة"""
        try:
            if os.path.exists('bot_state.json'):
                with open('bot_state.json', 'r') as f:
                    state = json.load(f)
                self.total_trades = state.get('total_trades', 0)
                self.winning_trades = state.get('winning_trades', 0)
                self.success_rate = state.get('success_rate', 0.85)
                self.sent_news_ids = set(state.get('sent_news', []))
                logger.info(f"تم تحميل الحالة: {self.total_trades} صفقة")
        except Exception as e:
            logger.error(f"خطأ في تحميل الحالة: {e}")

# إنشاء النظم
connection_keeper = ConnectionKeeper()
smart_system = SmartTradingSystem()

# --- خادم ويب بسيط لإبقاء Render نشطاً ---
class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            status = f"""
            <html>
                <body style="font-family: Arial; padding: 20px;">
                    <h2>🤖 البوت الذكي يعمل</h2>
                    <p>آخر نبض: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>الصفقات: {smart_system.total_trades}</p>
                    <p>نسبة النجاح: {smart_system.success_rate*100:.1f}%</p>
                    <p>الحالة: ✅ نشط</p>
                </body>
            </html>
            """
            self.wfile.write(status.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        return  # إلغاء تسجيل الطلبات العادية

def run_health_server():
    """تشغيل خادم الصحة في خيط منفصل"""
    try:
        handler = HealthCheckHandler
        with socketserver.TCPServer(("", PORT), handler) as httpd:
            logger.info(f"✅ خادم الصحة يعمل على المنفذ {PORT}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"خطأ في خادم الصحة: {e}")

# --- دوال البوت الأساسية مع تحسينات للاستضافة ---

def get_smart_price(symbol):
    """جلب السعر مع محاولات متعددة"""
    for attempt in range(3):
        try:
            url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_KEY}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = float(data.get('price', 0))
                if price > 0:
                    smart_system.price_history.append(price)
                    connection_keeper.heartbeat()
                    return price
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout في محاولة {attempt+1} لـ {symbol}")
        except Exception as e:
            logger.error(f"خطأ في جلب السعر: {e}")
        await asyncio.sleep(2)
    
    connection_keeper.report_error()
    return 0

def analyze_market_conditions(symbol):
    """تحليل ظروف السوق"""
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=20&apikey={TWELVE_DATA_KEY}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return "عادية", "متوسطة"
        
        data = response.json()
        if "values" not in data:
            return "عادية", "متوسطة"
        
        prices = [float(v['close']) for v in data['values']]
        
        # حساب التقلب
        price_range = max(prices) - min(prices)
        avg_price = sum(prices) / len(prices)
        volatility_percent = (price_range / avg_price) * 100
        
        if volatility_percent > 0.5:
            volatility = "عالية 📈"
        elif volatility_percent > 0.2:
            volatility = "متوسطة 📊"
        else:
            volatility = "منخفضة 📉"
        
        # تحليل الاتجاه
        sma_5 = sum(prices[-5:]) / 5
        sma_20 = sum(prices) / 20
        
        if sma_5 > sma_20 * 1.001:
            condition = "صاعدة 🚀"
        elif sma_5 < sma_20 * 0.999:
            condition = "هابطة 📉"
        else:
            condition = "جانبية ↔️"
        
        return condition, volatility
        
    except Exception as e:
        logger.error(f"خطأ في تحليل السوق: {e}")
        return "عادية", "متوسطة"

async def smart_capture_chart(symbol):
    """سحب الشارت مع تحمل الأخطاء"""
    for attempt in range(3):
        try:
            async with async_playwright() as p:
                tv_symbol = symbol.replace("/", "")
                url = f"https://www.tradingview.com/chart/?symbol=FX:{tv_symbol}"
                
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--single-process'  # مهم لـ Render
                    ]
                )
                page = await browser.new_page()
                await page.set_viewport_size({"width": 1280, "height": 720})
                
                await page.goto(url, timeout=30000, wait_until='domcontentloaded')
                await asyncio.sleep(5)
                
                path = f"/tmp/chart_{tv_symbol}_{int(time.time())}.png"
                await page.screenshot(path=path, full_page=False)
                await browser.close()
                
                logger.info(f"تم سحب الشارت: {path}")
                return path
                
        except Exception as e:
            logger.error(f"خطأ في سحب الشارت (محاولة {attempt+1}): {e}")
            await asyncio.sleep(3)
    
    return None

async def send_smart_signal(context, symbol, currency, price, news_item, decision, strength, market_condition, volatility):
    """إرسال إشارة التداول"""
    
    # حساب الأهداف
    base_distance = 0.0050
    pip_value = 0.0001 if 'JPY' not in symbol else 0.01
    
    if volatility == "عالية 📈":
        tp_multiplier = 3.0
    elif volatility == "متوسطة 📊":
        tp_multiplier = 2.0
    else:
        tp_multiplier = 1.5
    
    if decision == "شراء 🟢":
        tp1 = price + (base_distance * tp_multiplier)
        tp2 = price + (base_distance * tp_multiplier * 2)
        tp3 = price + (base_distance * tp_multiplier * 3)
        sl = price - (base_distance * 1.2)
    else:
        tp1 = price - (base_distance * tp_multiplier)
        tp2 = price - (base_distance * tp_multiplier * 2)
        tp3 = price - (base_distance * tp_multiplier * 3)
        sl = price + (base_distance * 1.2)
    
    # إنشاء الرسالة
    signal_message = (
        f"🎯 **إشارة تنفيذية - {currency}/USD**\n\n"
        f"📊 **التحليل:**\n"
        f"• السعر: `{price:.5f}`\n"
        f"• القرار: {decision}\n"
        f"• القوة: {strength}\n"
        f"• السوق: {market_condition}\n"
        f"• التقلب: {volatility}\n\n"
        f"📈 **التفاصيل:**\n"
        f"📍 الدخول: `{price:.5f}`\n\n"
        f"🎯 **الأهداف:**\n"
        f"  TP1: `{tp1:.5f}`\n"
        f"  TP2: `{tp2:.5f}`\n"
        f"  TP3: `{tp3:.5f}`\n\n"
        f"🛡️ **وقف الخسارة:** `{sl:.5f}`\n\n"
        f"#{currency} #{'شراء' if 'شراء' in decision else 'بيع'}"
    )
    
    # حفظ الصفقة
    trade_id = f"{symbol}_{int(time.time())}"
    smart_system.active_trades[trade_id] = {
        'symbol': symbol,
        'currency': currency,
        'entry': price,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'sl': sl,
        'time': time.time(),
        'decision': decision
    }
    
    return signal_message, trade_id

# --- المراقبة الرئيسية ---
async def monitored_news_check(context: ContextTypes.DEFAULT_TYPE):
    """فحص الأخبار مع مراقبة الصحة"""
    try:
        connection_keeper.heartbeat()
        logger.info("جاري فحص الأخبار...")
        
        url = f"https://api.twelvedata.com/economic_calendar?apikey={TWELVE_DATA_KEY}"
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"خطأ في API: {response.status_code}")
            return
        
        data = response.json()
        news_list = data.get("calendar", [])
        
        for item in news_list[:5]:  # حد أقصى 5 أخبار لكل دورة
            event_id = f"{item.get('event')}_{item.get('timestamp', '')}"
            
            # فلترة الأخبار
            if (item.get('importance') in ['High', 'Medium'] and 
                event_id not in smart_system.sent_news_ids):
                
                currency = item.get('currency', 'USD')
                symbol = f"{currency}/USD"
                
                logger.info(f"خبر جديد: {item.get('event')} - {currency}")
                
                # تحليل السوق
                market_condition, volatility = analyze_market_conditions(symbol)
                
                # انتظار
                await asyncio.sleep(5)
                
                # جلب السعر
                price = get_smart_price(symbol)
                
                if price > 0:
                    # تحديد القرار
                    decision = "شراء 🟢" if item.get('importance') == 'High' else "بيع 🔴"
                    strength = "عالية جدا 💥" if item.get('importance') == 'High' else "عالية 🔥"
                    
                    # إرسال الإشارة
                    signal_message, trade_id = await send_smart_signal(
                        context, symbol, currency, price, item,
                        decision, strength, market_condition, volatility
                    )
                    
                    # سحب الشارت
                    chart_file = await smart_capture_chart(symbol)
                    
                    # إرسال للقناة
                    try:
                        if chart_file:
                            with open(chart_file, 'rb') as photo:
                                await context.bot.send_photo(
                                    chat_id=CHANNEL_ID,
                                    photo=photo,
                                    caption=signal_message
                                )
                            os.remove(chart_file)  # تنظيف
                        else:
                            await context.bot.send_message(
                                chat_id=CHANNEL_ID,
                                text=signal_message
                            )
                        
                        # تحديث الإحصائيات
                        smart_system.total_trades += 1
                        smart_system.sent_news_ids.add(event_id)
                        
                        logger.info(f"تم إرسال توصية {currency}")
                        
                    except Exception as e:
                        logger.error(f"خطأ في إرسال التوصية: {e}")
                
                # حفظ الحالة كل 10 أخبار
                if len(smart_system.sent_news_ids) % 10 == 0:
                    smart_system.save_state()
        
        # حفظ الحالة دورياً
        if time.time() - smart_system.last_save > 300:  # كل 5 دقائق
            smart_system.save_state()
            smart_system.last_save = time.time()
            
    except Exception as e:
        logger.error(f"خطأ في المراقبة: {e}")
        connection_keeper.report_error()

# --- معالج إيقاف التشغيل ---
def shutdown_handler(signum, frame):
    """حفظ البيانات قبل الإيقاف"""
    logger.info("جارٍ إيقاف التشغيل... حفظ البيانات")
    smart_system.save_state()
    sys.exit(0)

# --- أوامر التليجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            "🤖 ** جميع التوصيات **\n\n"
            f"📊 الصفقات: {smart_system.total_trades}\n"
            f"📈 نسبة النجاح: {smart_system.success_rate*100:.1f}%\n"
            f"⏱️ آخر نبض: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"✅ النظام مستقر"
        )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            f"📊 **إحصائيات توصيات **\n\n"
            f"• إجمالي الصفقات: {smart_system.total_trades}\n"
            f"• الناجحة: {smart_system.winning_trades}\n"
            f"• نسبة النجاح: {smart_system.success_rate*100:.1f}%\n"
            f"• النشطة حالياً: {len(smart_system.active_trades)}\n"
            f"• الأخبار المخزنة: {len(smart_system.sent_news_ids)}\n"
            f"• حالة الاتصال: {'✅ جيد' if connection_keeper.is_healthy else '⚠️ ضعيف'}"
        )

async def force_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص فوري للأخبار"""
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("🔄 جاري الفحص الفوري...")
        await monitored_news_check(context)
        await update.message.reply_text("✅ تم الفحص")

# --- الدالة الرئيسية ---
def main():
    # تسجيل معالج الإيقاف
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    
    # تشغيل خادم الصحة في خيط منفصل
    health_thread = Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # إنشاء تطبيق التليجرام
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # جدولة المهام - استراتيجية متعددة لضمان عدم التوقف
    app.job_queue.run_repeating(monitored_news_check, interval=30, first=5)  # كل 30 ثانية
    app.job_queue.run_repeating(lambda ctx: smart_system.save_state(), interval=300, first=3600)  # حفظ كل 60 دقائق
    
    # إضافة الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("force", force_check))
    
    logger.info("🚀 البوت الذكي بدأ يعمل ")
    logger.info(f"المنفذ: {PORT}")
    
    # تشغيل البوت
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=['message'],
        timeout=30
    )

if __name__ == '__main__':
    main()
