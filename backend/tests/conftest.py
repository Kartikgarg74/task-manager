"""Points the test suite at its own database, never the dev one — must run
before anything imports app.database (which creates its engine at import
time from whatever DATABASE_URL is set right now).
"""

import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://kartikgarg@localhost:5432/task_manager_test"
