#!/usr/bin/env python

"""
Code to download usage data for Flo
Warning: selenium code is extremely fragile to website changes!
"""

import os
from datetime import date

from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

DEBUG = False

def getFloData(outFileDir):
    profile=FirefoxProfile()
    profile.set_preference('browser.download.folderList', 2)
    profile.set_preference('browser.download.manager.showWhenStarting', False)
    profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'text/csv')
    profile.set_preference('browser.download.dir', outFileDir)

    opts = Options()
    opts.set_headless()
    assert opts.headless

    browser = Firefox(options=opts, firefox_profile=profile)
    browser.get('https://user.meetflo.com/login')

    assert(browser.title == 'Flo - My Account')
    
    FloUser = os.environ['FLO_USER']
    FloPW = os.environ['FLO_PW']

    login_form=browser.find_elements_by_class_name('form-control')
    login_form[0].send_keys(FloUser)
    login_form[1].send_keys(FloPW)
    login_button=browser.find_elements_by_class_name('btn')
    login_button[0].click()

    try:
        element = WebDriverWait(browser, 10).until(
            EC.title_is('Flo - Home'))
    finally:
        pass
        
    browser.get('https://user.meetflo.com/usage')

    assert(browser.title == 'Flo - Usage')

    dropdownList=browser.find_elements_by_class_name('dropdown-toggle')
    if DEBUG:
        for (i,drop) in enumerate(dropdownList):
            print(i, drop.get_attribute('outerHTML'))
              
    download_btn = dropdownList[3]
    download_btn.click()
    
    dropdownItemList=browser.find_elements_by_class_name('dropdown-item')
    csv_button = dropdownItemList[12]

    assert(csv_button.text=='as CSV')

    csv_button.click()

    browser.close()

if __name__ == '__main__':

    baseDir = '/home/tsa/Dropbox/WaterUsage/Data'
    todayString = date.today().isoformat()
    destDir = os.path.join(baseDir, todayString)
    if not os.path.exists(destDir):
        os.makedirs(destDir)
    getFloData(destDir)
    
