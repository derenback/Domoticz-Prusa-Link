import sys
import types
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import requests

sys.modules.setdefault("Domoticz", types.ModuleType("Domoticz"))

import plugin


class PrintTimeTests(unittest.TestCase):
    def setUp(self):
        self.plugin = plugin.BasePlugin()
        self.devices = {
            unit: Mock()
            for unit in (
                self.plugin.UNIT_TIME_REMAINING,
                self.plugin.UNIT_TIME_ELAPSED,
                self.plugin.UNIT_FINISH_TIME,
            )
        }
        self.devices_patch = patch.object(plugin, "Devices", self.devices, create=True)
        self.devices_patch.start()
        self.addCleanup(self.devices_patch.stop)

    def value(self, unit):
        return self.devices[unit].Update.call_args.kwargs["sValue"]

    def test_times_and_estimated_finish(self):
        status = {"printer": {"state": "PRINTING"}}
        job = {"time_remaining": 3661, "time_printing": 90061}
        with patch.object(plugin.time, "time", return_value=1700000000):
            self.plugin._update_job_times(status, job)
        self.devices[self.plugin.UNIT_TIME_REMAINING].Update.assert_called_once_with(
            nValue=0, sValue="61.02", TimedOut=0
        )
        self.devices[self.plugin.UNIT_TIME_ELAPSED].Update.assert_called_once_with(
            nValue=0, sValue="1501.02", TimedOut=0
        )
        self.assertEqual(
            self.value(self.plugin.UNIT_FINISH_TIME),
            datetime.fromtimestamp(1700003661).strftime("%Y-%m-%d %H:%M"),
        )

    def test_missing_invalid_and_paused_times(self):
        status = {"printer": {"state": "PAUSED"}, "job": {"time_remaining": 0}}
        self.plugin._update_job_times(status, None)
        self.devices[self.plugin.UNIT_TIME_REMAINING].Update.assert_called_once_with(
            nValue=0, sValue="0.00", TimedOut=0
        )
        self.assertEqual(self.devices[self.plugin.UNIT_TIME_ELAPSED].TimedOut, 1)
        self.devices[self.plugin.UNIT_TIME_ELAPSED].Update.assert_not_called()
        self.assertEqual(self.value(self.plugin.UNIT_FINISH_TIME), "Unavailable")

        for device in self.devices.values():
            device.reset_mock()
        self.plugin._update_job_times(
            {"printer": {"state": "PRINTING"}},
            {"time_remaining": -1, "time_printing": None},
        )
        for unit in self.plugin.TIME_UNITS:
            self.devices[unit].Update.assert_not_called()
            self.assertEqual(self.devices[unit].TimedOut, 1)
        self.assertEqual(self.value(self.plugin.UNIT_FINISH_TIME), "Unavailable")

    def test_idle_clears_previous_times(self):
        self.plugin._update_job_times(
            {"printer": {"state": "PRINTING"}},
            {"time_remaining": 30, "time_printing": 60},
        )
        for device in self.devices.values():
            device.reset_mock()
        self.plugin._update_job_times({"printer": {"state": "IDLE"}}, None)
        for unit in self.plugin.TIME_UNITS:
            self.devices[unit].Update.assert_not_called()
            self.assertEqual(self.devices[unit].TimedOut, 1)
        self.assertEqual(self.value(self.plugin.UNIT_FINISH_TIME), "Unavailable")

    def test_device_creation_and_legacy_migration(self):
        created = {}

        def create_device(**kwargs):
            device = Mock()
            device.Create.side_effect = lambda: self.devices.__setitem__(kwargs["Unit"], device)
            created[kwargs["Unit"]] = kwargs
            return device

        legacy = {unit: Mock(TimedOut=0) for unit in self.plugin.LEGACY_TIME_UNITS}
        self.devices.update(legacy)
        for unit in self.plugin.TIME_UNITS:
            del self.devices[unit]
        with patch.object(plugin, "Parameters", {"Mode2": "host", "Mode3": "key", "Mode4": "Off"}, create=True), \
                patch.object(plugin.Domoticz, "Device", side_effect=create_device, create=True), \
                patch.object(plugin.Domoticz, "Log", create=True), \
                patch.object(plugin.Domoticz, "Heartbeat", create=True):
            self.plugin.onStart()
            self.plugin.onStop()
            for unit in self.plugin.TIME_UNITS:
                self.assertEqual(self.devices[unit].TimedOut, 1)
                self.assertEqual(created[unit]["Type"], self.plugin.TYPE_GENERAL)
                self.assertEqual(created[unit]["Subtype"], self.plugin.SUBTYPE_CUSTOM)
                self.assertEqual(created[unit]["Options"], {"Custom": "1;min"})
            for device in legacy.values():
                self.assertEqual(device.TimedOut, 1)
                device.Update.assert_not_called()
            self.assertNotIn(9, created)
            self.assertNotIn(10, created)


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.plugin = plugin.BasePlugin()
        self.plugin.session = Mock()
        self.alert = Mock(nValue=0, sValue="Connected")
        self.devices_patch = patch.object(
            plugin, "Devices", {self.plugin.UNIT_CONNECTION: self.alert}, create=True
        )
        self.devices_patch.start()
        self.addCleanup(self.devices_patch.stop)
        self.log_patch = patch.object(plugin.Domoticz, "Log", create=True)
        self.log = self.log_patch.start()
        self.addCleanup(self.log_patch.stop)

    @staticmethod
    def response(status, data=None):
        response = Mock(status_code=status)
        response.json.return_value = data
        return response

    def test_idle_without_job_is_connected(self):
        self.alert.nValue = 4
        self.alert.sValue = "PrusaLink unavailable"
        self.plugin.session.get.side_effect = [
            self.response(200, {"printer": {"state": "IDLE"}}),
            self.response(204),
        ]
        self.plugin.onHeartbeat()
        self.alert.Update.assert_called_once_with(nValue=0, sValue="Connected")
        self.assertEqual(self.plugin.session.get.call_count, 2)

    def test_timeout_marks_unavailable_and_skips_job(self):
        duration_devices = {unit: Mock(TimedOut=0) for unit in self.plugin.TIME_UNITS}
        plugin.Devices.update(duration_devices)
        self.plugin.session.get.side_effect = requests.exceptions.Timeout("timeout")
        self.plugin.onHeartbeat()
        self.alert.Update.assert_called_once_with(nValue=4, sValue="PrusaLink unavailable")
        self.assertEqual(self.plugin.session.get.call_count, 1)
        for device in duration_devices.values():
            self.assertEqual(device.TimedOut, 1)
            device.Update.assert_not_called()

    def test_connection_recovers_after_failure(self):
        def update(nValue, sValue):
            self.alert.nValue = nValue
            self.alert.sValue = sValue

        self.alert.Update.side_effect = update
        self.plugin.session.get.side_effect = [
            requests.exceptions.ConnectionError("offline"),
            self.response(200, {"printer": {"state": "IDLE"}}),
            self.response(204),
        ]
        self.plugin.onHeartbeat()
        self.assertEqual((self.alert.nValue, self.alert.sValue), (4, "PrusaLink unavailable"))
        self.plugin.onHeartbeat()
        self.assertEqual((self.alert.nValue, self.alert.sValue), (0, "Connected"))

    def test_auth_failure_and_invalid_status_are_unavailable(self):
        for response in (
            self.response(401),
            self.response(200, {}),
            self.response(200, {"printer": {}}),
        ):
            with self.subTest(response=response):
                self.alert.reset_mock()
                self.plugin.session.get.reset_mock()
                self.plugin.session.get.side_effect = None
                self.plugin.session.get.return_value = response
                self.plugin.onHeartbeat()
                self.alert.Update.assert_called_once_with(
                    nValue=4, sValue="PrusaLink unavailable"
                )
                self.assertEqual(self.plugin.session.get.call_count, 1)

    def test_bad_json_is_logged_and_reported(self):
        response = self.response(200)
        response.json.side_effect = ValueError("invalid JSON")
        self.plugin.session.get.return_value = response
        self.plugin.onHeartbeat()
        self.alert.Update.assert_called_once_with(nValue=4, sValue="PrusaLink unavailable")
        self.log.assert_any_call("PRUSALINK Invalid JSON from /api/v1/status: invalid JSON")

    def test_job_failure_does_not_mark_status_endpoint_offline(self):
        self.plugin.session.get.side_effect = [
            self.response(200, {"printer": {"state": "PRINTING"}}),
            self.response(500),
        ]
        self.plugin.onHeartbeat()
        self.alert.Update.assert_not_called()
        self.log.assert_any_call("PRUSALINK Error fetching /api/v1/job: HTTP 500")


if __name__ == "__main__":
    unittest.main()
