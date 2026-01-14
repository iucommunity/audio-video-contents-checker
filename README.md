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

Generate only PDF report:
```bash
python main.py --output pdf
```

Generate only CSV report:
```bash
python main.py --output csv
```

Generate both (default):
```bash
python main.py --output both
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

Reports are saved in the `reports/` directory with timestamps:
- `content_check_report_YYYY-MM-DD_HH-MM-SS.csv`
- `content_check_report_YYYY-MM-DD_HH-MM-SS.pdf`

### CSV Report

Contains columns:
- Name
- Type
- URL
- Status
- Error Message
- Check Time

### PDF Report

Contains:
- Summary statistics (total, working, broken)
- Summary by content type
- Detailed broken content (grouped by type)
- Working content (if not too many items)

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
- reportlab

## Notes

- Checking is done sequentially per type to ensure accuracy
- Timeouts are set to prioritize accuracy over speed
- The script will create the `reports/` directory if it doesn't exist
