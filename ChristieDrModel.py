#!/usr/bin/env python

import datetime as dt
from datetime import date
import WaterModel as wm
import ProcessFloData as pf
import ProcessHydrawiseData as ph
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_pdf import PdfPages
from scipy.stats import median_absolute_deviation as mad
from collections import OrderedDict
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import numpy as np
import os
import sys
import argparse

def getZoneFlows(model, measFlows):

    # Solve the model for the zone flows

    result=wm.findFlows(model, measFlows)

    return result

def printResult(result, model, full=False):

    if full:
        print(result)
    wm.printResult(result, model, plotLegend=False)

def plotResids(result, model, measFlows, timeDateString, pp):

    resids = wm.formatResids(measFlows, result.fun)
    plt.figure()
    plt.plot(resids[:,0], resids[:,1], '.')

    plt.plot(resids[:,0], measFlows[:,1])

    flowTimes = measFlows[:,0]
    flows = result.x
    flowPredict = np.zeros_like(measFlows[:,1])
    for (i, sched) in enumerate(model.schedList):
        parameterBlock = flows[model.sliceList[i]]
        zoneFlows = parameterBlock[0:sched.nzones]
        tOffset = parameterBlock[-1]
        sched.setToffset(tOffset)
        for i in range(len(flowTimes)-1):
            flowPredict[i] = sched.flowIntegral(zoneFlows, flowTimes[i], flowTimes[i+1])
        plt.plot(resids[:,0], flowPredict)

    wm.printResult(result, model, plotLegend=True)
    plt.yscale('symlog')
    plt.xlim(4.0, 8.0)
    plt.title(timeDateString)

    plt.savefig(pp, format='pdf')

def plotScheds(result, model, measFlows, timeDateString, pp):

    flowTimes = measFlows[:,0]
    plotTimes = np.arange(np.amin(flowTimes), np.amax(flowTimes), 10.0)
    plotHours = np.zeros_like(plotTimes)
    for i in range(len(plotTimes)):
        t = dt.datetime.fromtimestamp(plotTimes[i])
        plotHours[i] = t.time().hour + t.time().minute/60.0

    plt.figure()

    flows = result.x
    for (i, sched) in enumerate(model.schedList):
        parameterBlock = flows[model.sliceList[i]]
        zoneFlows = parameterBlock[0:sched.nzones]
        tOffset = parameterBlock[-1]
        sched.setToffset(tOffset)
        schedFlow = sched.schedFlow(zoneFlows, plotTimes)
        plt.plot(plotHours, schedFlow, '.', markersize=1)

    plt.yscale('symlog')
    plt.xlim(4.0, 8.0)
    plt.title(timeDateString)

    plt.savefig(pp, format='pdf')

def updateSheet(time, flowData):
    # first part copied from Google sheet API quickstart.py

    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # with API ready to go connect to the spreadsheet, and append the data as a new row

    valueList = [time]
    for (n, flow) in enumerate(flowData):
        median, sigma = flowData[flow]
        valueList.append(median)
        valueList.append(sigma)
        
    valueList.append(dt.date.fromtimestamp(time).isoformat())
    
    values = [ valueList ]
    body = {
        'values': values
    }

    range_name = 'Model Fit'
    spreadsheet_id = os.environ['CHRISTIE_WATER_DOC']
    value_input_option = 'USER_ENTERED'
    insert_data_option = 'INSERT_ROWS'
    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id, range=range_name, insertDataOption=insert_data_option,
        valueInputOption=value_input_option, body=body).execute()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--date', help = 'date as 20yy-mm-dd')
    parser.add_argument('--plot', help = 'output plots to a pdf file named {date}.pdf', action='store_true')
    parser.add_argument('--csv', help = 'output data file specified by --dataOut in csv format', action='store_true')
    parser.add_argument('--print', help = 'print results of each trial', action='store_true')
    parser.add_argument('--oldSched', help = 'use schedule from before 7/21/19 change', action='store_true')
    parser.add_argument('--updateSheet', help = 'append results to Google sheet identified by environment variable $SHEET_ID' , action='store_true')
    parser.add_argument('--dataDir', help = 'directory root for Flo and Hydrawise data')
    parser.add_argument('--dataOut', help = 'file to append output data')
    parser.add_argument('--nTrials', help = 'number of solutions from random initial guesses on which to base statistics', type=int)
    args = parser.parse_args()

    print('plot: ',args.plot)
    
    if args.date:
        testDateString = args.date
    else:
        testDateString = date.today().isoformat()

    print(args.date, testDateString)
    testDate = dt.datetime.strptime(testDateString, '%Y-%m-%d')

    if args.dataDir:
        dataDir = args.dataDir
    else:
        dataDir = '/home/tsa/Dropbox/WaterUsageData'

    print('datadir: ', dataDir)

    if args.nTrials:
        nTrials = args.nTrials
    else:
        nTrials = 5

    print('nTrials: ', nTrials)

    # ------------------------------------
    # Set up schedules, variable and fixed
    
    # Schedule constant over 24 hours, representing a fixed leak
    # Currently set to reflect the fact that we turn the system on and off daily to minimize the leak...

    ConstLeakSched = wm.schedule(3)
    ConstLeakSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('00:00','%H:%M').time()), 23.95*60.0, 'Const Leak')
    ConstLeakSched.finalize()

    # This is the fixed schedule (except for clock drift) for
    # the irrigation controller in the rear of the house

    RearSched = wm.schedule(2)
    if args.oldSched:
        RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('05:30','%H:%M').time()), 10.0, 'Lawn')
        RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('05:40','%H:%M').time()), 15.0, 'Fruit Trees')
        RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('05:55','%H:%M').time()), 5.0, 'Planter')
        RearSched.finalize()
    else:
        RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('06:38','%H:%M').time()), 10.0, 'Lawn')
        RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('06:53','%H:%M').time()), 15.0, 'Fruit Trees')
        RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('07:08','%H:%M').time()), 5.0, 'Planter')
        RearSched.finalize()

    # Read in the Hydrawise schedule for testDate.  NOTE - because it varies with the weather, it may be empty
    #

    hydraDatafile = os.path.join(dataDir, 'Hydrawise', testDateString, 'hydrawise-Watering Time (min).xlsx')
    HydraSched = ph.loadHydraData(hydraDatafile, 1, checkDate=testDate)

    # Read in the Flo data
    floDataFile = os.path.join(dataDir, 'Flo', testDateString, 'total-consumption-last-day.csv')
    measFlows=pf.loadFloData(floDataFile)

    # Data structure for all flows, both active and inactive

    flowData = OrderedDict([('FrontOrangeMesquite',(0, 0)), ('NorthHillside',(0, 0)), ('SouthHillside',(0, 0)), ('EastPlanter',(0, 0)), ('SouthPalm',(0, 0)), ('Lawn',(0, 0)), ('FruitTrees',(0, 0)), ('Planter',(0, 0)), ('ConstLeak',(0, 0))])
    # Construct the model

    model = wm.model()

    if HydraSched is not None:
        model.addSched(HydraSched)
    model.addSched(RearSched)
    model.addSched(ConstLeakSched)

    activeFlowLabels = []
    for sched in model.schedList:
        for zone in sched.zoneList:
            activeFlowLabels.append(zone[2].translate({ord(' '):None}))
        activeFlowLabels.append('toffset')
    

    # Calculate the flows and print results

    if args.plot:
        pp=PdfPages('{}.pdf'.format(testDateString))

    resultArr = np.zeros((nTrials, model.nFlows + model.nsched))
    
    for n in range(nTrials):
        result = getZoneFlows(model, measFlows)

        resultArr[n, :] = result.x
        resultArr[n, :-1] *= 60.0  # gps to gpm

        if args.print:
            printResult(result, model, full=False)
        if args.plot:
            plotResids(result, model, measFlows, testDateString, pp)
            plotScheds(result, model, measFlows, testDateString, pp)

    if args.plot:
        pp.close()

    if args.print:
        print(resultArr)

    meds = np.median(resultArr, axis=0)
    mads = mad(resultArr, axis=0)

    for n in range(len(meds)):
        if flowData.get(activeFlowLabels[n]):
            flowData[activeFlowLabels[n]] = (meds[n], mads[n])

    if args.updateSheet:
        updateSheet(testDate.timestamp(), flowData)
        
    if args.dataOut:
        # check for existence.  if exists just append line.  if not, put out header line first
        if os.path.exists(args.dataOut):
            df = open(args.dataOut,'a')
        else:
            df = open(args.dataOut,'w')
            if args.csv:
                print('time', end=', ', file=df)
                for (n, label) in enumerate(flowData):
                    if n == len(flowData) - 1:
                        endstr = ''
                    else:
                        endstr = ', '
                    print(label, ', ', 'sigma_'+label, end=endstr, file=df)
            else:
                print('# time', end=' ', file=df)
                for label in flowData:
                    print(label, ' ', 'sigma_'+label, end=' ', file=df)
            print('', file=df)
        if args.csv:
            print(testDate.timestamp(), end=', ', file=df)
        else:
            print(testDate.timestamp(), end=' ', file=df)

        for (n, flow) in enumerate(flowData):
            median, sigma = flowData[flow]
            # if csv and last item, endstr = '', else endstr = ', '
            if args.csv:
                if n == len(flowData) - 1:
                    endstr = ''
                else:
                    endstr = ', '
                print('{:.3f}, {:.3f}'.format(median, sigma), end=endstr, file=df)
            else:
                print('{:.3f} {:.3f}'.format(median, sigma), end=' ', file=df)
        print('', file=df)
        df.close()
    else:
        for n in range(len(meds)):
            print(activeFlowLabels[n], meds[n], mads[n])

        
        

    




