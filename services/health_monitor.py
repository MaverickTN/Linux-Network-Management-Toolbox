#!/usr/bin/env python3
"""
LNMT Health Monitor Module

Monitors system health including:
- Critical service status (dnsmasq, Pi-hole, unbound, Shorewall)
- System resource usage (CPU, memory, disk)
- Configuration file integrity
- Alert management via logs, CLI, and web UI

Safety-first approach with actionable alerts and comprehensive logging.
"""

import json
import logging
import os
import psutil
import subprocess
import time
import hashlib
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


class ServiceStatus(Enum):
    """Service status states"""
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class Alert:
    """Alert data structure"""
    timestamp: str
    level: AlertLevel
    service: str
    message: str
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'level': self.level.value,
            'service': self.service,
            'message': self.message,
            'details': self.details
        }


@dataclass
class ServiceInfo:
    """Service information structure"""
    name: str
    status: ServiceStatus
    pid: Optional[int]
    memory_mb: float
    cpu_percent: float
    uptime: Optional[str]
    config_files: List[str]


@dataclass
class SystemResources:
    """System resource usage data"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_avg: Tuple[float, float, float]
    uptime: str


class HealthMonitor:
    """
    Main health monitoring class for LNMT system
    
    Example usage:
        monitor = HealthMonitor()
        status = monitor.get_system_status()
        monitor.check_service("dnsmasq")
        alerts = monitor.get_recent_alerts()
    """
    
    # Critical services to monitor
    CRITICAL_SERVICES = {
        'dnsmasq': {
            'process_name': 'dnsmasq',
            'config_files': ['/etc/dnsmasq.conf', '/etc/dnsmasq.d/'],
            'port': 53
        },
        'pihole': {
            'process_name': 'pihole-FTL',
            'config_files': ['/etc/pihole/pihole-FTL.conf'],
            'port': 4711
        },
        'unbound': {
            'process_name': 'unbound',
            'config_files': ['/etc/unbound/unbound.conf'],
            'port': 5335
        },
        'shorewall': {
            'process_name': 'shorewall',
            'config_files': ['/etc/shorewall/'],
            'check_command': ['shorewall', 'status']
        }
    }
    
    # Resource usage thresholds
    THRESHOLDS = {
        'cpu_warning': 80.0,
        'cpu_critical': 95.0,
        'memory_warning': 85.0,
        'memory_critical': 95.0,
        'disk_warning': 85.0,
        'disk_critical': 95.0
    }
    
    def __init__(self, log_file: str = '/var/log/lnmt-health.log'):
        """Initialize health monitor with logging setup"""
        self.log_file = log_file
        self.alerts: List[Alert] = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Config file hash cache for change detection
        self.config_hashes: Dict[str, str] = {}
        self._load_config_hashes()
    
    def _load_config_hashes(self) -> None:
        """Load stored configuration file hashes"""
        hash_file = '/var/lib/lnmt/config_hashes.json'
        try:
            if os.path.exists(hash_file):
                with open(hash_file, 'r') as f:
                    self.config_hashes = json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load config hashes: {e}")
    
    def _save_config_hashes(self) -> None:
        """Save configuration file hashes"""
        hash_file = '/var/lib/lnmt/config_hashes.json'
        try:
            os.makedirs(os.path.dirname(hash_file), exist_ok=True)
            with open(hash_file, 'w') as f:
                json.dump(self.config_hashes, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save config hashes: {e}")
    
    def _hash_file(self, filepath: str) -> Optional[str]:
        """Calculate SHA256 hash of a file"""
        try:
            if os.path.isfile(filepath):
                with open(filepath, 'rb') as f:
                    return hashlib.sha256(f.read()).hexdigest()
            elif os.path.isdir(filepath):
                # Hash directory contents
                file_hashes = []
                for root, dirs, files in os.walk(filepath):
                    for file in sorted(files):
                        file_path = os.path.join(root, file)
                        if os.path.isfile(file_path):
                            with open(file_path, 'rb') as f:
                                file_hashes.append(hashlib.sha256(f.read()).hexdigest())
                return hashlib.sha256(''.join(file_hashes).encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"Error hashing {filepath}: {e}")
        return None
    
    def _add_alert(self, level: AlertLevel, service: str, message: str, 
                   details: Dict[str, Any] = None) -> None:
        """Add an alert to the system"""
        alert = Alert(
            timestamp=datetime.now().isoformat(),
            level=level,
            service=service,
            message=message,
            details=details or {}
        )
        
        self.alerts.append(alert)
        
        # Log the alert
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.CRITICAL: logging.CRITICAL,
            AlertLevel.ERROR: logging.ERROR
        }[level]
        
        self.logger.log(log_level, f"[{service}] {message}")
        
        # Keep only recent alerts (last 1000)
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
    
    def check_service(self, service_name: str) -> ServiceInfo:
        """
        Check status of a specific service
        
        Example:
            info = monitor.check_service("dnsmasq")
            if info.status == ServiceStatus.STOPPED:
                print("dnsmasq is not running!")
        """
        if service_name not in self.CRITICAL_SERVICES:
            raise ValueError(f"Unknown service: {service_name}")
        
        service_config = self.CRITICAL_SERVICES[service_name]
        process_name = service_config['process_name']
        
        # Find process
        pid = None
        memory_mb = 0.0
        cpu_percent = 0.0
        uptime = None
        status = ServiceStatus.STOPPED
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent', 'create_time']):
                if proc.info['name'] == process_name:
                    pid = proc.info['pid']
                    memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                    cpu_percent = proc.info['cpu_percent']
                    create_time = datetime.fromtimestamp(proc.info['create_time'])
                    uptime = str(datetime.now() - create_time)
                    status = ServiceStatus.RUNNING
                    break
            
            # Additional checks for specific services
            if status == ServiceStatus.RUNNING:
                if service_name == 'shorewall' and 'check_command' in service_config:
                    try:
                        result = subprocess.run(
                            service_config['check_command'], 
                            capture_output=True, 
                            text=True, 
                            timeout=10
                        )
                        if result.returncode != 0:
                            status = ServiceStatus.FAILED
                    except Exception:
                        status = ServiceStatus.FAILED
            
        except Exception as e:
            self.logger.error(f"Error checking service {service_name}: {e}")
            status = ServiceStatus.UNKNOWN
        
        service_info = ServiceInfo(
            name=service_name,
            status=status,
            pid=pid,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            uptime=uptime,
            config_files=service_config['config_files']
        )
        
        # Generate alerts for service issues
        if status == ServiceStatus.STOPPED:
            self._add_alert(
                AlertLevel.CRITICAL,
                service_name,
                f"Service {service_name} is not running",
                {'pid': pid, 'expected_process': process_name}
            )
        elif status == ServiceStatus.FAILED:
            self._add_alert(
                AlertLevel.ERROR,
                service_name,
                f"Service {service_name} is running but not functioning properly",
                {'pid': pid}
            )
        
        return service_info
    
    def get_system_resources(self) -> SystemResources:
        """
        Get current system resource usage
        
        Example:
            resources = monitor.get_system_resources()
            if resources.cpu_percent > 90:
                print("High CPU usage detected!")
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load_avg = os.getloadavg()
            uptime = str(timedelta(seconds=time.time() - psutil.boot_time()))
            
            resources = SystemResources(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                load_avg=load_avg,
                uptime=uptime
            )
            
            # Check thresholds and generate alerts
            if cpu_percent >= self.THRESHOLDS['cpu_critical']:
                self._add_alert(
                    AlertLevel.CRITICAL,
                    'system',
                    f"Critical CPU usage: {cpu_percent:.1f}%",
                    {'cpu_percent': cpu_percent, 'threshold': self.THRESHOLDS['cpu_critical']}
                )
            elif cpu_percent >= self.THRESHOLDS['cpu_warning']:
                self._add_alert(
                    AlertLevel.WARNING,
                    'system',
                    f"High CPU usage: {cpu_percent:.1f}%",
                    {'cpu_percent': cpu_percent, 'threshold': self.THRESHOLDS['cpu_warning']}
                )
            
            if memory.percent >= self.THRESHOLDS['memory_critical']:
                self._add_alert(
                    AlertLevel.CRITICAL,
                    'system',
                    f"Critical memory usage: {memory.percent:.1f}%",
                    {'memory_percent': memory.percent, 'threshold': self.THRESHOLDS['memory_critical']}
                )
            elif memory.percent >= self.THRESHOLDS['memory_warning']:
                self._add_alert(
                    AlertLevel.WARNING,
                    'system',
                    f"High memory usage: {memory.percent:.1f}%",
                    {'memory_percent': memory.percent, 'threshold': self.THRESHOLDS['memory_warning']}
                )
            
            if disk.percent >= self.THRESHOLDS['disk_critical']:
                self._add_alert(
                    AlertLevel.CRITICAL,
                    'system',
                    f"Critical disk usage: {disk.percent:.1f}%",
                    {'disk_percent': disk.percent, 'threshold': self.THRESHOLDS['disk_critical']}
                )
            elif disk.percent >= self.THRESHOLDS['disk_warning']:
                self._add_alert(
                    AlertLevel.WARNING,
                    'system',
                    f"High disk usage: {disk.percent:.1f}%",
                    {'disk_percent': disk.percent, 'threshold': self.THRESHOLDS['disk_warning']}
                )
            
            return resources
            
        except Exception as e:
            self.logger.error(f"Error getting system resources: {e}")
            self._add_alert(
                AlertLevel.ERROR,
                'system',
                f"Could not retrieve system resources: {e}",
                {}
            )
            raise
    
    def validate_configs(self) -> Dict[str, bool]:
        """
        Validate configuration files for all services
        
        Returns:
            Dictionary mapping config files to validation status
            
        Example:
            results = monitor.validate_configs()
            for config, is_valid in results.items():
                if not is_valid:
                    print(f"Configuration issue in {config}")
        """
        results = {}
        
        for service_name, service_config in self.CRITICAL_SERVICES.items():
            for config_path in service_config['config_files']:
                try:
                    # Check if file/directory exists
                    if not os.path.exists(config_path):
                        results[config_path] = False
                        self._add_alert(
                            AlertLevel.ERROR,
                            service_name,
                            f"Configuration file missing: {config_path}",
                            {'config_path': config_path}
                        )
                        continue
                    
                    # Check file permissions
                    if os.path.isfile(config_path):
                        if not os.access(config_path, os.R_OK):
                            results[config_path] = False
                            self._add_alert(
                                AlertLevel.ERROR,
                                service_name,
                                f"Configuration file not readable: {config_path}",
                                {'config_path': config_path}
                            )
                            continue
                    
                    # Check for configuration changes
                    current_hash = self._hash_file(config_path)
                    if current_hash:
                        if config_path in self.config_hashes:
                            if self.config_hashes[config_path] != current_hash:
                                self._add_alert(
                                    AlertLevel.INFO,
                                    service_name,
                                    f"Configuration file changed: {config_path}",
                                    {'config_path': config_path, 'action': 'recommend_service_restart'}
                                )
                        
                        self.config_hashes[config_path] = current_hash
                    
                    # Service-specific validation
                    if service_name == 'dnsmasq' and config_path.endswith('dnsmasq.conf'):
                        # Basic dnsmasq config validation
                        try:
                            result = subprocess.run(
                                ['dnsmasq', '--test', '--conf-file', config_path],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            if result.returncode != 0:
                                results[config_path] = False
                                self._add_alert(
                                    AlertLevel.ERROR,
                                    service_name,
                                    f"dnsmasq configuration test failed: {result.stderr}",
                                    {'config_path': config_path, 'error': result.stderr}
                                )
                                continue
                        except Exception as e:
                            self.logger.warning(f"Could not test dnsmasq config: {e}")
                    
                    elif service_name == 'unbound' and config_path.endswith('unbound.conf'):
                        # Basic unbound config validation
                        try:
                            result = subprocess.run(
                                ['unbound-checkconf', config_path],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            if result.returncode != 0:
                                results[config_path] = False
                                self._add_alert(
                                    AlertLevel.ERROR,
                                    service_name,
                                    f"unbound configuration test failed: {result.stderr}",
                                    {'config_path': config_path, 'error': result.stderr}
                                )
                                continue
                        except Exception as e:
                            self.logger.warning(f"Could not test unbound config: {e}")
                    
                    results[config_path] = True
                    
                except Exception as e:
                    results[config_path] = False
                    self.logger.error(f"Error validating {config_path}: {e}")
                    self._add_alert(
                        AlertLevel.ERROR,
                        service_name,
                        f"Configuration validation error: {e}",
                        {'config_path': config_path, 'error': str(e)}
                    )
        
        # Save updated hashes
        self._save_config_hashes()
        return results
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status
        
        Returns:
            Complete system health report including services, resources, and configs
            
        Example:
            status = monitor.get_system_status()
            print(f"System health: {status['overall_health']}")
            for service in status['services']:
                print(f"{service['name']}: {service['status']}")
        """
        services = []
        failed_services = 0
        
        # Check all critical services
        for service_name in self.CRITICAL_SERVICES:
            try:
                service_info = self.check_service(service_name)
                services.append(asdict(service_info))
                
                if service_info.status in [ServiceStatus.STOPPED, ServiceStatus.FAILED]:
                    failed_services += 1
            except Exception as e:
                self.logger.error(f"Error checking service {service_name}: {e}")
                failed_services += 1
        
        # Get system resources
        try:
            resources = self.get_system_resources()
            resources_dict = asdict(resources)
        except Exception as e:
            self.logger.error(f"Error getting system resources: {e}")
            resources_dict = {}
        
        # Validate configurations
        try:
            config_results = self.validate_configs()
            failed_configs = sum(1 for result in config_results.values() if not result)
        except Exception as e:
            self.logger.error(f"Error validating configs: {e}")
            config_results = {}
            failed_configs = 0
        
        # Determine overall health
        if failed_services == 0 and failed_configs == 0:
            if (resources_dict.get('cpu_percent', 0) < self.THRESHOLDS['cpu_warning'] and
                resources_dict.get('memory_percent', 0) < self.THRESHOLDS['memory_warning'] and
                resources_dict.get('disk_percent', 0) < self.THRESHOLDS['disk_warning']):
                overall_health = "healthy"
            else:
                overall_health = "warning"
        elif failed_services > 0:
            overall_health = "critical"
        else:
            overall_health = "degraded"
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_health': overall_health,
            'services': services,
            'resources': resources_dict,
            'config_validation': config_results,
            'summary': {
                'total_services': len(self.CRITICAL_SERVICES),
                'failed_services': failed_services,
                'total_configs': len(config_results),
                'failed_configs': failed_configs
            }
        }
    
    def get_recent_alerts(self, hours: int = 24, level: Optional[AlertLevel] = None) -> List[Dict[str, Any]]:
        """
        Get recent alerts within specified timeframe
        
        Args:
            hours: Number of hours to look back
            level: Filter by alert level (optional)
            
        Returns:
            List of alert dictionaries
            
        Example:
            # Get critical alerts from last 6 hours
            critical_alerts = monitor.get_recent_alerts(hours=6, level=AlertLevel.CRITICAL)
            for alert in critical_alerts:
                print(f"CRITICAL: {alert['message']}")
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_alerts = []
        for alert in self.alerts:
            alert_time = datetime.fromisoformat(alert.timestamp)
            if alert_time >= cutoff_time:
                if level is None or alert.level == level:
                    recent_alerts.append(alert.to_dict())
        
        return sorted(recent_alerts, key=lambda x: x['timestamp'], reverse=True)
    
    def clear_alerts(self, hours: Optional[int] = None) -> int:
        """
        Clear alerts older than specified hours (or all if None)
        
        Returns:
            Number of alerts cleared
        """
        if hours is None:
            cleared = len(self.alerts)
            self.alerts = []
            return cleared
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        original_count = len(self.alerts)
        
        self.alerts = [
            alert for alert in self.alerts
            if datetime.fromisoformat(alert.timestamp) >= cutoff_time
        ]
        
        return original_count - len(self.alerts)
    
    def send_web_alert(self, alert: Alert) -> bool:
        """
        Send alert to web UI endpoint (stub implementation)
        
        In production, this would POST to a web API endpoint
        """
        try:
            # Stub implementation - would normally POST to web endpoint
            web_alert_file = '/tmp/lnmt_web_alerts.json'
            
            alerts_data = []
            if os.path.exists(web_alert_file):
                try:
                    with open(web_alert_file, 'r') as f:
                        alerts_data = json.load(f)
                except Exception:
                    alerts_data = []
            
            alerts_data.append(alert.to_dict())
            
            # Keep only last 100 alerts for web UI
            if len(alerts_data) > 100:
                alerts_data = alerts_data[-100:]
            
            with open(web_alert_file, 'w') as f:
                json.dump(alerts_data, f, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send web alert: {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    # Example: Basic health check
    print("=== LNMT Health Monitor Example ===")
    
    monitor = HealthMonitor()
    
    # Check system status
    print("\n1. System Status:")
    status = monitor.get_system_status()
    print(f"Overall Health: {status['overall_health']}")
    print(f"Services: {status['summary']['failed_services']}/{status['summary']['total_services']} failed")
    print(f"Configs: {status['summary']['failed_configs']}/{status['summary']['total_configs']} failed")
    
    # Check individual service
    print("\n2. Service Check Example:")
    try:
        dnsmasq_info = monitor.check_service("dnsmasq")
        print(f"dnsmasq: {dnsmasq_info.status.value}")
        if dnsmasq_info.pid:
            print(f"  PID: {dnsmasq_info.pid}")
            print(f"  Memory: {dnsmasq_info.memory_mb:.1f} MB")
            print(f"  Uptime: {dnsmasq_info.uptime}")
    except Exception as e:
        print(f"Error checking dnsmasq: {e}")
    
    # Show recent alerts
    print("\n3. Recent Alerts:")
    alerts = monitor.get_recent_alerts(hours=1)
    for alert in alerts[:5]:  # Show last 5 alerts
        print(f"  [{alert['level'].upper()}] {alert['service']}: {alert['message']}")
    
    print(f"\nTotal alerts in last hour: {len(alerts)}")
    print("Health monitor example completed.")
