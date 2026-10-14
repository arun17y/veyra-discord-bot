FROM python:3.11-slim

# Install Node.js 18, FFmpeg, and Opus audio codecs for music playback on Linux
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    build-essential \
    ffmpeg \
    libopus0 \
    libopus-dev && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production


# Install Python requirements (discord.py, psycopg2-binary, etc.)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Node dependencies (pg, express, cors, etc.)
COPY package*.json ./
RUN npm install --omit=dev --omit=optional



COPY . .

EXPOSE 3000

CMD ["node", "web/server.js"]
