import requests
import time
import json
import os
import logging
from datetime import datetime, timedelta
from threading import Thread
import sys
import hashlib
import hmac
from collections import defaultdict
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple
import random

# --- الإعدادات الأساسية ---
CRYPTONEWS_KEY = 'J6iiywynmkxu8ja7gkhltnpnfvgrxxqagsj6o8fi'
TELEGRAM_TOKEN = '8797849454:AAH3Uk6OcfPjwjPVcG7VPTxuZ06e_9l89Go'
CHANNEL_USERNAME = '@ObeidaTrading'
CHANNEL_LINK = 'https://t.me/ObeidaTrading'
ADMIN_IDS = [6207431030]  # ضع معرف المشرف هنا

# --- ملفات البيانات ---
USERS_FILE = 'bot_users.json'
BANNED_USERS_FILE = 'banned_users.json'
CHANNELS_FILE = 'required_channels.json'
STATS_FILE = 'bot_stats.json'
LOG_FILE = 'bot_activity.log'
ADMIN_PANEL_FILE = 'admin_panel.json'
SIGNALS_HISTORY_FILE = 'signals_history.json'
USER_FEEDBACK_FILE = 'user_feedback.json'
ANALYTICS_FILE = 'analytics.json'
SCHEDULED_POSTS_FILE = 'scheduled_posts.json'
ECONOMIC_CALENDAR_FILE = 'economic_calendar.json'
LEADERBOARD_FILE = 'leaderboard.json'
REFERRALS_FILE = 'referrals.json'
ALERTS_FILE = 'alerts.json'
PRICE_ALERTS_FILE = 'price_alerts.json'
PORTFOLIO_FILE = 'portfolio.json'
EDUCATION_FILE = 'education.json'
SIGNAL_PERFORMANCE_FILE = 'signal_performance.json'

# --- إعداد التسجيل المحسن ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- إعدادات البوت المتقدمة ---
BOT_CONFIG = {
    'CHECK_INTERVAL': 3,  # فحص كل 3 ثواني
    'NEWS_CHECK_INTERVAL': 10,  # فحص الأخبار كل 10 ثواني
    'REPORT_INTERVAL': 30,  # تقرير كل 30 ثانية
    'MAX_RETRIES': 3,
    'TIMEOUT': 15,
    'BATCH_SIZE': 50,  # عدد الرسائل في الدفعة الواحدة
    'RATE_LIMIT': 20,  # رسالة في الثانية
    'CACHE_TTL': 300,  # تخزين مؤقت لمدة 5 دقائق
    'MIN_CONFIDENCE': 0.7,  # الحد الأدنى للثقة في الإشارة
    'MAX_SIGNALS_PER_DAY': 10,  # الحد الأقصى للإشارات يومياً
    'PREMIUM_FEATURES': True,  # تفعيل الميزات المدفوعة
    'DEMO_MODE': False,  # وضع التجربة
    'MAINTENANCE_MODE': False,  # وضع الصيانة
}

# --- قنوات موصى بها للاشتراك الإضافي (اختياري) ---
RECOMMENDED_CHANNELS = [
    {'name': 'Binance Announcements', 'link': 'https://t.me/binance_announcements'},
    {'name': 'CoinMarketCap', 'link': 'https://t.me/CoinMarketCap'},
    {'name': 'TradingView', 'link': 'https://t.me/tradingview'},
]

# --- دوال مساعدة متقدمة لإدارة الملفات ---
def load_json(file_path, default=None):
    """تحميل البيانات من ملف JSON مع معالجة الأخطاء"""
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default if default is not None else {}
    except json.JSONDecodeError as e:
        logger.error(f"خطأ في تنسيق JSON في {file_path}: {e}")
        # عمل نسخة احتياطية من الملف التالف
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(file_path, backup_path)
            logger.info(f"تم إنشاء نسخة احتياطية من الملف التالف: {backup_path}")
        return default if default is not None else {}
    except Exception as e:
        logger.error(f"خطأ في قراءة {file_path}: {e}")
        return default if default is not None else {}

def save_json(file_path, data, backup=True):
    """حفظ البيانات في ملف JSON مع إنشاء نسخة احتياطية"""
    try:
        # إنشاء نسخة احتياطية إذا كان الملف موجوداً
        if backup and os.path.exists(file_path):
            backup_path = f"{file_path}.backup"
            import shutil
            shutil.copy2(file_path, backup_path)
        
        # حفظ البيانات
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        return True
    except Exception as e:
        logger.error(f"خطأ في حفظ {file_path}: {e}")
        return False

# --- تهيئة جميع الملفات ---
def initialize_all_files():
    """إنشاء جميع الملفات المطلوبة إذا لم تكن موجودة"""
    
    files_config = {
        USERS_FILE: {},
        BANNED_USERS_FILE: [],
        CHANNELS_FILE: [CHANNEL_USERNAME],
        STATS_FILE: {
            'total_signals': 0,
            'total_users': 0,
            'total_premium_users': 0,
            'total_referrals': 0,
            'last_signal_time': None,
            'signals_today': 0,
            'successful_signals': 0,
            'failed_signals': 0,
            'pending_signals': 0,
            'accuracy_rate': 0,
            'total_profit': 0,
            'total_loss': 0,
            'date_reset': str(datetime.now().date()),
            'bot_start_time': datetime.now().isoformat(),
            'last_check_time': None,
            'last_news': None,
            'api_calls_today': 0,
            'messages_sent_today': 0,
            'uptime': 0,
        },
        ADMIN_PANEL_FILE: {
            'notifications_enabled': True,
            'last_report_time': None,
            'report_interval': 30,
            'auto_restart': True,
            'debug_mode': False,
            'maintenance_message': None,
            'feature_flags': {
                'signals': True,
                'news': True,
                'alerts': True,
                'portfolio': True,
                'education': True,
                'leaderboard': True,
                'referrals': True,
            }
        },
        SIGNALS_HISTORY_FILE: [],
        USER_FEEDBACK_FILE: {},
        ANALYTICS_FILE: {
            'daily_users': [],
            'daily_signals': [],
            'popular_pairs': {},
            'best_performing': {},
            'user_activity': {},
            'peak_hours': defaultdict(int),
            'referral_stats': {},
        },
        SCHEDULED_POSTS_FILE: [],
        ECONOMIC_CALENDAR_FILE: [],
        LEADERBOARD_FILE: {
            'daily': [],
            'weekly': [],
            'monthly': [],
            'all_time': [],
            'last_update': None,
        },
        REFERRALS_FILE: {},
        ALERTS_FILE: {},
        PRICE_ALERTS_FILE: {},
        PORTFOLIO_FILE: {},
        EDUCATION_FILE: {
            'articles': [],
            'videos': [],
            'courses': [],
            'tips': [],
            'faq': [],
        },
        SIGNAL_PERFORMANCE_FILE: {
            'total_signals': 0,
            'successful': 0,
            'failed': 0,
            'average_profit': 0,
            'average_loss': 0,
            'best_signal': None,
            'worst_signal': None,
            'performance_by_pair': {},
        }
    }
    
    for file_path, default_content in files_config.items():
        if not os.path.exists(file_path):
            save_json(file_path, default_content)
            logger.info(f"تم إنشاء ملف: {file_path}")

initialize_all_files()

# --- نظام التخزين المؤقت المتقدم ---
class Cache:
    """نظام تخزين مؤقت للبيانات"""
    
    def __init__(self, ttl=BOT_CONFIG['CACHE_TTL']):
        self.cache = {}
        self.ttl = ttl
        self.timestamps = {}
    
    def get(self, key):
        """الحصول على قيمة من التخزين المؤقت"""
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.ttl:
                return self.cache[key]
            else:
                self.delete(key)
        return None
    
    def set(self, key, value):
        """تخزين قيمة في التخزين المؤقت"""
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def delete(self, key):
        """حذف قيمة من التخزين المؤقت"""
        if key in self.cache:
            del self.cache[key]
            del self.timestamps[key]
    
    def clear(self):
        """مسح التخزين المؤقت"""
        self.cache.clear()
        self.timestamps.clear()

cache = Cache()

# --- نظام الإحصائيات المتقدم ---
class Statistics:
    """نظام متقدم للإحصائيات والتحليلات"""
    
    @staticmethod
    def update_user_activity(user_id, action):
        """تحديث نشاط المستخدم"""
        try:
            analytics = load_json(ANALYTICS_FILE, {})
            
            if 'user_activity' not in analytics:
                analytics['user_activity'] = {}
            
            user_id_str = str(user_id)
            if user_id_str not in analytics['user_activity']:
                analytics['user_activity'][user_id_str] = {
                    'first_seen': datetime.now().isoformat(),
                    'last_seen': datetime.now().isoformat(),
                    'actions_count': 0,
                    'actions': [],
                    'total_time': 0,
                }
            
            user_data = analytics['user_activity'][user_id_str]
            user_data['last_seen'] = datetime.now().isoformat()
            user_data['actions_count'] += 1
            
            # تسجيل آخر 10 إجراءات فقط
            user_data['actions'].append({
                'action': action,
                'time': datetime.now().isoformat()
            })
            if len(user_data['actions']) > 10:
                user_data['actions'] = user_data['actions'][-10:]
            
            # تحديث ساعات الذروة
            hour = datetime.now().hour
            if 'peak_hours' not in analytics:
                analytics['peak_hours'] = {}
            analytics['peak_hours'][str(hour)] = analytics['peak_hours'].get(str(hour), 0) + 1
            
            save_json(ANALYTICS_FILE, analytics)
            
        except Exception as e:
            logger.error(f"خطأ في تحديث نشاط المستخدم: {e}")
    
    @staticmethod
    def track_signal_performance(signal_data, result):
        """تتبع أداء الإشارات"""
        try:
            performance = load_json(SIGNAL_PERFORMANCE_FILE, {})
            
            performance['total_signals'] = performance.get('total_signals', 0) + 1
            
            if result.get('success'):
                performance['successful'] = performance.get('successful', 0) + 1
                performance['average_profit'] = (
                    (performance.get('average_profit', 0) * (performance['successful'] - 1) + 
                     result.get('profit', 0)) / performance['successful']
                )
            else:
                performance['failed'] = performance.get('failed', 0) + 1
                performance['average_loss'] = (
                    (performance.get('average_loss', 0) * (performance['failed'] - 1) + 
                     abs(result.get('loss', 0))) / performance['failed']
                )
            
            # تحديث أداء كل زوج
            pair = signal_data.get('symbol', 'UNKNOWN')
            if pair not in performance['performance_by_pair']:
                performance['performance_by_pair'][pair] = {
                    'signals': 0,
                    'successful': 0,
                    'failed': 0,
                    'total_profit': 0,
                }
            
            pair_stats = performance['performance_by_pair'][pair]
            pair_stats['signals'] += 1
            if result.get('success'):
                pair_stats['successful'] += 1
                pair_stats['total_profit'] += result.get('profit', 0)
            else:
                pair_stats['failed'] += 1
            
            # تحديث أفضل وأسوأ إشارة
            if result.get('success'):
                if not performance.get('best_signal') or result.get('profit', 0) > performance['best_signal'].get('profit', 0):
                    performance['best_signal'] = {
                        'signal': signal_data,
                        'profit': result.get('profit', 0),
                        'date': datetime.now().isoformat()
                    }
            else:
                if not performance.get('worst_signal') or abs(result.get('loss', 0)) > abs(performance['worst_signal'].get('loss', 0)):
                    performance['worst_signal'] = {
                        'signal': signal_data,
                        'loss': result.get('loss', 0),
                        'date': datetime.now().isoformat()
                    }
            
            save_json(SIGNAL_PERFORMANCE_FILE, performance)
            
        except Exception as e:
            logger.error(f"خطأ في تتبع أداء الإشارة: {e}")
    
    @staticmethod
    def calculate_accuracy():
        """حساب دقة الإشارات"""
        try:
            performance = load_json(SIGNAL_PERFORMANCE_FILE, {})
            total = performance.get('total_signals', 0)
            if total == 0:
                return 0
            
            successful = performance.get('successful', 0)
            return (successful / total) * 100
        except:
            return 0

# --- نظام إدارة المستخدمين المتقدم ---
class UserManager:
    """نظام متقدم لإدارة المستخدمين"""
    
    @staticmethod
    def get_user(user_id):
        """الحصول على بيانات المستخدم"""
        users = load_json(USERS_FILE, {})
        return users.get(str(user_id))
    
    @staticmethod
    def update_user(user_id, **kwargs):
        """تحديث بيانات المستخدم"""
        try:
            users = load_json(USERS_FILE, {})
            user_id_str = str(user_id)
            
            if user_id_str not in users:
                users[user_id_str] = {
                    'id': user_id,
                    'joined_date': datetime.now().isoformat(),
                    'last_active': datetime.now().isoformat(),
                    'signals_received': 0,
                    'signals_taken': 0,
                    'successful_trades': 0,
                    'total_profit': 0,
                    'premium': False,
                    'premium_until': None,
                    'referrals': [],
                    'referral_code': UserManager.generate_referral_code(user_id),
                    'settings': {
                        'notifications': True,
                        'language': 'ar',
                        'risk_level': 'medium',
                        'preferred_pairs': [],
                    },
                    'stats': {
                        'messages_received': 0,
                        'commands_used': 0,
                        'last_command': None,
                        'active_days': 0,
                    }
                }
            
            user = users[user_id_str]
            for key, value in kwargs.items():
                if key in user:
                    user[key] = value
                elif key in user['settings']:
                    user['settings'][key] = value
                elif key in user['stats']:
                    user['stats'][key] = value
            
            user['last_active'] = datetime.now().isoformat()
            
            save_json(USERS_FILE, users)
            Statistics.update_user_activity(user_id, 'update')
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تحديث المستخدم: {e}")
            return False
    
    @staticmethod
    def generate_referral_code(user_id):
        """توليد كود إحالة فريد"""
        import hashlib
        import base64
        
        # إنشاء كود فريد من معرف المستخدم والوقت
        unique_string = f"{user_id}_{datetime.now().timestamp()}"
        hash_object = hashlib.sha256(unique_string.encode())
        hash_hex = hash_object.hexdigest()[:8]
        
        # تحويل إلى كود سهل القراءة
        code = base64.b32encode(hash_hex.encode()).decode()[:8].upper()
        return code
    
    @staticmethod
    def add_referral(user_id, referral_code):
        """إضافة إحالة جديدة"""
        try:
            # البحث عن المستخدم الذي يملك هذا الكود
            users = load_json(USERS_FILE, {})
            referrer_id = None
            
            for uid, data in users.items():
                if data.get('referral_code') == referral_code:
                    referrer_id = uid
                    break
            
            if referrer_id and str(user_id) != referrer_id:
                # إضافة الإحالة
                referrals = load_json(REFERRALS_FILE, {})
                
                if referrer_id not in referrals:
                    referrals[referrer_id] = []
                
                # التحقق من عدم تكرار الإحالة
                if str(user_id) not in [r.get('user_id') for r in referrals[referrer_id]]:
                    referrals[referrer_id].append({
                        'user_id': str(user_id),
                        'date': datetime.now().isoformat(),
                        'status': 'pending',
                        'rewards': 0
                    })
                    
                    save_json(REFERRALS_FILE, referrals)
                    
                    # تحديث إحصائيات المحول
                    stats = load_json(STATS_FILE, {})
                    stats['total_referrals'] = stats.get('total_referrals', 0) + 1
                    save_json(STATS_FILE, stats)
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"خطأ في إضافة إحالة: {e}")
            return False
    
    @staticmethod
    def check_premium(user_id):
        """التحقق من صلاحية الاشتراك المميز"""
        user = UserManager.get_user(user_id)
        if not user:
            return False
        
        premium_until = user.get('premium_until')
        if not premium_until:
            return False
        
        try:
            expiry = datetime.fromisoformat(premium_until)
            return datetime.now() < expiry
        except:
            return False
    
    @staticmethod
    def get_user_stats(user_id):
        """الحصول على إحصائيات المستخدم"""
        user = UserManager.get_user(user_id)
        if not user:
            return None
        
        # حساب النشاط
        joined = datetime.fromisoformat(user['joined_date'])
        days_active = (datetime.now() - joined).days
        
        # حساب الدقة
        accuracy = 0
        if user.get('signals_taken', 0) > 0:
            accuracy = (user.get('successful_trades', 0) / user['signals_taken']) * 100
        
        # حساب الأرباح
        profit_loss = user.get('total_profit', 0)
        
        return {
            'joined_days': days_active,
            'signals_received': user.get('signals_received', 0),
            'signals_taken': user.get('signals_taken', 0),
            'successful_trades': user.get('successful_trades', 0),
            'accuracy': accuracy,
            'profit_loss': profit_loss,
            'premium': UserManager.check_premium(user_id),
            'referrals_count': len(user.get('referrals', [])),
            'last_active': user.get('last_active'),
        }

# --- نظام الأخبار المتقدم ---
class NewsManager:
    """نظام متقدم لإدارة الأخبار"""
    
    def __init__(self):
        self.last_news = None
        self.news_history = []
        self.api_calls_today = 0
        self.last_api_reset = datetime.now().date()
    
    def get_latest_news(self) -> Optional[Dict]:
        """جلب آخر الأخبار مع تحسينات"""
        
        # التحقق من حد الاستخدام اليومي
        if datetime.now().date() != self.last_api_reset:
            self.api_calls_today = 0
            self.last_api_reset = datetime.now().date()
        
        if self.api_calls_today >= 1000:  # حد آمن
            logger.warning("تم الوصول للحد الأقصى من استدعاءات API")
            return None
        
        url = f"https://cryptonews-api.com/api/v1"
        params = {
            'items': 10,
            'token': CRYPTONEWS_KEY,
            'type': 'news',
            'source': 'cointelegraph,coindesk,decrypt,bitcoinist,newsbtc',
            'sentiment': 'positive,negative',
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        try:
            response = requests.get(url, params=params, timeout=BOT_CONFIG['TIMEOUT'])
            self.api_calls_today += 1
            
            # تحديث إحصائيات API
            stats = load_json(STATS_FILE, {})
            stats['api_calls_today'] = stats.get('api_calls_today', 0) + 1
            save_json(STATS_FILE, stats)
            
            if response.status_code == 200:
                data = response.json()
                
                if data and 'data' in data and len(data['data']) > 0:
                    news_list = data['data']
                    
                    # تحليل وتقييم الأخبار
                    analyzed_news = []
                    for news in news_list:
                        analysis = self.analyze_news(news)
                        if analysis:
                            analyzed_news.append(analysis)
                    
                    if analyzed_news:
                        # اختيار أفضل خبر بناءً على التحليل
                        best_news = max(analyzed_news, key=lambda x: x['score'])
                        
                        # تحديث التاريخ
                        self.news_history.append(best_news)
                        if len(self.news_history) > 100:  # الاحتفاظ بآخر 100 خبر
                            self.news_history.pop(0)
                        
                        return best_news
            
            return None
            
        except requests.exceptions.Timeout:
            logger.error("Timeout في جلب الأخبار")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("خطأ في الاتصال بمنصة الأخبار")
            return None
        except Exception as e:
            logger.error(f"خطأ في جلب الأخبار: {e}")
            return None
    
    def analyze_news(self, news: Dict) -> Optional[Dict]:
        """تحليل الخبر وتقييمه"""
        try:
            title = news.get('title', '')
            sentiment = news.get('sentiment', 'Neutral')
            tickers = news.get('tickers', [])
            source = news.get('source', '')
            date = news.get('date', '')
            
            # حساب score الخبر
            score = 0
            
            # وزن المشاعر
            if sentiment == 'Positive':
                score += 10
            elif sentiment == 'Negative':
                score += 8
            else:
                score += 3
            
            # وزن المصدر
            trusted_sources = ['cointelegraph', 'coindesk', 'decrypt', 'bloomberg', 'reuters']
            if any(s in source.lower() for s in trusted_sources):
                score += 5
            
            # طول العنوان (العناوين الأطول غالباً أكثر تفصيلاً)
            if len(title) > 50:
                score += 2
            
            # وجود تيكرات
            if tickers:
                score += len(tickers) * 2
            
            # تاريخ الخبر
            if date:
                try:
                    news_time = datetime.fromisoformat(date.replace('Z', '+00:00'))
                    time_diff = datetime.now() - news_time
                    if time_diff.total_seconds() < 3600:  # أقل من ساعة
                        score += 10
                    elif time_diff.total_seconds() < 7200:  # أقل من ساعتين
                        score += 5
                except:
                    pass
            
            return {
                'title': title,
                'sentiment': sentiment,
                'symbol': tickers[0] if tickers else 'BTC',
                'source': source,
                'time': date,
                'score': score,
                'tickers': tickers[:3],  # أول 3 تيكرات فقط
                'summary': self.generate_summary(news)
            }
            
        except Exception as e:
            logger.error(f"خطأ في تحليل الخبر: {e}")
            return None
    
    def generate_summary(self, news: Dict) -> str:
        """توليد ملخص للخبر"""
        title = news.get('title', '')
        if len(title) > 100:
            return title[:100] + '...'
        return title
    
    def get_news_history(self, limit: int = 10) -> List[Dict]:
        """الحصول على تاريخ الأخبار"""
        return self.news_history[-limit:]
    
    def get_news_stats(self) -> Dict:
        """الحصول على إحصائيات الأخبار"""
        if not self.news_history:
            return {}
        
        stats = {
            'total_news': len(self.news_history),
            'positive': 0,
            'negative': 0,
            'neutral': 0,
            'top_sources': {},
            'top_symbols': {},
        }
        
        for news in self.news_history:
            # إحصائيات المشاعر
            sentiment = news.get('sentiment', 'Neutral')
            stats[sentiment.lower()] = stats.get(sentiment.lower(), 0) + 1
            
            # إحصائيات المصادر
            source = news.get('source', 'Unknown')
            stats['top_sources'][source] = stats['top_sources'].get(source, 0) + 1
            
            # إحصائيات الرموز
            symbol = news.get('symbol', 'BTC')
            stats['top_symbols'][symbol] = stats['top_symbols'].get(symbol, 0) + 1
        
        # ترتيب المصادر والرموز
        stats['top_sources'] = dict(sorted(stats['top_sources'].items(), key=lambda x: x[1], reverse=True)[:5])
        stats['top_symbols'] = dict(sorted(stats['top_symbols'].items(), key=lambda x: x[1], reverse=True)[:5])
        
        return stats

news_manager = NewsManager()

# --- نظام تحليل السوق المتقدم ---
class MarketAnalyzer:
    """نظام متقدم لتحليل السوق"""
    
    def __init__(self):
        self.supported_pairs = ['BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'DOT', 'LINK', 'MATIC', 'AVAX', 'UNI']
        self.timeframes = ['1h', '4h', '1d', '1w']
        self.indicators = ['RSI', 'MACD', 'MA', 'BB', 'Volume']
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """الحصول على بيانات السوق"""
        try:
            # بيانات 24 ساعة
            url_24h = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
            response_24h = requests.get(url_24h, timeout=BOT_CONFIG['TIMEOUT'])
            
            # بيانات اللحظية
            url_price = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
            response_price = requests.get(url_price, timeout=BOT_CONFIG['TIMEOUT'])
            
            if response_24h.status_code == 200 and response_price.status_code == 200:
                data_24h = response_24h.json()
                data_price = response_price.json()
                
                # حساب القيم
                price = float(data_price['price'])
                high = float(data_24h['highPrice'])
                low = float(data_24h['lowPrice'])
                volume = float(data_24h['volume'])
                quote_volume = float(data_24h['quoteVolume'])
                price_change = float(data_24h['priceChangePercent'])
                
                # حساب مؤشرات إضافية
                volatility = ((high - low) / price) * 100
                volume_ratio = volume / (quote_volume / price) if quote_volume > 0 else 1
                
                return {
                    'symbol': symbol,
                    'price': price,
                    'high_24h': high,
                    'low_24h': low,
                    'volume_24h': volume,
                    'quote_volume_24h': quote_volume,
                    'price_change_24h': price_change,
                    'volatility': volatility,
                    'volume_ratio': volume_ratio,
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"خطأ في تحليل {symbol}: {e}")
            return None
    
    def calculate_technical_indicators(self, symbol: str) -> Optional[Dict]:
        """حساب المؤشرات الفنية"""
        try:
            # جلب بيانات الشموع
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': f"{symbol}USDT",
                'interval': '1h',
                'limit': 100
            }
            
            response = requests.get(url, params=params, timeout=BOT_CONFIG['TIMEOUT'])
            
            if response.status_code == 200:
                candles = response.json()
                
                # استخراج بيانات الإغلاق
                closes = [float(c[4]) for c in candles]
                highs = [float(c[2]) for c in candles]
                lows = [float(c[3]) for c in candles]
                volumes = [float(c[5]) for c in candles]
                
                # حساب RSI
                rsi = self.calculate_rsi(closes)
                
                # حساب MACD
                macd, signal, hist = self.calculate_macd(closes)
                
                # حساب المتوسطات المتحركة
                ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
                ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
                ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None
                
                # حساب Bollinger Bands
                bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(closes)
                
                # حساب الدعم والمقاومة
                support, resistance = self.calculate_support_resistance(highs, lows)
                
                return {
                    'rsi': rsi,
                    'macd': {
                        'macd': macd,
                        'signal': signal,
                        'histogram': hist
                    },
                    'moving_averages': {
                        'ma20': ma20,
                        'ma50': ma50,
                        'ma200': ma200
                    },
                    'bollinger_bands': {
                        'upper': bb_upper,
                        'middle': bb_middle,
                        'lower': bb_lower
                    },
                    'support_resistance': {
                        'support': support,
                        'resistance': resistance
                    },
                    'trend': self.determine_trend(closes)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"خطأ في حساب المؤشرات لـ {symbol}: {e}")
            return None
    
    def calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """حساب مؤشر RSI"""
        if len(closes) < period + 1:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, closes: List[float]) -> Tuple[float, float, float]:
        """حساب مؤشر MACD"""
        if len(closes) < 26:
            return 0, 0, 0
        
        # حساب EMA12 و EMA26
        ema12 = self.calculate_ema(closes, 12)
        ema26 = self.calculate_ema(closes, 26)
        
        if ema12 is None or ema26 is None:
            return 0, 0, 0
        
        macd = ema12 - ema26
        
        # حساب Signal line (EMA9 of MACD)
        # هذه طريقة مبسطة، للأفضل يمكن حساب سلسلة MACD أولاً
        signal = macd * 0.9  # تقريب
        
        histogram = macd - signal
        
        return macd, signal, histogram
    
    def calculate_ema(self, closes: List[float], period: int) -> Optional[float]:
        """حساب المتوسط المتحرك الأسي"""
        if len(closes) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = closes[-period]
        
        for price in closes[-period+1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def calculate_bollinger_bands(self, closes: List[float], period: int = 20, std_dev: int = 2) -> Tuple[float, float, float]:
        """حساب Bollinger Bands"""
        if len(closes) < period:
            return closes[-1], closes[-1], closes[-1]
        
        # المتوسط المتحرك
        ma = sum(closes[-period:]) / period
        
        # الانحراف المعياري
        variance = sum((x - ma) ** 2 for x in closes[-period:]) / period
        std = variance ** 0.5
        
        upper = ma + (std * std_dev)
        lower = ma - (std * std_dev)
        
        return upper, ma, lower
    
    def calculate_support_resistance(self, highs: List[float], lows: List[float]) -> Tuple[float, float]:
        """حساب مستويات الدعم والمقاومة"""
        if not highs or not lows:
            return 0, 0
        
        # مستويات بسيطة: أعلى قمة وآخر قاع
        resistance = max(highs[-20:]) if len(highs) >= 20 else max(highs)
        support = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        
        return support, resistance
    
    def determine_trend(self, closes: List[float]) -> str:
        """تحديد اتجاه السوق"""
        if len(closes) < 50:
            return "غير واضح"
        
        # مقارنة المتوسطات
        ma20 = sum(closes[-20:]) / 20
        ma50 = sum(closes[-50:]) / 50
        ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else ma50
        
        current_price = closes[-1]
        
        if current_price > ma20 > ma50:
            return "صاعد قوي"
        elif current_price > ma20 and ma20 > ma50:
            return "صاعد"
        elif current_price < ma20 < ma50:
            return "هابط قوي"
        elif current_price < ma20 and ma20 < ma50:
            return "هابط"
        else:
            return "جانبي"

market_analyzer = MarketAnalyzer()

# --- نظام الإشارات المتقدم ---
class SignalGenerator:
    """نظام متقدم لتوليد الإشارات"""
    
    def __init__(self):
        self.signals_today = 0
        self.last_signal_date = datetime.now().date()
        self.signals_history = load_json(SIGNALS_HISTORY_FILE, [])
    
    def generate_signal(self, news: Dict, market: Dict, technical: Dict) -> Optional[Dict]:
        """توليد إشارة متكاملة"""
        
        # التحقق من حد الإشارات اليومي
        if datetime.now().date() != self.last_signal_date:
            self.signals_today = 0
            self.last_signal_date = datetime.now().date()
        
        if self.signals_today >= BOT_CONFIG['MAX_SIGNALS_PER_DAY']:
            logger.warning("تم الوصول للحد الأقصى من الإشارات اليومية")
            return None
        
        # حساب الثقة في الإشارة
        confidence = self.calculate_confidence(news, market, technical)
        
        if confidence < BOT_CONFIG['MIN_CONFIDENCE']:
            logger.info(f"ثقة منخفضة للإشارة: {confidence}")
            return None
        
        # تحديد نوع الصفقة
        trade_type = "شراء BUY 📈" if news['sentiment'] == 'Positive' else "بيع SELL 📉"
        
        # حساب الأهداف المتقدمة
        entry = market['price']
        atr = self.calculate_atr(technical)  # Average True Range
        
        if news['sentiment'] == 'Positive':
            tp1 = entry * 1.015  # 1.5%
            tp2 = entry * 1.03   # 3%
            tp3 = entry * 1.05   # 5%
            sl = entry * 0.985   # 1.5%
        else:
            tp1 = entry * 0.985
            tp2 = entry * 0.97
            tp3 = entry * 0.95
            sl = entry * 1.015
        
        # ضبط الأهداف بناءً على ATR
        if atr:
            tp1 = entry + (atr * 1.5) if news['sentiment'] == 'Positive' else entry - (atr * 1.5)
            tp2 = entry + (atr * 3) if news['sentiment'] == 'Positive' else entry - (atr * 3)
            tp3 = entry + (atr * 5) if news['sentiment'] == 'Positive' else entry - (atr * 5)
            sl = entry - (atr * 1.5) if news['sentiment'] == 'Positive' else entry + (atr * 1.5)
        
        # تحليل إضافي
        risk_reward = abs(tp1 - entry) / abs(sl - entry) if sl != entry else 1
        
        signal = {
            'id': self.generate_signal_id(),
            'timestamp': datetime.now().isoformat(),
            'symbol': news['symbol'],
            'type': trade_type,
            'sentiment': news['sentiment'],
            'entry': entry,
            'take_profit': {
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3
            },
            'stop_loss': sl,
            'confidence': confidence,
            'risk_reward': risk_reward,
            'market_data': {
                'price_change_24h': market['price_change_24h'],
                'volume_24h': market['volume_24h'],
                'volatility': market['volatility']
            },
            'technical_indicators': technical,
            'news': {
                'title': news['title'][:100],
                'source': news['source'],
                'time': news['time']
            },
            'recommendation': self.generate_recommendation(confidence, risk_reward),
            'risk_level': self.determine_risk_level(technical)
        }
        
        # حفظ الإشارة
        self.signals_history.append(signal)
        if len(self.signals_history) > 1000:
            self.signals_history = self.signals_history[-1000:]
        
        save_json(SIGNALS_HISTORY_FILE, self.signals_history)
        self.signals_today += 1
        
        return signal
    
    def calculate_confidence(self, news: Dict, market: Dict, technical: Dict) -> float:
        """حساب مستوى الثقة في الإشارة"""
        confidence = 0.5  # أساسي
        
        # وزن الخبر
        if news['score'] > 15:
            confidence += 0.2
        elif news['score'] > 10:
            confidence += 0.1
        
        # وزن تحليل السوق
        if abs(market['price_change_24h']) > 5:
            confidence += 0.1
        elif abs(market['price_change_24h']) > 2:
            confidence += 0.05
        
        # وزن المؤشرات الفنية
        if technical and technical.get('rsi'):
            rsi = technical['rsi']
            if news['sentiment'] == 'Positive' and rsi < 30:
                confidence += 0.15  # ذروة بيع
            elif news['sentiment'] == 'Negative' and rsi > 70:
                confidence += 0.15  # ذروة شراء
        
        # وزن الاتجاه
        trend = technical.get('trend', '')
        if news['sentiment'] == 'Positive' and 'صاعد' in trend:
            confidence += 0.2
        elif news['sentiment'] == 'Negative' and 'هابط' in trend:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def calculate_atr(self, technical: Dict) -> Optional[float]:
        """حساب Average True Range (مبسط)"""
        # في التطبيق الحقيقي، سنحسب ATR من بيانات الشموع
        return None
    
    def generate_signal_id(self) -> str:
        """توليد معرف فريد للإشارة"""
        import hashlib
        import time
        
        unique = f"{time.time()}{random.randint(1000, 9999)}"
        return hashlib.md5(unique.encode()).hexdigest()[:8].upper()
    
    def generate_recommendation(self, confidence: float, risk_reward: float) -> str:
        """توليد توصية بناءً على التحليل"""
        if confidence > 0.8 and risk_reward > 2:
            return "توصية قوية ✅✅✅"
        elif confidence > 0.7 and risk_reward > 1.5:
            return "توصية جيدة ✅✅"
        elif confidence > 0.6:
            return "توصية متوسطة ✅"
        else:
            return "مراقبة فقط 👁"
    
    def determine_risk_level(self, technical: Dict) -> str:
        """تحديد مستوى المخاطرة"""
        volatility = technical.get('volatility', 0)
        
        if volatility > 10:
            return "مرتفع 🔴"
        elif volatility > 5:
            return "متوسط 🟡"
        else:
            return "منخفض 🟢"
    
    def format_signal_message(self, signal: Dict) -> str:
        """تنسيق رسالة الإشارة بشكل احترافي"""
        
        # أيقونات حسب النوع
        if signal['sentiment'] == 'Positive':
            main_icon = "🟢"
            type_icon = "📈"
        else:
            main_icon = "🔴"
            type_icon = "📉"
        
        # تنسيق الأرقام
        entry_str = f"${signal['entry']:,.4f}"
        tp1_str = f"${signal['take_profit']['tp1']:,.4f}"
        tp2_str = f"${signal['take_profit']['tp2']:,.4f}"
        tp3_str = f"${signal['take_profit']['tp3']:,.4f}"
        sl_str = f"${signal['stop_loss']:,.4f}"
        
        # نسبة الثقة
        confidence_percent = int(signal['confidence'] * 100)
        confidence_bar = "█" * (confidence_percent // 10) + "░" * (10 - (confidence_percent // 10))
        
        message = f"""
{main_icon} *Obeida Trading Signal* {main_icon}
━━━━━━━━━━━━━━━━━━━━━━
📰 {signal['news']['title']}

💎 *{signal['symbol']}/USDT*
💰 {entry_str} | {signal['market_data']['price_change_24h']:+.2f}%

━━━━━━━━━━━━━━━━━━━━━━
⚡️ {signal['type']} {type_icon}

🎯 TP1: {tp1_str}
🎯 TP2: {tp2_str}
🎯 TP3: {tp3_str}
🛑 SL:  {sl_str}

━━━━━━━━━━━━━━━━━━━━━━
📊 *التحليل الفني*
• RSI: {signal['technical_indicators'].get('rsi', 'N/A'):.1f}
• الاتجاه: {signal['technical_indicators'].get('trend', 'N/A')}
• المخاطرة: {signal['risk_level']}

━━━━━━━━━━━━━━━━━━━━━━
🎯 *نسبة الثقة*: {confidence_percent}%
{confidence_bar}

💡 {signal['recommendation']}

━━━━━━━━━━━━━━━━━━━━━━
📢 {CHANNEL_LINK}
⚡️ @ObeidaTrading
        """
        
        return message.strip()

signal_generator = SignalGenerator()

# --- نظام الإشعارات المتقدم للمشرف ---
class AdminNotifier:
    """نظام متقدم لإشعارات المشرف"""
    
    @staticmethod
    def send_detailed_report():
        """إرسال تقرير مفصل للمشرف"""
        
        stats = load_json(STATS_FILE, {})
        users = load_json(USERS_FILE, {})
        banned = load_json(BANNED_USERS_FILE, [])
        performance = load_json(SIGNAL_PERFORMANCE_FILE, {})
        news_stats = news_manager.get_news_stats()
        
        # حساب المستخدمين النشطين اليوم
        today = datetime.now().date()
        active_today = 0
        for user_id, user_data in users.items():
            try:
                last_active = datetime.fromisoformat(user_data.get('last_active', '2000-01-01')).date()
                if last_active == today:
                    active_today += 1
            except:
                pass
        
        # حساب المستخدمين المميزين
        premium_users = sum(1 for u in users.values() if UserManager.check_premium(u.get('id')))
        
        # حساب دقة الإشارات
        accuracy = Statistics.calculate_accuracy()
        
        # آخر فحص
        last_check = stats.get('last_check_time', 'لم يتم الفحص بعد')
        last_news = stats.get('last_news', 'لا يوجد')
        
        # إحصائيات API
        api_calls = stats.get('api_calls_today', 0)
        messages_sent = stats.get('messages_sent_today', 0)
        
        # وقت التشغيل
        start_time = datetime.fromisoformat(stats.get('bot_start_time', datetime.now().isoformat()))
        uptime = datetime.now() - start_time
        uptime_str = str(uptime).split('.')[0]  # إزالة الكسور
        
        report = f"""
👑 *Obeida Trading - تقرير شامل* 👑
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 *إحصائيات المستخدمين*
• 👥 الإجمالي: {len(users)}
• ⭐ المميزين: {premium_users}
• 📅 نشط اليوم: {active_today}
• 🚫 المحظورين: {len(banned)}

📈 *أداء الإشارات*
• 🔄 إجمالي: {performance.get('total_signals', 0)}
• ✅ ناجحة: {performance.get('successful', 0)}
• ❌ فاشلة: {performance.get('failed', 0)}
• 🎯 الدقة: {accuracy:.1f}%
• 💰 صافي الربح: ${performance.get('total_profit', 0):,.2f}

📰 *آخر الأخبار*
• 🕒 آخر فحص: {last_check}
• 📰 آخر خبر: {last_news}
• 👍 إيجابي: {news_stats.get('positive', 0)}
• 👎 سلبي: {news_stats.get('negative', 0)}

📊 *أشهر العملات*
{AdminNotifier._format_top_symbols(news_stats.get('top_symbols', {}))}

⚙️ *أداء النظام*
• 📡 استدعاءات API: {api_calls}
• 📨 رسائل مرسلة: {messages_sent}
• ⏳ وقت التشغيل: {uptime_str}
• 💾 حالة الذاكرة: {AdminNotifier._get_memory_usage()}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡️ البوت يعمل بكفاءة عالية ✅
        """
        
        return report
    
    @staticmethod
    def _format_top_symbols(symbols: Dict) -> str:
        """تنسيق عرض أشهر العملات"""
        if not symbols:
            return "لا توجد بيانات كافية"
        
        result = ""
        for symbol, count in list(symbols.items())[:5]:
            result += f"• {symbol}: {count} مرة\n"
        return result
    
    @staticmethod
    def _get_memory_usage() -> str:
        """الحصول على استخدام الذاكرة"""
        try:
            import psutil
            process = psutil.Process()
            memory = process.memory_info().rss / 1024 / 1024  # تحويل إلى MB
            return f"{memory:.1f} MB"
        except:
            return "غير متوفر"
    
    @staticmethod
    def send_news_update(news: Dict):
        """إرسال تحديث الأخبار للمشرف"""
        
        # تحديد نوع الخبر
        if news['sentiment'] == 'Positive':
            icon = "🟢 خبر إيجابي"
        elif news['sentiment'] == 'Negative':
            icon = "🔴 خبر سلبي"
        else:
            icon = "⚪️ خبر محايد"
        
        # تنسيق الوقت
        time_str = "الآن"
        if news.get('time'):
            try:
                news_time = datetime.fromisoformat(news['time'].replace('Z', '+00:00'))
                now = datetime.now().replace(tzinfo=news_time.tzinfo)
                diff = now - news_time
                
                if diff.days > 0:
                    time_str = f"منذ {diff.days} يوم"
                elif diff.seconds > 3600:
                    hours = diff.seconds // 3600
                    time_str = f"منذ {hours} ساعة"
                elif diff.seconds > 60:
                    minutes = diff.seconds // 60
                    time_str = f"منذ {minutes} دقيقة"
            except:
                time_str = news.get('time', 'غير معروف')
        
        message = f"""
📰 *تحديث الأخبار*
━━━━━━━━━━━━━━━━━━
{icon}
💎 {news['symbol']}
📊 الثقة: {news['score']}/20

📌 {news['title'][:150]}...
⏱ {time_str}
📰 المصدر: {news['source']}

━━━━━━━━━━━━━━━━━━
⚡️ تم رصد خبر جديد
        """
        
        for admin_id in ADMIN_IDS:
            send_telegram_message(admin_id, message)
    
    @staticmethod
    def send_signal_report(signal: Dict, sent_count: int):
        """إرسال تقرير الإشارة للمشرف"""
        
        # حساب النسبة المئوية للثقة
        confidence_percent = int(signal['confidence'] * 100)
        
        # تحديد لون الثقة
        if confidence_percent >= 80:
            confidence_color = "🟢"
        elif confidence_percent >= 60:
            confidence_color = "🟡"
        else:
            confidence_color = "🔴"
        
        message = f"""
📊 *تقرير الإشارة الجديدة*
━━━━━━━━━━━━━━━━━━━━
💎 {signal['symbol']}/USDT
⚡️ {signal['type']}
💰 السعر: ${signal['entry']:,.4f}

🎯 *الأهداف*
TP1: ${signal['take_profit']['tp1']:,.4f}
TP2: ${signal['take_profit']['tp2']:,.4f}
TP3: ${signal['take_profit']['tp3']:,.4f}
🛑 SL: ${signal['stop_loss']:,.4f}

📊 *التحليل*
• الثقة: {confidence_color} {confidence_percent}%
• المخاطرة: {signal['risk_level']}
• {signal['recommendation']}

📈 *الإرسال*
• 👥 المستلمين: {sent_count} مستخدم
• ⏱ الوقت: {datetime.now().strftime('%H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━
✅ تم إرسال الإشارة بنجاح
        """
        
        for admin_id in ADMIN_IDS:
            send_telegram_message(admin_id, message)
    
    @staticmethod
    def send_error_report(error: str, details: Dict = None):
        """إرسال تقرير خطأ للمشرف"""
        
        message = f"""
🚨 *تنبيه خطأ في النظام*
━━━━━━━━━━━━━━━━━━━━
❌ {error}

⏱ الوقت: {datetime.now().strftime('%H:%M:%S')}
        """
        
        if details:
            details_str = "\n".join([f"• {k}: {v}" for k, v in details.items()])
            message += f"\n📋 *التفاصيل*\n{details_str}"
        
        message += "\n━━━━━━━━━━━━━━━━━━━━\n⚠️ يرجى المراجعة"
        
        for admin_id in ADMIN_IDS:
            send_telegram_message(admin_id, message)

# --- دوال التلغرام المحسنة ---
class TelegramBot:
    """فئة محسنة للتعامل مع تلغرام"""
    
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.message_queue = []
        self.last_request_time = 0
        self.request_count = 0
        self.daily_reset = datetime.now().date()
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = "Markdown", 
                     disable_web_preview: bool = True, reply_markup: dict = None) -> bool:
        """إرسال رسالة مع التحكم بالمعدل"""
        
        # التحقق من حد الطلبات اليومي
        if datetime.now().date() != self.daily_reset:
            self.request_count = 0
            self.daily_reset = datetime.now().date()
        
        if self.request_count >= 1000:  # حد تلغرام الأساسي
            logger.warning("تم الوصول للحد اليومي من الطلبات")
            return False
        
        # التحكم بمعدل الطلبات
        current_time = time.time()
        if current_time - self.last_request_time < (1 / BOT_CONFIG['RATE_LIMIT']):
            time.sleep((1 / BOT_CONFIG['RATE_LIMIT']) - (current_time - self.last_request_time))
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_web_preview
            }
            
            if reply_markup:
                data["reply_markup"] = reply_markup
            
            response = requests.post(url, json=data, timeout=BOT_CONFIG['TIMEOUT'])
            self.last_request_time = time.time()
            self.request_count += 1
            
            # تحديث إحصائيات الرسائل
            stats = load_json(STATS_FILE, {})
            stats['messages_sent_today'] = stats.get('messages_sent_today', 0) + 1
            save_json(STATS_FILE, stats)
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"خطأ في إرسال رسالة لـ {chat_id}: {e}")
            return False
    
    def send_photo(self, chat_id: str, photo_url: str, caption: str = None) -> bool:
        """إرسال صورة"""
        try:
            url = f"{self.base_url}/sendPhoto"
            data = {
                "chat_id": chat_id,
                "photo": photo_url
            }
            if caption:
                data["caption"] = caption
            
            response = requests.post(url, json=data, timeout=BOT_CONFIG['TIMEOUT'])
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"خطأ في إرسال صورة: {e}")
            return False
    
    def send_poll(self, chat_id: str, question: str, options: list) -> bool:
        """إرسال استفتاء"""
        try:
            url = f"{self.base_url}/sendPoll"
            data = {
                "chat_id": chat_id,
                "question": question,
                "options": json.dumps(options),
                "is_anonymous": False
            }
            
            response = requests.post(url, json=data, timeout=BOT_CONFIG['TIMEOUT'])
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"خطأ في إرسال استفتاء: {e}")
            return False
    
    def broadcast(self, message: str, exclude_banned: bool = True) -> Tuple[int, int]:
        """بث رسالة لجميع المستخدمين مع تحسينات"""
        
        users = load_json(USERS_FILE, {})
        banned = load_json(BANNED_USERS_FILE, []) if exclude_banned else []
        
        sent = 0
        failed = 0
        batch = []
        
        for user_id, user_data in users.items():
            if str(user_id) not in banned:
                # التحقق من إعدادات الإشعارات للمستخدم
                if not user_data.get('settings', {}).get('notifications', True):
                    continue
                
                batch.append(user_id)
                
                if len(batch) >= BOT_CONFIG['BATCH_SIZE']:
                    # إرسال الدفعة
                    for uid in batch:
                        if self.send_message(uid, message):
                            sent += 1
                            # تحديث عدد الإشارات المستلمة
                            users[str(uid)]['signals_received'] = users[str(uid)].get('signals_received', 0) + 1
                        else:
                            failed += 1
                        time.sleep(0.05)  # تجنب الحظر
                    
                    batch = []
        
        # إرسال الدفعة الأخيرة
        for uid in batch:
            if self.send_message(uid, message):
                sent += 1
                users[str(uid)]['signals_received'] = users[str(uid)].get('signals_received', 0) + 1
            else:
                failed += 1
            time.sleep(0.05)
        
        # حفظ تحديثات المستخدمين
        save_json(USERS_FILE, users)
        
        return sent, failed

telegram_bot = TelegramBot()

# --- دوال مساعدة للرسائل ---
def send_telegram_message(chat_id, text):
    """دالة مساعدة لإرسال الرسائل"""
    return telegram_bot.send_message(chat_id, text)

def send_to_admin(message):
    """دالة مساعدة لإرسال رسالة للمشرفين"""
    for admin_id in ADMIN_IDS:
        telegram_bot.send_message(admin_id, message)

# --- نظام معالجة الأوامر المتقدم ---
class CommandHandler:
    """معالج الأوامر المتقدم"""
    
    def __init__(self):
        self.commands = {
            '/start': self.cmd_start,
            '/help': self.cmd_help,
            '/stats': self.cmd_stats,
            '/profile': self.cmd_profile,
            '/channels': self.cmd_channels,
            '/price': self.cmd_price,
            '/analyze': self.cmd_analyze,
            '/signals': self.cmd_signals,
            '/news': self.cmd_news,
            '/alert': self.cmd_alert,
            '/portfolio': self.cmd_portfolio,
            '/learn': self.cmd_learn,
            '/referral': self.cmd_referral,
            '/leaderboard': self.cmd_leaderboard,
            '/settings': self.cmd_settings,
            '/feedback': self.cmd_feedback,
            '/premium': self.cmd_premium,
        }
        
        self.admin_commands = {
            '/ban': self.cmd_ban,
            '/unban': self.cmd_unban,
            '/addchannel': self.cmd_addchannel,
            '/removechannel': self.cmd_removechannel,
            '/broadcast': self.cmd_broadcast,
            '/lastnews': self.cmd_lastnews,
            '/panel': self.cmd_panel,
            '/report': self.cmd_report,
            '/notify': self.cmd_notify,
            '/interval': self.cmd_interval,
            '/maintenance': self.cmd_maintenance,
            '/backup': self.cmd_backup,
            '/restart': self.cmd_restart,
            '/test': self.cmd_test,
        }
    
    def handle(self, user_id: int, text: str, username: str = None, first_name: str = None):
        """معالجة الأمر"""
        
        if not text or not text.startswith('/'):
            return
        
        # التحقق من وضع الصيانة
        if BOT_CONFIG['MAINTENANCE_MODE'] and user_id not in ADMIN_IDS:
            telegram_bot.send_message(user_id, "🔧 البوت في وضع الصيانة حالياً، يرجى المحاولة لاحقاً.")
            return
        
        # التحقق من الحظر
        if is_user_banned(user_id):
            telegram_bot.send_message(user_id, "❌ أنت محظور من استخدام البوت.")
            return
        
        parts = text.split(' ', 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else None
        
        # تسجيل الأمر
        UserManager.update_user(user_id, stats={'last_command': command, 'commands_used': 1})
        Statistics.update_user_activity(user_id, command)
        
        # معالجة الأمر
        if command in self.commands:
            self.commands[command](user_id, args, username, first_name)
        elif command in self.admin_commands and user_id in ADMIN_IDS:
            self.admin_commands[command](user_id, args)
        else:
            telegram_bot.send_message(user_id, "❌ أمر غير معروف. أرسل /help لعرض الأوامر المتاحة.")
    
    def cmd_start(self, user_id, args, username, first_name):
        """أمر بدء البوت"""
        
        # التحقق من الاشتراك
        if not check_all_subscriptions(user_id):
            channels = get_required_channels()
            msg = "❌ *يجب الاشتراك في القنوات التالية:*\n\n"
            for ch in channels:
                msg += f"📢 {ch}\n"
            msg += "\n✅ بعد الاشتراك أرسل /start مرة أخرى"
            
            # إضافة قنوات موصى بها
            msg += "\n\n📌 *قنوات موصى بها (اختياري):*\n"
            for ch in RECOMMENDED_CHANNELS:
                msg += f"• {ch['name']}: {ch['link']}\n"
            
            telegram_bot.send_message(user_id, msg)
            return
        
        # التحقق من وجود كود إحالة
        if args and args.startswith('ref_'):
            referral_code = args.replace('ref_', '')
            UserManager.add_referral(user_id, referral_code)
        
        # إضافة المستخدم
        UserManager.update_user(user_id, 
                               username=username or '',
                               first_name=first_name or '')
        
        # إنشاء لوحة الأزرار
        keyboard = {
            "inline_keyboard": [
                [{"text": "📊 إحصائياتي", "callback_data": "profile"},
                 {"text": "📈 آخر الإشارات", "callback_data": "signals"}],
                [{"text": "💰 أسعار العملات", "callback_data": "prices"},
                 {"text": "📰 آخر الأخبار", "callback_data": "news"}],
                [{"text": "🎓 تعلم التداول", "callback_data": "learn"},
                 {"text": "👥 دعوة الأصدقاء", "callback_data": "referral"}],
                [{"text": "⚙️ الإعدادات", "callback_data": "settings"},
                 {"text": "📞 الدعم", "url": CHANNEL_LINK}]
            ]
        }
        
        welcome = f"""
🎉 *مرحباً بك في Obeida Trading!* 🎉

✅ تم تفعيل حسابك بنجاح
🔔 سيتم إرسال التوصيات هنا تلقائياً

✨ *مميزات البوت:*
• إشارات دقيقة تعتمد على الأخبار والتحليل الفني
• تحليل متقدم للسوق مع مؤشرات RSI, MACD
• تنبيهات أسعار مخصصة
• محفظة لتتبع صفقاتك
• نظام إحالة بمكافآت حصرية
• محتوى تعليمي للمبتدئين والمحترفين

📢 {CHANNEL_LINK}
        """
        
        telegram_bot.send_message(user_id, welcome, reply_markup=keyboard)
        send_to_admin(f"👤 مستخدم جديد: {username or first_name} (ID: {user_id})")
    
    def cmd_help(self, user_id, args, username, first_name):
        """أمر المساعدة"""
        
        help_text = """
📚 *قائمة الأوامر المتاحة*

👤 *أوامر عامة*
/start - بدء البوت
/help - عرض هذه المساعدة
/stats - إحصائيات البوت
/profile - ملفك الشخصي
/channels - القنوات المطلوبة

💰 *أوامر التداول*
/price [رمز] - سعر عملة (مثال: /price BTC)
/analyze [رمز] - تحليل فني متقدم
/signals - آخر الإشارات
/news - آخر الأخبار
/alert [رمز] [سعر] - تنبيه سعر

📊 *أوامر متقدمة*
/portfolio - محفظتك الاستثمارية
/learn - محتوى تعليمي
/referral - نظام الإحالة
/leaderboard - قائمة المتصدرين
/settings - إعدادات البوت
/feedback - إرسال اقتراح

⭐ *المميزين فقط*
/premium - معلومات الاشتراك المميز

👑 *أوامر المشرف*
/panel - لوحة التحكم
/report - تقرير شامل
/lastnews - آخر الأخبار
/broadcast [رسالة] - إذاعة
/ban [id] - حظر مستخدم
/unban [id] - إلغاء حظر
/addchannel [قناة] - إضافة قناة
/removechannel [قناة] - حذف قناة

📌 *لمزيد من المعلومات، تواصل معنا*
📢 {CHANNEL_LINK}
        """
        
        telegram_bot.send_message(user_id, help_text)
    
    def cmd_stats(self, user_id, args, username, first_name):
        """أمر الإحصائيات"""
        
        stats = load_json(STATS_FILE, {})
        users = load_json(USERS_FILE, {})
        performance = load_json(SIGNAL_PERFORMANCE_FILE, {})
        
        accuracy = Statistics.calculate_accuracy()
        
        msg = f"""
📊 *إحصائيات Obeida Trading*

👥 *المستخدمين*
• الإجمالي: {len(users)}
• النشطون اليوم: {stats.get('active_today', 0)}
• المميزون: {stats.get('premium_users', 0)}

📈 *الإشارات*
• إجمالي: {performance.get('total_signals', 0)}
• ناجحة: {performance.get('successful', 0)}
• فاشلة: {performance.get('failed', 0)}
• الدقة: {accuracy:.1f}%

💰 *الأداء*
• إجمالي الأرباح: ${performance.get('total_profit', 0):,.2f}
• متوسط الربح: ${performance.get('average_profit', 0):,.2f}

⚡️ *حالة البوت*
• آخر تحديث: {stats.get('last_check_time', 'N/A')}
• الإشارات اليوم: {stats.get('signals_today', 0)}
• وقت التشغيل: نشط ✅

📢 {CHANNEL_LINK}
        """
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_profile(self, user_id, args, username, first_name):
        """أمر الملف الشخصي"""
        
        user_stats = UserManager.get_user_stats(user_id)
        
        if not user_stats:
            telegram_bot.send_message(user_id, "❌ لم يتم العثور على بياناتك. أرسل /start أولاً.")
            return
        
        premium_status = "⭐ مميز" if user_stats['premium'] else "👤 عادي"
        
        msg = f"""
👤 *ملفك الشخصي*

🆔 المعرف: {user_id}
📛 الاسم: {first_name or 'غير معروف'}
⭐ الحالة: {premium_status}

📊 *إحصائياتك*
• 📅 عضو منذ: {user_stats['joined_days']} يوم
• 📈 إشارات مستلمة: {user_stats['signals_received']}
• 🎯 صفقات منفذة: {user_stats['signals_taken']}
• ✅ ناجحة: {user_stats['successful_trades']}
• 📊 الدقة: {user_stats['accuracy']:.1f}%
• 💰 الربح/الخسارة: ${user_stats['profit_loss']:,.2f}

👥 *الإحالات*
• عدد المحالين: {user_stats['referrals_count']}
• المكافآت: قريباً

⚙️ *الإعدادات*
• الإشعارات: مفعلة
• اللغة: العربية
• المخاطرة: متوسطة

📢 {CHANNEL_LINK}
        """
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_channels(self, user_id, args, username, first_name):
        """أمر عرض القنوات"""
        
        channels = get_required_channels()
        msg = "📢 *القنوات المطلوبة للاشتراك:*\n\n"
        
        for i, ch in enumerate(channels, 1):
            # التحقق من الاشتراك
            subscribed = check_subscription(user_id, ch)
            status = "✅ مشترك" if subscribed else "❌ غير مشترك"
            msg += f"{i}. {ch} - {status}\n"
        
        msg += f"\n📌 *قنوات موصى بها*\n"
        for ch in RECOMMENDED_CHANNELS:
            msg += f"• {ch['name']}: {ch['link']}\n"
        
        msg += f"\n✅ بعد الاشتراك أرسل /start للتأكيد"
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_price(self, user_id, args, username, first_name):
        """أمر عرض سعر عملة"""
        
        if not args:
            telegram_bot.send_message(user_id, "❌ الرجاء إدخال رمز العملة. مثال: /price BTC")
            return
        
        symbol = args.upper().strip()
        if symbol.endswith('USDT'):
            symbol = symbol.replace('USDT', '')
        
        market = market_analyzer.get_market_data(symbol)
        
        if market:
            # تحديد اتجاه السعر
            if market['price_change_24h'] > 0:
                trend = "🟢 صاعد"
            elif market['price_change_24h'] < 0:
                trend = "🔴 هابط"
            else:
                trend = "⚪️ مستقر"
            
            msg = f"""
💰 *{symbol}/USDT*

💵 السعر: ${market['price']:,.4f}
📊 التغير 24h: {market['price_change_24h']:+.2f}%
📈 أعلى 24h: ${market['high_24h']:,.4f}
📉 أدنى 24h: ${market['low_24h']:,.4f}
📊 الحجم 24h: {market['volume_24h']:,.0f}
📊 التذبذب: {market['volatility']:.2f}%

{trend}

⏱ آخر تحديث: {datetime.now().strftime('%H:%M:%S')}

للتحليل الفني: /analyze {symbol}
            """
        else:
            msg = f"❌ لم يتم العثور على {symbol}. الرجاء التأكد من الرمز."
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_analyze(self, user_id, args, username, first_name):
        """أمر التحليل الفني المتقدم"""
        
        if not args:
            telegram_bot.send_message(user_id, "❌ الرجاء إدخال رمز العملة. مثال: /analyze BTC")
            return
        
        symbol = args.upper().strip()
        
        # جلب بيانات السوق والمؤشرات
        market = market_analyzer.get_market_data(symbol)
        technical = market_analyzer.calculate_technical_indicators(symbol)
        
        if not market or not technical:
            telegram_bot.send_message(user_id, f"❌ فشل في تحليل {symbol}")
            return
        
        # تنسيق المؤشرات
        rsi = technical.get('rsi', 50)
        if rsi > 70:
            rsi_status = "🔴 ذروة شراء"
        elif rsi < 30:
            rsi_status = "🟢 ذروة بيع"
        else:
            rsi_status = "⚪️ محايد"
        
        macd = technical.get('macd', {})
        macd_status = "🟢 إيجابي" if macd.get('histogram', 0) > 0 else "🔴 سلبي" if macd.get('histogram', 0) < 0 else "⚪️ محايد"
        
        ma20 = technical['moving_averages'].get('ma20', 0)
        ma50 = technical['moving_averages'].get('ma50', 0)
        current_price = market['price']
        
        if ma20 and ma50:
            if current_price > ma20 > ma50:
                trend = "🟢 صاعد قوي"
            elif current_price > ma20:
                trend = "🟢 صاعد"
            elif current_price < ma20 < ma50:
                trend = "🔴 هابط قوي"
            elif current_price < ma20:
                trend = "🔴 هابط"
            else:
                trend = "⚪️ جانبي"
        else:
            trend = technical.get('trend', 'غير متوفر')
        
        bb = technical.get('bollinger_bands', {})
        if current_price > bb.get('upper', 0):
            bb_status = "🔴 فوق النطاق"
        elif current_price < bb.get('lower', 0):
            bb_status = "🟢 تحت النطاق"
        else:
            bb_status = "⚪️ داخل النطاق"
        
        support = technical['support_resistance'].get('support', 0)
        resistance = technical['support_resistance'].get('resistance', 0)
        
        msg = f"""
📊 *تحليل {symbol}/USDT الفني*
━━━━━━━━━━━━━━━━━━━━━

💰 *السعر الحالي*
💵 ${current_price:,.4f} | {market['price_change_24h']:+.2f}%

📈 *المؤشرات الفنية*
• RSI ({rsi:.1f}): {rsi_status}
• MACD: {macd_status}
• الاتجاه: {trend}

📊 *Bollinger Bands*
• {bb_status}
• العلوي: ${bb.get('upper', 0):,.4f}
• الأوسط: ${bb.get('middle', 0):,.4f}
• السفلي: ${bb.get('lower', 0):,.4f}

📌 *المتوسطات المتحركة*
• MA20: ${ma20:,.4f}
• MA50: ${ma50:,.4f}

🎯 *مستويات مهمة*
• مقاومة: ${resistance:,.4f}
• دعم: ${support:,.4f}

💡 *التوصية*
• المخاطرة: {signal_generator.determine_risk_level(technical)}

━━━━━━━━━━━━━━━━━━━━━
📢 {CHANNEL_LINK}
        """
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_signals(self, user_id, args, username, first_name):
        """أمر عرض آخر الإشارات"""
        
        signals = load_json(SIGNALS_HISTORY_FILE, [])
        
        if not signals:
            telegram_bot.send_message(user_id, "📊 لا توجد إشارات سابقة حالياً.")
            return
        
        # عرض آخر 5 إشارات
        recent = signals[-5:]
        
        msg = "📈 *آخر الإشارات*\n━━━━━━━━━━━━━━━━\n\n"
        
        for i, signal in enumerate(reversed(recent), 1):
            icon = "🟢" if signal['sentiment'] == 'Positive' else "🔴"
            time_str = ""
            if signal.get('timestamp'):
                try:
                    sig_time = datetime.fromisoformat(signal['timestamp'])
                    time_diff = datetime.now() - sig_time
                    if time_diff.total_seconds() < 3600:
                        time_str = f"منذ {int(time_diff.total_seconds() / 60)} دقيقة"
                    else:
                        time_str = f"منذ {int(time_diff.total_seconds() / 3600)} ساعة"
                except:
                    time_str = signal['timestamp']
            
            msg += f"{i}. {icon} *{signal['symbol']}/USDT*\n"
            msg += f"   ⚡️ {signal['type']}\n"
            msg += f"   💰 ${signal['entry']:,.4f}\n"
            msg += f"   ⏱ {time_str}\n"
            msg += f"   📊 ثقة: {int(signal.get('confidence', 0.5) * 100)}%\n\n"
        
        msg += "━━━━━━━━━━━━━━━━\n"
        msg += f"📢 {CHANNEL_LINK}"
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_news(self, user_id, args, username, first_name):
        """أمر عرض آخر الأخبار"""
        
        news_history = news_manager.get_news_history(limit=10)
        
        if not news_history:
            telegram_bot.send_message(user_id, "📰 لا توجد أخبار حالياً.")
            return
        
        msg = "📰 *آخر الأخبار*\n━━━━━━━━━━━━━━━━\n\n"
        
        for i, news in enumerate(news_history, 1):
            icon = "🟢" if news['sentiment'] == 'Positive' else "🔴" if news['sentiment'] == 'Negative' else "⚪️"
            time_str = ""
            if news.get('time'):
                try:
                    news_time = datetime.fromisoformat(news['time'].replace('Z', '+00:00'))
                    time_diff = datetime.now() - news_time
                    if time_diff.total_seconds() < 3600:
                        time_str = f"منذ {int(time_diff.total_seconds() / 60)} دقيقة"
                    else:
                        time_str = f"منذ {int(time_diff.total_seconds() / 3600)} ساعة"
                except:
                    time_str = news['time']
            
            msg += f"{i}. {icon} *{news['title'][:80]}...*\n"
            msg += f"   💎 {news['symbol']} | 📰 {news['source']}\n"
            msg += f"   ⏱ {time_str}\n\n"
        
        msg += "━━━━━━━━━━━━━━━━\n"
        msg += f"📢 {CHANNEL_LINK}"
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_alert(self, user_id, args, username, first_name):
        """أمر إعداد تنبيه سعر"""
        
        if not args:
            telegram_bot.send_message(user_id, "❌ الرجاء إدخال العملة والسعر. مثال: /alert BTC 50000")
            return
        
        parts = args.split()
        if len(parts) != 2:
            telegram_bot.send_message(user_id, "❌ صيغة غير صحيحة. مثال: /alert BTC 50000")
            return
        
        symbol = parts[0].upper()
        try:
            target_price = float(parts[1])
        except:
            telegram_bot.send_message(user_id, "❌ السعر يجب أن يكون رقماً")
            return
        
        # حفظ التنبيه
        alerts = load_json(PRICE_ALERTS_FILE, {})
        
        user_id_str = str(user_id)
        if user_id_str not in alerts:
            alerts[user_id_str] = []
        
        # التحقق من عدم تكرار التنبيه
        for alert in alerts[user_id_str]:
            if alert['symbol'] == symbol and abs(alert['price'] - target_price) < 0.01:
                telegram_bot.send_message(user_id, f"❌ لديك بالفعل تنبيه لـ {symbol} عند ${target_price:,.2f}")
                return
        
        # إضافة التنبيه
        alerts[user_id_str].append({
            'symbol': symbol,
            'price': target_price,
            'created': datetime.now().isoformat(),
            'triggered': False,
            'direction': 'above' if target_price > 0 else 'below'
        })
        
        save_json(PRICE_ALERTS_FILE, alerts)
        
        telegram_bot.send_message(user_id, f"✅ تم إعداد تنبيه لـ {symbol} عند ${target_price:,.2f}\nسيتم إعلامك عند الوصول للسعر.")
    
    def cmd_portfolio(self, user_id, args, username, first_name):
        """أمر إدارة المحفظة"""
        
        portfolios = load_json(PORTFOLIO_FILE, {})
        user_id_str = str(user_id)
        
        if user_id_str not in portfolios:
            portfolios[user_id_str] = {
                'balance': 10000,  # رصيد ابتدائي تجريبي
                'trades': [],
                'total_profit': 0,
                'win_rate': 0
            }
            save_json(PORTFOLIO_FILE, portfolios)
        
        portfolio = portfolios[user_id_str]
        
        # حساب الإحصائيات
        trades = portfolio.get('trades', [])
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('profit', 0) > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # آخر 5 صفقات
        recent_trades = trades[-5:] if trades else []
        
        msg = f"""
💰 *محفظتك الاستثمارية*

💵 الرصيد: ${portfolio.get('balance', 0):,.2f}
📊 إجمالي الأرباح: ${portfolio.get('total_profit', 0):,.2f}

📈 *إحصائيات الصفقات*
• إجمالي الصفقات: {total_trades}
• الصفقات الرابحة: {winning_trades}
• نسبة النجاح: {win_rate:.1f}%

📋 *آخر الصفقات*
"""
        
        if recent_trades:
            for trade in recent_trades[-5:]:
                icon = "✅" if trade.get('profit', 0) > 0 else "❌"
                msg += f"\n{icon} {trade['symbol']} | ${trade.get('profit', 0):+.2f}"
        else:
            msg += "\nلا توجد صفقات مسجلة"
        
        msg += f"\n\n📢 {CHANNEL_LINK}"
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_learn(self, user_id, args, username, first_name):
        """أمر المحتوى التعليمي"""
        
        education = load_json(EDUCATION_FILE, {})
        
        msg = """
🎓 *أكاديمية Obeida Trading*

📚 *مستويات التعلم*
1. مبتدئ - أساسيات التداول
2. متوسط - التحليل الفني
3. متقدم - استراتيجيات متقدمة

📖 *الدروس المتاحة*
• ما هي العملات الرقمية؟
• كيفية قراءة الشموع اليابانية
• المؤشرات الفنية الأساسية
• إدارة رأس المال
• تحليل الأخبار والتأثير على السوق

🎥 *فيديوهات تعليمية*
• سلسلة التداول للمبتدئين
• شرح منصة Binance
• كيفية استخدام المؤشرات

📌 *نصائح يومية*
• ابدأ بمبالغ صغيرة
• تعلم قبل أن تستثمر
• لا تستثمر ما لا يمكنك خسارته
• استخدم وقف الخسارة دائماً

للحصول على درس محدد: /lesson [رقم]
لطرح سؤال: /ask [سؤالك]

📢 {CHANNEL_LINK}
        """
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_referral(self, user_id, args, username, first_name):
        """أمر نظام الإحالة"""
        
        user = UserManager.get_user(user_id)
        
        if not user:
            telegram_bot.send_message(user_id, "❌ أرسل /start أولاً")
            return
        
        referral_code = user.get('referral_code', '')
        referral_link = f"https://t.me/ObeidaTradingBot?start=ref_{referral_code}"
        
        # إحصائيات الإحالات
        referrals = load_json(REFERRALS_FILE, {})
        user_refs = referrals.get(str(user_id), [])
        successful_refs = [r for r in user_refs if r.get('status') == 'active']
        
        msg = f"""
👥 *نظام الإحالة*

🎁 *المميزات*
• دعوة 5 أصدقاء = شهر مجاني مميز
• دعوة 10 أصدقاء = 3 أشهر مجانية
• دعوة 20 صديق = سنة كاملة مجاناً

🔗 *رابط الإحالة الخاص بك*
{referral_link}

📊 *إحصائياتك*
• إجمالي الدعوات: {len(user_refs)}
• الدعوات النشطة: {len(successful_refs)}
• المكافآت المستحقة: 0

📌 *كيف تعمل؟*
1. شارك الرابط مع أصدقائك
2. عندما يسجل صديقك عبر الرابط
3. تحصل على نقاط إحالة
4. استبدل النقاط باشتراك مميز

لمشاركة الرابط: /share

📢 {CHANNEL_LINK}
        """
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_leaderboard(self, user_id, args, username, first_name):
        """أمر قائمة المتصدرين"""
        
        users = load_json(USERS_FILE, {})
        
        # حساب أفضل المستخدمين
        top_users = []
        for uid, data in users.items():
            profit = data.get('total_profit', 0)
            if profit > 0:
                top_users.append({
                    'id': uid,
                    'name': data.get('first_name', 'مستخدم')[:15],
                    'profit': profit,
                    'trades': data.get('successful_trades', 0)
                })
        
        # ترتيب حسب الأرباح
        top_users.sort(key=lambda x: x['profit'], reverse=True)
        top_10 = top_users[:10]
        
        msg = """
🏆 *قائمة المتصدرين*

━━━━━━━━━━━━━━━━
"""
        
        if top_10:
            for i, user in enumerate(top_10, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
                msg += f"\n{i}. {medal} {user['name']}\n"
                msg += f"   💰 ${user['profit']:,.2f} | 🎯 {user['trades']} صفقة\n"
        else:
            msg += "\nلا يوجد متصدرين بعد"
        
        msg += """
━━━━━━━━━━━━━━━━
💡 كلما زادت أرباحك، ارتفع ترتيبك!

للمشاركة في المسابقة:
• سجل صفقاتك في المحفظة
• حقق أعلى الأرباح
• احصل على جوائز حصرية

📢 {CHANNEL_LINK}
        """
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_settings(self, user_id, args, username, first_name):
        """أمر الإعدادات"""
        
        user = UserManager.get_user(user_id)
        
        if not user:
            telegram_bot.send_message(user_id, "❌ أرسل /start أولاً")
            return
        
        settings = user.get('settings', {})
        
        # حالة الإعدادات
        notifications = "✅ مفعلة" if settings.get('notifications', True) else "❌ معطلة"
        language = "🇸🇦 العربية" if settings.get('language', 'ar') == 'ar' else "🇺🇸 English"
        risk = settings.get('risk_level', 'medium')
        risk_text = "منخفض 🟢" if risk == 'low' else "متوسط 🟡" if risk == 'medium' else "مرتفع 🔴"
        
        # العملات المفضلة
        preferred = settings.get('preferred_pairs', [])
        preferred_text = ', '.join(preferred) if preferred else 'الكل'
        
        msg = f"""
⚙️ *الإعدادات*

🔔 الإشعارات: {notifications}
🌐 اللغة: {language}
📊 مستوى المخاطرة: {risk_text}
⭐ العملات المفضلة: {preferred_text}

📌 *لتغيير الإعدادات*
• /notify on/off - تفعيل/تعطيل الإشعارات
• /risk low/medium/high - تغيير المخاطرة
• /language ar/en - تغيير اللغة
• /pairs BTC,ETH - تعيين العملات المفضلة

📢 {CHANNEL_LINK}
        """
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_feedback(self, user_id, args, username, first_name):
        """أمر إرسال ملاحظات"""
        
        if not args:
            telegram_bot.send_message(user_id, "❌ الرجاء كتابة ملاحظاتك. مثال: /feedback البوت رائع!")
            return
        
        # حفظ الملاحظة
        feedback = load_json(USER_FEEDBACK_FILE, {})
        
        user_id_str = str(user_id)
        if user_id_str not in feedback:
            feedback[user_id_str] = []
        
        feedback[user_id_str].append({
            'text': args,
            'date': datetime.now().isoformat(),
            'status': 'new'
        })
        
        save_json(USER_FEEDBACK_FILE, feedback)
        
        # إرسال للمشرف
        admin_msg = f"""
💬 *ملاحظة مستخدم جديدة*
👤 ID: {user_id}
📝 {args}
⏱ {datetime.now().strftime('%H:%M:%S')}
        """
        send_to_admin(admin_msg)
        
        telegram_bot.send_message(user_id, "✅ شكراً لملاحظاتك! تم استلامها وسيتم مراجعتها.")
    
    def cmd_premium(self, user_id, args, username, first_name):
        """أمر الاشتراك المميز"""
        
        msg = """
⭐ *الاشتراك المميز*

✨ *مميزات العضوية المميزة*
• 🚀 إشارات حصرية إضافية
• 📊 تحليل فني متقدم لكل العملات
• 🔔 تنبيهات أسعار غير محدودة
• 📈 مؤشرات مخصصة
• 💼 محفظة متقدمة مع تقارير
• 🎓 دورات تعليمية حصرية
• 👥 دعم مباشر من المحللين
• 🏆 المشاركة في المسابقات الحصرية

💰 *الأسعار*
• شهري: $50
• 3 أشهر: $120 (وفر $30)
• سنوي: $400 (وفر $200)

🎁 *عروض خاصة*
• أول 100 مشترك: خصم 20%
• نظام الإحالة: ادعُ أصدقاءك واحصل على شهر مجاني

📌 *للاشتراك*
• /subscribe monthly - اشتراك شهري
• /subscribe quarterly - اشتراك ربع سنوي
• /subscribe yearly - اشتراك سنوي

💳 طرق الدفع: USDT (TRC20/BEP20) | BTC | بطاقة ائتمان

📢 للاستفسار: @ObeidaSupport
        """
        
        telegram_bot.send_message(user_id, msg)
    
    # أوامر المشرف
    
    def cmd_ban(self, user_id, args):
        """حظر مستخدم"""
        if not args:
            telegram_bot.send_message(user_id, "❌ استخدم: /ban [user_id]")
            return
        
        try:
            target = int(args.strip())
            result = ban_user(user_id, target)
            telegram_bot.send_message(user_id, result['message'])
        except:
            telegram_bot.send_message(user_id, "❌ معرف المستخدم غير صالح")
    
    def cmd_unban(self, user_id, args):
        """إلغاء حظر مستخدم"""
        if not args:
            telegram_bot.send_message(user_id, "❌ استخدم: /unban [user_id]")
            return
        
        try:
            target = int(args.strip())
            result = unban_user(user_id, target)
            telegram_bot.send_message(user_id, result['message'])
        except:
            telegram_bot.send_message(user_id, "❌ معرف المستخدم غير صالح")
    
    def cmd_addchannel(self, user_id, args):
        """إضافة قناة مطلوبة"""
        if not args:
            telegram_bot.send_message(user_id, "❌ استخدم: /addchannel [channel]")
            return
        
        result = add_channel(user_id, args.strip())
        telegram_bot.send_message(user_id, result['message'])
    
    def cmd_removechannel(self, user_id, args):
        """حذف قناة مطلوبة"""
        if not args:
            telegram_bot.send_message(user_id, "❌ استخدم: /removechannel [channel]")
            return
        
        result = remove_channel(user_id, args.strip())
        telegram_bot.send_message(user_id, result['message'])
    
    def cmd_broadcast(self, user_id, args):
        """بث رسالة لجميع المستخدمين"""
        if not args:
            telegram_bot.send_message(user_id, "❌ استخدم: /broadcast [message]")
            return
        
        telegram_bot.send_message(user_id, "📢 جاري البث...")
        sent, failed = telegram_bot.broadcast(args)
        telegram_bot.send_message(user_id, f"✅ تم البث: {sent} نجح، {failed} فشل")
    
    def cmd_lastnews(self, user_id, args):
        """آخر الأخبار مع تحليل"""
        news_history = news_manager.get_news_history(limit=5)
        
        if not news_history:
            telegram_bot.send_message(user_id, "📰 لا توجد أخبار حالياً.")
            return
        
        msg = "📰 *آخر الأخبار وتحليلها*\n━━━━━━━━━━━━━━━━\n\n"
        
        for i, news in enumerate(news_history, 1):
            # تحديد لون المشاعر
            if news['sentiment'] == 'Positive':
                sentiment_icon = "🟢"
                sentiment_text = "إيجابي"
            elif news['sentiment'] == 'Negative':
                sentiment_icon = "🔴"
                sentiment_text = "سلبي"
            else:
                sentiment_icon = "⚪️"
                sentiment_text = "محايد"
            
            # تنسيق الوقت
            time_ago = "الآن"
            if news.get('time'):
                try:
                    news_time = datetime.fromisoformat(news['time'].replace('Z', '+00:00'))
                    now = datetime.now().replace(tzinfo=news_time.tzinfo)
                    diff = now - news_time
                    
                    if diff.days > 0:
                        time_ago = f"منذ {diff.days} يوم"
                    elif diff.seconds > 3600:
                        hours = diff.seconds // 3600
                        time_ago = f"منذ {hours} ساعة"
                    elif diff.seconds > 60:
                        minutes = diff.seconds // 60
                        time_ago = f"منذ {minutes} دقيقة"
                except:
                    time_ago = news.get('time', 'غير معروف')
            
            msg += f"{i}. {sentiment_icon} *{news['title'][:80]}...*\n"
            msg += f"   💎 {news['symbol']} | {sentiment_text}\n"
            msg += f"   📰 {news['source']} | ⏱ {time_ago}\n"
            msg += f"   📊 الثقة: {news['score']}/20\n\n"
        
        # إحصائيات
        stats = news_manager.get_news_stats()
        msg += "━━━━━━━━━━━━━━━━\n"
        msg += f"📊 *إحصائيات*\n"
        msg += f"• إيجابي: {stats.get('positive', 0)}\n"
        msg += f"• سلبي: {stats.get('negative', 0)}\n"
        msg += f"• أشهر العملات: {', '.join(list(stats.get('top_symbols', {}).keys())[:3])}\n"
        
        telegram_bot.send_message(user_id, msg)
    
    def cmd_panel(self, user_id, args):
        """لوحة التحكم"""
        report = AdminNotifier.send_detailed_report()
        telegram_bot.send_message(user_id, report)
    
    def cmd_report(self, user_id, args):
        """تقرير فوري"""
        report = AdminNotifier.send_detailed_report()
        telegram_bot.send_message(user_id, report)
    
    def cmd_notify(self, user_id, args):
        """تفعيل/تعطيل الإشعارات"""
        panel = get_admin_panel()
        
        if args and args.lower() == 'on':
            panel['notifications_enabled'] = True
            save_admin_panel(panel)
            telegram_bot.send_message(user_id, "✅ تم تفعيل إشعارات المشرف")
        elif args and args.lower() == 'off':
            panel['notifications_enabled'] = False
            save_admin_panel(panel)
            telegram_bot.send_message(user_id, "❌ تم تعطيل إشعارات المشرف")
        else:
            status = 'مفعلة' if panel.get('notifications_enabled', True) else 'معطلة'
            telegram_bot.send_message(user_id, f"🔔 حالة إشعارات المشرف: {status}")
    
    def cmd_interval(self, user_id, args):
        """تغيير فترة التقرير"""
        if not args:
            telegram_bot.send_message(user_id, "❌ استخدم: /interval [ثانية]")
            return
        
        try:
            interval = int(args.strip())
            if 10 <= interval <= 300:
                panel = get_admin_panel()
                panel['report_interval'] = interval
                save_admin_panel(panel)
                telegram_bot.send_message(user_id, f"✅ تم تغيير فترة التقرير إلى {interval} ثانية")
            else:
                telegram_bot.send_message(user_id, "❌ الرجاء إدخال قيمة بين 10 و 300")
        except:
            telegram_bot.send_message(user_id, "❌ قيمة غير صالحة")
    
    def cmd_maintenance(self, user_id, args):
        """وضع الصيانة"""
        global BOT_CONFIG
        
        if args and args.lower() == 'on':
            BOT_CONFIG['MAINTENANCE_MODE'] = True
            telegram_bot.send_message(user_id, "🔧 تم تفعيل وضع الصيانة")
        elif args and args.lower() == 'off':
            BOT_CONFIG['MAINTENANCE_MODE'] = False
            telegram_bot.send_message(user_id, "✅ تم إلغاء وضع الصيانة")
        else:
            status = 'مفعل' if BOT_CONFIG['MAINTENANCE_MODE'] else 'معطل'
            telegram_bot.send_message(user_id, f"🔧 وضع الصيانة: {status}")
    
    def cmd_backup(self, user_id, args):
        """إنشاء نسخة احتياطية"""
        try:
            import shutil
            from datetime import datetime
            
            # إنشاء مجلد للنسخ الاحتياطية
            backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(backup_dir, exist_ok=True)
            
            # نسخ جميع ملفات JSON
            json_files = [f for f in os.listdir('.') if f.endswith('.json')]
            for file in json_files:
                shutil.copy2(file, backup_dir)
            
            # نسخ ملف السجل
            if os.path.exists(LOG_FILE):
                shutil.copy2(LOG_FILE, backup_dir)
            
            # ضغط المجلد
            shutil.make_archive(backup_dir, 'zip', backup_dir)
            shutil.rmtree(backup_dir)
            
            telegram_bot.send_message(user_id, f"✅ تم إنشاء نسخة احتياطية: {backup_dir}.zip")
            
        except Exception as e:
            telegram_bot.send_message(user_id, f"❌ فشل إنشاء النسخة الاحتياطية: {e}")
    
    def cmd_restart(self, user_id, args):
        """إعادة تشغيل البوت"""
        telegram_bot.send_message(user_id, "🔄 جاري إعادة تشغيل البوت...")
        
        # إرسال إشعار لجميع المشرفين
        for admin in ADMIN_IDS:
            if admin != user_id:
                telegram_bot.send_message(admin, f"🔄 تم إعادة تشغيل البوت بواسطة {user_id}")
        
        # إعادة التشغيل
        os.execl(sys.executable, sys.executable, *sys.argv)
    
    def cmd_test(self, user_id, args):
        """اختبار النظام"""
        
        results = []
        
        # اختبار API الأخبار
        try:
            news = news_manager.get_latest_news()
            results.append(f"✅ API الأخبار: {'يعمل' if news else 'لا توجد أخبار'}")
        except Exception as e:
            results.append(f"❌ API الأخبار: {e}")
        
        # اختبار API Binance
        try:
            market = market_analyzer.get_market_data('BTC')
            results.append(f"✅ Binance API: {'يعمل' if market else 'فشل'}")
        except Exception as e:
            results.append(f"❌ Binance API: {e}")
        
        # اختبار تلغرام
        try:
            telegram_bot.send_message(user_id, "✅ اختبار البوت: الرسالة تعمل")
            results.append("✅ تلغرام API: يعمل")
        except Exception as e:
            results.append(f"❌ تلغرام API: {e}")
        
        # اختبار الملفات
        try:
            test_file = "test.json"
            save_json(test_file, {"test": True})
            if os.path.exists(test_file):
                os.remove(test_file)
            results.append("✅ نظام الملفات: يعمل")
        except Exception as e:
            results.append(f"❌ نظام الملفات: {e}")
        
        # معلومات النظام
        import platform
        import psutil
        
        results.append(f"\n📊 *معلومات النظام*")
        results.append(f"• OS: {platform.system()} {platform.release()}")
        results.append(f"• Python: {platform.python_version()}")
        results.append(f"• CPU: {psutil.cpu_percent()}%")
        results.append(f"• RAM: {psutil.virtual_memory().percent}%")
        results.append(f"• وقت التشغيل: {datetime.now() - datetime.fromisoformat(load_json(STATS_FILE, {}).get('bot_start_time', datetime.now().isoformat()))}")
        
        msg = "🔧 *نتائج اختبار النظام*\n━━━━━━━━━━━━━━━━\n" + "\n".join(results)
        telegram_bot.send_message(user_id, msg)

# --- الدوال الأساسية ---
def get_users():
    """الحصول على قائمة المستخدمين"""
    users = load_json(USERS_FILE, {})
    return users

def get_banned_users():
    """الحصول على قائمة المحظورين"""
    return load_json(BANNED_USERS_FILE, [])

def get_required_channels():
    """الحصول على قائمة القنوات المطلوبة"""
    return load_json(CHANNELS_FILE, [CHANNEL_USERNAME])

def get_admin_panel():
    """الحصول على إعدادات لوحة التحكم"""
    return load_json(ADMIN_PANEL_FILE, {
        'notifications_enabled': True,
        'last_report_time': None,
        'report_interval': 30,
        'auto_restart': True,
        'debug_mode': False,
        'maintenance_message': None,
        'feature_flags': {
            'signals': True,
            'news': True,
            'alerts': True,
            'portfolio': True,
            'education': True,
            'leaderboard': True,
            'referrals': True,
        }
    })

def save_admin_panel(panel):
    """حفظ إعدادات لوحة التحكم"""
    save_json(ADMIN_PANEL_FILE, panel)

def is_user_banned(user_id):
    """التحقق إذا كان المستخدم محظوراً"""
    banned = get_banned_users()
    return str(user_id) in banned

def check_subscription(user_id, channel):
    """التحقق من الاشتراك في قناة"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getChatMember"
        params = {"chat_id": channel, "user_id": user_id}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            status = data.get('result', {}).get('status')
            return status in ['member', 'administrator', 'creator']
        return False
    except Exception as e:
        logger.error(f"خطأ في التحقق من الاشتراك في {channel}: {e}")
        return False

def check_all_subscriptions(user_id):
    """التحقق من الاشتراك في جميع القنوات"""
    channels = get_required_channels()
    for channel in channels:
        if not check_subscription(user_id, channel):
            return False
    return True

def ban_user(admin_id, user_id):
    """حظر مستخدم"""
    if admin_id not in ADMIN_IDS:
        return {'success': False, 'message': '❌ غير مصرح'}
    
    banned = get_banned_users()
    user_id_str = str(user_id)
    
    if user_id_str not in banned:
        banned.append(user_id_str)
        save_json(BANNED_USERS_FILE, banned)
        
        # إزالة المستخدم من قائمة المستخدمين
        users = load_json(USERS_FILE, {})
        if user_id_str in users:
            del users[user_id_str]
            save_json(USERS_FILE, users)
        
        logger.warning(f"المستخدم {user_id} تم حظره")
        return {'success': True, 'message': f'✅ تم حظر المستخدم {user_id}'}
    
    return {'success': False, 'message': '❌ المستخدم محظور بالفعل'}

def unban_user(admin_id, user_id):
    """إلغاء حظر مستخدم"""
    if admin_id not in ADMIN_IDS:
        return {'success': False, 'message': '❌ غير مصرح'}
    
    banned = get_banned_users()
    user_id_str = str(user_id)
    
    if user_id_str in banned:
        banned.remove(user_id_str)
        save_json(BANNED_USERS_FILE, banned)
        logger.warning(f"المستخدم {user_id} تم إلغاء حظره")
        return {'success': True, 'message': f'✅ تم إلغاء حظر المستخدم {user_id}'}
    
    return {'success': False, 'message': '❌ المستخدم غير موجود في قائمة المحظورين'}

def add_channel(admin_id, channel):
    """إضافة قناة مطلوبة"""
    if admin_id not in ADMIN_IDS:
        return {'success': False, 'message': '❌ غير مصرح'}
    
    channels = get_required_channels()
    if channel not in channels:
        channels.append(channel)
        save_json(CHANNELS_FILE, channels)
        return {'success': True, 'message': f'✅ تم إضافة القناة {channel}'}
    
    return {'success': False, 'message': '❌ القناة موجودة بالفعل'}

def remove_channel(admin_id, channel):
    """حذف قناة مطلوبة"""
    if admin_id not in ADMIN_IDS:
        return {'success': False, 'message': '❌ غير مصرح'}
    
    channels = get_required_channels()
    if channel in channels:
        channels.remove(channel)
        save_json(CHANNELS_FILE, channels)
        return {'success': True, 'message': f'✅ تم حذف القناة {channel}'}
    
    return {'success': False, 'message': '❌ القناة غير موجودة'}

# --- الدالة الرئيسية ---
def get_updates(offset=None):
    """جلب التحديثات من تلغرام"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        params = {
            'timeout': 30,
            'offset': offset,
            'allowed_updates': ['message', 'callback_query']
        }
        response = requests.get(url, params=params, timeout=35)
        data = response.json()
        return data.get('result', [])
    except Exception as e:
        logger.error(f"خطأ في جلب التحديثات: {e}")
        return []

def handle_callback(user_id, callback_data):
    """معالجة ضغط الأزرار"""
    # يمكن إضافة معالجة للأزرار هنا
    pass

def main():
    """الدالة الرئيسية للبوت"""
    logger.info("🚀 تشغيل البوت المتطور...")
    
    # إشعار بدء التشغيل
    start_msg = f"""
✅ *Obeida Trading Bot v3.0*
━━━━━━━━━━━━━━━━━━━━
🚀 تم تشغيل البوت بنجاح
⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 الإصدار: 3.0 (المتطور)
━━━━━━━━━━━━━━━━━━━━
    """
    send_to_admin(start_msg)
    
    command_handler = CommandHandler()
    last_update_id = 0
    last_news_check = 0
    last_report_time = time.time()
    last_stats_update = 0
    
    # حلقة التشغيل الرئيسية
    while True:
        try:
            current_time = time.time()
            
            # جلب ومعالجة التحديثات
            updates = get_updates(last_update_id + 1)
            for update in updates:
                last_update_id = update['update_id']
                
                # معالجة الرسائل
                if 'message' in update:
                    msg = update['message']
                    user_id = msg['from']['id']
                    text = msg.get('text', '')
                    username = msg['from'].get('username')
                    first_name = msg['from'].get('first_name')
                    
                    if text:
                        command_handler.handle(user_id, text, username, first_name)
                
                # معالجة ضغط الأزرار
                elif 'callback_query' in update:
                    callback = update['callback_query']
                    user_id = callback['from']['id']
                    data = callback.get('data')
                    if data:
                        handle_callback(user_id, data)
                    
                    # إرسال إشعار استلام الضغطة
                    telegram_bot.send_message(
                        callback['message']['chat']['id'],
                        "✅ تم استلام طلبك"
                    )
            
            # التحقق من الأخبار الجديدة (كل 10 ثواني)
            if current_time - last_news_check >= BOT_CONFIG['NEWS_CHECK_INTERVAL']:
                last_news_check = current_time
                
                # جلب الأخبار
                news = news_manager.get_latest_news()
                
                # تحديث آخر فحص
                stats = load_json(STATS_FILE, {})
                stats['last_check_time'] = datetime.now().strftime("%H:%M:%S")
                
                if news:
                    # تحديث آخر خبر
                    stats['last_news'] = news['title'][:50] + "..."
                    
                    # إرسال تحديث للمشرف
                    if news != news_manager.last_news:
                        AdminNotifier.send_news_update(news)
                        
                        # جلب بيانات السوق والتحليل الفني
                        market = market_analyzer.get_market_data(news['symbol'])
                        technical = market_analyzer.calculate_technical_indicators(news['symbol'])
                        
                        if market and technical:
                            # توليد الإشارة
                            signal = signal_generator.generate_signal(news, market, technical)
                            
                            if signal:
                                # تنسيق وإرسال الإشارة
                                signal_message = signal_generator.format_signal_message(signal)
                                
                                # إرسال للقناة
                                telegram_bot.send_message(CHANNEL_USERNAME, signal_message)
                                
                                # بث للمستخدمين
                                sent, failed = telegram_bot.broadcast(signal_message)
                                
                                # تحديث الإحصائيات
                                stats['total_signals'] = stats.get('total_signals', 0) + 1
                                stats['signals_today'] = stats.get('signals_today', 0) + 1
                                stats['last_signal_time'] = datetime.now().strftime("%H:%M:%S")
                                
                                # إرسال تقرير للمشرف
                                AdminNotifier.send_signal_report(signal, sent)
                                
                                logger.info(f"✅ إشارة جديدة: {news['symbol']} - ثقة: {int(signal['confidence']*100)}%")
                    
                    news_manager.last_news = news
                
                save_json(STATS_FILE, stats)
            
            # إرسال تقرير دوري للمشرف
            if current_time - last_report_time >= BOT_CONFIG['REPORT_INTERVAL']:
                panel = get_admin_panel()
                if panel.get('notifications_enabled', True):
                    report = AdminNotifier.send_detailed_report()
                    send_to_admin(report)
                last_report_time = current_time
            
            # تحديث إحصائيات اليوم
            stats = load_json(STATS_FILE, {})
            if stats.get('date_reset') != str(datetime.now().date()):
                stats['signals_today'] = 0
                stats['api_calls_today'] = 0
                stats['messages_sent_today'] = 0
                stats['date_reset'] = str(datetime.now().date())
                save_json(STATS_FILE, stats)
            
            # تحديث وقت التشغيل
            start_time = datetime.fromisoformat(stats.get('bot_start_time', datetime.now().isoformat()))
            stats['uptime'] = str(datetime.now() - start_time).split('.')[0]
            
            # نوم قصير
            time.sleep(BOT_CONFIG['CHECK_INTERVAL'])
            
        except KeyboardInterrupt:
            logger.info("🛑 إيقاف البوت...")
            send_to_admin("🛑 *تم إيقاف البوت*")
            break
            
        except Exception as e:
            logger.error(f"خطأ رئيسي: {e}")
            
            # إرسال تقرير الخطأ للمشرف
            AdminNotifier.send_error_report(str(e), {
                'time': datetime.now().strftime('%H:%M:%S'),
                'last_update': last_update_id
            })
            
            # انتظار قبل إعادة المحاولة
            time.sleep(180)

if __name__ == "__main__":
    main()
