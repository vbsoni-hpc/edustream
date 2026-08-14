FROM python:3.11-slim

# Install system dependencies including Nginx
RUN apt-get update && \
    apt-get install -y nginx && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make start script executable
RUN chmod +x /app/start.sh

# The main port exposed by Hugging Face Spaces / Render
EXPOSE 7860

# Run the startup script
CMD ["/app/start.sh"]
