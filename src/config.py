import configparser
import os
from pathlib import Path


def load_config() -> dict:
    cfg_path = Path.home() / "doit.cfg"
    parser = configparser.ConfigParser()

    if not cfg_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {cfg_path}\n"
            f"Copy doit.cfg.example to ~/doit.cfg and fill in your API key."
        )

    parser.read(cfg_path)

    model = parser.get("model", "name", fallback="gemini/gemini-2.0-flash")
    api_key = parser.get("model", "api_key", fallback=None)

    if api_key:
        provider = model.split("/")[0] if "/" in model else "openai"
        env_map = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        env_var = env_map.get(provider)
        if env_var:
            os.environ.setdefault(env_var, api_key)

    return {"model": model}
