"""Drug ranking inference module.

Refactored from Stage 6 Cell 2 (predict_drug_ranking) of the original
mega-notebook into a clean, importable Python module.

This module provides the core inference logic used by both:
  - The interactive widget (notebooks/06_drug_ranking_widget.ipynb)
  - The PDF report generator (notebooks/07_pdf_report_generator.ipynb)

Usage
-----
>>> from src.drug_ranking import load_artifacts, predict_drug_ranking
>>> artifacts = load_artifacts(intermediates_dir='intermediates/')
>>> ranking = predict_drug_ranking('SIDM00083', artifacts, top_k=15)
>>> print(ranking.head())

Author: Chia-Ying Lin
License: MIT
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------

@dataclass
class Artifacts:
    """Bundle of all artifacts needed for inference.

    Attributes
    ----------
    X_joint : pd.DataFrame
        Joint feature matrix (16,137 cell-drug pairs × 4,165 features).
    drug_features : pd.DataFrame
        Drug-only feature matrix (229 drugs × 2,165 drug features), indexed by
        drug name.
    cell_metadata_lookup : dict[str, dict]
        Per-cell metadata: {SANGER_MODEL_ID: {CELL_LINE_NAME, CANCER_TYPE}}.
    cell_expression_lookup : dict[str, pd.Series]
        Per-cell expression vector (2,000-dim).
    drug_text_lookup : dict[str, dict]
        Per-drug target / pathway annotations.
    ensemble : list
        List of 5 trained XGBoost models from cell-blind CV.
    calibrator : object
        Fitted IsotonicRegression instance from Stage 4B.
    cell_feat_cols : list[str]
        Column names for the cell-feature block of X_joint.
    drug_feat_cols : list[str]
        Column names for the drug-feature block of X_joint.
    """
    X_joint: pd.DataFrame
    drug_features: pd.DataFrame
    cell_metadata_lookup: dict
    cell_expression_lookup: dict
    drug_text_lookup: dict
    ensemble: list
    calibrator: object
    cell_feat_cols: list
    drug_feat_cols: list


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_artifacts(intermediates_dir: str | Path = 'intermediates') -> Artifacts:
    """Load all artifacts from disk.

    Parameters
    ----------
    intermediates_dir : str or Path
        Directory containing the intermediate files. These files are not in
        git — download them from the GitHub Release or regenerate by running
        notebooks 01-05.

    Returns
    -------
    Artifacts
        Container with everything needed for inference.

    Raises
    ------
    FileNotFoundError
        If any required intermediate file is missing.
    """
    d = Path(intermediates_dir)
    if not d.exists():
        raise FileNotFoundError(
            f'Intermediates directory not found: {d}\n'
            f'Download from GitHub Release or run notebooks 01-05 to '
            f'regenerate.'
        )

    # Load core dataframes
    X_joint = pd.read_parquet(d / 'stage2b_X_joint.parquet')
    meta_joint = pd.read_parquet(d / 'stage2b_meta_joint.parquet')
    drug_features = pd.read_parquet(d / 'stage2b_drug_features.parquet')

    # Load metadata
    with open(d / 'stage2b_metadata.pkl', 'rb') as f:
        stage2b_meta = pickle.load(f)

    cell_feat_cols = stage2b_meta['cell_feature_cols']
    drug_feat_cols = stage2b_meta['drug_feature_cols']

    # Load ensemble + calibrator
    with open(d / 'stage6_ensemble_models.pkl', 'rb') as f:
        ensemble = pickle.load(f)
    calibrator = joblib.load(d / 'stage4b_calibrator.joblib')

    # Build per-cell lookups
    cell_metadata_lookup = {}
    for cell_id, group in meta_joint.groupby('SANGER_MODEL_ID'):
        cell_metadata_lookup[cell_id] = {
            'CELL_LINE_NAME': group['CELL_LINE_NAME'].iloc[0],
            'CANCER_TYPE': group['CANCER_TYPE'].iloc[0],
        }

    X_cell_only = X_joint[cell_feat_cols]
    cell_expression_lookup = {}
    for cell_id, group_idx in meta_joint.groupby('SANGER_MODEL_ID').groups.items():
        cell_expression_lookup[cell_id] = X_cell_only.iloc[group_idx[0]].copy()

    # Build drug text lookup from meta_joint
    drug_text_lookup = {}
    drug_text_cols = ['DRUG_NAME']
    if 'PUTATIVE_TARGET' in meta_joint.columns:
        drug_text_cols.append('PUTATIVE_TARGET')
    if 'PATHWAY_NAME' in meta_joint.columns:
        drug_text_cols.append('PATHWAY_NAME')

    drug_text_df = meta_joint[drug_text_cols].drop_duplicates(
        subset='DRUG_NAME'
    ).reset_index(drop=True)

    for _, r in drug_text_df.iterrows():
        drug_text_lookup[r['DRUG_NAME']] = {
            'target': r.get('PUTATIVE_TARGET', 'Unknown')
                      if pd.notna(r.get('PUTATIVE_TARGET', np.nan)) else 'Unknown',
            'pathway': r.get('PATHWAY_NAME', 'Unknown')
                       if pd.notna(r.get('PATHWAY_NAME', np.nan)) else 'Unknown',
        }

    return Artifacts(
        X_joint=X_joint,
        drug_features=drug_features,
        cell_metadata_lookup=cell_metadata_lookup,
        cell_expression_lookup=cell_expression_lookup,
        drug_text_lookup=drug_text_lookup,
        ensemble=ensemble,
        calibrator=calibrator,
        cell_feat_cols=cell_feat_cols,
        drug_feat_cols=drug_feat_cols,
    )


# ---------------------------------------------------------------------------
# Core inference
# ---------------------------------------------------------------------------

def predict_drug_ranking(
    cell_id: str,
    artifacts: Artifacts,
    top_k: Optional[int] = None,
    with_ci: bool = True,
    calibrate: bool = True,
) -> pd.DataFrame:
    """Predict drug sensitivity ranking for one cell line.

    Parameters
    ----------
    cell_id : str
        SANGER_MODEL_ID (e.g., 'SIDM00083' for SF539 glioblastoma).
    artifacts : Artifacts
        Loaded artifact bundle, from `load_artifacts()`.
    top_k : int or None
        Return only the top K drugs. None returns all 229 drugs.
    with_ci : bool
        If True, compute 95% bootstrap CI across the 5-fold ensemble.
    calibrate : bool
        If True, apply isotonic calibration to probabilities.

    Returns
    -------
    pd.DataFrame
        Columns: drug_name, P_sens, CI_lo, CI_hi, CI_width, target, pathway
        Sorted by P_sens descending.

    Raises
    ------
    ValueError
        If cell_id is not in the dataset.

    Examples
    --------
    >>> ranking = predict_drug_ranking(
    ...     'SIDM00083', artifacts, top_k=15, with_ci=True
    ... )
    >>> ranking[['drug_name', 'P_sens']].head()
    """
    if cell_id not in artifacts.cell_expression_lookup:
        raise ValueError(
            f'Cell {cell_id} not in dataset. '
            f'Available cells: {len(artifacts.cell_expression_lookup)}'
        )

    cell_expr = artifacts.cell_expression_lookup[cell_id]

    # Build X for this cell × all drugs
    drug_feat_arr = artifacts.drug_features.values
    drug_names_idx = artifacts.drug_features.index.tolist()
    cell_feat_arr = np.tile(cell_expr.values, (len(drug_feat_arr), 1))

    X_query = np.hstack([cell_feat_arr, drug_feat_arr]).astype(np.float32)
    X_query_df = pd.DataFrame(
        X_query, columns=artifacts.X_joint.columns, index=drug_names_idx
    )

    # Predict with ensemble
    probs_all = np.zeros((len(artifacts.ensemble), len(drug_names_idx)))
    for i, m in enumerate(artifacts.ensemble):
        probs_all[i] = m.predict_proba(X_query_df)[:, 1]

    # Aggregate
    prob_mean = probs_all.mean(axis=0)
    if with_ci:
        prob_lo = np.percentile(probs_all, 2.5, axis=0)
        prob_hi = np.percentile(probs_all, 97.5, axis=0)
    else:
        prob_lo = prob_mean
        prob_hi = prob_mean

    # Calibrate
    if calibrate:
        prob_mean = artifacts.calibrator.transform(prob_mean)
        prob_lo = artifacts.calibrator.transform(prob_lo)
        prob_hi = artifacts.calibrator.transform(prob_hi)

    # Build result
    result = pd.DataFrame({
        'drug_name': drug_names_idx,
        'P_sens': prob_mean,
        'CI_lo': prob_lo,
        'CI_hi': prob_hi,
        'CI_width': prob_hi - prob_lo,
    })

    # Add target / pathway annotations
    result['target'] = result['drug_name'].map(
        lambda d: artifacts.drug_text_lookup.get(d, {}).get('target', 'N/A')
    )
    result['pathway'] = result['drug_name'].map(
        lambda d: artifacts.drug_text_lookup.get(d, {}).get('pathway', 'N/A')
    )

    # Sort
    result = result.sort_values('P_sens', ascending=False).reset_index(drop=True)

    if top_k:
        result = result.head(top_k)

    return result


# ---------------------------------------------------------------------------
# Convenience utilities
# ---------------------------------------------------------------------------

def list_cells_by_cancer_type(artifacts: Artifacts) -> dict[str, list]:
    """Return a dict of {cancer_type: [(cell_id, cell_line_name), ...]}.

    Useful for building dropdowns / pickers.
    """
    cells_by_type: dict[str, list] = {}
    for cid, m in artifacts.cell_metadata_lookup.items():
        cells_by_type.setdefault(m['CANCER_TYPE'], []).append(
            (cid, m['CELL_LINE_NAME'])
        )
    return cells_by_type
