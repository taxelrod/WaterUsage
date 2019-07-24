#!/usr/bin/tcsh
source /home/tsa/.cshrc
cd /home/tsa/Venv3.5
source bin/activate.csh
cd /home/tsa/Dropbox/WaterUsage
./ChristieDrModel.py --nTrials=50 --updateSheet
