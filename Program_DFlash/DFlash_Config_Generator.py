'''
Created on Mar 1, 2017

@author: andrew robbins
'''

import re
import datetime

import config_evse
import config_ev_1
import config_ev_2

'''Summary: Writes the header for an EVSE config file
   Arguments: fileObject - File object to write to
              fileHeaderText - optional arg to pass string to write in as header otherwise default header used
   Returns: 0 for failure, 1 for success
   Exceptions: null file object'''
def WriteEVSEConfigHeader(fileObject, fileHeaderText=None):
    if fileObject:
        if fileHeaderText:
            fileObject.write(fileHeaderText)
        else:
            fileObject.write("EVSE Configuration File. Version 2.0\n")
            dateString = "Date: " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"
            fileObject.write(dateString)
            fileObject.write("See config_file_format_help.txt for formatting notes\n")
    else:
        print 'ERROR: File object null'
        return 0
    
    return 1

'''Summary: Writes the header for an EV config file
   Arguments: fileObject - File object to write to
              fileHeaderText - optional arg to pass string to write in as header otherwise default header used
   Returns: nothing
   Exceptions: null file object'''        
def WriteEVConfigHeader(fileObject, fileHeaderText=None):
    if fileObject:
        if fileHeaderText:
            fileObject.write(fileHeaderText)
        else:
            fileObject.write("EV 1 (E-Box) Configuration File.\n")
            fileObject.write("See config_file_format_help.txt for formatting notes\n")
    else:
        print 'ERROR: File object null'

'''Summary: Writes the starting indicator string or symbol(s) before a page title
   Arguments: fileObject - File object to write to
              startIndicatorString - optional arg to pass string to write in as starting indicator otherwise default indicator used
   Returns: nothing
   Exceptions: null file object'''        
def WritePageTitleStartIndicator(fileObject, startIndicatorString=None):
    if fileObject:
        if startIndicatorString:
            fileObject.write(startIndicatorString)
        else:
            fileObject.write(":::")
    else:
        print 'ERROR: File object null'

'''Summary: Writes the new field indicator string or symbol(s) before a new field in a page
   Arguments: fileObject - File object to write to
              newFieldIndicatorString - optional arg to pass string to write in as new field indicator otherwise default indicator used
   Returns: nothing
   Exceptions: null file object'''         
def WriteNewFieldIndicator(fileObject, newFieldIndicatorString=None):
    if fileObject:
        if newFieldIndicatorString:
            fileObject.write(newFieldIndicatorString)
        else:
            fileObject.write("+")
    else:
        print 'ERROR: File object null'

'''Summary: Writes the end of line indicator string or symbol(s)
   Arguments: fileObject - File object to write to
              endLineIndicatorString - optional arg to pass string to write in as end of line indicator otherwise default indicator used
   Returns: nothing
   Exceptions: null file object'''        
def WriteEndLineIndicator(fileObject, endLineIndicatorString=None):
    if fileObject:
        if endLineIndicatorString:
            fileObject.write(endLineIndicatorString)
        else:
            fileObject.write(";")
    else:
        print 'ERROR: File object null'

'''Summary: Writes the configuration file
   Arguments: fileObject - File object to write to
              pageList - list of pages
              fieldAndInfoList - list of fields and their respective data
   Returns: nothing
   Exceptions: null file object'''        
def WriteConfigFile(fileObject, pageList, fieldAndInfoList):
    pageTitleDelimeter = ','
    
    if WriteEVSEConfigHeader(fileObject):
        combinedLists = zip(pageList, fieldAndInfoList)
        
        for pageInfo, page in combinedLists:
            WritePageTitleStartIndicator(fileObject)
            newString = pageInfo[0]
            
            if pageTitleDelimeter in pageInfo[0]:
                '''Remove commas and spaces'''
                splitString = re.split(', ', pageInfo[0])
                newString = "/".join(splitString)
            
            fileObject.write(newString)
            fileObject.write(', ')
            fileObject.write(str(pageInfo[1]))
            fileObject.write('\n')
            
            for fieldAndInfo in page:
                WriteNewFieldIndicator(fileObject)
                    
                for info in fieldAndInfo:
                    if info == None or info == False:
                        WriteEndLineIndicator(fileObject)
                        fileObject.write('\n')
                    elif type(info) is tuple:
                        infoLength = len(info)
                        if infoLength != 0:
                            fileObject.write(info[0])
                                
                            for tupleInfo in info[1:infoLength]:
                                fileObject.write(', ')
                                fileObject.write(str(tupleInfo))
                                    
                        WriteEndLineIndicator(fileObject)
                        fileObject.write('\n')
                    else:
                        if info == str:
                            fileObject.write('string')
                        elif info == int:
                            fileObject.write('integer')
                        else:
                            fileObject.write(str(info))
                                
                        WriteEndLineIndicator(fileObject)
                        fileObject.write('\n')

'''Summary: Closes the file object
   Arguments: fileObject - File object to write to
   Returns: nothing
   Exceptions: null file object'''     
def CloseFileObject(fileObject):
    if fileObject:
        fileObject.close()
        

if __name__ == '__main__':
    filePath = 'evse_config.txt'
    fileObject = open(filePath, "wb")
    
    WriteConfigFile(fileObject, config_evse.evse_index, config_evse.evse)
    
    CloseFileObject(fileObject)

    pass    