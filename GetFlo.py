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
import pdb
import time

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

    try:
        element = WebDriverWait(browser, 10).until(
            EC.title_is('Flo - Usage'))
    finally:
        pass

    assert(browser.title == 'Flo - Usage')

    dataDownload = browser.find_element_by_class_name('data-download')
#    pdb.set_trace()

    # why this sleep should be necessary is a mystery
    time.sleep(2)
    
    dataDownloadButton = dataDownload.find_element_by_class_name('dropdown-toggle')
    dataDownloadButton.click()
    
    csv_button = None
    dropdownItemList=browser.find_elements_by_class_name('dropdown-item')
    for (i,item) in enumerate(dropdownItemList):
        if DEBUG:
            print(i, item.get_attribute('outerHTML'))
            print(item.text)
        if item.text=='as CSV':
            csv_button = item

    assert(csv_button.text=='as CSV')

    csv_button.click()

    browser.close()

if __name__ == '__main__':

    baseDir = '/home/tsa/Dropbox/WaterUsageData/Flo'
    todayString = date.today().isoformat()
    destDir = os.path.join(baseDir, todayString)
    if not os.path.exists(destDir):
        os.makedirs(destDir)
    getFloData(destDir)
    
