import numpy as np
import re
from datetime import datetime

def loadFloData(inputFileName):
    marker = re.compile('Gallons')
    
    d = np.loadtxt(inputFileName, delimiter=',', dtype=str)
    nrows = d.shape[0]

    first = True
    for n in range(nrows):
        d[n,0] = d[n,0].translate({ord('"'):None})
        d[n,1] = d[n,1].translate({ord('"'):None})
        if marker.match(d[n,1]):
            if first:
                marker0 = n+1
                first = False
            else:
                marker1 = n-1

    dtoday = d[marker0:marker1,:]

    decoded = np.zeros_like(dtoday, dtype=float)

    timeFormat = "%m/%d/%Y %I:%M %p"
    
    for (i, row) in enumerate(dtoday):
        decoded[i,0] = datetime.strptime(row[0], timeFormat).timestamp()
        decoded[i,1] = float(row[1])

    return decoded
    
