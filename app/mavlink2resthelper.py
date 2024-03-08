import math
from typing import Any, Optional

import requests
from loguru import logger


class Mavlink2RestBase:
    """
    Responsible for interfacing with Mavlink2Rest
    This class is supposed to be usecase independant.

    Exception handling: All exceptions are caught and reported over logging. Severity "error", as they should not happen.
    """

    def __init__(self, host: str = "http://127.0.0.1/mavlink2rest", vehicle: int = 1, component: int = 220, get_vehicle: int = 1, get_component: int = 1):
        # store mavlink-url, vehicle and component to access telemetry data from
        self.host = host
        # default own role in mavlink protocol (for sending data)
        self.vehicle = vehicle
        self.component = component  # default for post
        # default for acquiring data (e.g. from flight controller)
        self.get_vehicle = get_vehicle
        self.get_component = get_component
        self.helper_structs = dict()

    def get(self, path: str):
        """
        Helper to request with GET from mavlink2rest
        Returns the response object or None on failure
        """
        full_url = self.host + path
        logger.debug(f"Request url: {full_url}")
        response = None
        try:
            response = requests.get(full_url)
            if response.status_code == 200:
                logger.debug(f"Got response: {response.text}")
                if response.text == "None":
                    return None
                return response.json()
            else:
                logger.error(f"Got HTTP Error: {response.status_code} {response.reason} {response.text}")
                return None
        except Exception as e:
            logger.error(f"Got exception: {e}")
            return None

    def get_helper_struct(self, name: str):
        """
        This abstraction gets a data strcuture from mavlink2rest via the helper-path
        The result is cached.
        """
        if name in self.helper_structs:
            return self.helper_structs[name]
        else:
            helper_struct = self.get(f"/helper/mavlink?name={name}")
            if helper_struct is not None:
                self.helper_structs[name] = helper_struct
                logger.debug(f"Cached helper struct for: {name}")
            else:
                logger.debug(f"Could not cache helper struct for: {name}")
            return helper_struct

    def get_message(self, path: str, vehicle: Optional[int] = None, component: Optional[int] = None) -> Optional[str]:
        """
        Get mavlink data from mavlink2rest
        Uses initialised get_vehicle and get_component as defaults, unless overridden.
        Example: get_message('/VFR_HUD')
        Returns the data or None on failure
        """
        vehicle = vehicle or self.get_vehicle
        component = component or self.get_component
        message_path = f"/mavlink/vehicles/{vehicle}/components/{component}/messages" + path
        return self.get(message_path)

    def get_float(self, path: str, vehicle: Optional[int] = None, component: Optional[int] = None) -> float:
        """
        Get mavlink data from mavlink2rest.
        Uses initialised get_vehicle and get_component as defaults, unless overridden.
        Example: get_float('/VFR_HUD')
        Returns the data as a float (nan on failure)
        """
        response = self.get_message(path, vehicle, component)
        try:
            result = float(response)
        except Exception:
            result = float("nan")
        return result

    def post(self, path: str, json: object) -> bool:
        """
        Helper to request with POST from mavlink2rest
        Returns if request was successful
        """
        full_url = self.host + path
        logger.debug(f"Request url: {full_url} json: {json}")
        response = None
        try:
            response = requests.post(full_url, json=json)
            if response.status_code == 200:
                logger.debug(f"Got response: {response.reason}")
                return True
            else:
                logger.error(f"Got HTTP Error: {response.status_code} {response.reason} {response.text}")
                return False
        except Exception as e:
            logger.error(f"Got exception: {e}")
            return False

    def ensure_message_frequency(self, message_name: str, frequency: int) -> bool:
        """
        Makes sure that a mavlink message is being received at least at "frequency" Hertz
        Returns true if successful, false otherwise
        """
        msg_ids = {
            "VFR_HUD": 74,
            "SCALED_PRESSURE2": 137
        }
        message_name = message_name.upper()

        logger.info(f"Trying to set message frequency of {message_name} to {frequency} Hz")

        previous_frequency = self.get_float(f"/{message_name}/message_information/frequency")
        if math.isnan(previous_frequency):
            previous_frequency = 0.0

        # load message template from mavlink2rest helper
        command = self.get_helper_struct("COMMAND_LONG")
        if command is None:
            return False

        try:
            msg_id = msg_ids[message_name]
            # msg_id = getattr(mavutil.mavlink, 'MAVLINK_MSG_ID_' + message_name)
        except Exception:
            logger.error(f"{message_name} not in internal LUT")
            return False

        command["message"]["command"] = {"type": "MAV_CMD_SET_MESSAGE_INTERVAL"}
        command["message"]["param1"] = msg_id
        command["message"]["param2"] = int(1000 / frequency)

        success = self.post("/mavlink", json=command)
        if success:
            logger.info(f"Successfully set message frequency of {message_name} to {frequency} Hz, was {previous_frequency} Hz")
        return success

    def set_param(self, param_name, param_type, param_value):
        """
        Sets parameter "param_name" of type param_type to value "value" in the autpilot
        Returns True if succesful, False otherwise
        """
        payload = self.get_helper_struct("PARAM_SET")
        if payload is None:
            return False
        try:
            for i, char in enumerate(param_name):
                payload["message"]["param_id"][i] = char

            payload["message"]["param_type"] = {"type": param_type}
            payload["message"]["param_value"] = param_value

            success = self.post("/mavlink", json=payload)
            if success:
                logger.info(f"Successfully set parameter {param_name} to {param_value}")
            return success
        except Exception as error:
            logger.warning(f"Error setting parameter '{param_name}': {error}")
            return False


class Mavlink2RestHelper(Mavlink2RestBase):
    def get_depth(self):
        return -self.get_float('/VFR_HUD/message/alt')

    def get_orientation(self):
        return self.get_float('/VFR_HUD/message/heading')

    def get_temperature(self):
        return self.get_float('/SCALED_PRESSURE2/message/temperature')/100.0

    def send_gps_input(self, global_locator_position: object, acoustic_locator_position: object, args: object, gps_id: int = 0):
        """
        Forwards the locator(ROV) position to mavproxy's GPSInput module
        """
        out_json = self.get_helper_struct("GPS_INPUT")

        try:
            out_json["header"]["system_id"] = self.vehicle
            out_json["header"]["component_id"] = self.component
            out_json["message"]["gps_id"] = gps_id
            out_json["message"]['ignore_flags']['bits'] = 1 | 8 | 16 | 32 | 128

            # fix_quality of GPS and acoustic location quality is independent in API
            # combine them here
            # global_locator_position is None when heading is not set. That should always yield no fix.
            # global_locator_position['fix_quality'] = 1 in demo, = 0 when topside position is set to static. So only look at hdop
            # ignore_gps can override if fix_quality is 0 due to static or external GPS position
            # ignore_acoustic can override position_valid if necessary
            fix_valid = global_locator_position is not None and (global_locator_position['hdop'] < 20 or args.ignore_gps) and \
                        (acoustic_locator_position is not None and acoustic_locator_position['position_valid']) or args.ignore_acoustic

            out_json["message"]['fix_type'] = 3 if fix_valid else 0

            # The Topside GPS has a hdop, the acoustic positioning has a standard deviation in meters.
            # It is not possible to combine them correctly with the provided information.
            out_json["message"]['hdop'] = 65535.0 if global_locator_position is None else global_locator_position['hdop']
            # 300m as maximum range
            out_json["message"]['horiz_accuracy'] = 300 if acoustic_locator_position is None else acoustic_locator_position['std']
            # This is a hack to see the acoustic accuracy in QGC in an easy way.
            # The accuracy is not available in standard telemetry values.
            out_json["message"]['vdop'] = 65535.0 if acoustic_locator_position is None else acoustic_locator_position['std']

            if global_locator_position is not None:
                out_json["message"]['lat'] = math.floor(global_locator_position['lat'] * 1e7)
                out_json["message"]['lon'] = math.floor(global_locator_position['lon'] * 1e7)
                # ignore_gps overrides satellites_visible so that ArduSub will trust the GPS
                out_json["message"]['satellites_visible'] = max(global_locator_position['numsats'], 6 if args.ignore_gps else 0)
                # GPS orientation is forwarded from the received heading /VFR_HUD/message/heading
                if global_locator_position['orientation'] == -1:
                    out_json["message"]['yaw'] = 0  # invalid
                elif global_locator_position['orientation'] == 0:
                    out_json["message"]['yaw'] = 36000  # remap 0 -> 360
                else:
                    out_json["message"]['yaw'] = math.floor(global_locator_position['orientation'] * 100)  # default

        except Exception as e:
            logger.error(f"Parsing locator position not successfull. {e}")
            return

        self.post("/mavlink", out_json)
