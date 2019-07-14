#!/usr/bin/env python

"""
Code to download schedule data for Hydrawise
Warning: selenium code is extremely fragile to website changes!
"""

import os
import re
from datetime import date

from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def getHydrawiseData(outFileDir):
    profile=FirefoxProfile()
    profile.set_preference('browser.download.folderList', 2)
    profile.set_preference('browser.download.manager.showWhenStarting', False)
    profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/vnd.ms-excel')
    profile.set_preference('browser.download.dir', outFileDir)

    opts = Options()
    opts.set_headless()
    assert opts.headless

    browser = Firefox(options=opts, firefox_profile=profile)
    browser.implicitly_wait(10)
    
    browser.get('https://app.hydrawise.com/config/login')

    assert(browser.title == 'Hydrawise')
    
    hydraUser = os.environ['HYDRA_USER']
    hydraPW = os.environ['HYDRA_PW']
    
    login_form=browser.find_elements_by_class_name('form-control')
    login_form[0].send_keys(hydraUser)
    login_form[1].send_keys(hydraPW)
    login_button=browser.find_element_by_class_name('login-btn')
    login_button.click()

    try:
        element = WebDriverWait(browser, 10).until(
            EC.title_is('Hydrawise Configuration'))
    except TimeoutException:
        print('logged in failed!')

    assert(browser.title == 'Hydrawise Configuration')

    # After logging in, short circuit all the button clicking by just loading up where we
    # want to go

    browser.get('https://app.hydrawise.com/config/reports')

    downloadButton = -1
    todayButton = -1
    dayButton = -1

    downloadRe = re.compile(r'>Download<')
    todayRe = re.compile(r'>today<')
    dayRe = re.compile(r'>day<')
    buttons = browser.find_elements_by_tag_name('button')
    for (i, button) in enumerate(buttons):
        html = button.get_attribute('outerHTML')
        if downloadRe.search(html):
            downloadButton = i
        if todayRe.search(html):
            todayButton = i
        if dayRe.search(html):
            dayButton = i

    buttons[dayButton].click()
    buttons[todayButton].click()
    buttons[downloadButton].click()
    
    browser.close()

def listChildElements(el):
    children = el.find_elements_by_xpath(".//*")
    for child in children:
        print(child.tag_name)
        print(child.get_property('attributes'))
        
if __name__ == '__main__':

    baseDir = '/home/tsa/Dropbox/WaterUsageData/Hydrawise'
    todayString = date.today().isoformat()
    destDir = os.path.join(baseDir, todayString)
    if not os.path.exists(destDir):
        os.makedirs(destDir)
    getHydrawiseData(destDir)
    #
    # convert .xls from Hydrawise to .xslx for ProcessHydrawiseData
    #
    xlsFile = os.path.join(destDir, 'hydrawise-Watering\ Time\ \(min\).xls')
    cmd = 'libreoffice "-env:UserInstallation=file:///tmp/LibO_Conversion" --headless --invisible --convert-to xlsx {} --outdir {}'.format(xlsFile, destDir)
    os.system(cmd)
    
