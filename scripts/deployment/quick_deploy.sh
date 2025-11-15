#!/bin/bash
# Quick deployment helper script
# Run this on your LOCAL machine to deploy to production

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SSH_KEY="${SSH_KEY:-$HOME/.ssh/tvs_wages_prod}"
SSH_HOST="${SSH_HOST:-tvs-wages-prod}"
REMOTE_USER="${REMOTE_USER:-tvswages}"
REMOTE_PATH="${REMOTE_PATH:-/var/www/tvs-wages}"
LOCAL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if SSH key exists
    if [ ! -f "$SSH_KEY" ]; then
        print_error "SSH key not found: $SSH_KEY"
        print_info "Generate one with: ssh-keygen -t ed25519 -f $SSH_KEY"
        exit 1
    fi
    print_success "SSH key found"
    
    # Check if can connect to server
    if ! ssh -i "$SSH_KEY" -o ConnectTimeout=5 "$SSH_HOST" "echo 'Connection test'" &> /dev/null; then
        print_error "Cannot connect to server: $SSH_HOST"
        print_info "Check your SSH configuration in ~/.ssh/config"
        exit 1
    fi
    print_success "Server connection verified"
    
    # Check if .env file exists
    if [ ! -f "$LOCAL_PATH/.env" ]; then
        print_warning ".env file not found locally"
        print_info "Make sure to create it on the server"
    else
        print_success ".env file found"
    fi
}

sync_code() {
    print_header "Syncing Application Code"
    
    print_info "Syncing from: $LOCAL_PATH"
    print_info "Syncing to: $SSH_HOST:$REMOTE_PATH"
    
    rsync -avz --progress \
        --exclude 'data/' \
        --exclude '__pycache__/' \
        --exclude '*.pyc' \
        --exclude '.git/' \
        --exclude 'venv/' \
        --exclude '.env' \
        --exclude '*.log' \
        --exclude '.DS_Store' \
        -e "ssh -i $SSH_KEY" \
        "$LOCAL_PATH/" \
        "$SSH_HOST:$REMOTE_PATH/"
    
    print_success "Code synced successfully"
}

sync_data() {
    print_header "Syncing Data (Database & Documents)"
    
    read -p "Do you want to sync the database? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Syncing database..."
        rsync -avz --progress \
            -e "ssh -i $SSH_KEY" \
            "$LOCAL_PATH/data/database/payslips.db" \
            "$SSH_HOST:$REMOTE_PATH/data/database/"
        print_success "Database synced"
    fi
    
    read -p "Do you want to sync payslips? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Syncing payslips (this may take a while)..."
        rsync -avz --progress \
            -e "ssh -i $SSH_KEY" \
            "$LOCAL_PATH/data/documents/payslips/" \
            "$SSH_HOST:$REMOTE_PATH/data/documents/payslips/"
        print_success "Payslips synced"
    fi
    
    read -p "Do you want to sync runsheets? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Syncing runsheets (this may take a while)..."
        rsync -avz --progress \
            -e "ssh -i $SSH_KEY" \
            "$LOCAL_PATH/data/documents/runsheets/" \
            "$SSH_HOST:$REMOTE_PATH/data/documents/runsheets/"
        print_success "Runsheets synced"
    fi
}

update_dependencies() {
    print_header "Updating Dependencies on Server"
    
    ssh -i "$SSH_KEY" "$SSH_HOST" << 'ENDSSH'
        cd /var/www/tvs-wages
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
ENDSSH
    
    print_success "Dependencies updated"
}

restart_application() {
    print_header "Restarting Application"
    
    ssh -i "$SSH_KEY" "$SSH_HOST" "sudo systemctl restart tvs-wages"
    print_success "Application restarted"
    
    sleep 3
    
    print_info "Checking application status..."
    ssh -i "$SSH_KEY" "$SSH_HOST" "sudo systemctl status tvs-wages --no-pager"
}

check_logs() {
    print_header "Recent Application Logs"
    
    ssh -i "$SSH_KEY" "$SSH_HOST" "sudo journalctl -u tvs-wages -n 20 --no-pager"
}

show_menu() {
    print_header "TVS Wages - Quick Deployment Tool"
    
    echo "1) Full Deployment (code + dependencies + restart)"
    echo "2) Code Only (sync code + restart)"
    echo "3) Data Migration (database + documents)"
    echo "4) Update Dependencies Only"
    echo "5) Restart Application"
    echo "6) View Logs"
    echo "7) Check Status"
    echo "8) Run Prerequisites Check"
    echo "9) Exit"
    echo
    read -p "Select option: " choice
    
    case $choice in
        1)
            check_prerequisites
            sync_code
            update_dependencies
            restart_application
            check_logs
            ;;
        2)
            check_prerequisites
            sync_code
            restart_application
            check_logs
            ;;
        3)
            check_prerequisites
            sync_data
            restart_application
            ;;
        4)
            check_prerequisites
            update_dependencies
            restart_application
            ;;
        5)
            restart_application
            check_logs
            ;;
        6)
            print_header "Application Logs (last 50 lines)"
            ssh -i "$SSH_KEY" "$SSH_HOST" "sudo journalctl -u tvs-wages -n 50 --no-pager"
            ;;
        7)
            print_header "Application Status"
            ssh -i "$SSH_KEY" "$SSH_HOST" "sudo systemctl status tvs-wages --no-pager"
            ;;
        8)
            check_prerequisites
            print_success "All prerequisites met!"
            ;;
        9)
            print_info "Goodbye!"
            exit 0
            ;;
        *)
            print_error "Invalid option"
            ;;
    esac
}

# Main execution
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "TVS Wages Quick Deployment Tool"
    echo
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --help, -h          Show this help message"
    echo "  --full              Full deployment (code + deps + restart)"
    echo "  --code              Code only deployment"
    echo "  --data              Data migration"
    echo "  --restart           Restart application"
    echo "  --logs              View logs"
    echo "  --status            Check status"
    echo
    echo "Environment Variables:"
    echo "  SSH_KEY             Path to SSH private key (default: ~/.ssh/tvs_wages_prod)"
    echo "  SSH_HOST            SSH host alias (default: tvs-wages-prod)"
    echo "  REMOTE_USER         Remote user (default: tvswages)"
    echo "  REMOTE_PATH         Remote path (default: /var/www/tvs-wages)"
    echo
    echo "Examples:"
    echo "  $0                  # Interactive menu"
    echo "  $0 --full           # Full deployment"
    echo "  $0 --code           # Code only"
    echo "  SSH_HOST=myserver $0 --restart  # Restart on custom host"
    exit 0
fi

# Handle command line arguments
case "$1" in
    --full)
        check_prerequisites
        sync_code
        update_dependencies
        restart_application
        check_logs
        ;;
    --code)
        check_prerequisites
        sync_code
        restart_application
        check_logs
        ;;
    --data)
        check_prerequisites
        sync_data
        restart_application
        ;;
    --restart)
        restart_application
        check_logs
        ;;
    --logs)
        ssh -i "$SSH_KEY" "$SSH_HOST" "sudo journalctl -u tvs-wages -n 50 --no-pager"
        ;;
    --status)
        ssh -i "$SSH_KEY" "$SSH_HOST" "sudo systemctl status tvs-wages --no-pager"
        ;;
    *)
        # Interactive mode
        while true; do
            show_menu
            echo
            read -p "Press Enter to continue or Ctrl+C to exit..."
        done
        ;;
esac

print_success "Done!"
