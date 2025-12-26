"""Configuration for MCP server."""
import os
from pathlib import Path

# File paths
BASE_DIR = Path(__file__).parent
ACAT_REFERENCE_FILE = os.getenv(
    "ACAT_REFERENCE_FILE", 
    BASE_DIR / "data" / "ACAT_Data_Stores_Master.xlsx"
)

# Endoflife.date API configuration
ENDOFLIFE_API_BASE_URL = "https://endoflife.date/api"
ENDOFLIFE_API_TIMEOUT = 30
ENDOFLIFE_API_RETRIES = 3
RATE_LIMIT_DELAY = 0.5  # seconds between API calls

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
