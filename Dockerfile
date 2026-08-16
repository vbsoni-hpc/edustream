FROM python:3.11-slim

# Install system dependencies including Nginx and curl
RUN apt-get update && \
    apt-get install -y nginx curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Install and build Next.js frontend
WORKDIR /app/frontend
RUN npm install
RUN npm run build

# Reset working directory back to root for the start script
WORKDIR /app

# Make start script executable
RUN chmod +x /app/start.sh

# The main port exposed by Hugging Face Spaces / Render
EXPOSE 7860

# Run the startup script
CMD ["/app/start.sh"]
