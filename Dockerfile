FROM python:3.11-slim

WORKDIR /app

# تثبيت المكتبات المطلوبة
RUN pip install --no-cache-dir \
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

# تشغيل البوت
CMD ["python", "Bot.py"]
