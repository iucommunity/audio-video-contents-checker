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
            
            # Wait longer for YouTube player/page to fully load (restricted embeds take time)
            await asyncio.sleep(5)
            
            # Check for error messages and "Watch on YouTube" button in page content
            page_text = await page.evaluate("document.body.innerText")
            page_html = await page.evaluate("document.body.innerHTML")
            
            # Also check for YouTube redirect links/buttons
            has_youtube_link = await page.evaluate("""
                () => {
                    // Check for links that go to youtube.com/watch (Watch on YouTube button)
                    const links = document.querySelectorAll('a[href*="youtube.com/watch"], a[href*="youtu.be"]');
                    if (links.length > 0) return true;
                    
                    // Check for buttons/elements with YouTube-related text or href
                    const allElements = Array.from(document.querySelectorAll('button, a, div, span'));
                    for (const elem of allElements) {
                        const text = (elem.innerText || elem.textContent || '').toLowerCase();
                        const href = elem.href || elem.getAttribute('href') || '';
                        const onclick = elem.getAttribute('onclick') || '';
                        
                        // Check for YouTube watch URLs
                        if (href.includes('youtube.com/watch') || href.includes('youtu.be')) {
                            return true;
                        }
                        
                        // Check for "watch" + "youtube" in text (Watch on YouTube button)
                        if ((text.includes('watch') && text.includes('youtube')) || 
                            text.includes('watch on youtube') || 
                            text.includes('watch video on youtube')) {
                            return true;
                        }
                        
                        // Check onclick handlers that might redirect to YouTube
                        if (onclick.includes('youtube.com') || onclick.includes('youtu.be')) {
                            return true;
                        }
                    }
                    return false;
                }
            """)
            
            page_text_lower = page_text.lower()
            page_html_lower = page_html.lower()
            
            # Check for "Watch on YouTube" button - this means video exists but embedding is restricted
            # This is actually a working video, just not embeddable
            watch_on_youtube_indicators = [
                "watch on youtube",
                "watch video on youtube",
                "watch on yt",
                "watch video",
                "youtube.com/watch"
            ]
            
            has_watch_button = (has_youtube_link or 
                              any(indicator in page_text_lower or indicator in page_html_lower 
                                  for indicator in watch_on_youtube_indicators))
            
            # Check for actual error messages (video doesn't exist, removed, etc.)
            error_indicators = [
                "video unavailable",
                "private video",
                "this video is not available",
                "video has been removed",
                "this video does not exist",
                "playback error",
                "video has been deleted"
            ]
            
            has_error = any(indicator in page_text_lower for indicator in error_indicators)
            
            # If we see "Watch on YouTube" button, video exists (just restricted embedding)
            if has_watch_button and not has_error:
                await page.close()
                return {
                    "status": "working",
                    "error_message": "Video available but embedding restricted (Watch on YouTube button present)",
                    "check_time": None
                }
            
            # If we see actual errors, mark as broken
            if has_error:
                error_msg = next((indicator for indicator in error_indicators if indicator in page_text_lower), "Unknown error")
                await page.close()
                return {
                    "status": "broken",
                    "error_message": f"YouTube error: {error_msg}",
                    "check_time": None
                }
            
            # Try to check player state using YouTube IFrame API if available
            try:
                # Wait for iframe to load (with longer timeout for restricted embeds)
                await page.wait_for_selector("iframe", timeout=10000)
                
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
                    # If no iframe but we saw "Watch on YouTube", it's still working
                    if has_watch_button:
                        await page.close()
                        return {
                            "status": "working",
                            "error_message": "Video available but embedding restricted",
                            "check_time": None
                        }
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
                    # If no player but we saw "Watch on YouTube", it's still working
                    if has_watch_button:
                        await page.close()
                        return {
                            "status": "working",
                            "error_message": "Video available but embedding restricted",
                            "check_time": None
                        }
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
                # Re-check for "Watch on YouTube" button after timeout (page might have loaded more)
                page_text_retry = await page.evaluate("document.body.innerText")
                page_html_retry = await page.evaluate("document.body.innerHTML")
                has_youtube_link_retry = await page.evaluate("""
                    () => {
                        // Check for links that go to youtube.com/watch (Watch on YouTube button)
                        const links = document.querySelectorAll('a[href*="youtube.com/watch"], a[href*="youtu.be"]');
                        if (links.length > 0) return true;
                        
                        // Check for buttons/elements with YouTube-related text or href
                        const allElements = Array.from(document.querySelectorAll('button, a, div, span'));
                        for (const elem of allElements) {
                            const text = (elem.innerText || elem.textContent || '').toLowerCase();
                            const href = elem.href || elem.getAttribute('href') || '';
                            const onclick = elem.getAttribute('onclick') || '';
                            
                            // Check for YouTube watch URLs
                            if (href.includes('youtube.com/watch') || href.includes('youtu.be')) {
                                return true;
                            }
                            
                            // Check for "watch" + "youtube" in text (Watch on YouTube button)
                            if ((text.includes('watch') && text.includes('youtube')) || 
                                text.includes('watch on youtube') || 
                                text.includes('watch video on youtube')) {
                                return true;
                            }
                            
                            // Check onclick handlers that might redirect to YouTube
                            if (onclick.includes('youtube.com') || onclick.includes('youtu.be')) {
                                return true;
                            }
                        }
                        return false;
                    }
                """)
                
                page_text_retry_lower = page_text_retry.lower()
                page_html_retry_lower = page_html_retry.lower()
                has_watch_button_retry = (has_youtube_link_retry or 
                                         any(indicator in page_text_retry_lower or indicator in page_html_retry_lower 
                                             for indicator in watch_on_youtube_indicators))
                
                # If we can't find iframe but we see "Watch on YouTube" button, it's working
                if has_watch_button or has_watch_button_retry:
                    await page.close()
                    return {
                        "status": "working",
                        "error_message": "Video available but embedding restricted (Watch on YouTube button present)",
                        "check_time": None
                    }
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
            
            # Wait longer for content to load (players like ParsaTV show "Loading the player...")
            await asyncio.sleep(5)
            
            # Check if it's a YouTube embed FIRST (before error detection)
            # YouTube embeds have their own checking logic that handles "Watch on YouTube" buttons
            if video_id or "youtube.com" in embed_url:
                return await self.check_youtube_video(video_id or "", name, embed_url)
            
            # For non-YouTube embeds, check for error messages
            # But be more careful - don't flag generic "error" text that might be part of normal page content
            page_text = await page.evaluate("document.body.innerText")
            page_text_lower = page_text.lower()
            
            # Check for positive indicators first (player elements, video-related content)
            has_positive_indicators = await page.evaluate("""
                () => {
                    // Check for video/iframe elements
                    if (document.querySelector('video') || document.querySelector('iframe')) {
                        return true;
                    }
                    // Check for player-related elements
                    const playerElements = document.querySelectorAll('[class*="player"], [id*="player"], [class*="video"], [id*="video"]');
                    if (playerElements.length > 0) {
                        return true;
                    }
                    // Check for YouTube links (Watch on YouTube button)
                    const youtubeLinks = document.querySelectorAll('a[href*="youtube.com"], a[href*="youtu.be"]');
                    if (youtubeLinks.length > 0) {
                        return true;
                    }
                    return false;
                }
            """)
            
            # More specific error indicators (avoid generic "error" which appears in many contexts)
            error_indicators = [
                "channel offline",
                "stream offline",
                "not available",
                "unavailable",
                "not found",
                "404",
                "this channel is offline",
                "this stream is offline"
            ]
            
            # Only flag as error if we see specific error phrases AND page is short (likely an error page)
            # AND there are no positive indicators (player elements, etc.)
            # This prevents false positives when "error" appears in normal page content
            for indicator in error_indicators:
                if indicator in page_text_lower:
                    # If we have positive indicators, don't mark as broken (error text might be part of normal content)
                    if has_positive_indicators:
                        break  # Skip error detection if we found player elements
                    
                    # If page is very short, it's likely an error page
                    if len(page_text_lower) < 300:
                        await page.close()
                        return {
                            "status": "broken",
                            "error_message": f"Channel appears offline: {indicator}",
                            "check_time": None
                        }
                    # If page is longer but contains clear error message, still check
                    # But be more lenient - might be part of larger page content
                    if len(page_text_lower) < 500 and page_text_lower.count(indicator) > 1:
                        await page.close()
                        return {
                            "status": "broken",
                            "error_message": f"Channel appears offline: {indicator}",
                            "check_time": None
                        }
            
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
                # Wait a bit more for player to initialize (some players take time to load)
                await asyncio.sleep(2)
                
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
                                error: video.error ? video.error.message : null,
                                errorCode: video.error ? video.error.code : null,
                                networkState: video.networkState,
                                src: video.src || (video.querySelector('source') ? video.querySelector('source').src : '')
                            };
                        }
                        return {hasVideo: false};
                    }
                """)
                
                # Handle video errors more intelligently
                # Decode errors (PIPELINE_ERROR_DECODE) are often transient or codec-related
                # and don't necessarily mean the channel is broken
                error_message = video_state.get("error")
                error_code = video_state.get("errorCode")
                
                if error_message:
                    # Check if it's a decode error - these are often non-fatal
                    is_decode_error = (
                        "decode" in error_message.lower() or
                        "pipeline" in error_message.lower() or
                        "decoding" in error_message.lower() or
                        error_code == 3  # MEDIA_ERR_DECODE
                    )
                    
                    # If it's a decode error but video has loaded metadata or is trying to play,
                    # treat as working (decode errors can be transient or codec compatibility issues)
                    if is_decode_error:
                        ready_state = video_state.get("readyState", 0)
                        network_state = video_state.get("networkState", 0)
                        has_src = bool(video_state.get("src"))
                        
                        # If video has loaded metadata (readyState >= 1) or has a source URL,
                        # it's likely working despite the decode error
                        if ready_state >= 1 or has_src or network_state >= 1:
                            await page.close()
                            return {
                                "status": "working",
                                "error_message": None,
                                "check_time": None
                            }
                    
                    # For non-decode errors, check if video has loaded any data
                    # Sometimes errors occur during initial load but video can still play
                    ready_state = video_state.get("readyState", 0)
                    if ready_state >= 1:  # HAVE_METADATA - video has at least loaded metadata
                        await page.close()
                        return {
                            "status": "working",
                            "error_message": None,
                            "check_time": None
                        }
                    
                    # Only mark as broken if there's a clear fatal error and no progress
                    await page.close()
                    return {
                        "status": "broken",
                        "error_message": f"Video error: {error_message}",
                        "check_time": None
                    }
                
                if video_state.get("hasVideo"):
                    # Video element exists and has loaded some data
                    if video_state.get("readyState", 0) >= 2:  # HAVE_CURRENT_DATA or better
                        await page.close()
                        return {
                            "status": "working",
                            "error_message": None,
                            "check_time": None
                        }
                    
                    # Even if readyState is lower, if video element exists, it's likely working
                    # (might just need more time or user interaction)
                    if video_state.get("readyState", 0) >= 1:  # HAVE_METADATA
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
    
    async def check_generic_embed(self, embed_url: str, name: str) -> Dict:
        """Check a generic embed URL (non-YouTube, e.g., Arclight API)."""
        timeout = config.YOUTUBE_TIMEOUT
        
        try:
            page = await self.context.new_page()
            page.set_default_timeout(timeout * 1000)
            
            # Load the embed URL
            await page.goto(embed_url, wait_until="domcontentloaded")
            
            # Wait for content to load (longer for API-based players)
            await asyncio.sleep(5)
            
            # Check for error messages
            page_text = await page.evaluate("document.body.innerText")
            page_html = await page.evaluate("document.body.innerHTML")
            
            page_text_lower = page_text.lower()
            
            # Check for error indicators
            error_indicators = [
                "not available",
                "video unavailable",
                "error loading",
                "404",
                "not found",
                "access denied"
            ]
            
            for indicator in error_indicators:
                if indicator in page_text_lower and len(page_text_lower) < 500:
                    await page.close()
                    return {
                        "status": "broken",
                        "error_message": f"Embed error: {indicator}",
                        "check_time": None
                    }
            
            # Check for video player elements (video tag, iframe, or player containers)
            player_check = await page.evaluate("""
                () => {
                    // Check for video element
                    const video = document.querySelector('video');
                    if (video) {
                        return {
                            hasPlayer: true,
                            type: 'video',
                            readyState: video.readyState,
                            error: video.error ? video.error.message : null
                        };
                    }
                    
                    // Check for iframe
                    const iframe = document.querySelector('iframe');
                    if (iframe) {
                        return {
                            hasPlayer: true,
                            type: 'iframe',
                            src: iframe.src
                        };
                    }
                    
                    // Check for common player container classes/ids
                    const playerSelectors = [
                        '[class*="player"]',
                        '[id*="player"]',
                        '[class*="video"]',
                        '[id*="video"]',
                        '[class*="media"]',
                        '[id*="media"]'
                    ];
                    
                    for (const selector of playerSelectors) {
                        const elem = document.querySelector(selector);
                        if (elem) {
                            return {
                                hasPlayer: true,
                                type: 'container',
                                selector: selector
                            };
                        }
                    }
                    
                    // Check for play button or video-related content
                    const playButtons = document.querySelectorAll('button, a, div');
                    for (const btn of playButtons) {
                        const text = (btn.innerText || btn.textContent || '').toLowerCase();
                        const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                        if (text.includes('play') || text.includes('video') || ariaLabel.includes('play')) {
                            return {
                                hasPlayer: true,
                                type: 'playButton',
                                text: text
                            };
                        }
                    }
                    
                    // Check if page mentions video-related content (e.g., "click play", "enable javascript")
                    const bodyText = document.body.innerText.toLowerCase();
                    if (bodyText.includes('enable javascript') || 
                        bodyText.includes('upgrade your browser') ||
                        bodyText.includes('html5 video')) {
                        // These messages usually mean the player is there but needs JS/browser support
                        return {
                            hasPlayer: true,
                            type: 'requiresJs',
                            message: 'Player requires JavaScript'
                        };
                    }
                    
                    return {hasPlayer: false};
                }
            """)
            
            if player_check.get("hasPlayer"):
                # Player element found - check if there are errors
                if player_check.get("error"):
                    await page.close()
                    return {
                        "status": "broken",
                        "error_message": f"Player error: {player_check.get('error')}",
                        "check_time": None
                    }
                
                # If we found a video element with good readyState, it's working
                if player_check.get("type") == "video" and player_check.get("readyState", 0) >= 2:
                    await page.close()
                    return {
                        "status": "working",
                        "error_message": None,
                        "check_time": None
                    }
                
                # If we found any player element or play button, assume working
                # (player might need user interaction to start)
                await page.close()
                return {
                    "status": "working",
                    "error_message": None,
                    "check_time": None
                }
            
            # If no player found but page loaded, might still be valid (e.g., redirects to player)
            # Check if page has useful content (not just error)
            if len(page_text) > 100:  # Has substantial content
                await page.close()
                return {
                    "status": "working",
                    "error_message": "Player page loaded (may require user interaction)",
                    "check_time": None
                }
            
            await page.close()
            return {
                "status": "broken",
                "error_message": "No video player found on page",
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
                "error_message": f"Error checking embed: {str(e)}",
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
                # YouTube video
                result = await self.check_youtube_video(video_id, name, url)
            else:
                # Non-YouTube embed (e.g., Arclight API)
                result = await self.check_generic_embed(url, name)
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
