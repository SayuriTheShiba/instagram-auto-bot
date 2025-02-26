# Usar la imagen base de Python
FROM python:3.12-slim

# 1. Establecer el directorio de trabajo
WORKDIR /app

# 2. Copiar los archivos del proyecto
COPY . /app

# 3. Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 4. Añadir la clave y el repositorio de Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# 5. Instalar Google Chrome
RUN apt-get update && apt-get install -y \
    google-chrome-stable \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 6. Descargar e instalar ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+') && \
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION") && \
    wget -q --continue -P /usr/local/bin/ "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" && \
    unzip /usr/local/bin/chromedriver_linux64.zip -d /usr/local/bin/ && \
    rm /usr/local/bin/chromedriver_linux64.zip && \
    chmod +x /usr/local/bin/chromedriver

# 7. Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# 8. Crear un usuario sin privilegios
RUN adduser --disabled-password --gecos '' myuser

# 9. Cambiar al nuevo usuario
USER myuser

# 10. Establecer la variable de entorno para Chrome en modo sin cabeza
ENV DISPLAY=:99

# 11. Comando para ejecutar Celery
CMD ["celery", "-A", "bot_instagram", "worker", "--loglevel=info", "--concurrency=2", "--pool=solo"]










