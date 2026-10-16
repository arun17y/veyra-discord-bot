FROM python:3.11-slim

# Install Node.js 18, FFmpeg, Opus, Git, Unzip, Deno, and bgutil-pot for YouTube PO Token generation
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    build-essential \
    ffmpeg \
    libopus0 \
    libopus-dev \
    git \
    unzip && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    curl -fsSL -o /tmp/deno.zip "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip" && \
    unzip /tmp/deno.zip -d /usr/local/bin && \
    chmod +x /usr/local/bin/deno && \
    rm -f /tmp/deno.zip && \
    curl -L -o /usr/local/bin/bgutil-pot "https://github.com/jim60105/bgutil-ytdlp-pot-provider-rs/releases/download/v0.8.1/bgutil-pot-linux-x86_64" && \
    chmod +x /usr/local/bin/bgutil-pot && \
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
