import os
import wx
import wx.lib.intctrl
import dflash_controller as con


class StartFrame(wx.Frame):
    
    #Initialization------------------------------------------------------------
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(700, 400))
        self.parent = parent
        self.initialize()

    def initialize(self):
        self.controller = con.Controller()
        self.setup_menu_1()
        self.setup_status_bar()
        self.setup_panel_one()
        self.setup_outside_sizer()
    
    def setup_menu_1(self):
        self.menu_bar = wx.MenuBar()
        # 1st menu from the left (File)
        self.file_menu = wx.Menu()
        self.file_menu_exit = self.file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+q", " Terminate the program")
        self.file_menu_restart = self.file_menu.Append(-1, "Restart", "Restart the program" )
        
        # Add menu to the menu bar
        self.menu_bar.Append(self.file_menu, "&File")
        self.SetMenuBar(self.menu_bar)
        # Menu events
        self.Bind(wx.EVT_MENU, self.OnClose, self.file_menu_exit)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_MENU, self.OnRestart, self.file_menu_restart)
    
    def setup_status_bar(self):
        #Setup the status bar
        self.status = self.CreateStatusBar()
        self.status.SetStatusText("Not connected to a serial port")
    
    def setup_panel_one(self):
        #Panel initialization (the frame is the parent)
        self.panel_one = SerialSelect(self)

    def setup_outside_sizer(self):
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.panel_one, 1, wx.EXPAND)
        # self.sizer.Add(self.panel_two, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
        self.Show(True)
    #--------------------------------------------------------------------------
    
    #Future initializations in the same frame
    #Called in SerialSelect.OnClick()
    def init_notebook(self):
        self.setup_notebook()
        self.setup_help_panel()
        self.setup_control_panel()
        self.setup_inside_sizer()

    def setup_notebook(self):
        #Create the notebook (StartFrame is the parent)
        self.nb = wx.Notebook(self)
        #Populate the config file with already written values
        for i, index in enumerate(self.controller.config_index[1:]):
            if self.controller.serial_connected():
                self.controller.populate_from_vel(index[0])
            #send the pages to the NotebookTab class
            self.nb.AddPage(NotebookTab(self.nb, i+1), index[0])

    def setup_help_panel(self):
        self.hp = HelpPanel(self)

    def setup_control_panel(self):
        self.cp = ControlPanel(self)

    def setup_inside_sizer(self):
        self.inner_sizer = wx.BoxSizer(wx.VERTICAL)
        self.inner_sizer.Add(self.hp, 1, wx.EXPAND)
        self.inner_sizer.Add(self.cp, 1, wx.EXPAND)
        #Fit the notebook to to the frame
        self.sizer.Add(self.nb, 2, wx.EXPAND)
        self.sizer.Add(self.inner_sizer, 1, wx.EXPAND)
        #self.SetSizer(self.sizer) #possibly needed

    def init_second_menu(self):
        # 2nd menu from the left (Fields)
        self.field_menu = wx.Menu()
        #Read Save
        self.field_menu_read_save = self.field_menu.Append(wx.ID_ANY, "Populate fields from save\tCtrl+p", "Populates the fields from a previously saved file" )
        self.Bind(wx.EVT_MENU, self.OnReadSave, self.field_menu_read_save)
        #Write Save
        self.field_menu_write_save = self.field_menu.Append(wx.ID_ANY, "Save current fields\tCtrl+s", "Saves the current information in fields on all pages")
        self.Bind(wx.EVT_MENU, self.OnWriteSave, self.field_menu_write_save)
        
        self.field_menu.AppendSeparator()
        #Clear Fields
        self.field_menu_clear = self.field_menu.Append(wx.ID_ANY, "Clear fields\tCtrl+d", "Clear all text fields")
        self.Bind(wx.EVT_MENU, self.OnClear, self.field_menu_clear)
        #Repopulate Fields
        if self.controller.serial_connected():
            self.field_menu_repopulate = self.field_menu.Append(wx.ID_ANY, "Repopulate fields\tCtrl+r", "Repopulate fields with information written on board")
            self.Bind(wx.EVT_MENU, self.OnRepopulate, self.field_menu_repopulate)
        # Add menu to the menu bar
        self.menu_bar.Append(self.field_menu, "Fields")
        self.SetMenuBar(self.menu_bar)
        
    # Methods
    def OnClear(self, event):
        tabs = self.nb.GetChildren()
        for tab in tabs:
            lines = tab.scroll.GetChildren()
            for line in lines:
                if type(line) is InfoLine:
                    if type(line.tc) is wx.TextCtrl:
                        line.tc.SetValue("")
                        line.field[con.ConfigFields.VALUE] = ""
                    elif type(line.tc) is wx.lib.intctrl.IntCtrl:
                        line.tc.SetValue(None)
                        line.field[con.ConfigFields.VALUE] = None

    def OnRepopulate(self, event):
        unrecognized_lists = []
        # Walk through index list in config file
        for title, page_num in self.controller.config_index[1:]:
            # Populate each page from the VEL, get any unrecognized values
            # An unrecognized value is one that is not currently in the config_list
            unrecognized = self.controller.populate_from_vel(title)
            unrecognized_lists.append(unrecognized)
        tabs = self.nb.GetChildren()
        for i, tab in enumerate(tabs):
            lines = tab.scroll.GetChildren()
            for line in lines:
                if type(line) is InfoLine:
                    line.tc.SetValue(line.field[con.ConfigFields.VALUE])
                elif type(line) is AdditionalLine:
                    if line.IsShown():
                        line.tc.SetValue(line.field[con.ConfigFields.VALUE])
                    elif (not line.IsShown()) and (line.key in unrecognized_lists[i]):
                        line.Show(True)
                        line.st.Show(True)
                        line.tc.Show(True)
                        line.kill_button.Show(True)
                        page_index, field_index = self.controller.id_map[line.key]
                        line.field = self.controller.config_list[page_index][field_index]
                        line.tc.SetValue(line.field[con.ConfigFields.VALUE])
                        unrecognized_lists[i].remove(line.key)

    # def OnReadSave2(self, event):
    #     ensure_directory("./user_save_files" + str(self.controller.vel_type))
    #     files = os.listdir("./user_save_files" + str(self.controller.vel_type))
    #     dlg = wx.SingleChoiceDialog(self, "Choose file to populate fields", "Populate From Saved File", files, wx.CHOICEDLG_STYLE)
    #     if dlg.ShowModal() == wx.ID_OK:
    #         if dlg.GetringSelection() != "":
    #             self.controller.populate_from_save_dir("./user_save_files" + str(self.controller.vel_type) + "/" + dlg.GetStringSelection())

    def OnReadSave(self, event):
        dlg = wx.DirDialog(self, "Choose a directory:", style=wx.DD_DEFAULT_STYLE | wx.DD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            unrecognized_lists = self.controller.populate_from_save_dir(dlg.GetPath().replace('\\', '/'))
            # Check if the folder had any .dflash files
            if unrecognized_lists == []:
                msg_dlg = wx.MessageDialog(self, "No save index file for this type of board found in this directory!", "Save Index Not Found!", wx.OK | wx.ICON_WARNING)
                msg_dlg.ShowModal()
                msg_dlg.Destroy()
                return 
            # Update the GUI from the config_file that has new info
            tabs = self.nb.GetChildren()
            for i, tab in enumerate(tabs):
                lines = tab.scroll.GetChildren()
                for line in lines:
                    if type(line) is InfoLine:
                        line.tc.SetValue(line.field[con.ConfigFields.VALUE])
                    elif type(line) is AdditionalLine:
                        if line.IsShown():
                            line.tc.SetValue(line.field[con.ConfigFields.VALUE])
                        elif (not line.IsShown()) and (line.key in unrecognized_lists[i]):
                            line.Show(True)
                            line.st.Show(True)
                            line.tc.Show(True)
                            line.kill_button.Show(True)
                            page_index, field_index = self.controller.id_map[line.key]
                            line.field = self.controller.config_list[page_index][field_index]
                            line.tc.SetValue(line.field[con.ConfigFields.VALUE])
                            unrecognized_lists[i].remove(line.key)
                if unrecognized_lists[i]:
                    for key in unrecognized_lists[i]:
                        page_index, field_index = self.controller.id_map[key]
                        tab.pos_y += 30
                        AdditionalLine(tab.scroll, self.controller.config_list[page_index][field_index], tab.pos_x, tab.pos_y)

    def OnWriteSave(self, event):
        dlg = wx.DirDialog(self, "Choose a directory:", style=wx.DD_DEFAULT_STYLE | wx.DD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            directory = dlg.GetPath().replace('\\', '/') 
            # Check for other dflash saves, and delete them if the user OKs
            delete_old = False
            for item in os.listdir(directory):
                if item.endswith('.dflash'):
                    if delete_old:
                        os.remove(directory + '/' + item)
                    else:
                        msg_dlg = wx.MessageDialog(self, "There are existing .dflash saves in this folder, would you like to overwrite them?", "Overwrite?", wx.OK | wx.CANCEL | wx.ICON_INFORMATION) 
                        if msg_dlg.ShowModal() == wx.ID_OK:
                            delete_old = True
                            os.remove(directory + '/' + item)
                        else:
                            msg_dlg.Destroy()
                            return        
            self.controller.save_user_values(dlg.GetPath().replace('\\', '/'))
    
    def OnExit(self, event):
        print ("closing")
        if self.controller.serial_connected():
            self.controller.switch_to_execute()
            self.controller.ser.close()
        self.Destroy()  # Close the frame
    
    def OnClose(self, event):
        print ("closing")
        if self.controller.serial_connected():
            self.controller.switch_to_execute()
            self.controller.ser.close()
        self.Destroy()

    def OnRestart(self, event):
        if self.controller.serial_connected():
            self.controller.switch_to_execute()
            self.controller.ser.close()
        StartFrame(None, "StartFrame")
        self.Destroy()



#The first panel; used to select a serial port
class SerialSelect(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.initialize()

    def initialize(self):
        
        self.current_port = "-"
        self.current_config = "-"
        available_ports = ["-"]
        available_configs = ["-"]
        available_ports.extend(self.parent.controller.list_serial_ports())
        available_configs.extend(["EVSE", "E-Box", "Mini-E"])
        #----------------------------------------------------------------------
        #Serial connection
                                                      #location #size of field
        wx.StaticText(self, -1, "Select Serial Port:", (75, 50))
        self.ch1 = wx.Choice(self, -1, (200, 50), choices = available_ports)
        self.Bind(wx.EVT_CHOICE, self.EvtChoice1, self.ch1)

        b1 = wx.Button(self, wx.ID_ANY, "Open Selected Port", (475, 50))
        self.Bind(wx.EVT_BUTTON, self.OnClick1, b1)
        # b.SetDefault()  # highlights the button as the default
        b1.SetToolTipString("After selecting the serial port of the VEL board, click here")
        b1.SetSize(b1.GetBestSize())
        #----------------------------------------------------------------------
        #Configuration file without serial connection
        wx.StaticText(self, -1, "-or-", (75,125))
        wx.StaticText(self, -1, "Select Configuration:", (75, 200))
        self.ch2 = wx.Choice(self, -1, (250, 200), choices = available_configs)
        self.Bind(wx.EVT_CHOICE, self.EvtChoice2, self.ch2)
        b2 = wx.Button(self, wx.ID_ANY, "Open Configuration", (475, 200))
        self.Bind(wx.EVT_BUTTON, self.OnClick2, b2)
        b2.SetToolTipString("After selecting a configuration file to open, click here")
        b2.SetSize(b2.GetBestSize())


    def EvtChoice1(self, event):
        self.current_port = event.GetString()

    def EvtChoice2(self, event):
        self.current_config = event.GetString()

    def OnClick1(self, event):
        # Go here if user has not selected any port, or if no ports were found
        if self.current_port == "-":
            dlg = wx.MessageDialog(self, "No serial port connection found/selected.  Ensure a connection, then click 'OK' retry", "No Connection Found", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            dlg.Destroy()
            StartFrame(None, "Start Frame")
            self.parent.Destroy()
        # Go here if user has selected a port
        else:
            # Try to connect to a serial port, if not opened controller.ser is None
            self.parent.controller.set_serial_port(self.current_port)
            # Go here if controller.ser is not None and isOpen
            if (self.parent.controller.serial_connected()):
                self.parent.status.SetStatusText("Connected to serial port: " + self.current_port)
                self.Hide()
                #Get the VEL type
                vel_type = self.parent.controller.determine_vel_type() #sets vel type and config list/index
                if not vel_type:
                    dlg = wx.MessageDialog(self, "Could not determine green board type!\nEnsure VEL page 0 is written before considering other issues.", "Reading Error!", wx.OK | wx.ICON_ERROR)
                    dlg.ShowModal()
                    dlg.Destroy()
                    StartFrame(None, "Start Frame")
                    self.Destroy()
                else:
                    self.init_config_file(vel_type)
                    ####################### The Notebook Startup
                    self.parent.init_notebook()
                    self.parent.init_second_menu()
                    # self.parent.panel_two.Show()
                    self.parent.Layout()
                    #######################
            else:
                dlg = wx.MessageDialog(self, "Selected serial port could not be connected or opened", "Invalid Port", wx.OK | wx.ICON_WARNING)
                dlg.ShowModal()
                dlg.Destroy()
                StartFrame(None, "Start Frame")
                self.parent.Destroy()

    def OnClick2(self, event):
        if self.current_config == 'EVSE':
            self.init_config_file(0)
        elif self.current_config == 'E-Box':
            self.init_config_file(1)
        elif self.current_config == 'Mini-E':
            self.init_config_file(2)
        else:
            return
        self.parent.status.SetStatusText("No serial device connected. Open only for saving files.")
        self.Hide()
        self.parent.init_notebook()
        self.parent.init_second_menu()
        self.parent.Layout()

    def init_config_file(self, number):
        """
        Takes in a integer (0, 1, or 2) and returns the corresponding config file's list
        """
        number = int(number)
        if number == 0:
            fname = "evse_config.txt"
        elif number == 1:
            fname = "ev_1_config.txt"
        elif number == 2:
            fname = "ev_2_config.txt"
        self.parent.controller.set_vel_type(number)
        try:
            index, list_ = con.create_config_list(fname)
        except IOError:
            open_dlg = wx.FileDialog(self.parent, message="Choose a configuration file",
                                     defaultDir=os.getcwd(),
                                     defaultFile="",
                                     wildcard="Text (*.txt)|*.txt",
                                     style=wx.FD_OPEN | wx.FD_CHANGE_DIR)
            if open_dlg.ShowModal() == wx.ID_OK:
                index, list_ = con.create_config_list(open_dlg.GetPath())  # Should the file be checked?
            open_dlg.Destroy()
        self.parent.controller.set_config_index(index)
        self.parent.controller.set_config_list(list_)
        if self.parent.controller.get_config_list():
            self.parent.controller.set_id_map(self.parent.controller.make_id_map())

#The second set of panels; arranged in a notebook (Each tab has StartFrame as its GrandParent)
class NotebookTab(wx.Panel):
    def __init__(self, parent, page_index):
        wx.Panel.__init__(self, parent)
        self.parent = parent # parent contains all the information needed in the controller
        self.page_index = page_index
        self.initialize_new()

    def initialize_new(self):
        self.pos_x = 0
        self.pos_y = 10
        page = self.GetGrandParent().controller.config_list[self.page_index]
        self.scroll = wx.ScrolledWindow(self, -1, style=wx.TAB_TRAVERSAL)
        self.scroll.SetScrollbars(5, 5, -1, len(page)*6 + 30)  # 6 = 30/5
        # self.scroll.EnableScrolling(False, True)
        self.info_line_list = []
        for i, item in enumerate(page):
            if item[con.ConfigFields.TITLE] == "UNRECOGNIZED VALUE": 
            # The end values will be unrecognized because they were appended to the end in populate_from_dictionary_hex
                while (i < len(page)):
                    self.pos_y += 30
                    AdditionalLine(self.scroll, page[i], self.pos_x, self.pos_y)
                    i += 1
                break
            self.info_line_list = InfoLine(self.scroll, item, self.pos_x, self.pos_y)  # is info_line_list necessary?
            self.pos_y += 30
        #The sizer is used for the scroll bar
        bs = wx.BoxSizer(wx.VERTICAL)
        bs.Add(self.scroll, 1, wx.EXPAND)
        self.SetSizer(bs)

#An Info Line consists of a Label and a Text or Int Ctrl field
class InfoLine(wx.Panel):
    def __init__(self, parent, field, x, y):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.field = field
        text = self.field[con.ConfigFields.TITLE] + ' (' + self.field[con.ConfigFields.ID] + '):'
        #Static text portion
        wx.StaticText(self.parent, -1, text, pos=(x, y), size=(215, -1), style=wx.ALIGN_RIGHT)
        #Text ctrl portion
        if field[con.ConfigFields.TYPE] is int:
            self.tc = wx.lib.intctrl.IntCtrl(self.parent, -1, field[con.ConfigFields.VALUE], pos=(x+220, y-3), size=(200, -1), allow_none=True)
            if (field[con.ConfigFields.RANGE]) and (field[con.ConfigFields.RANGE][0] == 'range'):
                self.tc.SetBounds(field[con.ConfigFields.RANGE][1], field[con.ConfigFields.RANGE][2])
                self.tc.SetLimited(True)
                if field[con.ConfigFields.VALUE] is None:
                    #Solves the problem of the IntCtrl entering a 0 when a range is set
                    self.tc.SetValue(None)
        else:
            if field[con.ConfigFields.VALUE] is None:
                field[con.ConfigFields.VALUE] = ""
            self.tc = wx.TextCtrl(self.parent, -1, str(field[con.ConfigFields.VALUE]), pos=(x+220, y-3), size=(200, -1))
            if (field[con.ConfigFields.RANGE]) and (field[con.ConfigFields.RANGE][0] == 'length'):
                self.tc.SetMaxLength(field[con.ConfigFields.RANGE][1])
        self.tc.Bind(wx.EVT_SET_FOCUS, self.HelpMessages(field))
        self.tc.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
    
    def HelpMessages(self, info):
        def OnSetFocus(event):
            self.GetGrandParent().GetGrandParent().hp.setText(generate_help_message(info))
        return OnSetFocus
    
    def OnKillFocus(self, event):
        #Frame is the grandparents grandparent
        self.GetGrandParent().GetGrandParent().hp.setText("")
        self.field[con.ConfigFields.VALUE] = self.tc.GetValue()
        #page_index, field_index = self.GetGrandParent().GetGrandParent().controller.id_map[self.field[con.ConfigFields.ID]]

class AdditionalLine(wx.Panel):
    def __init__(self, parent, field, x, y):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.field = field
        self.key = field[con.ConfigFields.ID]
        self.x = x
        self.y = y
        text = self.field[con.ConfigFields.TITLE] + ' (' + self.field[con.ConfigFields.ID] + '):'
        self.st = wx.StaticText(self.parent, -1, text, pos=(self.x, self.y), size=(215, -1), style=wx.ALIGN_RIGHT)
        self.tc = wx.TextCtrl(self.parent, -1, str(field[con.ConfigFields.VALUE]), pos=(self.x+220, y-3), size=(200, -1))
        self.tc.Bind(wx.EVT_SET_FOCUS, self.HelpMessages(field))
        self.tc.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.kill_button = wx.Button(self.parent, -1, "X", pos=(self.x+405, self.y-3), size=(20, -1))
        self.kill_button.SetToolTipString("Click to delete this value from the DFlash (will delete when page is written)")
        self.kill_button.Bind(wx.EVT_BUTTON, self.OnClick)

    def HelpMessages(self, info):
        def OnSetFocus(event):
            self.GetGrandParent().GetGrandParent().hp.setText(generate_help_message(info))
        return OnSetFocus
    
    def OnKillFocus(self, event):
        #Frame is the grandparents grandparent
        self.GetGrandParent().GetGrandParent().hp.setText("")
        self.field[con.ConfigFields.VALUE] = self.tc.GetValue()
        #page_index, field_index = self.GetGrandParent().GetGrandParent().controller.id_map[self.field[con.ConfigFields.ID]]

    def OnClick(self, event):
        self.SetFocus()
        page_index, field_index = self.GetGrandParent().GetGrandParent().controller.id_map[self.field[con.ConfigFields.ID]]
        #remove the field from the page list
        self.GetGrandParent().GetGrandParent().controller.config_list[page_index].remove(self.field)
        #update the id map so there are no discrepencies
        self.GetGrandParent().GetGrandParent().controller.id_map = self.GetGrandParent().GetGrandParent().controller.make_id_map()
        self.field = None
        #destroy the field
        self.st.Show(False)
        self.tc.Show(False)
        self.kill_button.Show(False)
        self.Show(False)

#The help panel on the StartFrame that displays the help text
class HelpPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.parent = parent # parent contains all the information needed in the controller
        self.bsize = wx.BoxSizer(wx.VERTICAL)
        self.title = wx.StaticText(self, -1, "Help Information")
        self.text_area = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.bsize.Add(self.title, 0, wx.EXPAND)
        self.bsize.Add(self.text_area, 1, wx.EXPAND)
        self.SetSizer(self.bsize)
        # self.SetAutoLayout(1) # Necessary?
        # self.bsize.Fit(self) # Necessary?
    
    def setText(self, text):
        self.text_area.SetValue(text)
        
#The control panel on the StartFrame that has the buttons for writing
class ControlPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.parent = parent # parent contains all the information needed in the controller
        self.title = wx.StaticText(self, -1, "Control Panel")
        self.blank1 = wx.StaticText(self, -1, "")
        self.blank2 = wx.StaticText(self, -1, "")
        self.blank3 = wx.StaticText(self, -1, "")
        
        self.write_page = wx.Button(self, -1, "Write Current Page")
        self.Bind(wx.EVT_BUTTON, self.OnClickPage, self.write_page)
        self.write_all = wx.Button(self, -1, "Write All Pages")
        self.Bind(wx.EVT_BUTTON, self.OnClickAll, self.write_all)
        if not self.parent.controller.serial_connected():
            self.write_page.Disable()
            self.write_all.Disable()
        self.bsize = wx.BoxSizer(wx.VERTICAL)
        self.bsize.Add(self.blank1, 1, wx.EXPAND)
        self.bsize.Add(self.write_page, 1, wx.EXPAND)
        self.bsize.Add(self.blank2, 1, wx.EXPAND)
        self.bsize.Add(self.write_all, 1, wx.EXPAND)
        self.bsize.Add(self.blank3, 1, wx.EXPAND)
        self.SetSizer(self.bsize)

# 0: "String entered where integer needed 
# 1: "Field required but no information given!",
# 2: "Value entered is too long, out of range, or not a permitted value!"
    def OnClickPage(self, event):
        self.SetFocus()
        current_page_text = self.parent.controller.config_index[self.parent.nb.GetCurrentPage().page_index][0]
        #Include a dlg box allowing user to cancel action
        faults = self.parent.controller.write_page_to_VEL(current_page_text)
        if faults:
            string = ""
            print (faults)
            for fault in faults:
                if len(fault) == 2:
                    string += "Fault at id: (" + fault[0] + ") | " + self.parent.controller.fault_messages[int(fault[1])] + '\n'
                else:
                    string = fault
            dlg = wx.MessageDialog(self, string, "Faults On Page", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            dlg = wx.MessageDialog(self, "Current page written successfully!", "Page Written", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
        

    def OnClickAll(self, event):
        self.SetFocus()
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
                    print("faults")
            print(faults)
            dlg = wx.MessageDialog(self, string, "Faults on Pages", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            dlg.Destroy()
            print (faults)
        else:
            dlg = wx.MessageDialog(self, "All pages written successfully!", "All Pages Written", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()


def ensure_directory(path):
    """
    Input: Takes in a path that you want to ensure will be there in the future
    Output: No output, but creates a new folder if the specified directory did
            not exist before
    """
    if not os.path.exists(path):
        os.makedirs(path)


def generate_help_message(field):
    restrict = ""
    if field[2] is int:
        restrict += "Type: Integer"
    elif field[2] is str:
        restrict += "Type: String"
    else:
        restrict += str(field[2])
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


if __name__ == "__main__":
    app = wx.App(False)
    frame = StartFrame(None, "Start Frame")
    app.MainLoop()

