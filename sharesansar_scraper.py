import requests
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
import os

# ================= CONFIGURATION =================
SHEET_NAME = "nepseScrap"
SHEET_WORKSHEET = "Sheet1"
URL = "https://www.sharesansar.com/today-share-price"
SERVICE_ACCOUNT_FILE = "service-account-key.json"  

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

def is_market_holiday(date_str):
    from datetime import datetime
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    if date_obj.weekday() == 5:  # Saturday
        return True
    return False

def setup_google_sheets():
    """Authenticate and connect to Google Sheets"""
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
        sheet = spreadsheet.add_worksheet(title=SHEET_WORKSHEET, rows=10000, cols=50)
        print(f"✓ Created new worksheet: {SHEET_WORKSHEET}")
    
    return sheet

def scrape_sharesansar():
    """Scrape today's share price table from Sharesansar"""
    print("=" * 70)
    print(f"📊 Scraping Sharesansar: {URL}")
    print("=" * 70)
    
    try:
        # FIX: Use 'header' (singular), not 'headers'
        tables = pd.read_html(URL, header=0)
        
        if not tables:
            raise Exception("No tables found on Sharesansar page")
        
        df = tables[0]
        print(f"✓ Successfully scraped {len(df)} companies")
        print(f"✓ Columns found: {len(df.columns)}")
        print(f"  Column names: {df.columns.tolist()}")
        
        return df
        
    except Exception as e:
        print(f"✗ Error scraping data: {e}")
        raise

def check_if_date_exists(sheet, today_date):
    """Check if today's date already exists in the sheet"""
    try:
        all_values = sheet.get_all_values()
        
        if len(all_values) <= 1:
            return False
        
        for row in all_values[1:]:
            if row and row[0] == today_date:
                print(f"⚠️  Date {today_date} already exists - skipping")
                return True
        
        return False
    except Exception as e:
        print(f"⚠️  Could not check date: {e}")
        return False

def update_google_sheet(sheet, df):
    """Append today's scraped data to the single Google Sheet"""
    today = get_nepal_date()
    
    print("\n" + "=" * 70)
    print(f"📅 Updating Google Sheet: {SHEET_NAME} / {SHEET_WORKSHEET}")
    print(f"📅 Date: {today}")
    print("=" * 70)
    
    # Skip if market holiday
    if is_market_holiday(today):
        print(f"⚠️  Market holiday ({today}) - skipping")
        return 0
    
    # Skip if date already exists
    if check_if_date_exists(sheet, today):
        print(f"✅ Data for {today} already exists")
        return 0
    
    # Add Date column at the beginning
    df_copy = df.copy()
    df_copy.insert(0, 'Date', today)
    
    # Clean column names
    df_copy.columns = [col.strip().rstrip('.') for col in df_copy.columns]
    
    print(f"✓ Dataset has {len(df_copy)} rows")
    
    # Check if sheet needs headers
    try:
        existing_headers = sheet.row_values(1)
    except:
        existing_headers = ['']
    
    is_new_sheet = existing_headers == [''] or all(h == '' for h in existing_headers)
    
    if is_new_sheet:
        headers = df_copy.columns.tolist()
        sheet.append_row(headers)
        print(f"✓ Headers written")
    
    # Append data
    data = df_copy.values.tolist()
    sheet.append_rows(data)
    
    total_rows = len(sheet.get_all_values()) - 1
    print(f"✓ Successfully appended {len(data)} rows")
    print(f"✓ Total rows: {total_rows}")
    print(f"✅ Data saved for: {today}")
    
    return len(data)

def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("🚀 SHARESANSAR DAILY SCRAPER - Local Testing")
    print("🚀 Sheet: nepseScrap / Sheet1")
    print("=" * 70)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Scrape data
        df = scrape_sharesansar()
        
        # Step 2: Connect to Google Sheets
        print("\n" + "-" * 70)
        print("🔗 Connecting to Google Sheets...")
        sheet = setup_google_sheets()
        
        # Step 3: Update sheet
        rows_added = update_google_sheet(sheet, df)
        
        # Success!
        if rows_added > 0:
            print("\n" + "=" * 70)
            print("✅ SUCCESS!")
            print("=" * 70)
            print(f"  • Scraped {len(df)} companies")
            print(f"  • Added {rows_added} rows")
            print(f"  • Sheet: nepseScrap / Sheet1")
        else:
            print("\n" + "=" * 70)
            print("ℹ️  NO ACTION NEEDED")
            print("=" * 70)
            print(f"  • Data exists or market closed")
        
        print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ ERROR!")
        print("=" * 70)
        print(f"  • Error: {e}")
        print("=" * 70)
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)