from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import time
import psycopg2
import re
from psycopg2 import OperationalError
import requests
import PyPDF2
from io import BytesIO
from pdf2image import convert_from_bytes
import pytesseract
import os



# os.environ['PATH'] += r";C:\Users\buiho\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"

def count_page(driver):
    pagination_links = driver.find_elements(By.XPATH, "//a[contains(@href, \"javascript:__doPostBack('ctl00$ContentPlaceHolder1$GridView1','Page$\")]")
    # Step 2: Filter only numeric pagination links and get the last page number
    page_numbers = []
    loop=1
    k=1
    for link in pagination_links:
            text = link.text.strip()
            if text not in page_numbers and text.isdigit():  # Filter only numeric values
                page_numbers.append(text)  

   
    print("page number: ", page_numbers)

    if page_numbers:
        last_page_number = len(page_numbers)+1  # Get the highest page number
        print(f"Total number of pages: {last_page_number}")
    else:
        last_page_number = 1  # Assume only 1 page if no pagination is found
        print("Only one page found.")   
                
    return last_page_number


def read_doc(last_page_number, cursor):
    for page in range(1, last_page_number + 1):
        print(f"Navigating to page {page}")
        if page > 1:
            # Only click pagination links if we're past the first page
            pagination_link = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, \"javascript:__doPostBack('ctl00$ContentPlaceHolder1$GridView1','Page${page}')\")]"))
            )
            pagination_link.click()
            time.sleep(3)  # Give time for the page to load

        elements = []
        elements = driver.find_elements(By.XPATH, "//*[contains(@id, 'ctl00_ContentPlaceHolder1_GridView1_ct')]")
        attempts = 0
        while attempts < 100:
            elements = driver.find_elements(By.XPATH, "//*[contains(@id, 'ctl00_ContentPlaceHolder1_GridView1_ct')]")
            attempts+=1
        grouped_data = {}
        text=""
        for element in elements:
            element_id = element.get_attribute('id')  
            text = element.text.strip()
            # Extract the unique key from the ID (e.g., ct1, ct2)
            unique_key = element_id[len('ctl00_ContentPlaceHolder1_GridView1_ct'):len('ctl00_ContentPlaceHolder1_GridView1_ct')+3]  # Adjust if needed            

            # Add the text to the respective group in the dictionary
            if unique_key not in grouped_data:
                grouped_data[unique_key] = []

            element_href = element.get_attribute('href')

            if element_href!=None:
                grouped_data[unique_key].append(element_href)
            grouped_data[unique_key].append(text)

        # Print the grouped data
        for key, texts in grouped_data.items():
            #print(f"Group: {key} -> Values: {texts}")
            cursor.execute("""INSERT INTO doc_info(doc_id, sale_date, file_date, pages, link)
                      VALUES (%s, %s, %s, %s, %s);""", (texts[1], texts[2], texts[3], texts[4], texts[0]))

def connect_to_db():
    # Define our connection parameters
    db_params = {
        "host": "localhost",
        "dbname": "foreclosure",
        "user": "postgres",
        "port": "5433",
        "password": "postgres"  
    }

    try:
        print("Connecting to database...")
        conn = psycopg2.connect(**db_params)
        
        cursor = conn.cursor()
        
        print("Connected successfully!")
        return conn, cursor
    
    except OperationalError as e:
        print(f"Error connecting to the database: {e}")
        return None, None


# Set up Chrome options to run in headless mode (optional)
chrome_options = Options()

# Path to your chromedriver executable
chromedriver_path = 'C:\\Hoang Minh Bui\\coding_projects\\prospector\\chromedriver.exe'

# Initialize the Chrome WebDriver
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

# Open the webpage
url = 'https://www.cclerk.hctx.net/Applications/WebSearch/FRCL_R.aspx'
driver.get(url)

# Wait for the File Date radio button to be clickable and select it
file_date_radio = WebDriverWait(driver, 20).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input#ctl00_ContentPlaceHolder1_rbtlDate_1'))
)
file_date_radio.click()

# Select the year 2024 from the year dropdown
year_dropdown = WebDriverWait(driver, 20).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, 'select#ctl00_ContentPlaceHolder1_ddlYear'))
)
year_select = Select(year_dropdown)
year_select.select_by_visible_text('2024')

# Select October from the month dropdown
month_dropdown = WebDriverWait(driver, 20).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, 'select#ctl00_ContentPlaceHolder1_ddlMonth'))
)
month_select = Select(month_dropdown)
month_select.select_by_visible_text('October')

# Click the Search button
search_button = WebDriverWait(driver, 20).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input#ctl00_ContentPlaceHolder1_btnSearch'))
)
search_button.click()
print("Search button clicked successfully.")

time.sleep(2)

connection, cursor = connect_to_db()
cursor.execute("""DROP TABLE IF EXISTS doc_info""")
cursor.execute(f"""CREATE TABLE doc_info (
               id SERIAL PRIMARY KEY, 
               doc_id VARCHAR(15), 
               sale_date DATE, 
               file_date DATE, 
               pages INT,
               link VARCHAR(255)
               );""")


last_page_number=count_page(driver)

read_doc(2, cursor)

time.sleep(2)

cursor.execute("""SELECT * FROM doc_info;""")
data = cursor.fetchall()


def extract_text_from_pdf(pdf_content):
    pages = convert_from_bytes(pdf_content)
    extracted_text = ""
    for page_num, page in enumerate(pages):
        text = pytesseract.image_to_string(page)
        extracted_text += text + "\n"
        
    return extracted_text

import os
import replicate

def analyze_text(text):
    client = replicate.Client(api_token="r8_Iv3MpAieFC9iWF8CkZUXEhKkqE1RsmN3apYsN")
    output = client.run(
        "a16z-infra/llama13b-v2-chat:df7690f1994d94e96ad9d568eac121aecf50684a0b0963b25a41cc40061269e5",
        input={"prompt": f"Extract the name of the grantor (or mortgagor) from the following text:\n\n{text}\n\nGrantor name:", "temperature": 0.1, "top_p": 0.9, "max_length": 128}
    )
    full_response = ""

    for item in output:
        full_response += item

    print(full_response)

"""
import re
import pytesseract
import requests
from openai import OpenAI
client = OpenAI()

#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

def analyze_text(text):
    # Send the extracted text to OpenAI
    prompt = f"Extract the name of the grantor (or mortgagor) from the following text:\n\n{text}\n\nGrantor name:"

    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",  # Use the most suitable model, e.g., "gpt-4" or "gpt-3.5-turbo"
        prompt=prompt,
        max_tokens=100,
        temperature=0.5  # You can adjust temperature for creativity, 0.5 is a balanced choice
    )
    # Extract the grantor name from the response
    name = response.choices[0].text.strip()
    print("Name of mortgagor: ", name)

    prompt = f"Extract the address (starts with 'block' or 'lot', end with 'texas') from the following text:\n\n{text}\n\nAddress:"
    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",  # Use the most suitable model, e.g., "gpt-4" or "gpt-3.5-turbo"
        prompt=prompt,
        max_tokens=100,
        temperature=0.5  # You can adjust temperature for creativity, 0.5 is a balanced choice
    )
    # Extract the address from the response
    address = response.choices[0].text.strip()
    print("Address: ", address)

    prompt = f"Extract the address (starts with 'block' or 'lot', end with 'texas') from the following text:\n\n{text}\n\nAddress:"
    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",  # Use the most suitable model, e.g., "gpt-4" or "gpt-3.5-turbo"
        prompt=prompt,
        max_tokens=100,
        temperature=0.5  # You can adjust temperature for creativity, 0.5 is a balanced choice
    )
    address = response.choices[0].text.strip()
    print("Address: ", address)


    prompt = f"Extract the date of sale from the following text:\n\n{text}\n\nDate:"
    response = openai.Completion.create(
        model="gpt-4",  # Use the most suitable model, e.g., "gpt-4" or "gpt-3.5-turbo"
        prompt=prompt,
        max_tokens=100,
        temperature=0.5  # You can adjust temperature for creativity, 0.5 is a balanced choice
    )
    date = response.choices[0].text.strip()
    print("Date of sale: ", date)
"""


for link in data:
    try:
        response = requests.get(link[5])
        response.raise_for_status()  # Ensure the request was successful
        pdf_content = response.content
        text = extract_text_from_pdf(pdf_content)
        analyze_text(text)
    except Exception as e:
        print(f"Error processing {link[5]}: {e}")


# Commit the transaction to persist the changes
connection.commit()

# Close the connection
cursor.close()
connection.close()