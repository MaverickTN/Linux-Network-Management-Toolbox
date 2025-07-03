#!/bin/bash

# ============================================================================
# LNMT Demo Scenario 4: VLAN Management
# ============================================================================

cat > "/opt/lnmt/demo/scenarios/04_vlan_management.sh" << 'SCENARIO4'
#!/bin/bash
# Demo Scenario 4: VLAN Management and Network Segmentation

echo "🌐 Demo Scenario 4: VLAN Management"
echo "This scenario demonstrates network segmentation using VLANs"
echo ""

echo "Step 1: Viewing current VLAN configuration..."
lnmt vlan list --detailed

echo -e "\nStep 2: Creating a new VLAN for guest access..."
lnmt vlan create \
    --id 150 \
    --name "Guest-WiFi" \
    --network "10.150.0.0/24" \
    --description "Isolated guest wireless network" \
    --dhcp-enabled \
    --dhcp-start "10.150.0.10" \
    --dhcp-end "10.150.0.100"

echo -e "\nStep 3: Configuring VLAN access controls..."
lnmt vlan acl add \
    --vlan 150 \
    --rule "deny any to 192.168.0.0/16" \
    --description "Block guest access to internal networks"

echo -e "\nStep 4: Assigning devices to appropriate VLANs..."
lnmt device assign-vlan --hostname "ws-001" --vlan 100  # Workstation VLAN
lnmt device assign-vlan --hostname "srv-001" --vlan 110  # Server VLAN

echo -e "\nStep 5: Monitoring VLAN traffic and utilization..."
lnmt vlan stats --id 150
lnmt vlan monitor --id 150 --duration 30

echo -e "\nStep 6: Testing inter-VLAN connectivity..."
lnmt network test-connectivity \
    --source-vlan 100 \
    --target-vlan 110 \
    --protocol icmp

echo "✅ VLAN management demo completed!"
echo "📊 Review VLAN dashboard at: http://localhost:8080/vlans"
SCENARIO4

# ============================================================================
# LNMT Demo Scenario 5: Reporting and Analytics
# ============================================================================

cat > "/opt/lnmt/demo/scenarios/05_reporting_analytics.sh" << 'SCENARIO5'
#!/bin/bash
# Demo Scenario 5: Reporting and Analytics

echo "📊 Demo Scenario 5: Reporting and Analytics"
echo "This scenario demonstrates report generation and data analytics"
echo ""

echo "Step 1: Generating device inventory report..."
lnmt report generate \
    --type "device-inventory" \
    --format pdf \
    --output "/tmp/device_inventory_$(date +%Y%m%d).pdf" \
    --include-charts

echo -e "\nStep 2: Creating security compliance report..."
lnmt report generate \
    --type "security-compliance" \
    --timeframe "last-30-days" \
    --format html \
    --output "/tmp/security_compliance.html"

echo -e "\nStep 3: Network performance analytics..."
lnmt analytics performance \
    --metric "network-utilization" \
    --timeframe "last-7-days" \
    --group-by device-type

echo -e "\nStep 4: Alert trend analysis..."
lnmt analytics alerts \
    --trend-analysis \
    --timeframe "last-month" \
    --breakdown severity,type

echo -e "\nStep 5: Custom dashboard creation..."
lnmt dashboard create \
    --name "Executive Summary" \
    --widgets "device-status,alert-summary,network-health,compliance-score" \
    --refresh-interval 300

echo -e "\nStep 6: Scheduling automated reports..."
lnmt schedule report \
    --name "Weekly Network Report" \
    --type "comprehensive" \
    --schedule "0 9 * * 1" \
    --email "admin@company.com" \
    --format pdf

echo -e "\nStep 7: Exporting data for external analysis..."
lnmt export data \
    --type "device-metrics" \
    --format csv \
    --timeframe "last-30-days" \
    --output "/tmp/device_metrics_export.csv"

echo "✅ Reporting and analytics demo completed!"
echo "📈 Access reports at: http://localhost:8080/reports"
echo "📊 View analytics at: http://localhost:8080/analytics"
SCENARIO5

# ============================================================================
# Health Check Script
# ============================================================================

cat > "/opt/lnmt/demo/scripts/health_check.sh" << 'HEALTHCHECK'
#!/bin/bash
# LNMT Demo Environment Health Check

echo "🏥 LNMT Demo Environment Health Check"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local service=$1
    local description=$2
    
    if systemctl is-active --quiet "$service"; then
        echo -e "${GREEN}✅ $description: RUNNING${NC}"
        return 0
    else
        echo -e "${RED}❌ $description: STOPPED${NC}"
        return 1
    fi
}

check_port() {
    local port=$1
    local description=$2
    
    if netstat -tuln | grep -q ":$port "; then
        echo -e "${GREEN}✅ $description (port $port): LISTENING${NC}"
        return 0
    else
        echo -e "${RED}❌ $description (port $port): NOT LISTENING${NC}"
        return 1
    fi
}

check_file() {
    local file=$1
    local description=$2
    
    if [[ -f "$file" ]]; then
        echo -e "${GREEN}✅ $description: EXISTS${NC}"
        return 0
    else
        echo -e "${RED}❌ $description: MISSING${NC}"
        return 1
    fi
}

check_database() {
    local db_type=$1
    
    case $db_type in
        "postgresql")
            if sudo -u postgres psql -c '\l' &>/dev/null; then
                echo -e "${GREEN}✅ PostgreSQL Database: ACCESSIBLE${NC}"
                return 0
            else
                echo -e "${RED}❌ PostgreSQL Database: INACCESSIBLE${NC}"
                return 1
            fi
            ;;
        "mysql")
            if mysql -e "SHOW DATABASES;" &>/dev/null; then
                echo -e "${GREEN}✅ MySQL Database: ACCESSIBLE${NC}"
                return 0
            else
                echo -e "${RED}❌ MySQL Database: INACCESSIBLE${NC}"
                return 1
            fi
            ;;
    esac
}

# Main health checks
echo -e "\n🔧 System Services:"
check_service "lnmt" "LNMT Main Service"
check_service "lnmt-web" "LNMT Web Interface"
check_service "lnmt-scheduler" "LNMT Scheduler"
check_service "lnmt-monitor" "LNMT Health Monitor"

echo -e "\n🌐 Network Services:"
check_port 8080 "Web Interface"
check_port 5432 "PostgreSQL" || check_port 3306 "MySQL"
check_port 53 "DNS Service"

echo -e "\n📁 Demo Files:"
check_file "/opt/lnmt/demo/lnmt_demo_data.json" "Demo Data"
check_file "/opt/lnmt/demo/DEMO_GUIDE.md" "Demo Guide"
check_file "/opt/lnmt/demo/scenarios/01_device_onboarding.sh" "Demo Scenarios"

echo -e "\n🗄️ Database Connectivity:"
check_database "postgresql" || check_database "mysql"

echo -e "\n💾 Disk Space:"
df -h /opt/lnmt | tail -1 | awk '{
    if ($5+0 > 90) 
        printf "\033[0;31m❌ Disk Usage: %s (CRITICAL)\033[0m\n", $5
    else if ($5+0 > 80) 
        printf "\033[1;33m⚠️ Disk Usage: %s (WARNING)\033[0m\n", $5
    else 
        printf "\033[0;32m✅ Disk Usage: %s (OK)\033[0m\n", $5
}'

echo -e "\n🧠 Memory Usage:"
free -h | awk 'NR==2{
    used_pct = $3/$2 * 100
    if (used_pct > 90) 
        printf "\033[0;31m❌ Memory Usage: %.1f%% (CRITICAL)\033[0m\n", used_pct
    else if (used_pct > 80) 
        printf "\033[1;33m⚠️ Memory Usage: %.1f%% (WARNING)\033[0m\n", used_pct
    else 
        printf "\033[0;32m✅ Memory Usage: %.1f%% (OK)\033[0m\n", used_pct
}'

echo -e "\n📊 Demo Statistics:"
echo "Device Count: $(lnmt device count 2>/dev/null || echo 'N/A')"
echo "Active Alerts: $(lnmt alert count --active 2>/dev/null || echo 'N/A')"
echo "VLAN Count: $(lnmt vlan count 2>/dev/null || echo 'N/A')"
echo "User Count: $(lnmt user count 2>/dev/null || echo 'N/A')"

echo -e "\n🔍 Recent Logs:"
echo "Last 5 log entries:"
tail -5 /var/log/lnmt/lnmt.log 2>/dev/null || echo "Log file not accessible"

echo -e "\n⏱️ Health check completed at $(date)"
HEALTHCHECK

# ============================================================================
# Performance Test Script
# ============================================================================

cat > "/opt/lnmt/demo/scripts/performance_test.sh" << 'PERFTEST'
#!/bin/bash
# LNMT Performance Test Script

USERS=${1:-10}
DURATION=${2:-60}
BASE_URL="http://localhost:8080"

echo "🚀 LNMT Performance Test"
echo "======================="
echo "Users: $USERS"
echo "Duration: ${DURATION}s"
echo "Target: $BASE_URL"
echo ""

# Check if curl and ab are available
if ! command -v curl &> /dev/null; then
    echo "❌ curl not found. Please install curl."
    exit 1
fi

if ! command -v ab &> /dev/null; then
    echo "❌ Apache Bench (ab) not found. Please install apache2-utils."
    exit 1
fi

# Test 1: Basic connectivity
echo "🔍 Test 1: Basic Connectivity"
if curl -s "$BASE_URL" > /dev/null; then
    echo "✅ Web interface accessible"
else
    echo "❌ Web interface not accessible"
    exit 1
fi

# Test 2: Login performance
echo -e "\n🔐 Test 2: Login Performance"
LOGIN_TIME=$(curl -w "%{time_total}" -s -o /dev/null \
    -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"viewer.demo","password":"DemoView123!"}')
echo "Login response time: ${LOGIN_TIME}s"

# Test 3: API endpoint performance
echo -e "\n📊 Test 3: API Performance"
endpoints=(
    "/api/devices"
    "/api/alerts"
    "/api/vlans"
    "/api/health/status"
)

for endpoint in "${endpoints[@]}"; do
    response_time=$(curl -w "%{time_total}" -s -o /dev/null "$BASE_URL$endpoint")
    echo "$endpoint: ${response_time}s"
done

# Test 4: Concurrent load test
echo -e "\n⚡ Test 4: Concurrent Load Test"
echo "Running Apache Bench test..."

ab -n $((USERS * 10)) -c $USERS -t $DURATION "$BASE_URL/" > /tmp/ab_results.txt 2>&1

if [[ $? -eq 0 ]]; then
    echo "✅ Load test completed"
    echo "Results summary:"
    grep -E "(Requests per second|Time per request|Transfer rate)" /tmp/ab_results.txt
else
    echo "❌ Load test failed"
fi

# Test 5: Database performance
echo -e "\n🗄️ Test 5: Database Performance"
DB_TEST_START=$(date +%s.%N)
lnmt device list > /dev/null 2>&1
DB_TEST_END=$(date +%s.%N)
DB_TIME=$(echo "$DB_TEST_END - $DB_TEST_START" | bc -l)
echo "Device list query time: ${DB_TIME}s"

# Test 6: Memory usage during load
echo -e "\n🧠 Test 6: Memory Usage"
echo "Memory usage before load:"
free -h | grep Mem

echo -e "\nGenerating load for 30 seconds..."
for i in {1..30}; do
    curl -s "$BASE_URL/api/devices" > /dev/null &
    curl -s "$BASE_URL/api/alerts" > /dev/null &
    sleep 1
done
wait

echo "Memory usage after load:"
free -h | grep Mem

echo -e "\n📈 Performance test completed at $(date)"
echo "Detailed results saved to /tmp/ab_results.txt"
PERFTEST

# ============================================================================
# Reset Demo Script
# ============================================================================

cat > "/opt/lnmt/demo/reset_demo.sh" << 'RESETDEMO'
#!/bin/bash
# LNMT Demo Environment Reset Script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

RESET_TYPE=${1:-"--interactive"}

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    LNMT Demo Reset                           ║"
    echo "║          Reset demo environment to fresh state              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

confirm_reset() {
    if [[ "$RESET_TYPE" == "--interactive" ]]; then
        echo -e "${YELLOW}⚠️ This will remove all demo data and reset the environment.${NC}"
        echo -e "${YELLOW}   Are you sure you want to continue? (yes/no)${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy][Ee][Ss]$ ]]; then
            echo "Reset cancelled."
            exit 0
        fi
    fi
}

reset_database() {
    echo -e "\n${BLUE}🗄️ Resetting database...${NC}"
    
    # Stop services
    systemctl stop lnmt-web lnmt-scheduler lnmt-monitor || true
    
    # Clear demo data
    lnmt database reset --demo-data-only --confirm || true
    
    echo -e "${GREEN}✅ Database reset completed${NC}"
}

reset_files() {
    echo -e "\n${BLUE}📁 Cleaning demo files...${NC}"
    
    # Remove generated files
    rm -f /opt/lnmt/demo/lnmt_demo_data.json
    rm -f /opt/lnmt/demo/data/*.csv
    rm -f /tmp/lnmt_demo_*
    rm -f /tmp/ab_results.txt
    
    # Clean logs
    > /var/log/lnmt/demo_setup.log
    
    echo -e "${GREEN}✅ Files cleaned${NC}"
}

reset_config() {
    echo -e "\n${BLUE}⚙️ Resetting configuration...${NC}"
    
    # Reset web dashboard
    lnmt web dashboard reset --confirm || true
    
    # Remove demo users (keep admin.demo for access)
    lnmt user delete --username "operator.demo" --force || true
    lnmt user delete --username "viewer.demo" --force || true
    
    # Clear scheduled jobs
    lnmt schedule job clear --demo-jobs || true
    
    echo -e "${GREEN}✅ Configuration reset${NC}"
}

restart_services() {
    echo -e "\n${BLUE}🔄 Restarting services...${NC}"
    
    systemctl start lnmt-web lnmt-scheduler lnmt-monitor
    systemctl status lnmt --no-pager
    
    echo -e "${GREEN}✅ Services restarted${NC}"
}

run_fresh_setup() {
    if [[ "$RESET_TYPE" == "--full" ]] || [[ "$RESET_TYPE" == "--interactive" ]]; then
        echo -e "\n${BLUE}🚀 Running fresh demo setup...${NC}"
        
        cd /opt/lnmt/demo
        ./setup_demo.sh
        
        echo -e "${GREEN}✅ Fresh demo environment ready${NC}"
    fi
}

main() {
    print_header
    confirm_reset
    
    case "$RESET_TYPE" in
        "--full")
            echo "Performing full reset..."
            reset_database
            reset_files
            reset_config
            restart_services
            run_fresh_setup
            ;;
        "--partial")
            echo "Performing partial reset (keeping users)..."
            reset_database
            reset_files
            restart_services
            run_fresh_setup
            ;;
        "--interactive")
            echo "Interactive reset mode..."
            reset_database
            reset_files
            reset_config
            restart_services
            run_fresh_setup
            ;;
        *)
            echo "Usage: $0 [--full|--partial|--interactive]"
            echo "  --full: Complete reset including all users and config"
            echo "  --partial: Reset data but keep user accounts"
            echo "  --interactive: Prompt for confirmation (default)"
            exit 1
            ;;
    esac
    
    echo -e "\n${GREEN}🎉 Demo environment reset completed!${NC}"
    echo -e "${BLUE}📱 Access: http://localhost:8080${NC}"
    echo -e "${BLUE}👤 Login: admin.demo / DemoAdmin123!${NC}"
}

main "$@"
RESETDEMO

# ============================================================================
# Cleanup Script
# ============================================================================

cat > "/opt/lnmt/demo/scripts/cleanup.sh" << 'CLEANUP'
#!/bin/bash
# LNMT Demo Cleanup Script - Remove temporary files and logs

echo "🧹 LNMT Demo Cleanup"
echo "==================="

# Clean temporary files
echo "Removing temporary files..."
rm -f /tmp/lnmt_demo_*
rm -f /tmp/ab_results.txt
rm -f /tmp/policy_*.json
rm -f /tmp/device_inventory_*.pdf
rm -f /tmp/security_compliance.html
rm -f /tmp/device_metrics_export.csv

# Rotate logs
echo "Rotating log files..."
if [[ -f /var/log/lnmt/demo_setup.log ]]; then
    mv /var/log/lnmt/demo_setup.log /var/log/lnmt/demo_setup.log.old
    touch /var/log/lnmt/demo_setup.log
fi

# Clean old backup files
echo "Cleaning old backup files..."
find /opt/lnmt/backups -name "demo_backup_*" -mtime +7 -delete 2>/dev/null || true

# Clear cache
echo "Clearing application cache..."
rm -rf /var/cache/lnmt/demo/* 2>/dev/null || true

echo "✅ Cleanup completed"
CLEANUP

# Make all scripts executable
chmod +x /opt/lnmt/demo/scenarios/*.sh
chmod +x /opt/lnmt/demo/scripts/*.sh
chmod +x /opt/lnmt/demo/reset_demo.sh

echo "✅ Demo scenarios and utility scripts created successfully!"