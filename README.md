# Light-Restore
AppDamon app for restoring lights to their state prior to a home assistant restart.

Restore all lights to their last state before HA restarted. Ideal for a situtation where
you have smart bulbs that do not have a power on behaviour that will come back to an 'on' state
after a power outage.

## Installation
Requires the following:
- [AppDaemon](https://appdaemon.readthedocs.io/en/latest/) Addon for Home Assistant
- [Uptime Sensor](https://www.home-assistant.io/integrations/uptime/) defined in you HA instance
- Light states are being logged to the HA history database (done by default unless you told the [recorder integration](https://www.home-assistant.io/integrations/recorder/) to ignore them)

The uptime sensor is used to determine what time range to grab the prior light states for. This will allows the app to grab the light states at a time prior to HA restart.

### Settings
In your apps.yaml file, add the following after placing light_restore.py in your apps directory
```yaml
light_restore:                      # name of the app, can be whatever you want it to be
  module: light_restore             # must be included, name of the Python file without the .py extension
  class: LightRestore               # must be included, name of the Python class that extends hass.Hass
  # settings 
  days: 1                           # optional, defaults to 1
  uptime_sensor: sensor.time_online # optional if your uptime sensor is named 'sensor.time_online'
  ignored_entites:                  # optional, takes a list of entities to be ignored
    - light.configuration_tool_1
  night_range:                      # optional, if included, the keys for 'start_time' and 'end_time' must be included and point to a HH:MM:SS formated string
    start_time: '22:00:00'
    end_time: '07:00:00'

```
