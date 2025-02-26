FROM python:3.12-slim

# 1. Set workdir
WORKDIR /app

# 2. Copy project files
COPY . /app

# 3. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Supervisord config into the container
COPY supervisord.conf /etc/supervisord.conf

# 5. Use Supervisord as the main process
CMD ["supervisord", "-c", "/etc/supervisord.conf"]








