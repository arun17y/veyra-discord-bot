FROM node:18-bullseye

# Install Python 3 & build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    ffmpeg \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project dependencies
COPY package*.json ./
RUN npm install --production

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt || true

COPY . .

EXPOSE 3000

CMD ["node", "web/server.js"]
