# Usa Python 3.12 slim como base
FROM python:3.12-slim

# Crea y usa /app como directorio de trabajo
WORKDIR /app

# Instala dependencias del sistema (Chrome, Supervisor, etc.)
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    xdg-utils \
    build-essential \
    supervisor \
    libffi-dev \
    libssl-dev \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Agrega la clave y el repositorio de Google Chrome
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub \
        | tee /etc/apt/keyrings/google-chrome.asc > /dev/null && \
    echo "deb [signed-by=/etc/apt/keyrings/google-chrome.asc] http://dl.google.com/linux/chrome/deb/ stable main" \
        | tee /etc/apt/sources.list.d/google-chrome.list

# Instala Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Obtiene la versión de Chrome y descarga ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    CHROME_MAJOR_VERSION=$(echo "$CHROME_VERSION" | cut -d '.' -f1) && \
    CHROMEDRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
    echo "🔹 Chrome version: $CHROME_VERSION" && \
    if wget --spider "$CHROMEDRIVER_URL" 2>/dev/null; then \
        wget -q "$CHROMEDRIVER_URL" -O /tmp/chromedriver.zip && \
        unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
        rm /tmp/chromedriver.zip && \
        chmod +x /usr/local/bin/chromedriver-linux64 && \
        mv /usr/local/bin/chromedriver-linux64 /usr/local/bin/chromedriver; \
    else \
        echo "⚠️ No se encontró ChromeDriver para la versión $CHROME_VERSION. Usando API antigua..." && \
        CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_MAJOR_VERSION") && \
        CHROMEDRIVER_URL_OLD="https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" && \
        wget -q "$CHROMEDRIVER_URL_OLD" -O /tmp/chromedriver.zip && \
        unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
        rm /tmp/chromedriver.zip && \
        chmod +x /usr/local/bin/chromedriver; \
    fi

# Actualiza pip, setuptools y wheel
RUN pip install --upgrade pip setuptools wheel

# Copia e instala dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el archivo de configuración de Supervisor
COPY supervisord.conf /etc/supervisor/supervisord.conf

# Copia todo el resto de la aplicación
COPY . .

# (Opcional) Crea un usuario sin privilegios y cambia a él
RUN adduser --disabled-password --gecos '' myuser
USER myuser

# Variables de entorno (si usas Chrome o Celery que las requiera)
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_BIN=/usr/local/bin/chromedriver
ENV DISPLAY=:99

# Inicia Supervisor con la configuración (Celery + Servidor HTTP dummy)
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
