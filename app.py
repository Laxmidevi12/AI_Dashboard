import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from serpapi import GoogleSearch

# Load environment variables
load_dotenv()

# Retrieve API keys and credentials
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
GROQ_API_URL = os.getenv("GROQ_API_URL")

if not GROQ_API_KEY or not GROQ_API_URL:
    raise ValueError("Groq API credentials are missing! Check your .env file.")

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Function to load CSV file
def load_csv():
    file = st.file_uploader("Upload a CSV file", type="csv")
    if file is not None:
        data = pd.read_csv(file)
        st.write(data.head())
        return data
    return None

# Function to authenticate and get Google Sheets data
def authenticate_google_sheets():
    flow = InstalledAppFlow.from_client_secrets_file(
        GOOGLE_SHEETS_CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('sheets', 'v4', credentials=creds)
    return service

# Function to fetch Google Sheets data
def get_google_sheet_data(spreadsheet_id, range_name):
    service = authenticate_google_sheets()
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    return result.get('values', [])

# Function to perform web search using SerpAPI
def perform_web_search(query):
    params = {
        "q": query,
        "api_key": SERPAPI_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return results

# Function to interact with Groq API
def process_with_groq(search_data, query):
    """
    Process the query and search data using Groq API.
    """
    try:
        # Input structure for Groq API
        payload = {
            "model": "text-davinci-003",  # Use a model that you have access to
            "messages": [
                {"role": "system", "content": "You are an AI assistant."},
                {"role": "user", "content": f"{query}\n\nAdditional context: {search_data}"}
            ]
        }
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Send the request to Groq API
        response = requests.post(GROQ_API_URL, json=payload, headers=headers)

        # Handle the response
        if response.status_code == 200:
            return response.json().get("choices", [{}])[0].get("message", {}).get("content", "No result found")
        else:
            st.error(f"Groq API Error: {response.status_code} - {response.text}")
            return f"Error: {response.text}"

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None


# Function to display and download data
def display_data(extracted_data):
    if extracted_data:
        df = pd.DataFrame(extracted_data)
        st.write(df)
        st.download_button(
            label="Download CSV",
            data=df.to_csv(index=False),
            file_name="extracted_data.csv",
            mime="text/csv"
        )

# Main dashboard function
def main():
    # Main dashboard function
    st.title("AI Agent for Data Extraction with Groq")

    # File Upload or Google Sheets connection
    uploaded_csv = load_csv()
    query = st.text_input("Enter your query template (use {company} for placeholders):","Extract contact details for {company}")
    
    # Ensure query is defined before using it
    if query and uploaded_csv is not None:
        selected_column = st.selectbox("Select main column", uploaded_csv.columns)
        st.write(f"Showing data from column: {selected_column}")

        search_results = []
        for entity in uploaded_csv[selected_column]:
            # Convert entity to string to avoid TypeError
            search_query = query.replace("{company}", str(entity))
            search_data = perform_web_search(search_query)
            extracted_data = process_with_groq(search_data, search_query)
            search_results.append({selected_column: entity, 'Extracted Data': extracted_data})
        
        # Display the extracted results
        display_data(search_results)
    else:
        st.warning("Please upload a CSV file and enter a query template.")



if __name__ == "__main__":
    main()
