"""Configuration settings for the content checker."""

# Base URL for JSON data files
BASE_URL = "https://www.eternityready.com/data"

# JSON file URLs
JSON_URLS = {
    "channels": f"{BASE_URL}/channels.json",
    "music": f"{BASE_URL}/music.json",
    "radio": f"{BASE_URL}/radio.json",
    "movies": f"{BASE_URL}/movies.json",
}

# Default timeout settings (in seconds)
DEFAULT_TIMEOUT = 30
RADIO_TIMEOUT = 25
YOUTUBE_TIMEOUT = 30
CHANNEL_TIMEOUT = 35

# Retry settings
MAX_RETRIES = 1
RETRY_DELAY = 2  # seconds

# Output directory
REPORTS_DIR = "reports"
