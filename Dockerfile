FROM python:3.11-slim

WORKDIR /app

# تثبيت المكتبات المطلوبة - مع التأكد من اسم المكتبة الصحيح
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        python-telegram-bot \
        requests \
        aiohttp \
        beautifulsoup4 \
        fake-useragent \
        Faker \
        colorama \
        pyfiglet \
        cfonts \
        user_agent

# نسخ ملف البوت
COPY Bot.py .

# التحقق من التثبيت (باستخدام الاسم الصحيح للاستيراد)
RUN python -c "import telegram; print('✅ telegram module installed')" && \
    python -c "from telegram.ext import Application; print('✅ telegram.ext works')"

# تشغيل البوت
CMD ["python", "Bot.py"]
