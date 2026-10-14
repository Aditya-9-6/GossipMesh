import os

# Set dummy test values for required configuration variables
# Note: ENCRYPTION_KEY must be exactly 32 url-safe base64-encoded bytes (Fernet key requirement)
os.environ["ENCRYPTION_KEY"] = "b_wH5yL7g3XQz8T1kVcZp6sN0mR9dE2fA4uYxWqVjMw="
os.environ["SECRET_KEY"] = "supersecretkey_please_change_in_production"
os.environ["POSTGRES_USER"] = "testuser"
os.environ["POSTGRES_PASSWORD"] = "testpass"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "testdb"
os.environ["POSTGRES_USER"] = "test"
os.environ["POSTGRES_PASSWORD"] = "test"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "test"
