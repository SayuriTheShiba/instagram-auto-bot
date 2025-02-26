# Usa una imagen base de Python
FROM python:3.12-slim

# Configurar el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar los archivos del proyecto al contenedor
COPY . /app

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Comando para iniciar Celery como worker
CMD ["sh", "-c", "celery -A bot_instagram worker --loglevel=info --uid=nobody"]


