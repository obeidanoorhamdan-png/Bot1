FROM python:3.11-slim

WORKDIR /app

# تثبيت المتطلبات الأساسية للنظام (لـ Selenium و Chrome)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxshmfence1 \
    libxtst6 \
    libxss1 \
    libxkbcommon0 \
    libxkbcommon-x11-0 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# تثبيت المكتبات المطلوبة للبايثون
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
        user_agent \
        selenium \
        webdriver-manager

# إنشاء المجلدات المطلوبة
RUN mkdir -p /app/data /app/backups /app/temp

# نسخ ملف البوت
COPY Bot.py .

# التحقق من التثبيت
RUN python -c "import telebot; print('✅ Telebot installed successfully')" && \
    python -c "from selenium import webdriver; print('✅ Selenium installed successfully')"

# متغيرات البيئة
ENV PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_BIN=/usr/bin/chromedriver

# تشغيل Xvfb ثم البوت
CMD Xvfb :99 -screen 0 1280x1024x24 & \
    export DISPLAY=:99 && \
    python Bot.py
