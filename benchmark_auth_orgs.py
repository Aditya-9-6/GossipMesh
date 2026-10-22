import time
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.user import User

# Using an in-memory SQLite database
engine = create_engine('sqlite:///:memory:', connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_original():
    db = SessionLocal()
    org_names = [f"org_{i}" for i in range(100)]

    # Create a user
    user = User(email="test@test.com", hashed_password="hash")
    db.add(user)
    db.commit()
    db.refresh(user)

    start = time.time()
    # Map organizations
    for org_name in org_names:
        org = db.query(Organization).filter(Organization.name == org_name).first()
        if not org:
            org = Organization(name=org_name)
            db.add(org)
            db.commit()
            db.refresh(org)

        user_org = (
            db.query(UserOrganization)
            .filter(UserOrganization.user_id == user.id, UserOrganization.organization_id == org.id)
            .first()
        )

        if not user_org:
            user_org = UserOrganization(user_id=user.id, organization_id=org.id, role="member")
            db.add(user_org)

    db.commit()
    end = time.time()
    print(f"Original Code Time: {end - start:.4f}s")
    db.close()

def test_optimized():
    db = SessionLocal()
    org_names = [f"org_opt_{i}" for i in range(100)]

    # Create a user
    user = User(email="test_opt@test.com", hashed_password="hash")
    db.add(user)
    db.commit()
    db.refresh(user)

    start = time.time()

    # --- Optimized logic ---
    existing_orgs = db.query(Organization).filter(Organization.name.in_(org_names)).all()
    existing_orgs_by_name = {org.name: org for org in existing_orgs}

    new_orgs = []
    for org_name in org_names:
        if org_name not in existing_orgs_by_name:
            new_org = Organization(name=org_name)
            new_orgs.append(new_org)

    if new_orgs:
        db.add_all(new_orgs)
        db.commit()
        for org in new_orgs:
            existing_orgs_by_name[org.name] = org

    org_ids = [org.id for org in existing_orgs_by_name.values()]
    existing_user_orgs = db.query(UserOrganization).filter(
        UserOrganization.user_id == user.id,
        UserOrganization.organization_id.in_(org_ids)
    ).all()

    existing_user_orgs_by_org_id = {uo.organization_id: uo for uo in existing_user_orgs}

    new_user_orgs = []
    for org_id in org_ids:
        if org_id not in existing_user_orgs_by_org_id:
            new_user_orgs.append(UserOrganization(user_id=user.id, organization_id=org_id, role="member"))

    if new_user_orgs:
        db.add_all(new_user_orgs)
        db.commit()
    # --- End Optimized logic ---

    end = time.time()
    print(f"Optimized Code Time: {end - start:.4f}s")
    db.close()

if __name__ == "__main__":
    test_original()
    test_optimized()
