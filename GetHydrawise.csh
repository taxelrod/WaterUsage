#!/usr/bin/tcsh
source /home/tsa/.cshrc
cd /home/tsa/Venv3.5
source bin/activate.csh
cd /home/tsa/Dropbox/WaterUsage
./GetHydrawise.py
#libreoffice "-env:UserInstallation=file:///tmp/LibO_Conversion" --headless --invisible --convert-to xlsx hydrawise-Watering\ Time\ \(min\).xls
