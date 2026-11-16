import sys
import types
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

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
        self.assertEqual(self.value(self.plugin.UNIT_TIME_REMAINING), "1:01:01")
        self.assertEqual(self.value(self.plugin.UNIT_TIME_ELAPSED), "25:01:01")
        self.assertEqual(
            self.value(self.plugin.UNIT_FINISH_TIME),
            datetime.fromtimestamp(1700003661).strftime("%Y-%m-%d %H:%M"),
        )

    def test_missing_invalid_and_paused_times(self):
        status = {"printer": {"state": "PAUSED"}, "job": {"time_remaining": 0}}
        self.plugin._update_job_times(status, None)
        self.assertEqual(self.value(self.plugin.UNIT_TIME_REMAINING), "0:00:00")
        self.assertEqual(self.value(self.plugin.UNIT_TIME_ELAPSED), "Unavailable")
        self.assertEqual(self.value(self.plugin.UNIT_FINISH_TIME), "Unavailable")

        self.plugin._update_job_times(
            {"printer": {"state": "PRINTING"}},
            {"time_remaining": -1, "time_printing": None},
        )
        for unit in self.devices:
            self.assertEqual(self.value(unit), "Unavailable")

    def test_idle_clears_previous_times(self):
        self.plugin._update_job_times(
            {"printer": {"state": "PRINTING"}},
            {"time_remaining": 30, "time_printing": 60},
        )
        self.plugin._update_job_times({"printer": {"state": "IDLE"}}, None)
        for unit in self.devices:
            self.assertEqual(self.value(unit), "Unavailable")


if __name__ == "__main__":
    unittest.main()
