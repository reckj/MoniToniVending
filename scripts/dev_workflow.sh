#!/bin/bash
# MoniToni Development Workflow Script (for MacBook)
# This script helps with common development tasks

# Configuration
PI_USER="${PI_USER:-pi}"
PI_HOST="${PI_HOST:-monitoni-pi.local}"  # Change to your Pi's IP or hostname
PI_DIR="~/MoniToniVending"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function for colored output
print_header() {
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=====================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Function to check SSH connection
check_connection() {
    ssh -o ConnectTimeout=5 -o BatchMode=yes ${PI_USER}@${PI_HOST} "echo 2>&1" > /dev/null 2>&1
    return $?
}

# Function: Sync code to Pi
sync_to_pi() {
    print_header "Syncing Code to Raspberry Pi"

    if ! check_connection; then
        print_error "Cannot connect to Pi at ${PI_USER}@${PI_HOST}"
        print_info "Make sure the Pi is on and accessible"
        exit 1
    fi

    print_info "Syncing files..."
    rsync -avz --delete \
        --exclude '.git' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.pytest_cache' \
        --exclude 'venv' \
        --exclude '.venv' \
        --exclude 'data/' \
        --exclude 'logs/' \
        --exclude 'config/local.yaml' \
        ./ ${PI_USER}@${PI_HOST}:${PI_DIR}/

    print_success "Code synced to Pi"
}

# Function: Run on Pi
run_on_pi() {
    print_header "Running MoniToni on Raspberry Pi"

    if ! check_connection; then
        print_error "Cannot connect to Pi"
        exit 1
    fi

    MODE="${1:---mock}"
    print_info "Running with mode: $MODE"

    ssh -t ${PI_USER}@${PI_HOST} "cd ${PI_DIR} && python3 -m monitoni.main $MODE"
}

# Function: View logs on Pi
view_logs() {
    print_header "Viewing Logs on Raspberry Pi"

    if ! check_connection; then
        print_error "Cannot connect to Pi"
        exit 1
    fi

    ssh -t ${PI_USER}@${PI_HOST} "cd ${PI_DIR} && tail -f logs/monitoni.log"
}

# Function: Pull changes from Pi
pull_from_pi() {
    print_header "Pulling Changes from Raspberry Pi"

    if ! check_connection; then
        print_error "Cannot connect to Pi"
        exit 1
    fi

    print_info "Pulling modified files..."
    rsync -avz \
        --exclude '.git' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude 'venv' \
        --exclude 'data/' \
        --exclude 'logs/' \
        ${PI_USER}@${PI_HOST}:${PI_DIR}/ ./

    print_success "Changes pulled from Pi"
}

# Function: SSH into Pi
ssh_to_pi() {
    print_header "Connecting to Raspberry Pi via SSH"

    if ! check_connection; then
        print_error "Cannot connect to Pi"
        exit 1
    fi

    print_info "Opening SSH session..."
    ssh -t ${PI_USER}@${PI_HOST} "cd ${PI_DIR} && bash"
}

# Function: Test LED control
test_led() {
    print_header "Testing LED Control on Raspberry Pi"

    if ! check_connection; then
        print_error "Cannot connect to Pi"
        exit 1
    fi

    print_info "Running LED test script..."
    ssh -t ${PI_USER}@${PI_HOST} "cd ${PI_DIR} && python3 -c \"
import asyncio
from monitoni.hardware.wled_controller import WLEDController

async def test():
    config = {
        'ip_address': '192.168.1.100',  # Change to your WLED IP
        'universe': 0,
        'pixel_count': 300,
        'fps': 30,
        'zones': [
            {'name': f'Level {i+1}', 'start': i*30, 'end': (i+1)*30-1}
            for i in range(10)
        ]
    }

    controller = WLEDController(config)
    await controller.connect()

    print('Testing rainbow animation...')
    await controller.set_animation('rainbow_chase', brightness=0.5, speed=2.0)
    await asyncio.sleep(5)

    print('Testing zone highlight...')
    for zone in range(10):
        await controller.highlight_zone(zone, color=(255, 0, 0))
        await asyncio.sleep(1)

    print('Clearing...')
    await controller.clear()
    await controller.disconnect()

asyncio.run(test())
\""
}

# Function: Setup SSH keys
setup_ssh() {
    print_header "Setting Up SSH Key Authentication"

    print_info "This will copy your SSH key to the Pi for passwordless login"

    if [ ! -f ~/.ssh/id_rsa.pub ]; then
        print_info "No SSH key found. Generating one..."
        ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
    fi

    print_info "Copying SSH key to Pi..."
    ssh-copy-id ${PI_USER}@${PI_HOST}

    print_success "SSH key installed. You can now connect without a password."
}

# Function: Show status
show_status() {
    print_header "Raspberry Pi Status"

    if ! check_connection; then
        print_error "Pi is OFFLINE or unreachable"
        exit 1
    fi

    print_success "Pi is ONLINE at ${PI_USER}@${PI_HOST}"

    echo ""
    print_info "System Information:"
    ssh ${PI_USER}@${PI_HOST} "
        echo 'Hostname:    \$(hostname)'
        echo 'IP Address:  \$(hostname -I | awk '{print \$1}')'
        echo 'OS:          \$(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')'
        echo 'Uptime:      \$(uptime -p)'
        echo 'Temperature: \$(vcgencmd measure_temp 2>/dev/null || echo 'N/A')'
    "

    echo ""
    print_info "MoniToni Status:"
    ssh ${PI_USER}@${PI_HOST} "
        if systemctl is-active --quiet monitoni; then
            echo 'Service:     RUNNING'
        else
            echo 'Service:     STOPPED'
        fi

        if [ -d ${PI_DIR} ]; then
            cd ${PI_DIR}
            echo \"Git Branch:  \$(git branch --show-current 2>/dev/null || echo 'N/A')\"
            echo \"Git Commit:  \$(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')\"
        fi
    "
}

# Main menu
show_menu() {
    clear
    print_header "MoniToni Development Workflow"
    echo ""
    echo "Pi Target: ${PI_USER}@${PI_HOST}"
    echo ""
    echo "1)  Sync code to Pi"
    echo "2)  Run on Pi (with real hardware)"
    echo "3)  Run on Pi (with --mock)"
    echo "4)  View logs on Pi"
    echo "5)  Pull changes from Pi"
    echo "6)  SSH into Pi"
    echo "7)  Test LED control"
    echo "8)  Setup SSH keys"
    echo "9)  Show Pi status"
    echo "10) Run locally (--mock)"
    echo "q)  Quit"
    echo ""
    read -p "Choose an option: " choice

    case $choice in
        1) sync_to_pi ;;
        2) run_on_pi "" ;;
        3) run_on_pi "--mock" ;;
        4) view_logs ;;
        5) pull_from_pi ;;
        6) ssh_to_pi ;;
        7) test_led ;;
        8) setup_ssh ;;
        9) show_status ;;
        10) python3 -m monitoni.main --mock ;;
        q|Q) exit 0 ;;
        *) print_error "Invalid option" ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
    show_menu
}

# Parse command line arguments
case "$1" in
    sync)
        sync_to_pi
        ;;
    run)
        run_on_pi "${2:---mock}"
        ;;
    logs)
        view_logs
        ;;
    pull)
        pull_from_pi
        ;;
    ssh)
        ssh_to_pi
        ;;
    led)
        test_led
        ;;
    setup-ssh)
        setup_ssh
        ;;
    status)
        show_status
        ;;
    *)
        show_menu
        ;;
esac
