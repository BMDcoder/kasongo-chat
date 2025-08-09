FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --silent || npm install
COPY . .
RUN npm run build
CMD ["npx","vite","preview","--port", "3000", "--host"]
