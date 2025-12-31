#!/usr/bin/env python3
"""
Script to redesign the telemetry frontend with unique graphical styling and charts.

This creates a visually stunning dashboard with:
- Unique cyberpunk/neon design
- Animated statistics cards
- Interactive charts (Chart.js)
- Better visual hierarchy
- Particle effects background
"""

from pathlib import Path
import re

# Enhanced CSS for unique visual design
ENHANCED_CSS = '''
        /* Enhanced Color Palette - Cyberpunk/Neon Theme */
        :root {
            --bg-primary: #0a0e27;
            --bg-secondary: #151937;
            --bg-card: #1a1f3a;
            --bg-card-hover: #252b4a;
            --accent-primary: #00f5ff;
            --accent-secondary: #b026ff;
            --accent-tertiary: #ff2e97;
            --accent-success: #00ff88;
            --accent-warning: #ffb800;
            --accent-danger: #ff3864;
            --text-primary: #ffffff;
            --text-secondary: #b8c5d6;
            --border-color: #2a3354;
            --glow-primary: rgba(0, 245, 255, 0.4);
            --glow-secondary: rgba(176, 38, 255, 0.4);
            --shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }

        /* Animated Background */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background:
                radial-gradient(circle at 20% 50%, rgba(176, 38, 255, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(0, 245, 255, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 40% 20%, rgba(255, 46, 151, 0.06) 0%, transparent 50%);
            animation: bgShift 20s ease-in-out infinite alternate;
            pointer-events: none;
            z-index: 0;
        }

        @keyframes bgShift {
            0% { transform: translate(0, 0) scale(1); }
            100% { transform: translate(30px, -30px) scale(1.05); }
        }

        /* Grid Lines Background */
        body::after {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image:
                linear-gradient(rgba(0, 245, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 245, 255, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            pointer-events: none;
            z-index: 0;
        }

        /* Glassmorphism Effect */
        .glass {
            background: rgba(26, 31, 58, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* Enhanced Header */
        .header {
            background: linear-gradient(135deg, rgba(21, 25, 55, 0.95) 0%, rgba(26, 31, 58, 0.95) 100%);
            backdrop-filter: blur(20px);
            padding: 1.5rem 2.5rem;
            border-bottom: 2px solid transparent;
            border-image: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary), var(--accent-tertiary)) 1;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
        }

        .header h1 {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            display: flex;
            align-items: center;
            gap: 1rem;
            text-shadow: 0 0 30px var(--glow-primary);
            animation: headerGlow 3s ease-in-out infinite alternate;
        }

        @keyframes headerGlow {
            0% { filter: drop-shadow(0 0 5px var(--glow-primary)); }
            100% { filter: drop-shadow(0 0 20px var(--glow-primary)); }
        }

        /* Neon Connection Status */
        .connection-status {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1.5rem;
            background: rgba(26, 31, 58, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 30px;
            font-size: 0.95rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }

        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--accent-danger);
            box-shadow: 0 0 20px var(--accent-danger);
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        .status-dot.connected {
            background: var(--accent-success);
            box-shadow: 0 0 20px var(--accent-success);
        }

        @keyframes pulse {
            0%, 100% {
                opacity: 1;
                transform: scale(1);
            }
            50% {
                opacity: 0.5;
                transform: scale(1.2);
            }
        }

        /* Main Layout */
        .main-container {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 1.5rem;
            padding: 2rem;
            max-width: 1800px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }

        @media (max-width: 1400px) {
            .main-container {
                grid-template-columns: repeat(6, 1fr);
            }
        }

        @media (max-width: 768px) {
            .main-container {
                grid-template-columns: 1fr;
            }
        }

        /* Enhanced Cards with Neon Borders */
        .card {
            background: linear-gradient(135deg, rgba(26, 31, 58, 0.8) 0%, rgba(21, 25, 55, 0.8) 100%);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 1.75rem;
            border: 1px solid rgba(0, 245, 255, 0.2);
            box-shadow:
                var(--shadow),
                0 0 0 1px rgba(0, 245, 255, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.05);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, transparent 0%, rgba(0, 245, 255, 0.03) 100%);
            opacity: 0;
            transition: opacity 0.4s ease;
            pointer-events: none;
        }

        .card:hover {
            transform: translateY(-5px);
            border-color: rgba(0, 245, 255, 0.4);
            box-shadow:
                0 15px 50px rgba(0, 0, 0, 0.5),
                0 0 20px rgba(0, 245, 255, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }

        .card:hover::before {
            opacity: 1;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1.25rem;
            border-bottom: 1px solid rgba(0, 245, 255, 0.15);
        }

        .card-title {
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: var(--text-primary);
        }

        .card-title i {
            color: var(--accent-primary);
            filter: drop-shadow(0 0 8px var(--accent-primary));
        }

        /* Statistics Cards - Large & Visual */
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

        .stat-card {
            background: linear-gradient(135deg, rgba(26, 31, 58, 0.9) 0%, rgba(21, 25, 55, 0.9) 100%);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
            transition: all 0.4s ease;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, var(--stat-color) 0%, transparent 70%);
            opacity: 0.1;
            transition: opacity 0.4s ease;
        }

        .stat-card:hover {
            transform: translateY(-8px) scale(1.02);
            border-color: var(--stat-color);
            box-shadow: 0 15px 60px rgba(0, 0, 0, 0.5), 0 0 30px var(--stat-glow);
        }

        .stat-card:hover::before {
            opacity: 0.2;
        }

        .stat-card.success {
            --stat-color: var(--accent-success);
            --stat-glow: rgba(0, 255, 136, 0.3);
        }

        .stat-card.danger {
            --stat-color: var(--accent-danger);
            --stat-glow: rgba(255, 56, 100, 0.3);
        }

        .stat-card.primary {
            --stat-color: var(--accent-primary);
            --stat-glow: rgba(0, 245, 255, 0.3);
        }

        .stat-card.warning {
            --stat-color: var(--accent-warning);
            --stat-glow: rgba(255, 184, 0, 0.3);
        }

        .stat-icon {
            width: 60px;
            height: 60px;
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            margin-bottom: 1.25rem;
            background: linear-gradient(135deg, var(--stat-color) 0%, transparent 100%);
            border: 2px solid var(--stat-color);
            color: var(--stat-color);
            box-shadow: 0 0 30px var(--stat-glow), inset 0 0 20px var(--stat-glow);
            animation: iconPulse 3s ease-in-out infinite;
        }

        @keyframes iconPulse {
            0%, 100% {
                transform: scale(1);
                box-shadow: 0 0 30px var(--stat-glow), inset 0 0 20px var(--stat-glow);
            }
            50% {
                transform: scale(1.05);
                box-shadow: 0 0 40px var(--stat-glow), inset 0 0 30px var(--stat-glow);
            }
        }

        .stat-label {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 500;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--stat-color);
            line-height: 1;
            margin-bottom: 0.5rem;
            text-shadow: 0 0 20px var(--stat-glow);
            font-variant-numeric: tabular-nums;
        }

        .stat-change {
            font-size: 0.85rem;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }

        .stat-change i {
            font-size: 0.75rem;
        }

        .stat-change.positive {
            color: var(--accent-success);
        }

        .stat-change.negative {
            color: var(--accent-danger);
        }

        /* Chart Containers */
        .chart-container {
            position: relative;
            width: 100%;
            height: 300px;
            padding: 1rem;
        }

        .chart-card {
            grid-column: span 6;
        }

        @media (max-width: 1200px) {
            .chart-card {
                grid-column: span 12;
            }
        }

        /* Hardware Status - Icon Grid */
        .hardware-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.25rem;
        }

        .hardware-item {
            display: flex;
            align-items: center;
            gap: 1.25rem;
            padding: 1.25rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.3s ease;
        }

        .hardware-item:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(0, 245, 255, 0.3);
            transform: translateX(5px);
        }

        .hardware-icon {
            width: 55px;
            height: 55px;
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            flex-shrink: 0;
            position: relative;
        }

        .hardware-icon::before {
            content: '';
            position: absolute;
            inset: -2px;
            border-radius: 15px;
            padding: 2px;
            background: linear-gradient(135deg, var(--hw-color) 0%, transparent 100%);
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
            -webkit-mask-composite: xor;
            mask-composite: exclude;
        }

        .hardware-icon.connected {
            --hw-color: var(--accent-success);
            background: rgba(0, 255, 136, 0.15);
            color: var(--accent-success);
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.2);
        }

        .hardware-icon.error {
            --hw-color: var(--accent-danger);
            background: rgba(255, 56, 100, 0.15);
            color: var(--accent-danger);
            box-shadow: 0 0 20px rgba(255, 56, 100, 0.2);
        }

        .hardware-info h4 {
            font-size: 1rem;
            margin-bottom: 0.35rem;
            font-weight: 600;
        }

        .hardware-info span {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        /* Buttons with Neon Effect */
        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 10px;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            position: relative;
            overflow: hidden;
            font-family: 'Inter', sans-serif;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }

        .btn:hover::before {
            width: 300px;
            height: 300px;
        }

        .btn span, .btn i {
            position: relative;
            z-index: 1;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(0, 245, 255, 0.3);
        }

        .btn-primary:hover {
            box-shadow: 0 6px 25px rgba(0, 245, 255, 0.5);
            transform: translateY(-2px);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.15);
            border-color: rgba(0, 245, 255, 0.5);
        }

        /* Full width cards */
        .full-width {
            grid-column: span 12;
        }

        .half-width {
            grid-column: span 6;
        }

        .third-width {
            grid-column: span 4;
        }

        @media (max-width: 1200px) {
            .half-width, .third-width {
                grid-column: span 12;
            }
        }

        /* Loading Animation */
        @keyframes shimmer {
            0% {
                background-position: -1000px 0;
            }
            100% {
                background-position: 1000px 0;
            }
        }

        .loading {
            background: linear-gradient(90deg,
                rgba(255, 255, 255, 0.05) 25%,
                rgba(255, 255, 255, 0.1) 50%,
                rgba(255, 255, 255, 0.05) 75%
            );
            background-size: 1000px 100%;
            animation: shimmer 2s infinite;
        }
'''

# Additional JavaScript for charts
CHARTS_JS = '''
        // Chart.js Configuration
        let purchaseChart, hardwareChart;

        function initializeCharts() {
            // Purchase Success Rate Chart (Donut)
            const purchaseCtx = document.getElementById('purchaseChart');
            if (purchaseCtx) {
                purchaseChart = new Chart(purchaseCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Successful', 'Failed'],
                        datasets: [{
                            data: [0, 0],
                            backgroundColor: [
                                'rgba(0, 255, 136, 0.8)',
                                'rgba(255, 56, 100, 0.8)'
                            ],
                            borderColor: [
                                'rgba(0, 255, 136, 1)',
                                'rgba(255, 56, 100, 1)'
                            ],
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    color: '#b8c5d6',
                                    font: {
                                        size: 12,
                                        family: 'Inter'
                                    },
                                    padding: 15
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(26, 31, 58, 0.95)',
                                titleColor: '#fff',
                                bodyColor: '#b8c5d6',
                                borderColor: 'rgba(0, 245, 255, 0.3)',
                                borderWidth: 1,
                                padding: 12,
                                displayColors: true,
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = context.parsed || 0;
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                        return label + ': ' + value + ' (' + percentage + '%)';
                                    }
                                }
                            }
                        },
                        cutout: '70%'
                    }
                });
            }

            // Hardware Health Chart (Bar)
            const hardwareCtx = document.getElementById('hardwareChart');
            if (hardwareCtx) {
                hardwareChart = new Chart(hardwareCtx, {
                    type: 'bar',
                    data: {
                        labels: ['Relay', 'LED', 'Sensor', 'Audio'],
                        datasets: [{
                            label: 'Status',
                            data: [0, 0, 0, 0],
                            backgroundColor: [
                                'rgba(0, 245, 255, 0.6)',
                                'rgba(176, 38, 255, 0.6)',
                                'rgba(255, 46, 151, 0.6)',
                                'rgba(0, 255, 136, 0.6)'
                            ],
                            borderColor: [
                                'rgba(0, 245, 255, 1)',
                                'rgba(176, 38, 255, 1)',
                                'rgba(255, 46, 151, 1)',
                                'rgba(0, 255, 136, 1)'
                            ],
                            borderWidth: 2,
                            borderRadius: 8
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 1,
                                ticks: {
                                    color: '#b8c5d6',
                                    font: { family: 'Inter' },
                                    callback: function(value) {
                                        return value === 1 ? 'OK' : 'Error';
                                    }
                                },
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.05)',
                                    borderColor: 'rgba(255, 255, 255, 0.1)'
                                }
                            },
                            x: {
                                ticks: {
                                    color: '#b8c5d6',
                                    font: { family: 'Inter' }
                                },
                                grid: {
                                    display: false
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                backgroundColor: 'rgba(26, 31, 58, 0.95)',
                                titleColor: '#fff',
                                bodyColor: '#b8c5d6',
                                borderColor: 'rgba(0, 245, 255, 0.3)',
                                borderWidth: 1,
                                padding: 12
                            }
                        }
                    }
                });
            }
        }

        function updateCharts(status) {
            // Update purchase chart
            if (purchaseChart && status.statistics) {
                const completed = status.statistics.completed_purchases || 0;
                const failed = status.statistics.failed_purchases || 0;
                purchaseChart.data.datasets[0].data = [completed, failed];
                purchaseChart.update();
            }

            // Update hardware chart
            if (hardwareChart && status.hardware) {
                const components = status.hardware.components || {};
                const data = [
                    components.relay?.status === 'CONNECTED' ? 1 : 0,
                    components.led?.status === 'CONNECTED' ? 1 : 0,
                    components.sensor?.status === 'CONNECTED' ? 1 : 0,
                    components.audio?.status === 'CONNECTED' ? 1 : 0
                ];
                hardwareChart.data.datasets[0].data = data;
                hardwareChart.update();
            }
        }

        // Initialize charts on load
        window.addEventListener('load', () => {
            if (typeof Chart !== 'undefined') {
                initializeCharts();
            }
        });
'''

def enhance_dashboard():
    """Enhance the dashboard with unique graphical styling."""

    frontend_dir = Path(__file__).parent.parent / "monitoni" / "telemetry" / "frontend"
    html_file = frontend_dir / "index.html"

    if not html_file.exists():
        print(f"Error: {html_file} not found!")
        return False

    # Read the HTML file
    with open(html_file, 'r') as f:
        content = f.read()

    # Add Chart.js CDN before closing </head>
    chart_js_cdn = '''    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>'''
    content = content.replace('</head>', chart_js_cdn)
    print("✓ Added Chart.js CDN")

    # Replace existing CSS (find the style block and replace)
    # Find the start of style block
    style_start = content.find('<style>')
    if style_start != -1:
        # Find the end of original styles (before QR management styles or end of style tag)
        # We'll replace everything up to the QR management styles
        qr_start = content.find('/* QR Code Management Styles */', style_start)
        if qr_start != -1:
            # Replace only the original styles, keep QR styles
            style_end = qr_start
            content = content[:style_start + 7] + '\n' + ENHANCED_CSS + '\n' + content[style_end:]
        else:
            # No QR styles found, replace up to </style>
            style_end = content.find('</style>', style_start)
            content = content[:style_start + 7] + '\n' + ENHANCED_CSS + '\n    ' + content[style_end:]
        print("✓ Enhanced CSS applied")

    # Add charts JavaScript before closing </script>
    last_script = list(re.finditer(r'</script>', content))
    if last_script:
        insert_pos = last_script[-1].start()
        content = content[:insert_pos] + CHARTS_JS + '\n' + content[insert_pos:]
        print("✓ Added Chart.js initialization code")

    # Write the enhanced HTML
    with open(html_file, 'w') as f:
        f.write(content)

    print(f"\n✓ Enhanced dashboard saved to {html_file}")
    print("\nNext: Update HTML structure to add stat cards and charts")
    return True

if __name__ == "__main__":
    enhance_dashboard()
