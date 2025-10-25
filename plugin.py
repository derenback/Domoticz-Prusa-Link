#!/usr/bin/env python
"""
Prusa Link for Domoticz
Author: Derenback
"""
"""
<plugin key="PRUSALINK" name="Prusa-Link" version="0.0.1" author="Derenback">
    <description>
        <h2>PrusaLink plugin</h2><br/>
    </description>
    <params>
        <param field="Mode2" label="IP adress" width="300px" required="true" default="192.168.10.21" />
        <param field="Mode3" label="API key" width="300px" required="true" default="" />
        <param field="Mode4" label="Debug" width="75px">
            <options>
                <option label="On" value="Debug"/>
                <option label="Off" value="Off" default="true" />
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import requests
import json

class BasePlugin:
    # Device configuration: unit -> (name, type, subtype)
    DEVICES = {
        1: ("Bed", 80, 5),
        2: ("Bed Target", 80, 5),
        3: ("Nozzle", 80, 5),
        4: ("Nozzle Target", 80, 5),
        5: ("Progress", 243, 6),
        6: ("Filename", 243, 19),
        7: ("Fan hotend", 243, 7),
        8: ("Fan print", 243, 7),
    }
    
    # API endpoints
    STATUS_ENDPOINT = "/api/v1/status"
    JOB_ENDPOINT = "/api/v1/job"
    
    def __init__(self):
        self.ip_address = ""
        self.api_key = ""
        self.last_filename = ""
        self.session = None
        self.debug = False

    def onStart(self):
        Domoticz.Log("Domoticz Prusa link plugin started")

        self.ip_address = Parameters["Mode2"].strip()
        self.api_key = Parameters["Mode3"].strip()
        self.debug = Parameters["Mode4"] == "Debug"
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': self.api_key,
            'Accept': 'application/json'
        })
        
        if self.debug:
            Domoticz.Log(f"PRUSALINK Debug enabled for IP: {self.ip_address}")
        
        # Create devices
        for unit, (name, type_val, subtype) in self.DEVICES.items():
            if unit not in Devices:
                Domoticz.Device(Name=name, Unit=unit, Type=type_val, Subtype=subtype, Used=1).Create()
        
        Domoticz.Heartbeat(5)

    def onStop(self):
        Domoticz.Log("PRUSALINK Stopped")
        if self.session:
            self.session.close()

    def onHeartbeat(self):
        if self.debug:
            Domoticz.Log("PRUSALINK Heartbeat")
        
        try:
            printer_data = self._fetch_api(self.STATUS_ENDPOINT)
            job_data = self._fetch_api(self.JOB_ENDPOINT)
            
            if printer_data:
                self._update_all_devices(printer_data, job_data)
                
        except Exception as e:
            Domoticz.Log(f"PRUSALINK Error in heartbeat: {e}")

    def _fetch_api(self, endpoint):
        """Fetch data from API endpoint"""
        try:
            response = self.session.get(f"http://{self.ip_address}{endpoint}", timeout=2)
            return response.json() if response.status_code == 200 else None
        except requests.exceptions.RequestException as e:
            Domoticz.Log(f"PRUSALINK Error fetching {endpoint}: {e}")
            return None

    def _update_all_devices(self, status_data, job_data):
        """Update all devices with latest data"""
        if not status_data:
            return
            
        printer = status_data.get('printer', {})
        
        # Temperature devices
        self._update_device(1, printer.get('temp_bed', 0))
        self._update_device(2, printer.get('target_bed', 0))
        self._update_device(3, printer.get('temp_nozzle', 0))
        self._update_device(4, printer.get('target_nozzle', 0))
        
        # Fan devices
        self._update_device(7, printer.get('fan_hotend', 0))
        self._update_device(8, printer.get('fan_print', 0))
        
        # Job devices
        if job_data:
            progress = job_data.get('progress', 0)
            filename = job_data.get('file', {}).get('display_name', 'No file')
            
            # Only update filename when it changes
            if filename != self.last_filename and filename != 'No job':
                Devices[6].Update(nValue=0, sValue=str(filename))
                self.last_filename = filename
                if self.debug:
                    Domoticz.Log(f"PRUSALINK Updated Filename to {filename}")
        else:
            progress = 0

        self._update_device(5, progress)

    def _update_device(self, unit, value):
        """Generic device update method"""
        if unit in Devices:
            Devices[unit].Update(nValue=1, sValue=f"{value:.1f}" if isinstance(value, float) else str(value))
            if self.debug:
                Domoticz.Log(f"PRUSALINK Updated {self.DEVICES[unit][0]} to {value}")

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

