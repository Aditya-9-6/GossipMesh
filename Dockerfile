FROM python:3.12-slim
WORKDIR /app
RUN useradd -ms /bin/bash gossipmesh
COPY . /app
RUN pip install --no-cache-dir -e .
USER gossipmesh
CMD ["python", "-m", "gossipmesh.main"]
