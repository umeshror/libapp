FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Copy all files
COPY . .

# Build the Next.js app
RUN npm run build

# Expose port 3003
EXPOSE 3003

# Start the application
CMD ["npm", "start", "--", "-p", "3003"]
