FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
COPY offline_checker.py .
COPY dashboard_manager.py .
EXPOSE 8000
