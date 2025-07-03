#!/usr/bin/env python3
"""
Generate LNMT Network Architecture Diagram
Creates a visual representation of LNMT components and their connections
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import numpy as np

def create_network_diagram():
    """Create LNMT network architecture diagram"""
    
    # Create figure and axis
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Title
    ax.text(7, 9.5, 'LNMT Network Architecture', fontsize=20, fontweight='bold', ha='center')
    
    # Color scheme
    colors = {
        'client': '#3498db',
        'web': '#e74c3c',
        'app': '#2ecc71',
        'data': '#f39c12',
        'network': '#9b59b6',
        'external': '#95a5a6'
    }
    
    # Client Layer
    client_box = FancyBboxPatch((0.5, 7), 3, 1.5, 
                                boxstyle="round,pad=0.1",
                                facecolor=colors['client'],
                                edgecolor='black',
                                alpha=0.8)
    ax.add_patch(client_box)
    ax.text(2, 7.75, 'Client Layer', fontsize=12, fontweight='bold', ha='center', color='white')
    ax.text(2, 7.4, 'Web Browsers\nMobile Apps\nAPI Clients', fontsize=9, ha='center', color='white')
    
    # Load Balancer / Reverse Proxy
    lb_box = FancyBboxPatch((5, 7), 4, 1.5,
                            boxstyle="round,pad=0.1",
                            facecolor=colors['web'],
                            edgecolor='black',
                            alpha=0.8)
    ax.add_patch(lb_box)
    ax.text(7, 7.75, 'Nginx/HAProxy', fontsize=12, fontweight='bold', ha='center', color='white')
    ax.text(7, 7.4, 'Load Balancing\nSSL Termination\nRate Limiting', fontsize=9, ha='center', color='white')
    
    # Application Layer
    app_y = 4.5
    
    # Main App
    main_app = FancyBboxPatch((0.5, app_y), 2.5, 1.5,
                              boxstyle="round,pad=0.1",
                              facecolor=colors['app'],
                              edgecolor='black',
                              alpha=0.8)
    ax.add_patch(main_app)
    ax.text(1.75, app_y + 0.75, 'LNMT Core', fontsize=11, fontweight='bold', ha='center')
    ax.text(1.75, app_y + 0.35, 'FastAPI/Flask\nGunicorn/Uvicorn', fontsize=8, ha='center')
    
    # Scheduler
    scheduler = FancyBboxPatch((3.5, app_y), 2.5, 1.5,
                               boxstyle="round,pad=0.1",
                               facecolor=colors['app'],
                               edgecolor='black',
                               alpha=0.8)
    ax.add_patch(scheduler)
    ax.text(4.75, app_y + 0.75, 'Scheduler', fontsize=11, fontweight='bold', ha='center')
    ax.text(4.75, app_y + 0.35, 'APScheduler\nCron Jobs', fontsize=8, ha='center')
    
    # Health Monitor
    health = FancyBboxPatch((6.5, app_y), 2.5, 1.5,
                            boxstyle="round,pad=0.1",
                            facecolor=colors['app'],
                            edgecolor='black',
                            alpha=0.8)
    ax.add_patch(health)
    ax.text(7.75, app_y + 0.75, 'Health Monitor', fontsize=11, fontweight='bold', ha='center')
    ax.text(7.75, app_y + 0.35, 'Device Checks\nAlerts', fontsize=8, ha='center')
    
    # Worker Processes
    workers = FancyBboxPatch((9.5, app_y), 2.5, 1.5,
                             boxstyle="round,pad=0.1",
                             facecolor=colors['app'],
                             edgecolor='black',
                             alpha=0.8)
    ax.add_patch(workers)
    ax.text(10.75, app_y + 0.75, 'Workers', fontsize=11, fontweight='bold', ha='center')
    ax.text(10.75, app_y + 0.35, 'Celery\nBackground Tasks', fontsize=8, ha='center')
    
    # Data Layer
    data_y = 2
    
    # PostgreSQL
    postgres = FancyBboxPatch((0.5, data_y), 2.5, 1.5,
                              boxstyle="round,pad=0.1",
                              facecolor=colors['data'],
                              edgecolor='black',
                              alpha=0.8)
    ax.add_patch(postgres)
    ax.text(1.75, data_y + 0.75, 'PostgreSQL', fontsize=11, fontweight='bold', ha='center')
    ax.text(1.75, data_y + 0.35, 'Primary Database\nPersistent Storage', fontsize=8, ha='center')
    
    # Redis
    redis = FancyBboxPatch((3.5, data_y), 2.5, 1.5,
                           boxstyle="round,pad=0.1",
                           facecolor=colors['data'],
                           edgecolor='black',
                           alpha=0.8)
    ax.add_patch(redis)
    ax.text(4.75, data_y + 0.75, 'Redis', fontsize=11, fontweight='bold', ha='center')
    ax.text(4.75, data_y + 0.35, 'Cache\nSessions\nQueues', fontsize=8, ha='center')
    
    # File Storage
    storage = FancyBboxPatch((6.5, data_y), 2.5, 1.5,
                             boxstyle="round,pad=0.1",
                             facecolor=colors['data'],
                             edgecolor='black',
                             alpha=0.8)
    ax.add_patch(storage)
    ax.text(7.75, data_y + 0.75, 'File Storage', fontsize=11, fontweight='bold', ha='center')
    ax.text(7.75, data_y + 0.35, 'Backups\nConfigs\nReports', fontsize=8, ha='center')
    
    # Network Devices
    network_y = 0.2
    network_box = FancyBboxPatch((0.5, network_y), 8.5, 1.2,
                                 boxstyle="round,pad=0.1",
                                 facecolor=colors['network'],
                                 edgecolor='black',
                                 alpha=0.8)
    ax.add_patch(network_box)
    ax.text(4.75, network_y + 0.6, 'Network Infrastructure', fontsize=12, fontweight='bold', ha='center', color='white')
    ax.text(4.75, network_y + 0.25, 'Switches • Routers • Firewalls • Access Points • Servers', fontsize=9, ha='center', color='white')
    
    # External Services
    ext_box = FancyBboxPatch((10, 0.5), 3.5, 5,
                             boxstyle="round,pad=0.1",
                             facecolor=colors['external'],
                             edgecolor='black',
                             alpha=0.8)
    ax.add_patch(ext_box)
    ax.text(11.75, 4.8, 'External Services', fontsize=11, fontweight='bold', ha='center', color='white')
    
    # External service items
    services = ['SMTP Server', 'LDAP/AD', 'Syslog', 'SNMP Traps', 'Webhook Endpoints', 'Cloud Backup']
    for i, service in enumerate(services):
        ax.text(11.75, 4.2 - i*0.5, service, fontsize=8, ha='center', color='white')
    
    # Connections
    # Client to Load Balancer
    ax.annotate('', xy=(5, 7.75), xytext=(3.5, 7.75),
                arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    
    # Load Balancer to Apps
    for x in [1.75, 4.75, 7.75, 10.75]:
        ax.annotate('', xy=(x, 6), xytext=(7, 7),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='black'))
    
    # Apps to Data Layer
    # Main app to PostgreSQL and Redis
    ax.annotate('', xy=(1.75, 3.5), xytext=(1.75, 4.5),
                arrowprops=dict(arrowstyle='<->', lw=1.5, color='black'))
    ax.annotate('', xy=(4.75, 3.5), xytext=(2.5, 4.5),
                arrowprops=dict(arrowstyle='<->', lw=1.5, color='black'))
    
    # Scheduler to Redis and Storage
    ax.annotate('', xy=(4.75, 3.5), xytext=(4.75, 4.5),
                arrowprops=dict(arrowstyle='<->', lw=1.5, color='black'))
    ax.annotate('', xy=(7.75, 3.5), xytext=(5.5, 4.5),
                arrowprops=dict(arrowstyle='<->', lw=1.5, color='black'))
    
    # Health Monitor to Network
    ax.annotate('', xy=(7.75, 1.4), xytext=(7.75, 4.5),
                arrowprops=dict(arrowstyle='<->', lw=2, color='purple'))
    
    # External connections
    ax.annotate('', xy=(10, 2.5), xytext=(9, 2.5),
                arrowprops=dict(arrowstyle='<->', lw=1.5, color='gray'))
    
    # Protocols and Ports
    ax.text(2, 6.5, 'HTTPS/WSS', fontsize=8, ha='center', style='italic')
    ax.text(7, 3.8, 'TCP/5432', fontsize=7, ha='center', style='italic')
    ax.text(5, 3.8, 'TCP/6379', fontsize=7, ha='center', style='italic')
    ax.text(8, 2.5, 'SNMP/SSH', fontsize=7, ha='center', style='italic')
    
    # Legend
    legend_elements = [
        patches.Patch(color=colors['client'], label='Client Layer'),
        patches.Patch(color=colors['web'], label='Web Layer'),
        patches.Patch(color=colors['app'], label='Application Layer'),
        patches.Patch(color=colors['data'], label='Data Layer'),
        patches.Patch(color=colors['network'], label='Network Devices'),
        patches.Patch(color=colors['external'], label='External Services')
    ]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1), fontsize=9)
    
    # Save the diagram
    plt.tight_layout()
    output_path = '/tmp/lnmt_network_architecture.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"Network architecture diagram saved to: {output_path}")
    
    # Also save as PDF
    pdf_path = '/tmp/lnmt_network_architecture.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"Network architecture diagram (PDF) saved to: {pdf_path}")
    
    plt.close()

if __name__ == "__main__":
    create_network_diagram()