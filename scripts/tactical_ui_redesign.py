#!/usr/bin/env python3
"""
Tactical UI Redesign Script
Transforms the telemetry dashboard into a retro tactical/military interface
inspired by old CD player decks and cyberpunk HUD aesthetics.
"""

import re
from pathlib import Path

# Tactical UI CSS - Retro/Military/CD Player aesthetic
TACTICAL_CSS = '''
        /* Tactical UI Theme - Retro/Military/CD Player Aesthetic */
        :root {
            --bg-primary: #000000;
            --bg-secondary: #0a0a0a;
            --bg-card: #000000;
            --border-primary: #ffffff;
            --border-secondary: #666666;
            --text-primary: #ffffff;
            --text-secondary: #999999;
            --text-dim: #666666;
            --accent-live: #00ff00;
            --accent-warning: #ffaa00;
            --accent-danger: #ff0000;
            --accent-info: #00aaff;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Courier New', 'IBM Plex Mono', 'Consolas', monospace;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
            font-size: 13px;
            letter-spacing: 0.5px;
        }

        /* Optional scanline effect */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: repeating-linear-gradient(
                0deg,
                rgba(0, 0, 0, 0) 0px,
                rgba(0, 0, 0, 0) 1px,
                rgba(255, 255, 255, 0.01) 1px,
                rgba(255, 255, 255, 0.01) 2px
            );
            pointer-events: none;
            z-index: 1000;
            opacity: 0.3;
        }

        /* Header */
        .header {
            background: var(--bg-primary);
            padding: 1.5rem 2rem;
            border-bottom: 1px solid var(--border-primary);
            position: relative;
            z-index: 100;
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 1.5rem;
            font-weight: normal;
            letter-spacing: 3px;
            text-transform: uppercase;
        }

        .header-status {
            display: flex;
            gap: 2rem;
            align-items: center;
            font-size: 0.85rem;
        }

        .status-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border: 1px solid var(--text-primary);
            background: transparent;
        }

        .status-dot.active {
            background: var(--accent-live);
            box-shadow: 0 0 10px var(--accent-live);
            animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* Main Container */
        .container {
            padding: 2rem;
            max-width: 1800px;
            margin: 0 auto;
        }

        /* Grid Layout */
        .grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 1.5rem;
        }

        /* Tactical Card with Corner Brackets */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-primary);
            padding: 1.5rem;
            position: relative;
            grid-column: span 12;
        }

        /* Corner brackets */
        .card::before,
        .card::after {
            content: '';
            position: absolute;
            width: 12px;
            height: 12px;
            border: 1px solid var(--border-primary);
        }

        .card::before {
            top: -1px;
            left: -1px;
            border-right: none;
            border-bottom: none;
        }

        .card::after {
            top: -1px;
            right: -1px;
            border-left: none;
            border-bottom: none;
        }

        .card .corner-bl,
        .card .corner-br {
            position: absolute;
            width: 12px;
            height: 12px;
            border: 1px solid var(--border-primary);
        }

        .card .corner-bl {
            bottom: -1px;
            left: -1px;
            border-right: none;
            border-top: none;
        }

        .card .corner-br {
            bottom: -1px;
            right: -1px;
            border-left: none;
            border-top: none;
        }

        /* Card Header */
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border-secondary);
        }

        .card-title {
            font-size: 0.9rem;
            font-weight: normal;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        .card-meta {
            font-size: 0.75rem;
            color: var(--text-secondary);
            letter-spacing: 1px;
        }

        /* Stats Grid */
        .stats-grid {
            grid-column: span 12;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1.5rem;
        }

        @media (max-width: 1200px) {
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Stat Card */
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-primary);
            padding: 1.5rem;
            position: relative;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        /* Add corners to stat cards */
        .stat-card::before,
        .stat-card::after,
        .stat-card .corner-bl,
        .stat-card .corner-br {
            content: '';
            position: absolute;
            width: 10px;
            height: 10px;
            border: 1px solid var(--border-primary);
        }

        .stat-card::before {
            top: -1px;
            left: -1px;
            border-right: none;
            border-bottom: none;
        }

        .stat-card::after {
            top: -1px;
            right: -1px;
            border-left: none;
            border-bottom: none;
        }

        .stat-card .corner-bl {
            bottom: -1px;
            left: -1px;
            border-right: none;
            border-top: none;
        }

        .stat-card .corner-br {
            bottom: -1px;
            right: -1px;
            border-left: none;
            border-top: none;
        }

        .stat-label {
            font-size: 0.7rem;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: var(--text-secondary);
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: normal;
            letter-spacing: 2px;
            line-height: 1;
        }

        .stat-unit {
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-top: 0.25rem;
        }

        /* Chart Card */
        .chart-card {
            grid-column: span 6;
        }

        @media (max-width: 968px) {
            .chart-card {
                grid-column: span 12;
            }
        }

        .chart-container {
            width: 100%;
            height: 250px;
            position: relative;
        }

        /* Buttons - Tactical Style */
        button, .btn {
            background: transparent;
            border: 1px solid var(--border-primary);
            color: var(--text-primary);
            padding: 0.5rem 1.5rem;
            font-family: 'Courier New', monospace;
            font-size: 0.75rem;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
        }

        button:hover, .btn:hover {
            background: var(--text-primary);
            color: var(--bg-primary);
        }

        button:active, .btn:active {
            transform: translateY(1px);
        }

        button.primary {
            border-color: var(--accent-live);
            color: var(--accent-live);
        }

        button.primary:hover {
            background: var(--accent-live);
            color: var(--bg-primary);
        }

        button.danger {
            border-color: var(--accent-danger);
            color: var(--accent-danger);
        }

        button.danger:hover {
            background: var(--accent-danger);
            color: var(--bg-primary);
        }

        /* Status Badge */
        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border: 1px solid var(--border-primary);
            font-size: 0.65rem;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }

        .badge.live {
            border-color: var(--accent-live);
            color: var(--accent-live);
        }

        .badge.warning {
            border-color: var(--accent-warning);
            color: var(--accent-warning);
        }

        .badge.danger {
            border-color: var(--accent-danger);
            color: var(--accent-danger);
        }

        /* Status Grid Items */
        .status-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }

        .status-item-card {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem;
            border: 1px solid var(--border-secondary);
        }

        .status-label {
            font-size: 0.75rem;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: var(--text-secondary);
        }

        .status-value {
            font-size: 0.85rem;
            letter-spacing: 1px;
        }

        /* Control Panel */
        .control-group {
            margin-bottom: 1.25rem;
        }

        .control-group:last-child {
            margin-bottom: 0;
        }

        .control-label {
            font-size: 0.7rem;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
            display: block;
        }

        .button-group {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        .button-group button {
            flex: 1;
            min-width: 100px;
        }

        /* Input Fields */
        input, select, textarea {
            background: var(--bg-primary);
            border: 1px solid var(--border-secondary);
            color: var(--text-primary);
            padding: 0.5rem;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            width: 100%;
        }

        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: var(--border-primary);
        }

        /* Divider */
        .divider {
            height: 1px;
            background: var(--border-secondary);
            margin: 1.5rem 0;
        }

        /* Half-width cards */
        .half-width {
            grid-column: span 6;
        }

        @media (max-width: 968px) {
            .half-width {
                grid-column: span 12;
            }
        }

        /* Full-width cards */
        .full-width {
            grid-column: span 12;
        }

        /* Icon replacements - use simple text indicators */
        .icon {
            display: inline-block;
            width: 16px;
            height: 16px;
            text-align: center;
            line-height: 16px;
            font-size: 0.75rem;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .header {
                padding: 1rem;
            }

            .header h1 {
                font-size: 1.2rem;
            }

            .stat-value {
                font-size: 2rem;
            }
        }
'''

# Font link for IBM Plex Mono
FONT_LINK = '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&display=swap" rel="stylesheet">'

def update_dashboard():
    """Update the dashboard with tactical UI styling."""

    html_path = Path(__file__).parent.parent / "monitoni" / "telemetry" / "frontend" / "index.html"

    if not html_path.exists():
        print(f"Error: {html_path} not found")
        return

    with open(html_path, 'r') as f:
        content = f.read()

    # Replace the font link
    content = re.sub(
        r'<link href="https://fonts\.googleapis\.com/css2\?family=Inter[^"]+',
        FONT_LINK.replace('<link href="', '').replace('" rel="stylesheet">', ''),
        content
    )

    # Replace the entire style section
    content = re.sub(
        r'<style>.*?</style>',
        f'<style>{TACTICAL_CSS}\n    </style>',
        content,
        flags=re.DOTALL
    )

    # Add corner bracket elements to cards via JavaScript
    # We'll add this to the existing JavaScript section
    corner_script = '''
        // Add corner brackets to all cards
        document.addEventListener('DOMContentLoaded', function() {
            const cards = document.querySelectorAll('.card, .stat-card');
            cards.forEach(card => {
                if (!card.querySelector('.corner-bl')) {
                    const cornerBL = document.createElement('div');
                    cornerBL.className = 'corner-bl';
                    card.appendChild(cornerBL);

                    const cornerBR = document.createElement('div');
                    cornerBR.className = 'corner-br';
                    card.appendChild(cornerBR);
                }
            });
        });
'''

    # Insert corner script before closing script tag
    content = content.replace('</script>\n</body>', f'{corner_script}\n    </script>\n</body>')

    with open(html_path, 'w') as f:
        f.write(content)

    print(f"✓ Updated {html_path} with tactical UI styling")

if __name__ == "__main__":
    update_dashboard()
