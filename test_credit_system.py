import os
import sys

sys.path.insert(0, os.path.abspath("."))

from gossipmesh_agent.credit_manager import lock_credits, get_credit_balance, is_unlimited

print("Is Aditya-9-6/GossipMesh unlimited?", is_unlimited("Aditya-9-6/GossipMesh"))
print("Is otheruser/project unlimited?", is_unlimited("otheruser/project"))

# Test lock on unlimited repo
res1 = lock_credits("Aditya-9-6/GossipMesh", "auto_fix")
print(f"Auto-fix lock for Aditya-9-6 (cost 3): {res1}")
print(f"Remaining balance for Aditya-9-6: {get_credit_balance('Aditya-9-6/GossipMesh')}")

# Test lock on an empty external repo (should fail as expected)
res2 = lock_credits("unknown/demo-empty-repo", "auto_fix")
print(f"Lock for uncredited external repo: {res2}")
