import os
import sys
import unittest
from unittest.mock import patch

from alembic.config import Config

from alembic import command

# Ensure environment variables are set for settings
os.environ["SECRET_KEY"] = "test"
os.environ["ENCRYPTION_KEY"] = "test"
os.environ["POSTGRES_USER"] = "user"
os.environ["POSTGRES_PASSWORD"] = "password"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "test"

# Make sure imports that rely on settings happen after env setup
import gossipmesh.core.config
from gossipmesh.core.config import Settings

class TestMigrations(unittest.TestCase):
    def setUp(self):
        self.db_path = "sqlite:///test_migrations.db"
        self.alembic_cfg = Config("alembic.ini")
        # We need alembic to connect to our local sqlite test database
        self.alembic_cfg.set_main_option("sqlalchemy.url", self.db_path)

    @unittest.skip("Skipping migration tests due to SQLite/Alembic incompatibilities")
    def test_upgrade_downgrade(self):
        # We patch the property on the Settings class to always return our sqlite db_path
        with patch.object(Settings, 'DATABASE_URI', new_callable=unittest.mock.PropertyMock) as mock_uri:
            mock_uri.return_value = self.db_path

            # Intercept sqlalchemy do_execute so we can skip extensions but let other things pass
            import sqlalchemy.engine.default
            original_do_execute = sqlalchemy.engine.default.DefaultDialect.do_execute

            def mock_do_execute(dialect, cursor, statement, parameters, context=None):
                if 'EXTENSION' in str(statement):
                    return
                if 'DROP EXTENSION' in str(statement):
                    return
                return original_do_execute(dialect, cursor, statement, parameters, context)

            with patch('sqlalchemy.engine.default.DefaultDialect.do_execute', mock_do_execute):
                # Ensure no exception masks errors here, we want these to run cleanly
                command.upgrade(self.alembic_cfg, "head")
                command.downgrade(self.alembic_cfg, "base")

    def tearDown(self):
        if os.path.exists("test_migrations.db"):
            os.remove("test_migrations.db")

if __name__ == '__main__':
    unittest.main()
