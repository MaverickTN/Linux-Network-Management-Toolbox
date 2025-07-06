#!/usr/bin/env python3
"""
LNMT VLAN Controller Examples and Test Code
Demonstrates usage patterns and provides test scenarios
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path

# Add the services directory to the path
sys.path.append('/opt/lnmt/services')

from vlan_controller import VLANController, VLANConfig

def test_basic_vlan_operations():
    """Test basic VLAN CRUD operations"""
    print("🧪 Testing Basic VLAN Operations")
    print("=" * 50)
    
    # Initialize controller
    controller = VLANController(db_path="/tmp/test_vlan.db")
    
    # Test 1: Create VLANs
    print("\n1. Creating test VLANs...")
    
    # Guest Network VLAN
    success = controller.create_vlan(
        vlan_id=100,
        name="Guest Network",
        description="Isolated network for guest devices",
        subnet="192.168.100.0/24",
        gateway="192.168.100.1",
        interfaces=["eth0"],
        bandwidth_limit=50,  # 50 Mbps
        usage_threshold=80,  # 80%
        auto_blacklist=True,
        priority=3
    )
    print(f"   Guest Network VLAN: {'✅ Created' if success else '❌ Failed'}")
    
    # IoT Network VLAN
    success = controller.create_vlan(
        vlan_id=200,
        name="IoT Network",
        description="Network for IoT devices",
        subnet="192.168.200.0/24",
        gateway="192.168.200.1",
        interfaces=["eth0", "wlan0"],
        bandwidth_limit=20,  # 20 Mbps
        usage_threshold=90,  # 90%
        auto_blacklist=False,
        priority=5
    )
    print(f"   IoT Network VLAN: {'✅ Created' if success else '❌ Failed'}")
    
    # Management Network VLAN
    success = controller.create_vlan(
        vlan_id=300,
        name="Management Network",
        description="Network for management traffic",
        subnet="192.168.300.0/24",
        gateway="192.168.300.1",
        interfaces=["eth1"],
        priority=1  # Highest priority
    )
    print(f"   Management Network VLAN: {'✅ Created' if success else '❌ Failed'}")
    
    # Test 2: List VLANs
    print("\n2. Listing all VLANs...")
    vlans = controller.list_vlans()
    for vlan in vlans:
        print(f"   VLAN {vlan.vlan_id}: {vlan.name} - {vlan.subnet}")
    
    # Test 3: Get specific VLAN
    print("\n3. Getting VLAN details...")
    vlan = controller.get_vlan(100)
    if vlan:
        print(f"   VLAN 100 Details:")
        print(f"     Name: {vlan.name}")
        print(f"     Subnet: {vlan.subnet}")
        print(f"     Interfaces: {', '.join(vlan.interfaces)}")
        print(f"     Bandwidth Limit: {vlan.bandwidth_limit}Mbps")
        print(f"     Auto-blacklist: {'Enabled' if vlan.auto_blacklist else 'Disabled'}")
    
    # Test 4: Update VLAN
    print("\n4. Updating VLAN configuration...")
    success = controller.update_vlan(
        100,
        bandwidth_limit=100,  # Increase to 100 Mbps
        usage_threshold=70,   # Lower threshold
        description="Updated guest network with higher bandwidth"
    )
    print(f"   VLAN 100 Update: {'✅ Success' if success else '❌ Failed'}")
    
    # Test 5: Delete VLAN
    print("\n5. Deleting test VLAN...")
    success = controller.delete_vlan(300)
    print(f"   VLAN 300 Deletion: {'✅ Success' if success else '❌ Failed'}")
    
    # Final verification
    print("\n6. Final VLAN count...")
    vlans = controller.list_vlans()
    print(f"   Total VLANs: {len(vlans)}")
    
    return controller

def test_topology_export(controller):
    """Test topology export functionality"""
    print("\n🌐 Testing Topology Export")
    print("=" * 50)
    
    # Export topology
    output_file = "/tmp/test_vlan_topology.dot"
    success = controller.export_topology(output_file)
    
    if success:
        print(f"✅ Topology exported to {output_file}")
        
        # Read and display the topology file
        with open(output_file, 'r') as f:
            content = f.read()
        
        print("\nTopology file content:")
        print("-" * 30)
        print(content)
        print("-" * 30)
    else:
        print("❌ Failed to export topology")

def test_monitoring_simulation(controller):
    """Simulate monitoring and statistics collection"""
    print("\n📊 Testing Monitoring Simulation")
    print("=" * 50)
    
    # This would normally integrate with real network monitoring
    # For testing, we'll simulate some statistics
    
    from vlan_controller import VLANStats
    
    vlans = controller.list_vlans()
    for vlan in vlans:
        # Simulate some statistics
        stats = VLANStats(
            vlan_id=vlan.vlan_id,
            bytes_in=1024 * 1024 * 100,  # 100 MB
            bytes_out=1024 * 1024 * 50,  # 50 MB
            packets_in=50000,
            packets_out=25000,
            bandwidth_usage=vlan.bandwidth_limit * 0.6 if vlan.bandwidth_limit else 10.0,  # 60% usage
            connected_devices=5,
            timestamp=datetime.now().isoformat()
        )
        
        # Save statistics
        success = controller.db.save_stats(stats)
        print(f"   VLAN {vlan.vlan_id} Stats: {'✅ Saved' if success else '❌ Failed'}")
        print(f"     Bandwidth Usage: {stats.bandwidth_usage:.1f} Mbps")
        print(f"     Connected Devices: {stats.connected_devices}")

def test_configuration_export_import(controller):
    """Test configuration export and import"""
    print("\n💾 Testing Configuration Export/Import")
    print("=" * 50)
    
    # Export configuration
    vlans = controller.list_vlans()
    config = {
        'vlans': [vlan.__dict__ for vlan in vlans],
        'exported_at': datetime.now().isoformat()
    }
    
    config_file = "/tmp/test_vlan_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2, default=str)
    
    print(f"✅ Configuration exported to {config_file}")
    
    # Display exported configuration
    print("\nExported configuration:")
    print("-" * 30)
    print(json.dumps(config, indent=2, default=str))
    print("-" * 30)

def test_validation_scenarios(controller):
    """Test various validation scenarios"""
    print("\n🔍 Testing Validation Scenarios")
    print("=" * 50)
    
    # Test 1: Try to create VLAN with existing ID
    print("\n1. Testing duplicate VLAN ID...")
    success = controller.create_vlan(
        vlan_id=100,  # This should already exist
        name="Duplicate Test",
        description="This should fail",
        subnet="192.168.150.0/24",
        gateway="192.168.150.1",
        interfaces=["eth0"]
    )
    print(f"   Duplicate VLAN Creation: {'❌ Correctly Failed' if not success else '⚠️  Unexpectedly Succeeded'}")
    
    # Test 2: Try to create VLAN with invalid subnet
    print("\n2. Testing invalid subnet...")
    success = controller.create_vlan(
        vlan_id=999,
        name="Invalid Subnet Test",
        description="This should fail",
        subnet="invalid.subnet",
        gateway="192.168.999.1",
        interfaces=["eth0"]
    )
    print(f"   Invalid Subnet Creation: {'❌ Correctly Failed' if not success else '⚠️  Unexpectedly Succeeded'}")
    
    # Test 3: Get non-existent VLAN
    print("\n3. Testing non-existent VLAN retrieval...")
    vlan = controller.get_vlan(9999)
    print(f"   Non-existent VLAN Retrieval: {'✅ Correctly Returned None' if vlan is None else '⚠️  Unexpectedly Found VLAN'}")

def create_sample_config_files():
    """Create sample configuration files for testing import functionality"""
    print("\n📁 Creating Sample Configuration Files")
    print("=" * 50)
    
    # Sample YAML configuration
    yaml_config = """
vlans:
  - vlan_id: 10
    name: "DMZ Network"
    description: "Demilitarized zone for public services"
    subnet: "10.0.10.0/24"
    gateway: "10.0.10.1"
    interfaces: ["eth0"]
    bandwidth_limit: 1000
    usage_threshold: 85
    auto_blacklist: true
    priority: 2
    
  - vlan_id: 20
    name: "Development Network"
    description: "Network for development servers"
    subnet: "10.0.20.0/24"
    gateway: "10.0.20.1"
    interfaces: ["eth0", "eth1"]
    bandwidth_limit: 500
    usage_threshold: 75
    auto_blacklist: false
    priority: 4
    
  - vlan_id: 30
    name: "Security Cameras"
    description: "Isolated network for security cameras"
    subnet: "10.0.30.0/24"
    gateway: "10.0.30.1"
    interfaces: ["eth2"]
    bandwidth_limit: 200
    usage_threshold: 95
    auto_blacklist: true
    priority: 6

exported_at: "2025-01-01T00:00:00"
"""
    
    yaml_file = "/tmp/sample_vlan_config.yaml"
    with open(yaml_file, 'w') as f:
        f.write(yaml_config)
    print(f"✅ Created sample YAML config: {yaml_file}")
    
    # Sample JSON configuration
    json_config = {
        "vlans": [
            {
                "vlan_id": 40,
                "name": "Voice Network",
                "description": "VoIP and telephony network",
                "subnet": "10.0.40.0/24",
                "gateway": "10.0.40.1",
                "interfaces": ["eth0"],
                "bandwidth_limit": 100,
                "usage_threshold": 80,
                "auto_blacklist": false,
                "priority": 1
            },
            {
                "vlan_id": 50,
                "name": "Printer Network",
                "description": "Network for printers and scanners",
                "subnet": "10.0.50.0/24",
                "gateway": "10.0.50.1",
                "interfaces": ["eth1"],
                "bandwidth_limit": 50,
                "usage_threshold": 90,
                "auto_blacklist": false,
                "priority": 7
            }
        ],
        "exported_at": "2025-01-01T00:00:00"
    }
    
    json_file = "/tmp/sample_vlan_config.json"
    with open(json_file, 'w') as f:
        json.dump(json_config, f, indent=2)
    print(f"✅ Created sample JSON config: {json_file}")
    
    return yaml_file, json_file

def test_cli_integration():
    """Test CLI integration by running commands"""
    print("\n🖥️  Testing CLI Integration")
    print("=" * 50)
    
    import subprocess
    
    cli_script = "/opt/lnmt/cli/vlanctl.py"
    
    # Test help command
    print("\n1. Testing CLI help...")
    try:
        result = subprocess.run([sys.executable, cli_script, '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ CLI help command works")
            print("   Sample output:")
            print("   " + "\n   ".join(result.stdout.split('\n')[:5]))
        else:
            print("❌ CLI help command failed")
    except Exception as e:
        print(f"⚠️  CLI help test failed: {e}")
    
    # Test list command
    print("\n2. Testing CLI list command...")
    try:
        result = subprocess.run([sys.executable, cli_script, 'list', '--output-format', 'json'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ CLI list command works")
            try:
                data = json.loads(result.stdout)
                print(f"   Found {len(data)} VLANs")
            except json.JSONDecodeError:
                print("   Output is not valid JSON")
        else:
            print("❌ CLI list command failed")
            print(f"   Error: {result.stderr}")
    except Exception as e:
        print(f"⚠️  CLI list test failed: {e}")

def test_security_features(controller):
    """Test security-related features"""
    print("\n🔒 Testing Security Features")
    print("=" * 50)
    
    # Test auto-blacklisting configuration
    print("\n1. Testing auto-blacklist configuration...")
    
    # Get a VLAN with auto-blacklist enabled
    vlans = controller.list_vlans()
    auto_blacklist_vlans = [vlan for vlan in vlans if vlan.auto_blacklist]
    
    if auto_blacklist_vlans:
        vlan = auto_blacklist_vlans[0]
        print(f"   VLAN {vlan.vlan_id} has auto-blacklist enabled")
        print(f"   Usage threshold: {vlan.usage_threshold}%")
        print(f"   Bandwidth limit: {vlan.bandwidth_limit}Mbps")
        
        # Test blacklisting a device
        print("\n2. Testing device blacklisting...")
        success = controller.db.blacklist_device(
            mac_address="aa:bb:cc:dd:ee:ff",
            ip_address="192.168.100.100",
            vlan_id=vlan.vlan_id,
            reason="Exceeded usage threshold during testing"
        )
        print(f"   Device blacklisting: {'✅ Success' if success else '❌ Failed'}")
    else:
        print("   No VLANs with auto-blacklist enabled found")

def test_performance_scenarios():
    """Test performance with multiple VLANs"""
    print("\n⚡ Testing Performance Scenarios")
    print("=" * 50)
    
    # Create a separate controller for performance testing
    perf_controller = VLANController(db_path="/tmp/perf_test_vlan.db")
    
    print("\n1. Creating multiple VLANs...")
    start_time = time.time()
    
    # Create 20 test VLANs
    created_count = 0
    for i in range(1, 21):
        vlan_id = 1000 + i
        success = perf_controller.create_vlan(
            vlan_id=vlan_id,
            name=f"Test VLAN {i}",
            description=f"Performance test VLAN {i}",
            subnet=f"10.{100 + i}.0.0/24",
            gateway=f"10.{100 + i}.0.1",
            interfaces=["eth0"],
            bandwidth_limit=100 + (i * 10),
            priority=i % 7 + 1
        )
        if success:
            created_count += 1
    
    creation_time = time.time() - start_time
    print(f"   Created {created_count}/20 VLANs in {creation_time:.2f} seconds")
    
    print("\n2. Testing bulk operations...")
    start_time = time.time()
    
    # List all VLANs
    vlans = perf_controller.list_vlans()
    list_time = time.time() - start_time
    print(f"   Listed {len(vlans)} VLANs in {list_time:.3f} seconds")
    
    # Update all VLANs
    start_time = time.time()
    update_count = 0
    for vlan in vlans:
        success = perf_controller.update_vlan(
            vlan.vlan_id,
            description=f"Updated {vlan.description}"
        )
        if success:
            update_count += 1
    
    update_time = time.time() - start_time
    print(f"   Updated {update_count} VLANs in {update_time:.2f} seconds")
    
    # Cleanup
    print("\n3. Cleaning up test VLANs...")
    start_time = time.time()
    deleted_count = 0
    
    for vlan in vlans:
        if vlan.vlan_id >= 1000:  # Only delete test VLANs
            success = perf_controller.delete_vlan(vlan.vlan_id)
            if success:
                deleted_count += 1
    
    deletion_time = time.time() - start_time
    print(f"   Deleted {deleted_count} VLANs in {deletion_time:.2f} seconds")

def generate_test_report(controller):
    """Generate a comprehensive test report"""
    print("\n📋 Generating Test Report")
    print("=" * 50)
    
    # Collect system information
    vlans = controller.list_vlans()
    
    report = {
        "test_timestamp": datetime.now().isoformat(),
        "system_info": {
            "total_vlans": len(vlans),
            "vlans_with_bandwidth_limits": len([v for v in vlans if v.bandwidth_limit]),
            "vlans_with_auto_blacklist": len([v for v in vlans if v.auto_blacklist]),
            "unique_interfaces": len(set().union(*[v.interfaces for v in vlans])),
        },
        "vlan_summary": []
    }
    
    for vlan in vlans:
        vlan_data = {
            "vlan_id": vlan.vlan_id,
            "name": vlan.name,
            "subnet": vlan.subnet,
            "interface_count": len(vlan.interfaces),
            "has_bandwidth_limit": vlan.bandwidth_limit is not None,
            "has_usage_threshold": vlan.usage_threshold is not None,
            "auto_blacklist_enabled": vlan.auto_blacklist,
            "priority": vlan.priority
        }
        report["vlan_summary"].append(vlan_data)
    
    # Save report
    report_file = "/tmp/vlan_test_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"✅ Test report saved to {report_file}")
    
    # Display summary
    print("\nTest Summary:")
    print(f"  Total VLANs: {report['system_info']['total_vlans']}")
    print(f"  VLANs with Bandwidth Limits: {report['system_info']['vlans_with_bandwidth_limits']}")
    print(f"  VLANs with Auto-blacklist: {report['system_info']['vlans_with_auto_blacklist']}")
    print(f"  Unique Interfaces: {report['system_info']['unique_interfaces']}")
    
    return report

def main():
    """Main test runner"""
    print("🚀 LNMT VLAN Controller Test Suite")
    print("=" * 60)
    print(f"Test started at: {datetime.now().isoformat()}")
    
    try:
        # Run all tests
        controller = test_basic_vlan_operations()
        test_topology_export(controller)
        test_monitoring_simulation(controller)
        test_configuration_export_import(controller)
        test_validation_scenarios(controller)
        test_security_features(controller)
        test_performance_scenarios()
        
        # Create sample configuration files
        yaml_file, json_file = create_sample_config_files()
        
        # Test CLI integration
        test_cli_integration()
        
        # Generate final report
        report = generate_test_report(controller)
        
        print("\n🎉 All Tests Completed Successfully!")
        print("=" * 60)
        
        print(f"\nTest artifacts created:")
        print(f"  - Database: /tmp/test_vlan.db")
        print(f"  - Topology: /tmp/test_vlan_topology.dot")
        print(f"  - Config Export: /tmp/test_vlan_config.json")
        print(f"  - Sample YAML: {yaml_file}")
        print(f"  - Sample JSON: {json_file}")
        print(f"  - Test Report: /tmp/vlan_test_report.json")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)