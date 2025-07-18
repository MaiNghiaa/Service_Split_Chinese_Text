#!/bin/bash

# Script monitoring cho FastAPI container - Tối ưu cho máy yếu
CONTAINER_NAME="fastapi-segment"
MAX_CPU_PERCENT=60      # Giảm từ 80 xuống 60
MAX_MEMORY_PERCENT=70   # Giảm từ 85 xuống 70

echo "Starting monitoring for $CONTAINER_NAME (Low-resource mode)..."

while true; do
    # Kiểm tra container có đang chạy không
    if ! docker ps | grep -q $CONTAINER_NAME; then
        echo "$(date): Container $CONTAINER_NAME is not running. Restarting..."
        docker-compose up -d
        sleep 60  # Tăng thời gian chờ
        continue
    fi
    
    # Lấy thông tin CPU và Memory
    CPU_PERCENT=$(docker stats --no-stream --format "table {{.CPUPerc}}" $CONTAINER_NAME | tail -n 1 | sed 's/%//')
    MEMORY_PERCENT=$(docker stats --no-stream --format "table {{.MemPerc}}" $CONTAINER_NAME | tail -n 1 | sed 's/%//')
    
    # Loại bỏ ký tự không phải số
    CPU_PERCENT=$(echo $CPU_PERCENT | tr -cd '0-9.')
    MEMORY_PERCENT=$(echo $MEMORY_PERCENT | tr -cd '0-9.')
    
    echo "$(date): CPU: ${CPU_PERCENT}%, Memory: ${MEMORY_PERCENT}%"
    
    # Kiểm tra nếu vượt quá ngưỡng
    if (( $(echo "$CPU_PERCENT > $MAX_CPU_PERCENT" | bc -l) )) || (( $(echo "$MEMORY_PERCENT > $MAX_MEMORY_PERCENT" | bc -l) )); then
        echo "$(date): High resource usage detected. Restarting container..."
        docker-compose restart
        sleep 120  # Tăng thời gian chờ sau restart
    fi
    
    # Kiểm tra health check
    if ! curl -f http://localhost:8058/health > /dev/null 2>&1; then
        echo "$(date): Health check failed. Restarting container..."
        docker-compose restart
        sleep 60
    fi
    
    # Kiểm tra memory usage của hệ thống
    SYSTEM_MEMORY=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ "$SYSTEM_MEMORY" -gt 90 ]; then
        echo "$(date): System memory usage is ${SYSTEM_MEMORY}%. Clearing Docker cache..."
        docker system prune -f
        sleep 30
    fi
    
    sleep 120  # Tăng interval từ 60s lên 120s
done 