FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -u 10001 gossipuser && chown -R gossipuser:gossipuser /app
USER gossipuser
CMD ["python", "scripts/autonomous_loop.py"]
