# Multi-stage build để giảm kích thước image
FROM python:3.10-slim as builder

WORKDIR /app

# Cài đặt dependencies cần thiết cho build
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài đặt Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.10-slim

WORKDIR /app

# Cài đặt curl cho health check và các tools cần thiết
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages từ builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . /app

# Tạo user không phải root để chạy ứng dụng
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8058

# Tối ưu hóa uvicorn settings cho máy yếu
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8058", "--workers", "1", "--limit-concurrency", "20", "--limit-max-requests", "500", "--backlog", "10"]

