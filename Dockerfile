FROM python:3.9-slim
WORKDIR /app
COPY . .
CMD ["python3", "serve.py", "--host", "0.0.0.0", "--port", "8080"]
