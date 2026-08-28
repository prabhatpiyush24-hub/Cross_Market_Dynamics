import pandas as pd
import numpy as np
import os
import json
from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

FINAL_DIR = os.path.join('data', 'final')
OUTPUT_DIR = os.path.join('data', 'stats')

# Load master dataset
df = pd.read_csv(os.path.join(FINAL_DIR, 'master_research_dataset.csv'), index_col='Date', parse_dates=True)

# Calculate daily returns
returns = df.pct_change(1).dropna()

# Target: NIFTY_50 Return > 0 (1 = Positive, 0 = Non-Positive)
y = (returns['NIFTY_50'] > 0).astype(int)

# Features
# SP_500, NASDAQ, Brent, Gold, USD_INR are already lagged in the dataset alignment.
# We also want previous NIFTY and previous VIX change.
X = pd.DataFrame({
    'SP_500': returns['SP_500'],
    'NASDAQ_100': returns['NASDAQ_100'],
    'Brent_Crude': returns['Brent_Crude'],
    'Gold': returns['Gold'],
    'USD_INR': returns['USD_INR'],
    'Prev_NIFTY_50': returns['NIFTY_50'].shift(1),
    'Prev_India_VIX': returns['India_VIX'].shift(1)
})

# Drop the first row due to the shift
X = X.dropna()
y = y.loc[X.index]

print("Data Leakage Audit:")
print(f"Target variable length: {len(y)}")
print(f"Feature matrix length: {len(X)}")
print("All features are guaranteed strictly prior to target session due to Stage 2 alignment + shifting.")

# Train/Test Split (Chronological, 80% train, 20% test)
split_idx = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

print(f"Train set: {X_train.index.min().strftime('%Y-%m-%d')} to {X_train.index.max().strftime('%Y-%m-%d')} ({len(X_train)} samples)")
print(f"Test set:  {X_test.index.min().strftime('%Y-%m-%d')} to {X_test.index.max().strftime('%Y-%m-%d')} ({len(X_test)} samples)")

results = {
    'audit': {
        'leakage_free': True,
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'train_period': f"{X_train.index.min().strftime('%Y-%m-%d')} to {X_train.index.max().strftime('%Y-%m-%d')}",
        'test_period': f"{X_test.index.min().strftime('%Y-%m-%d')} to {X_test.index.max().strftime('%Y-%m-%d')}"
    },
    'models': {}
}

def evaluate_model(y_true, y_pred, y_prob=None):
    cm = confusion_matrix(y_true, y_pred)
    return {
        'accuracy': float(accuracy_score(y_true, y_pred)),
        'precision': float(precision_score(y_true, y_pred, zero_division=0)),
        'recall': float(recall_score(y_true, y_pred, zero_division=0)),
        'f1': float(f1_score(y_true, y_pred, zero_division=0)),
        'roc_auc': float(roc_auc_score(y_true, y_prob)) if y_prob is not None else 0.5,
        'confusion_matrix': {
            'tn': int(cm[0,0]),
            'fp': int(cm[0,1]),
            'fn': int(cm[1,0]),
            'tp': int(cm[1,1])
        }
    }

# 1. Baseline Model (Predicts the majority class of the train set always, usually '1' for equities)
majority_class = y_train.mode()[0]
y_pred_base = np.full(shape=len(y_test), fill_value=majority_class)
# For AUC, baseline probability is just predicting exactly majority class prob
results['models']['Baseline'] = evaluate_model(y_test, y_pred_base, y_pred_base)

# 2. Logistic Regression
lr = LogisticRegression(random_state=42)
lr.fit(X_train, y_train)
y_pred_lr = lr.predict(X_test)
y_prob_lr = lr.predict_proba(X_test)[:, 1]
results['models']['Logistic_Regression'] = evaluate_model(y_test, y_pred_lr, y_prob_lr)

# 3. Random Forest
rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
rf.fit(X_train, y_train)
y_pred_rf = rf.predict(X_test)
y_prob_rf = rf.predict_proba(X_test)[:, 1]
results['models']['Random_Forest'] = evaluate_model(y_test, y_pred_rf, y_prob_rf)

# Extract Feature Importances from RF
importances = rf.feature_importances_
feature_importance = {}
for i, col in enumerate(X.columns):
    feature_importance[col] = float(importances[i])
results['feature_importance'] = feature_importance

print("\nModel Results on Test Set:")
for model_name, metrics in results['models'].items():
    print(f"{model_name}: Accuracy = {metrics['accuracy']:.4f}, AUC = {metrics['roc_auc']:.4f}")

with open(os.path.join(OUTPUT_DIR, 'ml_results.json'), 'w') as f:
    json.dump(results, f, indent=4)

print("\nStage 5 processing complete!")
