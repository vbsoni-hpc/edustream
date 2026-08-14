"""
Custom Video.js player component for Streamlit.

Embeds a full-featured video player via st.components.v1.html() that:
- Streams video from FastAPI's MTProto proxy endpoint
- Tracks watch progress via JS fetch() calls (every 10s)
- Auto-marks completion when video ends
- Resumes playback from last saved position
"""
import streamlit as st
import streamlit.components.v1 as components


def render_video_player(
    video_msg_id: int,
    video_id: int,
    jwt_token: str,
    api_base: str = "http://127.0.0.1:8000",
    last_position: float = 0,
    title: str = "",
    height: int = 520,
):
    """
    Render an embedded Video.js player inside Streamlit.

    Args:
        video_msg_id: Telegram message ID (used for streaming URL)
        video_id:     Database video ID (used for progress API calls)
        jwt_token:    JWT auth token for API calls
        api_base:     FastAPI server URL
        last_position: Resume position in seconds
        title:        Video title (shown in player)
        height:       Player height in pixels
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                background: transparent;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                overflow: hidden;
            }}
            .player-wrapper {{
                position: relative;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 8px 32px rgba(108, 99, 255, 0.15),
                            0 2px 8px rgba(0, 0, 0, 0.3);
                background: #0E1117;
            }}
            .video-js {{
                width: 100% !important;
                aspect-ratio: 16/9;
                border-radius: 16px;
            }}
            .video-js .vjs-big-play-button {{
                border: none;
                background: rgba(108, 99, 255, 0.9);
                border-radius: 50%;
                width: 80px;
                height: 80px;
                line-height: 80px;
                font-size: 36px;
                left: 50%;
                top: 50%;
                transform: translate(-50%, -50%);
                transition: all 0.3s ease;
            }}
            .video-js .vjs-big-play-button:hover {{
                background: rgba(108, 99, 255, 1);
                transform: translate(-50%, -50%) scale(1.1);
                box-shadow: 0 0 30px rgba(108, 99, 255, 0.5);
            }}
            .video-js .vjs-control-bar {{
                background: linear-gradient(transparent, rgba(0,0,0,0.85));
                height: 44px;
                padding: 0 8px;
            }}
            .video-js .vjs-play-progress {{
                background: linear-gradient(90deg, #6C63FF, #a78bfa);
            }}
            .video-js .vjs-slider {{
                background: rgba(255,255,255,0.15);
            }}
            .status-bar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 10px 16px;
                background: #1A1D29;
                border-radius: 0 0 16px 16px;
                color: #9CA3AF;
                font-size: 13px;
            }}
            .status-indicator {{
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            .pulse-dot {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #6C63FF;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.4; }}
            }}
            .completed-badge {{
                display: none;
                align-items: center;
                gap: 6px;
                color: #34D399;
                font-weight: 600;
            }}
            .completed-badge.show {{
                display: flex;
            }}

            /* Confetti */
            .confetti-container {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                z-index: 9999;
                overflow: hidden;
            }}
            .confetti {{
                position: absolute;
                width: 10px;
                height: 10px;
                top: -10px;
                animation: confetti-fall 3s ease-out forwards;
            }}
            @keyframes confetti-fall {{
                0% {{ transform: translateY(0) rotate(0deg); opacity: 1; }}
                100% {{ transform: translateY(600px) rotate(720deg); opacity: 0; }}
            }}
        </style>
    </head>
    <body>
        <div class="player-wrapper">
            <video
                id="edtech-player"
                class="video-js vjs-big-play-centered vjs-theme-fantasy"
                controls
                preload="metadata"
                data-setup='{{}}'
            >
                <source src="{api_base}/api/stream/{video_msg_id}" type="video/mp4" />
                <p class="vjs-no-js">Enable JavaScript to watch this video.</p>
            </video>
            <div class="status-bar">
                <div class="status-indicator">
                    <div class="pulse-dot" id="stream-dot"></div>
                    <span id="stream-status">Streaming from Telegram</span>
                </div>
                <div class="completed-badge" id="completed-badge">
                    ✅ Completed
                </div>
                <span id="watch-time">0:00 watched</span>
            </div>
        </div>

        <div class="confetti-container" id="confetti-container"></div>

        <script src="https://vjs.zencdn.net/8.10.0/video.min.js"></script>
        <script>
            (function() {{
                const API_BASE = "{api_base}";
                const VIDEO_ID = {video_id};
                const TOKEN = "{jwt_token}";
                const LAST_POS = {last_position};

                // Initialise player
                const player = videojs('edtech-player', {{
                    fluid: true,
                    playbackRates: [0.5, 1, 1.25, 1.5, 2],
                    controlBar: {{
                        children: [
                            'playToggle',
                            'volumePanel',
                            'currentTimeDisplay',
                            'timeDivider',
                            'durationDisplay',
                            'progressControl',
                            'playbackRateMenuButton',
                            'fullscreenToggle'
                        ]
                    }}
                }});

                // Resume from last position
                player.one('loadedmetadata', function() {{
                    if (LAST_POS > 0) {{
                        player.currentTime(LAST_POS);
                    }}
                }});

                // ── Progress tracking ──
                let lastSavedTime = 0;
                let totalWatched = 0;

                function formatTime(sec) {{
                    const h = Math.floor(sec / 3600);
                    const m = Math.floor((sec % 3600) / 60);
                    const s = Math.floor(sec % 60);
                    if (h > 0) return h + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
                    return m + ':' + String(s).padStart(2,'0');
                }}

                player.on('timeupdate', function() {{
                    const current = Math.floor(player.currentTime());
                    totalWatched = Math.max(totalWatched, current);

                    // Update display
                    document.getElementById('watch-time').textContent = formatTime(totalWatched) + ' watched';

                    // Save every 10 seconds
                    if (current - lastSavedTime >= 10) {{
                        lastSavedTime = current;
                        fetch(API_BASE + '/api/progress/' + VIDEO_ID, {{
                            method: 'POST',
                            headers: {{
                                'Authorization': 'Bearer ' + TOKEN,
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{
                                watch_seconds: totalWatched,
                                last_position: current
                            }})
                        }}).catch(err => console.warn('Progress save failed:', err));
                    }}
                }});

                // ── Auto-complete on ended ──
                player.on('ended', function() {{
                    // Save final progress
                    fetch(API_BASE + '/api/progress/' + VIDEO_ID, {{
                        method: 'POST',
                        headers: {{
                            'Authorization': 'Bearer ' + TOKEN,
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            watch_seconds: totalWatched,
                            last_position: player.duration()
                        }})
                    }}).catch(() => {{}});

                    // Mark as complete
                    fetch(API_BASE + '/api/complete/' + VIDEO_ID, {{
                        method: 'POST',
                        headers: {{ 'Authorization': 'Bearer ' + TOKEN }}
                    }}).then(() => {{
                        document.getElementById('completed-badge').classList.add('show');
                        document.getElementById('stream-dot').style.background = '#34D399';
                        document.getElementById('stream-status').textContent = 'Completed!';
                        showConfetti();
                        // Notify parent Streamlit
                        window.parent.postMessage({{type: 'video_completed', videoId: VIDEO_ID}}, '*');
                    }}).catch(err => console.warn('Complete failed:', err));
                }});

                // ── Save on pause / page leave ──
                function saveProgress() {{
                    if (totalWatched > 0) {{
                        const data = JSON.stringify({{
                            watch_seconds: totalWatched,
                            last_position: Math.floor(player.currentTime())
                        }});
                        // Use sendBeacon for page unload reliability
                        if (navigator.sendBeacon) {{
                            const blob = new Blob([data], {{ type: 'application/json' }});
                            navigator.sendBeacon(API_BASE + '/api/progress/' + VIDEO_ID + '?token=' + TOKEN, blob);
                        }}
                    }}
                }}

                player.on('pause', function() {{
                    const current = Math.floor(player.currentTime());
                    fetch(API_BASE + '/api/progress/' + VIDEO_ID, {{
                        method: 'POST',
                        headers: {{
                            'Authorization': 'Bearer ' + TOKEN,
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            watch_seconds: totalWatched,
                            last_position: current
                        }})
                    }}).catch(() => {{}});
                }});

                window.addEventListener('beforeunload', saveProgress);

                // ── Confetti effect ──
                function showConfetti() {{
                    const container = document.getElementById('confetti-container');
                    const colors = ['#6C63FF', '#34D399', '#F59E0B', '#EF4444', '#EC4899', '#3B82F6'];
                    for (let i = 0; i < 60; i++) {{
                        const conf = document.createElement('div');
                        conf.classList.add('confetti');
                        conf.style.left = Math.random() * 100 + '%';
                        conf.style.background = colors[Math.floor(Math.random() * colors.length)];
                        conf.style.animationDelay = Math.random() * 1.5 + 's';
                        conf.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
                        conf.style.width = (Math.random() * 8 + 6) + 'px';
                        conf.style.height = (Math.random() * 8 + 6) + 'px';
                        container.appendChild(conf);
                    }}
                    setTimeout(() => container.innerHTML = '', 4000);
                }}
            }})();
        </script>
    </body>
    </html>
    """
    components.html(html, height=height, scrolling=False)
