"""Configuration for Python Agent."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Claude API Configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 8000  # Increased for processing multiple datastores
CLAUDE_TEMPERATURE = 0.1

# File Paths
BASE_DIR = Path(__file__).parent.parent
# Note: ACAT reference is accessed via MCP server tool, not direct file access
user_input_env = os.getenv("USER_INPUT_FILE", "")
if user_input_env and not Path(user_input_env).is_absolute():
    # If env var is relative, make it relative to BASE_DIR
    USER_INPUT_FILE = str(BASE_DIR / user_input_env)
else:
    # Use env var if absolute, otherwise use default
    USER_INPUT_FILE = user_input_env if user_input_env else str(BASE_DIR / "input" / "user_input.xlsx")
OUTPUT_DIR = BASE_DIR / "output"

# Matching Configuration
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

# Rate Limiting
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "0.5"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
