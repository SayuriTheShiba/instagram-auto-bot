FROM python:3.12-slim

# 1. Set workdir
WORKDIR /app

# 2. Copy project files
COPY . /app

# 3. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 4. Run Celery directly
CMD ["celery", "-A", "bot_instagram", "worker", "--loglevel=info", "--concurrency=2", "--pool=solo"]









