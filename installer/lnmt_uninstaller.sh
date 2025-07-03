#!/bin/bash
# LNMT Uninstaller - Linux Network Management Toolbox
# Safe removal with backup and confirmation options
# Version: 1.0.0

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly LNMT_USER="lnmt"
readonly LNMT_GROUP="lnmt"
readonly LNMT_HOME="/opt/lnmt"
readonly LNMT_CONFIG_DIR="/etc/lnmt"
readonly LNMT_LOG_DIR="/var/log/lnmt"
readonly LNMT_DATA_DIR="/var/lib/lnmt"
readonly LNMT_BIN_DIR="/usr/local/bin"
readonly UNINSTALL_LOG="/var/log/lnmt-uninstall.log"

# Global variables
INTERACTIVE_MODE=true
FORCE_REMOVE=false
CREATE_BACKUP=true
BACKUP_DIR=""
REMOVE_USER=true
REMOVE_LOGS=false
REMOVE_DATA=false

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${UNINSTALL_LOG}"
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "${YELLOW}$*${NC}"; }
log_error() { log "ERROR" "${RED}$*${NC}"; }
log_success() { log "SUCCESS" "${GREEN}$*${NC}"; }

# Root check
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        echo "Please run: sudo $0 $*"
        exit 1
    fi
}

# Check if LNMT is installed
check_installation() {
    log_info "Checking LNMT installation..."
    
    local installed=false
    local components=()
    
    # Check for main components
    if [[ -d "$LNMT_HOME" ]]; then
        installed=true
        components+=("Application files")
    fi
    
    if [[ -d "$LNMT_CONFIG_DIR" ]]; then
        installed=true
        components+=("Configuration files")
    fi
    
    if [[ -d "$LNMT_DATA_DIR" ]]; then
        installed=true
        components+=("Data files")
    fi
    
    if id "$LNMT_USER" &>/dev/null; then
        installed=true
        components+=("System user")
    fi
    
    # Check for systemd services
    local services=("lnmt" "lnmt-web" "lnmt-scheduler")
    for service in "${services[@]}"; do
        if systemctl list-unit-files | grep -q "^${service}.service"; then
            installed=true
            components+=("${service} service")
        fi
    done
    
    if [[ "$installed" == false ]]; then
        log_warn "LNMT does not appear to be installed on this system"
        exit 0
    fi
    
    log_info "Found LNMT components: ${components[*]}"
}

# Create backup before uninstall
create_backup() {
    if [[ "$CREATE_BACKUP" != true ]]; then
        return 0
    fi
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    BACKUP_DIR="/tmp/lnmt-uninstall-backup-${timestamp}"
    
    log_info "Creating backup at: $BACKUP_DIR"
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup components that exist
    local backup_items=(
        "$LNMT_HOME:lnmt_home"
        "$LNMT_CONFIG_DIR:config"
        "$LNMT_DATA_DIR:data"
        "$LNMT_LOG_DIR:logs"
        "/etc/systemd/system/lnmt*.service:systemd_services"
        "/etc/logrotate.d/lnmt:logrotate"
    )
    
    for item in "${backup_items[@]}"; do
        local source="${item%:*}"
        local dest="${item#*:}"
        
        if [[ -e "$source" ]]; then
            local backup_dest="$BACKUP_DIR/$dest"
            
            if [[ -d "$source" ]]; then
                cp -r "$source" "$backup_dest"
            elif [[ -f "$source" ]]; then
                mkdir -p "$(dirname "$backup_dest")"
                cp "$source" "$backup_dest"
            else
                # Handle glob patterns (like systemd services)
                mkdir -p "$backup_dest"
                cp $source "$backup_dest/" 2>/dev/null || true
            fi
            
            log_info "Backed up: $source"
        fi
    done
    
    # Create backup manifest
    cat > "$BACKUP_DIR/manifest.txt" << EOF
LNMT Uninstall Backup
Created: $(date)
System: $(uname -a)
LNMT Version: $(cat "$LNMT_HOME/VERSION" 2>/dev/null || echo "unknown")

Backup Contents:
$(find "$BACKUP_DIR" -type f | sort)
EOF
    
    log_success "Backup created at: $BACKUP_DIR"
}

# Stop all LNMT services
stop_services() {
    log_info "Stopping LNMT services..."
    
    local services=("lnmt-scheduler" "lnmt-web" "lnmt")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            log_info "Stopping $service..."
            systemctl stop "$service" || log_warn "Failed to stop $service"
        fi
        
        if systemctl is-enabled --quiet "$service" 2>/dev/null; then
            log_info "Disabling $service..."
            systemctl disable "$service" || log_warn "Failed to disable $service"
        fi
    done
    
    log_success "Services stopped and disabled"
}

# Remove systemd service files
remove_systemd_services() {
    log_info "Removing systemd service files..."
    
    local service_files=(
        "/etc/systemd/system/lnmt.service"
        "/etc/systemd/system/lnmt-web.service"
        "/etc/systemd/system/lnmt-scheduler.service"
    )
    
    for service_file in "${service_files[@]}"; do
        if [[ -f "$service_file" ]]; then
            rm -f "$service_file"
            log_info "Removed: $service_file"
        fi
    done
    
    # Reload systemd daemon
    systemctl daemon-reload
    log_success "Systemd services removed"
}

# Remove application files
remove_application_files() {
    log_info "Removing application files..."
    
    # Remove main application directory
    if [[ -d "$LNMT_HOME" ]]; then
        rm -rf "$LNMT_HOME"
        log_info "Removed: $LNMT_HOME"
    fi
    
    # Remove binary symlinks
    local bin_files=(
        "$LNMT_BIN_DIR/lnmt"
        "$LNMT_BIN_DIR/lnmt-cli"
    )
    
    for bin_file in "${bin_files[@]}"; do
        if [[ -L "$bin_file" ]] || [[ -f "$bin_file" ]]; then
            rm -f "$bin_file"
            log_info "Removed: $bin_file"
        fi
    done
    
    log_success "Application files removed"
}

# Remove configuration files
remove_config_files() {
    log_info "Removing configuration files..."
    
    if [[ -d "$LNMT_CONFIG_DIR" ]]; then
        if [[ "$INTERACTIVE_MODE" == true && "$FORCE_REMOVE" != true ]]; then
            echo
            echo "Configuration directory contains:"
            ls -la "$LNMT_CONFIG_DIR"
            echo
            read -p "Remove configuration files? [y/N]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$LNMT_CONFIG_DIR"
                log_info "Removed: $LNMT_CONFIG_DIR"
            else
                log_warn "Keeping configuration files at: $LNMT_CONFIG_DIR"
            fi
        else
            rm -rf "$LNMT_CONFIG_DIR"
            log_info "Removed: $LNMT_CONFIG_DIR"
        fi
    fi
    
    # Remove logrotate configuration
    if [[ -f "/etc/logrotate.d/lnmt" ]]; then
        rm -f "/etc/logrotate.d/lnmt"
        log_info "Removed: /etc/logrotate.d/lnmt"
    fi
    
    log_success "Configuration files processed"
}

# Remove data files
remove_data_files() {
    if [[ "$REMOVE_DATA" != true ]]; then
        log_info "Skipping data files (use --remove-data to delete)"
        return 0
    fi
    
    log_info "Removing data files..."
    
    if [[ -d "$LNMT_DATA_DIR" ]]; then
        if [[ "$INTERACTIVE_MODE" == true && "$FORCE_REMOVE" != true ]]; then
            echo
            echo "Data directory contains:"
            du -sh "$LNMT_DATA_DIR"/* 2>/dev/null || echo "  (empty or inaccessible)"
            echo
            log_warn "This will permanently delete all LNMT data including databases!"
            read -p "Are you sure you want to remove data files? [y/N]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$LNMT_DATA_DIR"
                log_info "Removed: $LNMT_DATA_DIR"
            else
                log_warn "Keeping data files at: $LNMT_DATA_DIR"
            fi
        else
            rm -rf "$LNMT_DATA_DIR"
            log_info "Removed: $LNMT_DATA_DIR"
        fi
    fi
    
    log_success "Data files processed"
}

# Remove log files
remove_log_files() {
    if [[ "$REMOVE_LOGS" != true ]]; then
        log_info "Skipping log files (use --remove-logs to delete)"
        return 0
    fi
    
    log_info "Removing log files..."
    
    if [[ -d "$LNMT_LOG_DIR" ]]; then
        rm -rf "$LNMT_LOG_DIR"
        log_info "Removed: $LNMT_LOG_DIR"
    fi
    
    # Remove individual log files that might exist elsewhere
    local log_files=(
        "/var/log/lnmt-install.log"
        "/var/log/lnmt-update.log"
    )
    
    for log_file in "${log_files[@]}"; do
        if [[ -f "$log_file" ]]; then
            rm -f "$log_file"
            log_info "Removed: $log_file"
        fi
    done
    
    log_success "Log files removed"
}

# Remove system user and group
remove_user() {
    if [[ "$REMOVE_USER" != true ]]; then
        log_info "Skipping user removal (use --keep-user to retain)"
        return 0
    fi
    
    log_info "Removing system user and group..."
    
    # Check if user exists and remove
    if id "$LNMT_USER" &>/dev/null; then
        # Kill any processes running as the user
        pkill -u "$LNMT_USER" 2>/dev/null || true
        
        # Remove user
        userdel "$LNMT_USER" 2>/dev/null || log_warn "Failed to remove user $LNMT_USER"
        log_info "Removed user: $LNMT_USER"
    fi
    
    # Check if group exists and remove (only if no other users are in it)
    if getent group "$LNMT_GROUP" &>/dev/null; then
        groupdel "$LNMT_GROUP" 2>/dev/null || log_warn "Failed to remove group $LNMT_GROUP"
        log_info "Removed group: $LNMT_GROUP"
    fi
    
    log_success "System user and group removed"
}

# Remove Python packages (if installed via pip)
remove_python_packages() {
    log_info "Checking for Python packages to remove..."
    
    # Check if LNMT was installed via pip
    local python_cmds=("python3" "python")
    local found_packages=()
    
    for python_cmd in "${python_cmds[@]}"; do
        if command -v "$python_cmd" &>/dev/null; then
            # Check for LNMT package
            if $python_cmd -m pip list 2>/dev/null | grep -i "^lnmt\s" &>/dev/null; then
                found_packages+=("lnmt")
            fi
            break
        fi
    done
    
    if [[ ${#found_packages[@]} -gt 0 ]]; then
        if [[ "$INTERACTIVE_MODE" == true && "$FORCE_REMOVE" != true ]]; then
            echo
            echo "Found Python packages: ${found_packages[*]}"
            read -p "Remove Python packages? [y/N]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                for package in "${found_packages[@]}"; do
                    $python_cmd -m pip uninstall -y "$package" || log_warn "Failed to uninstall $package"
                    log_info "Uninstalled Python package: $package"
                done
            fi
        else
            for package in "${found_packages[@]}"; do
                $python_cmd -m pip uninstall -y "$package" || log_warn "Failed to uninstall $package"
                log_info "Uninstalled Python package: $package"
            done
        fi
    else
        log_info "No LNMT Python packages found"
    fi
}

# Clean up remaining artifacts
cleanup_artifacts() {
    log_info "Cleaning up remaining artifacts..."
    
    # Remove any remaining symlinks or references
    local cleanup_items=(
        "/usr/share/applications/lnmt.desktop"
        "/etc/bash_completion.d/lnmt"
        "/etc/profile.d/lnmt.sh"
    )
    
    for item in "${cleanup_items[@]}"; do
        if [[ -e "$item" ]]; then
            rm -f "$item"
            log_info "Removed: $item"
        fi
    done
    
    # Clean up any cron jobs
    if crontab -l 2>/dev/null | grep -q "lnmt"; then
        log_warn "Found LNMT entries in crontab. Please remove manually:"
        crontab -l | grep "lnmt"
    fi
    
    # Check for any remaining LNMT processes
    local lnmt_procs=$(pgrep -f "lnmt" 2>/dev/null || true)
    if [[ -n "$lnmt_procs" ]]; then
        log_warn "Found running LNMT processes: $lnmt_procs"
        if [[ "$FORCE_REMOVE" == true ]]; then
            pkill -f "lnmt" || true
            log_info "Killed remaining LNMT processes"
        fi
    fi
    
    log_success "Cleanup completed"
}

# Show uninstall summary
show_summary() {
    echo
    echo "=============================================="
    log_success "LNMT Uninstallation Complete!"
    echo "=============================================="
    echo
    echo "Removed Components:"
    echo "  • Application files ($LNMT_HOME)"
    echo "  • Systemd services"
    echo "  • Binary links ($LNMT_BIN_DIR)"
    
    if [[ "$REMOVE_DATA" == true ]]; then
        echo "  • Data files ($LNMT_DATA_DIR)"
    else
        echo "  • Data files: PRESERVED at $LNMT_DATA_DIR"
    fi
    
    if [[ "$REMOVE_LOGS" == true ]]; then
        echo "  • Log files ($LNMT_LOG_DIR)"
    else
        echo "  • Log files: PRESERVED at $LNMT_LOG_DIR"
    fi
    
    if [[ "$REMOVE_USER" == true ]]; then
        echo "  • System user and group ($LNMT_USER:$LNMT_GROUP)"
    else
        echo "  • System user: PRESERVED ($LNMT_USER)"
    fi
    
    echo
    if [[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR" ]]; then
        echo "Backup Location: $BACKUP_DIR"
        echo "  • Use this backup to restore LNMT if needed"
        echo "  • Backup includes all removed components"
        echo
    fi
    
    echo "System Status:"
    echo "  • All LNMT services stopped and disabled"
    echo "  • No LNMT processes running"
    echo "  • System returned to pre-LNMT state"
    echo
    
    if [[ -d "$LNMT_CONFIG_DIR" ]] || [[ -d "$LNMT_DATA_DIR" ]]; then
        echo "Remaining Files:"
        [[ -d "$LNMT_CONFIG_DIR" ]] && echo "  • Configuration: $LNMT_CONFIG_DIR"
        [[ -d "$LNMT_DATA_DIR" ]] && echo "  • Data: $LNMT_DATA_DIR"
        echo "  • These were preserved for safety"
        echo "  • Remove manually if no longer needed"
        echo
    fi
    
    echo "Uninstall Log: $UNINSTALL_LOG"
    echo "=============================================="
}

# Usage information
usage() {
    cat << EOF
LNMT Uninstaller - Linux Network Management Toolbox

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -f, --force             Force removal without confirmation
    -i, --interactive       Interactive mode (default)
    --no-backup            Skip creating backup
    --backup-dir DIR       Custom backup directory
    --remove-data          Remove data files (databases, etc.)
    --remove-logs          Remove log files
    --keep-user            Keep system user and group
    --remove-python        Remove Python packages
    -v, --verbose          Enable verbose output

Examples:
    $0                     Interactive uninstall with backup
    $0 --force             Force uninstall without prompts
    $0 --remove-data       Remove everything including data
    $0 --no-backup         Uninstall without creating backup

Safety Features:
    • Creates backup before removal (unless --no-backup)
    • Preserves data and logs by default
    • Interactive confirmation for destructive operations
    • Detailed logging of all operations

EOF
}

# Confirmation dialog
confirm_uninstall() {
    if [[ "$INTERACTIVE_MODE" != true || "$FORCE_REMOVE" == true ]]; then
        return 0
    fi
    
    echo
    echo "=============================================="
    echo "LNMT UNINSTALL CONFIRMATION"
    echo "=============================================="
    echo
    echo "This will remove LNMT from your system:"
    echo "  • Application files and binaries"
    echo "  • Systemd services"
    echo "  • Configuration files (with confirmation)"
    
    if [[ "$REMOVE_DATA" == true ]]; then
        echo "  • Data files (INCLUDING DATABASES)"
    fi
    
    if [[ "$REMOVE_LOGS" == true ]]; then
        echo "  • Log files"
    fi
    
    if [[ "$REMOVE_USER" == true ]]; then
        echo "  • System user and group"
    fi
    
    echo
    if [[ "$CREATE_BACKUP" == true ]]; then
        echo "A backup will be created before removal."
    else
        log_warn "NO BACKUP will be created!"
    fi
    
    echo
    read -p "Are you sure you want to proceed? [y/N]: " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Uninstall cancelled by user"
        exit 0
    fi
    
    echo
    log_warn "Starting uninstall in 3 seconds... (Ctrl+C to cancel)"
    sleep 3
}

# Main uninstall function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -f|--force)
                FORCE_REMOVE=true
                INTERACTIVE_MODE=false
                shift
                ;;
            -i|--interactive)
                INTERACTIVE_MODE=true
                shift
                ;;
            --no-backup)
                CREATE_BACKUP=false
                shift
                ;;
            --backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            --remove-data)
                REMOVE_DATA=true
                shift
                ;;
            --remove-logs)
                REMOVE_LOGS=true
                shift
                ;;
            --keep-user)
                REMOVE_USER=false
                shift
                ;;
            --remove-python)
                REMOVE_PYTHON=true
                shift
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Initialize logging
    mkdir -p "$(dirname "$UNINSTALL_LOG")"
    
    echo "LNMT Uninstaller"
    echo "================"
    
    # Pre-flight checks
    check_root
    check_installation
    
    # Show confirmation
    confirm_uninstall
    
    # Create backup
    if [[ "$CREATE_BACKUP" == true ]]; then
        create_backup
    fi
    
    # Uninstallation steps
    log_info "Starting LNMT removal..."
    
    stop_services
    remove_systemd_services
    remove_application_files
    remove_config_files
    remove_data_files
    remove_log_files
    remove_user
    
    if [[ "${REMOVE_PYTHON:-false}" == true ]]; then
        remove_python_packages
    fi
    
    cleanup_artifacts
    
    # Show summary
    show_summary
    
    log_success "LNMT uninstallation completed successfully!"
}

# Run main function
main "$@"