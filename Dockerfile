FROM python:3.12-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para Chrome y Selenium
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libasound2 \
    libnspr4 \
    xdg-utils \
    lsb-release \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Descargar e instalar Google Chrome estable
RUN wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome.deb && \
    rm google-chrome.deb

# Definir la versión específica de ChromeDriver compatible con Google Chrome
ENV CHROMEDRIVER_VERSION=114.0.5735.90

# Descargar e instalar ChromeDriver
RUN wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" && \
    unzip chromedriver_linux64.zip -d /usr/local/bin/ && \
    rm chromedriver_linux64.zip && \
    chmod +x /usr/local/bin/chromedriver

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear un usuario sin privilegios
RUN adduser --disabled-password --gecos '' myuser

# Cambiar al nuevo usuario
USER myuser

# Copiar el resto de la aplicación
COPY . .

# Ejecutar Celery
CMD ["celery", "-A", "bot_instagram", "worker", "--loglevel=info", "--concurrency=2", "--pool=solo"]












