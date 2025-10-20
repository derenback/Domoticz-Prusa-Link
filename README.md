# Domoticz Prusa Link Plugin

A Domoticz plugin to monitor Prusa 3D printers via PrusaLink API.

## Features

- Monitor bed temperature and target temperature
- Monitor nozzle temperature and target temperature  
- Track print progress percentage
- Display current filename being printed
- Real-time updates every 5 seconds
- Debug logging support

## Requirements

- Domoticz home automation system
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

## Created Devices

The plugin creates the following devices in Domoticz:

1. **Bed** - Current bed temperature (°C)
2. **Bed Target** - Target bed temperature (°C)  
3. **Nozzle** - Current nozzle temperature (°C)
4. **Nozzle Target** - Target nozzle temperature (°C)
5. **Progress** - Print progress percentage (%)
6. **Filename** - Currently printing filename
7. **Fan hotend** - Hotend fan speed (%)
8. **Fan print** - Print fan speed (%)

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

- **0.0.1** - Initial release
  - Basic temperature monitoring
  - Print progress tracking
  - Filename display


