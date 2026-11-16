# Domoticz Prusa Link Plugin

A Domoticz plugin to monitor Prusa 3D printers via PrusaLink API.

## Features

- Monitor bed temperature and target temperature
- Monitor nozzle temperature and target temperature  
- Track print progress percentage
- Display current filename being printed
- Show elapsed time, remaining time and estimated finish time
- Monitor PrusaLink connection availability with a Domoticz alert
- Real-time updates every 5 seconds
- Debug logging support

## Requirements

- Domoticz with support for `SuppressTriggers` on Python device updates
- Prusa 3D printer with PrusaLink enabled
- Python 3.x with `requests` library
- Network access between Domoticz and the printer

## Installation

1. Clone or download this repository to your Domoticz plugins directory:
   ```bash
   cd /path/to/domoticz/plugins/
   git clone https://github.com/derenback/Domoticz-Prusa-Link.git
   ```

2. Restart Domoticz

3. Go to **Setup** → **Hardware** in the Domoticz web interface

4. Add new hardware with type "Prusa-Link"

## Configuration

### Hardware Setup Parameters

- **IP Address**: Enter the IP address of your Prusa printer (default: 192.168.10.21)
- **API Key**: Enter your PrusaLink API key (obtain from printer's web interface)
- **Debug**: Enable/disable debug logging

### Getting the API Key

1. Access your printer's via https://connect.prusa3d.com/
2. Go to the settings page
3. Copy the key to the plugin configuration

## Testing the Connection

Before setting up the plugin in Domoticz, you can test the connection to your printer using the included test script:

```bash
python3 test.py --ip <PRINTER_IP> --api-key <YOUR_API_KEY>
```
Replace `<PRINTER_IP>` and `<YOUR_API_KEY>` with your printer's IP address and API key.

The test script will display:
- Connection status and response codes
- Current printer state (PRINTING, IDLE, STOPPED, etc.)
- Real-time temperature readings (nozzle and bed)
- Fan speeds
- Print progress and filename (if printing)

This helps verify your IP address and API key are correct before configuring the Domoticz plugin.

## Created Devices

The plugin creates the following devices in Domoticz:

1. **Bed** - Current bed temperature (°C)
2. **Bed Target** - Target bed temperature (°C)  
3. **Nozzle** - Current nozzle temperature (°C)
4. **Nozzle Target** - Target nozzle temperature (°C)
5. **Progress** - Print progress percentage (%)
6. **Filename** - Currently printing filename
7. **Fan hotend** - Hotend fan speed (rpm)
8. **Fan print** - Print fan speed (rpm)
11. **Estimated finish** - Estimated local finish date and time
12. **Connection** - Alert: connected or PrusaLink unavailable
13. **Time remaining** - Estimated remaining time (numeric, minutes)
14. **Time elapsed** - Elapsed print time (numeric, minutes)

When the printer is idle, ready or a print is stopped, durations reset to zero.
Unchanged duration and connection readings are refreshed so they do not
become stale. When a duration is unavailable during a job, its numeric device
is marked timed out (red header) and retains its last reading; the value may be
stale and should not be treated as zero. Check the timeout state when using it
in automations. New devices start at zero until the first printer check; this
is a placeholder, not a confirmed reading. Existing readings are marked
unavailable until the first successful check. The finish time is shown as
"Unavailable" unless the printer is printing and provides a remaining time.
It is an estimate and can change during a print.

### Upgrading time devices

The numeric duration sensors use new device units (13 and 14). Previous text
devices (9 and 10) are left in place but marked timed out and no longer
updated. Update dashboards and automations to use the new devices; remove the
old devices in Domoticz only if their history and configuration are no longer
needed.

Domoticz supports custom device icons. Where available, choose a clock icon in
the device's Edit dialog, or upload a custom clock icon. The plugin does not
assign an icon ID because available icons depend on the Domoticz installation.

Connection checks use the printer status endpoint. The alert reports an
unavailable PrusaLink for network, authentication, HTTP or invalid-response
errors; check the Domoticz log for details. An idle printer or an absent job
does not trigger the alert. Configure notifications on the alert device in
Domoticz if desired. Device readings retain their last values while PrusaLink
is unavailable; the duration devices are also marked timed out.

## Usage

Once configured, the plugin will automatically:

- Update temperature readings every 5 seconds
- Monitor print progress
- Display the current print job filename
- Log debug information if enabled

## Troubleshooting

### Common Issues

1. **Connection Failed**: Verify the IP address and network connectivity
2. **Authentication Error**: Check the API key is correct
3. **No Data**: Ensure PrusaLink is enabled on the printer

### Debug Mode

Enable debug mode in the hardware configuration to see detailed logging in the Domoticz log:

- Connection status
- Temperature readings
- Print progress updates
- API response details

## API Endpoints Used

- `/api/v1/status` - Printer status and temperatures
- `/api/v1/job` - Current print job information

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Author

Derenback

## Version History

- **0.0.2** - Improved monitoring and reliability
  - Improve readability
  - Corrected fan speed units

- **0.0.1** - Initial release
  - Basic temperature monitoring
  - Print progress tracking
  - Filename display


