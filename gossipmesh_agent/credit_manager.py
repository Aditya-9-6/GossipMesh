import os
import redis
from typing import Literal
from .utils import logger, load_dotenv

load_dotenv()

# Redis connection (shared across module)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL)

UNLIMITED_ACCOUNTS = [
    acc.strip().lower() for acc in os.getenv("UNLIMITED_ACCOUNTS", "Aditya-9-6").split(",") if acc.strip()
]


def is_unlimited(repo: str) -> bool:
    """Check if the repository or organization is on the unlimited tier."""
    if not repo:
        return False
    repo_lower = repo.lower()
    # Matches "Aditya-9-6" or any repo owned by user "Aditya-9-6/..."
    return any(repo_lower.startswith(f"{acc}/") or repo_lower == acc for acc in UNLIMITED_ACCOUNTS)


def get_credit_balance(repo: str) -> int:
    """Retrieve current credit balance from Redis."""
    try:
        val = redis_client.hget(f"credits:{repo}", "balance")
        return int(val) if val else 0
    except Exception:
        return 0


def lock_credits(repo: str, task_type: Literal["issue_scan", "pr_review", "auto_fix"]) -> bool:
    """Deduct the appropriate credit amount (2 or 3) atomically using Redis.
    For whitelisted unlimited accounts (e.g. Aditya-9-6), credits are tracked
    continuously with an infinite auto-replenishing reserve so tasks never fail.
    """
    cost_map = {
        "issue_scan": 2,
        "pr_review": 2,
        "auto_fix": 3,
    }
    cost = cost_map.get(task_type, 0)
    if cost == 0:
        logger.error("Unknown task_type %s for credit locking", task_type)
        return False

    unlimited = is_unlimited(repo)

    # If account is on the unlimited tier, auto-replenish buffer if low
    if unlimited:
        try:
            curr_bal = get_credit_balance(repo)
            if curr_bal < 100:
                redis_client.hset(f"credits:{repo}", "balance", 999999)
                redis_client.hset(f"credits:{repo}", "tier", "UNLIMITED_VIP")
        except Exception as e:
            logger.debug("Unlimited buffer replenish notice: %s", e)

    # Lua script: check balance >= cost then decrement, else return 0
    lua = """
    local key = KEYS[1]
    local field = ARGV[1]
    local cost = tonumber(ARGV[2])
    local is_unlimited = ARGV[3]
    local bal = tonumber(redis.call('HGET', key, field) or '0')

    if is_unlimited == '1' or bal >= cost then
        redis.call('HINCRBY', key, field, -cost)
        return 1
    else
        return 0
    end
    """
    try:
        result = redis_client.eval(lua, 1, f"credits:{repo}", "balance", str(cost), "1" if unlimited else "0")
        if result == 1:
            tier_str = " (Unlimited VIP Tier)" if unlimited else ""
            logger.info("Locked %d credits for %s%s – task %s", cost, repo, tier_str, task_type)
            return True
        else:
            logger.warning("Insufficient credits for %s – required %d", repo, cost)
            return False
    except Exception:
        logger.exception("Error locking credits for %s", repo)
        return False


def release_credits(repo: str, task_type: str) -> None:
    """Refund credits (used when a job is cancelled before any work or crashed)."""
    cost_map = {"issue_scan": 2, "pr_review": 2, "auto_fix": 3}
    cost = cost_map.get(task_type, 0)
    if cost == 0:
        logger.error("Unknown task_type %s for credit release", task_type)
        return
    try:
        redis_client.hincrby(f"credits:{repo}", "balance", cost)
        logger.info("Released %d credits for %s – task %s", cost, repo, task_type)
    except Exception:
        logger.exception("Error releasing credits for %s", repo)
