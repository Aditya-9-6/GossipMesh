import base64
import os

os.environ["SECRET_KEY"] = "testsecretkey"
os.environ["ENCRYPTION_KEY"] = base64.urlsafe_b64encode(b"A" * 32).decode("utf-8")
os.environ["POSTGRES_USER"] = "test"
os.environ["POSTGRES_PASSWORD"] = "test"
os.environ["POSTGRES_HOST"] = "test"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "test"

import time

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from gossipmesh.api import deps
from gossipmesh.api.routers.organizations import router as organizations_router
from gossipmesh.api.routers.providers import router as providers_router
from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.user import User

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app = FastAPI()
app.include_router(providers_router, prefix="/providers")
app.include_router(organizations_router, prefix="/organizations")
app.dependency_overrides[deps.get_db] = override_get_db

# We don't override deps.get_current_user to make sure we don't cheat by pre-fetching
# But since we can't easily mock the token verification without it, we override it to return a lazily fetched user
# Actually, the user object is already queried within get_current_user:
# user = db.query(User).filter(User.id == token_data).first()
# This doesn't eagerly load organizations. So any access to current_user.organizations will trigger a lazy load
# which can lead to N+1 queries down the line.

def override_get_current_user(db: Session = Depends(override_get_db)):
    user = db.query(User).filter(User.id == 1).first()
    return user

app.dependency_overrides[deps.get_current_user] = override_get_current_user

# Setup data
db = TestingSessionLocal()
user = User(email="test@example.com", hashed_password="pw")
db.add(user)
db.commit()
db.refresh(user)

num_orgs = 50
for i in range(num_orgs):
    org = Organization(name=f"Org {i}")
    db.add(org)
    db.commit()
    db.refresh(org)
    user_org = UserOrganization(user_id=user.id, organization_id=org.id, role="member")
    db.add(user_org)
db.commit()
db.close()

# Count queries
query_count = 0
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    global query_count
    # Count ALL queries
    if "SELECT" in statement:
        query_count += 1

client = TestClient(app)

# Warmup
try:
    client.get("/organizations/me")
except Exception:
    pass

try:
    client.get("/providers/health?organization_id=1")
except Exception:
    pass

def run_benchmark(endpoint, num_iterations=10):
    global query_count

    total_time = 0
    total_queries = 0

    for _ in range(num_iterations):
        query_count = 0
        start = time.time()

        try:
            client.get(endpoint)
        except Exception:
            pass

        end = time.time()

        total_time += (end - start)
        total_queries += query_count

    avg_time = total_time / num_iterations
    avg_queries = total_queries / num_iterations

    return avg_time, avg_queries

if __name__ == "__main__":
    avg_time_orgs, avg_queries_orgs = run_benchmark("/organizations/me")
    print(f"BASELINE Organizations - Avg Time: {avg_time_orgs:.4f}s, Avg Queries: {avg_queries_orgs}")
    avg_time_providers, avg_queries_providers = run_benchmark("/providers/health?organization_id=1")
    print(f"BASELINE Providers - Avg Time: {avg_time_providers:.4f}s, Avg Queries: {avg_queries_providers}")
