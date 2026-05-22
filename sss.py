#!/usr/bin/env python3
"""
Sharesansar Daily Share Price Scraper -> Google Sheets
Scrapes: https://www.sharesansar.com/today-share-price
Saves to: nepseScrap Google Sheet (single sheet, Sheet1)
Runs on: GitHub Actions (daily at 5:00 PM Nepal Time = 11:15 UTC)
Columns: Date, Symbol, Open, High, Low, Close, Close-LTP %, Volumn
Skips: Saturday (market holiday) and if all data same as yesterday
"""

import requests
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timedelta
import os
import json

# ================= CONFIGURATION =================
SHEET_NAME = "nepseScrap"
SHEET_WORKSHEET = "Sheet1"
URL = "https://www.sharesansar.com/today-share-price"
SERVICE_ACCOUNT_FILE = "GOOGLE_SERVICE_ACCOUNT_JSON"

# 8 columns in exact order
OUTPUT_COLUMNS = [
    'Date', 'Symbol', 'Open', 'High', 'Low', 
    'Close', 'Close-LTP %', 'Volumn'
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
# =================================================

def get_nepal_date():
    from datetime import datetime
    import pytz
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    return datetime.now(nepal_tz).strftime("%Y-%m-%d")

def is_saturday(date_str):
    from datetime import datetime
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.weekday() == 5

def setup_google_sheets():
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if service_account_json:
        credentials_info = json.loads(service_account_json)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
    else:
        credentials = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
    
    client = gspread.authorize(credentials)
    
    try:
        spreadsheet = client.open(SHEET_NAME)
        print(f"✓ Opened existing sheet: {SHEET_NAME}")
    except gspread.exceptions.NotFound:
        spreadsheet = client.create(SHEET_NAME)
        print(f"✓ Created new sheet: {SHEET_NAME}")
    
    try:
        sheet = spreadsheet.worksheet(SHEET_WORKSHEET)
        print(f"✓ Opened worksheet: {SHEET_WORKSHEET}")
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=SHEET_WORKSHEET, rows=100000, cols=20)
        print(f"✓ Created new worksheet: {SHEET_WORKSHEET}")
    
    return sheet

def scrape_sharesansar():
    print("=" * 70)
    print(f"📊 Scraping Sharesansar: {URL}")
    print("=" * 70)
    
    tables = pd.read_html(URL, header=0)
    
    if not tables:
        raise Exception("No tables found on Sharesansar page")
    
    df = tables[0]
    print(f"✓ Found {len(df)} companies")
    print(f"✓ Original columns: {df.columns.tolist()}")
    
    return df

def extract_required_columns(df):
    df.columns = [str(col).strip().rstrip('.') for col in df.columns]
    
    column_mapping = {}
    
    for col in df.columns:
        col_lower = col.lower()
        
        if 'symbol' in col_lower:
            column_mapping[col] = 'Symbol'
        elif 'open' in col_lower:
            column_mapping[col] = 'Open'
        elif 'high' in col_lower:
            column_mapping[col] = 'High'
        elif 'low' in col_lower:
            column_mapping[col] = 'Low'
        elif col_lower == 'close':
            column_mapping[col] = 'Close'
        elif 'close - ltp %' in col_lower or 'close-ltp %' in col_lower:
            column_mapping[col] = 'Close-LTP %'
        elif 'vol' in col_lower or 'volume' in col_lower:
            column_mapping[col] = 'Volumn'
    
    df_renamed = df.rename(columns=column_mapping)
    print(f"✓ Mapped columns: {df_renamed.columns.tolist()}")
    
    required_cols = ['Symbol', 'Open', 'High', 'Low', 'Close', 'Close-LTP %', 'Volumn']
    
    missing_cols = [col for col in required_cols if col not in df_renamed.columns]
    if missing_cols:
        print(f"⚠️  Missing columns: {missing_cols}")
        for col in missing_cols:
            df_renamed[col] = ''
    
    df_filtered = df_renamed[required_cols].copy()
    
    today = get_nepal_date()
    df_filtered.insert(0, 'Date', today)
    
    print(f"✓ Final columns: {df_filtered.columns.tolist()}")
    print(f"✓ Extracted {len(df_filtered)} rows")
    
    return df_filtered

def check_if_data_changed(sheet, today_data):
    print("\n" + "-" * 70)
    print("🔍 Checking if data changed from yesterday...")
    
    try:
        all_values = sheet.get_all_values()
        
        if len(all_values) <= 1:
            print("✓ Sheet is empty - new data will be added")
            return True
        
        from datetime import datetime, timedelta
        import pytz
        nepal_tz = pytz.timezone('Asia/Kathmandu')
        now = datetime.now(nepal_tz)
        yesterday = now - timedelta(days=1)
        yesterday_date = yesterday.strftime("%Y-%m-%d")
        
        yesterday_data = []
        for i, row in enumerate(all_values[1:], start=1):
            if row and len(row) > 0 and row[0] == yesterday_date:
                yesterday_data.append(row)
        
        if not yesterday_data:
            print(f"✓ No data found for {yesterday_date} - new data will be added")
            return True
        
        print(f"✓ Found {len(yesterday_data)} rows for {yesterday_date}")
        
        today_rows = today_data.values.tolist()
        
        if len(today_rows) != len(yesterday_data):
            print(f"✓ Row count changed: {len(today_rows)} vs {len(yesterday_data)} - adding new data")
            return True
        
        all_same = True
        changes_found = 0
        
        for i, (today_row, yesterday_row) in enumerate(zip(today_rows, yesterday_data)):
            if today_row != yesterday_row:
                all_same = False
                changes_found += 1
                if changes_found <= 3:
                    print(f"  Change found in row {i+1}: {today_row[1]} (Symbol)")
        
        if all_same:
            print(f"⚠️  All data is IDENTICAL to {yesterday_date} - skipping to avoid duplicates")
            return False
        else:
            print(f"✓ Data changed ({changes_found} differences) - will add new data")
            return True
        
    except Exception as e:
        print(f"⚠️  Could not check for changes: {e}")
        print("✓ Will add new data to be safe")
        return True

def update_google_sheet(sheet, df):
    today = get_nepal_date()
    
    print("\n" + "=" * 70)
    print(f"📅 Updating Google Sheet: {SHEET_NAME} / {SHEET_WORKSHEET}")
    print(f"📅 Date: {today}")
    print("=" * 70)
    
    if is_saturday(today):
        print(f"⚠️  Today is Saturday ({today}) - market holiday, skipping")
        return 0
    
    df_filtered = extract_required_columns(df)
    
    if not check_if_data_changed(sheet, df_filtered):
        print("✅ No data changes detected - skipping")
        return 0
    
    try:
        existing_headers = sheet.row_values(1)
    except:
        existing_headers = ['']
    
    is_new_sheet = existing_headers == [''] or all(h == '' for h in existing_headers)
    
    if is_new_sheet:
        sheet.append_row(OUTPUT_COLUMNS)
        print(f"✓ Headers written: {OUTPUT_COLUMNS}")
    
    data = df_filtered.values.tolist()
    sheet.append_rows(data)
    
    total_rows = len(sheet.get_all_values()) - 1
    print(f"✓ Successfully appended {len(data)} rows")
    print(f"✓ Total rows in sheet: {total_rows}")
    print(f"✅ Data saved for: {today}")
    
    return len(data)

def main():
    print("\n" + "=" * 70)
    print("🚀 SHARESANSAR DAILY SCRAPER")
    print("🚀 Sheet: nepseScrap / Sheet1")
    print("🚀 Columns: Date, Symbol, Open, High, Low, Close, Close-LTP %, Volumn")
    print("=" * 70)
    
    try:
        df = scrape_sharesansar()
        sheet = setup_google_sheets()
        rows_added = update_google_sheet(sheet, df)
        
        if rows_added > 0:
            print("\n" + "=" * 70)
            print("✅ SUCCESS!")
            print("=" * 70)
            print(f"  • Scraped {len(df)} companies")
            print(f"  • Extracted {rows_added} rows")
            print(f"  • Columns: {OUTPUT_COLUMNS}")
            print(f"  • Sheet: nepseScrap / Sheet1")
        else:
            print("\n" + "=" * 70)
            print("ℹ️  NO ACTION NEEDED")
            print("=" * 70)
        
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
