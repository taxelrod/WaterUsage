import numpy as np
import datetime
from scipy.optimize import least_squares as lsq
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

# square wave function

def s(t, t1, t2):
    if t>=t1 and t<=t2:
        return 1.0
    else:
        return 0.0

# and its integral

def sIntegral(ta, tb, t1, t2):
    # integral of s(t, t1, t2) from ta to tb
    if ta>t2 or tb<t1:
        return 0
    tLow = max(t1, ta)
    tHi = min(t2, tb)
    return tHi - tLow


# schedule for a controller
# limited at present by assumption a given zone has a single run time and duration

class schedule:
    def __init__(self, controllerId):
        self.id = controllerId
        self.nzones = 0
        self.toffset = 0  # added to schedule times to agree with timestamp() times
        self.zoneList = []

    def addZone(self, t, duration, name):
        self.zoneList.append((t, duration, name))
        self.nzones += 1

    def setToffset(self, t):
        self.toffset = t

    def finalize(self, dump=False):
        self.times = np.zeros((self.nzones, 2))
        for (i,zone) in enumerate(self.zoneList):
            if dump:
                print(zone)
            self.times[i, 0] = zone[0].timestamp()
            self.times[i, 1] = self.times[i, 0] + zone[1]*60.0  # zone[1] is in minutes

    def flow(self, zoneFlows, t):
        assert(len(zoneFlows)==self.nzones)
        totFlow = 0.
        for i in range(self.nzones):
            totFlow += zoneFlows[i] * s(t, self.times[i, 0] + self.toffset, self.times[i, 1] + self.toffset)

        return totFlow

    def flowIntegral(self, zoneFlows, ta, tb):
        assert(len(zoneFlows)==self.nzones)
        flowIntegral = 0.
        for i in range(self.nzones):
            flowIntegral += zoneFlows[i] * sIntegral(ta, tb, self.times[i, 0] + self.toffset, self.times[i, 1] + self.toffset)

        return flowIntegral

"""
optFunc takes as input an array of flow rates, which is the concatenation of flow rates for each of the schedules.  
The timeseries of measured flows, F, is the first and only argument, passed from least_squares() as args=F
"""

class model:
    def __init__(self):
        self.schedList = []
        self.sliceList = []
        self.nsched = 0
        self.nFlows = 0
        self.indxStart = 0
        # array of slices to partition the flows argument by schedule? Use np.s_[i:j]

    def addSched(self, sched):
        self.schedList.append(sched)
        i = self.indxStart
        j = i + sched.nzones + 1  # last element in the block is the toffset
        self.sliceList.append(np.s_[i:j])
        if self.nsched == 0:
            self.lowerBounds = np.zeros((j-i))
            self.lowerBounds[j-1] = -1 # sec
            self.upperBounds = np.repeat(np.inf, j-i)
            self.upperBounds[j-1] = 1 # sec
        else:
            self.lowerBounds = np.hstack((self.lowerBounds, np.zeros((j-i))))
            self.lowerBounds[j-1] = -1 # sec
            self.upperBounds = np.hstack((self.upperBounds, np.repeat(np.inf, j-i)))
            self.upperBounds[j-1] = 1 # sec
        self.indxStart += sched.nzones + 1
        self.nsched += 1
        self.nFlows += sched.nzones
    
def optFunc(flows, *args): # take out of class, give it a model as one of *args
    # flows arg needs to include timeoffset for each sched
    flowMeas = args[0] # array of [time, gallons in time interval]
    flowTimes = flowMeas[:,0]  # sec past the Epoch
    flowIntegrals = flowMeas[:,1]  # gallons
    flowModel = args[1]

    flowPredict = np.zeros_like(flowIntegrals)
    for (i, sched) in enumerate(flowModel.schedList):
        parameterBlock = flows[flowModel.sliceList[i]]
        zoneFlows = parameterBlock[0:sched.nzones]
        tOffset = parameterBlock[-1]
        sched.setToffset(tOffset)
        for i in range(len(flowTimes)-1):
            flowPredict[i] += sched.flowIntegral(zoneFlows, flowTimes[i], flowTimes[i+1])
            
    return flowIntegrals - flowPredict

def formatResids(flowMeasurements, resids):
    fResids = np.zeros_like(flowMeasurements)
    for i in range(len(resids)):
        dt = datetime.datetime.fromtimestamp(flowMeasurements[i,0])
        fResids[i, 0] = dt.time().hour + dt.time().minute/60.0
        fResids[i, 1] = resids[i]

    return fResids

def findFlows(flowModel, flowMeasurements):
    flowGuess = 0.0005*np.ones((flowModel.nFlows + flowModel.nsched)) # includes timeoffsets
    result = lsq(optFunc, flowGuess, bounds=(flowModel.lowerBounds, flowModel.upperBounds), args=(flowMeasurements, flowModel))
    plotResids = formatResids(flowMeasurements, result.fun)
    return result

def printResult(result, flowModel, plot=False):
    flows = result.x
    if plot:
        xpos = 0.6
        ypos = 0.85
        font = FontProperties()
        font.set_size(6)
    for (i,sched) in enumerate(flowModel.schedList):
        schedFlows = flows[flowModel.sliceList[i]]
        for j in range(sched.nzones):
            text = '{} :\t {:.3f} gpm'.format(sched.zoneList[j][2], schedFlows[j]*60)
            if plot:
                plt.figtext(xpos, ypos, text, fontproperties=font)
                ypos -= 0.025
            else:
                print(text)
        text = 'timeOffset: {:.1f} sec'.format(schedFlows[j+1])
        if plot:
            plt.figtext(xpos, ypos, text, fontproperties=font)
            ypos -= 0.025
        else:
            print(text)
        
        
