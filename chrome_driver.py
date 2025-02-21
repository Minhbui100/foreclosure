from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

class Driver:
    def __init__(self):
        # Set up Chrome options to run in headless mode
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        chromedriver_path = './chromedriver'

        # Initialize Chrome driver
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

