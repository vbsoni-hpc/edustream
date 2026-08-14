#!/bin/bash

# Start FastAPI server in the background
echo "Starting FastAPI backend..."
uvicorn backend.server:app --host 127.0.0.1 --port 8000 &
FASTAPI_PID=$!

# Start Streamlit frontend in the background
echo "Starting Streamlit frontend..."
streamlit run app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true --server.enableCORS false --server.enableXsrfProtection false --server.fileWatcherType none &
STREAMLIT_PID=$!

# Replace the port in nginx.conf
export PORT=${PORT:-10000}
sed -i "s/\${PORT}/$PORT/g" /app/nginx.conf

# Start Nginx in the foreground
echo "Starting Nginx on port $PORT..."
nginx -g 'daemon off;' -c /app/nginx.conf
