#!/usr/bin/env python3
import requests
import argparse
from datetime import datetime

def fetch_api(session, base_url, endpoint):
    """Fetch data from API endpoint"""
    try:
        response = session.get(f"{base_url}{endpoint}", timeout=5)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return None

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Test Prusa Link API')
    parser.add_argument('--ip', required=True, help='Printer IP address')
    parser.add_argument('--api-key', required=True, help='API key for authentication')
    args = parser.parse_args()
    
    base_url = f"http://{args.ip}"
    
    # Setup session
    session = requests.Session()
    session.headers.update({
        'X-Api-Key': args.api_key,
        'Accept': 'application/json'
    })

    # Fetch data
    status_data = fetch_api(session, base_url, "/api/v1/status")
    job_data = fetch_api(session, base_url, "/api/v1/job")
    
    if not status_data:
        print("Failed to get status data")
        return

    # Extract printer data
    printer = status_data.get('printer', {})
    
    if status_data:
        print("Status data:", status_data)
    if job_data:
        print("Job data:", job_data)
    print()
    
    # Display formatted output
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {printer.get('state', 'UNKNOWN')}")
    print(f"  Nozzle: {printer.get('temp_nozzle', 0):.1f}°C → {printer.get('target_nozzle', 0):.1f}°C")
    print(f"  Bed:    {printer.get('temp_bed', 0):.1f}°C → {printer.get('target_bed', 0):.1f}°C")
    print(f"  Fan Hotend: {printer.get('fan_hotend', 0)}%")
    print(f"  Fan Print:  {printer.get('fan_print', 0)}%")
    
    # Display job info if available
    if job_data:
        progress = job_data.get('progress', 0)
        filename = job_data.get('file', {}).get('display_name', 'No file')
        
        if progress > 0:
            print(f"  Progress: {progress:.1f}% - {filename}")
        elif filename != 'No file':
            print(f"  File: {filename}")

if __name__ == "__main__":
    main()