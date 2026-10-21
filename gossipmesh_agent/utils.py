import logging
import os
from pathlib import Path

logger = logging.getLogger("gossipmesh_agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

def slugify(text: str) -> str:
    """Simple slug generator for branch names / file prefixes."""
    import re
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def load_dotenv() -> None:
    """Load environment variables from a `.env` file if present (useful for local dev)."""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parents[1] / ".env"
        if env_path.is_file():
            load_dotenv(dotenv_path=env_path)
            logger.info("Loaded .env file from %s", env_path)
    except Exception as e:
        logger.debug("Could not load dotenv: %s", e)
