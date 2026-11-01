FROM python:3.12-slim

WORKDIR /app

RUN useradd -m -u 1000 gossipmesh && \
    chown -R gossipmesh:gossipmesh /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER gossipmesh

EXPOSE 8000
CMD ["python", "-m", "gossipmesh.main"]
