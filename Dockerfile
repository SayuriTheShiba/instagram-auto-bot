# Utilizar la imagen base de Python
FROM python:3.12-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para Chrome y Selenium
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
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Agregar la clave y el repositorio de Google Chrome
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub | tee /etc/apt/keyrings/google-chrome.asc > /dev/null && \
    echo "deb [signed-by=/etc/apt/keyrings/google-chrome.asc] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list

# Instalar Google Chrome estable desde el repositorio oficial
RUN apt-get update && apt-get install -y google-chrome-stable --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Obtener la versión de Google Chrome instalada y descargar el ChromeDriver correcto
RUN export CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    export CHROME_MAJOR_VERSION=$(echo "$CHROME_VERSION" | cut -d '.' -f1) && \
    export CHROMEDRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
    echo "🔹 Versión de Google Chrome instalada: $CHROME_VERSION" && \
    echo "🔹 Intentando descargar ChromeDriver desde: $CHROMEDRIVER_URL" && \
    if wget --spider "$CHROMEDRIVER_URL" 2>/dev/null; then \
        wget -q "$CHROMEDRIVER_URL" -O /tmp/chromedriver.zip && \
        unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
        rm /tmp/chromedriver.zip && \
        chmod +x /usr/local/bin/chromedriver-linux64 && \
        mv /usr/local/bin/chromedriver-linux64 /usr/local/bin/chromedriver; \
    else \
        echo "⚠️ No se encontró ChromeDriver para la versión $CHROME_VERSION. Probando con la API antigua..." && \
        export CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_MAJOR_VERSION") && \
        export CHROMEDRIVER_URL_OLD="https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" && \
        wget -q "$CHROMEDRIVER_URL_OLD" -O /tmp/chromedriver.zip && \
        unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
        rm /tmp/chromedriver.zip && \
        chmod +x /usr/local/bin/chromedriver; \
    fi

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear un usuario sin privilegios para ejecutar la aplicación
RUN adduser --disabled-password --gecos '' myuser

# Cambiar al nuevo usuario
USER myuser

# Copiar el resto de la aplicación
COPY . .

# Definir variables de entorno para Chrome y ChromeDriver
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_BIN=/usr/local/bin/chromedriver
ENV DISPLAY=:99

# Ejecutar Celery y evitar que el contenedor se cierre en Railway
CMD ["sh", "-c", "celery -A bot_instagram worker --loglevel=info --concurrency=2 --pool=solo --without-heartbeat & while true; do sleep 30; done"]









