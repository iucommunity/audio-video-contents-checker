"""JSON parser to fetch and parse content data from JSON files."""

import json
import requests
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs
import config


def _find_radio_items(data) -> List[Dict]:
    """
    Recursively search any JSON structure for objects that look like radio
    stations (dicts that contain a stream URL, usually under 'src').
    """
    results: List[Dict] = []

    if isinstance(data, list):
        for item in data:
            results.extend(_find_radio_items(item))
    elif isinstance(data, dict):
        # If this dict itself looks like a station (has 'src'), keep it
        if "src" in data and isinstance(data["src"], str):
            results.append(data)
        # Recurse into all values
        for value in data.values():
            results.extend(_find_radio_items(value))

    return results


def _find_items_with_key(data, key: str) -> List[Dict]:
    """
    Recursively search any JSON structure for dicts that contain a given key.
    Used for music/movies where items may be nested under categories.
    """
    results: List[Dict] = []

    if isinstance(data, list):
        for item in data:
            results.extend(_find_items_with_key(item, key))
    elif isinstance(data, dict):
        if key in data and isinstance(data[key], str):
            results.append(data)
        for value in data.values():
            results.extend(_find_items_with_key(value, key))

    return results


def extract_youtube_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    if not url:
        return None
    
    # Handle YouTube embed URLs
    if "youtube.com/embed/" in url:
        video_id = url.split("youtube.com/embed/")[1].split("?")[0].split("&")[0]
        return video_id
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0].split("&")[0]
        return video_id
    elif "youtube.com/watch" in url:
        parsed = urlparse(url)
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        return video_id
    
    return None


def fetch_json(url: str) -> Optional[Dict]:
    """Fetch JSON data from a URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from {url}: {e}")
        return None


def parse_radio_data(data: List[Dict]) -> List[Dict]:
    """Parse radio.json data and extract stream URLs."""
    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        
        name = item.get("name", "Unknown")
        src = item.get("src")
        
        if src:
            results.append({
                "type": "radio",
                "name": name,
                "url": src,
                "source_file": "radio.json"
            })
    
    return results


def parse_music_data(data: List[Dict]) -> List[Dict]:
    """Parse music.json data and extract YouTube video URLs."""
    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        
        # Some files use "title" instead of "name"
        name = item.get("name") or item.get("title") or "Unknown"
        embed = item.get("embed")
        if not embed:
            continue

        # We keep all items, even if the URL is duplicated or not a YouTube URL.
        # Non-YouTube embeds will have video_id=None and can still be checked
        # generically by the browser checker.
        video_id = extract_youtube_video_id(embed)

        results.append({
            "type": "music",
            "name": name,
            "url": embed,
            "video_id": video_id,
            "source_file": "music.json"
        })
    
    return results


def parse_movies_data(data: List[Dict]) -> List[Dict]:
    """Parse movies.json data and extract YouTube video URLs."""
    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        
        # Some files use "title" instead of "name"
        name = item.get("name") or item.get("title") or "Unknown"
        embed = item.get("embed")
        if not embed:
            continue

        # No dedup + no requirement for YouTube; count all movie entries
        video_id = extract_youtube_video_id(embed)

        results.append({
            "type": "movie",
            "name": name,
            "url": embed,
            "video_id": video_id,
            "source_file": "movies.json"
        })
    
    return results


def parse_channels_data(data: List[Dict]) -> List[Dict]:
    """Parse channels.json data and extract embed URLs."""
    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        
        name = item.get("name", "Unknown")
        embed = item.get("embed")
        
        if embed:
            # Extract video ID if it's a YouTube URL
            video_id = extract_youtube_video_id(embed)
            results.append({
                "type": "channel",
                "name": name,
                "url": embed,
                "video_id": video_id,  # None if not YouTube
                "source_file": "channels.json"
            })
    
    return results


def parse_json_file(file_type: str) -> List[Dict]:
    """Parse a specific JSON file type and return structured data."""
    url = config.JSON_URLS.get(file_type)
    if not url:
        print(f"Unknown file type: {file_type}")
        return []
    
    data = fetch_json(url)
    if data is None:
        return []
    
    # Handle different data structures
    if isinstance(data, list):
        # Root is already a list of items
        items = data
    elif isinstance(data, dict):
        # Prefer known top-level lists first
        if file_type == "radio":
            if isinstance(data.get("radio"), list):
                items = data["radio"]
            elif isinstance(data.get("stations"), list):
                items = data["stations"]
            else:
                # Fallback: search entire structure for station-like dicts
                items = _find_radio_items(data)
        elif file_type == "music":
            if isinstance(data.get("music"), list):
                items = data["music"]
            else:
                # Fallback: find any dicts with an 'embed' key
                items = _find_items_with_key(data, "embed")
        elif file_type == "movies":
            if isinstance(data.get("movies"), list):
                items = data["movies"]
            else:
                items = _find_items_with_key(data, "embed")
        elif file_type == "channels":
            if isinstance(data.get("channels"), list):
                items = data["channels"]
            else:
                # Generic fallbacks in case structure changes again
                for key in ["items", "data", "channels", "stations"]:
                    if isinstance(data.get(key), list):
                        items = data[key]
                        break
                else:
                    items = [data]
        else:
            # Generic handling for any future types
            for key in ["items", "data"]:
                if isinstance(data.get(key), list):
                    items = data[key]
                    break
            else:
                items = [data]
    else:
        print(f"Unexpected data structure in {file_type}: {type(data)}")
        return []
    
    # Parse based on file type
    if file_type == "radio":
        return parse_radio_data(items)
    elif file_type == "music":
        return parse_music_data(items)
    elif file_type == "movies":
        return parse_movies_data(items)
    elif file_type == "channels":
        return parse_channels_data(items)
    
    return []


def parse_all_json_files(file_types: Optional[List[str]] = None) -> List[Dict]:
    """Parse all or specified JSON files and return combined results."""
    if file_types is None:
        file_types = list(config.JSON_URLS.keys())
    
    all_results = []
    for file_type in file_types:
        print(f"Fetching and parsing {file_type}.json...")
        results = parse_json_file(file_type)
        all_results.extend(results)
        print(f"  Found {len(results)} items")
    
    return all_results
