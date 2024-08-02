from typing import Any, Optional

import requests
import time
from loguru import logger


class UgpsConnection:
    """
    Responsible for interfacing with UGPS G2 API

    Exception handling: All exceptions are caught and reported over logging. Severity "error", as they should not happen.
    """

    def __init__(self, host: str = "https://demo.waterlinked.com"):
        # store host
        self.host = host

        # settings of the UGPS Topside: read through API
        self.config_gps_static = False
        self.config_compass_static = False
        self.host_is_demo = "demo" in host

    def get(self, path: str):
        """
        Helper to request with GET from ugps
        Returns the response object or None on failure
        """
        full_url = self.host + path
        logger.debug(f"Request url: {full_url}")
        response = None
        try:
            response = requests.get(full_url, timeout=1)
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

    def put(self, path: str, json: object) -> bool:
        """
        Helper to request with POST from ugps
        Returns if request was successful
        """
        full_url = self.host + path
        logger.debug(f"Request url: {full_url} json: {json}")
        response = None
        try:
            response = requests.put(full_url, json=json, timeout=1)
            if response.status_code == 200:
                logger.debug(f"Got response: {response.reason}")
                return True
            else:
                logger.error(f"Got HTTP Error: {response.status_code} {response.reason} {response.text}")
                return False
        except Exception as e:
            logger.error(f"Got exception: {e}")
            return False

    def wait_for_connection(self):
        """
        Waits until the Underwater GPS system is available
        Returns when it is found
        """
        while True:
            logger.info("Scanning for Water Linked underwater GPS...")
            try:
                requests.get(self.host + "/api/v1/about/", timeout=1)
                break
            except Exception as e:
                logger.debug(f"Got {e}")
            time.sleep(5)
        logger.debug("Got response to about")
        while True:
            if self.fetch_ugps_config(is_init=True):
                break
            time.sleep(5)

    # Specific messages
    def check_position(self, json: object):
        if json is None:
            return None
        if 'lat' not in json or 'lon' not in json or 'orientation' not in json:
            logger.error(f"Position format not valid.")
            return None
        return json

    def get_acoustic_locator_position(self):
        return self.get("/api/v1/position/acoustic/filtered")

    def get_global_locator_position(self):
        return self.check_position(self.get("/api/v1/position/global"))

    def get_ugps_topside_position(self):
        return self.check_position(self.get("/api/v1/position/master"))

    def fetch_ugps_config(self, is_init=False) -> bool:
        """
        Gets configuration from UGPS Topside and updates the state
        is_init: If called from init, the values are always updated.
        returns: True on success
        """
        cfg = self.get("/api/v1/config/generic")
        if cfg is None:
            return False
        try:
            gps_static = cfg["gps"] == "static"
            compass_static = cfg["compass"] == "static"
        except Exception:
            logger.error("UGPS Config format unexpected")
            return False

        if is_init or self.config_gps_static != gps_static or self.config_compass_static != compass_static:
            logger.info(f"Updating configuration to gps_static={gps_static} compass_static={compass_static}")
            self.config_gps_static = gps_static
            self.config_compass_static = compass_static
        return True


    def send_locator_depth_temperature(self, depth: float, temperature: float):
        json = {}
        json['depth'] = depth
        json['temp'] = temperature
        return self.put("/api/v1/external/depth", json)

    def send_locator_orientation(self, orientation: int):
        json = {}
        # ensure value range 0-359 degrees
        json['orientation'] = orientation % 360
        return self.put("/api/v1/external/orientation", json)
