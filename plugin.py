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
    ip_address = ""
    api_key = ""
    last_filename = ""

    def onStart(self):
        Domoticz.Log("Domoticz Prusa link plugin started")

        self.ip_address = Parameters["Mode2"].strip()
        self.api_key = Parameters["Mode3"].strip()

        if (Parameters["Mode4"] == "Debug"):
            Domoticz.Log("PRUSALINK Debug is On")
            Domoticz.Log(f"PRUSALINK ip_address: {self.ip_address}")

        if 1 not in Devices:
            Domoticz.Device(Name="Bed", Unit=1, Type=80, Subtype=5, Used=1).Create()
        if 2 not in Devices:
            Domoticz.Device(Name="Bed Target", Unit=2, Type=80, Subtype=5, Used=1).Create()
        if 3 not in Devices:
            Domoticz.Device(Name="Nozzle", Unit=3, Type=80, Subtype=5, Used=1).Create()
        if 4 not in Devices:
            Domoticz.Device(Name="Nozzle Target", Unit=4, Type=80, Subtype=5, Used=1).Create()
        if 5 not in Devices:
            Domoticz.Device(Name="Progress", Unit=5, Type=243, Subtype=6, Used=1).Create()
        if 6 not in Devices:
            Domoticz.Device(Name="Filename", Unit=6, Type=243, Subtype=19, Used=1).Create()

        # Just keeping the plugin alive. 
        Domoticz.Heartbeat(5)

    def onStop(self):
        Domoticz.Log("PRUSALINK Stopped")

    def onHeartbeat(self):
        if (Parameters["Mode4"] == "Debug"):
            Domoticz.Log("PRUSALINK Heartbeat")
        session = requests.Session()
        session.headers.update({
            'X-Api-Key': self.api_key,
            'Accept': 'application/json'
        })

        # Get temperature and progress data
        try:
            response = session.get(f"http://{self.ip_address}/api/v1/status", timeout=2)
            if response.status_code == 200:
                data = response.json()
                printer = data.get('printer', {})

                result = {
                    'nozzle_temp': printer.get('temp_nozzle', 0),
                    'nozzle_target': printer.get('target_nozzle', 0),
                    'bed_temp': printer.get('temp_bed', 0),
                    'bed_target': printer.get('target_bed', 0),
                    'status': printer.get('state', 'UNKNOWN')
                }
                
                # Try to get job progress
                try:
                    job_response = session.get(f"http://{self.ip_address}/api/v1/job", timeout=2)
                    if job_response.status_code == 200:
                        job_data = job_response.json()
                        result['progress'] = job_data.get('progress', 0)
                        result['filename'] = job_data.get('file', {}).get('display_name', 'No file')
                    else:
                        result['progress'] = 0
                        result['filename'] = 'No job'
                except Exception as e:
                    Domoticz.Log(f"PRUSALINK Error getting job data: {e}")
                    result['progress'] = 0
                    result['filename'] = 'Unknown'
                
                # Print status in a clean format
                if result:
                    Devices[1].Update(nValue=1, sValue=f"{result['bed_temp']:.1f}")
                    Devices[2].Update(nValue=1, sValue=f"{result['bed_target']:.1f}")
                    Devices[3].Update(nValue=1, sValue=f"{result['nozzle_temp']:.1f}")
                    Devices[4].Update(nValue=1, sValue=f"{result['nozzle_target']:.1f}")
                    Devices[5].Update(nValue=1, sValue=f"{result['progress']:.1f}")
                    if result['filename'] != self.last_filename:
                        Devices[6].Update(nValue=0, sValue=result['filename'])
                        self.last_filename = result['filename']

                    if (Parameters["Mode4"] == "Debug"):
                        Domoticz.Log(f"PRUSALINK Bed: {result['bed_temp']:.1f}°C → {result['bed_target']:.1f}°C")
                        Domoticz.Log(f"PRUSALINK Nozzle: {result['nozzle_temp']:.1f}°C → {result['nozzle_target']:.1f}°C")
                        if result['progress'] > 0:
                            Domoticz.Log(f"PRUSALINK Progress: {result['progress']:.1f}% - {result['filename']}")
                        elif result['filename'] != 'No job':
                            Domoticz.Log(f"PRUSALINK File: {result['filename']}")                        
                else:
                    Domoticz.Log("PRUSALINK No data available")
            else:
                Domoticz.Log("PRUSALINK Failed to get status data")
                
        except Exception as e:
            Domoticz.Log(f"PRUSALINK Error getting data: {e}")
                

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

