# LNMT Report Engine 📊

A comprehensive reporting engine for analyzing bandwidth, application usage, and session data across VLANs, hosts, and devices in the LNMT (Local Network Management Tool) ecosystem.

## Features

- **📈 Comprehensive Analytics**: Bandwidth usage, session analysis, and application classification
- **🏢 Multi-Level Reporting**: Per-VLAN, per-device, and network-wide statistics
- **🔍 DNS Classification**: Intelligent application categorization based on hostname patterns
- **⚡ Multiple Export Formats**: JSON, text, and HTML output options
- **🚫 Smart Filtering**: DNS whitelist to exclude OS updates and telemetry traffic
- **⏰ Time-Based Analysis**: 24-hour, 14-day rolling, and custom time periods
- **🖥️ CLI Interface**: Easy command-line access to all reporting features
- **🔌 API Ready**: Programmatic access for integration with web UIs and dashboards

## Quick Start

### Installation

```bash
# Clone or download the LNMT report engine files
git clone <repository-url>
cd lnmt-report-engine

# Ensure Python 3.8+ is installed
python3 --version

# Install dependencies (if any additional packages are needed)
pip3 install -r requirements.txt  # Create this file if needed
```

### Basic Usage

#### 1. Command Line Interface

```bash
# Generate a comprehensive 24-hour report
python3 cli/reportctl.py generate --period 24 --format text

# Export detailed JSON report
python3 cli/reportctl.py generate --period 24 --format json --output daily_report.json

# Show top devices for the last week
python3 cli/reportctl.py devices --period 168 --limit 10 --details

# Analyze VLAN usage
python3 cli/reportctl.py vlans --period 24

# Application usage breakdown
python3 cli/reportctl.py apps --period 24 --show-classification
```

#### 2. Python API

```python
from services.report_engine import ReportEngine
from datetime import datetime, timedelta

# Initialize the report engine
with ReportEngine("network.db") as engine:
    # Generate comprehensive report
    report = engine.generate_comprehensive_report(period_hours=24)
    
    # Export in different formats
    json_output = engine.export_report(report, 'json', 'report.json')
    text_output = engine.export_report(report, 'text')
    
    print("Report generated successfully!")
```

### Testing and Examples

```bash
# Run the comprehensive test suite
python3 examples/test_report_engine.py

# This will:
# - Create a test database with sample data
# - Test DNS classification
# - Generate sample reports
# - Demonstrate API usage
```

## Architecture

### Core Components

#### 1. ReportEngine Class
The main engine that handles database queries, data processing, and report generation.

**Key Methods:**
- `get_session_data()`: Query session data with filtering options
- `calculate_usage_stats()`: Compute bandwidth and usage statistics
- `generate_device_reports()`: Per-device usage analysis
- `generate_vlan_reports()`: Per-VLAN usage analysis
- `generate_comprehensive_report()`: Full network analysis
- `export_report()`: Export reports in multiple formats

#### 2. DNSClassifier Class
Intelligent classification of network traffic based on DNS hostnames.

**Features:**
- **Application Patterns**: YouTube, Facebook, Netflix, Microsoft, Apple, Gaming, CDN
- **Whitelist Support**: Automatically exclude OS updates and telemetry
- **Extensible**: Easy to add new classification patterns

**Example Classifications:**
```
www.youtube.com          -> YouTube
googlevideo.com          -> YouTube
facebook.com             -> Facebook
instagram.com            -> Facebook
netflix.com              -> Netflix
windowsupdate.microsoft.com -> EXCLUDED (whitelist)
steamcontent.com         -> Gaming
```

#### 3. Data Models
Structured data classes for type safety and clear APIs:

- `SessionData`: Network session records
- `UsageStats`: Bandwidth and session statistics
- `DeviceReport`: Per-device usage metrics
- `VLANReport`: Per-VLAN usage metrics

### Database Schema

The report engine expects the following SQLite tables:

```sql
-- Network sessions
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    src_ip TEXT NOT NULL,
    dst_ip TEXT NOT NULL,
    src_port INTEGER NOT NULL,
    dst_port INTEGER NOT NULL,
    protocol TEXT NOT NULL,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    duration REAL DEFAULT 0.0
);

-- Device information
CREATE TABLE devices (
    mac_address TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    device_name TEXT,
    vlan_id INTEGER,
    first_seen TEXT,
    last_seen TEXT
);

-- DNS resolution records
CREATE TABLE dns_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    vlan_id INTEGER,
    timestamp TEXT NOT NULL
);

-- VLAN configuration
CREATE TABLE vlans (
    vlan_id INTEGER PRIMARY KEY,
    vlan_name TEXT NOT NULL,
    description TEXT
);
```

## Command Line Interface

### Available Commands

#### `generate` - Comprehensive Reports
Generate full network usage reports with historical analysis.

```bash
# Basic 24-hour report
reportctl.py generate

# Custom period with JSON export
reportctl.py generate --period 72 --format json --output weekly.json

# Include historical comparison
reportctl.py generate --period 24 --include-historical --format text
```

**Options:**
- `--period HOURS`: Analysis period in hours (default: 24)
- `--format {json,text,html}`: Output format (default: text)
- `--output FILE`: Save to file
- `--include-historical`: Add period-over-period comparison

#### `devices` - Device Analysis
Show per-device usage statistics and top applications.

```bash
# Top 10 devices for last 24 hours
reportctl.py devices --limit 10

# Detailed device analysis for last week
reportctl.py devices --period 168 --details
```

**Options:**
- `--period HOURS`: Analysis period (default: 24)
- `--limit N`: Show top N devices
- `--details`: Include per-device application breakdown

#### `vlans` - VLAN Analysis
Analyze usage patterns across VLANs.

```bash
# VLAN usage summary
reportctl.py vlans

# Detailed VLAN analysis with top devices
reportctl.py vlans --details --period 48
```

**Options:**
- `--period HOURS`: Analysis period (default: 24)
- `--details`: Show top devices per VLAN

#### `apps` - Application Analysis
Break down network usage by application category.

```bash
# Application usage summary
reportctl.py apps

# Show classification examples
reportctl.py apps --show-classification --period 72
```

**Options:**
- `--period HOURS`: Analysis period (default: 24)
- `--show-classification`: Display DNS classification examples

#### `test-classifier` - DNS Testing
Test hostname classification rules.

```bash
# Test specific hostname
reportctl.py test-classifier --hostname www.youtube.com

# Test built-in examples
reportctl.py test-classifier
```

## Configuration

### DNS Classification Customization

Edit the `DNSClassifier` class in `services/report_engine.py` to customize application patterns:

```python
self.app_patterns = {
    'YouTube': [
        r'.*youtube\.com$',
        r'.*googlevideo\.com$',
        r'.*ytimg\.com$'
    ],
    'CustomApp': [
        r'.*yourapp\.com$',
        r'.*yourcdn\.net$'
    ]
}

# Add to whitelist to exclude from reports
self.whitelist_patterns.append(r'.*internal-updates\.company\.com$')
```

### Database Connection

Set the database path when initializing:

```python
# Default location
engine = ReportEngine("network.db")

# Custom location
engine = ReportEngine("/path/to/your/network.db")
```

For CLI usage:
```bash
reportctl.py generate --db /path/to/network.db
```

## API Reference

### ReportEngine Methods

#### `get_session_data(start_time, end_time, vlan_id=None, device_mac=None)`
Query session data with optional filtering.

**Parameters:**
- `start_time`: datetime - Start of analysis period
- `end_time`: datetime - End of analysis period  
- `vlan_id`: int, optional - Filter by VLAN ID
- `device_mac`: str, optional - Filter by device MAC address

**Returns:** List[SessionData]

#### `calculate_usage_stats(sessions)`
Calculate comprehensive usage statistics from session data.

**Parameters:**
- `sessions`: List[SessionData] - Session data to analyze

**Returns:** UsageStats object with:
- `total_bytes`: Total bandwidth used
- `total_sessions`: Number of sessions
- `avg_session_duration`: Average session length
- `top_applications`: Dict of application usage
- `peak_usage_hour`: Hour with highest usage
- `bytes_sent/received`: Directional traffic

#### `generate_comprehensive_report(period_hours=24, include_historical=True)`
Generate a complete network usage report.

**Parameters:**
- `period_hours`: int - Analysis period in hours
- `include_historical`: bool - Include period-over-period comparison

**Returns:** Dict containing:
- `report_metadata`: Generation info and period details
- `overall_stats`: Network-wide usage statistics
- `device_reports`: Per-device usage breakdown
- `vlan_reports`: Per-VLAN usage breakdown
- `historical_comparison`: Period-over-period analysis (if enabled)

#### `export_report(report, format_type='json', output_file=None)`
Export report in specified format.

**Parameters:**
- `report`: Dict - Report data from generate_comprehensive_report()
- `format_type`: str - 'json', 'text', or 'html'
- `output_file`: str, optional - File path to save output

**Returns:** str - Formatted report content

### Usage Examples

#### Custom Time Range Analysis
```python
from datetime import datetime, timedelta

with ReportEngine("network.db") as engine:
    # Last 6 hours
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=6)
    
    sessions = engine.get_session_data(start_time, end_time)
    stats = engine.calculate_usage_stats(sessions)
    
    print(f"Bandwidth used: {stats.total_bytes:,} bytes")
    print(f"Top app: {list(stats.top_applications.keys())[0]}")
```

#### VLAN-Specific Analysis
```python
with ReportEngine("network.db") as engine:
    # Analyze VLAN 10 for last 24 hours
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    sessions = engine.get_session_data(start_time, end_time, vlan_id=10)
    stats = engine.calculate_usage_stats(sessions)
    
    print(f"VLAN 10 usage: {stats.total_bytes:,} bytes")
```

#### Building Custom Reports
```python
with ReportEngine("network.db") as engine:
    # Get data for analysis
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    sessions = engine.get_session_data(start_time, end_time)
    
    # Custom analysis: Traffic by hour
    hourly_traffic = {}
    for session in sessions:
        hour = session.timestamp.hour
        hourly_traffic[hour] = hourly_traffic.get(hour, 0) + \
                              session.bytes_sent + session.bytes_received
    
    # Find peak hour
    peak_hour = max(hourly_traffic.items(), key=lambda x: x[1])
    print(f"Peak traffic: {peak_hour[1]:,} bytes at {peak_hour[0]}:00")
```

## Output Formats

### JSON Format
Structured data perfect for APIs and web applications:

```json
{
  "report_metadata": {
    "generated_at": "2025-07-01T15:30:00",
    "period_start": "2025-06-30T15:30:00", 
    "period_end": "2025-07-01T15:30:00",
    "period_hours": 24,
    "total_sessions_analyzed": 1247
  },
  "overall_stats": {
    "total_bytes": 15678234567,
    "total_sessions": 1247,
    "avg_session_duration": 245.6,
    "top_applications": {
      "YouTube": 8234567890,
      "Netflix": 4567890123,
      "Facebook": 1234567890
    },
    "peak_usage_hour": 20
  },
  "device_reports": [...],
  "vlan_reports": [...]
}
```

### Text Format
Human-readable summary reports:

```
============================================================
LNMT NETWORK USAGE REPORT
============================================================
Generated: 2025-07-01T15:30:00
Period: 2025-06-30T15:30:00 to 2025-07-01T15:30:00
Duration: 24 hours

OVERALL STATISTICS
--------------------
Total Bandwidth: 14.60 GB
Total Sessions: 1,247
Average Session Duration: 245.60s
Peak Usage Hour: 20:00
Data Sent: 2.34 GB
Data Received: 12.26 GB

TOP APPLICATIONS
--------------------
YouTube: 7.67 GB
Netflix: 4.25 GB
Facebook: 1.15 GB
```

### HTML Format
Web-ready reports with basic styling:

```html
<!DOCTYPE html>
<html>
<head>
    <title>LNMT Network Usage Report</title>
    <style>/* Modern CSS styling */</style>
</head>
<body>
    <div class="header">
        <h1>LNMT Network Usage Report</h1>
        <!-- Report content with tables and grids -->
    </div>
</body>
</html>
```

## Integration

### Web UI Integration
The JSON output format is designed for easy integration with web dashboards:

```javascript
// Fetch report data
fetch('/api/reports/generate?period=24&format=json')
  .then(response => response.json())
  .then(data => {
    // Use data.overall_stats, data.device_reports, etc.
    updateDashboard(data);
  });
```

### Automated Reporting
Set up scheduled reports using cron:

```bash
# Daily report at 6 AM
0 6 * * * /usr/bin/python3 /path/to/reportctl.py generate --period 24 --format json --output /reports/daily-$(date +\%Y\%m\%d).json

# Weekly summary on Mondays
0 8 * * 1 /usr/bin/python3 /path/to/reportctl.py generate --period 168 --format html --output /reports/weekly.html
```

### Custom Analytics Pipeline
```python
# Example: Custom analytics workflow
class NetworkAnalytics:
    def __init__(self, db_path):
        self.engine = ReportEngine(db_path)
    
    def detect_anomalies(self, threshold_multiplier=2.0):
        """Detect usage anomalies."""
        with self.engine:
            # Get current and historical data
            current = self.engine.generate_comprehensive_report(24)
            historical = self.engine.generate_comprehensive_report(168)
            
            # Compare usage patterns
            current_total = current['overall_stats']['total_bytes']
            historical_avg = historical['overall_stats']['total_bytes'] / 7
            
            if current_total > historical_avg * threshold_multiplier:
                return f"Anomaly detected: {current_total:,} bytes vs {historical_avg:,} average"
            
        return "Normal usage patterns"
```

## Troubleshooting

### Common Issues

#### Database Connection Errors
```
Error: Database file 'network.db' not found.
```
**Solution:** Ensure the LNMT tracker is running and has created the database, or specify the correct path with `--db`.

#### No Data in Reports
```
No sessions found for the specified period.
```
**Solution:** Check that:
- The tracker is actively collecting data
- The specified time period contains network activity
- Database permissions allow read access

#### Memory Issues with Large Datasets
For very large databases, consider:
- Using shorter time periods
- Implementing data pagination in custom applications
- Adding database indices for better performance

### Performance Optimization

#### Database Indices
Add these indices to improve query performance:

```sql
CREATE INDEX idx_sessions_timestamp ON sessions(timestamp);
CREATE INDEX idx_sessions_src_ip ON sessions(src_ip);
CREATE INDEX idx_dns_hostname ON dns_records(hostname);
CREATE INDEX idx_devices_vlan ON devices(vlan_id);
```

#### Memory Usage
For large datasets, consider streaming data processing:

```python
# Process data in chunks for large time periods
def process_large_dataset(engine, start_time, end_time, chunk_hours=6):
    results = []
    current_time = start_time
    
    while current_time < end_time:
        chunk_end = min(current_time + timedelta(hours=chunk_hours), end_time)
        sessions = engine.get_session_data(current_time, chunk_end)
        stats = engine.calculate_usage_stats(sessions)
        results.append(stats)
        current_time = chunk_end
    
    return results
```

## Contributing

### Adding New Classification Patterns

1. Edit `services/report_engine.py`
2. Update the `app_patterns` dictionary in `DNSClassifier.__init__()`
3. Add test cases in `examples/test_report_engine.py`
4. Test with `reportctl.py test-classifier`

### Adding New Export Formats

1. Add format handling in `ReportEngine.export_report()`
2. Implement format-specific method (e.g., `_format_csv_report()`)
3. Update CLI argument choices
4. Add tests and documentation

### Custom Analytics

Extend the `ReportEngine` class for specialized analysis:

```python
class ExtendedReportEngine(ReportEngine):
    def analyze_security_events(self, period_hours=24):
        """Custom security analysis."""
        # Your custom analysis logic here
        pass
    
    def generate_executive_summary(self, period_hours=168):
        """High-level executive report."""
        # Custom executive reporting logic
        pass
```

## License

[Specify your license here]

## Support

For issues, questions, or contributions:
- Create an issue in the project repository
- Check the troubleshooting section above
- Review the example code in `examples/test_report_engine.py`

---

**LNMT Report Engine** - Making network analytics simple and powerful! 🚀