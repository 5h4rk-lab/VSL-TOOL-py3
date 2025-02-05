#!/usr/bin/python2.7
#--coding:utf-8 --

import serial_connect as sc
# import config_evse
# import config_ev_1
# import config_ev_2
import os
import logging
#import wx

class ConfigFields:
    ID        = 0
    TITLE     = 1
    TYPE      = 2
    RANGE     = 3
    HELP_TEXT = 4
    VALUE     = 5
    MANDATORY = 6
    
class Controller(object):

    def __init__(self):
        self.checker = validator()
        # 0: "String entered where integer needed ""
# 1: "Field required but no information given!",
# 2: "Value entered is too long, out of range, or not a permitted value!"
        self.fault_messages = ["String entered where integer needed!", "Field required but no information given!", "Value entered is not permitted!"]
        self.ser = None
        self.config_index = None
        self.config_list = None
        self.id_map = None
        self.vel_type = None

    def get_serial_port(self):
        return self.ser

    def set_serial_port(self, port_name):
        self.ser = sc.connect_to_port(port_name)
    
    def get_config_list(self):
        return self.config_list

    def set_config_list(self, list_):
        self.config_list = list_
    
    def get_config_index(self):
        return self.config_index
    
    def set_config_index(self, i_list):
        self.config_index = i_list

    def set_id_map(self, map_):
        self.id_map = map_

    def set_vel_type(self, number):
        self.vel_type = number

    def list_serial_ports(self):
        return sc.list_serial_ports()
    
    def switch_to_execute(self):
        sc.switch_to_program_execute(self.ser)

    def disconnect_serial(self):
        if self.ser is not None and self.ser.isOpen():
            self.ser.close()
            print ('Disconnected serial port')
    
    ### Moved to dflash_gui to add open_file functionality ###
    # def init_config_file(self, number):
    #     """
    #     Takes in a integer (0, 1, or 2) and returns the corresponding config file's list
    #     """
    #     number = int(number)
    #     #--TEMPORARY - Set to EVSE Automatically--#
    #     # if number>=0 and number<=2:
    #     #     number = 0
    #     #-----------------------------------------#
    #     if number == 0:
    #         fname = "evse_config.txt"
    #     elif number == 1:
    #         fname = "ev_1_config.txt"
    #     elif number == 2:
    #         fname = "ev_2_config.txt"
    #     self.vel_type = number
        
    #     try:
    #         self.config_index, self.config_list = create_config_list(fname)
    #     except IOError:
    #         open_dlg = wx.FileDialog(self, message="Choose a configuration file",
    #                                  defaultDir=os.getcwd(),
    #                                  defaultFile="",
    #                                  wildcard="Text (*.txt)|*.txt|",
    #                                  style=wx.OPEN | wx.CHANGE_DIR)
    #         if open_dlg.ShowModal() == wx.ID_OK:
    #             self.config_index, self.config_list = create_config_list(open_dlg.GetPath())
    #     if self.config_list:
    #         self.id_map = self.make_id_map()

    def determine_vel_type(self):
        """
        Output: retunrs a boolean telling if page 0 of the config was correctly read
        """
        d = sc.read(self.ser, 'ff')
        if d is not None and 'vv' in d:
            return d['vv'][-1]
        return None

    def serial_connected(self):
        """
        Output: returns true if there is a serial port connected and open, else false
        """
        if self.ser:
            if self.ser.isOpen():
                return True
        return False


    def make_id_map(self):
        """
        Input: a list from a config file and maps the id's to their location.
        Output: returns a dictionary of key: id, value: location
                #returns a function that takes an id and returns an id's list
        """
        id_map = {}
        for i, page in enumerate(self.config_list):
            for j, field in enumerate(page):
                id_map[field[ConfigFields.ID]] = (i, j)
        return id_map
        # def hash_list(id_):
        #     p = id_map[id_]
        #     return self.config_list[p[0]][p[1]]
        # return hash_list
        
    
    # def validate_range(self, range_tuple):
    #     def validate2(value):
    #         return (value >= range_tuple[1]) and (value <= range_tuple[2])
    #     return validate2
    
    # _validators = {
    #     "range": validate_range,
    #     "length": validate_length
    # }

    ######################################################
    #Not currently used
    def page_validation(self, page_list):
        """
        Input: takes in a list of lists of ids & info for a page, also takes in a 
            validator, could be an old one, or default is a new one
        Output: returns a list of faults, with the (location, and the fault message value),
            If the fault list is empty, then the page is completely validated and 
            empty list is returned
        """
        faults = []
        #fault_messages 1: "Field required but no information given!",
        #               2:  "Value entered is too long, out of range, or not a permitted value!"
        for i, field in enumerate(page_list):
            # If the field is mandatory but no information was entered
            if(field[ConfigFields.MANDATORY] is True) and (field[ConfigFields.VALUE] is None):
                faults.append((i, 1))
            # If there is entered information
            elif field[ConfigFields.VALUE] is not None:
                # Uses the range_checker to see if the value is in range
                if not self.checker(field[ConfigFields.RANGE])(field[ConfigFields.VALUE]):
                    faults.append((i, 2))
        return faults

    def complete_validation(self):
        faults = []
        for i, page in enumerate(self.config_list):
            page_faults = self.page_validation(page)
            if page_faults != []:
                logging.info("Page %d faults:" % i)
                logging.info(page_faults)
                faults.append((i, page_faults))
        return faults
    ######################################################

    def page_to_dictionary(self, page_list):
        """
        Input: page_list: one of the first-inner lists from a config file
        Output: returns a dictionary of id:value if all the values were valid
                returns a list tuples of faults (id, fault_message_number) if
                    one or more of the values were not valid
        NOTES: First validates the type (fault should only arise from strings 
               entered for ints)
               Second checks that all mandatory fields are filled
               Third checks that value is in range
               If no faults arose, then integers are converted to hexadecimal
                   and all values are put in the dictionary
        """
        valid_values = {}
        faults = []
        #fault_messages 
        # 0: "String entered where integer needed"
        # 1: "Field required but no information given!",
        # 2: "Value entered is too long, out of range, or not a permitted value!"
        for item in page_list:
            id_ = item[ConfigFields.ID]
            type_ = item[ConfigFields.TYPE]
            value = item[ConfigFields.VALUE]
            if (value is not None ):     #if (value is not None ) and (value is not '')
                value = type_validation(id_, type_, value, faults)
            elif item[ConfigFields.MANDATORY] is True: #Field is mandatory and value is None
                faults.append((id_, 1))
            if (value is not None) and (value != "") and (not self.checker(item[ConfigFields.RANGE])(value)):
                faults.append((id_, 2))
            if len(faults) == 0:  # only adds to the dictionary if we haven't found a fault
                if (type_ is int) and (value is not None):
                    # Make int values either 2 characters or 4 characters 
                    # long due to a bug in the handling of hev values
                    # having an odd length
                    if (value & 0xFFFFFF00):
                        value = "%04X" % value
                    else:
                        value = "%02X" % value
                if value is None:
                    value = ""
                if len(id_) == 2:
                    valid_values[id_] = value
                else: #len(id_) == 3 For now, this is to combine the address (all strings or None)
                    value = value.strip("|")  # remove any user entered pipe characters
                    if id_[:2] in valid_values:
                        valid_values[id_[:2]] = valid_values[id_[:2]] + "|" + value
                    else:
                        valid_values[id_[:2]] = value
        if not faults:
            return valid_values
        else:
            return faults

    def page_title_to_numbers(self, page_title):
        """
        Input: page_title - the title of any page from the config_list
        Output: returns the page_number on the VEL and index of page information
                in the config_list
        """
        for i, item in enumerate(self.config_index):
            if item[0] == page_title:
                page_number = item[1]
                page_list_index = i
                return page_number, page_list_index

    def write_page_to_VEL(self, page_title): #page_number, page_list):
        """
        Input: page_title - the title of any page from the config_list
        Output: returns a list of faults, if the list is empty, there were
                no faults and the page was written to the VEL board.
        """
        page_number, page_list_index = self.page_title_to_numbers(page_title)
        output = self.page_to_dictionary(self.config_list[page_list_index])
        if type(output) is dict:
            written = sc.write(self.ser, page_number, output)
            if written:
                return []
            else:
                return ["No user faults, but page was not written"]
        else: # There are faults on the page
            return output
    
    def populate_from_dictionary_hex(self, dictionary, page_list_index):
        """
        Input: dictionary - a {id:value} dictionary with number values as hex
        Output: updates the config_list, returns a list of unrecognized keys
        """
        unrecognized = []
        for key, value in dictionary.items():
            if key == 'ad' and value is not None:  # Update the address fields
                adr_lines = value.split('|')  # Split the address into multiple parts

                # 🛠 **NEW: Ensure 'ad1', 'ad2', etc., exist in self.id_map**
                for i in range(len(adr_lines)):  
                    key_name = f"ad{i+1}"  # Creates 'ad1', 'ad2', etc.
                    if key_name not in self.id_map:  
                        self.id_map[key_name] = (page_list_index, len(self.config_list[page_list_index]))

                # Now call split_address() since the necessary keys exist
                self.split_address(key, value)

            elif key in self.id_map:
                page_index, field_index = self.id_map[key]
                if self.config_list[page_index][field_index][ConfigFields.TYPE] is int and value:  
                    value = int(value, 16)  # Convert hex values to int
                self.config_list[page_index][field_index][ConfigFields.VALUE] = value
            else:
                new_list = [key, "UNRECOGNIZED VALUE", str, None, "This value was in DFLASH but might be new or preexisting. If it's a number, it should be hexadecimal.", value, False]
                unrecognized.append(key)
                self.config_list[page_list_index].append(new_list)
                self.id_map[key] = (page_list_index, len(self.config_list[page_list_index]) - 1)

        return unrecognized

        # unrecognized = []
        # for key, value in dictionary.items():
        #     if (key == 'ad') and (value is not None): #Update the address fields
        #         self.split_address(key, value)
        #     elif key in self.id_map:
        #         page_index, field_index = self.id_map[key]
        #         if (self.config_list[page_index][field_index][ConfigFields.TYPE] is int) and (value): #convert hex values to int
        #             value = int(value, 16)
        #         self.config_list[page_index][field_index][ConfigFields.VALUE] = value
        #     else:
        #         new_list = [key, "UNRECOGNIZED VALUE", str, None, "This is a value that was on the DFLASH but may be new or preexisting from.  If this is supposed to be a number, it should be in hexidecimal", 
        #                     value, False]
        #         unrecognized.append(key)
        #         self.config_list[page_list_index].append(new_list)
        #         self.id_map[key] = (page_list_index, len(self.config_list[page_list_index]) - 1)
        # return unrecognized

    # def split_address(self, key, value):
    #     adr_lines = value.split('|')
    #     if len(adr_lines) == 6:
    #         page_index, field_index = self.id_map['ad1']
    #         for i, line in enumerate(adr_lines):
    #             self.config_list[page_index][field_index + i][ConfigFields.VALUE] = line
    
        

    def split_address(self, key, value):
        adr_lines = value.split('|')
        if len(adr_lines) == 6:
            page_index, field_index = self.id_map.get('ad1', (None, None))
    
            if page_index is None or field_index is None:
                print(f"Error: 'ad1' not found in id_map. Available keys: {self.id_map.keys()}")
                return
            
            if page_index >= len(self.config_list):
                print(f"Error: page_index {page_index} out of range for config_list (size={len(self.config_list)})")
                return
    
            # 🔹 Determine number of fields in ConfigFields
            if isinstance(ConfigFields, dict):  
                num_fields = len(ConfigFields.keys())  # Dictionary case
            elif hasattr(ConfigFields, '__len__'):  
                num_fields = len(ConfigFields)  # List or tuple case
            else:  
                num_fields = len([attr for attr in dir(ConfigFields) if not attr.startswith("__")])  # Enum or class case
    
            # 🔹 Expand the list if needed
            while field_index + len(adr_lines) > len(self.config_list[page_index]):
                self.config_list[page_index].append([None] * num_fields)  
    
            # ✅ Assign values safely
            for i, line in enumerate(adr_lines):
                self.config_list[page_index][field_index + i][ConfigFields.VALUE] = line






    def populate_from_vel(self, page_title):
        """
        Input: page_title - the title of any page from the config_list
        Output: does not return anything, but reads fixed_information from
                the VEL and updates the config_list
        NOTES: Converts hexadecimal values from the VEL to integers for the 
               config_list
        """
        page_number, page_list_index = self.page_title_to_numbers(page_title)
        vel_dictionary = sc.read(self.ser, page_number)
        if vel_dictionary is not None:
            unrecognized = self.populate_from_dictionary_hex(vel_dictionary, page_list_index)
            return unrecognized
        else:
            return False

    def save_user_values(self, directory):
        file_list = []
        output_list = []
        # look through the pages and return faults if there were any, if not, return a list of dictionaries
        for page in self.config_list[1:]:
            output = self.page_to_dictionary(page)
            if type(output) is dict:
                output_list.append(output)
            else:
                return output
        # save the list of dictionaries as files of DFlash ready strings
        for i, dictionary in enumerate(output_list):
            string = sc.format_dict_to_string(dictionary)
            fname = 'b%02X%04X' % (self.config_index[i+1][1], len(string)) + '.dflash'
            file_list.append(fname)
            with open(directory + '/' + fname, 'wb') as f:
                f.write(string)
        # save the index file for the populate from save function
        with open(directory + '/' + "dflash_save_index.txt", 'wb') as f:
            information = "Do not delete this file, needed to populate from save in DFlash Program\n"
            information += "type:" + str(self.vel_type) + '\n'
            information += "~".join(file_list)
            f.write(information)

    def populate_from_save_dir(self, directory):
        # list all files in chosen directory
        files = os.listdir(directory)
        unrecognized = []
        # check if there is a save index in the directory
        if "dflash_save_index.txt" in files:
            #open the index file
            with open(directory + '/' + "dflash_save_index.txt", 'rb') as f:
                # read the first line, which is just a message
                f.readline()
                # read the second line, which is the type of board and check it against the current type
                if self.vel_type == int(f.readline().replace("type:", "")):
                    # list all the filenames
                    filenames = f.readline().split('~')
                    for i, fname in enumerate(filenames):
                        # open each file and read it
                        with open(directory + '/' + fname, 'rb') as g:
                            text = g.read()
                            unrecognized.append(self.populate_from_dictionary_hex(sc.create_fixed_info_dict(text), i+1))
        return unrecognized


def create_config_list(config_file):
    """
    Input: a .txt file that is formatted to be a configuration file.
    Output: a index list and list of list in the same format as the old config list
    """
    config_list = []  # This will become the same list of list as the old config.py files
    config_index = []  # This will become the same index list as the old config.py files
    curr_page = -1  # This is to count how many pages we've found
    with open(config_file, 'r') as cf:
        line = cf.readline().strip()  # read a line, strip outside whitespace
        while(line):
            semicolon = line.find(';')  # find the first semi-colon in a line
            if semicolon >= 0:  # if the semi-colon was found...
                line = line[:semicolon].rstrip() #only use string before the semicolon, stripping outside whitespace
            #Title line
            if line.find(':::') == 0:
                page_title, page_index = line.lstrip(':').split(',')
                try:
                    page_index = int(page_index)
                except ValueError:
                    page_index = page_index.strip()
                config_index.append([page_title.strip(), page_index])
                config_list.append([])
                curr_page += 1
            elif curr_page >= 0:
                #Field lines
                if line.find('+') == 0:  
                    field = [line.lstrip('+')]
                    i = 1
                    #Get info after id
                    while (i < 7):
                        line = cf.readline().strip()
                        semicolon = line.find(';')
                        if semicolon >= 0:
                            line = line[:semicolon].rstrip()
                        if i == 2: #Type
                            if line == 'string' or line == 'str':
                                field.append(str)
                            elif line == 'integer' or line == 'int':
                                field.append(int)
                            else:
                                field.append(line)
                        elif i == 3: #Range Value
                            values = line.split(',')
                            if values[0] == 'range':
                                values[1] = int(values[1])
                                values[2] = int(values[2])
                                field.append(tuple(values))
                            elif values[0] == 'length':
                                values[1] = int(values[1])
                                field.append(tuple(values))
                            elif values[0] == 'set':
                                for j, val in enumerate(values):
                                    values[j] = val.strip()
                                field.append(tuple(values))
                            #Add condition for regex here
                            else:
                                field.append(None)
                        elif i == 5: #Default Value
                            if line == '':
                                field.append(None)
                            else:
                                if field[2] is int:
                                    line = int(line)
                                field.append(line)  # note that numbers will be strings
                        elif i == 6: #Mandatory Value
                            if line == 'True' or line == 'true':
                                field.append(True)
                            else:
                                field.append(False)
                        else: #Title, Help Text
                            field.append(line)
                        i+=1
                    config_list[curr_page].append(field)
            ###
            line = cf.readline().strip() #read a line
    return config_index, config_list

# def converter(): #possible helper for converting config_list from text
#     def field_selector(i)


def validator():
    def range_checker(range_tuple):
        if not range_tuple:
            def validate1(value):
                return True
            return validate1
        elif range_tuple[0] == "range":
            def validate2(value):
                return (value >= range_tuple[1]) and (value <= range_tuple[2])
            return validate2
        elif range_tuple[0] == "length":
            def validate3(value):
                return len(value) <= range_tuple[1]
            return validate3
        elif range_tuple[0] == "set":
            def validate4(value):
                i = 1
                while (i < len(range_tuple)):
                    if range_tuple[i] == value:
                        return True
                    i += 1
                return False
            return validate4
        # elif range_tuple[0] == "regex":
        #     def validate5(value):
    return range_checker

def type_validation(id_, type_, value, fault_list):
    """
    Input: id_ - the two character id
           type_ - the type that the data should be
           value - the data itself
           fault_list - a list of faults that this function can add to
    Output: returns the value as its correct type, adds any faults to the
            fault_list
    NOTES: used for the page_to_dictionary method
    """
    #Should floating point values be checked if entered?
    faults_list = []    #add by bkc
    if type(type_) is type:
        try: 
            value = type_(value)
        except ValueError:
            logging.info("User Input Error! String value entered in place of integer")
            faults_list.append((id_, 0))
            value = None
    return value

if __name__ == '__main__':
    #Code to wipe the writable pages of fixed information on the VEL board
    # con = Controller()
    # l = con.list_serial_ports()
    # if len(l) == 1:
    #     con.set_serial_port(l[0])
    #     for i in range(2,7):
    #         sc.write(con.ser, i, {})
    # else:
    #     print "Nothing Happened"
    config_index, config_list = create_config_list('ev_1_config.txt')
    print ('HERE IS OUTPUT')
    print (config_list)
