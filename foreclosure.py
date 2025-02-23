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
from transformers import pipeline, GPT2Tokenizer
import string






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


def extract_text_from_pdf(pdf_content):
    pages = convert_from_bytes(pdf_content)
    extracted_text = ""
    for page_num, page in enumerate(pages):
        text = pytesseract.image_to_string(page)
        extracted_text += text + "\n"
        
    return extracted_text

# Initialize model and tokenizer
generator = pipeline("text-generation", model="gpt2")
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")  # Initialize the tokenizer


def analyze_text_name(text):
    text_lower=text.lower()
    if "mortgagor" in text_lower:
        index=text_lower.find("mortgagor")
    elif "grantor" in text_lower:
        index=text_lower.find("grantor")
    else:
        return print("Mortgagor not found")
    subtext=text[index-50:index+50]
    print(subtext)

    tokens = tokenizer.encode(subtext)  # Keep some space for the prompt
    truncated_text = tokenizer.decode(tokens, skip_special_tokens=True)

    # Create a concise prompt
    prompt = f"Extract only the mortgagor's or grantor's name from the following text:\n\n{truncated_text}\n\nMortgagor/Grantor's name:"
    
    # Generate the result using GPT-2
    result = generator(prompt, max_new_tokens=10, temperature=0.5, return_full_text=False)

    # Extract only the first generated line (to avoid extra output)
    name = result[0]['generated_text'].strip().split("\n")[0]
    name = re.sub(rf"[{string.punctuation}]", "", name)
    name = re.sub("\n", "", name)
    
    print("Name of the martgagor: ",name)

def analyze_text_date(text):
    text_lower=text.lower()
    if "date" in text_lower:
        index=text_lower.find("date")
    else:
        return print("Date not found")
    subtext=text[index-50:index+60]
    print(subtext)

    tokens = tokenizer.encode(subtext, truncation=True, max_length=800)  # Keep some space for the prompt
    truncated_text = tokenizer.decode(tokens, skip_special_tokens=True)

    # Create a concise prompt
    prompt = f"Extract only the date from the following text:\n\n{truncated_text}\n\Date:"
    
    # Generate the result using GPT-2
    result = generator(prompt, max_new_tokens=10, temperature=0.5, return_full_text=False)

    # Extract only the first generated line (to avoid extra output)
    date = result[0]['generated_text'].strip().split("\n")[0]
    allowed_chars = "/-"
    date = re.sub(rf"[{string.punctuation}&&[^{allowed_chars}]]", "", date)
    
    print("Date: ",date)


def analyze_text_price(text):
    text_lower=text.lower()
    if "$" in text_lower:
        index=text_lower.find("$")
    elif "amount" in text_lower:
        index=text_lower.find("amount")
    else:
        return print("Price not found")
    subtext=text[index-20:index+25]
    print(subtext)

    tokens = tokenizer.encode(subtext, truncation=True, max_length=800)  # Keep some space for the prompt
    truncated_text = tokenizer.decode(tokens, skip_special_tokens=True)

    # Create a concise prompt
    prompt = f"Extract only the price from the following text:\n\n{truncated_text}\n\nPrice: $"
    
    # Generate the result using GPT-2
    result = generator(prompt, max_new_tokens=10, temperature=0.5, return_full_text=False)

    # Extract only the first generated line (to avoid extra output)
    price = result[0]['generated_text'].strip().split("\n")[0]
    allowed_chars = ",."
    date = re.sub(rf"[{string.punctuation}&&[^{allowed_chars}]]", "", date)

    
    print("Price: $",price)

def analyze_text_address(text):
    text_lower=text.lower()
    if "lot" in text_lower:
        index=text_lower.find("lot")
    elif "block" in text_lower:
        index=text_lower.find("block")
    else:
        return print("Address not found")
    texas=text_lower.find("texas", index)
    subtext=text[index:texas+5]
    subtext = re.sub("\n", "", subtext)

    print("Address",subtext)

connection, cursor = connect_to_db()
cursor.execute("""SELECT * FROM doc_info;""")
data = cursor.fetchall()


generator = pipeline("text-generation", model="gpt2")


for link in data:
    try:
        response = requests.get(link[5])
        response.raise_for_status()  
        pdf_content = response.content
        text = extract_text_from_pdf(pdf_content)
        if "postponement" in text.lower(): 
            continue  
        print("===============================================================================")
        print(link[5], "\n")
        analyze_text_name(text)
        analyze_text_date(text)
        analyze_text_price(text)
        analyze_text_address(text)
    except Exception as e:
        print(f"Error processing {link[5]}: {e}")
