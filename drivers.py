"""Module containing a classes to communicate with devices over a few distinct communication channels

This module requires a National Instruments VISA driver, which can be found at
https://www.ni.com/visa/
It also requires an Agilent VISA driver - if there is need for either one 
(at least one VISA driver is required, may depend on your instrumentation)

Attributes:
    logger: a python logger object

Classes:
        AbstractSerialDeviceDriver: used for interactions with a serial connection
            the characteristics of the serial connection can be specified
            defaults are good for connections with "Oxford Instruments" devices
            over a serial connection

        AbstractGPIBDeviceDriver: used for interactions with a GPIB connection
            methods:
                query() - send a command and wait for an answer

                go() - send a command, not waiting for answers
Author(s):
    bklebel (Benjamin Klebel)
"""
import threading
import logging
import time
import visa
from pyvisa.errors import VisaIOError
from visa import constants as vconst

# create a logger object for this module
logger = logging.getLogger(__name__)

try:
    # the pyvisa manager we'll use to connect to the GPIB resources
    NI_RESOURCE_MANAGER = visa.ResourceManager()
    AGILENT_RESOURCE_MANAGER = visa.ResourceManager(
        'C:\\Windows\\System32\\agvisa32.dll')
except OSError:
    logger.exception(
        "\n\tCould not find the VISA library. Is the National Instruments VISA driver installed?\n\n")


class AbstractSerialDeviceDriver(object):
    """Abstract Device driver class"""
    timeouterror = VisaIOError(-1073807339)

    def __init__(self, InstrumentAddress, timeout=500, read_termination='\r', write_termination='\r', baud_rate=9600, data_bits=8, nivsag='ni', **kwargs):
        super().__init__(**kwargs)
        resource_manager = AGILENT_RESOURCE_MANAGER if nivsag.strip(
        ) == 'ag' else NI_RESOURCE_MANAGER
        self._visa_resource = resource_manager.open_resource(InstrumentAddress)
        # self._visa_resource.query_delay = 0.
        self._visa_resource.timeout = timeout
        self._visa_resource.read_termination = read_termination
        self._visa_resource.write_termination = write_termination
        self._visa_resource.baud_rate = baud_rate
        self._visa_resource.data_bits = data_bits
        self._visa_resource.stop_bits = vconst.StopBits.two
        self._visa_resource.parity = vconst.Parity.none
        self._comLock = threading.Lock()
        self.delay = 0.1
        self.delay_force = 0.1

    # def res_open(self):
    #     self._visa_resource = resource_manager.open_resource(InstrumentAddress)
    #     # self._visa_resource.query_delay = 0.
    #     self._visa_resource.timeout = 500
    #     self._visa_resource.read_termination = '\r'
    #     self._visa_resource.write_termination = '\r'

    def res_close(self):
        self._visa_resource.close()

    def write(self, command, f=False):
        """
            low-level communication wrapper for visa.write with Communication Lock,
            to prevent multiple writes to serial adapter
        """
        if not f:
            with self._comLock:
                self._visa_resource.write(command)
                time.sleep(self.delay)
        else:
            self._visa_resource.write(command)
            time.sleep(self.delay_force)

    def query(self, command):
        """
            low-level communication wrapper for visa.query with Communication Lock,
            to prevent multiple writes to serial adapter
        """
        with self._comLock:
            answer = self._visa_resource.query(command)
            time.sleep(self.delay)
        return answer

    def read(self):
        with self._comLock:
            answer = self._visa_resource.read()
            # time.sleep(self.delay)
        return answer

    def clear_buffers(self):
        # self._visa_resource.timeout = 5
        try:
            # with self._comLock:
            self.read()
        except VisaIOError as e_visa:
            if isinstance(e_visa, type(self.timeouterror)) and e_visa.args == self.timeouterror.args:
                pass
            else:
                raise e_visa
        # self._visa_resource.timeout = 500


class AbstractGPIBDeviceDriver(object):
    """docstring for Instrument_GPIB"""

    def __init__(self, InstrumentAddress, nivsag='ag', **kwargs):
        super().__init__(**kwargs)
        # self.arg = arg
        resource_manager = AGILENT_RESOURCE_MANAGER if nivsag.strip(
        ) == 'ag' else NI_RESOURCE_MANAGER
        self._visa_resource = resource_manager.open_resource(InstrumentAddress)
        # self._visa_resource.read_termination = '\r'
        self._comLock = threading.Lock()
        self._device = self._visa_resource

    def query(self, command):
        """Sends commands as strings to the device and receives strings from the device

        :param command: string generated by a given function, whom will be sent to the device
        :type command: str

        :return: answer from the device
        """
        with self._comLock:
            received = self._device.query(command)
        return received.strip().split(',')

    def go(self, command):
        """Sends commands as strings to the device

        :param command: string generated by a given function, whom will be sent to the device
        :type command: str

        """
        with self._comLock:
            self._device.write(command)
