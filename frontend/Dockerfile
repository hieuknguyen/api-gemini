FROM node:20-alpine

WORKDIR /app

# Sao chép package.json và package-lock.json để cài đặt dependencies
COPY package*.json ./
RUN npm install

# Sao chép toàn bộ mã nguồn frontend
COPY . .

# Expose cổng Vite Dev Server
EXPOSE 5173

# Khởi chạy Vite với host 0.0.0.0
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
