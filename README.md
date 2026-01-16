# Audio/Video Content Checker

A Python-based script that checks audio/video content from JSON files and generates comprehensive PDF/CSV reports. Uses Playwright for accurate playback verification.

## Features

- **Accurate Detection**: Uses headless browser to actually attempt playback
- **Multiple Content Types**: Supports radio streams, YouTube videos, and TV channel embeds
- **Comprehensive Reporting**: Generates both PDF and CSV reports
- **Concurrent Checking**: Configurable concurrent checks for efficiency
- **Error Handling**: Robust error handling with retry logic

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

## Usage

### Basic Usage

Check all default JSON files and generate both PDF and CSV reports:
```bash
python main.py
```

### Check Specific Files

Check only specific JSON files:
```bash
python main.py --files channels,music
python main.py --files radio
python main.py --files movies,channels
```

Available file types: `channels`, `music`, `radio`, `movies`

### Output Format

Generate HTML report (default, auto-opens in browser):
```bash
python main.py --output html
```

Prevent auto-opening the report:
```bash
python main.py --output html --no-open
```

### Configuration Options

Custom timeout per check (in seconds):
```bash
python main.py --timeout 45
```

Maximum concurrent checks:
```bash
python main.py --max-concurrent 5
```

## Output

HTML reports are saved in the `reports/` directory with timestamps:
- `content_check_report_YYYY-MM-DD_HH-MM-SS.html`

The HTML report includes:
- **Summary Cards**: Total items, working, broken, and success rate
- **Interactive Charts**: 
  - Doughnut chart showing status overview
  - Bar chart showing status breakdown by content type
- **Interactive Table**: 
  - All results with filtering by type and status
  - Search functionality
  - Clickable URLs
  - Color-coded status badges
- **Auto-open**: Automatically opens in your default browser (can be disabled with `--no-open`)

## Content Types

### Radio Stations
- Checks audio stream URLs from `radio.json`
- Verifies stream is playable
- Detects stream errors and timeouts

### YouTube Videos (Music & Movies)
- Checks YouTube embed URLs from `music.json` and `movies.json`
- Detects unavailable, private, or removed videos
- Verifies player loads correctly

### TV Channels
- Checks various embed formats from `channels.json`
- Supports YouTube embeds, custom players, and HLS streams
- Detects offline channels and player errors

## Project Structure

```
.
├── main.py              # Main entry point with CLI
├── checker.py           # Core checking logic
├── json_parser.py       # Parse JSON files and extract URLs
├── browser_checker.py   # Playwright-based content verification
├── report_generator.py  # Generate PDF and CSV reports
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── reports/            # Output directory for reports
```

## Configuration

Edit `config.py` to customize:
- JSON file URLs
- Timeout settings
- Retry settings
- Output directory

## Error Handling

The script handles:
- Network timeouts
- Invalid JSON structures
- Missing or malformed URLs
- Browser crashes (with automatic recovery)
- Rate limiting (with delays)

## Requirements

- Python 3.7+
- Playwright
- requests

## Notes

- Checking is done sequentially per type to ensure accuracy
- Timeouts are set to prioritize accuracy over speed
- The script will create the `reports/` directory if it doesn't exist
