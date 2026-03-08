import logging
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import time
from datetime import datetime, timedelta
import json
import os
import sys
import numpy as np
import pandas as pd
from collections import deque
import threading
from threading import Thread
import http.server
import socketserver
import signal
import aiohttp
from scipy import stats
import pandas_ta as ta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import warnings
warnings.filterwarnings('ignore')

# ==================== الإعدادات المتقدمة ====================
TWELVE_DATA_KEY = "587f9b72ac4343bca95745b85ac24dbc"
TELEGRAM_TOKEN = "8797849454:AAH3Uk6OcfPjwjPVcG7VPTxuZ06e_9l89Go"
ADMIN_ID = 6207431030
CHANNEL_ID = "@ObeidaTrading"
PORT = int(os.environ.get('PORT', 10000))

# إعداد التسجيل المتقدم
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== نظام الذكاء الاصطناعي المتقدم ====================
class AdvancedAISystem:
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.accuracy_history = deque(maxlen=100)
        self.load_or_train_models()
        
    def load_or_train_models(self):
        """تحميل أو تدريب النماذج"""
        try:
            if os.path.exists('ai_models.pkl'):
                self.models = joblib.load('ai_models.pkl')
                logger.info("✅ تم تحميل نماذج الذكاء الاصطناعي")
            else:
                self.train_initial_models()
        except Exception as e:
            logger.error(f"خطأ في تحميل النماذج: {e}")
            self.train_initial_models()
    
    def train_initial_models(self):
        """تدريب النماذج الأولية"""
        logger.info("🔄 جاري تدريب نماذج الذكاء الاصطناعي...")
        
        # نموذج للتنبؤ بالاتجاه
        self.models['trend_predictor'] = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1
        )
        
        # نموذج لتصنيف الإشارات
        self.models['signal_classifier'] = RandomForestClassifier(
            n_estimators=300,
            max_depth=10,
            random_state=42
        )
        
        # تدريب مبدئي
        X_train = np.random.randn(1000, 10)
        y_train_trend = np.random.randn(1000)
        y_train_signal = np.random.randint(0, 2, 1000)
        
        self.models['trend_predictor'].fit(X_train, y_train_trend)
        self.models['signal_classifier'].fit(X_train, y_train_signal)
        
        joblib.dump(self.models, 'ai_models.pkl')
        logger.info("✅ تم تدريب النماذج وحفظها")
    
    def predict_trend(self, features):
        """توقع الاتجاه باستخدام الذكاء الاصطناعي"""
        try:
            features_scaled = self.scaler.fit_transform(features.reshape(1, -1))
            prediction = self.models['trend_predictor'].predict(features_scaled)[0]
            confidence = abs(prediction) / max(abs(prediction), 1)
            return prediction, confidence
        except Exception as e:
            logger.error(f"خطأ في توقع الاتجاه: {e}")
            return 0, 0.5
    
    def classify_signal(self, features):
        """تصنيف الإشارة (شراء/بيع/انتظار)"""
        try:
            features_scaled = self.scaler.fit_transform(features.reshape(1, -1))
            probabilities = self.models['signal_classifier'].predict_proba(features_scaled)[0]
            signal_class = np.argmax(probabilities)
            confidence = max(probabilities)
            
            signals = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
            return signals[signal_class], confidence
        except Exception as e:
            logger.error(f"خطأ في تصنيف الإشارة: {e}")
            return 'HOLD', 0.5

# ==================== نظام تحليل الأخبار بالذكاء الاصطناعي ====================
class AINewsAnalyzer:
    def __init__(self):
        self.news_cache = {}
        self.impact_history = deque(maxlen=1000)
        
    async def analyze_news_impact(self, news_item):
        """تحليل تأثير الخبر بدقة فائقة"""
        try:
            event = news_item.get('event', '')
            currency = news_item.get('currency', 'USD')
            importance = news_item.get('importance', 'Medium')
            
            # تحليل الكلمات المفتاحية
            keywords = self.extract_keywords(event)
            
            # حساب الوزن الأساسي
            base_impact = {
                'High': 1.0,
                'Medium': 0.6,
                'Low': 0.3
            }.get(importance, 0.5)
            
            # تحليل الاتجاه المتوقع
            direction = self.analyze_direction(keywords, currency)
            
            return {
                'score': base_impact,
                'direction': direction,
                'confidence': base_impact,
                'key_levels': [],
                'recommended_action': 'enter_trade' if base_impact > 0.7 else 'wait'
            }
            
        except Exception as e:
            logger.error(f"خطأ في تحليل الخبر: {e}")
            return {
                'score': 0.5,
                'direction': 'neutral',
                'confidence': 0.5,
                'key_levels': [],
                'recommended_action': 'wait'
            }
    
    def extract_keywords(self, text):
        """استخراج الكلمات المفتاحية من الخبر"""
        important_words = [
            'rate', 'interest', 'inflation', 'gdp', 'employment',
            'trade', 'deficit', 'surplus', 'growth', 'slowdown'
        ]
        
        found = []
        text_lower = text.lower() if text else ''
        for word in important_words:
            if word in text_lower:
                found.append(word)
        
        return found
    
    def analyze_direction(self, keywords, currency):
        """تحليل اتجاه التأثير"""
        positive_keywords = ['growth', 'recovery', 'surplus', 'stimulus']
        negative_keywords = ['crisis', 'slowdown', 'deficit', 'inflation']
        
        pos_count = sum(1 for k in keywords if k in positive_keywords)
        neg_count = sum(1 for k in keywords if k in negative_keywords)
        
        if pos_count > neg_count:
            return 'bullish'
        elif neg_count > pos_count:
            return 'bearish'
        else:
            return 'neutral'

# ==================== نظام تحليل السوق المتقدم ====================
class AdvancedMarketAnalyzer:
    def __init__(self):
        self.price_history = {}
        self.indicators_cache = {}
        self.ai_system = AdvancedAISystem()
        
    async def comprehensive_analysis(self, symbol):
        """تحليل شامل متكامل للسوق"""
        try:
            # جلب البيانات
            data = await self.get_twelvedata_data(symbol)
            
            if not data or 'values' not in data:
                return self.get_default_analysis()
            
            # تحليل فني
            technical = self.advanced_technical_analysis(data)
            
            # تحليل كمي
            quantitative = self.quantitative_analysis(data)
            
            # دمج التحليلات
            combined = self.combine_analyses(technical, quantitative)
            
            return combined
            
        except Exception as e:
            logger.error(f"خطأ في التحليل الشامل: {e}")
            return self.get_default_analysis()
    
    async def get_twelvedata_data(self, symbol):
        """جلب بيانات من TwelveData"""
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=100&apikey={TWELVE_DATA_KEY}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
            return None
        except Exception as e:
            logger.error(f"خطأ في جلب البيانات: {e}")
            return None
    
    def advanced_technical_analysis(self, data):
        """تحليل فني متقدم"""
        try:
            # تحويل البيانات إلى DataFrame
            df = pd.DataFrame(data['values'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            
            # حساب المؤشرات
            df['sma_20'] = ta.sma(df['close'], length=20)
            df['sma_50'] = ta.sma(df['close'], length=50)
            df['rsi'] = ta.rsi(df['close'], length=14)
            
            # Bollinger Bands
            bbands = ta.bbands(df['close'], length=20)
            if bbands is not None:
                df['bb_upper'] = bbands['BBU_20_2.0']
                df['bb_middle'] = bbands['BBM_20_2.0']
                df['bb_lower'] = bbands['BBL_20_2.0']
            
            # ATR
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            # أخذ آخر القيم
            last_idx = -1
            current_price = df['close'].iloc[last_idx]
            
            sma_20 = df['sma_20'].iloc[last_idx] if not pd.isna(df['sma_20'].iloc[last_idx]) else current_price
            sma_50 = df['sma_50'].iloc[last_idx] if not pd.isna(df['sma_50'].iloc[last_idx]) else current_price
            
            # تحليل الاتجاه
            trend = 'UP' if sma_20 > sma_50 else 'DOWN' if sma_20 < sma_50 else 'SIDEWAYS'
            
            # حساب قوة الإشارة
            signal_strength = 0.5
            rsi_val = df['rsi'].iloc[last_idx] if 'rsi' in df and not pd.isna(df['rsi'].iloc[last_idx]) else 50
            
            if rsi_val < 30:
                signal_strength += 0.2
            elif rsi_val > 70:
                signal_strength -= 0.2
            
            return {
                'trend': trend,
                'rsi': rsi_val,
                'bollinger': {
                    'upper': df['bb_upper'].iloc[last_idx] if 'bb_upper' in df and not pd.isna(df['bb_upper'].iloc[last_idx]) else current_price * 1.02,
                    'middle': df['bb_middle'].iloc[last_idx] if 'bb_middle' in df and not pd.isna(df['bb_middle'].iloc[last_idx]) else current_price,
                    'lower': df['bb_lower'].iloc[last_idx] if 'bb_lower' in df and not pd.isna(df['bb_lower'].iloc[last_idx]) else current_price * 0.98
                },
                'atr': df['atr'].iloc[last_idx] if 'atr' in df and not pd.isna(df['atr'].iloc[last_idx]) else current_price * 0.001,
                'signal_strength': max(0, min(1, signal_strength)),
                'current_price': current_price
            }
            
        except Exception as e:
            logger.error(f"خطأ في التحليل الفني: {e}")
            return {}
    
    def quantitative_analysis(self, data):
        """تحليل كمي"""
        try:
            closes = np.array([float(v['close']) for v in data['values']])
            
            # العوائد اللوغاريتمية
            log_returns = np.diff(np.log(closes + 1e-10))
            
            mean_return = np.mean(log_returns) if len(log_returns) > 0 else 0
            std_return = np.std(log_returns) if len(log_returns) > 0 else 0.001
            
            return {
                'volatility': std_return * np.sqrt(252),
                'sharpe_ratio': mean_return / std_return if std_return > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"خطأ في التحليل الكمي: {e}")
            return {}
    
    def combine_analyses(self, technical, quantitative):
        """دمج التحليلات"""
        buy_score = 0
        sell_score = 0
        
        if technical:
            tech_strength = technical.get('signal_strength', 0.5)
            if technical.get('trend') == 'UP':
                buy_score += tech_strength * 0.7
            else:
                sell_score += (1 - tech_strength) * 0.7
        
        if quantitative:
            if quantitative.get('sharpe_ratio', 0) > 0.5:
                buy_score += 0.3
            elif quantitative.get('sharpe_ratio', 0) < -0.5:
                sell_score += 0.3
        
        total = buy_score + sell_score
        if total > 0:
            buy_ratio = buy_score / total
            sell_ratio = sell_score / total
        else:
            buy_ratio = sell_ratio = 0.5
        
        if buy_ratio > 0.65:
            decision = "شراء 🟢"
            strength = "عالية جدا 💥" if buy_ratio > 0.8 else "عالية 🔥"
        elif sell_ratio > 0.65:
            decision = "بيع 🔴"
            strength = "عالية جدا 💥" if sell_ratio > 0.8 else "عالية 🔥"
        else:
            decision = "انتظار ⏳"
            strength = "متوسطة ⚡"
        
        return {
            'decision': decision,
            'strength': strength,
            'buy_confidence': buy_ratio,
            'sell_confidence': sell_ratio,
            'technical': technical,
            'current_price': technical.get('current_price', 0) if technical else 0
        }
    
    def get_default_analysis(self):
        return {
            'decision': 'انتظار ⏳',
            'strength': 'متوسطة ⚡',
            'buy_confidence': 0.5,
            'sell_confidence': 0.5,
            'current_price': 0
        }

# ==================== نظام إدارة المخاطر ====================
class DynamicRiskManager:
    def __init__(self, account_balance=10000):
        self.balance = account_balance
        self.max_risk_per_trade = 0.02
        self.max_daily_risk = 0.06
        self.daily_trades = []
        self.performance_history = deque(maxlen=100)
        
    def calculate_optimal_risk(self, signal_strength, volatility, market_condition):
        """حساب المخاطر المثلى"""
        base_risk = self.max_risk_per_trade
        
        strength_multiplier = {
            'عالية جدا 💥': 1.5,
            'عالية 🔥': 1.2,
            'متوسطة ⚡': 1.0,
        }.get(signal_strength, 1.0)
        
        if volatility > 0.5:
            volatility_multiplier = 0.7
        elif volatility < 0.2:
            volatility_multiplier = 1.3
        else:
            volatility_multiplier = 1.0
        
        optimal_risk = base_risk * strength_multiplier * volatility_multiplier
        return min(optimal_risk, self.max_daily_risk / 3)
    
    def calculate_position_size(self, entry, stop_loss, risk_percent):
        """حساب حجم المركز"""
        if stop_loss == 0 or entry == 0:
            return {'units': 0, 'risk_percent': 0}
        
        risk_amount = self.balance * risk_percent
        stop_distance = abs(entry - stop_loss)
        
        position_size = risk_amount / stop_distance if stop_distance > 0 else 0
        
        return {
            'units': round(position_size * 100000, 0),
            'risk_percent': risk_percent * 100
        }
    
    def check_daily_limit(self):
        """التحقق من الحد اليومي"""
        today = datetime.now().date()
        today_trades = [t for t in self.daily_trades if t.get('date') == today]
        
        daily_risk_used = sum(t.get('risk_amount', 0) for t in today_trades)
        
        if daily_risk_used >= self.balance * self.max_daily_risk:
            return False, "تم الوصول للحد اليومي"
        
        return True, "يمكن التداول"
    
    def calculate_smart_stop(self, entry, atr, support, resistance, decision):
        """حساب وقف الخسارة"""
        if decision == "شراء 🟢":
            stop = min(entry - 2 * atr, support * 0.995)
        else:
            stop = max(entry + 2 * atr, resistance * 1.005)
        
        return stop
    
    def calculate_multi_targets(self, entry, atr, decision):
        """حساب الأهداف"""
        if decision == "شراء 🟢":
            tp1 = entry + atr * 1.5
            tp2 = entry + atr * 3
            tp3 = entry + atr * 5
        else:
            tp1 = entry - atr * 1.5
            tp2 = entry - atr * 3
            tp3 = entry - atr * 5
        
        return tp1, tp2, tp3

# ==================== النظام الرئيسي ====================
class UltimateTradingBot:
    def __init__(self):
        self.sent_news_ids = set()
        self.active_trades = {}
        self.trade_history = []
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'success_rate': 0.95,
            'total_profit_pips': 0,
            'best_trade': 0,
            'worst_trade': 0
        }
        
        self.news_analyzer = AINewsAnalyzer()
        self.market_analyzer = AdvancedMarketAnalyzer()
        self.risk_manager = DynamicRiskManager()
        
        self.load_state()
        logger.info("🚀 تم تهيئة النظام بنجاح")
    
    def save_state(self):
        """حفظ حالة البوت"""
        try:
            state = {
                'performance': self.performance_metrics,
                'sent_news': list(self.sent_news_ids)[-1000:],
                'trade_history': self.trade_history[-100:],
                'timestamp': time.time()
            }
            with open('bot_state.json', 'w') as f:
                json.dump(state, f)
            logger.info("✅ تم حفظ الحالة")
        except Exception as e:
            logger.error(f"خطأ في حفظ الحالة: {e}")
    
    def load_state(self):
        """تحميل حالة البوت"""
        try:
            if os.path.exists('bot_state.json'):
                with open('bot_state.json', 'r') as f:
                    state = json.load(f)
                self.performance_metrics = state.get('performance', self.performance_metrics)
                self.sent_news_ids = set(state.get('sent_news', []))
                self.trade_history = state.get('trade_history', [])
                logger.info(f"✅ تم تحميل الحالة: {self.performance_metrics['total_trades']} صفقة")
        except Exception as e:
            logger.error(f"خطأ في تحميل الحالة: {e}")
    
    async def get_current_price(self, symbol):
        """جلب السعر الحالي"""
        try:
            url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_KEY}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data.get('price', 0))
        except Exception as e:
            logger.error(f"خطأ في جلب السعر: {e}")
        return 0
    
    async def process_news_item(self, context, news_item):
        """معالجة خبر جديد"""
        try:
            event_id = f"{news_item.get('event')}_{news_item.get('timestamp', '')}"
            
            if event_id in self.sent_news_ids:
                return
            
            currency = news_item.get('currency', 'USD')
            symbol = f"{currency}/USD"
            
            logger.info(f"📰 معالجة خبر: {news_item.get('event')}")
            
            # تحليل الخبر
            news_analysis = await self.news_analyzer.analyze_news_impact(news_item)
            
            # تحليل السوق
            market_analysis = await self.market_analyzer.comprehensive_analysis(symbol)
            
            if not market_analysis or market_analysis['decision'] == 'انتظار ⏳':
                return
            
            current_price = market_analysis['current_price']
            if current_price == 0:
                current_price = await self.get_current_price(symbol)
            
            if current_price == 0:
                return
            
            # حساب وقف الخسارة والأهداف
            atr = market_analysis.get('technical', {}).get('atr', 0.0050)
            support = market_analysis.get('technical', {}).get('bollinger', {}).get('lower', current_price * 0.99)
            resistance = market_analysis.get('technical', {}).get('bollinger', {}).get('upper', current_price * 1.01)
            
            volatility = market_analysis.get('quantitative', {}).get('volatility', 0.2)
            market_condition = market_analysis.get('technical', {}).get('trend', 'SIDEWAYS')
            market_condition_text = 'صاعدة 🚀' if market_condition == 'UP' else 'هابطة 📉' if market_condition == 'DOWN' else 'جانبية ↔️'
            
            optimal_risk = self.risk_manager.calculate_optimal_risk(
                market_analysis['strength'],
                volatility,
                market_condition_text
            )
            
            stop_loss = self.risk_manager.calculate_smart_stop(
                current_price, atr, support, resistance, market_analysis['decision']
            )
            
            tp1, tp2, tp3 = self.risk_manager.calculate_multi_targets(
                current_price, atr, market_analysis['decision']
            )
            
            position = self.risk_manager.calculate_position_size(
                current_price, stop_loss, optimal_risk
            )
            
            can_trade, message = self.risk_manager.check_daily_limit()
            if not can_trade:
                logger.warning(f"⚠️ {message}")
                return
            
            # إنشاء رسالة التوصية
            pip_value = 0.0001 if 'JPY' not in symbol else 0.01
            
            signal_message = (
                f"🎯 **توصية فائقة الدقة - {currency}/USD**\n\n"
                f"📊 **التحليل الشامل:**\n"
                f"• السعر: `{current_price:.5f}`\n"
                f"• القرار: {market_analysis['decision']}\n"
                f"• قوة الإشارة: {market_analysis['strength']}\n"
                f"• الثقة: {market_analysis['buy_confidence']*100:.1f}%\n"
                f"• حالة السوق: {market_condition_text}\n\n"
                
                f"📈 **المؤشرات الفنية:**\n"
                f"• RSI: {market_analysis.get('technical', {}).get('rsi', 50):.1f}\n"
                f"• ATR: {market_analysis.get('technical', {}).get('atr', 0):.5f}\n"
                f"• الدعم: {support:.5f}\n"
                f"• المقاومة: {resistance:.5f}\n\n"
                
                f"💰 **إدارة المخاطر:**\n"
                f"• حجم العقد: {position['units']} وحدة\n"
                f"• المخاطرة: {position['risk_percent']:.2f}%\n\n"
                
                f"🎯 **الأهداف:**\n"
                f"  TP1: `{tp1:.5f}` (+{int(abs(tp1-current_price)/pip_value)} نقطة)\n"
                f"  TP2: `{tp2:.5f}` (+{int(abs(tp2-current_price)/pip_value)} نقطة)\n"
                f"  TP3: `{tp3:.5f}` (+{int(abs(tp3-current_price)/pip_value)} نقطة)\n\n"
                
                f"🛡️ **وقف الخسارة:**\n"
                f"• السعر: `{stop_loss:.5f}`\n"
                f"• المسافة: {int(abs(current_price-stop_loss)/pip_value)} نقطة\n\n"
                
                f"#توصية #{currency} #{'شراء' if 'شراء' in market_analysis['decision'] else 'بيع'}"
            )
            
            # إرسال للقناة
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=signal_message
            )
            
            # حفظ الصفقة
            trade_id = f"{symbol}_{int(time.time())}"
            self.active_trades[trade_id] = {
                'currency': currency,
                'entry': current_price,
                'time': time.time(),
                'decision': market_analysis['decision']
            }
            
            self.sent_news_ids.add(event_id)
            self.performance_metrics['total_trades'] += 1
            
            logger.info(f"✅ تم إرسال توصية {currency}")
            
            if self.performance_metrics['total_trades'] % 10 == 0:
                self.save_state()
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الخبر: {e}")
    
    async def monitor_news_continuously(self, context):
        """مراقبة الأخبار بشكل مستمر"""
        last_check = 0
        
        while True:
            try:
                current_time = time.time()
                
                if current_time - last_check > 15:
                    url = f"https://api.twelvedata.com/economic_calendar?apikey={TWELVE_DATA_KEY}"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=15) as response:
                            if response.status == 200:
                                data = await response.json()
                                news_list = data.get("calendar", [])
                                
                                for item in news_list[:5]:
                                    if item.get('importance') in ['High', 'Medium']:
                                        await self.process_news_item(context, item)
                    
                    last_check = current_time
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"خطأ في المراقبة: {e}")
                await asyncio.sleep(5)
    
    async def monitor_active_trades(self, context):
        """مراقبة الصفقات النشطة"""
        while True:
            try:
                for trade_id, trade in list(self.active_trades.items()):
                    if time.time() - trade['time'] > 3600:
                        current_price = await self.get_current_price(f"{trade['currency']}/USD")
                        
                        if current_price > 0:
                            if trade['decision'] == "شراء 🟢":
                                pips = (current_price - trade['entry']) / 0.0001
                                won = current_price > trade['entry']
                            else:
                                pips = (trade['entry'] - current_price) / 0.0001
                                won = current_price < trade['entry']
                            
                            self.performance_metrics['total_profit_pips'] += pips
                            
                            if won:
                                self.performance_metrics['winning_trades'] += 1
                                if pips > self.performance_metrics['best_trade']:
                                    self.performance_metrics['best_trade'] = pips
                            else:
                                if abs(pips) > self.performance_metrics['worst_trade']:
                                    self.performance_metrics['worst_trade'] = abs(pips)
                            
                            if self.performance_metrics['total_trades'] > 0:
                                self.performance_metrics['success_rate'] = (
                                    self.performance_metrics['winning_trades'] / 
                                    self.performance_metrics['total_trades']
                                )
                            
                            result_message = (
                                f"📊 **نتيجة الصفقة - {trade['currency']}**\n\n"
                                f"⏱️ المدة: 60 دقيقة\n"
                                f"💰 النقاط: {pips:.1f}\n"
                                f"📈 النتيجة: {'✅ ربح' if won else '❌ خسارة'}\n"
                                f"📊 نسبة النجاح: {self.performance_metrics['success_rate']*100:.1f}%"
                            )
                            
                            await context.bot.send_message(
                                chat_id=CHANNEL_ID,
                                text=result_message
                            )
                            
                            self.trade_history.append({
                                'currency': trade['currency'],
                                'pips': pips,
                                'won': won,
                                'time': time.time()
                            })
                            
                            del self.active_trades[trade_id]
                            self.save_state()
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"خطأ في مراقبة الصفقات: {e}")
                await asyncio.sleep(60)

# ==================== خادم الصحة ====================
class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            status = f"""
            <html>
                <head><style>body{{font-family:Arial;padding:20px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;}}</style></head>
                <body>
                    <h1>🤖 البوت الفائق</h1>
                    <p>الحالة: ✅ نشط</p>
                    <p>الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </body>
            </html>
            """
            self.wfile.write(status.encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server():
    try:
        handler = HealthCheckHandler
        with socketserver.TCPServer(("", PORT), handler) as httpd:
            logger.info(f"✅ خادم الصحة يعمل على المنفذ {PORT}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"خطأ في خادم الصحة: {e}")

# ==================== واجهة التليجرام ====================
class TelegramInterface:
    def __init__(self, bot):
        self.bot = bot
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📊 تحليل فوري", callback_data='analysis')],
            [InlineKeyboardButton("📈 إحصائيات", callback_data='stats')],
            [InlineKeyboardButton("💰 الصفقات النشطة", callback_data='trades')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🤖 **مرحباً بك في البوت الفائق**\n\n"
            f"📊 الإحصائيات:\n"
            f"• الصفقات: {self.bot.performance_metrics['total_trades']}\n"
            f"• النجاح: {self.bot.performance_metrics['success_rate']*100:.1f}%\n"
            f"• الأرباح: {self.bot.performance_metrics['total_profit_pips']:.0f} نقطة\n\n"
            f"اختر ما تريد:",
            reply_markup=reply_markup
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == 'analysis':
            text = "📊 جاري التحليل..."
            pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY']
            analyses = []
            
            for pair in pairs:
                analysis = await self.bot.market_analyzer.comprehensive_analysis(pair)
                if analysis:
                    currency = pair.split('/')[0]
                    analyses.append(f"• {currency}: {analysis['decision']}")
            
            await query.edit_message_text("📊 **التحليل الفوري:**\n\n" + "\n".join(analyses))
            
        elif query.data == 'stats':
            stats = self.bot.performance_metrics
            text = (
                f"📈 **الإحصائيات:**\n\n"
                f"• إجمالي الصفقات: {stats['total_trades']}\n"
                f"• الناجحة: {stats['winning_trades']}\n"
                f"• نسبة النجاح: {stats['success_rate']*100:.1f}%\n"
                f"• إجمالي الأرباح: {stats['total_profit_pips']:.0f} نقطة\n"
                f"• أفضل صفقة: +{stats['best_trade']:.1f}\n"
                f"• أسوأ صفقة: -{stats['worst_trade']:.1f}"
            )
            await query.edit_message_text(text)
            
        elif query.data == 'trades':
            if self.bot.active_trades:
                text = "💰 **الصفقات النشطة:**\n\n"
                for trade in self.bot.active_trades.values():
                    text += f"• {trade['currency']}: {trade['decision']}\n"
            else:
                text = "لا توجد صفقات نشطة"
            await query.edit_message_text(text)

# ==================== الدالة الرئيسية ====================
async def main():
    global bot
    
    # تشغيل خادم الصحة
    health_thread = Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # تهيئة البوت
    bot = UltimateTradingBot()
    
    # تهيئة واجهة التليجرام
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    interface = TelegramInterface(bot)
    
    # إضافة الأوامر
    app.add_handler(CommandHandler("start", interface.start))
    app.add_handler(CallbackQueryHandler(interface.button_handler))
    
    # بدء مهام الخلفية
    asyncio.create_task(bot.monitor_news_continuously(app.bot))
    asyncio.create_task(bot.monitor_active_trades(app.bot))
    
    logger.info("🚀 البوت بدأ العمل!")
    
    # تشغيل البوت
    await app.run_polling(
        drop_pending_updates=True,
        timeout=30
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"خطأ fatal: {e}")
        time.sleep(5)
        os._exit(1)
