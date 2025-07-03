#!/bin/bash
# LNMT Bash API Usage Examples
#
# This script demonstrates various ways to use the LNMT Bash API client
# for common network management tasks.

set -euo pipefail

# Source the LNMT API client
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lnmt_api.sh"

# Configuration
LNMT_SERVER="${LNMT_SERVER:-https://api.lnmt.local}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-your_password}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

example_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

example_basic_usage() {
    example_header "Basic Usage Example"
    
    # Login
    echo "Logging in to $LNMT_SERVER..."
    if lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"; then
        echo -e "${GREEN}✓ Login successful${NC}"
        
        # Get system health
        echo "Getting system health..."
        health_json=$(lnmt_get_health_status)
        lnmt_pretty_print_health "$health_json"
        
        # Get current user
        echo -e "\nGetting current user info..."
        user_json=$(lnmt_get_current_user)
        username=$(echo "$user_json" | jq -r '.username')
        role=$(echo "$user_json" | jq -r '.role')
        echo "Logged in as: $username ($role)"
        
        # Logout
        lnmt_logout
    else
        echo "Login failed"
        return 1
    fi
}

example_device_management() {
    example_header "Device Management Examples"
    
    lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"
    
    # List all devices with pretty printing
    echo "Device inventory:"
    devices_json=$(lnmt_get_devices)
    lnmt_pretty_print_devices "$devices_json"
    
    # Get device counts by status
    echo -e "\nDevice status summary:"
    total=$(echo "$devices_json" | jq '.total')
    online=$(echo "$devices_json" | jq '[.devices[] | select(.status == "online")] | length')
    offline=$(echo "$devices_json" | jq '[.devices[] | select(.status == "offline")] | length')
    unknown=$(echo "$devices_json" | jq '[.devices[] | select(.status == "unknown")] | length')
    
    echo "  Total: $total"
    echo "  Online: $online"
    echo "  Offline: $offline"
    echo "  Unknown: $unknown"
    
    # Filter devices by type
    echo -e "\nServers only:"
    servers_json=$(lnmt_get_devices "" "server")
    server_count=$(echo "$servers_json" | jq '.devices | length')
    echo "Found $server_count servers"
    
    # Create a test device
    echo -e "\nCreating test device..."
    if new_device=$(lnmt_create_device "192.168.1.200" "test-bash-device" "" "workstation"); then
        device_id=$(echo "$new_device" | jq -r '.id')
        echo "Created device with ID: $device_id"
        
        # Update the device
        echo "Updating device..."
        lnmt_update_device "$device_id" "updated-bash-device" "server"
        echo "Device updated"
        
        # Delete the test device
        echo "Deleting test device..."
        lnmt_delete_device "$device_id"
        echo "Test device deleted"
    fi
    
    lnmt_logout
}

example_network_scanning() {
    example_header "Network Scanning Example"
    
    lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"
    
    # Start network scan
    echo "Starting network scan for 192.168.1.0/24..."
    scan_result=$(lnmt_start_network_scan "192.168.1.0/24" "false")
    scan_id=$(echo "$scan_result" | jq -r '.scan_id')
    
    echo "Scan started with ID: $scan_id"
    
    # Wait for scan completion
    echo "Waiting for scan to complete..."
    if lnmt_wait_for_scan "$scan_id" 120 5; then
        echo -e "${GREEN}✓ Scan completed successfully${NC}"
        
        # Show updated device count
        devices_json=$(lnmt_get_devices)
        total=$(echo "$devices_json" | jq '.total')
        echo "Total devices after scan: $total"
    else
        echo "Scan failed or timed out"
    fi
    
    lnmt_logout
}

example_vlan_management() {
    example_header "VLAN Management Examples"
    
    lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"
    
    # List VLANs with pretty printing
    echo "Current VLAN configuration:"
    vlans_json=$(lnmt_get_vlans)
    lnmt_pretty_print_vlans "$vlans_json"
    
    # Create a test VLAN
    echo -e "\nCreating test VLAN..."
    if lnmt_create_vlan 999 "Test VLAN" "Test VLAN for bash examples" "192.168.99.0/24" "192.168.99.1"; then
        echo "Test VLAN created successfully"
        
        # Update VLAN description
        echo "Updating VLAN description..."
        lnmt_update_vlan 999 "" "Updated test VLAN description"
        echo "VLAN updated"
        
        # Show updated VLAN
        vlan_info=$(lnmt_get_vlan 999)
        echo "VLAN 999 info:"
        echo "$vlan_info" | jq '.'
        
        # Delete the test VLAN
        echo "Deleting test VLAN..."
        lnmt_delete_vlan 999
        echo "Test VLAN deleted"
    fi
    
    lnmt_logout
}

example_dns_management() {
    example_header "DNS Management Examples"
    
    lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"
    
    # List DNS zones
    echo "DNS zones:"
    zones_json=$(lnmt_get_dns_zones)
    echo "$zones_json" | jq -r '.zones[] | "  \(.name) (\(.type)) - \(.record_count) records"'
    
    # Create test DNS zone
    echo -e "\nCreating test DNS zone..."
    if lnmt_create_dns_zone "bashtest.local" "master"; then
        echo "DNS zone created"
        
        # Add DNS records
        echo "Adding A record..."
        lnmt_create_dns_record "bashtest.local" "www" "A" "192.168.1.10"
        
        echo "Adding CNAME record..."
        lnmt_create_dns_record "bashtest.local" "mail" "CNAME" "www.bashtest.local"
        
        # List records
        echo "DNS records in bashtest.local:"
        records_json=$(lnmt_get_dns_records "bashtest.local")
        echo "$records_json" | jq -r '.records[] | "  \(.name) \(.type) \(.value)"'
    fi
    
    lnmt_logout
}

example_reporting() {
    example_header "Reporting Examples"
    
    lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"
    
    # List available reports
    echo "Available reports:"
    reports_json=$(lnmt_get_available_reports)
    echo "$reports_json" | jq -r '.reports[] | "  \(.type): \(.name)"'
    
    # Generate network summary report
    echo -e "\nGenerating network summary report..."
    if network_report=$(lnmt_generate_report "network_summary" "json" "24h"); then
        echo "Network Summary Report (24h):"
        echo "$network_report" | jq '.'
    fi
    
    # Generate CSV device report
    echo -e "\nGenerating device status CSV report..."
    if csv_report=$(lnmt_generate_report "device_status" "csv" "7d"); then
        echo "Device Status CSV (first 5 lines):"
        echo "$csv_report" | head -5
        
        # Save to file
        echo "$csv_report" > "device_status_report.csv"
        echo "Report saved to device_status_report.csv"
    fi
    
    lnmt_logout
}

example_backup_operations() {
    example_header "Backup Operations Examples"
    
    lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"
    
    # List existing backups
    echo "Available backups:"
    backups_json=$(lnmt_get_backups)
    echo "$backups_json" | jq -r '.backups[] | "  \(.filename) (\(.size) bytes) - \(.created_at)"'
    
    # Create a new backup
    echo -e "\nCreating system backup..."
    if backup_job=$(lnmt_create_backup "true" "true" "true"); then
        job_id=$(echo "$backup_job" | jq -r '.job_id')
        echo "Backup job started: $job_id"
        echo "Note: Backup will run in background. Check status later."
    fi
    
    lnmt_logout
}

example_scheduler() {
    example_header "Scheduler Examples"
    
    lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"
    
    # List scheduled jobs
    echo "Scheduled jobs:"
    jobs_json=$(lnmt_get_scheduled_jobs)
    echo "$jobs_json" | jq -r '.jobs[] | "  \(.name) (\(.type)) - \(.schedule) - Enabled: \(.enabled)"'
    
    # Create a scheduled scan job
    echo -e "\nCreating scheduled scan job..."
    if lnmt_create_scheduled_job "Weekly Network Scan" "scan" "0 1 * * 0" "Weekly network discovery scan"; then
        echo "Scheduled job created successfully"
    fi
    
    lnmt_logout
}

example_monitoring_dashboard() {
    example_header "Monitoring Dashboard Example"
    
    lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"
    
    # Collect data for dashboard
    health_json=$(lnmt_get_health_status)
    metrics_json=$(lnmt_get_system_metrics)
    devices_json=$(lnmt_get_devices)
    vlans_json=$(lnmt_get_vlans)
    
    # Extract key metrics
    system_status=$(echo "$health_json" | jq -r '.status')
    uptime=$(echo "$health_json" | jq -r '.uptime')
    cpu_usage=$(echo "$metrics_json" | jq -r '.cpu_usage')
    memory_usage=$(echo "$metrics_json" | jq -r '.memory_usage')
    disk_usage=$(echo "$metrics_json" | jq -r '.disk_usage')
    
    total_devices=$(echo "$devices_json" | jq '.total')
    online_devices=$(echo "$devices_json" | jq '[.devices[] | select(.status == "online")] | length')
    offline_devices=$((total_devices - online_devices))
    
    vlan_count=$(echo "$vlans_json" | jq '.vlans | length')
    
    # Display dashboard
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│                    LNMT Dashboard                           │"
    echo "├─────────────────────────────────────────────────────────────┤"
    printf "│ System Status: %42s │\n" "$system_status"
    printf "│ Uptime: %48s seconds │\n" "$uptime"
    echo "├─────────────────────────────────────────────────────────────┤"
    printf "│ CPU Usage: %46s%% │\n" "$cpu_usage"
    printf "│ Memory Usage: %43s%% │\n" "$memory_usage"
    printf "│ Disk Usage: %45s%% │\n" "$disk_usage"
    echo "├─────────────────────────────────────────────────────────────┤"
    printf "│ Total Devices: %44s │\n" "$total_devices"
    printf "│ Online: %49s │\n" "$online_devices"
    printf "│ Offline: %48s │\n" "$offline_devices"
    echo "├─────────────────────────────────────────────────────────────┤"
    printf "│ VLANs Configured: %40s │\n" "$vlan_count"
    echo "└─────────────────────────────────────────────────────────────┘"
    
    lnmt_logout
}

example_bulk_operations() {
    example_header "Bulk Operations Examples"
    
    lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"
    
    # Bulk device tagging
    echo "Adding 'managed' tag to all servers..."
    devices_json=$(lnmt_get_devices "" "server")
    server_count=0
    
    echo "$devices_json" | jq -r '.devices[] | @base64' | while read -r device_data; do
        device=$(echo "$device_data" | base64 --decode)
        device_id=$(echo "$device" | jq -r '.id')
        hostname=$(echo "$device" | jq -r '.hostname')
        
        echo "  Updating $hostname..."
        # Note: In real implementation, you'd check existing tags first
        # This is a simplified example
        server_count=$((server_count + 1))
    done
    
    echo "Processed servers for tagging"
    
    # Bulk VLAN assignment based on IP ranges
    echo -e "\nAssigning VLANs based on IP ranges..."
    all_devices_json=$(lnmt_get_devices)
    assignment_count=0
    
    echo "$all_devices_json" | jq -r '.devices[] | @base64' | while read -r device_data; do
        device=$(echo "$device_data" | base64 --decode)
        device_id=$(echo "$device" | jq -r '.id')
        ip_address=$(echo "$device" | jq -r '.ip_address')
        current_vlan=$(echo "$device" | jq -r '.vlan_id // empty')
        
        # Determine target VLAN based on IP
        target_vlan=""
        if [[ "$ip_address" =~ ^192\.168\.10\. ]]; then
            target_vlan="10"
        elif [[ "$ip_address" =~ ^192\.168\.20\. ]]; then
            target_vlan="20"
        fi
        
        # Update if different
        if [[ -n "$target_vlan" && "$current_vlan" != "$target_vlan" ]]; then
            echo "  Assigning $ip_address to VLAN $target_vlan"
            assignment_count=$((assignment_count + 1))
            # lnmt_update_device "$device_id" "" "" "$target_vlan"
        fi
    done
    
    echo "Processed devices for VLAN assignment"
    
    lnmt_logout
}

example_error_handling() {
    example_header "Error Handling Examples"
    
    # Test authentication error
    echo "Testing authentication error..."
    if ! lnmt_login "$LNMT_SERVER" "wrong_user" "wrong_pass" 2>/dev/null; then
        echo -e "${GREEN}✓ Authentication error handled correctly${NC}"
    fi
    
    # Test with valid login for other error types
    lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"
    
    # Test not found error
    echo "Testing not found error..."
    if ! lnmt_get_device "non-existent-id" 2>/dev/null; then
        echo -e "${GREEN}✓ Not found error handled correctly${NC}"
    fi
    
    # Test invalid VLAN creation
    echo "Testing invalid VLAN creation..."
    if ! lnmt_create_vlan "5000" "Invalid VLAN" 2>/dev/null; then
        echo -e "${GREEN}✓ Invalid VLAN error handled correctly${NC}"
    fi
    
    lnmt_logout
}

# CLI wrapper for running individual examples
run_example() {
    local example_name="$1"
    
    case "$example_name" in
        "basic"|"1")
            example_basic_usage
            ;;
        "devices"|"2")
            example_device_management
            ;;
        "scan"|"3")
            example_network_scanning
            ;;
        "vlans"|"4")
            example_vlan_management
            ;;
        "dns"|"5")
            example_dns_management
            ;;
        "reports"|"6")
            example_reporting
            ;;
        "backup"|"7")
            example_backup_operations
            ;;
        "scheduler"|"8")
            example_scheduler
            ;;
        "dashboard"|"9")
            example_monitoring_dashboard
            ;;
        "bulk"|"10")
            example_bulk_operations
            ;;
        "errors"|"11")
            example_error_handling
            ;;
        "all")
            echo "Running all examples..."
            example_basic_usage
            example_device_management
            example_network_scanning
            example_vlan_management
            example_dns_management
            example_reporting
            example_backup_operations
            example_scheduler
            example_monitoring_dashboard
            example_bulk_operations
            example_error_handling
            ;;
        *)
            echo "Unknown example: $example_name"
            show_help
            exit 1
            ;;
    esac
}

show_help() {
    cat << 'EOF'
LNMT Bash API Examples

Usage: ./api_examples.sh [options] [example]

Options:
  -h, --help              Show this help
  -s, --server URL        Set LNMT server URL
  -u, --user USERNAME     Set username
  -p, --pass PASSWORD     Set password

Examples:
  basic, 1               Basic API usage
  devices, 2             Device management
  scan, 3                Network scanning
  vlans, 4               VLAN management
  dns, 5                 DNS management
  reports, 6             Reporting
  backup, 7              Backup operations
  scheduler, 8           Job scheduling
  dashboard, 9           Monitoring dashboard
  bulk, 10               Bulk operations
  errors, 11             Error handling
  all                    Run all examples

Environment Variables:
  LNMT_SERVER            LNMT server URL
  USERNAME               Username for authentication
  PASSWORD               Password for authentication

Examples:
  ./api_examples.sh basic
  ./api_examples.sh -s https://lnmt.example.com devices
  LNMT_SERVER=https://lnmt.local ./api_examples.sh all

EOF
}

# Main script logic
main() {
    local example_to_run="all"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--server)
                LNMT_SERVER="$2"
                shift 2
                ;;
            -u|--user)
                USERNAME="$2"
                shift 2
                ;;
            -p|--pass)
                PASSWORD="$2"
                shift 2
                ;;
            -*)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                example_to_run="$1"
                shift
                ;;
        esac
    done
    
    # Validate configuration
    if [[ -z "$LNMT_SERVER" || -z "$USERNAME" || -z "$PASSWORD" ]]; then
        echo "Error: LNMT_SERVER, USERNAME, and PASSWORD must be set"
        echo "Use command line options or environment variables"
        show_help
        exit 1
    fi
    
    # Enable debug mode if requested
    if [[ "${LNMT_DEBUG:-false}" == "true" ]]; then
        echo "Debug mode enabled"
        echo "Server: $LNMT_SERVER"
        echo "Username: $USERNAME"
    fi
    
    echo "LNMT Bash API Examples"
    echo "======================"
    echo "Server: $LNMT_SERVER"
    echo "User: $USERNAME"
    echo ""
    
    # Run the requested example
    run_example "$example_to_run"
    
    echo ""
    echo -e "${GREEN}Examples completed!${NC}"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi