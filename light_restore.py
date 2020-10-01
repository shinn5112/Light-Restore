import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta

# print utilites (thanks geeks for geeks: https://www.geeksforgeeks.org/print-colors-python-terminal/)
def prRed(skk): return("\033[91m{}\033[00m".format(skk)) 
def prGreen(skk): return("\033[92m{}\033[00m".format(skk)) 
def prYellow(skk): return("\033[93m{}\033[00m".format(skk)) 
def prLightPurple(skk): return("\033[94m{}\033[00m".format(skk)) 
def prPurple(skk): return("\033[95m{}\033[00m".format(skk)) 
def prCyan(skk): return("\033[96m{}\033[00m".format(skk)) 
def prLightGray(skk): return("\033[97m{}\033[00m".format(skk)) 
def prBlack(skk): return("\033[98m{}\033[00m".format(skk)) 

class LightRestore(hass.Hass):
    """
    Restore all lights to their last state before HA restarted. Ideal for a situtation where
    you have smart bulbs that do not have a power on behaviour that will come back to an 'on' state
    after a power outage.
    """
    VERSION = '0.2'

    def initialize(self):
        """
        Adds an event listener for HASS startups, launches the right restore function
        when HASS reboots.
        """
        # entities to ignore, defaults to an empty list
        self.log("Light Restore Running: {}".format(self.VERSION))
        if "ignored_entites" in self.args:
            self.ignored = set(self.args["ignored_entites"])
        else:
            self.ignored = set()

        # number of days to grab for the entity history, defaults to 1
        if "days" in self.args:
            self.days = self.args['days']
        else:
            self.days = 1

        # get the sensor entity for how long the server has been up
        if "uptime_sensor" in self.args:
            self.up_time_sensor = self.args["uptime_sensor"]
        else:
            self.up_time_sensor = "sensor.time_online"

        # check a time range if one is provided for night time hours. If there is a range, get it.
        # if the server restarts in this time range, we will just turn everything to an off state.
        self.check_time = False
        if "night_range" in self.args:
            try:
                self.start_time = self.args['night_range']['start_time']
                self.end_time   = self.args['night_range']['end_time']
                self.check_time = True
            except KeyError as e:
                self.log("key missing in settings file: {}".format(str(e)), level="ERROR")

        #  only run once
        self.restore_lights()
        # TODO add switches option?

    def restore_lights(self):
        """
        Finds all lights that are not groups, then restores them to their prior state
        as defined in the history db.
        """
        self.log("Restoring Previous Light States")

        # get light entites
        lights = self.get_state("light")

        # subtract the ignored lights
        lights = tuple(set(lights).difference(self.ignored))

        # find groups
        group = []
        for light in lights:
            current_light_attributes = self.get_state(entity_id=light, attribute="all")["attributes"]
            if "entity_id" in current_light_attributes:
                group.append(light)
                self.log("{} is a group".format(light), level="DEBUG")
            elif "is_hue_group" in current_light_attributes and current_light_attributes["is_hue_group"]:
                group.append(light)
                self.log("{} is a hue group".format(light), level="DEBUG")

        # remove the groups
        lights = tuple(set(lights).difference(set(group)))

        # check to see if we have a nighttime range, if so, forget the states. Turn everything off
        if self.check_time:
            if self.now_is_between(self.start_time, self.end_time):
                self.log("The current time is within the defined night time range, turning all lights off")
                for light in lights:
                    self.turn_off(light)
                    self.log("{:25} => {}".format(light.split(".")[1], prRed("off")))
                return # we are done.
        
        # calculate server start time since we are not within the time range to turn everything off
        current_time = self.datetime(aware=False)  # We do not want tz aware, HA stores entites in times as UTC
        self.log("Current Time: {}".format(current_time))

        hass_up_time = timedelta(seconds=self.calculate_up_time(self.get_state(self.up_time_sensor, attribute='all')))
        server_start_time = current_time - hass_up_time
        self.log("Hass start time: {}".format(server_start_time))
        
        # now get the history of each light, before the server restarted
        light_restore_state = dict()
        for light in lights:
            try:
                # This is a double nested list for some reason. There is only one element in the outer list, so [0] gets the list of states
                light_states = self.get_history(entity_id=light, endtime=server_start_time, days=self.days)[0]
                if len(light_states) < 1:  # if we have not elements, go to the error case
                    raise IndexError()

                self.log(light_states[len(light_states) - 1], level="DEBUG")
                light_restore_state[light] = light_states[len(light_states) - 1]['state']  # get the state of the last entry

                if light_restore_state[light] == 'unavailable':  # if there is no data, assume off
                    light_restore_state[light] = 'off'
            except IndexError: # we have no data for this light at this time, assume an off state
                self.log("could not get state info for '{}', defaulting to off".format(light), level="WARNING")
                light_restore_state[light] = 'off'
        # apply light states
        self.log("Restoring lights to previous states:")
        for light in light_restore_state:
            if light_restore_state[light] == 'on':
                self.turn_on(light)
                self.log("{:25} => {}".format(light.split(".")[1], prGreen(light_restore_state[light])))
            else:
                self.turn_off(light)
                self.log("{:25} => {}".format(light.split(".")[1], prRed(light_restore_state[light])))


    def calculate_up_time(self, up_time_dict: dict) -> int:
        """
        Calculates the uptime in seconds based on the information in the uptime sensor
        attributes dictionary

        :param up_time_dict: the uptime sensor attributes dictionary
        :type up_time_dict: dict
        :returns: The number of seconds HA has been up
        :rtype: int
        """
        unit_of_measurement = up_time_dict['attributes']['unit_of_measurement']
        self.log("Uptime is measured in: {}, converting to seconds".format(unit_of_measurement))
        if unit_of_measurement == "days":
            scale_factor = 86400.0   # 86400 seconds per day
            self.log("Uptime measures in days, this may produce inaccurate results.", level="WARNING")
        if unit_of_measurement == "hours":
            scale_factor = 3600.0    # 3600 seconds per hour
            self.log("Uptime measures in hours, this may produce inaccurate results.", level="WARNING")
        elif unit_of_measurement == "minutes":
            scale_factor = 60.0      # 60 seconds per minute
            self.log("Uptime measures in minutes, this may produce inaccurate results.", level="WARNING")
        else: # seconds
            scale_factor = 1         # 1 seconds per second

        restart_time_offset = round(scale_factor * float(up_time_dict['state']))
        self.log("Calulated start time offest: {} seconds".format(restart_time_offset))
        return restart_time_offset
