with open("gossipmesh/worker/celery_app.py", "r") as f:
    content = f.read()

content = content.replace("from celery import Celery", "from celery import Celery  # type: ignore")

with open("gossipmesh/worker/celery_app.py", "w") as f:
    f.write(content)
