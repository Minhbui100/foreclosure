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
import os

import pytesseract
from transformers import pipeline, GPT2Tokenizer
import string
from PIL import ImageFilter



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
        # Preprocess image: Convert to grayscale & enhance readability
        page = page.convert("L")  # Convert to grayscale
        page = page.filter(ImageFilter.SHARPEN)  # Sharpen image

        text = pytesseract.image_to_string(page, config="--psm 6")  # Page segmentation mode 6 (Assumes single column)
        
        extracted_text += text + " "
    
    # Remove excessive newlines and extra spaces
    extracted_text = re.sub(r'\n+', '\n', extracted_text).strip()
    extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
    return extracted_text

import spacy

nlp = spacy.load("en_core_web_trf")

def remove_lowercase_words(text):
    words = text.split()  # Split the text into words
    filtered_words = [word for word in words if not re.match(r'^[a-z]', word)]  # Keep words that don't start with lowercase
    return " ".join(filtered_words)  

def analyze_text_name(text):
    text_lower=text.lower()
    keywords = ["executed by", "grantor:", "mortgagor:", "grantor", "mortgagor", "married"]
    index = None
    for keyword in keywords:
        if keyword in text_lower:
            index = text_lower.find(keyword)
            break
    
    if index is None:
        return print("Mortgagor not found")

    subtext=text[index-80:index+75]
    if 'and' in subtext.lower():
        subtext = re.sub(r'(?<!\s)and(?!\s)', ' and ', subtext, flags=re.IGNORECASE)

    print(subtext)

    doc = nlp(subtext)
    people=[]
    org=[]
    for ent in doc.ents:
        if ent.label_ == "PERSON" and "mortgag" not in ent.text.lower() and "grantor" not in ent.text.lower():  # Looks for names
            people.append(ent.text)
        if ent.label_=="ORG":
            org.append(ent.text)
    if people:
        for ent in doc.ents:
            if "llc" in ent.text.lower():
                people.append(ent.text)
        print("Name of the mortgagor:", people)
    elif org:
        print("Name of the mortgagor:", org)
    else:
        print("No name found")

def analyze_text_date(text):
    text_lower=text.lower()
    date = None
    if "2024" in text_lower:
        index=text_lower.find("2024")
    elif "date" in text_lower:
        index=text_lower.find("date")
    else:
        return print("Date not found")
    subtext=text[index-50:index+60]
    allow="/"
    subtext=re.sub(rf"[{re.escape(string.punctuation.replace(allow, ''))}]", " ", subtext)
    subtext = re.sub(r"(2024).*", r"\1", subtext)
    subtext = re.sub(r'\s+', ' ', subtext).strip()
    print(subtext)
    doc = nlp(subtext)
    for ent in doc.ents:
        print(ent)
        if ent.label_ == "DATE" and "20" in ent.text:  
            date = ent.text
            return print("Date: ",date)
    return print("Date not found")


def analyze_text_price(text):
    text_lower=text.lower()
    amount=None
    if "amount" in text_lower:
        index=text_lower.find("amount")
    elif "000" in text_lower:
        index=text_lower.find("000")
    elif ".00" in text_lower:
        index=text_lower.find(".00")
    else:
        return print("Price not found")
    subtext=text[index-20:index+25]
    print(subtext)

    allow = r"$,."  # Characters to keep
    pattern = rf"[{re.escape(''.join(c for c in string.punctuation if c not in allow))}]"  
    subtext = re.sub(pattern, " ", subtext)  

    doc = nlp(subtext)
    for ent in doc.ents:
        print(ent)
        if ent.label_ == "MONEY":  
            amount = ent.text
            break
    if amount:
        print("Price: $",amount)
    else:
        print("Price not found")

def analyze_text_address(text):
    text_lower=text.lower()
    keywords = ["lot", "block", "unit"]
    index = None
    for keyword in keywords:
        if keyword in text_lower:
            index = text_lower.find(keyword)
            break
    if index==None:
        return print("Address not found")
    texas=text_lower.find("texas", index)
    subtext=text[index:texas+5]
    subtext = re.sub("\n", "", subtext)

    print("Address: ",subtext)

connection, cursor = connect_to_db()
cursor.execute("""SELECT * FROM doc_info;""")
data = cursor.fetchall()


generator = pipeline("text-generation", model="gpt2")


for link in data:
    try:
        response = requests.get(link[5])
        response.raise_for_status()
        pdf_content = response.content
        time.sleep(2)
        text = extract_text_from_pdf(pdf_content)
        time.sleep(2)
        text = re.sub("\n", "", text)
        print(text)
        #import ipdb; ipdb.set_trace()
        print("===============================================================================")
        analyze_text_name(text)
        time.sleep(2)
        print("--------------------------------")
        analyze_text_date(text)
        time.sleep(2)
        print("--------------------------------")
        analyze_text_price(text)
        time.sleep(2)
        print("--------------------------------")
        analyze_text_address(text)
    except Exception as e:
        print(f"Error processing {link[5]}: {e}")


# Commit the transaction to persist the changes
connection.commit()

# Close the connection
cursor.close()
connection.close()
