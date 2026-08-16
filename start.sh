#!/bin/bash

# Run bootstrap: restore backup from Telegram + sync videos
echo "Running bootstrap (restore + sync)..."
python -m backend.bootstrap
echo "Bootstrap complete."

# Start FastAPI server in the background
echo "Starting FastAPI backend..."
uvicorn backend.server:app --host 127.0.0.1 --port 8000 &
FASTAPI_PID=$!

# Start Next.js frontend in the background
echo "Starting Next.js frontend..."
cd frontend
npm start &
NEXTJS_PID=$!
cd ..

# Replace the port in nginx.conf
export PORT=${PORT:-10000}
sed -i "s/\${PORT}/$PORT/g" /app/nginx.conf

# Start Nginx in the foreground
echo "Starting Nginx on port $PORT..."
nginx -g 'daemon off;' -c /app/nginx.conf
