FROM node:20-alpine AS base
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source
COPY . .

# Development mode (default)
EXPOSE 3000
CMD ["npm", "run", "dev"]
