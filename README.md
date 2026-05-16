# Pediatric High-Grade Glioma Drug Sensitivity Prediction

> 兒童高惡性度腦瘤藥物敏感性預測 — Cell-Drug 聯合特徵架構與嚴格交叉驗證

[![Open Widget in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/otonifrio2812/pediatric-bt-drug-prediction/blob/main/notebooks/06_drug_ranking_widget.ipynb)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> ✅ **帳號已替換完成**:本 repo 對應 `otonifrio2812/pediatric-bt-drug-prediction`

---

## 🎯 一句話總結

在最嚴苛的 Strict CV(同時新細胞 × 新藥)下達 **AUROC 0.686 [0.668, 0.705]**,
進入 SOTA 區間(MOLI: 0.62–0.74, DeepCDR: 0.68–0.82),並提供互動式藥物推薦
Widget 與 PDF 臨床報告生成工具。

---

## 🚀 三種使用方式(依您的需求挑一個)

### 方式 1:最快 — 直接在 Colab 玩 Widget(不用裝任何東西)

點上方 **「Open in Colab」** 徽章 → 一鍵開啟互動 Widget。
適合:想試用、看 demo、教學展示。

### 方式 2:在本機重現分析(完整重現論文結果)

```bash
# 1. clone repo
git clone https://github.com/otonifrio2812/pediatric-bt-drug-prediction.git
cd pediatric-bt-drug-prediction

# 2. 建虛擬環境(推薦)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. 安裝套件
pip install -r requirements.txt

# 4. 下載原始資料(GDSC2 + Cell Model Passports)
#    詳見 data/README.md
```

### 方式 3:只想用工具(不想重訓模型)

下載我們預訓練的模型(GitHub Release):

```bash
# 從 GitHub Release 抓 trained models + intermediate files
# 詳見 INTERMEDIATES.md(預訓練模型約 200 MB)
```

---

## 📁 Repository 結構

```
pediatric-bt-drug-prediction/
├── README.md                     ← 您現在看的這個
├── LICENSE                       ← MIT 授權
├── CITATION.cff                  ← 引用方式
├── requirements.txt              ← Python 套件清單(鎖定版本)
├── .gitignore                    ← 不上傳 git 的檔案規則
│
├── data/
│   └── README.md                 ← 如何下載 GDSC2 / Cell Model Passports
│
├── notebooks/                    ← 完整分析流程(依執行順序編號)
│   ├── 01_data_preparation.ipynb        ← 資料載入 + GBM/Astrocytoma 關鍵字擴充
│   ├── 02_feature_engineering.ipynb     ← Cell-drug 聯合特徵(4,165 維)
│   ├── 03_strict_cv_training.ipynb      ← 4 種 CV × 多模型(主結果)
│   ├── 04_calibration_dca.ipynb         ← Isotonic + Decision Curve
│   ├── 05_shap_analysis.ipynb           ← SHAP + 生物學驗證
│   ├── 06_drug_ranking_widget.ipynb     ⭐ 互動式 Widget Demo
│   └── 07_pdf_report_generator.ipynb    ⭐ PDF 臨床報告
│
├── src/                          ← 可被 import 的 Python 模組
│   ├── drug_ranking.py           ← predict_drug_ranking() 核心函數
│   └── pdf_report.py             ← generate_clinical_report() PDF 生成器
│
├── results/                      ← 分析輸出(圖、表)
│   ├── figures/
│   └── tables/
│
└── docs/
    └── REPRODUCIBILITY.md        ← 詳細重現步驟
```

---

## ⭐ 互動 Widget Demo(Tool A)

最簡單的玩法 — Colab 一鍵啟動:

1. 點頁面最上方的 **「Open Widget in Colab」** 徽章
2. 依序執行所有 cells(`Runtime → Run all`)
3. 出現滑桿與下拉選單後,選 cancer + cell → **即時** 顯示 Top K 推薦藥物

或在本機 Jupyter:

```bash
jupyter notebook notebooks/06_drug_ranking_widget.ipynb
```

**功能**:
- 28 種癌種下拉選單(Glioblastoma / Glioma / Neuroblastoma 為主)
- 81 株細胞快速切換
- Top 5–30 藥物滑桿
- 每個推薦顯示:`P(sensitive)`、95% CI、Target、Pathway

---

## 📄 PDF 臨床報告生成器(Tool C)

執行 `notebooks/07_pdf_report_generator.ipynb`,或直接在 Python 裡:

```python
from src.drug_ranking import predict_drug_ranking, load_artifacts
from src.pdf_report import generate_clinical_report

artifacts = load_artifacts()
generate_clinical_report(
    cell_id='SIDM00083',
    top_k=15,
    output_path='SF539_report.pdf',
    artifacts=artifacts,
)
```

**輸出 PDF 包含**:
- Cell line 資訊(ID, name, cancer type)
- Top 15 推薦藥物表(藥名、機率、95% CI、Target、Pathway)
- 「Research Use Only」紅字免責聲明
- 結果判讀指引 + 模型限制揭露
- 適合列印帶入分子腫瘤委員會(MTB)討論

---

## 📊 主要結果

| 驗證方式 | AUROC | 95% CI |
|---------|-------|--------|
| Random 5-fold | 0.786 | [0.778, 0.793] |
| Drug-blind | 0.781 | [0.764, 0.798] |
| Cell-blind | 0.700 | [0.693, 0.709] |
| **★ Strict CV(primary endpoint)** | **0.686** | **[0.668, 0.705]** |

| 癌種(Cell-blind) | AUROC | 95% CI | n_test |
|------------------|-------|--------|--------|
| Glioma | 0.696 | [0.675, 0.717] | 2,680 |
| Glioblastoma | 0.657 | [0.645, 0.669] | 7,325 |
| Neuroblastoma | 0.646 | [0.631, 0.660] | 6,132 |

---

## 🔬 資料來源

- **GDSC2**(Genomics of Drug Sensitivity in Cancer):藥物反應 IC50
  - 來源:https://www.cancerrxgene.org/downloads
  - 版本:`GDSC2_fitted_dose_response_27Oct23.xlsx`
- **Cell Model Passports**:RNA-seq 與 cell line metadata
  - 來源:https://cellmodelpassports.sanger.ac.uk/downloads
- **PubChem**:SMILES → Morgan Fingerprint
- **OpenPBTA**:臨床情境參考

詳見 [`data/README.md`](data/README.md)。

---

## 📖 引用 Citation

如本研究對您的工作有幫助,請引用:

```bibtex
@misc{lin2026pediatric,
  author       = {Lin, Chia-Ying and Tung, Chun-Wei},
  title        = {Pediatric High-Grade Glioma Drug Sensitivity Prediction},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/otonifrio2812/pediatric-bt-drug-prediction},
}
```

詳見 [`CITATION.cff`](CITATION.cff)。

---

## 🤖 AI 揭露(遵循 TRIPOD-AI 與 ICMJE 規範)

本研究運用 Anthropic Claude AI 協助:程式碼編寫、統計分析腳本生成、
圖表繪製、Manuscript 草稿撰寫。第一作者已驗證所有 AI 產出,並對結果
完整性與準確性負完全責任。

---

## 🙏 致謝

- 指導教授:Chun-Wei Tung, PhD(NHRI 國家衛生研究院 生技與藥物研究所)
- 開源資料社群:GDSC2、Cell Model Passports、OpenPBTA、PubChem、RDKit
- 特別致謝童年治癒我急性淋巴性白血病的兒癌主治醫師。
  「他給了我第二次生命,而我希望這份研究,是我回饋給兒癌領域的一點微薄貢獻。」

---

## 📄 授權 License

MIT License — 見 [LICENSE](LICENSE)。

歡迎 fork、修改、商業使用,但需保留 copyright notice。
