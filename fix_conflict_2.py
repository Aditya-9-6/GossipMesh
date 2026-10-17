with open("tests/test_runs.py", "r") as f:
    content = f.read()

conflict_block = """<<<<<<< Updated upstream
    response = client.post("/api/v1/runs/", json=run_data)
=======
    from gossipmesh.core.config import settings
    response = client.post(f"{settings.API_V1_STR}/runs/", json=run_data)
>>>>>>> Stashed changes"""

resolved_block = """    from gossipmesh.core.config import settings
    response = client.post(f"{settings.API_V1_STR}/runs/", json=run_data)"""

content = content.replace(conflict_block, resolved_block)

with open("tests/test_runs.py", "w") as f:
    f.write(content)
