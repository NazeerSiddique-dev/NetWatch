FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for scapy / pcap
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap-dev \
    iproute2 \
    bridge-utils \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
