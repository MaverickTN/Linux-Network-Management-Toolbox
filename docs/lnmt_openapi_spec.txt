openapi: 3.0.3
info:
  title: LNMT (Linux Network Management Toolkit) API
  description: |
    REST API for the Linux Network Management Toolkit (LNMT) - a comprehensive network management system 
    providing device tracking, VLAN management, DNS services, authentication, backup/restore, and monitoring capabilities.
    
    ## Authentication
    Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:
    `Authorization: Bearer <your-jwt-token>`
    
    ## Rate Limiting
    API requests are rate-limited to prevent abuse. Standard limits apply per authenticated user.
  version: 2.0.0
  contact:
    name: LNMT Support
    url: https://github.com/lnmt/lnmt
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://api.lnmt.local
    description: Production LNMT Server
  - url: http://localhost:8080
    description: Development Server
  - url: https://demo.lnmt.io
    description: Demo Environment

security:
  - BearerAuth: []
  - ApiKeyAuth: []

tags:
  - name: Authentication
    description: User authentication and session management
  - name: Devices
    description: Network device discovery and management
  - name: VLAN
    description: Virtual LAN configuration and management
  - name: DNS
    description: DNS server management and zone configuration
  - name: Reports
    description: System reports and analytics
  - name: Health
    description: System health monitoring and diagnostics
  - name: Backup
    description: Backup and restore operations
  - name: Scheduler
    description: Task scheduling and automation

paths:
  # Authentication Endpoints
  /api/v1/auth/login:
    post:
      tags: [Authentication]
      summary: User login
      description: Authenticate user and receive JWT token
      security: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [username, password]
              properties:
                username:
                  type: string
                  example: admin
                password:
                  type: string
                  format: password
                  example: secretpassword
                remember_me:
                  type: boolean
                  default: false
      responses:
        '200':
          description: Login successful
          content:
            application/json:
              schema:
                type: object
                properties:
                  token:
                    type: string
                    description: JWT authentication token
                  expires_in:
                    type: integer
                    description: Token expiration time in seconds
                  user:
                    $ref: '#/components/schemas/User'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '429':
          $ref: '#/components/responses/RateLimited'

  /api/v1/auth/logout:
    post:
      tags: [Authentication]
      summary: User logout
      description: Invalidate current JWT token
      responses:
        '200':
          description: Logout successful
        '401':
          $ref: '#/components/responses/Unauthorized'

  /api/v1/auth/refresh:
    post:
      tags: [Authentication]
      summary: Refresh JWT token
      description: Get a new JWT token using the refresh token
      responses:
        '200':
          description: Token refreshed successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  token:
                    type: string
                  expires_in:
                    type: integer
        '401':
          $ref: '#/components/responses/Unauthorized'

  /api/v1/auth/user:
    get:
      tags: [Authentication]
      summary: Get current user info
      responses:
        '200':
          description: User information
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '401':
          $ref: '#/components/responses/Unauthorized'

  # Device Management Endpoints
  /api/v1/devices:
    get:
      tags: [Devices]
      summary: List all devices
      description: Retrieve all discovered network devices
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [online, offline, unknown]
          description: Filter by device status
        - name: type
          in: query
          schema:
            type: string
          description: Filter by device type
        - name: vlan
          in: query
          schema:
            type: integer
          description: Filter by VLAN ID
        - name: limit
          in: query
          schema:
            type: integer
            default: 100
            maximum: 1000
        - name: offset
          in: query
          schema:
            type: integer
            default: 0
      responses:
        '200':
          description: List of devices
          content:
            application/json:
              schema:
                type: object
                properties:
                  devices:
                    type: array
                    items:
                      $ref: '#/components/schemas/Device'
                  total:
                    type: integer
                  pagination:
                    $ref: '#/components/schemas/Pagination'

    post:
      tags: [Devices]
      summary: Add new device
      description: Manually add a device to the network inventory
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DeviceCreate'
      responses:
        '201':
          description: Device created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Device'
        '400':
          $ref: '#/components/responses/BadRequest'
        '409':
          description: Device already exists

  /api/v1/devices/{device_id}:
    get:
      tags: [Devices]
      summary: Get device details
      parameters:
        - $ref: '#/components/parameters/DeviceId'
      responses:
        '200':
          description: Device information
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Device'
        '404':
          $ref: '#/components/responses/NotFound'

    put:
      tags: [Devices]
      summary: Update device
      parameters:
        - $ref: '#/components/parameters/DeviceId'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DeviceUpdate'
      responses:
        '200':
          description: Device updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Device'
        '404':
          $ref: '#/components/responses/NotFound'

    delete:
      tags: [Devices]
      summary: Delete device
      parameters:
        - $ref: '#/components/parameters/DeviceId'
      responses:
        '204':
          description: Device deleted successfully
        '404':
          $ref: '#/components/responses/NotFound'

  /api/v1/devices/scan:
    post:
      tags: [Devices]
      summary: Start network scan
      description: Initiate a network discovery scan
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                subnet:
                  type: string
                  example: "192.168.1.0/24"
                  description: Network subnet to scan
                aggressive:
                  type: boolean
                  default: false
                  description: Use aggressive scanning mode
      responses:
        '202':
          description: Scan started
          content:
            application/json:
              schema:
                type: object
                properties:
                  scan_id:
                    type: string
                    format: uuid
                  status:
                    type: string
                    enum: [started, running, completed, failed]

  /api/v1/devices/scan/{scan_id}:
    get:
      tags: [Devices]
      summary: Get scan status
      parameters:
        - name: scan_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Scan status
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ScanStatus'

  # VLAN Management Endpoints
  /api/v1/vlans:
    get:
      tags: [VLAN]
      summary: List all VLANs
      responses:
        '200':
          description: List of VLANs
          content:
            application/json:
              schema:
                type: object
                properties:
                  vlans:
                    type: array
                    items:
                      $ref: '#/components/schemas/VLAN'

    post:
      tags: [VLAN]
      summary: Create new VLAN
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/VLANCreate'
      responses:
        '201':
          description: VLAN created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VLAN'

  /api/v1/vlans/{vlan_id}:
    get:
      tags: [VLAN]
      summary: Get VLAN details
      parameters:
        - name: vlan_id
          in: path
          required: true
          schema:
            type: integer
            minimum: 1
            maximum: 4094
      responses:
        '200':
          description: VLAN information
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VLAN'

    put:
      tags: [VLAN]
      summary: Update VLAN
      parameters:
        - name: vlan_id
          in: path
          required: true
          schema:
            type: integer
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/VLANUpdate'
      responses:
        '200':
          description: VLAN updated successfully

    delete:
      tags: [VLAN]
      summary: Delete VLAN
      parameters:
        - name: vlan_id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '204':
          description: VLAN deleted successfully

  # DNS Management Endpoints
  /api/v1/dns/zones:
    get:
      tags: [DNS]
      summary: List DNS zones
      responses:
        '200':
          description: List of DNS zones
          content:
            application/json:
              schema:
                type: object
                properties:
                  zones:
                    type: array
                    items:
                      $ref: '#/components/schemas/DNSZone'

    post:
      tags: [DNS]
      summary: Create DNS zone
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DNSZoneCreate'
      responses:
        '201':
          description: DNS zone created

  /api/v1/dns/zones/{zone_name}/records:
    get:
      tags: [DNS]
      summary: List DNS records in zone
      parameters:
        - name: zone_name
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: DNS records
          content:
            application/json:
              schema:
                type: object
                properties:
                  records:
                    type: array
                    items:
                      $ref: '#/components/schemas/DNSRecord'

    post:
      tags: [DNS]
      summary: Create DNS record
      parameters:
        - name: zone_name
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DNSRecordCreate'
      responses:
        '201':
          description: DNS record created

  # Reports Endpoints
  /api/v1/reports:
    get:
      tags: [Reports]
      summary: List available reports
      responses:
        '200':
          description: Available reports
          content:
            application/json:
              schema:
                type: object
                properties:
                  reports:
                    type: array
                    items:
                      $ref: '#/components/schemas/ReportMeta'

  /api/v1/reports/{report_type}:
    get:
      tags: [Reports]
      summary: Generate report
      parameters:
        - name: report_type
          in: path
          required: true
          schema:
            type: string
            enum: [network_summary, device_status, vlan_usage, security_audit]
        - name: format
          in: query
          schema:
            type: string
            enum: [json, csv, pdf]
            default: json
        - name: period
          in: query
          schema:
            type: string
            enum: [1h, 24h, 7d, 30d]
            default: 24h
      responses:
        '200':
          description: Generated report
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Report'
            text/csv:
              schema:
                type: string
            application/pdf:
              schema:
                type: string
                format: binary

  # Health Monitoring Endpoints
  /api/v1/health:
    get:
      tags: [Health]
      summary: Get system health status
      security: []
      responses:
        '200':
          description: System health information
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthStatus'

  /api/v1/health/metrics:
    get:
      tags: [Health]
      summary: Get detailed system metrics
      responses:
        '200':
          description: System metrics
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SystemMetrics'

  # Backup/Restore Endpoints
  /api/v1/backup:
    post:
      tags: [Backup]
      summary: Create system backup
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                include_configs:
                  type: boolean
                  default: true
                include_data:
                  type: boolean
                  default: true
                compression:
                  type: boolean
                  default: true
      responses:
        '202':
          description: Backup job started
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                    format: uuid

    get:
      tags: [Backup]
      summary: List backup files
      responses:
        '200':
          description: Available backups
          content:
            application/json:
              schema:
                type: object
                properties:
                  backups:
                    type: array
                    items:
                      $ref: '#/components/schemas/BackupFile'

  /api/v1/backup/{backup_id}/restore:
    post:
      tags: [Backup]
      summary: Restore from backup
      parameters:
        - name: backup_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '202':
          description: Restore job started

  # Scheduler Endpoints
  /api/v1/scheduler/jobs:
    get:
      tags: [Scheduler]
      summary: List scheduled jobs
      responses:
        '200':
          description: Scheduled jobs
          content:
            application/json:
              schema:
                type: object
                properties:
                  jobs:
                    type: array
                    items:
                      $ref: '#/components/schemas/ScheduledJob'

    post:
      tags: [Scheduler]
      summary: Create scheduled job
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ScheduledJobCreate'
      responses:
        '201':
          description: Job scheduled successfully

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

  parameters:
    DeviceId:
      name: device_id
      in: path
      required: true
      schema:
        type: string
        format: uuid
      description: Unique device identifier

  responses:
    BadRequest:
      description: Bad request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    Unauthorized:
      description: Authentication required
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    RateLimited:
      description: Rate limit exceeded
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

  schemas:
    Error:
      type: object
      required: [error, message]
      properties:
        error:
          type: string
          description: Error code
        message:
          type: string
          description: Human-readable error message
        details:
          type: object
          description: Additional error details

    User:
      type: object
      properties:
        id:
          type: string
          format: uuid
        username:
          type: string
        email:
          type: string
          format: email
        role:
          type: string
          enum: [admin, operator, viewer]
        created_at:
          type: string
          format: date-time
        last_login:
          type: string
          format: date-time

    Device:
      type: object
      properties:
        id:
          type: string
          format: uuid
        hostname:
          type: string
        ip_address:
          type: string
          format: ipv4
        mac_address:
          type: string
          pattern: '^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        device_type:
          type: string
          enum: [router, switch, server, workstation, printer, iot, unknown]
        vendor:
          type: string
        model:
          type: string
        os:
          type: string
        status:
          type: string
          enum: [online, offline, unknown]
        vlan_id:
          type: integer
          minimum: 1
          maximum: 4094
        ports:
          type: array
          items:
            $ref: '#/components/schemas/DevicePort'
        last_seen:
          type: string
          format: date-time
        discovered_at:
          type: string
          format: date-time
        tags:
          type: array
          items:
            type: string

    DeviceCreate:
      type: object
      required: [ip_address]
      properties:
        hostname:
          type: string
        ip_address:
          type: string
          format: ipv4
        mac_address:
          type: string
        device_type:
          type: string
        vlan_id:
          type: integer
        tags:
          type: array
          items:
            type: string

    DeviceUpdate:
      type: object
      properties:
        hostname:
          type: string
        device_type:
          type: string
        vlan_id:
          type: integer
        tags:
          type: array
          items:
            type: string

    DevicePort:
      type: object
      properties:
        number:
          type: integer
        name:
          type: string
        status:
          type: string
          enum: [up, down, disabled]
        speed:
          type: string
        duplex:
          type: string
          enum: [full, half, auto]

    VLAN:
      type: object
      properties:
        id:
          type: integer
          minimum: 1
          maximum: 4094
        name:
          type: string
        description:
          type: string
        subnet:
          type: string
          pattern: '^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$'
        gateway:
          type: string
          format: ipv4
        status:
          type: string
          enum: [active, inactive]
        device_count:
          type: integer
        created_at:
          type: string
          format: date-time

    VLANCreate:
      type: object
      required: [id, name]
      properties:
        id:
          type: integer
          minimum: 1
          maximum: 4094
        name:
          type: string
        description:
          type: string
        subnet:
          type: string
        gateway:
          type: string
          format: ipv4

    VLANUpdate:
      type: object
      properties:
        name:
          type: string
        description:
          type: string
        subnet:
          type: string
        gateway:
          type: string
          format: ipv4

    DNSZone:
      type: object
      properties:
        name:
          type: string
        type:
          type: string
          enum: [master, slave, forward]
        serial:
          type: integer
        refresh:
          type: integer
        retry:
          type: integer
        expire:
          type: integer
        minimum:
          type: integer
        record_count:
          type: integer

    DNSZoneCreate:
      type: object
      required: [name, type]
      properties:
        name:
          type: string
        type:
          type: string
          enum: [master, slave, forward]
        master_ip:
          type: string
          format: ipv4

    DNSRecord:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        type:
          type: string
          enum: [A, AAAA, CNAME, MX, NS, PTR, SRV, TXT]
        value:
          type: string
        ttl:
          type: integer
        priority:
          type: integer

    DNSRecordCreate:
      type: object
      required: [name, type, value]
      properties:
        name:
          type: string
        type:
          type: string
          enum: [A, AAAA, CNAME, MX, NS, PTR, SRV, TXT]
        value:
          type: string
        ttl:
          type: integer
          default: 3600
        priority:
          type: integer

    ReportMeta:
      type: object
      properties:
        type:
          type: string
        name:
          type: string
        description:
          type: string
        available_formats:
          type: array
          items:
            type: string

    Report:
      type: object
      properties:
        type:
          type: string
        generated_at:
          type: string
          format: date-time
        period:
          type: string
        data:
          type: object

    HealthStatus:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, degraded, unhealthy]
        timestamp:
          type: string
          format: date-time
        version:
          type: string
        uptime:
          type: integer
        services:
          type: object
          additionalProperties:
            type: object
            properties:
              status:
                type: string
                enum: [running, stopped, error]
              last_check:
                type: string
                format: date-time

    SystemMetrics:
      type: object
      properties:
        cpu_usage:
          type: number
          format: float
        memory_usage:
          type: number
          format: float
        disk_usage:
          type: number
          format: float
        network_io:
          type: object
          properties:
            bytes_sent:
              type: integer
            bytes_received:
              type: integer
        active_connections:
          type: integer
        devices_online:
          type: integer
        devices_total:
          type: integer

    BackupFile:
      type: object
      properties:
        id:
          type: string
          format: uuid
        filename:
          type: string
        size:
          type: integer
        created_at:
          type: string
          format: date-time
        type:
          type: string
          enum: [full, incremental, config_only]
        compressed:
          type: boolean

    ScheduledJob:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        type:
          type: string
          enum: [backup, scan, report, maintenance]
        schedule:
          type: string
          description: Cron expression
        enabled:
          type: boolean
        last_run:
          type: string
          format: date-time
        next_run:
          type: string
          format: date-time
        status:
          type: string
          enum: [active, paused, error]

    ScheduledJobCreate:
      type: object
      required: [name, type, schedule]
      properties:
        name:
          type: string
        description:
          type: string
        type:
          type: string
          enum: [backup, scan, report, maintenance]
        schedule:
          type: string
          description: Cron expression
        enabled:
          type: boolean
          default: true
        parameters:
          type: object

    ScanStatus:
      type: object
      properties:
        id:
          type: string
          format: uuid
        status:
          type: string
          enum: [started, running, completed, failed]
        progress:
          type: integer
          minimum: 0
          maximum: 100
        devices_found:
          type: integer
        started_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
        error_message:
          type: string

    Pagination:
      type: object
      properties:
        limit:
          type: integer
        offset:
          type: integer
        total:
          type: integer
        has_more:
          type: boolean