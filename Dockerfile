# Usar la imagen base de Python
FROM python:3.12-slim

# Crear directorio de trabajo
WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación
COPY . .

# Exponer el puerto (Railway usará la variable $PORT, pero EXPOSE es informativo)
EXPOSE 5000

# Comando para iniciar la app Flask
CMD ["gunicorn", "-b", "0.0.0.0:$PORT", "app:app"]


