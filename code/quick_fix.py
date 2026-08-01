#!/usr/bin/env python3
"""
Quick fix for critical issues in output.csv
"""

import pandas as pd

print("="*70)
print("QUICK FIX: message_type + evidence_message_ids")
print("="*70)

# Load output
df = pd.read_csv('output.csv')
print(f"\nLoaded {len(df)} predictions")

# Fix message_type: update -> business_update, promotional -> promotion
fixed_types = 0
for idx in range(len(df)):
    old_type = df.at[idx, 'message_type']

    if old_type == 'update':
        df.at[idx, 'message_type'] = 'business_update'
        fixed_types += 1
    elif old_type == 'promotional':
        df.at[idx, 'message_type'] = 'promotion'
        fixed_types += 1

print(f"\nFixed {fixed_types} invalid message_type values")

# Fix evidence_message_ids: replace 'ml_features' with 'none' for now
fixed_evidence = 0
for idx in range(len(df)):
    if df.at[idx, 'evidence_message_ids'] == 'ml_features':
        df.at[idx, 'evidence_message_ids'] = 'none'
        fixed_evidence += 1

print(f"Fixed {fixed_evidence} placeholder evidence values")

# Save
df.to_csv('output_fixed.csv', index=False)
print(f"\nSaved to: output_fixed.csv")

# Verify
print("\n" + "="*70)
print("VERIFICATION")
print("="*70)

# Check message_type
invalid_types = df[df['message_type'].isin(['update', 'promotional'])]
print(f"\nInvalid message_types remaining: {len(invalid_types)}")

# Check evidence
ml_features = df[df['evidence_message_ids'] == 'ml_features']
print(f"ml_features evidence remaining: {len(ml_features)}")

# Show distribution
print("\nMessage type distribution:")
print(df['message_type'].value_counts())

print("\n[SUCCESS] Quick fixes applied!")
