import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

def load_tos_config() -> Dict[str, Any]:
    """Loads TOS configuration.

    Returns:
        TOS configuration dictionary.

    Raises:
        ValueError: When required environment variables are missing.
    """
    tos_config = {
        "access_key": os.getenv("TOS_ACCESS_KEY"),
        "secret_key": os.getenv("TOS_SECRET_KEY"),
        "endpoint": os.getenv("TOS_ENDPOINT", "tos-cn-beijing.volces.com"),
        "region": os.getenv("TOS_REGION", "cn-beijing"),
        "bucket_name": os.getenv("TOS_BUCKET_NAME"),
    }

    # Validate required configuration
    required_keys = ["access_key", "secret_key", "bucket_name"]
    missing_keys = [key for key in required_keys if not tos_config.get(key)]

    if missing_keys:
        env_vars = {
            "access_key": "TOS_ACCESS_KEY",
            "secret_key": "TOS_SECRET_KEY",
            "bucket_name": "TOS_BUCKET_NAME",
        }
        missing_vars = [env_vars[key] for key in missing_keys]
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    return tos_config