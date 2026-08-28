import pandas as pd
import numpy as np
import os
import json
import scipy.stats as stats

FINAL_DIR = os.path.join('data', 'final')
OUTPUT_DIR = os.path.join('data', 'stats')

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load master dataset
df = pd.read_csv(os.path.join(FINAL_DIR, 'master_research_dataset.csv'), index_col='Date', parse_dates=True)

# 1. Calculate Returns
# Return_t = (Price_t / Price_(t-1)) - 1
returns_1d = df.pct_change(1).dropna()
returns_5d = df.pct_change(5).dropna()
returns_20d = df.pct_change(20).dropna()
returns_60d = df.pct_change(60).dropna()

def calculate_descriptive_stats(ret_df, window_days=1):
    stats_dict = {}
    annualization_factor = 252 / window_days
    
    for col in ret_df.columns:
        s = ret_df[col]
        stats_dict[col] = {
            'mean': float(s.mean()),
            'median': float(s.median()),
            'std': float(s.std()),
            'min': float(s.min()),
            'max': float(s.max()),
            'skewness': float(stats.skew(s.dropna())),
            'kurtosis': float(stats.kurtosis(s.dropna())),
            # Annualization based on simple scaling for returns
            'annualized_mean_return': float(s.mean() * annualization_factor),
            'annualized_volatility': float(s.std() * np.sqrt(annualization_factor)),
            'observations': len(s.dropna()),
            'percentiles': {
                'p5': float(np.percentile(s.dropna(), 5)),
                'p25': float(np.percentile(s.dropna(), 25)),
                'p50': float(np.percentile(s.dropna(), 50)),
                'p75': float(np.percentile(s.dropna(), 75)),
                'p95': float(np.percentile(s.dropna(), 95))
            }
        }
    return stats_dict

print("Calculating Descriptive Statistics...")
descriptive_stats = {
    'daily': calculate_descriptive_stats(returns_1d, 1),
    '5d': calculate_descriptive_stats(returns_5d, 5),
    '20d': calculate_descriptive_stats(returns_20d, 20),
    '60d': calculate_descriptive_stats(returns_60d, 60)
}

# 2. Correlation Analysis (Full Period)
print("Calculating Full Period Correlations...")
corr_matrix = returns_1d.corr().to_dict()

def get_p_values(df):
    cols = df.columns
    p_values = pd.DataFrame(index=cols, columns=cols)
    for r in cols:
        for c in cols:
            if r == c:
                p_values.loc[r, c] = 0.0
            else:
                # dropna for pairwise
                valid = df[[r, c]].dropna()
                if len(valid) > 2:
                    p_val = stats.pearsonr(valid[r], valid[c])[1]
                    p_values.loc[r, c] = float(p_val)
                else:
                    p_values.loc[r, c] = np.nan
    return p_values.to_dict()

corr_p_values = get_p_values(returns_1d)

# 3. Rolling Correlations with NIFTY 50
print("Calculating Rolling Correlations...")
windows = [20, 60, 120, 252]
rolling_corr_series = {}

# We will export time series for UI charting
# Format: { 'SP_500': { '20d': [ {date: "2016-02-01", val: 0.85}, ... ] } }
for col in df.columns:
    if col == 'NIFTY_50': continue
    rolling_corr_series[col] = {}
    for w in windows:
        roll_corr = returns_1d['NIFTY_50'].rolling(w).corr(returns_1d[col]).dropna()
        # Downsample to save space (e.g. weekly data points is enough for 10-year chart visualization)
        # We will keep every 5th day
        roll_corr_sampled = roll_corr.iloc[::5]
        
        series_data = []
        for dt, val in roll_corr_sampled.items():
            if not np.isnan(val):
                series_data.append({
                    'date': dt.strftime('%Y-%m-%d'),
                    'val': float(val)
                })
        rolling_corr_series[col][f"{w}d"] = series_data

# Save to JSON
print("Saving statistics to JSON...")
with open(os.path.join(OUTPUT_DIR, 'descriptive_stats.json'), 'w') as f:
    json.dump(descriptive_stats, f, indent=4)

with open(os.path.join(OUTPUT_DIR, 'correlation_matrix.json'), 'w') as f:
    json.dump({
        'correlation': corr_matrix,
        'p_values': corr_p_values,
        'observations': len(returns_1d)
    }, f, indent=4)
    
with open(os.path.join(OUTPUT_DIR, 'rolling_correlations.json'), 'w') as f:
    json.dump(rolling_corr_series, f)

# Also save the normalized price series for historical performance charting
print("Saving Normalized Performance Series...")
# Normalize to 100 at the start
df_normalized = (df / df.iloc[0]) * 100
# Downsample to weekly for UI charting over 10 years to save payload size
df_norm_sampled = df_normalized.iloc[::5]

normalized_series = {}
for col in df_norm_sampled.columns:
    series_data = []
    for dt, val in df_norm_sampled[col].items():
        if not np.isnan(val):
            series_data.append({
                'date': dt.strftime('%Y-%m-%d'),
                'val': float(val)
            })
    normalized_series[col] = series_data

with open(os.path.join(OUTPUT_DIR, 'normalized_performance.json'), 'w') as f:
    json.dump(normalized_series, f)

print("Stage 3 processing complete!")
