#!/usr/bin/env python

import datetime as dt
import WaterModel as wm
import ProcessFloData as pf
import ProcessHydrawiseData as ph
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_pdf import PdfPages
from scipy.stats import median_absolute_deviation as mad
from collections import OrderedDict
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


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('date', help = 'date as 20yy-mm-dd')
    parser.add_argument('--plot', help = 'output plots to a pdf file named {date}.pdf', action='store_true')
    parser.add_argument('--print', help = 'print results of each trial', action='store_true')
    parser.add_argument('--dataDir', help = 'directory root for Flo and Hydrawise data')
    parser.add_argument('--dataOut', help = 'file to append output data')
    parser.add_argument('--nTrials', help = 'number of solutions from random initial guesses on which to base statistics', type=int)
    args = parser.parse_args()

    print('plot: ',args.plot)
    
    testDateString = args.date
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
    RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('06:45,'%H:%M').time()), 10.0, 'Lawn')
    RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('06:55','%H:%M').time()), 15.0, 'Fruit Trees')
    RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('07:10','%H:%M').time()), 5.0, 'Planter')
    RearSched.finalize()

    # Read in the Hydrawise schedule for testDate
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
        print(activeFlowLabels[n], meds[n], mads[n])

    if args.dataOut:
        # check for existence.  if exists just append line.  if not, put out header line first
        if os.path.exists(args.dataOut):
            df = open(args.dataOut,'a')
        else:
            df = open(args.dataOut,'w')
            print('# time', end=' ', file=df)
            for label in flowData:
                print(label, 'sigma_'+label, end=' ', file=df)
            print('', file=df)
        print(testDate.timestamp(), end=' ', file=df)
        for n in range(len(meds)):
            if flowData.get(activeFlowLabels[n]):
                flowData[activeFlowLabels[n]] = (meds[n], mads[n])
        for flow in flowData:
            median, sigma = flowData[flow]
            print(median, sigma, end=' ', file=df)
        print('', file=df)
        df.close()
        

    




