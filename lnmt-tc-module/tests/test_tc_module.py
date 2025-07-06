#!/usr/bin/env python3
"""
LNMT TC/QoS Test Suite
Comprehensive testing for Traffic Control module

Test Categories:
- Unit tests for core functionality
- Integration tests for policy application
- Performance tests for high-load scenarios
- Safety tests for rollback functionality
- API tests for web interface

Author: LNMT Development Team
License: MIT
"""

import json
import os
import sqlite3
import subprocess
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import modules to test
try:
    from tc_service import (
        TCManager, TCInterface, TCQdisc, TCClass, TCFilter, TCPolicy
    )
    from tcctl_cli import TCControlCLI
    from tc_web_api import TCWebAPI
except ImportError as e:
    print(f"Warning: Could not import TC modules: {e}")
    print("Make sure all TC modules are in the Python path")

class TestTCInterface(unittest.TestCase):
    """Test TCInterface class"""
    
    def test_interface_creation(self):
        """Test basic interface creation"""
        interface = TCInterface(
            name="eth0",
            index=1,
            type="ethernet",
            state="UP",
            mtu=1500,
            mac_address="00:11:22:33:44:55",
            ip_addresses=["192.168.1.100"]
        )
        
        self.assertEqual(interface.name, "eth0")
        self.assertEqual(interface.type, "ethernet")
        self.assertEqual(interface.state, "UP")
        self.assertEqual(len(interface.ip_addresses), 1)
    
    def test_vlan_interface_creation(self):
        """Test VLAN interface creation with auto-detection"""
        interface = TCInterface(
            name="eth0.100",
            index=2,
            type="vlan",
            state="UP",
            mtu=1500,
            mac_address="00:11:22:33:44:55",
            ip_addresses=["192.168.100.1"]
        )
        
        self.assertEqual(interface.vlan_id, 100)
        self.assertEqual(interface.parent_interface, "eth0")

class TestTCQdisc(unittest.TestCase):
    """Test TCQdisc class"""
    
    def test_qdisc_creation(self):
        """Test qdisc creation"""
        qdisc = TCQdisc(
            handle="1:",
            parent="root",
            kind="htb",
            interface="eth0",
            options={"default": "30"},
            created_at=datetime.now()
        )
        
        self.assertEqual(qdisc.kind, "htb")
        self.assertEqual(qdisc.options["default"], "30")
    
    def test_qdisc_to_tc_command(self):
        """Test conversion to tc command"""
        qdisc = TCQdisc(
            handle="1:",
            parent="root",
            kind="htb",
            interface="eth0",
            options={"default": "30"},
            created_at=datetime.now()
        )
        
        cmd = qdisc.to_tc_command()
        expected = ['tc', 'qdisc', 'add', 'dev', 'eth0', 'root', 'handle', '1:', 'htb', 'default', '30']
        self.assertEqual(cmd, expected)

class TestTCClass(unittest.TestCase):
    """Test TCClass class"""
    
    def test_class_creation(self):
        """Test class creation"""
        tc_class = TCClass(
            classid="1:10",
            parent="1:1",
            kind="htb",
            interface="eth0",
            rate="10mbit",
            ceil="20mbit",
            prio=1
        )
        
        self.assertEqual(tc_class.classid, "1:10")
        self.assertEqual(tc_class.rate, "10mbit")
        self.assertEqual(tc_class.prio, 1)
    
    def test_class_to_tc_command(self):
        """Test conversion to tc command"""
        tc_class = TCClass(
            classid="1:10",
            parent="1:1",
            kind="htb",
            interface="eth0",
            rate="10mbit",
            ceil="20mbit",
            prio=1
        )
        
        cmd = tc_class.to_tc_command()
        self.assertIn('tc', cmd)
        self.assertIn('class', cmd)
        self.assertIn('1:10', cmd)
        self.assertIn('10mbit', cmd)

class TestTCFilter(unittest.TestCase):
    """Test TCFilter class"""
    
    def test_filter_creation(self):
        """Test filter creation"""
        tc_filter = TCFilter(
            handle="1:",
            parent="1:",
            protocol="ip",
            prio=1,
            kind="u32",
            interface="eth0",
            match_criteria={"dport": 80},
            flowid="1:10"
        )
        
        self.assertEqual(tc_filter.protocol, "ip")
        self.assertEqual(tc_filter.match_criteria["dport"], 80)
    
    def test_filter_to_tc_command(self):
        """Test conversion to tc command"""
        tc_filter = TCFilter(
            handle="1:",
            parent="1:",
            protocol="ip",
            prio=1,
            kind="u32",
            interface="eth0",
            match_criteria={"dport": 80},
            flowid="1:10"
        )
        
        cmd = tc_filter.to_tc_command()
        self.assertIn('tc', cmd)
        self.assertIn('filter', cmd)
        self.assertIn('u32', cmd)

class TestTCManager(unittest.TestCase):
    """Test TCManager class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        
        # Create test configuration
        test_config = {
            "tc_path": "/bin/true",  # Use /bin/true to avoid actual tc commands
            "ip_path": "/bin/true",
            "backup_dir": tempfile.mkdtemp(),
            "safety": {
                "backup_before_apply": True,
                "rollback_timeout": 300
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize TC manager with test config
        self.tc_manager = TCManager(
            config_path=self.temp_config.name,
            db_manager=None
        )
        self.tc_manager.db_conn = sqlite3.connect(self.temp_db.name)
        self.tc_manager.db_conn.row_factory = sqlite3.Row
        self.tc_manager._create_tables()
    
    def tearDown(self):
        """Clean up test environment"""
        self.tc_manager.close()
        os.unlink(self.temp_db.name)
        os.unlink(self.temp_config.name)
    
    def test_database_initialization(self):
        """Test database table creation"""
        cursor = self.tc_manager.db_conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'tc_interfaces', 'tc_policies', 'tc_qdiscs', 
            'tc_classes', 'tc_filters', 'tc_statistics'
        ]
        
        for table in expected_tables:
            self.assertIn(table, tables)
    
    def test_policy_creation(self):
        """Test policy creation and storage"""
        # Create test policy
        qdisc = TCQdisc(
            handle="1:",
            parent="root",
            kind="htb",
            interface="eth0",
            options={"default": "30"},
            created_at=datetime.now()
        )
        
        tc_class = TCClass(
            classid="1:10",
            parent="1:",
            kind="htb",
            interface="eth0",
            rate="10mbit",
            ceil="20mbit"
        )
        
        policy = TCPolicy(
            name="test_policy",
            description="Test policy",
            interface="eth0",
            qdiscs=[qdisc],
            classes=[tc_class],
            filters=[]
        )
        
        # Create policy
        success = self.tc_manager.create_policy(policy)
        self.assertTrue(success)
        
        # Retrieve policy
        retrieved_policy = self.tc_manager.get_policy("test_policy")
        self.assertIsNotNone(retrieved_policy)
        self.assertEqual(retrieved_policy.name, "test_policy")
        self.assertEqual(len(retrieved_policy.qdiscs), 1)
        self.assertEqual(len(retrieved_policy.classes), 1)
    
    def test_policy_deletion(self):
        """Test policy deletion"""
        # Create and delete policy
        policy = TCPolicy(
            name="delete_test",
            description="Policy to delete",
            interface="eth0",
            qdiscs=[],
            classes=[],
            filters=[]
        )
        
        self.tc_manager.create_policy(policy)
        success = self.tc_manager.delete_policy("delete_test")
        self.assertTrue(success)
        
        # Verify deletion
        retrieved_policy = self.tc_manager.get_policy("delete_test")
        self.assertIsNone(retrieved_policy)
    
    @patch('subprocess.run')
    def test_interface_discovery_fallback(self, mock_subprocess):
        """Test interface discovery fallback method"""
        # Mock /proc/net/dev content
        mock_proc_content = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo col