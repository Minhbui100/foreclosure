import psycopg2
import re
from psycopg2 import OperationalError
import requests
from pdf2image import convert_from_bytes
import pytesseract
from transformers import pipeline, GPT2Tokenizer
import string
import time
from PIL import ImageFilter

def connect_to_db():
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
        # Preprocess image: Convert to grayscale & enhance readability
        page = page.convert("L")  # Convert to grayscale
        page = page.filter(ImageFilter.SHARPEN)  # Sharpen image

        text = pytesseract.image_to_string(page, config="--psm 6")  # Page segmentation mode 6 (Assumes single column)
        
        extracted_text += text + " "
    
    # Remove excessive newlines and extra spaces
    extracted_text = re.sub(r'\n+', '\n', extracted_text).strip()
    
    return extracted_text

import spacy

nlp = spacy.load("en_core_web_trf")

def remove_lowercase_words(text):
    words = text.split()  # Split the text into words
    filtered_words = [word for word in words if not re.match(r'^[a-z]', word)]  # Keep words that don't start with lowercase
    return " ".join(filtered_words)  

def analyze_text_name(text):
    text_lower=text.lower()
    keywords = ["grantor:", "mortgagor:", "grantor", "mortgagor", "executed by"]
    index = None
    for keyword in keywords:
        if keyword in text_lower:
            index = text_lower.find(keyword)
            break
    
    if index is None:
        return print("Mortgagor not found")

    subtext=text[index-75:index+75]
    print(subtext)

    doc = nlp(subtext)
    for ent in doc.ents:
        print(ent)
        if ent.label_ == "PERSON" or ent.label_ == "ORG":  
            name = ent.text
            break
    if name:
        name=remove_lowercase_words(name)
        name=name.title()
        print("\nName of the mortgagor: ",name)
    else:
        print("Mortgagor not found")

def analyze_text_date(text):
    text_lower=text.lower()
    if "date" in text_lower:
        index=text_lower.find("date")
    else:
        return print("Date not found")
    subtext=text[index-50:index+60]
    allow="/"
    subtext=re.sub(rf"[{re.escape(string.punctuation.replace(allow, ''))}]", " ", subtext)
    print(subtext)
    doc = nlp(subtext)
    for ent in doc.ents:
        print(ent)
        if ent.label_ == "DATE":  
            date = ent.text
            break
    if date:
        print("Date: ",date)
    else:
        print("Date not found")


def analyze_text_price(text):
    text_lower=text.lower()
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
            date = ent.text
            break
    if date:
        print("Price: $",date)
    else:
        print("Price not found")

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

        text = extract_text_from_pdf(pdf_content)
        text = re.sub("\n", "", text)
        print(text)
        #import ipdb; ipdb.set_trace()
        if "postponement" in text.lower(): 
            continue  
        print("===============================================================================")
        print(link[5], "\n")
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
