import yfinance as yf
import pandas as pd
import os
from datetime import datetime
import json

# Define the symbols and their friendly names
SYMBOLS = {
    'NIFTY_50': '^NSEI',
    'India_VIX': '^INDIAVIX',
    'SP_500': '^GSPC',
    'NASDAQ_100': '^NDX',
    'US_VIX': '^VIX',
    'Brent_Crude': 'BZ=F',
    'Gold': 'GC=F',
    'USD_INR': 'INR=X',
    'NIFTY_IT': '^CNXIT',
    'NIFTY_Bank': '^NSEBANK'
}

# 10 years of data (2016-01-01 to 2026-08-28 approx)
START_DATE = '2016-01-01'
END_DATE = '2026-08-28'

RAW_DIR = os.path.join('data', 'raw')
os.makedirs(RAW_DIR, exist_ok=True)

def download_data():
    print("Starting data download...")
    for name, ticker in SYMBOLS.items():
        print(f"Downloading {name} ({ticker})...")
        try:
            # Download data
            data = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
            
            if data.empty:
                print(f"WARNING: No data found for {name} ({ticker})")
                continue
                
            # Keep Adjusted Close if available, else Close
            # We want all columns for audit (Open, High, Low, Close, Adj Close, Volume)
            csv_path = os.path.join(RAW_DIR, f"{name}.csv")
            data.to_csv(csv_path)
            print(f"Saved {len(data)} rows to {csv_path}")
            
        except Exception as e:
            print(f"ERROR downloading {name}: {str(e)}")

def audit_data():
    print("\nStarting data audit...")
    audit_report = {
        'status': 'success',
        'warnings': [],
        'datasets': {}
    }
    
    for name in SYMBOLS.keys():
        csv_path = os.path.join(RAW_DIR, f"{name}.csv")
        if not os.path.exists(csv_path):
            audit_report['warnings'].append(f"Missing file for {name}")
            continue
            
        try:
            # yfinance downloaded CSVs usually have a MultiIndex header if multiple symbols were queried, 
            # but for single symbol it's a normal header, though the Date column might be the index.
            # We skip the first 2 rows if it's a multi-index, but yf.download for single symbol is simple.
            df = pd.read_csv(csv_path, header=[0, 1])
            # yfinance changed their output format recently to multi-index columns.
            # We can simplify by reading it, dropping the second level.
            # Actually, pd.read_csv(csv_path, header=[0, 1], index_col=0) handles it best.
            df = pd.read_csv(csv_path, header=[0, 1], index_col=0, parse_dates=True)
            
            # If the columns are multi-indexed, flatten them by taking the first level
            df.columns = [col[0] for col in df.columns]
            
            # Reset index to get Date as a column if needed, or keep as index
            
            # Check for missing dates
            expected_dates = pd.date_range(start=df.index.min(), end=df.index.max(), freq='B') # Business days
            missing_dates = expected_dates.difference(df.index)
            
            # Count nulls
            missing_prices = df['Close'].isnull().sum() if 'Close' in df.columns else 0
            
            # Zero or negative prices (except for VIX which can't be negative, but prices generally shouldn't be <=0 except maybe oil in extreme cases)
            invalid_prices = (df['Close'] <= 0).sum() if 'Close' in df.columns else 0
            
            # Suspicious jumps (e.g. > 20% in a day)
            pct_change = df['Close'].pct_change().abs() if 'Close' in df.columns else pd.Series(dtype=float)
            suspicious_jumps = (pct_change > 0.20).sum()
            
            dataset_info = {
                'first_available_date': df.index.min().strftime('%Y-%m-%d') if not df.empty else None,
                'last_available_date': df.index.max().strftime('%Y-%m-%d') if not df.empty else None,
                'number_of_observations': len(df),
                'missing_prices': int(missing_prices),
                'invalid_prices': int(invalid_prices),
                'suspicious_jumps': int(suspicious_jumps),
                'missing_business_days': len(missing_dates) # Note: missing business days might just be holidays, so this is just for context
            }
            
            audit_report['datasets'][name] = dataset_info
            
            # Add warnings if necessary
            if missing_prices > 0:
                audit_report['warnings'].append(f"{name} has {missing_prices} missing prices.")
            if invalid_prices > 0:
                audit_report['warnings'].append(f"{name} has {invalid_prices} invalid (<=0) prices.")
            if suspicious_jumps > 0:
                audit_report['warnings'].append(f"{name} has {suspicious_jumps} suspicious price jumps (>20%).")
                
        except Exception as e:
            audit_report['warnings'].append(f"Error auditing {name}: {str(e)}")
            
    # Save audit report
    report_path = os.path.join(RAW_DIR, 'audit_report.json')
    with open(report_path, 'w') as f:
        json.dump(audit_report, f, indent=4)
        
    print(f"\nAudit complete. Found {len(audit_report['warnings'])} warnings.")
    for w in audit_report['warnings']:
        print(f" - {w}")
    print(f"Report saved to {report_path}")

if __name__ == '__main__':
    download_data()
    audit_data()
