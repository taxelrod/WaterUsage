import datetime as dt
import WaterModel as wm
import ProcessFloData as pf
import ProcessHydrawiseData as ph

testDate = dt.datetime(2019, 7, 6)
testDateString = testDate.date().isoformat()

# Schedule constant over 24 hours, representing a fixed leak

ConstLeakSched = wm.schedule(3)
ConstLeakSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('00:00','%H:%M').time()), 24*60.0-1, 'Const Leak')
ConstLeakSched.finalize()

# This is the fixed schedule (except for clock drift) for
# the irrigation controller in the rear of the house

RearSched = wm.schedule(2)
RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('05:30','%H:%M').time()), 10.0, 'Lawn')
RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('05:40','%H:%M').time()), 10.0, 'Fruit Trees')
RearSched.addZone(dt.datetime.combine(testDate, dt.datetime.strptime('05:50','%H:%M').time()), 5.0, 'Planter')
RearSched.finalize()

# Read in the Hydrawise schedule for testDate
#

HydraSched = ph.loadHydraData('HydrawiseData/{}/hydrawise-Watering Time (min).xlsx'.format(testDateString), 1, checkDate=testDate)

model = wm.model()

# Read in the Flo data

measFlows=pf.loadFloData('Data/{}/total-consumption-last-day.csv'.format(testDateString))

def getZoneFlows():
    global model, measFlows
    # Construct the model

    model.addSched(HydraSched)
    model.addSched(RearSched)
    model.addSched(ConstLeakSched)

    # Solve the model for the zone flows

    result=wm.findFlows(model, measFlows)

    return result

def print(result):
    global model
    
    wm.printResult(result, model)

def getResids(result):
    global measFlows
    return wm.formatResids(measFlows, result.fun)



