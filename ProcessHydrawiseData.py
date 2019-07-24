"""
Read in .xlsx schedule data downloaded from Hydrawise.  Return it as a Schedule
"""
import numpy as np
import datetime
from openpyxl import load_workbook
from WaterModel import schedule

# spreadsheet may be empty.  In this case, there is a single sheet, 'Worksheet', and all cells are empty

def loadHydraData(inputFileName, controllerId, checkDate=None):
    wb = load_workbook(inputFileName)
    zoneList = wb.sheetnames

    sched = schedule(controllerId)

    for zone in zoneList:
        ws = wb[zone]
        if ws['A1'].value is None:  # check for empty
            return None
        
        assert(ws['A1'].value == 'Date')
        assert(ws['B1'].value == 'Time')
        assert(ws['C1'].value == 'min')

        zoneStart = ws['B2'].value # datetime
        zoneDuration = ws['C2'].value  # minutes
        if checkDate is not None:
            assert(zoneStart.date() == checkDate.date())

        sched.addZone(zoneStart, zoneDuration, zone)

    sched.finalize()

    return sched
        

    
