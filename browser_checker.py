"""Playwright-based browser checker for content verification."""

import asyncio
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from typing import Dict, Optional
import config


class BrowserChecker:
    """Browser-based content checker using Playwright."""
    
    def __init__(self, timeout: int = None):
        self.timeout = timeout or config.DEFAULT_TIMEOUT
        self.browser = None
        self.context = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()
    
    async def check_radio_stream(self, url: str, name: str) -> Dict:
        """Check if a radio stream is working."""
        timeout = config.RADIO_TIMEOUT
        
        try:
            # Create HTML page with audio element
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Radio Stream Check</title>
            </head>
            <body>
                <audio id="audioPlayer" controls preload="auto">
                    <source src="{url}" type="audio/mpeg">
                </audio>
                <script>
                    window.checkResult = {{}};
                    const audio = document.getElementById('audioPlayer');
                    
                    audio.addEventListener('error', function(e) {{
                        window.checkResult.error = true;
                        window.checkResult.errorMessage = 'Audio error: ' + (audio.error ? audio.error.message : 'Unknown error');
                    }});
                    
                    audio.addEventListener('loadeddata', function() {{
                        if (audio.readyState >= 2) {{
                            window.checkResult.loaded = true;
                            window.checkResult.readyState = audio.readyState;
                        }}
                    }});
                    
                    audio.addEventListener('canplay', function() {{
                        window.checkResult.canPlay = true;
                    }});
                    
                    // Start loading
                    audio.load();
                </script>
            </body>
            </html>
            """
            
            page = await self.context.new_page()
            
            # Set timeout
            page.set_default_timeout(timeout * 1000)
            
            # Load the HTML
            await page.set_content(html_content)
            
            # Wait for audio to load or error
            try:
                await page.wait_for_function(
                    "window.checkResult.error || window.checkResult.loaded",
                    timeout=timeout * 1000
                )
            except PlaywrightTimeoutError:
                pass
            
            # Check result
            result = await page.evaluate("window.checkResult")
            await page.close()
            
            if result.get("error"):
                return {
                    "status": "broken",
                    "error_message": result.get("errorMessage", "Audio stream error"),
                    "check_time": None
                }
            
            if result.get("loaded") or result.get("canPlay"):
                return {
                    "status": "working",
                    "error_message": None,
                    "check_time": None
                }
            
            # If no clear result, check readyState
            if result.get("readyState", 0) >= 2:
                return {
                    "status": "working",
                    "error_message": None,
                    "check_time": None
                }
            
            return {
                "status": "broken",
                "error_message": "Stream did not load within timeout",
                "check_time": None
            }
            
        except PlaywrightTimeoutError:
            return {
                "status": "broken",
                "error_message": f"Timeout after {timeout} seconds",
                "check_time": None
            }
        except Exception as e:
            return {
                "status": "broken",
                "error_message": f"Error checking stream: {str(e)}",
                "check_time": None
            }
    
    async def check_youtube_video(self, video_id: str, name: str, embed_url: str) -> Dict:
        """Check if a YouTube video is available."""
        timeout = config.YOUTUBE_TIMEOUT
        
        try:
            page = await self.context.new_page()
            page.set_default_timeout(timeout * 1000)
            
            # Load YouTube embed
            await page.goto(embed_url, wait_until="domcontentloaded")
            
            # Wait a bit for YouTube player to initialize
            await asyncio.sleep(3)
            
            # Check for error messages in page content
            page_text = await page.evaluate("document.body.innerText")
            
            error_indicators = [
                "video unavailable",
                "private video",
                "this video is not available",
                "video has been removed",
                "this video does not exist",
                "playback error"
            ]
            
            page_text_lower = page_text.lower()
            for indicator in error_indicators:
                if indicator in page_text_lower:
                    await page.close()
                    return {
                        "status": "broken",
                        "error_message": f"YouTube error: {indicator}",
                        "check_time": None
                    }
            
            # Try to check player state using YouTube IFrame API if available
            try:
                # Wait for iframe to load
                await page.wait_for_selector("iframe", timeout=5000)
                
                # Check if player is present
                player_check = await page.evaluate("""
                    () => {
                        const iframe = document.querySelector('iframe');
                        if (!iframe) return {error: 'No iframe found'};
                        
                        // Check if iframe has loaded
                        if (iframe.contentDocument || iframe.contentWindow) {
                            return {iframeLoaded: true};
                        }
                        return {iframeLoaded: false};
                    }
                """)
                
                if player_check.get("error"):
                    await page.close()
                    return {
                        "status": "broken",
                        "error_message": "YouTube player not found",
                        "check_time": None
                    }
                
                # Additional check: look for play button or player controls
                has_player = await page.evaluate("""
                    () => {
                        // Check for YouTube player elements
                        const iframe = document.querySelector('iframe');
                        if (iframe && iframe.src.includes('youtube.com')) {
                            return true;
                        }
                        return false;
                    }
                """)
                
                if not has_player:
                    await page.close()
                    return {
                        "status": "broken",
                        "error_message": "YouTube player not properly loaded",
                        "check_time": None
                    }
                
                await page.close()
                return {
                    "status": "working",
                    "error_message": None,
                    "check_time": None
                }
                
            except PlaywrightTimeoutError:
                # If we can't find iframe, might still be loading or error
                await page.close()
                return {
                    "status": "broken",
                    "error_message": "YouTube player did not load",
                    "check_time": None
                }
            
        except PlaywrightTimeoutError:
            return {
                "status": "broken",
                "error_message": f"Timeout after {timeout} seconds",
                "check_time": None
            }
        except Exception as e:
            return {
                "status": "broken",
                "error_message": f"Error checking video: {str(e)}",
                "check_time": None
            }
    
    async def check_tv_channel(self, embed_url: str, name: str, video_id: Optional[str] = None) -> Dict:
        """Check if a TV channel embed is working."""
        timeout = config.CHANNEL_TIMEOUT
        
        try:
            page = await self.context.new_page()
            page.set_default_timeout(timeout * 1000)
            
            # Load the embed URL
            await page.goto(embed_url, wait_until="domcontentloaded")
            
            # Wait for content to load
            await asyncio.sleep(3)
            
            # Check for error messages
            page_text = await page.evaluate("document.body.innerText")
            page_text_lower = page_text.lower()
            
            error_indicators = [
                "offline",
                "not available",
                "error",
                "unavailable",
                "not found",
                "404"
            ]
            
            for indicator in error_indicators:
                if indicator in page_text_lower and len(page_text_lower) < 500:  # Short error messages
                    await page.close()
                    return {
                        "status": "broken",
                        "error_message": f"Channel appears offline: {indicator}",
                        "check_time": None
                    }
            
            # Check if it's a YouTube embed
            if video_id or "youtube.com" in embed_url:
                return await self.check_youtube_video(video_id or "", name, embed_url)
            
            # Special handling for known non-<video> players (e.g. StreamSpot)
            # These use their own player UI without a direct <video> element in
            # the top-level DOM, so our usual video-element check would report
            # them as broken even when they are actually working.
            if "player2.streamspot.com" in embed_url:
                # If the page loaded and we didn't see any clear error text,
                # treat this as working.
                await page.close()
                return {
                    "status": "working",
                    "error_message": None,
                    "check_time": None
                }

            # For other embed types, check for video element
            try:
                # Check for video element
                has_video = await page.evaluate("""
                    () => {
                        const video = document.querySelector('video');
                        const iframe = document.querySelector('iframe');
                        return !!(video || iframe);
                    }
                """)
                
                if not has_video:
                    await page.close()
                    return {
                        "status": "broken",
                        "error_message": "No video element found",
                        "check_time": None
                    }
                
                # Check if video is playing or can play
                video_state = await page.evaluate("""
                    () => {
                        const video = document.querySelector('video');
                        if (video) {
                            return {
                                hasVideo: true,
                                readyState: video.readyState,
                                paused: video.paused,
                                error: video.error ? video.error.message : null
                            };
                        }
                        return {hasVideo: false};
                    }
                """)
                
                if video_state.get("error"):
                    await page.close()
                    return {
                        "status": "broken",
                        "error_message": f"Video error: {video_state.get('error')}",
                        "check_time": None
                    }
                
                if video_state.get("hasVideo"):
                    # Video element exists and has loaded some data
                    if video_state.get("readyState", 0) >= 2:
                        await page.close()
                        return {
                            "status": "working",
                            "error_message": None,
                            "check_time": None
                        }
                
                await page.close()
                return {
                    "status": "working",
                    "error_message": None,
                    "check_time": None
                }
                
            except Exception as e:
                await page.close()
                return {
                    "status": "broken",
                    "error_message": f"Error checking channel: {str(e)}",
                    "check_time": None
                }
            
        except PlaywrightTimeoutError:
            return {
                "status": "broken",
                "error_message": f"Timeout after {timeout} seconds",
                "check_time": None
            }
        except Exception as e:
            return {
                "status": "broken",
                "error_message": f"Error checking channel: {str(e)}",
                "check_time": None
            }
    
    async def check_content(self, content_item: Dict) -> Dict:
        """Check a content item based on its type."""
        from datetime import datetime
        
        content_type = content_item.get("type")
        name = content_item.get("name", "Unknown")
        url = content_item.get("url")
        
        if not url:
            return {
                "name": name,
                "type": content_type,
                "url": url,
                "status": "broken",
                "error_message": "No URL provided",
                "check_time": datetime.now().isoformat()
            }
        
        result = None
        
        if content_type == "radio":
            result = await self.check_radio_stream(url, name)
        elif content_type in ["music", "movie"]:
            video_id = content_item.get("video_id")
            if video_id:
                result = await self.check_youtube_video(video_id, name, url)
            else:
                result = {
                    "status": "broken",
                    "error_message": "No video ID found",
                    "check_time": None
                }
        elif content_type == "channel":
            video_id = content_item.get("video_id")
            result = await self.check_tv_channel(url, name, video_id)
        else:
            result = {
                "status": "broken",
                "error_message": f"Unknown content type: {content_type}",
                "check_time": None
            }
        
        # Add metadata
        result["name"] = name
        result["type"] = content_type
        result["url"] = url
        if result.get("check_time") is None:
            result["check_time"] = datetime.now().isoformat()
        
        return result
