FROM python:3.12-slim
WORKDIR /app
RUN useradd -u 10001 -m gossipmesh
COPY . /app
RUN pip install --no-cache-dir -e .
USER gossipmesh
CMD ["python", "-m", "gossipmesh.main"]
