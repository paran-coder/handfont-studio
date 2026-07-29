FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-venv libcairo2 libfontconfig1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY requirements.txt ./
RUN python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt
COPY worker ./worker
COPY engine ./engine
COPY queue-consumer.mjs docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["./docker-entrypoint.sh"]
