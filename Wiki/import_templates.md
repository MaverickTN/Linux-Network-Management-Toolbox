# Device Import Template
# Save as: device_import_template.csv
# Use this template to import your own devices into LNMT

hostname,ip_address,mac_address,device_type,manufacturer,model,os_version,department,location,status,tags
router-001,192.168.1.1,aa:bb:cc:dd:ee:01,Router,Cisco,ISR4321,16.9.4,IT,"Floor 1, Server Room",online,"critical,production"
switch-001,192.168.1.2,aa:bb:cc:dd:ee:02,Switch,HP,ProCurve 2530,YA.16.02.0008,IT,"Floor 1, Server Room",online,"production,managed"
firewall-001,192.168.1.3,aa:bb:cc:dd:ee:03,Firewall,Fortinet,FortiGate 60F,7.0.5,IT,"Floor 1, Server Room",online,"critical,security"
server-001,192.168.1.10,aa:bb:cc:dd:ee:04,Server,Dell,PowerEdge R740,Ubuntu 20.04,IT,"Floor 1, Server Room",online,"production,virtualization"
workstation-001,192.168.1.50,aa:bb:cc:dd:ee:05,Workstation,HP,EliteDesk 800,Windows 10,Sales,"Floor 2, Room 201",online,"managed"
printer-001,192.168.1.100,aa:bb:cc:dd:ee:06,Printer,HP,LaserJet Pro M404,1.0.12,Office,"Floor 2, Copy Room",online,"shared"
camera-001,192.168.1.150,aa:bb:cc:dd:ee:07,Camera,Hikvision,DS-2CD2143G0,5.7.3,Security,"Floor 1, Entrance",online,"monitoring,security"
ap-001,192.168.1.200,aa:bb:cc:dd:ee:08,Access Point,Ubiquiti,UniFi AP AC Pro,4.3.21,IT,"Floor 2, Ceiling",online,"wifi,managed"

---

# User Import Template  
# Save as: user_import_template.csv
# Use this template to import user accounts into LNMT

username,email,first_name,last_name,department,role,status,two_factor_enabled,session_timeout,password_expires_days
john.smith,john.smith@company.com,John,Smith,IT,admin,active,true,120,90
jane.doe,jane.doe@company.com,Jane,Doe,IT,operator,active,true,60,90
mike.wilson,mike.wilson@company.com,Mike,Wilson,Sales,viewer,active,false,30,90
sarah.johnson,sarah.johnson@company.com,Sarah,Johnson,HR,viewer,active,false,30,90
david.brown,david.brown@company.com,David,Brown,Finance,viewer,active,true,60,90
lisa.garcia,lisa.garcia@company.com,Lisa,Garcia,Marketing,viewer,active,false,30,90
chris.miller,chris.miller@company.com,Chris,Miller,Operations,operator,active,true,60,90
amy.davis,amy.davis@company.com,Amy,Davis,Support,viewer,active,false,30,90
tom.anderson,tom.anderson@company.com,Tom,Anderson,Engineering,operator,active,true,90,90
emma.taylor,emma.taylor@company.com,Emma,Taylor,Management,admin,active,true,240,90

---

# VLAN Import Template
# Save as: vlan_import_template.csv  
# Use this template to configure VLANs in LNMT

vlan_id,name,description,network,gateway,dhcp_enabled,dhcp_range_start,dhcp_range_end,dns_servers,domain,access_control
100,Management,Network management and admin access,192.168.100.0/24,192.168.100.1,false,,,8.8.8.8;8.8.4.4,mgmt.company.local,secured
110,Servers,Production servers and services,10.0.10.0/24,10.0.10.1,false,,,8.8.8.8;8.8.4.4,servers.company.local,restricted
120,Workstations,Employee workstations and laptops,192.168.1.0/24,192.168.1.1,true,192.168.1.10,192.168.1.200,8.8.8.8;8.8.4.4,corp.company.local,open
130,Guest,Guest network access,172.16.1.0/24,172.16.1.1,true,172.16.1.10,172.16.1.100,8.8.8.8;8.8.4.4,guest.company.local,restricted
140,IoT,IoT devices and sensors,10.0.20.0/24,10.0.20.1,true,10.0.20.10,10.0.20.200,8.8.8.8;8.8.4.4,iot.company.local,restricted
150,DMZ,Demilitarized zone for external services,203.0.113.0/24,203.0.113.1,false,,,8.8.8.8;8.8.4.4,dmz.company.local,secured
160,VoIP,Voice over IP phones and systems,10.0.30.0/24,10.0.30.1,true,10.0.30.10,10.0.30.100,8.8.8.8;8.8.4.4,voip.company.local,restricted
170,Security,Security cameras and access control,192.168.200.0/24,192.168.200.1,true,192.168.200.10,192.168.200.50,8.8.8.8;8.8.4.4,security.company.local,secured

---

# Policy Import Template
# Save as: policy_import_template.csv
# Use this template to import security and network policies

policy_name,type,description,scope,status,priority,enforcement,compliance_standard,auto_remediation
Block Malicious IPs,Firewall Rule,Block access to known malicious IP addresses,global,active,95,strict,NIST,true
Password Policy,Password Policy,Enforce strong password requirements,global,active,90,strict,ISO 27001,false
Guest Network Isolation,Network Segmentation,Isolate guest traffic from internal resources,department,active,85,strict,Custom,true
Admin Two-Factor,Access Control,Require 2FA for administrative access,user_group,active,95,strict,GDPR,false
Daily Backup Policy,Backup Policy,Automatic daily backup of critical systems,global,active,80,moderate,HIPAA,true
Software Update Policy,Security Baseline,Ensure all systems have latest security updates,global,active,75,moderate,NIST,true
VPN Access Policy,Access Control,Secure remote access requirements,user_group,active,70,strict,ISO 27001,false
Data Encryption Policy,Security Baseline,Encrypt sensitive data at rest and in transit,global,active,90,strict,GDPR,false
Incident Response Policy,Security Baseline,Procedures for security incident handling,global,active,85,advisory,NIST,false
Network Monitoring Policy,Network Segmentation,Continuous monitoring of network traffic,global,active,75,moderate,Custom,true

---

# Alert Rules Template
# Save as: alert_rules_template.csv
# Use this template to configure custom alert rules

rule_name,condition,severity,action,notification_email,escalation_time,auto_resolve
High CPU Usage,cpu_usage > 90,high,email;snmp_trap,admin@company.com,15,false
Low Disk Space,disk_usage > 95,critical,email;sms,admin@company.com,5,false
Device Offline,ping_failed > 5,medium,email,ops@company.com,10,true
Memory Warning,memory_usage > 85,medium,email,admin@company.com,20,false
High Network Traffic,network_utilization > 90,low,email,network@company.com,30,true
Failed Login Attempts,failed_logins > 5,high,email;disable_account,security@company.com,5,false
Service Down,service_status == down,critical,email;restart_service,admin@company.com,2,true
Temperature Alert,temperature > 80,medium,email,facilities@company.com,15,false
Backup Failure,backup_status == failed,high,email,backup@company.com,10,false
License Expiry,license_days_remaining < 30,low,email,admin@company.com,1440,false