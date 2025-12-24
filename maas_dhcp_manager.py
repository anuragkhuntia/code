#!/usr/bin/env python3
"""
MAAS DHCP Lease Manager
Manages DHCP leases in MAAS (Metal as a Service) via API
"""

import os
import json
import csv
import argparse
import requests
from datetime import datetime


# =============================================================================
# CONFIGURATION - Set your MAAS credentials here
# =============================================================================
MAAS_URL = "http://maas.example.com:5240"  # Your MAAS server URL
MAAS_API_KEY = "YOUR_API_KEY_HERE"         # Your MAAS API key
# =============================================================================


class MAASLeaseManager:
    """Manager for MAAS DHCP leases via API"""
    
    def __init__(self, maas_url=None, api_key=None):
        """
        Initialize the manager with MAAS API credentials
        
        Args:
            maas_url: MAAS server URL (e.g., http://maas.example.com:5240)
            api_key: MAAS API key for authentication
        """
        # Use command-line args or hardcoded constants
        self.maas_url = maas_url or MAAS_URL
        self.api_key = api_key or MAAS_API_KEY
        
        print(f"[DEBUG] Initialized with MAAS URL: {self.maas_url}")
        print(f"[DEBUG] API Key format: {self.api_key[:20]}..." if self.api_key else "[DEBUG] No API Key")
        
        if not self.maas_url or not self.api_key or self.maas_url == "http://maas.example.com:5240":
            print("ERROR: MAAS URL or API key not configured")
            print("Edit MAAS_URL and MAAS_API_KEY constants at the top of the script")
    
    def _get_headers(self):
        """Get headers for MAAS API requests"""
        # Parse API key in format: consumer_key:token:secret
        parts = self.api_key.split(':')
        if len(parts) != 3:
            print(f"[ERROR] API key must be in format 'consumer_key:token:secret'")
            print(f"[ERROR] Got {len(parts)} parts instead of 3")
            return {}
        
        consumer_key, token, secret = parts
        
        # Build OAuth header matching curl format
        auth_header = (
            f'OAuth oauth_version="1.0", '
            f'oauth_signature_method="PLAINTEXT", '
            f'oauth_consumer_key="{consumer_key}", '
            f'oauth_token="{token}", '
            f'oauth_signature="&{secret}"'
        )
        
        print(f"[DEBUG] Building OAuth header with consumer_key: {consumer_key[:10]}...")
        
        return {
            'Authorization': auth_header,
            'Accept': 'application/json'
        }
    
    def _maas_api_call(self, endpoint, method='GET', data=None):
        """
        Make a call to MAAS API
        
        Args:
            endpoint: API endpoint (e.g., '/MAAS/api/2.0/ipaddresses/')
            method: HTTP method
            data: Request data for POST/PUT
        """
        if not self.maas_url or not self.api_key:
            print("ERROR: MAAS API credentials not provided")
            return None
        
        url = f"{self.maas_url.rstrip('/')}{endpoint}"
        headers = self._get_headers()
        
        print(f"\n[DEBUG] ========== API CALL ==========")
        print(f"[DEBUG] Method: {method}")
        print(f"[DEBUG] Full URL: {url}")
        print(f"[DEBUG] Headers:")
        for key, value in headers.items():
            if key == 'Authorization':
                print(f"[DEBUG]   {key}: {value[:50]}...")
            else:
                print(f"[DEBUG]   {key}: {value}")
        if data:
            print(f"[DEBUG] Data: {data}")
        print(f"[DEBUG] ==================================\n")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, verify=False)
            elif method == 'POST':
                response = requests.post(url, headers=headers, data=data, verify=False)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, data=data, verify=False)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, verify=False)
            else:
                print(f"ERROR: Unsupported HTTP method {method}")
                return None
            
            print(f"[DEBUG] Response Status: {response.status_code}")
            print(f"[DEBUG] Response Headers: {dict(response.headers)}")
            
            if response.status_code in [200, 201, 202, 204]:
                print(f"[DEBUG] Success! Response length: {len(response.content)} bytes")
                return response.json() if response.content else {}
            else:
                print(f"[ERROR] API Error: {response.status_code}")
                print(f"[ERROR] Response Text: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request Exception: {e}")
            return None
    
    def list_leases(self, output_format='table'):
        """
        List all DHCP leases from MAAS API
        
        Args:
            output_format: 'table', 'json', or 'raw'
        """
        print(f"Fetching leases from MAAS API: {self.maas_url}")
        
        # Get IP addresses from MAAS
        result = self._maas_api_call('/MAAS/api/2.0/ipaddresses/')
        
        if result is None:
            return []
        
        leases = []
        for item in result:
            if item.get('alloc_type') in [1, 4, 5]:  # AUTO, DHCP, DISCOVERED
                lease = {
                    'ip_address': item.get('ip', 'N/A'),
                    'mac_address': item.get('mac_address', 'N/A'),
                    'hostname': item.get('hostname', 'N/A'),
                    'alloc_type': item.get('alloc_type_name', 'N/A'),
                    'resource': item.get('resource_uri', '')
                }
                leases.append(lease)
        
        if output_format == 'json':
            print(json.dumps(leases, indent=2))
        elif output_format == 'raw':
            print(json.dumps(result, indent=2))
        else:
            self._print_leases_table(leases)
        
        return leases
    
    def _print_leases_table(self, leases):
        """Print leases in table format"""
        if not leases:
            print("No leases found.")
            return
        
        print(f"\nTotal leases: {len(leases)}\n")
        print("-" * 100)
        print(f"{'IP Address':<16} {'MAC Address':<20} {'Hostname':<25} {'Status':<15}")
        print("-" * 100)
        
        for lease in leases:
            ip = lease.get('ip_address', 'N/A')
            mac = lease.get('mac_address', 'N/A')
            hostname = lease.get('hostname', 'N/A')
            status = lease.get('alloc_type', lease.get('ends', lease.get('timestamp', 'N/A')))
            print(f"{ip:<16} {mac:<20} {hostname:<25} {status:<15}")
        
        print("-" * 100)
    
    def delete_lease(self, identifier, identifier_type='ip'):
        """
        Delete a specific lease by IP or MAC address via MAAS API
        
        Args:
            identifier: IP address or MAC address to delete
            identifier_type: 'ip' or 'mac'
        """
        # First, find the lease
        result = self._maas_api_call('/MAAS/api/2.0/ipaddresses/')
        
        if result is None:
            return False
        
        resource_uri = None
        for item in result:
            if identifier_type == 'ip' and item.get('ip') == identifier:
                resource_uri = item.get('resource_uri')
                break
            elif identifier_type == 'mac' and item.get('mac_address', '').lower() == identifier.lower():
                resource_uri = item.get('resource_uri')
                break
        
        if not resource_uri:
            print(f"Lease not found for {identifier}")
            return False
        
        # Release the IP
        release_result = self._maas_api_call(f"{resource_uri}?op=release", method='POST')
        
        if release_result is not None:
            print(f"Successfully deleted lease for {identifier}")
            return True
        return False
    
    def append_lease(self, ip=None, mac=None, hostname=None):
        """
        Append a lease entry via MAAS API
        
        Args:
            ip: IP address for the new lease
            mac: MAC address for the new lease
            hostname: Hostname for the new lease
        """
        if not ip or not mac:
            print("Error: Must provide both ip and mac")
            return False
        
        # Reserve IP address in MAAS
        data = {
            'ip': ip,
            'mac': mac,
            'hostname': hostname or ''
        }
        
        result = self._maas_api_call('/MAAS/api/2.0/ipaddresses/?op=reserve', method='POST', data=data)
        
        if result:
            print(f"Successfully added lease for {ip} ({mac})")
            return True
        return False
    
    def append_from_csv(self, csv_file):
        """
        Append multiple leases from a CSV file
        
        Args:
            csv_file: Path to CSV file with columns: lease_name, ip, mac, hostname
        """
        if not os.path.exists(csv_file):
            print(f"Error: CSV file not found: {csv_file}")
            return False
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                
                # Validate required columns
                required = ['ip', 'mac']
                if not all(col in reader.fieldnames for col in required):
                    print(f"Error: CSV must contain columns: {', '.join(required)}")
                    print(f"Found columns: {', '.join(reader.fieldnames)}")
                    return False
                
                success_count = 0
                fail_count = 0
                
                print("Starting bulk append operation...")
                
                for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                    ip = row.get('ip', '').strip()
                    mac = row.get('mac', '').strip()
                    hostname = row.get('hostname', '').strip() or None
                    lease_name = row.get('lease_name', '').strip()
                    
                    if not ip or not mac:
                        print(f"Row {row_num}: Skipping - missing ip or mac")
                        fail_count += 1
                        continue
                    
                    # Use lease_name as hostname if hostname is not provided
                    if not hostname and lease_name:
                        hostname = lease_name
                    
                    print(f"Row {row_num}: Adding lease {ip} ({mac}) - {hostname or 'no hostname'}")
                    
                    if self.append_lease(ip=ip, mac=mac, hostname=hostname):
                        success_count += 1
                    else:
                        fail_count += 1
                
                print(f"\nCompleted: {success_count} leases added, {fail_count} failed")
                return success_count > 0
                
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='MAAS DHCP Lease Manager - Manage DHCP leases via MAAS API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration:
  Edit MAAS_URL and MAAS_API_KEY constants at the top of the script.
  API Key format must be: consumer_key:token:secret (three parts separated by colons)
  
  Optionally override with command-line: --maas-url and --api-key

Examples:
  # List all leases
  python maas_dhcp_manager.py list
  
  # List leases in JSON format
  python maas_dhcp_manager.py list --format json
  
  # Delete lease by IP address
  python maas_dhcp_manager.py delete --ip 192.168.1.100
  
  # Delete lease by MAC address
  python maas_dhcp_manager.py delete --mac 00:11:22:33:44:55
  
  # Append a new lease entry with IP, MAC, and hostname
  python maas_dhcp_manager.py append --ip 192.168.1.50 --mac 00:aa:bb:cc:dd:ee --hostname server-1
  
  # Append multiple leases from CSV file
  python maas_dhcp_manager.py append --file leases.csv
  
  # Override config with command-line credentials
  python maas_dhcp_manager.py list --maas-url http://other.maas.com:5240 --api-key OTHER_KEY
        """
    )
    
    parser.add_argument('action', 
                       choices=['list', 'delete', 'append'],
                       help='Action to perform')
    
    parser.add_argument('--maas-url', 
                       help='MAAS server URL (e.g., http://maas.example.com:5240)')
    
    parser.add_argument('--api-key', 
                       help='MAAS API key for authentication')
    
    parser.add_argument('--format', 
                       choices=['table', 'json', 'raw'],
                       default='table',
                       help='Output format for list command')
    
    parser.add_argument('--ip', 
                       help='IP address of the lease')
    
    parser.add_argument('--mac', 
                       help='MAC address of the lease')
    
    parser.add_argument('--hostname', 
                       help='Hostname to set/update')
    
    parser.add_argument('--file', 
                       help='CSV file with lease data (columns: lease_name, ip, mac, hostname)')
    
    args = parser.parse_args()
    
    manager = MAASLeaseManager(
        maas_url=args.maas_url,
        api_key=args.api_key
    )
    
    if args.action == 'list':
        manager.list_leases(output_format=args.format)
    
    elif args.action == 'delete':
        if args.ip:
            manager.delete_lease(args.ip, identifier_type='ip')
        elif args.mac:
            manager.delete_lease(args.mac, identifier_type='mac')
        else:
            print("Error: Must specify --ip or --mac for delete action")
    
    elif args.action == 'append':
        if args.file:
            manager.append_from_csv(args.file)
        elif args.ip and args.mac:
            manager.append_lease(ip=args.ip, mac=args.mac, hostname=args.hostname)
        else:
            print("Error: For append action, specify either:")
            print("  - --file with CSV file path")
            print("  - --ip and --mac (with optional --hostname)")


if __name__ == '__main__':
    main()
