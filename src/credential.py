import getpass
import os
from pathlib import Path

from dotenv import load_dotenv, set_key as dotenv_set_key, unset_key

ENV_FILE = Path(".env")
ENV_KEY = "DEEPSEEK_API_KEY"


def get_key() -> str | None:
    load_dotenv(ENV_FILE)
    return os.environ.get(ENV_KEY)


def set_key() -> None:
    key = getpass.getpass("Enter API Key: ")
    dotenv_set_key(ENV_FILE, ENV_KEY, key)


def clear_key() -> None:
    unset_key(ENV_FILE, ENV_KEY)


def status() -> str:
    load_dotenv(ENV_FILE)
    if os.environ.get(ENV_KEY):
        return "已配置"
    return "未配置"