"""
Bipolar to Monopolar LFP Power Estimation Companion
---------------------------------------------------
This notebook provides an interactive interface to help
you estimate Monopolar LFP Powers from Bipolar LFP Power
using the weights and model described in Fleeting et al.,
2025.

Input type: CSV
    >> Must contain ['C0-C3', 'C1-C2', and 'C2-C3'] in dB PSD (labeled at head of each column)
    >> If it contains ['C0', 'C1', 'C2' and 'C3'], it will also run validation.

Output type: CSV
    >> Saved locally to input file with suffix "_estimated"
    >> Conservative format. 
        >> Removed ['C0-C3', 'C1-C2', and 'C2-C3']
        >> Added ['C0', 'C1', 'C2' and 'C3']
        >> Added ['C0_SE', 'C1_SE', 'C2_SE' and 'C3_SE']

Author: Chance Fleeting


Example Workflow
----------------
A clinician or researcher performing postoperative LFP analysis could
apply the model as follows:

    1. Record or export bipolar PSD measurements from the sensing-enabled
       DBS system (e.g., BrainSense survey output).

    2. Extract bipolar powers in dB for:
            ['C0-C3', 'C1-C2', 'C2-C3']

       using the desired frequency band or spectral metric.

    3. Save these values in CSV format with the required column names.

    4. Run this script to estimate monopolar contact powers:
            ['C0', 'C1', 'C2', 'C3']

    5. Review the estimated monopolar distribution as if monopolar
       powers had been recorded directly.

No additional preprocessing is required prior to model application.
Because the model operates linearly in relative dB space, scaling or
band-selection choices applied to the bipolar inputs translate directly
to the monopolar estimates. Similarly, because the model was trained
across canonical frequency bands, it is agnostic to the specific band
power extraction method used, provided the inputs are expressed as PSD
power in dB.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path
from scipy.stats import norm
import matplotlib.pyplot as plt

## Coefficients from Fleeting et al. 2025
coef = pd.DataFrame({
    'C0': [3.931926, 0.737293,  0.076522, 0.101754],
    'C1': [4.738096, 0.410390,  0.393244, 0.125366],
    'C2': [4.953907, 0.284265,  0.157266, 0.488739],
    'C3': [3.844596, 0.564074, -0.043996, 0.409325],
    }, index=['const', 'C0-C3', 'C1-C2', 'C2-C3']) # <-------- Please Label 'C0-C3', 'C1-C2', and 'C2-C3' in your CSV

coef_cov = pd.DataFrame({
    'C0':[pd.DataFrame({
        'const': [ 4.15542477e-04, -5.07329624e-04, -2.91715631e-05,  5.56618849e-04],
        'C0-C3': [-5.07329624e-04,  1.99340800e-03, -1.45554879e-03, -3.50993309e-04],
        'C1-C2': [-2.91715631e-05, -1.45554879e-03,  2.17865725e-03, -9.18408054e-04],
        'C2-C3': [ 5.56618849e-04, -3.50993309e-04, -9.18408054e-04,  1.50124537e-03]
        }, index=['const', 'C0-C3', 'C1-C2', 'C2-C3'])],
    'C1':[pd.DataFrame({
        'const': [ 0.00041828, -0.00067915,  0.00018877,  0.0005084],
        'C0-C3': [-0.00067915,  0.00309587, -0.00265617, -0.00033659],
        'C1-C2': [ 0.00018877, -0.00265617,  0.00380632, -0.0012142],
        'C2-C3': [ 0.0005084,  -0.00033659, -0.0012142,   0.00172875]
        }, index=['const', 'C0-C3', 'C1-C2', 'C2-C3'])],
    'C2':[pd.DataFrame({
        'const': [ 0.00035501, -0.0003559,  -0.0001556,   0.00050323],
        'C0-C3': [-0.0003559,   0.00200934, -0.00118672, -0.00053107],
        'C1-C2': [-0.0001556,  -0.00118672,  0.00212619, -0.00114476],
        'C2-C3': [ 0.00050323, -0.00053107, -0.00114476,  0.00186151]
        }, index=['const', 'C0-C3', 'C1-C2', 'C2-C3'])],
    'C3':[pd.DataFrame({
        'const': [ 0.00049102, -0.00087397,  0.00023486,  0.00062031],
        'C0-C3': [-0.00087397,  0.00352449, -0.00227479, -0.00108152],
        'C1-C2': [ 0.00023486, -0.00227479,  0.00319753, -0.00097603],
        'C2-C3': [ 0.00062031, -0.00108152, -0.00097603,  0.00219852]
        }, index=['const', 'C0-C3', 'C1-C2', 'C2-C3'])]
    }) # I like that the labels propagate with Dataframes. Fit uncertainty

mse = pd.DataFrame({'C0':[3.2663031786532475], 
                    'C1':[3.280076521374565], 
                    'C2':[3.58149570047011], 
                    'C3':[3.7034584336408143]})**2 # system uncertainty

iv = list(coef.index)[1:]    # ['C0-C3', 'C1-C2', 'C2-C3']
dv = list(coef.columns)  # ['C0','C1','C2','C3']

def EstimateMonopolar(df):
  df = pd.DataFrame([df])
  for col in df.columns:
     df[col] = 10*np.log10(df[col]) # Convert to dB

  assert all(v in df.columns for v in iv), f"Missing columns: {set(iv) - set(df.columns)}" 
  df_remainder = df[[c for c in df.columns if c not in iv + dv]]

  # COMPUTATION Phase
  x = sm.add_constant(df[iv], has_constant='add')
  df_estimated = x @ coef
  df_SE = pd.DataFrame({v:[np.sqrt(np.diag(x @ coef_cov[v][0] @ x.T) + mse[v][0])] for v in dv}) #Standard model error (propagated) ignoring lagged component.

  # SAVE Phase
  for k,v in df_SE.items():
      df_estimated[k+'_SE'] = v[0]
  return pd.concat([df_remainder,df_estimated], axis = 1)