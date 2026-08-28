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

def load_data(name):
    csv_path = os.path.join(RAW_DIR, f"{name}.csv")
    df = pd.read_csv(csv_path, header=[0, 1])
    
    df.columns = [col[0] for col in df.columns]
    
    df = pd.read_csv(csv_path, index_col=0, header=[0, 1], parse_dates=True)
    df.columns = [col[0] for col in df.columns]
    df.index.name = 'Date'
    
    price_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    
    s = df[price_col].rename(name)
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    s = s.dropna()
    
    return pd.DataFrame(s), price_col

def align_datasets():
    print("Loading datasets...")
    
    dataset_metadata = {}
    
    df_anchor, field = load_data(ANCHOR)
    dataset_metadata[ANCHOR] = {'ticker': SYMBOLS[ANCHOR], 'field_used': field, 'source': 'Yahoo Finance'}
    
    df_master = df_anchor.copy()
    
    for var in INDIAN_VARS:
        df_var, field = load_data(var)
        dataset_metadata[var] = {'ticker': SYMBOLS[var], 'field_used': field, 'source': 'Yahoo Finance'}
        df_master = df_master.join(df_var, how='left')
        
    for var in GLOBAL_VARS:
        df_var, field = load_data(var)
        dataset_metadata[var] = {'ticker': SYMBOLS[var], 'field_used': field, 'source': 'Yahoo Finance'}
        
        df_master = df_master.sort_index()
        df_var = df_var.sort_index()
        
        df_merged = pd.merge_asof(
            df_master, 
            df_var, 
            left_index=True, 
            right_index=True, 
            direction='backward', 
            allow_exact_matches=False
        )
        df_master = df_merged

    missing_counts = df_master.isna().sum()
    print("\nMissing values before dropna:")
    print(missing_counts)
    
    df_final = df_master.dropna()
    
    print(f"\nOriginal Anchor Length: {len(df_master)}")
    print(f"Final Aligned Length: {len(df_final)}")
    
    start_date = df_final.index.min().strftime('%Y-%m-%d')
    end_date = df_final.index.max().strftime('%Y-%m-%d')
    print(f"Final Research Period: {start_date} to {end_date}")
    
    # Calculate observations for each asset over the aligned period
    for var in dataset_metadata.keys():
        dataset_metadata[var]['start_date'] = start_date
        dataset_metadata[var]['end_date'] = end_date
        dataset_metadata[var]['observations'] = len(df_final)
    
    csv_path = os.path.join(FINAL_DIR, 'master_research_dataset.csv')
    df_final.to_csv(csv_path)
    print(f"\nSaved final aligned dataset to {csv_path}")
    
    summary = {
        'start_date': start_date,
        'end_date': end_date,
        'total_observations': len(df_final),
        'methodology': {
            'anchor': ANCHOR,
            'same_day_alignment': INDIAN_VARS,
            'strictly_prior_alignment': GLOBAL_VARS
        },
        'columns': list(df_final.columns),
        'dataset_metadata': dataset_metadata
    }
    
    with open(os.path.join(FINAL_DIR, 'alignment_summary.json'), 'w') as f:
        json.dump(summary, f, indent=4)

if __name__ == '__main__':
    align_datasets()
