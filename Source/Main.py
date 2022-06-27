from abc import abstractmethod
from pathlib import Path
from enum import Enum
import configparser
import requests
import logging
import json
import os
import re
import copy


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

    @abstractmethod
    def formatData(self):
        LOGGER.log(logging.WARN, 'Implement formatData abstract method')
        return State.NOT_IMPLEMENTED

    def connect(self):
        response_API = requests.get(self.api_address)
        self.status_code = response_API.status_code
        if self.status_code != 200:
            LOGGER.log(logging.INFO, f'Status error on connect: {self.getStatusCode()}')
            return State.ERROR
        self.raw_data = json.loads(response_API.text)
        self.formatData()

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
        print(f'The result to part 1:\n{list(self.getTransformedData().values())}')

    def formatData(self):
        # for _station in self.raw_data:
        #     self.formattedData[_station["id"]] = _station
        pass

    def transformData(self):
        for _station in self.raw_data:
            for _key, _value in _station.items():
                if self.passFilter(_station):

                    copiedStation = copy.deepcopy(_station)
                    # Copy the existing key-value pairs
                    self.transformedData.append(copiedStation)  # TODO Maybe done need deepcopy

                    # Add the new key-value pairs
                    index = len(self.transformedData) - 1
                    self.transformedData[index]["active"] = copiedStation["status"] == "aktiv"
                    self.transformedData[index]["free_ratio"] = copiedStation["free_boxes"] / copiedStation["boxes"]
                    self.transformedData[index]["coordinates"] = [copiedStation["longitude"], copiedStation["latitude"]]

                    # Reorder the list to match the expected structure
                    # TODO Continue here
                    self.transformedData[index] = [self.transformedData[_key][k] for k in self.transformedKeys]

        self.sortData()

    def passFilter(self, station):
        return station["free_bikes"] != 0

    def sortData(self):
        secondarySorted = dict(sorted(self.transformedData.items(), key=lambda item: item[1]["name"]))
        primarySorted = dict(sorted(secondarySorted.items(), key=lambda item: item[1]["free_bikes"], reverse=True))
        self.transformedData = primarySorted

    def getTransformedData(self):
        return self.transformedData

    def setAddress(self):
        for _key, _station in self.transformedData.items():
            addressStr = 'https://api.i-mobility.at/routing/api/v1/nearby_address'
            addressStr += f'?latitude={_station["coordinates"][1]}&longitude={_station["coordinates"][0]}'
            apiAddressEndpoint = DecodeAPI2(addressStr)
            apiAddressEndpoint.run()
            _station["address"] = apiAddressEndpoint.getAddress()

    def getAddressFromAPI(self, apiRawData):
        return


class DecodeAPI2(ConnectAPI):
    def __init__(self, address):

        super().__init__(address)

    def run(self):
        if self.connect() == State.ERROR:
            return

    def formatData(self):
        try:
            idKey = re.search('"name": "[^"]*', self.raw_data)
            if idKey:
                foundText = idKey.group(0)
                address = foundText.replace('"name": "', '')
                self.formattedData["address"] = address

        except AttributeError:
            LOGGER.log(logging.ERROR, f'The API data could not be formatted')
            return State.ERROR

    def getAddress(self):
        return self.formattedData["address"]


if __name__ == "__main__":

    # Clear the log file
    logging.FileHandler(LOGGER_FILE, mode='w')

    apiEndpoint1 = DecodeAPI1('https://wegfinder.at/api/v1/stations')
    apiEndpoint1.run()
    # apiEndpoint1.setAddress()
    print(f'The result to part 2:\n{list(apiEndpoint1.getTransformedData().values())}')
