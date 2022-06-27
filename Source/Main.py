from abc import abstractmethod
from pathlib import Path
from enum import Enum
import configparser
import requests
import logging
import json
import copy
import os


PROJECT_PATH = Path(__file__).resolve().parent.parent
SOURCE_DIR = os.path.join(PROJECT_PATH, 'Source')
PROPERTIES_FILE = os.path.join(SOURCE_DIR, 'Config.properties')
LOGGER_FILE = os.path.join(SOURCE_DIR, 'wegfinder.log')

config = configparser.ConfigParser()
config.read(PROPERTIES_FILE)

LOGGER = logging.getLogger("wegfinder")
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.FileHandler(LOGGER_FILE))


class State(Enum):
    ERROR = -1
    SUCCESS = 1
    NOT_IMPLEMENTED = 0


class ConnectAPI(object):
    def __init__(self, address):

        self.api_address = address
        self.status_code = None
        self.raw_data = ''

    @abstractmethod
    def run(self):
        LOGGER.log(logging.WARN, 'Implement run abstract method')
        return State.NOT_IMPLEMENTED

    def connect(self):
        response_API = requests.get(self.api_address)
        self.status_code = response_API.status_code
        if self.status_code != 200:
            LOGGER.log(logging.INFO, f'Status error on connect: {self.getStatusCode()}')
            return State.ERROR
        self.raw_data = json.loads(response_API.text)

    def getStatusCode(self):
        return config.get("HttpStatusCodes", f'http.status.code.{self.status_code}')

    def getRawData(self):
        return self.raw_data


class DecodeAPI1(ConnectAPI):
    def __init__(self, address):

        super().__init__(address)

        self.transformedKeys = ["id", "name", "active", "description", "boxes", "free_boxes", "free_bikes", "free_ratio", "coordinates"]
        self.transformedData = []

    def run(self):
        if self.connect() == State.ERROR:
            return
        if self.transformData() == State.ERROR:
            return
        print(f'The result to part 1:\n{self.getTransformedData()}')

    def transformData(self):
        for _station in self.raw_data:
            if self.passFilter(_station):

                copiedStation = copy.deepcopy(_station)
                # Copy the existing key-value pairs
                self.transformedData.append(copiedStation)

                # Add the new key-value pairs
                index = len(self.transformedData) - 1
                self.transformedData[index]["active"] = copiedStation["status"] == "aktiv"
                self.transformedData[index]["free_ratio"] = copiedStation["free_boxes"] / copiedStation["boxes"]
                self.transformedData[index]["coordinates"] = [copiedStation["longitude"], copiedStation["latitude"]]

                # Reorder and trim the station to match the expected structure
                self.transformedData[index] = {k: self.transformedData[index][k] for k in self.transformedKeys}

        self.sortData()

    def passFilter(self, station):
        return station["free_bikes"] != 0

    def sortData(self):
        secondarySorted = list(sorted(self.transformedData, key=lambda station: station["name"]))
        primarySorted = list(sorted(secondarySorted, key=lambda station: station["free_bikes"], reverse=True))
        self.transformedData = primarySorted

    def getTransformedData(self):
        return self.transformedData

    def setAddress(self):
        for _station in self.transformedData:
            addressStr = 'https://api.i-mobility.at/routing/api/v1/nearby_address'
            addressStr += f'?latitude={_station["coordinates"][1]}&longitude={_station["coordinates"][0]}'
            apiAddressEndpoint = DecodeAPI2(addressStr)
            apiAddressEndpoint.run()
            _station["address"] = apiAddressEndpoint.getAddress()


class DecodeAPI2(ConnectAPI):
    def __init__(self, address):

        super().__init__(address)

    def run(self):
        if self.connect() == State.ERROR:
            return

    def getAddress(self):
        return self.raw_data["data"]["name"]


if __name__ == "__main__":

    # Clear the log file
    logging.FileHandler(LOGGER_FILE, mode='w')

    apiEndpoint1 = DecodeAPI1('https://wegfinder.at/api/v1/stations')
    apiEndpoint1.run()
    apiEndpoint1.setAddress()
    print(f'The result to part 2:\n{list(apiEndpoint1.getTransformedData())}')
