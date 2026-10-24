from celery import Celery


class CeleryStub:
    broker_url: str = "redis://localhost:6379/0"

    def task(self, *args, **kwargs):
        def decorator(f):
            return f

        return decorator


celery_app = CeleryStub()
app = celery_app
