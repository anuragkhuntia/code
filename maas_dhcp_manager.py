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
import time
import random
import string
from datetime import datetime

# Disable SSL warnings since we use verify=False
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
        
        if not self.maas_url or not self.api_key or self.maas_url == "http://maas.example.com:5240":
            print("ERROR: MAAS URL or API key not configured")
            print("Edit MAAS_URL and MAAS_API_KEY constants at the top of the script")
    
    def _get_headers(self):
        """Get headers for MAAS API requests using OAuth PLAINTEXT"""
        # Parse API key in format: consumer_key:token:secret
        parts = self.api_key.split(':')
        if len(parts) != 3:
            print(f"ERROR: API key must be in format 'consumer_key:token:secret'")
            print(f"ERROR: Got {len(parts)} parts instead of 3")
            return {}
        
        consumer_key, token, secret = parts
        
        # Build OAuth parameters (including timestamp and nonce for MAAS 3.x)
        oauth_params = {
            "oauth_consumer_key": consumer_key,
            "oauth_token": token,
            "oauth_signature_method": "PLAINTEXT",
            "oauth_signature": f"&{secret}",
            "oauth_timestamp": str(int(time.time())),
            "oauth_nonce": ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
            "oauth_version": "1.0"
        }
        
        # Build OAuth header
        auth_header = "OAuth " + ", ".join(f'{k}="{v}"' for k, v in oauth_params.items())
        
        return {
            'Authorization': auth_header,
            'Accept': 'application/json'
        }
    
    def _maas_api_call(self, endpoint, method='GET', data=None):
        """
        Make a call to MAAS API
        
        Args:
            endpoint: API endpoint (e.g., '/MAAS/api/2.0/dhcp-snippets/')
            method: HTTP method
            data: Request data for POST/PUT
        """
        if not self.maas_url or not self.api_key:
            print("ERROR: MAAS API credentials not provided")
            return None
        
        url = f"{self.maas_url.rstrip('/')}{endpoint}"
        headers = self._get_headers()
        
        print(f"→ {method} {url}")
        
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
            
            if response.status_code in [200, 201, 202, 204]:
                print(f"✓ Success ({response.status_code})")
                return response.json() if response.content else {}
            else:
                print(f"✗ Error {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Request failed: {e}")
            return None
    
    def list_leases(self, output_format='table'):
        """
        List all DHCP leases from MAAS API
        
        Args:
            output_format: 'table', 'json', or 'raw'
        """
        print(f"Fetching DHCP leases from MAAS...")
        
        # Get DHCP leases from MAAS
        result = self._maas_api_call('/MAAS/api/2.0/dhcp-snippets/')
        
        if result is None:
            return []
        
        leases = []
        for item in result:
            # Keep all fields from the API response
            lease = {
                'lease_name': item.get('lease_name', item.get('hostname', 'N/A')),
                'ip_address': item.get('ip', 'N/A'),
                'mac_address': item.get('mac', 'N/A'),
                'hostname': item.get('hostname', 'N/A'),
                'lease_time': item.get('lease_time_seconds', 'N/A')
            }
            # Add all other fields from the response
            for key, value in item.items():
                if key not in ['ip', 'mac', 'hostname', 'lease_time_seconds']:
                    lease[key] = value
            leases.append(lease)
        
        if output_format == 'json':
            print(json.dumps(leases, indent=2))
        elif output_format == 'raw':
            print(json.dumps(result, indent=2))
        else:
            self._print_leases_table(leases)
        
        return leases
    
    def _print_leases_table(self, leases):
        """Print leases in detailed format"""
        if not leases:
            print("No leases found.")
            return
        
        print(f"\nTotal leases: {len(leases)}\n")
        
        for idx, lease in enumerate(leases, 1):
            print("=" * 80)
            print(f"Lease #{idx}: {lease.get('lease_name', lease.get('hostname', 'Unnamed'))}")
            print("=" * 80)
            print(f"  IP Address:       {lease.get('ip_address', 'N/A')}")
            print(f"  MAC Address:      {lease.get('mac_address', 'N/A')}")
            print(f"  Hostname:         {lease.get('hostname', 'N/A')}")
            print(f"  Lease Time:       {lease.get('lease_time', 'N/A')} seconds")
            
            # Show all other fields from the API response
            for key, value in lease.items():
                if key not in ['lease_name', 'ip_address', 'mac_address', 'hostname', 'lease_time']:
                    print(f"  {key.replace('_', ' ').title():<17} {value}")
            print()
        
        print("=" * 80)
    
    def delete_lease(self, identifier, identifier_type='ip'):
        """
        Delete a specific lease by IP or MAC address via MAAS API
        
        Args:
            identifier: IP address or MAC address to delete
            identifier_type: 'ip' or 'mac'
        """
        # First, find the lease
        result = self._maas_api_call('/MAAS/api/2.0/dhcp-snippets/')
        
        if result is None:
            return False
        
        lease_id = None
        for item in result:
            if identifier_type == 'ip' and item.get('ip') == identifier:
                lease_id = item.get('id')
                break
            elif identifier_type == 'mac' and item.get('mac', '').lower() == identifier.lower():
                lease_id = item.get('id')
                break
        
        if not lease_id:
            print(f"Lease not found for {identifier}")
            return False
        
        # Delete the lease
        delete_result = self._maas_api_call(f'/MAAS/api/2.0/dhcp-snippets/{lease_id}/', method='DELETE')
        
        if delete_result is not None:
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
        
        # Create DHCP lease in MAAS
        data = {
            'ip': ip,
            'mac': mac,
            'hostname': hostname or '',
            'lease_name': hostname or ''  # Use hostname as lease_name if not provided separately
        }
        
        result = self._maas_api_call('/MAAS/api/2.0/dhcp-snippets/', method='POST', data=data)
        
        if result:
            print(f"Successfully added lease for {ip} ({mac})")
            return True
        return False
    
    def update_lease(self, snippet_name, ip, mac, hostname):
        """
        Update a DHCP snippet by appending lease configuration
        
        Args:
            snippet_name: Name of the DHCP snippet to update
            ip: IP address for the lease
            mac: MAC address for the lease
            hostname: Hostname for the lease
        """
        # Construct the lease string
        lease_string = f"host {hostname} {{ hardware ethernet {mac}; fixed-address {ip}; }}"
        
        # Update the snippet - append the lease string to the snippet's value
        data = {
            'name': snippet_name,
            'value': lease_string
        }
        
        update_result = self._maas_api_call(f'/MAAS/api/2.0/dhcp-snippets/{snippet_name}/', method='PUT', data=data)
        
        if update_result is not None:
            print(f"Successfully updated snippet '{snippet_name}' with lease for {hostname} ({ip})")
            return True
        return False
    
    def update_from_csv(self, csv_file):
        """
        Update DHCP snippets from a CSV file
        
        Args:
            csv_file: Path to CSV file with columns: lease_name, ip, mac, hostname
        """
        if not os.path.exists(csv_file):
            print(f"Error: CSV file not found: {csv_file}")
            return False
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                
                # Check required columns
                required = ['lease_name', 'ip', 'mac']
                if not all(col in reader.fieldnames for col in required):
                    print(f"Error: CSV must contain columns: {', '.join(required)}")
                    print(f"Found columns: {', '.join(reader.fieldnames)}")
                    return False
                
                success_count = 0
                fail_count = 0
                
                for row_num, row in enumerate(reader, start=2):
                    lease_name = row.get('lease_name', '').strip()
                    ip = row.get('ip', '').strip()
                    mac = row.get('mac', '').strip()
                    hostname = row.get('hostname', '').strip()
                    
                    if not lease_name or not ip or not mac:
                        print(f"Row {row_num}: Skipping - missing lease_name, ip, or mac")
                        fail_count += 1
                        continue
                    
                    # Use lease_name as hostname if hostname not provided
                    if not hostname:
                        hostname = lease_name
                    
                    print(f"Row {row_num}: Updating snippet '{lease_name}' with {hostname} ({ip})")
                    
                    if self.update_lease(lease_name, ip, mac, hostname):
                        success_count += 1
                    else:
                        fail_count += 1
                
                print(f"\nCompleted: {success_count} snippets updated, {fail_count} failed")
                return success_count > 0
                
        except Exception as e:
            print(f"Error reading CSV file: {e}")
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
                
                for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                    ip = row.get('ip', '').strip()
                    mac = row.get('mac', '').strip()
                    hostname = row.get('hostname', '').strip() or None
                    lease_name = row.get('lease_name', '').strip() or None
                    
                    if not ip or not mac:
                        print(f"Row {row_num}: Skipping - missing ip or mac")
                        fail_count += 1
                        continue
                    
                    # Use lease_name as hostname if hostname is not provided
                    if not hostname and lease_name:
                        hostname = lease_name
                    
                    # Use hostname as lease_name if lease_name is not provided
                    if not lease_name and hostname:
                        lease_name = hostname
                    
                    print(f"Row {row_num}: Adding lease '{lease_name}' - {ip} ({mac}) - {hostname or 'no hostname'}")
                    
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
  
  # Update DHCP snippet from CSV file (lease_name is snippet name)
  python maas_dhcp_manager.py update --file leases.csv
  
  # Append a new lease entry with IP, MAC, and hostname
  python maas_dhcp_manager.py append --ip 192.168.1.50 --mac 00:aa:bb:cc:dd:ee --hostname server-1
  
  # Append multiple leases from CSV file
  python maas_dhcp_manager.py append --file leases.csv
  
  # Override config with command-line credentials
  python maas_dhcp_manager.py list --maas-url http://other.maas.com:5240 --api-key OTHER_KEY
        """
    )
    
    parser.add_argument('action', 
                       choices=['list', 'delete', 'append', 'update'],
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
    
    elif args.action == 'update':
        if args.file:
            manager.update_from_csv(args.file)
        else:
            print("Error: Update action requires --file with CSV")
            print("CSV format: lease_name, ip, mac, hostname")
    
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
