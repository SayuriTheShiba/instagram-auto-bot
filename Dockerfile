# Usar imagen base de Python 3.12 slim
FROM python:3.12-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias necesarias para Selenium y Chrome
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
    libxss1 \
    xdg-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Agregar la clave y repositorio de Google Chrome
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | tee /etc/apt/keyrings/google-chrome.asc > /dev/null && \
    echo "deb [signed-by=/etc/apt/keyrings/google-chrome.asc] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list

# Instalar Google Chrome estable
RUN apt-get update && apt-get install -y google-chrome-stable --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Obtener la versión de Chrome y descargar el ChromeDriver correcto
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f1,2,3) && \
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION") && \
    wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" && \
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

# Ejecutar Celery con configuración optimizada
CMD ["celery", "-A", "bot_instagram", "worker", "--loglevel=info", "--concurrency=2", "--pool=solo"]











