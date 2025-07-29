from selenium import webdriver
from selenium.webdriver import ChromeOptions

# open current browser
def open_chrome():
    chrome_options= ChromeOptions()
    chrome_options.debugger_address= "localhost:9222"
    driver=webdriver.Chrome(options=chrome_options)
    return driver

