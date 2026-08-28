import pandas as pd
import os
import json

RAW_DIR = os.path.join('data', 'raw')
CLEANED_DIR = os.path.join('data', 'cleaned')
FINAL_DIR = os.path.join('data', 'final')

os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)

# Define groupings based on alignment rules
ANCHOR = 'NIFTY_50'
INDIAN_VARS = ['India_VIX', 'NIFTY_IT', 'NIFTY_Bank']
GLOBAL_VARS = ['SP_500', 'NASDAQ_100', 'US_VIX', 'Brent_Crude', 'Gold', 'USD_INR']

def load_data(name):
    # yfinance csv format might have multi-level if we used yf.download
    # download_data.py already saved it cleanly with Date as index if we passed index_col=0, but let's be robust
    # Actually, in download_data.py we just did data.to_csv(), which for a single ticker creates a normal CSV with 'Date' as index.
    csv_path = os.path.join(RAW_DIR, f"{name}.csv")
    df = pd.read_csv(csv_path, header=[0, 1])
    
    # yfinance returns multi-index columns, e.g., ('Adj Close', 'Ticker')
    # Flatten columns
    df.columns = [col[0] for col in df.columns]
    
    # Set the first column ('Price' usually named 'Price' or unnamed if it's the index, but let's check)
    # yfinance usually saves the index as 'Date'
    df = pd.read_csv(csv_path, index_col=0, header=[0, 1], parse_dates=True)
    df.columns = [col[0] for col in df.columns]
    df.index.name = 'Date'
    
    # We will primarily use 'Adj Close' if available, otherwise 'Close'
    # Actually user approved 'Adj Close'
    price_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    
    # Return a Series with the selected price column
    s = df[price_col].rename(name)
    
    # Ensure index is datetime
    s.index = pd.to_datetime(s.index)
    
    # Sort index to be safe
    s = s.sort_index()
    
    # Drop NaNs
    s = s.dropna()
    
    return pd.DataFrame(s)

def align_datasets():
    print("Loading datasets...")
    
    # Load anchor
    df_anchor = load_data(ANCHOR)
    
    # Start the master dataframe
    df_master = df_anchor.copy()
    
    # 1. Align Indian Variables (Same day exact match)
    for var in INDIAN_VARS:
        df_var = load_data(var)
        # Left join on exact Date
        df_master = df_master.join(df_var, how='left')
        
    # 2. Align Global Variables (Strictly prior day)
    # For each date in df_master, find the latest date in df_var that is < the df_master date.
    for var in GLOBAL_VARS:
        df_var = load_data(var)
        
        # Sort both just in case
        df_master = df_master.sort_index()
        df_var = df_var.sort_index()
        
        # Merge asof, direction='backward', allow_exact_matches=False
        # This means for a date like 2020-01-05 in anchor, it will look for the largest date <= 2020-01-04 in var.
        df_merged = pd.merge_asof(
            df_master, 
            df_var, 
            left_index=True, 
            right_index=True, 
            direction='backward', 
            allow_exact_matches=False
        )
        # Update master
        df_master = df_merged

    # Now df_master has all columns. 
    # Because of the strict lag, the first few rows might have NaNs for global variables if no prior data exists.
    # Also, some Indian holidays might cause missing values for same-day Indian vars.
    # Let's count missing values before dropping
    missing_counts = df_master.isna().sum()
    print("\nMissing values before dropna:")
    print(missing_counts)
    
    # We want a clean research period, so we drop any row with NaNs
    df_final = df_master.dropna()
    
    print(f"\nOriginal Anchor Length: {len(df_master)}")
    print(f"Final Aligned Length: {len(df_final)}")
    
    start_date = df_final.index.min().strftime('%Y-%m-%d')
    end_date = df_final.index.max().strftime('%Y-%m-%d')
    print(f"Final Research Period: {start_date} to {end_date}")
    
    # Save the aligned dataset
    csv_path = os.path.join(FINAL_DIR, 'master_research_dataset.csv')
    df_final.to_csv(csv_path)
    print(f"\nSaved final aligned dataset to {csv_path}")
    
    # Also save a JSON summary for the UI and artifacts
    summary = {
        'start_date': start_date,
        'end_date': end_date,
        'total_observations': len(df_final),
        'methodology': {
            'anchor': ANCHOR,
            'same_day_alignment': INDIAN_VARS,
            'strictly_prior_alignment': GLOBAL_VARS
        },
        'columns': list(df_final.columns)
    }
    
    with open(os.path.join(FINAL_DIR, 'alignment_summary.json'), 'w') as f:
        json.dump(summary, f, indent=4)

if __name__ == '__main__':
    align_datasets()
