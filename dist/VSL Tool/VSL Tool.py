#!/usr/bin/python2.7
#--coding:utf-8 --
import os
import sys
import glob
#import serial
import socket
import printer
import datetime
from serial.serialutil import SerialException
from collections import namedtuple
import subprocess
import re
import time
# import _winreg as winreg
import itertools
from PySide6 import QtGui, QtWidgets
from PySide6.QtGui import QFont
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt
from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtCore import Slot as pyqtSlot
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QTabWidget,QComboBox, QVBoxLayout, QWidget, QGridLayout, QPushButton, QFileDialog, QMessageBox, QInputDialog, QDialogButtonBox, QScrollArea, QTextEdit, QLineEdit

import xml.etree.ElementTree
import xml.etree.ElementInclude
from event import *
from serial_connection import *
from messages import *
from crc import *
import io
import dflash_controller as con
import serial_connect as sc
import sys

if os.sys.platform.startswith("win"):
    from winreg import *
#import gc

###
# Global variables
###
AUTO_INCREMENT = True
PRINTER_IP = '10.0.1.80'
DEFAULT_PRINTER_TEMPLATE = 1
STX = "\x02"
ETB = "\x17"
ETX = "\x03"
LINE_FEED = "\x0A"
CONFIG_VERSION = 1
HASH_METHOD = 1
VEL_MODE = True

###
# Class that groups together two labels and a button
###

class FormComponent(object):
    detected = False

    def __init__(self, fixed_txt, variable_txt_true, variable_txt_false, button_txt_true, button_txt_false):
        self.detectedChanged = Event()
        self.fixed_label_text = fixed_txt

        self.variable_label_text_true = variable_txt_true
        self.variable_label_text_false = variable_txt_false
        self.button_text_true = button_txt_true
        self.button_text_false = button_txt_false
        self.initSubComponents()




    def initSubComponents(self):
        # Fonts
        category_font = QFont("Helvetica", 12, QFont.Bold)
        status_font = QFont("Helvetica", 12)

        # Fixed label
        self.fixed_label = QLabel(self.fixed_label_text)
        self.fixed_label.setFont(category_font)

        # Variable label
        self.variable_label = QLabel(self.variable_label_text_false)
        self.variable_label.setFont(status_font)

        # Button
        self.btn = QPushButton(self.button_text_false)
        self.btn.setMinimumWidth(100)
        self.btn.setMinimumHeight(40)
        self.btn.setFont(status_font)

    def enable(self):
        self.btn.setEnabled(True)

    def disable(self):
        self.btn.setEnabled(False)

    def isEnabled(self):
        return self.btn.isEnabled()

    def setDetected(self, detect_newval):
        self.detected = detect_newval
        if self.detected:
            self.variable_label.setText(self.variable_label_text_true)
            self.btn.setText(self.button_text_true)
        else:
            self.variable_label.setText(self.variable_label_text_false)
            self.btn.setText(self.button_text_false)
        self.detectedChanged()

###
# The labels & button relating to the bootloader
###
###
#TODO: update the syntax to python3 and QtGui.QFileDialog
class BootloaderComponent(FormComponent):

    def __init__(self, serial, programmer):
        super(BootloaderComponent, self).__init__('Bootloader: ','Detected','Not Detected','Reprogram','Program')
        self.last_dir = None
        self.serial = serial
        self.programmer = programmer
        self.btn.clicked.connect(self.buttonClicked)

    def buttonClicked(self):
        print( "Selecting bootloader S19 to program")
        start_dir = 'C://' if not self.last_dir else self.last_dir
        fname = QFileDialog.getOpenFileName(None, 'Select Bootloader S19 File', start_dir)[0]
        if fname:
            print ("S19 selected:")
            print (" " + str(fname))
            self.setDetected(False)
            self.last_dir = fname
            print ("Attempting to program bootloader")
            self.programmer.vel_execute(str(fname))
            self.checkForBootloader()
            print ("\n")
        else:
            print ("No S19 selected \n"
)
    def enable(self):
        super(BootloaderComponent, self).enable()
        self.checkForBootloader()

    def checkForBootloader(self):
        print ("Checking for bootloader")
        if self.serial.switchToBootloader():
            print ("Bootloader detected \n")
            self.setDetected(True)
        else:
            print ("Bootloader not detected \n")
            self.setDetected(False)

###
# The labels & button relating to fixed information
#TODO: update the syntax to python3 and QtGui.QFileDialog
###
class FixedInfoComponent(FormComponent):

    def __init__(self, serial):
        super(FixedInfoComponent, self).__init__('Fixed Info: ','Written','Not Written','Read','Write')
        self.serial = serial
        self.config = None
        self.btn.clicked.connect(self.buttonClicked)

    def selectConfigFile(self):
        print("User is selecting a config file")
        start_dir = './' if not self.config else self.config.fname
        fname = QFileDialog.getOpenFileName(None, 'Select Configuration File', start_dir)[0]
        if fname:
            self.config = FixedInformationConfig(str(fname))
            print("Config file selected: ")
            print(" " + self.config.fname + "\n")
        else:
            print("No config file selected \n")

    def saveConfigFile(self):
        if self.config:
            print("Selecting file to save last fixed info configuration")
            fname = QFileDialog.getSaveFileName(None, 'Save as', self.config.fname)
            if fname:
                print("File selected. Saving configuration to " + str(fname) + "\n")
                self.config.writeFile(str(fname))
            else:
                print("No file selected. Not saving configuration \n")
        else:
            print("Cannot save configuration- don't have a configuration to save \n")

    def buttonClicked(self):
        if not self.detected:
            self.writeFixedInformation()
        else:
            self.readFixedInformation()

    def readFixedInformation(self):
        print("User wants to read fixed information \n")
        if self.serial.switchToBootloader():
            self.serial.ser.flushInput()
            print("Sending a 'c' to bootloader to read fixed information")
            self.serial.ser.write('cFF'.encode('utf-8'))  # Encoding string to bytes
            found, _ = self.serial.waitForResponse(
                desired_tag=Messages.DFLASH_DATA)
            if found:
                print("\nResponse:")
                print(found.text + "\n")
                dictionary = self.parseResponse(found.text)
                FixedInformationDialog.readFixedInformation(dictionary)
            else:
                QMessageBox.information(None, 'Read Fixed Info',
                                        "Fixed information has not " +
                                        "been written")

    def parseResponse(self, response):
        dictionary = {}
        stx_pos = response.find(STX)
        etb_pos = response.find(ETB)
        etx_pos = response.find(ETX)
        if (stx_pos >= 0) and (etb_pos >= 0) and (etx_pos >= 0):
            crc_valid_p = False
            if int(response[etb_pos+1], 16) == HASH_METHOD:
                computed_crc = crc(response[stx_pos+1:etb_pos])
                found_crc = int(response[etb_pos+2:etx_pos], 16)
                if (computed_crc == found_crc):
                    crc_valid_p = True
            if crc_valid_p:
                block_start = 2
                while response[block_start] != ETB:
                    block_end = response.find(LINE_FEED,block_start)
                    key = response[block_start:block_start+2]
                    value = response[block_start+2:block_end]
                    dictionary[key] = value
                    block_start = block_end+1
        return dictionary

    def writeFixedInformation(self):
        print ("User wants to write fixed information \n")
        if not self.config:
            self.selectConfigFile()
        fixedInfo = FixedInformationDialog.writeFixedInformation(self.config)
        if fixedInfo:
            # fd = open("Joa_Page0_bFF%04X.out" % len(fixedInfo),"wb")
            # for ch in fixedInfo:
            #     fd.write(ch)
            #     time.sleep(.001)
            # fd.close()
            # return
            if self.serial.switchToBootloader():
                self.serial.ser.flushInput()
                print ("Sending a 'b' to bootloader to write fixed information")
                self.serial.ser.write('bFF')
                self.serial.ser.write("%04X" % len(fixedInfo))

                found, tags = self.serial.waitForResponse( \
                    desired_tag=Messages.DFLASH_SEND_DATA)
                if found:
                    print ("Sending fixed information: ")
                    for ch in fixedInfo:
                        self.serial.ser.write(ch)
                        time.sleep(.001)
                    self.checkForFixedInfo()
                else:
                    print ("Error:")
                    for tag in tags:
                        print(tag.name, tag.text)
            else:
                print("Failed to switch to bootloader; " +
                      "no fixed information written \n")
        else:
            print("No fixed information written \n")

    def enable(self):
        super(FixedInfoComponent, self).enable()
        self.checkForFixedInfo()

    def checkForFixedInfo(self):
        print("Checking for fixed information")
        if self.serial.switchToBootloader():
            self.serial.ser.flushInput()
            print("Sending a 'c' to bootloader to read fixed information")
            self.serial.ser.write('cFF'.encode('utf-8'))  # Encoding string to bytes
            # self.serial.ser.write('\x00')
            found, _ = self.serial.waitForResponse(
                desired_tag=Messages.DFLASH_DATA, max_length=1000)

            if found:
                print("Fixed information has been written \n")
                self.setDetected(True)
            else:
                print("Fixed information has not been written \n")
                self.setDetected(False)
        else:
            print("Failed to switch to bootloader; could not check for fixed information \n")

###
# Custom dialog for writing fixed info
###
class FixedInformationDialog(QtWidgets.QDialog):
    """
    A dialog for displaying and editing fixed information.

    This dialog can operate in two modes: read-only and write. In read-only mode, it displays the information
    from a given dictionary without allowing modifications. In write mode, it allows the user to edit the information
    based on a given configuration.

    Attributes:
        lineEdit_dictionary (dict): A dictionary to store QLineEdit widgets for each category identifier.

    Methods:
        __init__(config=None, dictionary=None, readonly=False, parent=None):
            Initializes the dialog in either read-only or write mode based on the readonly flag.

        initForRead(dictionary):
            Initializes the dialog for read-only mode using the provided dictionary.

        initForWrite(config):
            Initializes the dialog for write mode using the provided configuration.

        writeFixedInformation(fixed_info_config):
            Static method to open the dialog in write mode and return the updated fixed information as a formatted string.

        readFixedInformation(fixed_info_dictionary):
            Static method to open the dialog in read-only mode to display the fixed information.
    """

    def __init__(self, config=None, dictionary=None, readonly=False, parent=None):
        super(FixedInformationDialog, self).__init__(parent)
        self.lineEdit_dictionary = {}
        if readonly:
            self.initForRead(dictionary)
        else:
            self.initForWrite(config)

    def initForRead(self, dictionary):
        grid = QtWidgets.QGridLayout()
        current_row = 0
        for key in dictionary.keys():
            label = QtWidgets.QLabel(key)
            lineEdit = QtWidgets.QLineEdit()
            lineEdit.setText(dictionary[key])
            lineEdit.setReadOnly(True)
            grid.addWidget(label, current_row, 0)
            grid.addWidget(lineEdit, current_row, 1)
            current_row = current_row + 1
        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        buttonBox.accepted.connect(self.accept)
        grid.addWidget(buttonBox, current_row, 1)
        self.setLayout(grid)
        self.setWindowTitle("Read Fixed Info")

    def initForWrite(self, config):
        grid = QtWidgets.QGridLayout()
        current_row = 0
        for category in config.list_of_categories:
            label = QtWidgets.QLabel(category.title)
            lineEdit = QtWidgets.QLineEdit()
            self.lineEdit_dictionary[category.identifier] = lineEdit
            lineEdit.setText(category.default)
            grid.addWidget(label, current_row, 0)
            grid.addWidget(lineEdit, current_row, 1)
            current_row = current_row + 1
        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        grid.addWidget(buttonBox, current_row, 1)
        self.setLayout(grid)
        self.setWindowTitle("Write Fixed Info")

    @staticmethod
    def writeFixedInformation(fixed_info_config):
        if fixed_info_config:
            print("Fixed information dialog opening in write mode")
            dlg = FixedInformationDialog(config=fixed_info_config,
                                         readonly=False)
            if dlg.exec_():
                my_dict = dlg.lineEdit_dictionary
                data = io.StringIO()
                for key, value in my_dict.iteritems():
                    value = value.text.encode("utf-8")
                    fixed_info_config.updateValue(key, value)
                    data.write(key[:2])
                    data.write(value)
                    data.write(LINE_FEED)

                data = data.getvalue()
                crc_str = crc(data)
                result = "%x%s%s%s%x%04X%s" % (CONFIG_VERSION,
                                               STX, data, ETB,
                                               HASH_METHOD, crc_str, ETX)
                return result

    @staticmethod
    def readFixedInformation(fixed_info_dictionary):
        if fixed_info_dictionary:
            print("Fixed information dialog opening in read only mode")
            dlg = FixedInformationDialog(dictionary=fixed_info_dictionary,
                                         readonly=True)
            dlg.exec_()
            print("Fixed information dialog closed \n")

###
# Typedef for a named tuple representing a fixed information category
###
FixedInformationCategory = namedtuple("FixedInformationCategory", "title identifier default")

###
# Class for parsing fixed information config files
###
class FixedInformationConfig(object):

    def __init__(self, fname):
        self.fname = fname
        self.last_serial_num = None
        self.list_of_categories = []
        self.parseFile()

    def parseFile(self):
        print("Attempting to parse xml config file")
        tree = xml.etree.ElementTree.parse(self.fname)
        root = tree.getroot()
        print("Trying to include any xinclude data (external serial number file)")
        try:
            xml.etree.ElementInclude.include(root)
            print( " xinclude successful")
        except Exception:
            print (" xinclude failed")
        print ("Looping through xml file to create categories")
        for category in root.findall('category'):
            title = category.find('title').text if category.find('title').text else ''
            identifier = category.find('identifier').text if category.find('identifier').text else ''
            default = category.find('default').text if category.find('default').text else ''
            self.list_of_categories.append(FixedInformationCategory(title.strip(),identifier.strip(),default.strip()))
            print ("Creating category: title=" + title + ", identifier=" + identifier + ", default=" + default)
        print ("Finished parsing xml file \n")

    def updateValue(self, identifier, new_val):
        old = self.list_of_categories.pop([c.identifier for c in self.list_of_categories].index(identifier))
        self.list_of_categories.append(self.updateCategoryDefault(old, new_val))

    def updateCategoryDefault(self, category_tuple, new_default):
        title = category_tuple.title
        identifier = category_tuple.identifier
        default = new_default if identifier != 'sn' else self.autoIncrement(new_default)
        return FixedInformationCategory(title.strip(),identifier.strip(),default.strip())

    def autoIncrement(self, last_serial_num):
        self.last_serial_num = last_serial_num
        print ("Auto-increment serial number? Last serial number = " + last_serial_num)
        if AUTO_INCREMENT:
            print ("Attempting to auto-increment")
            try:
                split_ser = re.match(r"([a-z]+)([0-9]+)", last_serial_num, re.I)
                txt = split_ser.group(1)
                num = split_ser.group(2)
                new_serial_num = txt + str(int(num) + 1).zfill(len(num))
                print("Auto-increment successful. New serial number = " + new_serial_num + "\n")
                f = open(os.path.join(os.path.dirname(self.fname),"serial_number.txt"), 'w')
                f.write(new_serial_num)
                f.close()
                return new_serial_num
            except Exception:
                print ("Failed to increment serial number \n")
                return last_serial_num
        else:
            print("Auto-increment is disabled. Leaving serial number alone. \n")
            return last_serial_num

    def writeFile(self, fname):
        root = xml.etree.ElementTree.Element('fixedinfo')
        root.text = "\n    "
        for c in self.list_of_categories:
            cat = xml.etree.ElementTree.Element('category')
            cat.text = "\n        "
            cat.tail = "\n    "
            title = xml.etree.ElementTree.Element('title')
            title.text = c.title
            title.tail = "\n        "
            identifier = xml.etree.ElementTree.Element('identifier')
            identifier.text = c.identifier
            identifier.tail = "\n        "
            default = xml.etree.ElementTree.Element('default')
            default.tail = "\n    "
            if c.identifier != 'sn':
                default.text = c.default
            else:
                default.text = "\n            "
                default.attrib['xmlns:xi'] = "http://www.w3.org/2001/XInclude"
                inc = xml.etree.ElementTree.Element('xi:include')
                inc.attrib['href'] = "serial_number.txt"
                inc.attrib['parse'] = "text"
                inc.tail = "\n        "
                default.append(inc)
                f2 = open(os.path.join(os.path.dirname(fname),"serial_number.txt"), 'w')
                f2.write(c.default)
                f2.close()
            cat.append(title)
            cat.append(identifier)
            cat.append(default)
            root.append(cat)
        cat.tail = "\n"
        f = open(fname, 'w')
        xml.etree.ElementTree.ElementTree(root).write(f, encoding='utf-8')
        f.close()

###
# The labels & button relating to vel code
###
class VelCodeComponent(FormComponent):

    def __init__(self, serial):
        super(VelCodeComponent, self).__init__('VEL Code: ','Detected','Not Detected','Reprogram','Program')
        self.last_dir = None
        self.serial = serial
        self.btn.clicked.connect(self.buttonClicked)

    def buttonClicked(self):
        print ("Selecting vel S19 to program")
        start_dir = 'C://' if not self.last_dir else self.last_dir
        fname = QFileDialog.getOpenFileName(None, 'Select VEL S19 File', start_dir)[0]
        if fname:
            print ("S19 selected:")
            print (" " + str(fname))
            self.setDetected(False)
            self.last_dir = fname
            print ("Switching to bootloader")
            if self.serial.switchToBootloader():
                self.serial.ser.flushInput()
                print("Sending an 'a' (erase & program) to bootloader")
                self.serial.ser.write('a')
                found, tags = self.serial.waitForResponse( \
                    desired_tag=Messages.ERASED_SUCCESSFULLY, \
                        timeout=10, max_length=1000)
                if found:
                    self.serial.sendFile(fname)
                    self.serial.waitForResponse( \
                        desired_tag=Messages.PROGRAMMED_SUCCESSFULLY, \
                            timeout=1, max_length=10000)
            self.checkForVelCode()
        else:
            print("No S19 selected \n")

    def enable(self):
        super(VelCodeComponent, self).enable()
        self.checkForVelCode()

    def checkForVelCode(self):
        print ("Checking for vel code")
        if self.serial.switchToVel():
            print ("Vel code detected \n")
            self.setDetected(True)
        else:
            print( "Vel code not detected \n")
            self.setDetected(False)


###
# Class that handles the HCS12 programmer executable
###
class ProgrammerExecutable(object):
    found = False
    vel = True

    def __init__(self, gfi_mode):
        self.statusChanged = Event()
        self.path = ""
        if gfi_mode:
            self.vel = False
        self.checkForExecutable()

    def statusMsg(self):
        start_txt = "VEL " if self.vel else "RCD "
        if self.found:
            return start_txt + 'Programmer: <font color="green">' + os.path.basename(self.path) + '</font> '
        else:
            return start_txt + 'Programmer: <font color="red">Executable Not Found</font> '

    def checkForExecutable(self):
        txt = "VEL" if self.vel else "RCD"
        print ("Searching for " + txt + " programmer executable")
        self.found = False

        if os.sys.platform.startswith("win"):
            aKeys = [r"SOFTWARE\pgo\USBDM", r"SOFTWARE\Wow6432Node\pgo\USBDM"]
            val = None
            for aKey in aKeys:
                try:
                    aReg = ConnectRegistry(None,HKEY_LOCAL_MACHINE)
                    asubkey=OpenKey(aReg,aKey)
                    val=QueryValueEx(asubkey, "InstallationDirectory")[0]
                    self.found = True
                    print ("Found the installation directory")
                    break
                except EnvironmentError:
                    print("Checking next key")
            if val is None:
                print("Error: Installation directory not found.")
                return # as we actually dont need it.
            if self.vel:
                self.path = os.path.join(val,"HCS12_FlashProgrammer.exe")
            else:
                self.path = os.path.join(val,"HCS08_FlashProgrammer.exe")

            #execglob = '\pgo\USBDM*\HCS12_FlashProgrammer.exe' if self.vel else '\pgo\USBDM*\HCS08_FlashProgrammer.exe'
            #self.found = False
            #for envvar in ["ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"]:
            #    try:
            #        matches = glob.glob(os.environ[envvar] + execglob)
            #    except KeyError:
            #        continue
            #    if matches:
            #        self.path = matches[0]
            #        self.found = True
            #       print "Executable located: "
            #        print " " + self.path + "\n"
        else:
            #linux mac
            print("No USBDM Linux or Mac support Yet ")

    def selectExecutable(self):
        txt = "VEL" if self.vel else "RCD"
        print ("User is selecting " + txt + " programmer executable")
        start_dir = 'C://' if not self.path else self.path
        fname = QFileDialog.getOpenFileName(None, 'Select Programmer Executable', start_dir)[0]
        if fname:
            self.path = str(fname)
            self.found = True
            print ("Executable selected: ")
            print (" " + self.path + "\n")
            self.statusChanged()
        else:
            print ("No executable selected \n")

    def vel_execute(self, s19_file):
        try:
            #print subprocess.check_output([self.path,s19_file,'-device=MC9S12XEP100','-unsecure','-masserase','-program','-execute'])\
            print(subprocess.check_output([self.path,s19_file,'-device=MC9S12XEP100','-erase=selective','-program','-execute']))
            print("Finished programming \n")
        except Exception as e:
            print("Error trying to execute programmer executable")
            QMessageBox.critical(None, 'Programmer executable failed', '%s' % (e))

    def gfi_execute(self, s19_file):
        try:
            print(subprocess.check_output([self.path,s19_file,'-device=MC9S08SH4','-trim=33.6','-nvloc=FFAE','-secure','-masserase','-program','-execute']))
            print("Finished programming \n")
        except Exception as e:
            print("Error trying to execute programmer executable")
            QMessageBox.critical(None, 'Programmer executable failed', '%s' % (e))

###
# Class that handles the label printer
###
class LabelPrinter(object):
    connected = False

    def __init__(self):
        self.printer = None
        self.ip = PRINTER_IP
        self.template = DEFAULT_PRINTER_TEMPLATE
        self.establishConnection(self.ip, True)

    def establishConnection(self, ip_address=None, suppress_error=False):
        if not ip_address:
            print("User is entering an ip address for the label printer")
            text, ok = QInputDialog.getText(None, 'Connect to Printer', 'Enter printer ip address:', text=self.ip)
            if text and ok:
                self.ip = text
                ip_address = text
            else:
                print("No ip address entered; aborting connection attempt \n")
        if ip_address:
            print("Trying to connect to printer at IP address " + ip_address)
            try:
                f_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                f_socket.settimeout(1)
                f_socket.connect((ip_address,9100))
                self.printer = printer.BrotherLabel(f_socket)
                self.printer.template_mode()
                self.printer.template_init()
                self.printer.choose_template(self.template)
                print("Succesful connection to printer \n")
            except Exception as e:
                print("Error connecting to the printer at the given ip \n")
                if not suppress_error:
                    QMessageBox.critical(None, 'Could Not Connect To Printer', '%s' % (e))

    def changeTemplate(self):
        print("User is entering a new template number")
        text, ok = QInputDialog.getText(None, 'Change Template', 'Enter new template number:', text=str(self.template))
        if text and ok:
            try:
                self.template = int(text)
                if self.printer:
                    self.printer.choose_template(self.template)
                print( "Template number has been changed to " + text + "\n")
            except ValueError:
                print("Value entered is not a valid number, not changing template \n")
        else:
            "Nothing entered, not changing template \n"

    def printLabel(self, serial_num):
        "User would like to print label"
        if not self.printer:
            print( "Cannot print label; do not have a connection to the printer \n")
            QMessageBox.critical(None, 'Printing Error', 'No connection to the printer')
        else:
            today = datetime.datetime.today()
            date = str(today.month) + '/' + str(today.day) + '/' + str(today.year)
            self.printer.select_and_insert('sn', serial_num)
            self.printer.select_and_insert('date', date)
            self.printer.template_print()
            print ("I think I printed a label. Do you think I printed a label? \n")

    def printTestLabel(self):
        "User would like to print a test label"
        if not self.printer:
            print ("Cannot print test label; do not have a connection to the printer \n")
            QMessageBox.critical(None, 'Printing Error', 'No connection to the printer')
        else:
            today = datetime.datetime.today()
            date = str(today.month) + '/' + str(today.day) + '/' + str(today.year)
            self.printer.select_and_insert('sn', 'TESTING')
            self.printer.select_and_insert('date', date)
            self.printer.template_print()
            print ("Test label sent to printer. Did it print? \n")

###
# Customized tab widget
###
class CustomTabWidget(QtWidgets.QTabWidget):

    def __init__(self):
        super(CustomTabWidget, self).__init__()
        self.modeChanged = Event()

    @pyqtSlot(int)
    def tabChangedSlot(self,argTabIndex):
        global VEL_MODE
        if argTabIndex == 1:
            VEL_MODE = True
        else:
            VEL_MODE = False
        self.modeChanged()

###
# Class that holds the main window
###
class MainWindow(QMainWindow):
    last_gfi_dir = None

    def __init__(self):
        super(MainWindow, self).__init__()
        print ("Initializing.. \n")
        self.controller = con.Controller()
        self.initComponents()
        self.initUI()
        self.initDFL()
    
    def initComponents(self):
        #Components
        self.printer = LabelPrinter()
        self.vel_programmer = ProgrammerExecutable(False)
        self.gfi_programmer = ProgrammerExecutable(True)
        self.serial = SerialConnection()
        self.bootloader = BootloaderComponent(self.serial, self.vel_programmer)
        self.fixedinfo = FixedInfoComponent(self.serial)
        self.velcode = VelCodeComponent(self.serial)
        #Event Handlers
        self.vel_programmer.statusChanged += self.formChangeHandler
        self.serial.statusChanged += self.formChangeHandler
        self.bootloader.detectedChanged += self.formChangeHandler
        self.fixedinfo.detectedChanged += self.formChangeHandler
        self.velcode.detectedChanged += self.formChangeHandler
        #self.hp = HelpPanel(self)
        #self.hp = None
        self.cp = ControlPanel(self)


    def initUI(self):
        self.setupMenu()
        self.setupStatusBar()
        self.setupLayout()
        self.formChangeHandler()
        self.resize(500, 200)
        self.center()
        self.setWindowTitle('VEL Programmer')
    # # Debugging code to find the source of "Help Information"
    #     print("Debugging QLabel instances:")
    #     for label in self.findChildren(QLabel):
    #         print("Found QLabel:", label.text(), "Parent:", label.parent())

    #     print("Debugging Menu Bar actions:")
    #     for action in self.menuBar().actions():
    #         print("Menu bar action:", action.text())       
        self.show()

    def initDFL(self):
        self.setup_menu_1()
        self.setup_status_bar()


    def setup_menu_1(self):
        self.menubar = self.menuBar()
        field_Menu = self.menubar.addMenu('Field')           #self.field_menu = wx.Menu()
        #Read Save
        on_read_save_Action = QtGui.QAction('Populate fields from save', self)
        on_read_save_Action.setShortcut('Ctrl+p')
        on_read_save_Action.triggered.connect(self.onReadSave)
        #Write Save
        on_write_save_Action = QtGui.QAction('Save current fields', self)
        on_write_save_Action.setShortcut('Ctrl+s')
        on_write_save_Action.triggered.connect(self.onWriteSave)
        #Clear Fields
        on_clear_Action = QtGui.QAction('Clear fields', self)
        on_clear_Action.setShortcut('Ctrl+c')
        on_clear_Action.triggered.connect(self.onClear)
        #Repopulate Fields
        on_repopulate_Action = QtGui.QAction('Repopulate fields', self)
        on_repopulate_Action.setShortcut('Ctrl+r')
        on_repopulate_Action.triggered.connect(self.onRepopulate)
        field_Menu.addAction(on_read_save_Action)
        field_Menu.addAction(on_write_save_Action)
        field_Menu.addAction(on_clear_Action)
        field_Menu.addAction(on_repopulate_Action)

    # Methods
    def onClear(self):
        #AddInfo.all_clear()
        for edit in self.nb.info_line_list.edits:
            edit.clear()





    def onRepopulate(self):
        self.tabs = self.findChildren(NotebookTab)
        for i in range(0, len(self.tabs)-1):
            for j in range(0, len(self.tabs)-1):
                if self.tabs[j].page_index > self.tabs[j+1].page_index:
                    temp = self.tabs[j]
                    self.tabs[j] = self.tabs[j+1]
                    self.tabs[j+1] = temp
        print(self.tabs)
        for i, tab in enumerate(self.tabs):
            if self.controller.serial_connected():
                self.page_title = self.config_index[i][0]
                self.controller.populate_from_vel(self.page_title)
            self.lineEdits = tab.info_line_list.findChildren(QLineEdit)
            print(self.lineEdits)
            for j,line in enumerate(self.lineEdits):
                line.setText(str(self.controller.config_list[i+1][j][con.ConfigFields.VALUE]))
                print(line.setText)




    def onReadSave(self):

        dlg = QtWidgets.QFileDialog.DontResolveSymlinks | QtWidgets.QFileDialog.ShowDirsOnly
        directory = QtWidgets.QFileDialog.getExistingDirectory()
        print ('selected_directory:', directory)
        unrecognized_lists = self.controller.populate_from_save_dir(directory.replace('\\', '/'))
        # Check if the folder had any .dflash files
        if unrecognized_lists == []:
            pass
        # Update the GUI from the config_file that has new info
        self.tabs = self.findChildren(NotebookTab)
        for i in range(0, len(self.tabs)-1):
            for j in range(0, len(self.tabs)-1):
                if self.tabs[j].page_index > self.tabs[j+1].page_index:
                    temp = self.tabs[j]
                    self.tabs[j] = self.tabs[j+1]
                    self.tabs[j+1] = temp
        print (self.tabs)
        for i, tab in enumerate(self.tabs):
            self.lineEdits = tab.info_line_list.findChildren(QtGui.QLineEdit)
            print (self.lineEdits)
            for j,line in enumerate(self.lineEdits):
                line.setText(str(self.controller.config_list[i+1][j][con.ConfigFields.VALUE]))
                print(line.setText)


    def onWriteSave(self):
        #create a new empty folder before you choose directory, and then save it in the folder you found
        dlg = QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory()
        print ('selected_directory:', directory)

        msgBox = QMessageBox(QMessageBox.Warning,
                "QMessageBox.warning()", "Do you really want to save the latest data?",
                QMessageBox.NoButton, self)
        msgBox.addButton("Yes", QMessageBox.AcceptRole)
        msgBox.addButton("No", QMessageBox.RejectRole)
        if msgBox.exec_() == QMessageBox.AcceptRole:
            self.controller.save_user_values(directory.replace('\\', '/'))
            reply = QMessageBox.information(self,
                "QMessageBox.information()", 'The files are saved in the folder you choose')
        else:
            pass




    def setup_status_bar(self):
        pass

    def OnClose(self):
        print ("closing")
        if self.controller.serial_connected():
            self.controller.switch_to_execute()
            self.controller.ser.close()
        self.close()


    #    def OnClose(self):
    # print("Closing")
    
    # def close_serial():
    #     try:
    #         if self.controller.serial_connected():
    #             print("Serial connection open, attempting to close...")
    #             self.controller.switch_to_execute()  # Long-running task
    #             if self.controller.ser and self.controller.ser.isOpen():
    #                 self.controller.ser.close()
    #                 print("Serial connection closed.")
    #     except Exception as e:
    #         print(f"Error during serial closure: {e}")
    
    # # Run the serial closure task in a background thread to avoid blocking the main thread
    # threading.Thread(target=close_serial).start()
    
    # # Close the window immediately
    # self.close()
    # print("Window closed successfully.")

    def OnRestart(self):
        if self.controller.serial_connected():
            self.controller.switch_to_execute()
            self.controller.ser.close()
        MainWindow()
        self.close()




    def center(self):
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        qr = self.frameGeometry()
        cp = screen_geometry.center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def setupLayout(self):
        tab_widget = CustomTabWidget()
        tab_widget.modeChanged += self.formChangeHandler
        gfi_tab = QWidget()
        vel_tab = QWidget()
        dfl_tab = QWidget()
        gfi_tab.setLayout(self.setupGfiGrid())
        vel_tab.setLayout(self.setupVelGrid())
        dfl_tab.setLayout(self.setupDflGrid())
        tab_widget.addTab(dfl_tab, "DFL")
        tab_widget.addTab(vel_tab, "VEL")
        tab_widget.addTab(gfi_tab, "RCD")
        #tab_widget.connect(tab_widget,QtCore.SIGNAL("currentChanged(int)"),tab_widget,QtCore.SLOT("tabChangedSlot(int)"))
        tab_widget.currentChanged.connect(tab_widget.tabChangedSlot)
        self.setCentralWidget(tab_widget)

    def setupDflGrid(self):
        self.current_port = "-"
        self.current_config = "-"
        available_ports = ["-"]
        available_configs = ["-"]
        available_ports.extend(self.controller.list_serial_ports())
        available_configs.extend(["EVSE", "EV_1", "EV_2", "EV_3", "EV_4"])

        #----------------------------------------------------------------------
        #Serial connection

        grid = QGridLayout()
        label_font = QtGui.QFont("Helvetica", 12, QtGui.QFont.Bold)

        label1 = QLabel("Select Serial Port", self)
        label2 = QLabel("--or--", self)
        label3 = QLabel("Select Configruation", self)
        combo2 = QComboBox(self)
        combo2.addItem(available_configs[0])
        combo2.addItem(available_configs[1])
        combo2.addItem(available_configs[2])
        combo2.addItem(available_configs[3])
        combo2.addItem(available_configs[4])
        combo2.addItem(available_configs[5])
        combo2.activated.connect(self.new_config)
        btn1 = QPushButton("Open Serial Port", self)
        btn1.clicked.connect(self.OnClick1)
        btn2 = QPushButton("Open Configruation", self)
        btn2.clicked.connect(self.OnClick2)
        btn3 = QPushButton("Select Serial Port", self)
        btn3.clicked.connect(self.serial.selectSerialPort)



        grid.addWidget(label1, 0, 0)
        grid.addWidget(label2, 1, 0)
        grid.addWidget(label3, 2, 0)
        grid.addWidget(btn1, 0, 2)
        grid.addWidget(btn2, 2, 2)
        grid.addWidget(btn3, 0, 1)
        grid.addWidget(combo2, 2, 1)
        return grid

    def new_config(self,combo2):
        self.current_config = int(combo2)





    def OnClick1(self):

        self.controller.ser = self.serial.ser;

        if (self.controller.ser.isOpen()):

            #self.status.SetStatusText("Connected to serial port: " + self.current_port)
            #self.Hide()
            #Get the VEL type
            vel_type = self.controller.determine_vel_type() #sets vel type and config list/index
            if not vel_type:
                QMessageBox.information(self, "Reading Error!", "Could not determine green board type!\nEnsure VEL page 0 is written before considering other issues.",QMessageBox.Ok)
            else:
                self.init_config_file(vel_type)
                ####################### The Notebook Startup

                self.second_window()
                #Second_panel.init_second_menu()
                # self.parent.panel_two.Show()
                self.show()#self.parent.Layout()

                #######################
        else:
            QMessageBox.information(self, "Invalid Port", "Selected serial port could not be connected or opened",QMessageBox.Ok)



    def OnClick2(self):
        if self.current_config == 1:
            self.init_config_file(0)
        elif self.current_config == 2:
            self.init_config_file(1)
        elif self.current_config == 3:
            self.init_config_file(2)
        elif self.current_config == 4:
            self.init_config_file(3)
        elif self.current_config == 5:
            self.init_config_file(4)
        else:
            return
        #self.parent.status.SetStatusText("No serial device connected. Open only for saving files.")
        #self.Hide()
        #self.init_notebook()
        #self.init_second_menu()
        #self.Layout()
        self.second_window()
        self.show()





    def second_window(self):



        wid = QWidget()
        grid = QGridLayout()


        # setting the inner widget and layout
        grid_inner = QGridLayout(wid)
        wid_inner = QWidget(wid)

        # add the inner widget to the outer layout
        #grid.addWidget(wid_inner)

        # add tab frame to widget
        wid_inner.tab = QTabWidget(wid_inner)
        grid_inner.addWidget(wid_inner.tab)




        # create tab
        edits = []
        for i, index in enumerate(self.controller.config_index[1:]):
            if self.controller.serial_connected():
                self.controller.populate_from_vel(index[0])
            #send the pages to the NotebookTab class
            self.nb = NotebookTab(self,i+1,edits)
            wid_inner.tab.addTab(self.nb, index[0])

        wid_inner.setLayout(grid_inner)

        grid.addWidget(wid_inner,0,0)
        self.hp = HelpPanel(self)
        grid.addWidget(self.hp,0,400)
        grid.addWidget(self.cp,400,400)
        widget = QWidget()
        widget.setLayout(grid)
        self.setGeometry(0,0,800,400)
        self.move(250,50)
        self.setCentralWidget(widget)
        self.show()
    # def setup_help_panel(self):
    #     if not self.hp:  # If the HelpPanel is not already created
    #         self.hp = HelpPanel(self)
    #     self.hp.show()

    

    

    def setup_control_panel(self):
        self.cp = ControlPanel(self)



    def init_config_file(self, number):
        """
        Takes in a integer (0, 1, 2, 3, or 4) and returns the corresponding config file's list
        """
        #number = self.current_config     #Don't need to waste time, 'vv' shows which config files I need.
        number = int(number)
        if number == 0:
            fname = "evse_config.txt"
        elif number == 1:
            fname = "ev_1_config.txt"
        elif number == 2:
            fname = "ev_2_config.txt"
        elif number == 3:
            fname = "ev_3_config.txt"
        elif number == 4:
            fname = "ev_4_config.txt"
        else:
            fname = QFileDialog.getOpenFileName(None, "Open File","Text files (*.txt)")
        self.controller.set_vel_type(number)
        try:
            index, list_ = con.create_config_list(fname)
        except IOError:
            open_dlg = QFileDialog.getOpenFileName(None, "Open File",filter = "Text files (*.txt)")
            index, list_ = con.create_config_list(open_dlg.GetPath())
        self.controller.set_config_index(index)
        #print index
        self.controller.set_config_list(list_)
        #print self.controller.config_index[1:]
        self.config_index = self.controller.config_index[1:]
        print(self.config_index)
        if self.controller.get_config_list():
            self.controller.set_id_map(self.controller.make_id_map())

    def setupVelGrid(self):
        grid = QGridLayout()
        label_font = QFont("Helvetica", 12, QFont.Bold)
        label = QLabel("Current Flash Status")
        label.setFont(label_font)
        grid.addWidget(label, 0, 0, 1, 3, Qt.AlignCenter)
        grid.addWidget(self.bootloader.fixed_label, 1, 0)
        grid.addWidget(self.bootloader.variable_label, 1, 1)
        grid.addWidget(self.bootloader.btn, 1, 2)
        grid.addWidget(self.fixedinfo.fixed_label, 2, 0)
        grid.addWidget(self.fixedinfo.variable_label, 2, 1)
        grid.addWidget(self.fixedinfo.btn, 2, 2)
        grid.addWidget(self.velcode.fixed_label, 3, 0)
        grid.addWidget(self.velcode.variable_label, 3, 1)
        grid.addWidget(self.velcode.btn, 3, 2)
        return grid

    def setupGfiGrid(self):
        grid = QGridLayout()
        label_font = QFont("Helvetica", 12, QFont.Bold)
        button_font = QFont("Helvetica", 12)
        label = QLabel("RCD Board:")
        label.setFont(label_font)
        button = QPushButton("Program")
        button.setMinimumWidth(100)
        button.setMinimumHeight(40)
        button.setFont(button_font)
        button.clicked.connect(self.gfiButtonClicked)
        grid.addWidget(label, 0, 0, Qt.AlignCenter)
        grid.addWidget(button, 0, 1)
        return grid

    def gfiButtonClicked(self):
        print ("Selecting RCD S19 to program")
        start_dir = 'C://' if not self.last_gfi_dir else self.last_gfi_dir
        fname = QFileDialog.getOpenFileName(None, 'Select RCD S19 File', start_dir)[0]
        if fname:
            print ("S19 selected:")
            print (" " + str(fname))
            self.last_dir = fname
            print ("Attempting to program gfi board")
            self.gfi_programmer.gfi_execute(str(fname))
            print ("\n")
        else:
            print ("No S19 selected \n")

    def setupMenu(self):
        menubar = self.menuBar()

        refAction = QtGui.QAction('Refresh', self)
        refAction.setShortcut('Ctrl+F')
        refAction.triggered.connect(self.forceRefresh)
        fileMenu = menubar.addMenu('File')
        fileMenu.addAction(refAction)
        exitAction = QtGui.QAction('Close', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.OnClose)
        restartAction = QtGui.QAction('Restart', self)
        restartAction.triggered.connect(self.OnRestart)
        fileMenu.addAction(exitAction)
        fileMenu.addAction(restartAction)

        vprogAction = QtGui.QAction('Select VEL Programmer', self)
        vprogAction.setShortcut('Ctrl+V')
        vprogAction.triggered.connect(self.vel_programmer.selectExecutable)
        gprogAction = QtGui.QAction('Select RCD Programmer', self)
        gprogAction.setShortcut('Ctrl+G')
        gprogAction.triggered.connect(self.gfi_programmer.selectExecutable)
        serialAction = QtGui.QAction('Select Serial Port', self)
        serialAction.setShortcut('Ctrl+S')
        serialAction.triggered.connect(self.serial.selectSerialPort)
        optionsMenu = menubar.addMenu('Options')
        optionsMenu.addAction(vprogAction)
        optionsMenu.addAction(gprogAction)
        optionsMenu.addAction(serialAction)

        opAction = QtGui.QAction('Open Config File', self)
        opAction.setShortcut('Ctrl+Alt+O')
        opAction.triggered.connect(self.fixedinfo.selectConfigFile)
        savAction = QtGui.QAction('Save Config File', self)
        savAction.setShortcut('Ctrl+Alt+S')
        savAction.triggered.connect(self.fixedinfo.saveConfigFile)
        self.autoAction = QtGui.QAction('Disable Auto Increment', self)
        self.autoAction.setShortcut('Ctrl+Alt+A')
        self.autoAction.triggered.connect(self.toggleAutoIncrement)
        fixedMenu = menubar.addMenu('Fixed Information')
        fixedMenu.addAction(opAction)
        fixedMenu.addAction(savAction)
        fixedMenu.addAction(self.autoAction)

        pconnAction = QtGui.QAction('Connect To Printer', self)
        pconnAction.setShortcut('Ctrl+Alt+C')
        pconnAction.triggered.connect(self.printer.establishConnection)
        ptempAction = QtGui.QAction('Change Template', self)
        ptempAction.setShortcut('Ctrl+Alt+T')
        ptempAction.triggered.connect(self.printer.changeTemplate)
        printAction = QtGui.QAction('Print Label', self)
        printAction.setShortcut('Ctrl+P')
        printAction.triggered.connect(self.printLabel)
        ptestAction = QtGui.QAction('Print Test Label', self)
        ptestAction.setShortcut('Ctrl+Alt+P')
        ptestAction.triggered.connect(self.printer.printTestLabel)
        printMenu = menubar.addMenu('Label Printer')
        printMenu.addAction(pconnAction)
        printMenu.addAction(ptempAction)
        printMenu.addAction(ptestAction)
        printMenu.addAction(printAction)

    def setupStatusBar(self):
        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)
        self.updateStatusMessage()

    def updateStatusMessage(self):
        stat_msg_font = QtGui.QFont("Helvetica", 10)
        if VEL_MODE:
            self.status_label.setText(self.vel_programmer.statusMsg() + '&nbsp;&nbsp;&nbsp;' + self.serial.statusMsg())
        else:
            self.status_label.setText(self.gfi_programmer.statusMsg())
        self.status_label.setFont(stat_msg_font)

    def formChangeHandler(self):
        self.updateStatusMessage()

        if self.bootloader.isEnabled() and (not self.vel_programmer.found or not self.serial.connected):
            self.bootloader.disable()
        elif not self.bootloader.isEnabled() and (self.vel_programmer.found and self.serial.connected):
            self.bootloader.enable()

        if self.fixedinfo.isEnabled() and (not self.vel_programmer.found or not self.serial.connected or not self.bootloader.detected):
            self.fixedinfo.disable()
        elif not self.fixedinfo.isEnabled() and (self.vel_programmer.found and self.serial.connected and self.bootloader.detected):
            self.fixedinfo.enable()

        if self.velcode.isEnabled() and (not self.vel_programmer.found or not self.serial.connected or not self.bootloader.detected):
            self.velcode.disable()
        elif not self.velcode.isEnabled() and (self.vel_programmer.found and self.serial.connected and self.bootloader.detected):
            self.velcode.enable()

    def forceRefresh(self):
        self.bootloader.disable()
        self.fixedinfo.disable()
        self.velcode.disable()
        self.formChangeHandler()

    def toggleAutoIncrement(self):
        global AUTO_INCREMENT
        if AUTO_INCREMENT:
            print ("Disabling serial number auto-increment \n")
            AUTO_INCREMENT = False
            self.autoAction.setText("Enable Auto Increment")
        else:
            print ("Enabling serial number auto-increment \n")
            AUTO_INCREMENT = True
            self.autoAction.setText("Disable Auto Increment")

    def printLabel(self):
        print ("Trying to print a label")
        success = False
        if self.fixedinfo:
            if self.fixedinfo.config:
                if self.fixedinfo.config.last_serial_num:
                    print ("Last serial number = " + self.fixedinfo.config.last_serial_num)
                    success = True
                    self.printer.printLabel(self.fixedinfo.config.last_serial_num)
        if not success:
            print ("Last serial number is unknown; can't print label \n")

    def closeEvent(self, event):
        if self.fixedinfo.config:
            msg = "Would you like to save the last fixed info configuration?"
            reply = QMessageBox.question(self, 'Save Prompt', msg, QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.fixedinfo.saveConfigFile()
        if self.controller.serial_connected():
             self.controller.switch_to_execute()
             self.controller.ser.close()
        event.accept()

class NotebookTab(QWidget):
    def __init__(self, parent, page_index, edits):
        super(NotebookTab, self).__init__(parent)  # Calls QWidget's constructor
        self.parent = parent  # parent contains all the information needed in the controller
        self.page_index = page_index
        self.edits = edits
        self.initialize_new()

    def initialize_new(self):
        page = self.parent.controller.config_list[self.page_index]
        self.info_line_list = []

        grid = QGridLayout()  # Use QGridLayout from PySide6.QtWidgets

        widget = QWidget()  # QWidget from PySide6.QtWidgets
        # Layout of Container Widget
        layout = QVBoxLayout(self)

        for i in range(len(page)):
            field = page[i]
            self.info_line_list = AddInfo(self, grid, field, i, self.edits)  # Assuming AddInfo is defined elsewhere
            layout.addWidget(self.info_line_list)

        widget.setLayout(layout)

        scroll = QScrollArea()  # QScrollArea from PySide6.QtWidgets
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  # Use Qt from PySide6.QtCore
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)  # Set to True to resize the widget inside the scroll area
        scroll.setWidget(widget)

        # Scroll Area Layer add
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(scroll)
        self.setLayout(vLayout)



#The help panel on the StartFrame that displays the help text

class HelpPanel(QWidget):
    def __init__(self, parent):
        super(HelpPanel, self).__init__(parent)
        self.parent = parent

        # Create layout
        bsize = QVBoxLayout()

        # Create and add title label
        title = QLabel('Help Information')  # This will stay inside the panel
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)

        # Add widgets to the layout
        bsize.addWidget(title)
        bsize.addStretch(0)
        bsize.addWidget(self.text_area)
        bsize.addStretch(1)

        # Set the layout for this widget
        self.setLayout(bsize)

    def setText(self, text):
        self.text_area.setText(text)


#The control panel on the StartFrame that has the buttons for writing
class ControlPanel(QWidget):
    def __init__(self, parent):
        super(ControlPanel,self).__init__(parent)
        self.parent = parent
        self.title = QLabel('Control Panel')
        self.write_page = QPushButton("Write One Page")
        self.write_page.clicked.connect(self.OnClickPage)
        self.write_all = QPushButton("Write All Pages")
        self.write_all.clicked.connect(self.OnClickAll)
        bsize = QVBoxLayout()
        bsize.addWidget(self.title)
        bsize.addWidget(self.write_page)
        bsize.addWidget(self.write_all)
        self.setLayout(bsize)
        self.show()


    def OnClickPage(self):

        self.setFocus()
        items = (self.parent.config_index[:])
        option = []
        for i in range(0, len(items)):
            option.append(str(items[i][0]))
        item, ok = QInputDialog.getItem(self, "QInputDialog.getItem()","Which page you want to save?", option, 0, False)
        if ok and item:
            current_page_text = item      #self.parent.controller.config_index[self.parent.nb.GetCurrentPage().page_index][0]
        #Include a dlg box allowing user to cancel action
        faults = self.parent.controller.write_page_to_VEL(current_page_text)
        if faults:
            string = ""
            print("faults: ")
            print (faults)
            for fault in faults:
                if len(fault) == 2:
                    string += "Fault at id: (" + fault[0] + ") | " + self.parent.controller.fault_messages[int(fault[1])] + '\n'
                else:
                    string = fault
            dlg = QMessageBox.information(self, 'Fault', ''' Faults On Page''',QMessageBox.Ok)
            #dlg = wx.MessageDialog(self, string, "Faults On Page", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            #reply = QtGui.QMessageBox.information(self,"QMessageBox.information()", Dialog.MESSAGE)
            #dlg = QtGui.QMessageBox.information(self, 'Info Message', ''' Info Message Box''',QMessageBox.Ok)
            QMessageBox.information(self, "Page Written", "Current page written successfully!",QMessageBox.Ok)
            #dlg = wx.MessageDialog(self, "Current page written successfully!", "Page Written", wx.OK | wx.ICON_INFORMATION)
            #dlg.ShowModal()
            #dlg.close()

    def OnClickAll(self):
        self.setFocus()
        faults = []
        for item in self.parent.controller.config_index[1:]:
            faults += self.parent.controller.write_page_to_VEL(item[0])
        if faults:
            string = ""
            for fault in faults:
                if len(fault) == 2:
                    page_index, field_index = self.parent.controller.id_map[fault[0]]
                    page = self.parent.controller.config_index[page_index][0]
                    string += "Fault at id: (" + fault[0] + ") in " + page + " | " + self.parent.controller.fault_messages[fault[1]] + '\n'
                    string += "\nNOTE: Pages without faults were written correctly"
                else:
                    string = fault
            QMessageBox.information(self, "Faults", "Faults on Pages",QMessageBox.Ok)
            print (faults)
        else:
            QMessageBox.information(self, "All Pages Written", "All pages written successfully!",QMessageBox.Ok)




class AddInfo(QWidget):



    def __init__(self,parent, grid, field,i,edits):
        super(AddInfo,self).__init__(parent)
        self.parent = parent
        self.edits = edits
        self.itemindex = i

        label1 = QLabel(str(field[1]) + ' (' + str(field[0]) + ')', self)


        if field[con.ConfigFields.TYPE] is int:
            if field[con.ConfigFields.VALUE] is None:
                field[con.ConfigFields.VALUE] = str('')
            self.tc = QLineEdit(str(field[con.ConfigFields.VALUE]))  #wx.lib.intctrl.IntCtrl(self.parent, -1, field[con.ConfigFields.VALUE], pos=(x+220, y-3), size=(200, -1), allow_none=True)
            grid.addWidget(label1, i, 0)
            grid.addWidget(self.tc, i, 1)
            self.edits.append(self.tc)
            self.setLayout(grid)
            if (field[con.ConfigFields.RANGE]) and (field[con.ConfigFields.RANGE][0] == 'range'):
                self.tc.setValidator(QtGui.QIntValidator(field[con.ConfigFields.RANGE][1], field[con.ConfigFields.RANGE][2], self))#self.tc.setRange(field[con.ConfigFields.RANGE][1], field[con.ConfigFields.RANGE][2])
            self.tc.cursorPositionChanged.connect(self.mousePressEvent)
            self.tc.textChanged.connect(self.new_value)



        else:
            if field[con.ConfigFields.VALUE] is None:
                field[con.ConfigFields.VALUE] = ""
            self.tc =  QLineEdit(str(field[con.ConfigFields.VALUE]))#self.tc = wx.TextCtrl(self.parent, -1, str(field[con.ConfigFields.VALUE]), pos=(x+220, y-3), size=(200, -1))
            grid.addWidget(label1, i, 0)
            grid.addWidget(self.tc, i, 1)
            self.edits.append(self.tc)
            self.setLayout(grid)
            if (field[con.ConfigFields.RANGE]) and (field[con.ConfigFields.RANGE][0] == 'length'):
                self.tc.setMaxLength(field[con.ConfigFields.RANGE][1])
            self.tc.cursorPositionChanged.connect(self.mousePressEvent)
            self.tc.textChanged.connect(self.new_value)

    def all_clear(self):
        for edit in self.edits:
            edit.clear()



    def new_value(self):
        i = self.parent.page_index
        j = self.itemindex
        self.parent.parent.controller.config_list[i][j][5] = str(self.tc.text())



    def mousePressEvent(self):
        print (" I clicked ")
        i = self.parent.page_index
        j = self.itemindex
        print (i)
        print (j)

        hptext = self.generate_help_message(self.parent.parent.controller.config_list[i][j])
        self.parent.parent.hp.setText(hptext)


    def generate_help_message(self,field):
        restrict = ""
        if field[2] is int:
            restrict += "Type: Integer"
        #elif field[2] is str:
            #restrict += "Type: String"
        else:
            restrict += "Type: String"
            #restrict += str(field[2])
        if field[3]:
            if field[3][0] == 'range':
                restrict += "\nRange: " + str(field[3][1]) + ' - ' + str(field[3][2])
            elif field[3][0] == 'length':
                restrict += "\nMax Length: " + str(field[3][1]) + ' characters'
            elif field[3][0] == 'set':
                restrict += "\nAcceptable Values: "
                temp = ", ".join(field[3][1:])
                restrict += temp
            else:
                restrict += str(field[3])
        else:
            restrict += "\nNo Restrictions Specified"

        message = "Details:\n" + field[4] + "\n\n" + restrict
        if field[6]:
            message += '\nThis is a MANDATORY value'
        return message

    def HelpMessages(self, info):
        def OnSetFocus():
            self.GetGrandParent().GetGrandParent().hp.setText(self.generate_help_message(info))
        return OnSetFocus





###
# Main
###
def main():
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()


