import os

def get_env_flag(flag_name):
    """Get the value of an environment flag, defaulting to False if not set."""
    return os.getenv(flag_name, "false").lower() == "true"


# Environment-controlled flags
GOSSIPMESH_AUTOMATION_ENABLED = get_env_flag("GOSSIPMESH_AUTOMATION_ENABLED")
GOSSIPMESH_ALLOW_PR_CREATION = get_env_flag("GOSSIPMESH_ALLOW_PR_CREATION")
GOSSIPMESH_ALLOW_PUSH = get_env_flag("GOSSIPMESH_ALLOW_PUSH")
GOSSIPMESH_ALLOW_FORCE_PUSH = get_env_flag("GOSSIPMESH_ALLOW_FORCE_PUSH")
GOSSIPMESH_ALLOW_AUTO_MERGE = get_env_flag("GOSSIPMESH_ALLOW_AUTO_MERGE")
GOSSIPMESH_MAX_FILES_PER_CHANGE = int(os.getenv("GOSSIPMESH_MAX_FILES_PER_CHANGE", "10"))
GOSSIPMESH_MAX_DAILY_RUNS = int(os.getenv("GOSSIPMESH_MAX_DAILY_RUNS", "100"))
GOSSIPMESH_MAX_DAILY_PR_CREATION = int(os.getenv("GOSSIPMESH_MAX_DAILY_PR_CREATION", "10"))

# Default PR creation, push, force-push, and auto-merge to disabled
if not GOSSIPMESH_ALLOW_PR_CREATION:
    print("PR creation is disabled.")
if not GOSSIPMESH_ALLOW_PUSH:
    print("Push is disabled.")
if not GOSSIPMESH_ALLOW_FORCE_PUSH:
    print("Force push is disabled.")
if not GOSSIPMESH_ALLOW_AUTO_MERGE:
    print("Auto merge is disabled.")

# Add checks in autonomous scripts
# ... (add your autonomous script checks here)

# Add tests for the new behavior
# ... (add your tests here)
