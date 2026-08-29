import pandas as pd
import numpy as np
import os
import json
import statsmodels.api as sm

FINAL_DIR = os.path.join('data', 'final')
OUTPUT_DIR = os.path.join('data', 'stats')

# Load master dataset
df = pd.read_csv(os.path.join(FINAL_DIR, 'master_research_dataset.csv'), index_col='Date', parse_dates=True)

# Calculate daily returns
returns = df.pct_change(1).dropna()

results = {}

print("1. Running Regime Analysis...")
# Regime Analysis based on India VIX level (not return)
vix_level = df['India_VIX'].loc[returns.index]
p25 = vix_level.quantile(0.25)
p75 = vix_level.quantile(0.75)

low_vix_mask = vix_level <= p25
high_vix_mask = vix_level >= p75
normal_vix_mask = (vix_level > p25) & (vix_level < p75)

regimes = {
    'Low Volatility (Bottom 25%)': returns[low_vix_mask],
    'Normal Volatility (Middle 50%)': returns[normal_vix_mask],
    'High Volatility (Top 25%)': returns[high_vix_mask]
}

regime_stats = {}
for name, regime_df in regimes.items():
    if len(regime_df) > 0:
        corr_matrix = regime_df.corr()
        regime_stats[name] = {
            'observations': len(regime_df),
            'avg_nifty_return_annualized': float(regime_df['NIFTY_50'].mean() * 252),
            'nifty_volatility_annualized': float(regime_df['NIFTY_50'].std() * np.sqrt(252)),
            'correlations': {
                'SP_500': float(corr_matrix.loc['NIFTY_50', 'SP_500']),
                'Brent_Crude': float(corr_matrix.loc['NIFTY_50', 'Brent_Crude']),
                'Gold': float(corr_matrix.loc['NIFTY_50', 'Gold']),
                'USD_INR': float(corr_matrix.loc['NIFTY_50', 'USD_INR'])
            }
        }

results['regime_analysis'] = regime_stats

print("2. Running Multiple Linear Regression...")
# Regression Lab
# Dependent Variable: NIFTY_50 current session return
y = returns['NIFTY_50']

# Independent Variables:
# - previous-session S&P return (which is just the SP_500 column in 'returns' because it was aligned as strictly prior)
# - previous-session NASDAQ return
# - previous-session Brent return
# - previous-session Gold return
# - previous-session USD/INR return
# - previous NIFTY return (we need to shift NIFTY_50 return by 1)
# - previous India VIX change (we need to shift India_VIX return by 1)

X = pd.DataFrame({
    'SP_500': returns['SP_500'],
    'NASDAQ_100': returns['NASDAQ_100'],
    'Brent_Crude': returns['Brent_Crude'],
    'Gold': returns['Gold'],
    'USD_INR': returns['USD_INR'],
    'Prev_NIFTY_50': returns['NIFTY_50'].shift(1),
    'Prev_India_VIX_Change': returns['India_VIX'].shift(1)
}).dropna()

# Align y with X
y = y.loc[X.index]

# Add constant
X_with_const = sm.add_constant(X)

# Fit OLS
model = sm.OLS(y, X_with_const)
res = model.fit()

regression_stats = {
    'rsquared': float(res.rsquared),
    'rsquared_adj': float(res.rsquared_adj),
    'f_pvalue': float(res.f_pvalue),
    'observations': int(res.nobs),
    'variables': {}
}

for var in res.params.index:
    regression_stats['variables'][var] = {
        'coefficient': float(res.params[var]),
        'std_error': float(res.bse[var]),
        't_stat': float(res.tvalues[var]),
        'p_value': float(res.pvalues[var]),
        'conf_int_lower': float(res.conf_int()[0][var]),
        'conf_int_upper': float(res.conf_int()[1][var])
    }

results['regression_analysis'] = regression_stats

print("3. Running NIFTY IT Regression Analysis...")
# New Regression: US Impact on NIFTY IT
y_it = returns['NIFTY_IT']
X_it = returns[['SP_500', 'NASDAQ_100', 'USD_INR', 'US_VIX']]
X_it = sm.add_constant(X_it)

model_it = sm.OLS(y_it, X_it).fit()

results['nifty_it_regression'] = {
    'rsquared': float(model_it.rsquared),
    'rsquared_adj': float(model_it.rsquared_adj),
    'f_pvalue': float(model_it.f_pvalue),
    'observations': int(model_it.nobs),
    'variables': {}
}

summary_table_it = model_it.summary2().tables[1]
for var_name, row in summary_table_it.iterrows():
    results['nifty_it_regression']['variables'][var_name] = {
        'coefficient': float(row['Coef.']),
        'std_error': float(row['Std.Err.']),
        't_stat': float(row['t']),
        'p_value': float(row['P>|t|']),
        'conf_int_lower': float(row['[0.025']),
        'conf_int_upper': float(row['0.975]'])
    }

# Save results
print("Saving Advanced Research results to JSON...")
with open(os.path.join(OUTPUT_DIR, 'advanced_research.json'), 'w') as f:
    json.dump(results, f, indent=4)

print("Stage 4 processing complete!")
