#!/usr/bin/env python
"""
Prusa Link for Domoticz
Author: Derenback
"""
"""
<plugin key="PRUSALINK" name="Prusa-Link" version="0.0.2" author="Derenback">
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
import math
import time
from datetime import datetime

class BasePlugin:
    # Domoticz device units
    UNIT_BED = 1
    UNIT_BED_TARGET = 2
    UNIT_NOZZLE = 3
    UNIT_NOZZLE_TARGET = 4
    UNIT_PROGRESS = 5
    UNIT_FILENAME = 6
    UNIT_FAN_HOTEND = 7
    UNIT_FAN_PRINT = 8
    LEGACY_TIME_UNITS = (9, 10)
    UNIT_FINISH_TIME = 11
    UNIT_CONNECTION = 12
    UNIT_TIME_REMAINING = 13
    UNIT_TIME_ELAPSED = 14
    TIME_UNITS = (UNIT_TIME_REMAINING, UNIT_TIME_ELAPSED)

    # Domoticz device types and subtypes
    TYPE_TEMPERATURE = 80
    SUBTYPE_CELSIUS = 5
    TYPE_GENERAL = 243
    SUBTYPE_PERCENTAGE = 6
    SUBTYPE_TEXT = 19
    SUBTYPE_FAN = 7
    SUBTYPE_ALERT = 22
    SUBTYPE_CUSTOM = 31

    HEARTBEAT_SECONDS = 5
    REQUEST_TIMEOUT_SECONDS = 2
    HTTP_OK = 200
    HTTP_NO_CONTENT = 204
    DEVICE_USED = 1
    UPDATE_VALUE = 1
    NO_UPDATE_VALUE = 0
    DEFAULT_SENSOR_VALUE = 0
    NO_FILE = "No file"
    NO_JOB = "No job"
    TIME_UNAVAILABLE = "Unavailable"
    CONNECTION_OK = 0
    CONNECTION_ERROR = 4

    # Device configuration: unit -> (name, type, subtype)
    DEVICES = {
        UNIT_BED: ("Bed", TYPE_TEMPERATURE, SUBTYPE_CELSIUS),
        UNIT_BED_TARGET: ("Bed Target", TYPE_TEMPERATURE, SUBTYPE_CELSIUS),
        UNIT_NOZZLE: ("Nozzle", TYPE_TEMPERATURE, SUBTYPE_CELSIUS),
        UNIT_NOZZLE_TARGET: ("Nozzle Target", TYPE_TEMPERATURE, SUBTYPE_CELSIUS),
        UNIT_PROGRESS: ("Progress", TYPE_GENERAL, SUBTYPE_PERCENTAGE),
        UNIT_FILENAME: ("Filename", TYPE_GENERAL, SUBTYPE_TEXT),
        UNIT_FAN_HOTEND: ("Fan hotend", TYPE_GENERAL, SUBTYPE_FAN),
        UNIT_FAN_PRINT: ("Fan print", TYPE_GENERAL, SUBTYPE_FAN),
        UNIT_TIME_REMAINING: ("Time remaining", TYPE_GENERAL, SUBTYPE_CUSTOM),
        UNIT_TIME_ELAPSED: ("Time elapsed", TYPE_GENERAL, SUBTYPE_CUSTOM),
        UNIT_FINISH_TIME: ("Estimated finish", TYPE_GENERAL, SUBTYPE_TEXT),
        UNIT_CONNECTION: ("Connection", TYPE_GENERAL, SUBTYPE_ALERT),
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
                config = {
                    "Name": name, "Unit": unit, "Type": type_val,
                    "Subtype": subtype, "Used": self.DEVICE_USED,
                }
                if unit in self.TIME_UNITS:
                    config["Options"] = {"Custom": "1;min"}
                Domoticz.Device(**config).Create()
                if unit in self.TIME_UNITS and unit in Devices:
                    Devices[unit].Update(nValue=0, sValue="0.00", TimedOut=0)
            elif unit in self.TIME_UNITS:
                self._mark_device_unavailable(unit)

        for unit in self.LEGACY_TIME_UNITS:
            if unit in Devices:
                self._mark_device_unavailable(unit)
                Domoticz.Log(f"PRUSALINK Legacy time device {unit} is no longer updated; see README for migration")
        
        Domoticz.Heartbeat(self.HEARTBEAT_SECONDS)

    def onStop(self):
        Domoticz.Log("PRUSALINK Stopped")
        if self.session:
            self.session.close()

    def onHeartbeat(self):
        if self.debug:
            Domoticz.Log("PRUSALINK Heartbeat")
        
        try:
            printer_data = self._fetch_api(self.STATUS_ENDPOINT)
            if not isinstance(printer_data, dict) or not isinstance(printer_data.get('printer'), dict) \
                    or not isinstance(printer_data['printer'].get('state'), str) \
                    or not printer_data['printer']['state']:
                if printer_data is not None:
                    Domoticz.Log("PRUSALINK Invalid status response: printer state missing")
                self._update_connection(False)
                self._mark_times_unavailable()
                return

            self._update_connection(True)
            job_data = self._fetch_api(self.JOB_ENDPOINT)
            self._update_all_devices(printer_data, job_data)
                
        except Exception as e:
            Domoticz.Log(f"PRUSALINK Error in heartbeat: {e}")

    def _fetch_api(self, endpoint):
        """Fetch data from API endpoint"""
        try:
            response = self.session.get(
                f"http://{self.ip_address}{endpoint}",
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == self.HTTP_OK:
                return response.json()
            if endpoint == self.JOB_ENDPOINT and response.status_code == self.HTTP_NO_CONTENT:
                return None
            Domoticz.Log(f"PRUSALINK Error fetching {endpoint}: HTTP {response.status_code}")
            return None
        except requests.exceptions.RequestException as e:
            Domoticz.Log(f"PRUSALINK Error fetching {endpoint}: {e}")
            return None
        except ValueError as e:
            Domoticz.Log(f"PRUSALINK Invalid JSON from {endpoint}: {e}")
            return None

    def _update_connection(self, connected):
        value = self.CONNECTION_OK if connected else self.CONNECTION_ERROR
        message = "Connected" if connected else "PrusaLink unavailable"
        if self.UNIT_CONNECTION in Devices:
            device = Devices[self.UNIT_CONNECTION]
            if device.nValue != value or device.sValue != message:
                device.Update(nValue=value, sValue=message)
                Domoticz.Log(f"PRUSALINK {message}")
            else:
                device.Touch()

    def _update_all_devices(self, status_data, job_data):
        """Update all devices with latest data"""
        if not status_data:
            return
            
        printer = status_data.get('printer', {})
        
        # Temperature devices
        self._update_device(self.UNIT_BED, printer.get('temp_bed', self.DEFAULT_SENSOR_VALUE))
        self._update_device(self.UNIT_BED_TARGET, printer.get('target_bed', self.DEFAULT_SENSOR_VALUE))
        self._update_device(self.UNIT_NOZZLE, printer.get('temp_nozzle', self.DEFAULT_SENSOR_VALUE))
        self._update_device(self.UNIT_NOZZLE_TARGET, printer.get('target_nozzle', self.DEFAULT_SENSOR_VALUE))
        
        # Fan devices
        self._update_device(self.UNIT_FAN_HOTEND, printer.get('fan_hotend', self.DEFAULT_SENSOR_VALUE))
        self._update_device(self.UNIT_FAN_PRINT, printer.get('fan_print', self.DEFAULT_SENSOR_VALUE))
        
        # Job devices
        if job_data:
            progress = job_data.get('progress', self.DEFAULT_SENSOR_VALUE)
            filename = job_data.get('file', {}).get('display_name', self.NO_FILE)
            
            if self.UNIT_FILENAME in Devices and filename != self.NO_JOB:
                if filename != self.last_filename:
                    Devices[self.UNIT_FILENAME].Update(nValue=self.NO_UPDATE_VALUE, sValue=str(filename))
                    self.last_filename = filename
                    if self.debug:
                        Domoticz.Log(f"PRUSALINK Updated Filename to {filename}")
                else:
                    Devices[self.UNIT_FILENAME].Touch()
        else:
            progress = self.DEFAULT_SENSOR_VALUE

        self._update_device(self.UNIT_PROGRESS, progress)
        self._update_job_times(status_data, job_data)

    def _update_job_times(self, status_data, job_data):
        status_job = status_data.get('job') or {}
        job = job_data or status_job
        state = status_data.get('printer', {}).get('state')
        if state in ('IDLE', 'READY', 'STOPPED'):
            remaining = elapsed = 0
        else:
            remaining = self._valid_seconds(job.get('time_remaining'))
            elapsed = self._valid_seconds(job.get('time_printing'))

        self._update_duration(self.UNIT_TIME_REMAINING, remaining)
        self._update_duration(self.UNIT_TIME_ELAPSED, elapsed)

        finish = self.TIME_UNAVAILABLE
        if remaining is not None and state == 'PRINTING':
            try:
                finish = datetime.fromtimestamp(time.time() + remaining).strftime('%Y-%m-%d %H:%M')
            except (OverflowError, OSError, ValueError) as e:
                Domoticz.Log(f"PRUSALINK Invalid estimated finish time: {e}")
        self._update_device(self.UNIT_FINISH_TIME, finish)

    @staticmethod
    def _valid_seconds(value):
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
            return int(value)
        return None

    def _mark_times_unavailable(self):
        for unit in self.TIME_UNITS:
            if unit in Devices:
                self._mark_device_unavailable(unit)

    def _mark_device_unavailable(self, unit):
        device = Devices[unit]
        if not device.TimedOut:
            device.Update(
                nValue=device.nValue, sValue=str(device.sValue),
                TimedOut=1, SuppressTriggers=True,
            )

    def _update_duration(self, unit, seconds):
        if unit not in Devices:
            return
        if seconds is None:
            self._mark_device_unavailable(unit)
        else:
            device = Devices[unit]
            value = f"{seconds / 60:.2f}"
            if not device.TimedOut and device.nValue == 0 and device.sValue == value:
                device.Touch()
            else:
                device.Update(nValue=0, sValue=value, TimedOut=0)

    def _update_device(self, unit, value):
        """Generic device update method"""
        if unit in Devices:
            Devices[unit].Update(nValue=self.UPDATE_VALUE, sValue=f"{value:.1f}" if isinstance(value, float) else str(value))
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

