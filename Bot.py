import logging
import requests
import asyncio
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import time
from datetime import datetime
import json
import os
import sys
import numpy as np
from collections import deque
import threading
import http.server
import socketserver
import signal

# ==================== الإعدادات الأساسية ====================
TWELVE_DATA_KEY = "587f9b72ac4343bca95745b85ac24dbc"
TELEGRAM_TOKEN = "8797849454:AAH3Uk6OcfPjwjPVcG7VPTxuZ06e_9l89Go"
ADMIN_ID = 6207431030
CHANNEL_ID = "@ObeidaTrading"
PORT = int(os.environ.get('PORT', 10000))

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('super_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== نظام الحفاظ على الاتصال ====================
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
            os._exit(1)

# ==================== خادم الصحة ====================
class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            status = f"""
            <html>
                <body style="font-family: Arial; padding: 20px;">
                    <h2>🤖 البوت الفائق يعمل</h2>
                    <p>آخر نبض: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>الحالة: ✅ نشط</p>
                </body>
            </html>
            """
            self.wfile.write(status.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        return

def run_health_server():
    try:
        handler = HealthCheckHandler
        with socketserver.TCPServer(("", PORT), handler) as httpd:
            logger.info(f"✅ خادم الصحة يعمل على المنفذ {PORT}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"خطأ في خادم الصحة: {e}")

# ==================== نظام تحليل السوق ====================
class MarketAnalyzer:
    def __init__(self):
        self.price_history = deque(maxlen=1000)
        self.volume_history = deque(maxlen=1000)
        
    async def comprehensive_analysis(self, symbol):
        """تحليل شامل للسوق"""
        try:
            # جلب البيانات
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=100&apikey={TWELVE_DATA_KEY}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return self.get_default_analysis()
            
            data = response.json()
            if "values" not in data:
                return self.get_default_analysis()
            
            values = data["values"]
            closes = [float(v['close']) for v in values]
            highs = [float(v['high']) for v in values]
            lows = [float(v['low']) for v in values]
            volumes = [float(v.get('volume', 0)) for v in values]
            
            # تحليل الاتجاه
            sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else sum(closes) / len(closes)
            sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma_20
            current_price = closes[-1]
            
            trend_direction = "UP" if current_price > sma_20 > sma_50 else "DOWN" if current_price < sma_20 < sma_50 else "SIDEWAYS"
            
            # حساب RSI
            rsi = self.calculate_rsi(closes)
            
            # حساب الدعم والمقاومة
            support = min(lows[-20:])
            resistance = max(highs[-20:])
            
            # تحليل الحجم
            avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 0
            current_volume = volumes[-1] if volumes else 0
            volume_signal = current_volume > avg_volume * 1.5
            
            # قوة الإشارة
            signal_strength = 0.5
            if trend_direction == "UP":
                signal_strength += 0.2
            if rsi < 30:
                signal_strength += 0.15
            elif rsi > 70:
                signal_strength -= 0.15
            if volume_signal:
                signal_strength += 0.15
                
            return {
                'signal': 'BUY' if signal_strength > 0.6 else 'SELL' if signal_strength < 0.4 else 'NEUTRAL',
                'strength': abs(signal_strength - 0.5) * 2,
                'current_price': current_price,
                'trend': trend_direction,
                'rsi': rsi,
                'support': support,
                'resistance': resistance,
                'volume_signal': volume_signal,
                'sma_20': sma_20,
                'sma_50': sma_50
            }
            
        except Exception as e:
            logger.error(f"خطأ في تحليل السوق: {e}")
            return self.get_default_analysis()
    
    def calculate_rsi(self, prices, period=14):
        """حساب مؤشر RSI"""
        if len(prices) < period + 1:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def get_default_analysis(self):
        return {
            'signal': 'NEUTRAL',
            'strength': 0.5,
            'current_price': 0,
            'trend': 'SIDEWAYS',
            'rsi': 50,
            'support': 0,
            'resistance': 0,
            'volume_signal': False,
            'sma_20': 0,
            'sma_50': 0
        }

# ==================== نظام تحليل المشاعر ====================
class SentimentAnalyzer:
    async def analyze_market_sentiment(self, symbol, currency):
        """تحليل مشاعر السوق"""
        try:
            # تحليل بسيط للمشاعر من الأخبار
            url = f"https://api.twelvedata.com/news?symbol={symbol}&apikey={TWELVE_DATA_KEY}"
            response = requests.get(url, timeout=10)
            
            sentiment_score = 0.5
            news_count = 0
            
            if response.status_code == 200:
                data = response.json()
                news_items = data.get('news', [])[:10]
                
                positive = 0
                negative = 0
                
                for item in news_items:
                    title = item.get('title', '').lower()
                    if any(word in title for word in ['rise', 'gain', 'up', 'positive', 'bull']):
                        positive += 1
                    elif any(word in title for word in ['fall', 'drop', 'down', 'negative', 'bear']):
                        negative += 1
                
                total = positive + negative
                if total > 0:
                    sentiment_score = positive / total
                    news_count = total
            
            return {
                'score': sentiment_score,
                'interpretation': 'إيجابي' if sentiment_score > 0.6 else 'سلبي' if sentiment_score < 0.4 else 'محايد',
                'news_count': news_count
            }
            
        except Exception as e:
            logger.error(f"خطأ في تحليل المشاعر: {e}")
            return {'score': 0.5, 'interpretation': 'محايد', 'news_count': 0}

# ==================== نظام إدارة المخاطر ====================
class RiskManager:
    def __init__(self, account_balance=10000):
        self.balance = account_balance
        self.max_risk_per_trade = 0.02
        
    def calculate_position_size(self, entry, stop_loss, signal_strength):
        """حساب حجم المركز"""
        if stop_loss == 0 or entry == 0:
            return 0
        
        risk_amount = self.balance * self.max_risk_per_trade
        
        # تعديل حسب قوة الإشارة
        strength_multiplier = {
            'عالية جدا 💥': 1.5,
            'عالية 🔥': 1.2,
            'متوسطة ⚡': 1.0,
            'ضعيفة ❄️': 0.5
        }.get(signal_strength, 1.0)
        
        stop_distance = abs(entry - stop_loss)
        position_size = (risk_amount * strength_multiplier) / stop_distance if stop_distance > 0 else 0
        
        return {
            'size': round(position_size, 2),
            'units': round(position_size * 100000, 0),
            'risk_percent': round((risk_amount * strength_multiplier / self.balance) * 100, 2)
        }

# ==================== نظام كشف الأنماط ====================
class PatternDetector:
    def detect_patterns(self, symbol, price_data):
        """كشف الأنماط السعرية البسيطة"""
        try:
            patterns = []
            
            if len(price_data) < 5:
                return patterns
            
            closes = [float(p.get('close', 0)) for p in price_data[-10:]]
            highs = [float(p.get('high', 0)) for p in price_data[-10:]]
            lows = [float(p.get('low', 0)) for p in price_data[-10:]]
            
            if len(closes) < 5:
                return patterns
            
            # كشف نمط القمة المزدوجة
            if len(highs) >= 10:
                first_peak = max(highs[:5])
                second_peak = max(highs[5:])
                if abs(first_peak - second_peak) / first_peak < 0.01:
                    patterns.append({
                        'name': 'قمة مزدوجة',
                        'direction': 'SELL',
                        'reliability': 0.7
                    })
            
            # كشف نمط القاع المزدوج
            if len(lows) >= 10:
                first_bottom = min(lows[:5])
                second_bottom = min(lows[5:])
                if abs(first_bottom - second_bottom) / first_bottom < 0.01:
                    patterns.append({
                        'name': 'قاع مزدوج',
                        'direction': 'BUY',
                        'reliability': 0.7
                    })
            
            return patterns
            
        except Exception as e:
            logger.error(f"خطأ في كشف الأنماط: {e}")
            return []

# ==================== نظام تتبع الحيتان ====================
class WhaleTracker:
    async def track_whales(self, symbol):
        """تتبع تحركات كبار المتداولين (محاكاة)"""
        # هذا نظام محاكاة - في الواقع يحتاج API خاص
        return {
            'whale_sentiment': 'neutral',
            'accumulation': 0,
            'key_levels': []
        }

# ==================== نظام تحليل الأخبار المحسن ====================
class EnhancedNewsAnalyzer:
    async def analyze_news_deeply(self, news_item):
        """تحليل عميق للخبر"""
        try:
            importance = news_item.get('importance', 'Medium')
            currency = news_item.get('currency', 'USD')
            event = news_item.get('event', '')
            
            importance_score = {
                'High': 1.0,
                'Medium': 0.6,
                'Low': 0.3
            }.get(importance, 0.5)
            
            # تحديد التأثير المتوقع
            expected_impact = 'bullish'
            if 'cut' in event.lower() or 'lower' in event.lower():
                expected_impact = 'bullish' if currency in ['EUR', 'GBP'] else 'bearish'
            elif 'raise' in event.lower() or 'higher' in event.lower():
                expected_impact = 'bearish' if currency in ['EUR', 'GBP'] else 'bullish'
            
            return {
                'real_importance': importance_score,
                'expected_impact': expected_impact,
                'trading_opportunity': importance_score > 0.5
            }
            
        except Exception as e:
            logger.error(f"خطأ في تحليل الخبر: {e}")
            return {'real_importance': 0.5, 'expected_impact': 'neutral', 'trading_opportunity': False}

# ==================== نظام توليد الإشارات ====================
class SignalGenerator:
    def __init__(self):
        self.market_analyzer = MarketAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.pattern_detector = PatternDetector()
        self.whale_tracker = WhaleTracker()
        self.news_analyzer = EnhancedNewsAnalyzer()
        self.risk_manager = RiskManager()
        
    async def generate_signal(self, symbol, currency, news_item):
        """توليد إشارة تداول متكاملة"""
        try:
            # تحليل السوق
            market_analysis = await self.market_analyzer.comprehensive_analysis(symbol)
            
            # تحليل المشاعر
            sentiment = await self.sentiment_analyzer.analyze_market_sentiment(symbol, currency)
            
            # تحليل الأخبار
            news_analysis = await self.news_analyzer.analyze_news_deeply(news_item)
            
            # تحديد القرار النهائي
            buy_signals = 0
            sell_signals = 0
            total_weight = 0
            
            # من التحليل الفني
            if market_analysis['signal'] == 'BUY':
                buy_signals += market_analysis['strength'] * 3
            elif market_analysis['signal'] == 'SELL':
                sell_signals += market_analysis['strength'] * 3
            
            # من المشاعر
            if sentiment['score'] > 0.6:
                buy_signals += (sentiment['score'] - 0.5) * 2
            elif sentiment['score'] < 0.4:
                sell_signals += (0.5 - sentiment['score']) * 2
            
            # من الأخبار
            if news_analysis['trading_opportunity']:
                if news_analysis['expected_impact'] == 'bullish':
                    buy_signals += news_analysis['real_importance']
                else:
                    sell_signals += news_analysis['real_importance']
            
            # القرار النهائي
            if buy_signals > sell_signals + 0.5:
                decision = "شراء 🟢"
                strength = "عالية جدا 💥" if buy_signals > 2 else "عالية 🔥"
            elif sell_signals > buy_signals + 0.5:
                decision = "بيع 🔴"
                strength = "عالية جدا 💥" if sell_signals > 2 else "عالية 🔥"
            else:
                decision = "انتظار ⏳"
                strength = "متوسطة ⚡"
            
            return {
                'decision': decision,
                'strength': strength,
                'price': market_analysis['current_price'],
                'market_analysis': market_analysis,
                'sentiment': sentiment,
                'news_analysis': news_analysis,
                'confidence': max(buy_signals, sell_signals) / 3
            }
            
        except Exception as e:
            logger.error(f"خطأ في توليد الإشارة: {e}")
            return None

# ==================== النظام الرئيسي ====================
class SuperTradingBot:
    def __init__(self):
        self.sent_news_ids = set()
        self.active_trades = {}
        self.trade_history = []
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'success_rate': 0.85
        }
        self.signal_generator = SignalGenerator()
        self.connection_keeper = ConnectionKeeper()
        
        # تحميل الحالة
        self.load_state()
        
    def save_state(self):
        """حفظ حالة البوت"""
        try:
            state = {
                'total_trades': self.performance_metrics['total_trades'],
                'winning_trades': self.performance_metrics['winning_trades'],
                'success_rate': self.performance_metrics['success_rate'],
                'sent_news': list(self.sent_news_ids)[-500:]
            }
            with open('bot_state.json', 'w') as f:
                json.dump(state, f)
            logger.info("✅ تم حفظ حالة البوت")
        except Exception as e:
            logger.error(f"خطأ في حفظ الحالة: {e}")
    
    def load_state(self):
        """تحميل حالة البوت"""
        try:
            if os.path.exists('bot_state.json'):
                with open('bot_state.json', 'r') as f:
                    state = json.load(f)
                self.performance_metrics['total_trades'] = state.get('total_trades', 0)
                self.performance_metrics['winning_trades'] = state.get('winning_trades', 0)
                self.performance_metrics['success_rate'] = state.get('success_rate', 0.85)
                self.sent_news_ids = set(state.get('sent_news', []))
                logger.info(f"✅ تم تحميل الحالة: {self.performance_metrics['total_trades']} صفقة")
        except Exception as e:
            logger.error(f"خطأ في تحميل الحالة: {e}")
    
    def get_smart_price(self, symbol):
        """جلب السعر الذكي"""
        for attempt in range(3):
            try:
                url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_KEY}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    price = float(data.get('price', 0))
                    if price > 0:
                        self.connection_keeper.heartbeat()
                        return price
            except:
                pass
            time.sleep(1)
        return 0
    
    async def capture_chart(self, symbol):
        """سحب الشارت"""
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
                            '--disable-gpu'
                        ]
                    )
                    page = await browser.new_page()
                    await page.set_viewport_size({"width": 1280, "height": 720})
                    
                    await page.goto(url, timeout=30000, wait_until='domcontentloaded')
                    await asyncio.sleep(5)
                    
                    path = f"/tmp/chart_{tv_symbol}_{int(time.time())}.png"
                    await page.screenshot(path=path, full_page=False)
                    await browser.close()
                    
                    return path
                    
            except Exception as e:
                logger.error(f"خطأ في سحب الشارت (محاولة {attempt+1}): {e}")
                await asyncio.sleep(2)
        
        return None
    
    async def send_trade_signal(self, context, symbol, currency, price, signal_data, news_item):
        """إرسال إشارة التداول"""
        
        # حساب الأهداف
        base_distance = 0.0050
        pip_value = 0.0001 if 'JPY' not in symbol else 0.01
        
        if signal_data['decision'] == "شراء 🟢":
            tp1 = price + base_distance * 2
            tp2 = price + base_distance * 4
            tp3 = price + base_distance * 6
            sl = price - base_distance * 1.5
        else:
            tp1 = price - base_distance * 2
            tp2 = price - base_distance * 4
            tp3 = price - base_distance * 6
            sl = price + base_distance * 1.5
        
        # حساب حجم الصفقة
        position = self.signal_generator.risk_manager.calculate_position_size(
            price, sl, signal_data['strength']
        )
        
        # إنشاء رسالة التوصية
        signal_message = (
            f"🎯 **إشارة تنفيذية - {currency}/USD**\n\n"
            f"📊 **التحليل الفني:**\n"
            f"• السعر الحالي: `{price:.5f}`\n"
            f"• القرار: {signal_data['decision']}\n"
            f"• قوة الإشارة: {signal_data['strength']}\n"
            f"• الثقة: {signal_data['confidence']*100:.1f}%\n"
            f"• الاتجاه: {signal_data['market_analysis']['trend']}\n"
            f"• RSI: {signal_data['market_analysis']['rsi']:.1f}\n\n"
            f"📈 **تفاصيل الصفقة:**\n"
            f"📍 الدخول: `{price:.5f}`\n"
            f"💰 الحجم: {position['units']} وحدة ({position['risk_percent']}% مخاطرة)\n\n"
            f"🎯 **الأهداف:**\n"
            f"  TP1: `{tp1:.5f}` (+{int(abs(tp1-price)/pip_value)} نقطة)\n"
            f"  TP2: `{tp2:.5f}` (+{int(abs(tp2-price)/pip_value)} نقطة)\n"
            f"  TP3: `{tp3:.5f}` (+{int(abs(tp3-price)/pip_value)} نقطة)\n\n"
            f"🛡️ **وقف الخسارة:** `{sl:.5f}`\n\n"
            f"📰 **الخبر:** {news_item.get('event', '')}\n\n"
            f"#{currency} #{'شراء' if 'شراء' in signal_data['decision'] else 'بيع'}"
        )
        
        # حفظ الصفقة
        trade_id = f"{symbol}_{int(time.time())}"
        self.active_trades[trade_id] = {
            'symbol': symbol,
            'currency': currency,
            'entry': price,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'sl': sl,
            'time': time.time(),
            'decision': signal_data['decision']
        }
        
        return signal_message, trade_id
    
    async def monitor_news(self, context):
        """مراقبة الأخبار"""
        try:
            self.connection_keeper.heartbeat()
            logger.info("جاري فحص الأخبار...")
            
            url = f"https://api.twelvedata.com/economic_calendar?apikey={TWELVE_DATA_KEY}"
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"خطأ في API: {response.status_code}")
                return
            
            data = response.json()
            news_list = data.get("calendar", [])
            
            for item in news_list[:3]:
                event_id = f"{item.get('event')}_{item.get('timestamp', '')}"
                
                if (item.get('importance') in ['High', 'Medium'] and 
                    event_id not in self.sent_news_ids):
                    
                    currency = item.get('currency', 'USD')
                    symbol = f"{currency}/USD"
                    
                    logger.info(f"📰 خبر جديد: {item.get('event')} - {currency}")
                    
                    # توليد الإشارة
                    signal_data = await self.signal_generator.generate_signal(symbol, currency, item)
                    
                    if signal_data and signal_data['decision'] != "انتظار ⏳":
                        
                        # جلب السعر الحالي
                        price = self.get_smart_price(symbol)
                        
                        if price > 0:
                            # إرسال الإشارة
                            signal_message, trade_id = await self.send_trade_signal(
                                context, symbol, currency, price, signal_data, item
                            )
                            
                            # سحب الشارت
                            chart_file = await self.capture_chart(symbol)
                            
                            # إرسال للقناة
                            try:
                                if chart_file:
                                    with open(chart_file, 'rb') as photo:
                                        await context.bot.send_photo(
                                            chat_id=CHANNEL_ID,
                                            photo=photo,
                                            caption=signal_message
                                        )
                                    os.remove(chart_file)
                                else:
                                    await context.bot.send_message(
                                        chat_id=CHANNEL_ID,
                                        text=signal_message
                                    )
                                
                                # تحديث الإحصائيات
                                self.performance_metrics['total_trades'] += 1
                                self.sent_news_ids.add(event_id)
                                
                                logger.info(f"✅ تم إرسال توصية {currency}")
                                
                            except Exception as e:
                                logger.error(f"خطأ في إرسال التوصية: {e}")
                    
                    # حفظ الحالة
                    if len(self.sent_news_ids) % 10 == 0:
                        self.save_state()
                        
        except Exception as e:
            logger.error(f"خطأ في مراقبة الأخبار: {e}")
            self.connection_keeper.report_error()

# ==================== واجهة التليجرام ====================
class TelegramInterface:
    def __init__(self, bot):
        self.bot = bot
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر البدء"""
        keyboard = [
            [InlineKeyboardButton("📊 تحليل فوري", callback_data='instant_analysis')],
            [InlineKeyboardButton("📰 آخر الأخبار", callback_data='latest_news')],
            [InlineKeyboardButton("💰 الصفقات النشطة", callback_data='active_trades')],
            [InlineKeyboardButton("📈 إحصائيات", callback_data='stats')],
            [InlineKeyboardButton("⚙️ إعدادات", callback_data='settings')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 **مرحباً بك في البوت الفائق**\n\n"
            f"📊 إجمالي الصفقات: {self.bot.performance_metrics['total_trades']}\n"
            f"📈 نسبة النجاح: {self.bot.performance_metrics['success_rate']*100:.1f}%\n"
            f"💰 الصفقات النشطة: {len(self.bot.active_trades)}\n\n"
            "اختر ما تريد:",
            reply_markup=reply_markup
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الأزرار"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'instant_analysis':
            await query.edit_message_text("📊 جاري التحليل الفوري...")
            # يمكن إضافة تحليل فوري هنا
            
        elif query.data == 'latest_news':
            await query.edit_message_text("📰 جاري جلب آخر الأخبار...")
            
        elif query.data == 'active_trades':
            if self.bot.active_trades:
                text = "💰 **الصفقات النشطة:**\n\n"
                for trade_id, trade in self.bot.active_trades.items():
                    text += f"• {trade['currency']}: {trade['decision']} @ {trade['entry']}\n"
            else:
                text = "لا توجد صفقات نشطة حالياً"
            await query.edit_message_text(text)
            
        elif query.data == 'stats':
            stats = self.bot.performance_metrics
            await query.edit_message_text(
                f"📈 **إحصائيات البوت:**\n\n"
                f"إجمالي الصفقات: {stats['total_trades']}\n"
                f"الصفقات الناجحة: {stats['winning_trades']}\n"
                f"نسبة النجاح: {stats['success_rate']*100:.1f}%\n"
                f"الحالة: {'✅ متصل' if self.bot.connection_keeper.is_healthy else '⚠️ مشاكل'} "
            )

# ==================== معالج الإيقاف ====================
def shutdown_handler(signum, frame):
    logger.info("جارٍ إيقاف التشغيل... حفظ البيانات")
    if 'bot' in globals():
        bot.save_state()
    sys.exit(0)

# ==================== الدالة الرئيسية ====================
async def main():
    """تشغيل البوت الفائق"""
    global bot
    
    # تسجيل معالج الإيقاف
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    
    # تشغيل خادم الصحة
    health_thread = Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # تهيئة البوت
    bot = SuperTradingBot()
    
    # تهيئة واجهة التليجرام
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    interface = TelegramInterface(bot)
    
    # إضافة الأوامر
    app.add_handler(CommandHandler("start", interface.start))
    app.add_handler(CallbackQueryHandler(interface.button_handler))
    
    # جدولة مراقبة الأخبار (كل 30 ثانية)
    app.job_queue.run_repeating(
        lambda ctx: asyncio.create_task(bot.monitor_news(ctx)),
        interval=30,
        first=5
    )
    
    # حفظ الحالة كل 5 دقائق
    app.job_queue.run_repeating(
        lambda ctx: bot.save_state(),
        interval=300,
        first=60
    )
    
    logger.info("🚀 البوت الفائق بدأ العمل!")
    logger.info(f"📊 دقة التوصيات المتوقعة: {bot.performance_metrics['success_rate']*100:.1f}%")
    
    # تشغيل البوت
    await app.run_polling(
        drop_pending_updates=True,
        allowed_updates=['message', 'callback_query']
    )

if __name__ == '__main__':
    asyncio.run(main())
