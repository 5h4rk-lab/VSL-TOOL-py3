#!/usr/bin/env python3

import time
import serial
import re
import sys
from serial.serialutil import SerialException
from event import *
from PySide6.QtGui import QInputDialog, QMessageBox
from PySide6.QtCore import Signal as pyqtSignal, Slot as pyqtSlot
import serial.tools.list_ports as serial_ports
from messages import *
import xml.etree.ElementTree
import xml.etree.ElementInclude

OUTPUT_RES = (
    re.compile(r"<(?P<tag>[FIESR][0-9A-Fa-f]{4})>(?P<text>.*?)</(?P=tag)>", re.DOTALL),
    re.compile(r"<(?P<tag>[FIESR][0-9A-Fa-f]{4})/>", re.DOTALL),
)

###
# Class that handles the serial connection
###
class SerialConnection(object):
    class tag_info(object):
        name = ""
        text = ""

        def __init__(self, name, text):
            self.name = name
            self.text = text

        def __str__(self):
            return self.name

    connected = False

    def __init__(self):
        self.statusChanged = Event()
        self.ser = None

    def statusMsg(self):
        if self.connected:
            return f'Serial: <font color="green">Connected to {self.ser.port}</font>'
        else:
            return 'Serial: <font color="red">Not Connected</font> '

    def waitForResponse(self, msg=None, desired_tag=None, timeout=0.1, max_length=500):
        print("\nWaiting for a serial response")
        if desired_tag:
            print(f"Looking for tag: {desired_tag}")
        if msg:
            print(f"Correct response should contain '{msg}'")
        print(f"Will timeout after {timeout} seconds")
        print(f"Will give up if response exceeds {max_length} characters")

        exceeded_timeout = False
        exceeded_max_length = False
        found_response = None
        response = ""
        start_time = time.time()
        elapsed_time = 0
        count = 0
        messages = []

        while not (found_response or exceeded_timeout or exceeded_max_length):
            while self.ser.in_waiting > 0 and not exceeded_max_length:
                ch = self.ser.read(1).decode('utf-8', errors='ignore')  # Decode byte to str
                response += ch
                count += 1
                if ch == '\n':
                    if desired_tag:
                        for curr_re in OUTPUT_RES:
                            parsed = curr_re.search(response)

                            if parsed:
                                tag, text = "", ""
                                groups = parsed.groups()
                                tag = groups[0]
                                if len(groups) == 2:
                                    text = groups[1]
                                tag_info = self.tag_info(tag, text)
                                messages.append(tag_info)
                                if tag == desired_tag:
                                    print("\n\n***FOUND***\n\n")
                                    found_response = tag_info
                                    response = ""
                                break
                    elif msg in response:
                        print("\n\n***FOUND***\n\n")
                        found_response = True

                if count > max_length:
                    exceeded_max_length = True
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                exceeded_timeout = True

        print(response)
        print("\nCorrect response: ", found_response)
        print(f"Response took {elapsed_time:.2f} seconds (timeout={exceeded_timeout})")
        return found_response, messages

    def switchToBootloader(self):
        self.ser.reset_output_buffer()
        print("Sending carriage return, seeing if bootloader responds")
        self.ser.reset_input_buffer()
        self.ser.write(b'\r')
        responded, tags = self.waitForResponse(desired_tag=Messages.MAIN_MENU)
        if responded is None:
            print("Didn't respond, sending '*1#' over serial")
            self.ser.reset_input_buffer()
            self.ser.write(b"*1#")
            print("Waiting .5 seconds to give board time to reboot if necessary")
            time.sleep(0.5)
            print("Sending a carriage return to prompt a bootloader response")
            self.ser.reset_input_buffer()
            self.ser.write(b'\r')
            responded, tags = self.waitForResponse(desired_tag=Messages.MAIN_MENU)
        return responded is not None

    def switchToVel(self):
        if self.switchToBootloader():
            self.ser.reset_input_buffer()
            print("Sending a 'd' to bootloader to execute application")
            self.ser.write(b'd')
            found, tags = self.waitForResponse(msg='Resetting', timeout=3, max_length=1000)
            return found
        return False

    def sendFile(self, fname):
        with open(fname, 'r') as f:
            print("Sending file: " + fname)
            start_time = time.time()
            self.ser.write(f.read().encode('utf-8'))  # Convert to bytes
            end_time = time.time()
            print(f"File sent (took {end_time - start_time:.2f} seconds) \n")

    def selectSerialPort(self):
        print("User is selecting a serial port")
        port_list = []
        for portname in self.enumerateSerialPorts():
            port_list.append(portname)
        item, ok = QInputDialog.getItem(
            None, "Select Serial Port", "Detected Ports: ", port_list, 0, False
        )
        if ok and item:
            if sys.platform == "win32":
                fullname = self.fullPortName(str(item))
            else:
                fullname = str(item)

            print("Selected port: " + fullname)
            self.ser = None
            self.connected = False
            self.statusChanged()
            print("Attempting to connect to port")
            try:
                self.ser = serial.Serial(
                    str(item), 115200, timeout=0.05, xonxoff=True
                )
                self.connected = True
                print("Connection successful \n")
                self.statusChanged()
            except SerialException as e:
                print("Connection failed \n")
                QMessageBox.critical(None, "Failed To Open Serial Port", f"{e}")
        else:
            print("No port selected \n")

    def enumerateSerialPorts(self):
        for port, desc, hw_id in serial_ports.comports():
            yield port

    def fullPortName(self, portname):
        m = re.match(r"^COM(\d+)$", portname)
        if m and int(m.group(1)) < 10:
            return portname
        return '\\\\.\\' + portname
