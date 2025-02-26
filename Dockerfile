FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

COPY supervisord.conf /etc/supervisord.conf
CMD ["sh", "-c", "while true; do celery -A bot_instagram worker --loglevel=info; sleep 5; done"]








