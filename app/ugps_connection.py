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

    # Specific messages
    def check_position(self, json: object) -> bool:
        if json is None:
            return None
        if 'lat' not in json or 'lon' not in json or 'orientation' not in json:
            logger.error(f"Position format not valid.")
            return None
        else:
            return json

    def get_acoustic_locator_position(self):
        return self.get("/api/v1/position/acoustic/filtered")

    def get_global_locator_position(self):
        return self.check_position(self.get("/api/v1/position/global"))

    def get_ugps_topside_position(self):
        return self.check_position(self.get("/api/v1/position/master"))

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
