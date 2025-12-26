"""Configuration for Python Agent."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Claude API Configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 1000
CLAUDE_TEMPERATURE = 0.1

# File Paths
BASE_DIR = Path(__file__).parent.parent
ACAT_REFERENCE_FILE = os.getenv("ACAT_REFERENCE_FILE", str(BASE_DIR / "mcp_server" / "data" / "ACAT_Data_Stores_Master.xlsx"))
USER_INPUT_FILE = os.getenv("USER_INPUT_FILE", str(BASE_DIR / "input" / "user_input.xlsx"))
OUTPUT_DIR = BASE_DIR / "output"

# Matching Configuration
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

# Rate Limiting
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "0.5"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
