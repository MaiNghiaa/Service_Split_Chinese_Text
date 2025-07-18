# Tối ưu hóa FastAPI Chinese Segmentation API

## Các tối ưu hóa đã thực hiện

### 1. Resource Limits trong Docker Compose
- Giới hạn CPU: 1.0 core (tối đa)
- Giới hạn Memory: 1GB (tối đa)
- Đảm bảo tối thiểu: 0.5 CPU core, 512MB RAM

### 2. Code Optimization
- **Caching**: Sử dụng `@lru_cache` cho jieba và pinyin
- **Async Processing**: Xử lý bất đồng bộ với semaphore
- **Connection Pooling**: Giới hạn concurrent requests
- **Gzip Compression**: Nén response cho giảm bandwidth

### 3. Docker Optimization
- Multi-stage build để giảm image size
- Non-root user để tăng security
- Optimized uvicorn settings

### 4. Monitoring & Auto-restart
- Health check endpoint
- Resource monitoring script
- Auto-restart khi quá tải

## Cách sử dụng

### 1. Build và chạy
```bash
cd API_Split_chinese
docker-compose up -d --build
```

### 2. Chạy monitoring (tùy chọn)
```bash
./monitor.sh
```

### 3. Kiểm tra health
```bash
curl http://localhost:8058/health
```

## Monitoring Commands

### Kiểm tra resource usage
```bash
docker stats fastapi-segment
```

### Xem logs
```bash
docker-compose logs -f fastapi-app
```

### Restart container
```bash
docker-compose restart
```

## Performance Tips

1. **Cache**: API đã được cache để tránh tính toán lại
2. **Batch Processing**: Gửi nhiều câu cùng lúc thay vì từng câu một
3. **Connection Pooling**: Giới hạn 100 concurrent requests
4. **Resource Limits**: Container sẽ restart nếu vượt quá ngưỡng

## Troubleshooting

### Nếu CPU vẫn cao:
1. Giảm `--limit-concurrency` trong Dockerfile
2. Tăng `MAX_CPU_PERCENT` trong monitor.sh
3. Kiểm tra có process nào khác đang chạy không

### Nếu Memory vẫn cao:
1. Giảm cache size trong `@lru_cache(maxsize=10000)`
2. Tăng memory limit trong docker-compose.yml
3. Kiểm tra memory leak

### Nếu API chậm:
1. Kiểm tra network latency
2. Tăng worker processes (chỉ khi có nhiều CPU cores)
3. Optimize database queries (nếu có) 