FROM node:20-alpine
WORKDIR /frontend
COPY package.json package-lock.json* ./
RUN npm ci --silent || npm install
COPY . .
RUN npm run build
# Use port from Railway environment variable PORT or default 3000
CMD ["sh", "-c", "npx vite preview --port ${PORT:-3000} --host"]
