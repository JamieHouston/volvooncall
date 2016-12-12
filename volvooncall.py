#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Retrieve information from VOC
"""

import logging
from datetime import timedelta, datetime

import requests
from requests.compat import urljoin

_LOGGER = logging.getLogger(__name__)

SERVICE_URL = 'https://vocapi.wirelesscar.net/customerapi/rest/v3.0/'
HEADERS = {'X-Device-Id': 'Device',
           'X-OS-Type': 'Android',
           'X-Originator-Type': 'App'}

TIMEOUT = timedelta(seconds=5)


def datetime_parser(obj):
    """Parse datetime (only Python3) because of timezone."""
    for key, val in obj.items():
        try:
            obj[key] = datetime.strptime(val, '%Y-%m-%dT%H:%M:%S%z')
        except (TypeError, ValueError):
            pass
    return obj


class Connection():

    """Connection to the VOC server."""

    def __init__(self, username, password):
        """Initialize."""
        self._session = requests.Session()
        self._session.headers.update(HEADERS)
        self._session.auth = (username,
                              password)
        self._state = {}
        _LOGGER.debug("User: <%s>", username)

    def query(self, ref, rel=SERVICE_URL):
        """Perform a query to the online service."""
        url = urljoin(rel, ref)
        _LOGGER.debug('Request for %s', url)
        res = self._session.get(url, timeout=TIMEOUT.seconds)
        res.raise_for_status()
        res = res.json(object_hook=datetime_parser)
        _LOGGER.debug('Received %s', res)
        return res

    def update(self, reset=False):
        """Update status."""
        try:
            _LOGGER.info('Updating')
            if not self._state or reset:
                _LOGGER.info('Querying vehicles')
                user = self.query('customeraccounts')
                _LOGGER.debug("Account for <%s> received",
                              user['username'])
                self._state = {}
                for vehicle in user['accountVehicleRelations']:
                    rel = self.query(vehicle)
                    vehicle = rel['vehicle'] + '/'
                    state = self.query('attributes', vehicle)
                    self._state.update({vehicle: state})
            for vin, vehicle in self._state.items():
                self._state[vin].update(
                    self.query('status', vin))
                self._state[vin].update(
                    self.query('position', vin))
                _LOGGER.debug('State: %s', self._state)
            return True
        except (IOError, OSError) as error:
            _LOGGER.error('Could not query server: %s', error)

    @property
    def vehicles(self):
        """Return state."""
        return (Vehicle(vehicle) for vehicle in self._state.values())


class Vehicle:
    """Convenience wrapper around the state returned from the server."""
    def __init__(self, data):
        self.__dict__ = data

    def __str__(self):
        # pylint: disable=no-member
        return "%s (%s/%d) %s %dkm (fuel %d%%:%dkm)" % (
            self.registrationNumber,
            self.vehicleType,
            self.modelYear,
            self.VIN,
            self.odometer / 1000,
            self.fuelAmountLevel,
            self.distanceToEmpty)


def main():
    """Command line interface."""
    from os import path
    from sys import argv
    logging.basicConfig(level=logging.INFO)

    if len(argv) == 3:
        credentials = argv[1:]
    else:
        try:
            with open(path.join(path.dirname(argv[0]),
                                '.credentials.conf')) as config:
                credentials = dict(x.split(": ")
                                   for x in config.read().strip().splitlines())
        except (IOError, OSError):
            print("Could not read configuration "
                  "and no credentials on command line\n"
                  "Usage: %s <username> <password>" % argv[0])
            exit(-1)
    connection = Connection(**credentials)
    if connection.update():
        for vehicle in connection.vehicles:
            print(vehicle)


if __name__ == '__main__':
    main()
