"""PDF clinical report generator.

Refactored from Stage 6 Cell 9 (generate_clinical_report) of the original
mega-notebook into a clean, importable Python module.

Generates a 2-page A4 PDF report suitable for printing and bringing to a
Molecular Tumor Board (MTB) discussion.

Usage
-----
>>> from src.drug_ranking import load_artifacts
>>> from src.pdf_report import generate_clinical_report
>>> artifacts = load_artifacts()
>>> path = generate_clinical_report(
...     cell_id='SIDM00083',
...     artifacts=artifacts,
...     top_k=15,
...     output_path='SF539_report.pdf',
... )

Author: Chia-Ying Lin
License: MIT
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .drug_ranking import Artifacts, predict_drug_ranking


# ---------------------------------------------------------------------------
# Performance metrics (from the published research — update if model retrained)
# ---------------------------------------------------------------------------

MODEL_PERFORMANCE = {
    'overall_auroc': '0.686 [0.668, 0.705] (n=3,217)',
    'glioblastoma_auroc': '0.657 (n=7,325)',
    'glioma_auroc': '0.696 (n=2,680)',
    'neuroblastoma_auroc': '0.646 (n=6,132)',
    'sota_range': 'MOLI: 0.62–0.74; DeepCDR: 0.68–0.82',
    'model_version': 'Stage 3B XGBoost + Stage 4B Isotonic Calibration',
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_clinical_report(
    cell_id: str,
    artifacts: Artifacts,
    top_k: int = 15,
    output_path: Optional[str | Path] = None,
) -> Path:
    """Generate a 2-page A4 PDF clinical report.

    Parameters
    ----------
    cell_id : str
        SANGER_MODEL_ID (e.g., 'SIDM00083' for SF539).
    artifacts : Artifacts
        Loaded artifact bundle, from `load_artifacts()`.
    top_k : int
        Number of top drugs to include in the report (default 15).
    output_path : str, Path, or None
        Output PDF path. If None, defaults to
        `report_{cell_id}_{cell_name}.pdf` in current directory.

    Returns
    -------
    Path
        Absolute path to the generated PDF.

    Notes
    -----
    The report includes:
      - Cell line metadata (ID, name, cancer type)
      - Top K drug recommendations with calibrated P(sensitive) and 95% CI
      - Drug target and pathway annotations
      - Research Use Only disclaimer (red, prominent)
      - Result interpretation guidance
      - Model limitations transparency
    """
    meta = artifacts.cell_metadata_lookup[cell_id]
    cell_name = meta['CELL_LINE_NAME']
    cancer = meta['CANCER_TYPE']

    if output_path is None:
        safe_name = cell_name.replace('/', '_').replace(' ', '_')
        output_path = Path(f'report_{cell_id}_{safe_name}.pdf')
    else:
        output_path = Path(output_path)

    # Run inference
    ranking = predict_drug_ranking(
        cell_id, artifacts, top_k=top_k, with_ci=True, calibrate=True
    )

    # Build PDF
    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    elements = []

    # === Title ===
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=18, textColor=colors.HexColor('#1f77b4'),
        alignment=TA_CENTER, spaceAfter=12,
    )
    elements.append(Paragraph(
        'Pediatric Brain Tumor Drug Sensitivity Report', title_style
    ))
    elements.append(Paragraph(
        '<b>Predictive AI Analysis (Research Use Only)</b>',
        ParagraphStyle(
            'subtitle', parent=styles['Normal'],
            alignment=TA_CENTER, fontSize=11,
            textColor=colors.grey, spaceAfter=20,
        ),
    ))

    # === Patient info table ===
    info_data = [
        ['Cell Line ID:', cell_id],
        ['Cell Line Name:', cell_name],
        ['Cancer Type:', cancer],
        ['Report Generated:', time.strftime('%Y-%m-%d %H:%M')],
        ['Model Version:', MODEL_PERFORMANCE['model_version']],
        ['Strict CV AUROC:', MODEL_PERFORMANCE['overall_auroc']],
    ]
    info_table = Table(info_data, colWidths=[5*cm, 11*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f0fe')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.6*cm))

    # === Disclaimer ===
    disclaimer_style = ParagraphStyle(
        'disclaimer', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#cc4444'),
        spaceAfter=12, leftIndent=10, rightIndent=10,
    )
    elements.append(Paragraph(
        '<b>⚠️ DISCLAIMER:</b> This report is generated by an AI research '
        'model trained on GDSC2 cell-line data. Predictions are <b>NOT</b> '
        'a substitute for clinical judgment. All treatment decisions must be '
        'made by qualified physicians considering individual patient factors. '
        'The model has not been validated for clinical use.',
        disclaimer_style,
    ))
    elements.append(Spacer(1, 0.4*cm))

    # === Top recommendations table ===
    elements.append(Paragraph(
        f'<b>Top {top_k} Drug Recommendations</b>',
        ParagraphStyle(
            'h2', parent=styles['Heading2'], fontSize=12, spaceAfter=8
        ),
    ))

    table_data = [['#', 'Drug', 'P(sens)', '95% CI', 'Target', 'Pathway']]
    for i, (_, row) in enumerate(ranking.iterrows()):
        p_str = f'{row["P_sens"]:.2f}'
        ci_str = f'[{row["CI_lo"]:.2f}, {row["CI_hi"]:.2f}]'
        tgt = str(row['target'])
        tgt = tgt[:18] if len(tgt) > 18 else tgt
        pw = str(row['pathway'])
        pw = pw[:18] if len(pw) > 18 else pw
        table_data.append([
            str(i + 1),
            row['drug_name'][:20],
            p_str, ci_str, tgt, pw,
        ])

    rank_table = Table(
        table_data,
        colWidths=[0.8*cm, 3.5*cm, 1.6*cm, 2.5*cm, 3.5*cm, 4.1*cm],
    )
    rank_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    elements.append(rank_table)
    elements.append(Spacer(1, 0.4*cm))

    # === Page 2: Interpretation ===
    elements.append(PageBreak())
    elements.append(Paragraph(
        '<b>How to Interpret These Predictions</b>',
        ParagraphStyle(
            'h2', parent=styles['Heading2'], fontSize=12, spaceAfter=8
        ),
    ))

    guidance_text = f'''
    <para><b>P(sensitive)</b>: Probability that the cell line will respond
    to the drug (range 0–1). Higher = more likely to be sensitive.
    A threshold of 0.5 separates predicted sensitive vs. resistant.</para>

    <para><b>95% Confidence Interval</b>: Reflects model uncertainty across
    5 cross-validation folds. Wider CIs indicate less reliable predictions.</para>

    <para><b>Target &amp; Pathway</b>: From the GDSC2 drug annotation. Helps
    identify whether top recommendations cluster by molecular mechanism.</para>

    <para><b>Model performance summary</b> (strict cross-validation,
    new patients × new drugs):</para>
    <para>• Overall AUROC: {MODEL_PERFORMANCE["overall_auroc"]}</para>
    <para>• Glioblastoma: {MODEL_PERFORMANCE["glioblastoma_auroc"]}</para>
    <para>• Glioma: {MODEL_PERFORMANCE["glioma_auroc"]}</para>
    <para>• Neuroblastoma: {MODEL_PERFORMANCE["neuroblastoma_auroc"]}</para>

    <para>These match SOTA models in published literature
    ({MODEL_PERFORMANCE["sota_range"]}).</para>

    <para><b>Important caveats</b>:</para>
    <para>• Trained on GDSC2 cell-line data, not patient tumors.</para>
    <para>• Per-drug confidence intervals can be wide for less-tested drugs.</para>
    <para>• Predictions do NOT account for: drug-drug interactions,
    pharmacokinetics, patient-specific genetic background, comorbidities,
    or clinical contraindications.</para>
    '''
    elements.append(Paragraph(guidance_text, styles['Normal']))
    elements.append(Spacer(1, 0.6*cm))

    # === Footer ===
    footer_style = ParagraphStyle(
        'footer', parent=styles['Normal'],
        fontSize=7, textColor=colors.grey, alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        'Pediatric HGG Drug Sensitivity Prediction Model — '
        'Research Use Only — Page 2 of 2',
        footer_style,
    ))

    # Build it
    doc.build(elements)
    return output_path.resolve()
