with open("gossipmesh/api/routers/service_accounts.py", "r") as f:
    content = f.read()

content = content.replace('    account = db.query(ServiceAccount).filter(ServiceAccount.id == api_key.service_account_id).first()\n    _ensure_org_access(db, current_user.id, account.organization_id)', '    account = db.query(ServiceAccount).filter(ServiceAccount.id == api_key.service_account_id).first()\n    if not account:\n        raise HTTPException(status_code=404, detail="Service account not found")\n    _ensure_org_access(db, current_user.id, account.organization_id)')

with open("gossipmesh/api/routers/service_accounts.py", "w") as f:
    f.write(content)
