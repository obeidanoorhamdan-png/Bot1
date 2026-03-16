FROM python:3.11-slim

WORKDIR /app

# تثبيت المكتبات المطلوبة - مع إضافة pyTelegramBotAPI
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        python-telegram-bot \
        pyTelegramBotAPI \
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

# التحقق من التثبيت
RUN python -c "import telebot; print('✅ Telebot installed successfully')"

# تشغيل البوت
CMD ["python", "Bot.py"]
