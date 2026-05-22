# Sharesansar Daily Scraper - nepseScrap

Automatically scrapes NEPSE share prices and saves to Google Sheet `nepseScrap`.

## Features
- ✅ Scrapes: https://www.sharesansar.com/today-share-price
- ✅ 8 columns: Date, Symbol, Open, High, Low, Close, Close-LTP %, Volumn
- ✅ All data in ONE sheet (Sheet1)
- ✅ Date format: YYYY-MM-DD (good for sorting)
- ✅ Skips Saturday (market holiday)
- ✅ Skips if all data same as yesterday (no duplicates)
- ✅ Runs daily at 5:00 PM Nepal Time
- ✅ Free cloud automation via GitHub Actions

## Data Structure
| Date | Symbol | Open | High | Low | Close | Close-LTP % | Volumn |
| 2026-05-22 | ACLBSL | 964.00 | 964.00 | 941.50 | 955.00 | 0.00% | 125430 |
| 2026-05-22 | ADBL | 311.80 | 312.50 | 308.00 | 311.00 | 0.00% | 98210 |