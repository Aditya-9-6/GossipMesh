import sys

with open('gossipmesh/api/main.py', 'r') as f:
    content = f.read()

content = content.replace('''<<<<<<< HEAD
from gossipmesh.api.routers import auth, users, organizations, providers, repositories, runtime, artifacts, enterprise, vector_search
=======
from gossipmesh.api.routers import auth, users, organizations, providers, repositories, runtime, service_accounts, sso, scim
>>>>>>> origin/main''', '''from gossipmesh.api.routers import auth, users, organizations, providers, repositories, runtime, artifacts, enterprise, vector_search, service_accounts, sso, scim''')

content = content.replace('''<<<<<<< HEAD
app.include_router(artifacts.router, prefix=f"{settings.API_V1_STR}/artifacts", tags=["artifacts"])
app.include_router(enterprise.router, prefix=f"{settings.API_V1_STR}/enterprise", tags=["enterprise"])
app.include_router(vector_search.router, prefix=f"{settings.API_V1_STR}/vector_search", tags=["vector_search"])
=======
app.include_router(service_accounts.router, prefix=f"{settings.API_V1_STR}/service-accounts", tags=["service-accounts"])
app.include_router(sso.router, prefix=f"{settings.API_V1_STR}/sso", tags=["sso"])
app.include_router(scim.router, prefix=f"{settings.API_V1_STR}/scim/v2", tags=["scim"])
>>>>>>> origin/main''', '''app.include_router(artifacts.router, prefix=f"{settings.API_V1_STR}/artifacts", tags=["artifacts"])
app.include_router(enterprise.router, prefix=f"{settings.API_V1_STR}/enterprise", tags=["enterprise"])
app.include_router(vector_search.router, prefix=f"{settings.API_V1_STR}/vector_search", tags=["vector_search"])
app.include_router(service_accounts.router, prefix=f"{settings.API_V1_STR}/service-accounts", tags=["service-accounts"])
app.include_router(sso.router, prefix=f"{settings.API_V1_STR}/sso", tags=["sso"])
app.include_router(scim.router, prefix=f"{settings.API_V1_STR}/scim/v2", tags=["scim"])''')

with open('gossipmesh/api/main.py', 'w') as f:
    f.write(content)
