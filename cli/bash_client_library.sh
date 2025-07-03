#!/bin/bash
# LNMT Bash API Client Library
#
# A comprehensive Bash client for the Linux Network Management Toolkit (LNMT) REST API.
# Provides command-line functions for all LNMT functionality including device management,
# VLAN configuration, DNS management, and system monitoring.
#
# Usage:
#   source lnmt_api.sh
#   lnmt_login "https://api.lnmt.local" "admin" "password"
#   lnmt_get_devices
#   lnmt_logout
#
# Environment Variables:
#   LNMT_BASE_URL    - Base URL of LNMT server
#   LNMT_TOKEN       - JWT authentication token
#   LNMT_API_KEY     - API key for authentication
#   LNMT_VERIFY_SSL  - Set to 'false' to disable SSL verification
#   LNMT_DEBUG       - Set to 'true' to enable debug output

set -euo pipefail

# Global variables
LNMT_BASE_URL="${LNMT_BASE_URL:-}"
LNMT_TOKEN="${LNMT_TOKEN:-}"
LNMT_API_KEY="${LNMT_API_KEY:-}"
LNMT_VERIFY_SSL="${LNMT_VERIFY_SSL:-true}"
LNMT_DEBUG="${LNMT_DEBUG:-false}"
LNMT_CONFIG_FILE="${HOME}/.lnmt/config"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Utility functions
lnmt_debug() {
    if [[ "$LNMT_DEBUG" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*" >&2
    fi
}

lnmt_info() {
    echo -e "${GREEN}[INFO]${NC} $*" >&2
}

lnmt_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

lnmt_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# Check if required tools are available
lnmt_check_dependencies() {
    local missing_deps=()
    
    if ! command -v curl >/dev/null 2>&1; then
        missing_deps+=("curl")
    fi
    
    if ! command -v jq >/dev/null 2>&1; then
        missing_deps+=("jq")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        lnmt_error "Missing required dependencies: ${missing_deps[*]}"
        lnmt_error "Please install: sudo apt-get install curl jq"
        return 1
    fi
}

# Load configuration from file
lnmt_load_config() {
    if [[ -f "$LNMT_CONFIG_FILE" ]]; then
        lnmt_debug "Loading config from $LNMT_CONFIG_FILE"
        source "$LNMT_CONFIG_FILE"
    fi
}

# Save configuration to file
lnmt_save_config() {
    local config_dir
    config_dir=$(dirname "$LNMT_CONFIG_FILE")
    
    if [[ ! -d "$config_dir" ]]; then
        mkdir -p "$config_dir"
    fi
    
    cat > "$LNMT_CONFIG_FILE" << EOF
LNMT_BASE_URL="$LNMT_BASE_URL"
LNMT_TOKEN="$LNMT_TOKEN"
LNMT_API_KEY="$LNMT_API_KEY"
LNMT_VERIFY_SSL="$LNMT_VERIFY_SSL"
EOF
    
    chmod 600 "$LNMT_CONFIG_FILE"
    lnmt_debug "Config saved to $LNMT_CONFIG_FILE"
}

# Make HTTP request to LNMT API
lnmt_request() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    local content_type="${4:-application/json}"
    local auth_required="${5:-true}"
    
    # Check dependencies
    lnmt_check_dependencies || return 1
    
    # Validate base URL
    if [[ -z "$LNMT_BASE_URL" ]]; then
        lnmt_error "LNMT_BASE_URL not set. Use lnmt_set_url or lnmt_login first."
        return 1
    fi
    
    # Build URL
    local url="${LNMT_BASE_URL}${endpoint}"
    
    # Prepare curl options
    local curl_opts=()
    curl_opts+=("-s" "-w" "%{http_code}")
    curl_opts+=("-X" "$method")
    curl_opts+=("-H" "Content-Type: $content_type")
    curl_opts+=("-H" "User-Agent: LNMT-Bash-Client/2.0.0")
    
    # SSL verification
    if [[ "$LNMT_VERIFY_SSL" == "false" ]]; then
        curl_opts+=("-k")
    fi
    
    # Authentication
    if [[ "$auth_required" == "true" ]]; then
        if [[ -n "$LNMT_TOKEN" ]]; then
            curl_opts+=("-H" "Authorization: Bearer $LNMT_TOKEN")
        elif [[ -n "$LNMT_API_KEY" ]]; then
            curl_opts+=("-H" "X-API-Key: $LNMT_API_KEY")
        else
            lnmt_error "No authentication token or API key set. Use lnmt_login first."
            return 1
        fi
    fi
    
    # Request body
    if [[ -n "$data" ]]; then
        curl_opts+=("-d" "$data")
    fi
    
    lnmt_debug "Making $method request to $url"
    
    # Make request and capture response
    local response
    response=$(curl "${curl_opts[@]}" "$url" 2>/dev/null)
    
    # Extract HTTP status code (last 3 characters)
    local http_code="${response: -3}"
    local body="${response%???}"
    
    lnmt_debug "HTTP Status: $http_code"
    
    # Handle HTTP status codes
    case "$http_code" in
        200|201|202)
            if [[ -n "$body" ]]; then
                echo "$body"
            fi
            return 0
            ;;
        204)
            # No content - success
            return 0
            ;;
        400)
            lnmt_error "Bad request (400)"
            if [[ -n "$body" ]]; then
                echo "$body" | jq -r '.message // .error // .' 2>/dev/null || echo "$body"
            fi
            return 1
            ;;
        401)
            lnmt_error "Authentication failed (401)"
            if [[ -n "$body" ]]; then
                echo "$body" | jq -r '.message // .error // .' 2>/dev/null || echo "$body"
            fi
            return 1
            ;;
        404)
            lnmt_error "Resource not found (404)"
            return 1
            ;;
        429)
            lnmt_error "Rate limit exceeded (429)"
            return 1
            ;;
        *)
            lnmt_error "API request failed (HTTP $http_code)"
            if [[ -n "$body" ]]; then
                echo "$body" | jq -r '.message // .error // .' 2>/dev/null || echo "$body"
            fi
            return 1
            ;;
    esac
}

# Configuration functions
lnmt_set_url() {
    local url="$1"
    LNMT_BASE_URL="${url%/}"  # Remove trailing slash
    lnmt_info "Base URL set to: $LNMT_BASE_URL"
}

lnmt_set_api_key() {
    local api_key="$1"
    LNMT_API_KEY="$api_key"
    lnmt_info "API key configured"
}

lnmt_disable_ssl_verification() {
    LNMT_VERIFY_SSL="false"
    lnmt_warn "SSL verification disabled"
}

# Authentication functions
lnmt_login() {
    local base_url="$1"
    local username="$2"
    local password="$3"
    local remember_me="${4:-false}"
    
    LNMT_BASE_URL="${base_url%/}"
    
    local data
    data=$(jq -n \
        --arg username "$username" \
        --arg password "$password" \
        --argjson remember_me "$remember_me" \
        '{username: $username, password: $password, remember_me: $remember_me}')
    
    local response
    response=$(lnmt_request "POST" "/api/v1/auth/login" "$data" "application/json" "false")
    
    if [[ $? -eq 0 ]]; then
        LNMT_TOKEN=$(echo "$response" | jq -r '.token')
        local user_info
        user_info=$(echo "$response" | jq -r '.user.username')
        lnmt_info "Successfully authenticated as: $user_info"
        lnmt_save_config
        return 0
    else
        lnmt_error "Login failed"
        return 1
    fi
}

lnmt_logout() {
    if [[ -n "$LNMT_TOKEN" ]]; then
        lnmt_request "POST" "/api/v1/auth/logout" "" "application/json" "true" >/dev/null 2>&1 || true
        LNMT_TOKEN=""
        lnmt_info "Logged out successfully"
        lnmt_save_config
    fi
}

lnmt_refresh_token() {
    local response
    response=$(lnmt_request "POST" "/api/v1/auth/refresh")
    
    if [[ $? -eq 0 ]]; then
        LNMT_TOKEN=$(echo "$response" | jq -r '.token')
        lnmt_info "Token refreshed successfully"
        lnmt_save_config
        return 0
    else
        lnmt_error "Token refresh failed"
        return 1
    fi
}

lnmt_get_current_user() {
    lnmt_request "GET" "/api/v1/auth/user"
}

# Device management functions
lnmt_get_devices() {
    local status="$1"
    local device_type="$2"
    local vlan="$3"
    local limit="${4:-100}"
    local offset="${5:-0}"
    
    local endpoint="/api/v1/devices?limit=$limit&offset=$offset"
    
    if [[ -n "$status" ]]; then
        endpoint="${endpoint}&status=$status"
    fi
    
    if [[ -n "$device_type" ]]; then
        endpoint="${endpoint}&type=$device_type"
    fi
    
    if [[ -n "$vlan" ]]; then
        endpoint="${endpoint}&vlan=$vlan"
    fi
    
    lnmt_request "GET" "$endpoint"
}

lnmt_get_device() {
    local device_id="$1"
    lnmt_request "GET" "/api/v1/devices/$device_id"
}

lnmt_create_device() {
    local ip_address="$1"
    local hostname="$2"
    local mac_address="$3"
    local device_type="$4"
    local vlan_id="$5"
    
    local data
    data=$(jq -n \
        --arg ip_address "$ip_address" \
        --arg hostname "$hostname" \
        --arg mac_address "$mac_address" \
        --arg device_type "$device_type" \
        --arg vlan_id "$vlan_id" \
        '{ip_address: $ip_address} + 
         (if $hostname != "" then {hostname: $hostname} else {} end) +
         (if $mac_address != "" then {mac_address: $mac_address} else {} end) +
         (if $device_type != "" then {device_type: $device_type} else {} end) +
         (if $vlan_id != "" then {vlan_id: ($vlan_id | tonumber)} else {} end)')
    
    lnmt_request "POST" "/api/v1/devices" "$data"
}

lnmt_update_device() {
    local device_id="$1"
    local hostname="$2"
    local device_type="$3"
    local vlan_id="$4"
    
    local data
    data=$(jq -n \
        --arg hostname "$hostname" \
        --arg device_type "$device_type" \
        --arg vlan_id "$vlan_id" \
        '(if $hostname != "" then {hostname: $hostname} else {} end) +
         (if $device_type != "" then {device_type: $device_type} else {} end) +
         (if $vlan_id != "" then {vlan_id: ($vlan_id | tonumber)} else {} end)')
    
    lnmt_request "PUT" "/api/v1/devices/$device_id" "$data"
}

lnmt_delete_device() {
    local device_id="$1"
    lnmt_request "DELETE" "/api/v1/devices/$device_id"
}

lnmt_start_network_scan() {
    local subnet="$1"
    local aggressive="${2:-false}"
    
    local data
    data=$(jq -n \
        --arg subnet "$subnet" \
        --argjson aggressive "$aggressive" \
        '(if $subnet != "" then {subnet: $subnet} else {} end) +
         {aggressive: $aggressive}')
    
    lnmt_request "POST" "/api/v1/devices/scan" "$data"
}

lnmt_get_scan_status() {
    local scan_id="$1"
    lnmt_request "GET" "/api/v1/devices/scan/$scan_id"
}

# VLAN management functions
lnmt_get_vlans() {
    lnmt_request "GET" "/api/v1/vlans"
}

lnmt_get_vlan() {
    local vlan_id="$1"
    lnmt_request "GET" "/api/v1/vlans/$vlan_id"
}

lnmt_create_vlan() {
    local vlan_id="$1"
    local name="$2"
    local description="$3"
    local subnet="$4"
    local gateway="$5"
    
    local data
    data=$(jq -n \
        --arg vlan_id "$vlan_id" \
        --arg name "$name" \
        --arg description "$description" \
        --arg subnet "$subnet" \
        --arg gateway "$gateway" \
        '{id: ($vlan_id | tonumber), name: $name} +
         (if $description != "" then {description: $description} else {} end) +
         (if $subnet != "" then {subnet: $subnet} else {} end) +
         (if $gateway != "" then {gateway: $gateway} else {} end)')
    
    lnmt_request "POST" "/api/v1/vlans" "$data"
}

lnmt_update_vlan() {
    local vlan_id="$1"
    local name="$2"
    local description="$3"
    local subnet="$4"
    local gateway="$5"
    
    local data
    data=$(jq -n \
        --arg name "$name" \
        --arg description "$description" \
        --arg subnet "$subnet" \
        --arg gateway "$gateway" \
        '(if $name != "" then {name: $name} else {} end) +
         (if $description != "" then {description: $description} else {} end) +
         (if $subnet != "" then {subnet: $subnet} else {} end) +
         (if $gateway != "" then {gateway: $gateway} else {} end)')
    
    lnmt_request "PUT" "/api/v1/vlans/$vlan_id" "$data"
}

lnmt_delete_vlan() {
    local vlan_id="$1"
    lnmt_request "DELETE" "/api/v1/vlans/$vlan_id"
}

# DNS management functions
lnmt_get_dns_zones() {
    lnmt_request "GET" "/api/v1/dns/zones"
}

lnmt_create_dns_zone() {
    local name="$1"
    local zone_type="$2"
    local master_ip="$3"
    
    local data
    data=$(jq -n \
        --arg name "$name" \
        --arg type "$zone_type" \
        --arg master_ip "$master_ip" \
        '{name: $name, type: $type} +
         (if $master_ip != "" then {master_ip: $master_ip} else {} end)')
    
    lnmt_request "POST" "/api/v1/dns/zones" "$data"
}

lnmt_get_dns_records() {
    local zone_name="$1"
    lnmt_request "GET" "/api/v1/dns/zones/$zone_name/records"
}

lnmt_create_dns_record() {
    local zone_name="$1"
    local name="$2"
    local record_type="$3"
    local value="$4"
    local ttl="${5:-3600}"
    local priority="$6"
    
    local data
    data=$(jq -n \
        --arg name "$name" \
        --arg type "$record_type" \
        --arg value "$value" \
        --arg ttl "$ttl" \
        --arg priority "$priority" \
        '{name: $name, type: $type, value: $value, ttl: ($ttl | tonumber)} +
         (if $priority != "" then {priority: ($priority | tonumber)} else {} end)')
    
    lnmt_request "POST" "/api/v1/dns/zones/$zone_name/records" "$data"
}

# Reporting functions
lnmt_get_available_reports() {
    lnmt_request "GET" "/api/v1/reports"
}

lnmt_generate_report() {
    local report_type="$1"
    local format="${2:-json}"
    local period="${3:-24h}"
    
    local endpoint="/api/v1/reports/$report_type?format=$format&period=$period"
    lnmt_request "GET" "$endpoint"
}

# Health monitoring functions
lnmt_get_health_status() {
    lnmt_request "GET" "/api/v1/health" "" "application/json" "false"
}

lnmt_get_system_metrics() {
    lnmt_request "GET" "/api/v1/health/metrics"
}

# Backup/restore functions
lnmt_create_backup() {
    local include_configs="${1:-true}"
    local include_data="${2:-true}"
    local compression="${3:-true}"
    
    local data
    data=$(jq -n \
        --argjson include_configs "$include_configs" \
        --argjson include_data "$include_data" \
        --argjson compression "$compression" \
        '{include_configs: $include_configs, include_data: $include_data, compression: $compression}')
    
    lnmt_request "POST" "/api/v1/backup" "$data"
}

lnmt_get_backups() {
    lnmt_request "GET" "/api/v1/backup"
}

lnmt_restore_backup() {
    local backup_id="$1"
    lnmt_request "POST" "/api/v1/backup/$backup_id/restore"
}

# Scheduler functions
lnmt_get_scheduled_jobs() {
    lnmt_request "GET" "/api/v1/scheduler/jobs"
}

lnmt_create_scheduled_job() {
    local name="$1"
    local job_type="$2"
    local schedule="$3"
    local description="$4"
    local enabled="${5:-true}"
    
    local data
    data=$(jq -n \
        --arg name "$name" \
        --arg type "$job_type" \
        --arg schedule "$schedule" \
        --arg description "$description" \
        --argjson enabled "$enabled" \
        '{name: $name, type: $type, schedule: $schedule, enabled: $enabled} +
         (if $description != "" then {description: $description} else {} end)')
    
    lnmt_request "POST" "/api/v1/scheduler/jobs" "$data"
}

# Utility functions
lnmt_wait_for_scan() {
    local scan_id="$1"
    local timeout="${2:-300}"
    local poll_interval="${3:-5}"
    
    local start_time
    start_time=$(date +%s)
    
    while true; do
        local current_time
        current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [[ $elapsed -gt $timeout ]]; then
            lnmt_error "Scan $scan_id did not complete within $timeout seconds"
            return 1
        fi
        
        local status_response
        status_response=$(lnmt_get_scan_status "$scan_id")
        local status
        status=$(echo "$status_response" | jq -r '.status')
        
        case "$status" in
            "completed")
                lnmt_info "Scan completed successfully"
                echo "$status_response"
                return 0
                ;;
            "failed")
                lnmt_error "Scan failed"
                echo "$status_response"
                return 1
                ;;
            "running"|"started")
                local progress
                progress=$(echo "$status_response" | jq -r '.progress // 0')
                lnmt_info "Scan in progress... ${progress}%"
                sleep "$poll_interval"
                ;;
            *)
                lnmt_warn "Unknown scan status: $status"
                sleep "$poll_interval"
                ;;
        esac
    done
}

# Pretty printing functions
lnmt_pretty_print_devices() {
    local devices_json="$1"
    
    echo "Device Inventory:"
    echo "=================="
    
    echo "$devices_json" | jq -r '.devices[] | 
        "\(.hostname // "N/A") | \(.ip_address) | \(.status) | \(.device_type // "unknown") | VLAN \(.vlan_id // "N/A")"' | \
    while IFS='|' read -r hostname ip status type vlan; do
        # Trim whitespace
        hostname=$(echo "$hostname" | xargs)
        ip=$(echo "$ip" | xargs)
        status=$(echo "$status" | xargs)
        type=$(echo "$type" | xargs)
        vlan=$(echo "$vlan" | xargs)
        
        # Status icon
        case "$status" in
            "online") status_icon="🟢" ;;
            "offline") status_icon="🔴" ;;
            *) status_icon="🟡" ;;
        esac
        
        printf "%-20s %-15s %s %-12s %-10s\n" "$hostname" "$ip" "$status_icon" "$type" "$vlan"
    done
}

lnmt_pretty_print_vlans() {
    local vlans_json="$1"
    
    echo "VLAN Configuration:"
    echo "==================="
    printf "%-6s %-20s %-15s %-8s\n" "ID" "Name" "Subnet" "Devices"
    printf "%-6s %-20s %-15s %-8s\n" "---" "----" "------" "-------"
    
    echo "$vlans_json" | jq -r '.vlans[] | 
        "\(.id) | \(.name) | \(.subnet // "N/A") | \(.device_count // 0)"' | \
    while IFS='|' read -r id name subnet devices; do
        # Trim whitespace
        id=$(echo "$id" | xargs)
        name=$(echo "$name" | xargs)
        subnet=$(echo "$subnet" | xargs)
        devices=$(echo "$devices" | xargs)
        
        printf "%-6s %-20s %-15s %-8s\n" "$id" "$name" "$subnet" "$devices"
    done
}

lnmt_pretty_print_health() {
    local health_json="$1"
    
    local status
    status=$(echo "$health_json" | jq -r '.status')
    local uptime
    uptime=$(echo "$health_json" | jq -r '.uptime')
    local version
    version=$(echo "$health_json" | jq -r '.version')
    
    echo "System Health Status:"
    echo "====================="
    
    case "$status" in
        "healthy") echo -e "Overall Status: ${GREEN}$status${NC}" ;;
        "degraded") echo -e "Overall Status: ${YELLOW}$status${NC}" ;;
        "unhealthy") echo -e "Overall Status: ${RED}$status${NC}" ;;
        *) echo "Overall Status: $status" ;;
    esac
    
    echo "Version: $version"
    echo "Uptime: $uptime seconds"
    
    # Services status
    if echo "$health_json" | jq -e '.services' >/dev/null 2>&1; then
        echo ""
        echo "Services:"
        echo "$health_json" | jq -r '.services | to_entries[] | "\(.key): \(.value.status)"' | \
        while IFS=':' read -r service status; do
            service=$(echo "$service" | xargs)
            status=$(echo "$status" | xargs)
            
            case "$status" in
                "running") echo -e "  $service: ${GREEN}$status${NC}" ;;
                "stopped") echo -e "  $service: ${YELLOW}$status${NC}" ;;
                "error") echo -e "  $service: ${RED}$status${NC}" ;;
                *) echo "  $service: $status" ;;
            esac
        done
    fi
}

# Command-line interface functions
lnmt_show_help() {
    cat << 'EOF'
LNMT Bash API Client

Usage: source lnmt_api.sh

Configuration:
  lnmt_set_url <url>              Set LNMT server URL
  lnmt_set_api_key <key>          Set API key for authentication
  lnmt_disable_ssl_verification   Disable SSL certificate verification

Authentication:
  lnmt_login <url> <user> <pass>  Login to LNMT server
  lnmt_logout                     Logout and clear token
  lnmt_refresh_token              Refresh JWT token
  lnmt_get_current_user           Get current user info

Device Management:
  lnmt_get_devices [status] [type] [vlan] [limit] [offset]
  lnmt_get_device <device_id>
  lnmt_create_device <ip> [hostname] [mac] [type] [vlan]
  lnmt_update_device <device_id> [hostname] [type] [vlan]
  lnmt_delete_device <device_id>
  lnmt_start_network_scan [subnet] [aggressive]
  lnmt_get_scan_status <scan_id>
  lnmt_wait_for_scan <scan_id> [timeout] [poll_interval]

VLAN Management:
  lnmt_get_vlans
  lnmt_get_vlan <vlan_id>
  lnmt_create_vlan <id> <name> [description] [subnet] [gateway]
  lnmt_update_vlan <id> [name] [description] [subnet] [gateway]
  lnmt_delete_vlan <vlan_id>

DNS Management:
  lnmt_get_dns_zones
  lnmt_create_dns_zone <name> <type> [master_ip]
  lnmt_get_dns_records <zone_name>
  lnmt_create_dns_record <zone> <name> <type> <value> [ttl] [priority]

Reports:
  lnmt_get_available_reports
  lnmt_generate_report <type> [format] [period]

Health & Monitoring:
  lnmt_get_health_status
  lnmt_get_system_metrics

Backup & Restore:
  lnmt_create_backup [configs] [data] [compression]
  lnmt_get_backups
  lnmt_restore_backup <backup_id>

Scheduler:
  lnmt_get_scheduled_jobs
  lnmt_create_scheduled_job <name> <type> <schedule> [description] [enabled]

Utilities:
  lnmt_pretty_print_devices <json>
  lnmt_pretty_print_vlans <json>
  lnmt_pretty_print_health <json>

Environment Variables:
  LNMT_BASE_URL     - Server URL
  LNMT_TOKEN        - JWT token
  LNMT_API_KEY      - API key
  LNMT_VERIFY_SSL   - SSL verification (true/false)
  LNMT_DEBUG        - Debug output (true/false)

Examples:
  # Basic usage
  lnmt_login "https://lnmt.local" "admin" "password"
  lnmt_get_devices | lnmt_pretty_print_devices
  lnmt_get_vlans | lnmt_pretty_print_vlans
  lnmt_logout

  # Network scan
  scan_result=$(lnmt_start_network_scan "192.168.1.0/24")
  scan_id=$(echo "$scan_result" | jq -r '.scan_id')
  lnmt_wait_for_scan "$scan_id"

  # Create VLAN
  lnmt_create_vlan 100 "Guest Network" "Guest access" "192.168.100.0/24" "192.168.100.1"

EOF
}

# Command-line wrapper functions for easier usage
lnmt_cli() {
    local command="$1"
    shift
    
    case "$command" in
        "help"|"-h"|"--help")
            lnmt_show_help
            ;;
        "login")
            lnmt_login "$@"
            ;;
        "logout")
            lnmt_logout
            ;;
        "devices")
            local devices_json
            devices_json=$(lnmt_get_devices "$@")
            if [[ $? -eq 0 ]]; then
                lnmt_pretty_print_devices "$devices_json"
            fi
            ;;
        "vlans")
            local vlans_json
            vlans_json=$(lnmt_get_vlans)
            if [[ $? -eq 0 ]]; then
                lnmt_pretty_print_vlans "$vlans_json"
            fi
            ;;
        "health")
            local health_json
            health_json=$(lnmt_get_health_status)
            if [[ $? -eq 0 ]]; then
                lnmt_pretty_print_health "$health_json"
            fi
            ;;
        "scan")
            local subnet="$1"
            local scan_result
            scan_result=$(lnmt_start_network_scan "$subnet")
            if [[ $? -eq 0 ]]; then
                local scan_id
                scan_id=$(echo "$scan_result" | jq -r '.scan_id')
                lnmt_info "Started scan with ID: $scan_id"
                lnmt_wait_for_scan "$scan_id"
            fi
            ;;
        *)
            lnmt_error "Unknown command: $command"
            lnmt_show_help
            return 1
            ;;
    esac
}

# Initialize - load config if available
lnmt_load_config

# If script is executed directly (not sourced), run CLI
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ $# -eq 0 ]]; then
        lnmt_show_help
    else
        lnmt_cli "$@"
    fi
fi