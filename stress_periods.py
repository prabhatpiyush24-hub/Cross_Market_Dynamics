import pandas as pd
import numpy as np
import os
import json
import scipy.stats as stats

FINAL_DIR = os.path.join('data', 'final')
OUTPUT_DIR = os.path.join('data', 'stats')

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load master dataset (prices)
df = pd.read_csv(os.path.join(FINAL_DIR, 'master_research_dataset.csv'), index_col='Date', parse_dates=True)

# Calculate daily returns for correlation
returns = df.pct_change(1).dropna()

stress_windows = {
    'COVID-19 Crash': {
        'start': '2020-02-19',
        'end': '2020-03-23',
        'description': 'The fastest global equity crash in history.'
    },
    '2022 Bear Market (Rate Hikes)': {
        'start': '2022-01-03',
        'end': '2022-10-12',
        'description': 'Prolonged global selloff driven by aggressive central bank tightening and inflation fears.'
    },
    'Late 2018 Selloff': {
        'start': '2018-10-01',
        'end': '2018-12-24',
        'description': 'Sharp market correction driven by US-China trade war fears and slowing global growth.'
    }
}

assets_to_analyze = ['NIFTY_50', 'SP_500', 'NASDAQ_100', 'Gold', 'Brent_Crude', 'USD_INR', 'India_VIX']

results = []

for name, window in stress_windows.items():
    start_date = pd.to_datetime(window['start'])
    end_date = pd.to_datetime(window['end'])
    
    # Slice prices
    # We use nearest available dates in case the exact date is a weekend/holiday
    sliced_prices = df.loc[start_date:end_date]
    
    if len(sliced_prices) == 0:
        continue
        
    sliced_returns = returns.loc[sliced_prices.index].dropna()
    
    period_stats = {
        'name': name,
        'start_date': sliced_prices.index.min().strftime('%Y-%m-%d'),
        'end_date': sliced_prices.index.max().strftime('%Y-%m-%d'),
        'description': window['description'],
        'assets': {},
        'correlations_with_nifty': {}
    }
    
    # Calculate correlations with NIFTY during this specific window
    if len(sliced_returns) > 2:
        for asset in assets_to_analyze:
            if asset != 'NIFTY_50':
                r, p = stats.pearsonr(sliced_returns['NIFTY_50'], sliced_returns[asset])
                period_stats['correlations_with_nifty'][asset] = float(r)
    
    # Calculate Cumulative Return and Max Drawdown
    for asset in assets_to_analyze:
        prices = sliced_prices[asset].dropna()
        if len(prices) > 0:
            start_price = prices.iloc[0]
            end_price = prices.iloc[-1]
            cum_ret = (end_price / start_price) - 1
            
            # Max Drawdown
            rolling_max = prices.cummax()
            drawdowns = (prices / rolling_max) - 1
            max_dd = drawdowns.min()
            
            period_stats['assets'][asset] = {
                'cumulative_return': float(cum_ret),
                'max_drawdown': float(max_dd)
            }
            
    results.append(period_stats)

print("Saving Stress Periods data to JSON...")
with open(os.path.join(OUTPUT_DIR, 'stress_periods.json'), 'w') as f:
    json.dump(results, f, indent=4)

print("Stress Periods processing complete!")
