
import time
import serial
import re
#import serial.tools.list_ports as serial_ports
from serial.serialutil import SerialException
import io

import logging

from messages import *
from crc import *

STX = "\x02"
ETB = "\x17"
ETX = "\x03"
LINE_FEED = "\x0A"
CONFIG_VERSION = 1
HASH_METHOD = 1

logging.basicConfig(filename='dflash_log.log',
                    filemode='w',
                    format = '%(levelname)s: %(message)s',
                    level=logging.DEBUG)

OUTPUT_RES = (
    re.compile(r"<(?P<tag>[FIESR][0-9A-Fa-f]{4})>(?P<text>.*?)</(?P=tag)>", 
               re.DOTALL),
    re.compile(r"<(?P<tag>[FIESR][0-9A-Fa-f]{4})/>", re.DOTALL)
    )


class TagInfo(object):
    name = ""
    text = ""

    def __init__(self, name, text):
        self.name = name
        self.text = text

    def __str__(self):
        return self.name


def enumerate_serial_ports():
    """
    Yields the ports
    """
    for port, desc, hw_id in serial.tools.list_ports.comports():
        yield port


def list_serial_ports():
    """
    Iterates through the serial ports available (given by enumerate_serial_ports),
    and returns a list of them
    """
    port_list = []
    for portname in enumerate_serial_ports():
        port_list.append(portname)
    return port_list


def full_port_name(portname):
    """
    Input: a portname
    Output: the full port name
    """
    m = re.match('^COM(\d+)$', portname)
    #If this is a windows port
    if m:
        if int(m.group(1)) < 10:
            return portname
        else:
            return '\\\\.\\' + portname
    #If this is not a window port
    else:
        return portname

        
def connect_to_port(port_name):
    try:
        ser = serial.Serial(full_port_name(port_name), 115200, timeout=0.05, xonxoff=True)
        return ser
    except SerialException as e:
        logging.warning("Failed to open serial port")
        return None
    logging.warning("Selected serial port not available")
    return None   


def wait_for_response(ser, msg=None, desired_tag=None, timeout=0.1, max_length=500):
    """
    Input: needs a serial connection (ser), can take in a message (msg), a desired_tag,
           timeout value, and max_length for the response from the serial connection
    Output: returns found_response - starts as False but can be True or an instance of TagInfo
                    messages - starts as an empty list, but can contain instances of TagInfo
    """
    logging.debug("Waiting for serial response...")
    if desired_tag:
        logging.debug("Looking for tag: %s" % desired_tag)
    if msg:
        logging.debug("Correct response should contain '%s'" % msg)
    logging.debug("Will timeout after %d seconds" % timeout)
    logging.debug("Will give up if response exceeds %d characters" % max_length)

    exceeded_timeout = False  # checking for timeout ensures the process won't take too long
    exceeded_max_length = False  # checking for max length makes sure we eventually stop
    found_response = False  # once we have found the desired response, we can exit
    response = ""
    start_time = time.time()
    elapsed_time = 0
    count = 0
    messages = []

    while (not found_response) and (not exceeded_timeout) and (not exceeded_max_length):
        while (ser.inWaiting() > 0) and (not exceeded_max_length):
            char = ser.read(1)  # read one character
            response += char  # add the character to the response
            count += 1
            if (char == '\n'):  # if our character is a newline
                if (desired_tag):  # if desired_tag was given as a parameter
                    for curr_re in OUTPUT_RES:
                        parsed = curr_re.search(response)
                        if parsed:
                            tag, text = "",""
                            groups = parsed.groups()
                            tag = groups[0]
                            if len(groups) == 2:
                                text = groups[1]
                            tag_info = TagInfo(tag, text)
                            messages.append(tag_info)
                            if (tag == desired_tag):
                                logging.info("FOUND DESIRED TAG")
                                found_response = tag_info
                                response = ""
                            break
                elif msg in response:
                    logging.info("FOUND MESSAGE")
                    found_response = True
            if count > max_length:
                exceeded_max_length = True
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            exceeded_timeout = True
    logging.info(response)
    logging.info("Correct response: " + str(found_response))
    logging.debug("Response took %0.2f seconds (timeout=%f)" % (elapsed_time, exceeded_timeout))
    return (found_response, messages)


def switch_to_bootloader(ser):
    """
    Input: takes in an open serial connection (ser) and connects to the bootloader
           if not already connected.
    Output: returns a boolean value whether it was successful or not
    """
    logging.debug("Switching to bootloader...")
    ser.flushOutput()
    ser.flushInput()
    logging.debug("Sending carriage return, seeing if bootloader responds")
    ser.write('\r')
    responded, tags = wait_for_response(ser, desired_tag=Messages.MAIN_MENU)
    i = 3  # try 3 times in case green board is sleeping 
    while (not responded) and (i > 0):
        logging.debug("Didn't respond, sending '*1#' over serial")
        ser.flushInput()
        ser.write("*1#")
        time.sleep(.5)
        ser.flushInput()
        ser.write('\r')
        responded, tags = wait_for_response(ser, desired_tag=Messages.MAIN_MENU)
        i - 1
    return (responded)


def switch_to_program_execute(ser):
    if switch_to_bootloader(ser):
        ser.flushInput()
        ser.write('d')
        print("success")
    else:
        print("STILL IN BOOTLOADER, SWITCH TO PROGRAM FROM TERA TERM")

def serial_is_open(ser):
    """
    Takes in a serial connection (ser), returns a boolean whether it's open or not
    """
    if ser:
        return ser.isOpen()
    else: 
        return ser


def check_fixed_info_written(ser, page_number):
    """
    Input: ser - serial connection
           page_number - page on which the desired information is located
    Output: returns the info on the desired page if found, returns False otherwise
    NOTES: must be connected to the bootloader for the function to work properly
    """
    ser.flushInput()
    if page_number == 'ff':
        ser.write('cff')
    else:
        ser.write('c%02X' % page_number)
    found, tags = wait_for_response(ser, desired_tag=Messages.DFLASH_DATA, max_length=65536)
    if found:
        return found.text
    else:
        return False


def print_fixed_info(info, format=0):
    """
    Takes in a string (info) formatted for the board, and a
    format value (format - optional) to specify how the output should look
    """
    #Format 0
    string = ""
    if format == 0:
        for i, ch in enumerate(info):
            if ((i % 10) == 0):
                "".join([string, "\n"])
            if (ord(ch) >= 32 and ord(ch) < 128):
                "".join([string, "%02x:%c " % (ord(ch), ch)])
            else:
                "".join(["%02x:  " % ord(ch)])
        "".join([string, "\n"])
    #Format 1
    else:
        for i, ch in enumerate(info):
            if (ord(ch) >= 32 and ord(ch) < 128):
                "".join([string, "%c" % ch])
            else:
                "".join([string, "\n"])
        "".join([string, "\n"])
    return string

###USED FOR THE READ FUNCTION
def validate_crc(response):
    stx_pos = response.find(STX)
    etb_pos = response.find(ETB)
    etx_pos = response.find(ETX)
    print(stx_pos, etb_pos, etx_pos)
    crc_valid_p = False
    if (stx_pos >= 0) and (etb_pos >= 0) and (etx_pos >= 0):
        if int(response[etb_pos+1], 16) == HASH_METHOD:
            computed_crc = crc(response[stx_pos+1:etb_pos])
            found_crc = int(response[etb_pos+2:etx_pos], 16)
            if (computed_crc == found_crc):
                crc_valid_p = True
    return crc_valid_p

###USED FOR THE READ FUNCTION
def create_fixed_info_dict(response):
    """
    Input: takes in a string formatted for the board (response)
    Output: returns a dictionary of the id (key) and the information (value)
    """
    dictionary = {}
    block_start = 2
    while response[block_start] != ETB:
        block_end = response.find(LINE_FEED, block_start)
        key = response[block_start:block_start+2]
        value = response[block_start+2:block_end].decode("utf8")
        if value != "":
            dictionary[key] = value
        block_start = block_end + 1
    return dictionary


def read(ser, page_number):
    """
    Input: ser - serial connection
           page_number - the page number of the information on the board
    Output: returns a dictionary of the id (key) and the information (value)
            if there was information on the page, else, returns None
    """
    logging.debug("Reading fixed information")
    if serial_is_open(ser) and switch_to_bootloader(ser):
        response = check_fixed_info_written(ser, page_number)
        if not response:
            logging.info("No fixed information written")
        else:
            logging.info("Response: " + response)
            logging.info(print_fixed_info(response))
            if validate_crc(response):
                return create_fixed_info_dict(response)
            else:
                logging.warning("Read information was not validated by crc")
    else:
        logging.info("Could not read fixed information")
    return None


###USED FOR THE WRITE FUNCTION
def format_dict_to_string(dictionary):
    """
    Input: takes in a dictionary of id's (key) and information (value) and formats
           the data to be written to the board
    """
    data = io.StringIO()
    for key, value in dictionary.iteritems():
        value = str(value).encode("utf-8")
        data.write(key[:2])
        data.write(value)
        data.write(LINE_FEED)
    data = data.getvalue()
    crc_str = crc(data)
    result = "%x%s%s%s%x%04X%s" % (CONFIG_VERSION, STX, data, ETB, HASH_METHOD, crc_str, ETX)
    return result


###USED FOR THE WRITE FUNCTION
def write_to_VEL(ser, page_number, formatted_string):
    """
    Input: ser - serial connection
           page_number - the page number of the information on the board
           formatted_string - a string containing the special characters and
                              information formatted for the board
    Output: writes to the board, returns True if successful, or False if unsuccessful
    NOTES: must be in the bootloader for this function to work
    """
    ser.flushInput()
    ser.write('b%02X%04X' % (page_number,len(formatted_string)))
    found, tags = wait_for_response(ser, desired_tag=Messages.DFLASH_SEND_DATA)
    if found:
        logging.info("Sending fixed information...")
        logging.info(print_fixed_info(formatted_string))
        for char in formatted_string:
            ser.write(char)
            time.sleep(.001)
        return True
    else: #optional
        logging.warning("ERROR!! " + str([tag.name for tag in tags])) #optional
        return False


###USED FOR THE WRITE FUNCTION
def confirm_written_correctly(ser, page_number, formatted_string):
    """
    Input: ser - serial connection
           page_number - the page number of the information on the board
           formatted_string - a string containing the special characters and
                              information formatted for the board
    Output: does not return anything, checks if the information was written correctly
    """
    switch_to_bootloader(ser)
    written_info = check_fixed_info_written(ser, page_number)
    if written_info:
        for ch1, ch2 in zip(formatted_string, written_info):
            if (ch1 != ch2):
                logging.warning("Written incorrectly")
                logging.warning("Attempted:\n" +
                              print_fixed_info(formatted_string) +
                              "Written:\n" +
                              print_fixed_info(written_info))
                return False
        return True
    else:
        return False


def write(ser, page_number, info_dict):
    formatted_data = format_dict_to_string(info_dict)
    if serial_is_open(ser) and switch_to_bootloader(ser):
        response = check_fixed_info_written(ser, page_number)
        overwrite_priveledges = True
        if (not response) or overwrite_priveledges:
            written = write_to_VEL(ser, page_number, formatted_data)
            if written:
                if confirm_written_correctly(ser, page_number, formatted_data):
                    return True
    logging.info("Could not write fixed information")
    return False


if __name__ == '__main__':
    # a = list_serial_ports()
    # for i, item in enumerate(a):
    # 	a[i] = fullPortName(str(item))
    # print a[0]
    

    # ser = select_serial_port(10, list_serial_ports())
    # switch_to_bootloader(ser)
    # d = {}
    # for i in range(7):
    #     r = read(ser, i)
    #     if r:
    #         d.update(r)
    # print d

    # # for i in range(2,10):
    # #     write(ser, i, {'aa':'hello'})
    # print ser.isOpen()
    # if ser.isOpen():
    #     ser.close()
    pass