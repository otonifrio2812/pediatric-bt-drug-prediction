# Reproducibility Guide

完整的重現步驟,符合 TRIPOD-AI 與多數期刊(Bioinformatics, JAMIA 等)的開源科學要求。

---

## 🎯 三種重現等級

依您的需求選擇:

| 等級 | 您需要 | 大約時間 |
|------|--------|---------|
| **L1 — 試用工具** | 跑 Widget + 生成 PDF | 10 分鐘 |
| **L2 — 重現 Stage 6** | 使用我們訓練好的模型 | 30 分鐘 |
| **L3 — 完整重現論文** | 從原始資料訓練 | 4–8 小時 |

---

## L1 — 試用 Widget + PDF(最簡單)

不需要原始資料,只下載預訓練模型即可。

### 步驟

```bash
# 1. Clone repo
git clone https://github.com/otonifrio2812/pediatric-bt-drug-prediction.git
cd pediatric-bt-drug-prediction

# 2. 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 下載預訓練的 intermediates(從 GitHub Release)
mkdir intermediates
cd intermediates
wget https://github.com/otonifrio2812/pediatric-bt-drug-prediction/releases/download/v1.0.0/intermediates.zip
unzip intermediates.zip
cd ..

# 5. 啟動 Jupyter,執行 Widget notebook
jupyter notebook notebooks/06_drug_ranking_widget.ipynb
```

### 或是更快 — 直接 Colab

點 README 上方的 「Open Widget in Colab」 徽章即可。

---

## L2 — 重現 Stage 6(從中繼檔開始)

如果您想驗證 Stage 6 的工具邏輯但不重訓模型,從 `intermediates/` 開始即可:

```bash
# 跑 notebooks 06、07(其他略過)
jupyter notebook notebooks/06_drug_ranking_widget.ipynb
jupyter notebook notebooks/07_pdf_report_generator.ipynb
```

執行後預期結果:
- 對 SF539(SIDM00083)的 Top 15 推薦中應有 **≥ 10 個 PI3K/AKT/mTOR 抑制劑**
- 生成的 PDF 應為 2 頁 A4,大小約 30–60 KB

---

## L3 — 完整重現論文結果

從 GDSC2 原始資料開始,**完整重訓模型**。

### 前置:下載原始資料

詳見 [`data/README.md`](../data/README.md)。需要:
- `GDSC2_fitted_dose_response_27Oct23.xlsx`
- Cell Model Passports RNA-seq + metadata

### 執行順序

按 notebook 編號依序執行:

| Notebook | 內容 | 預計時間 | 主要輸出 |
|----------|------|---------|---------|
| `01_data_preparation.ipynb` | 資料載入 + GBM/Astrocytoma 關鍵字擴充 | 5 分 | `stage1_filtered.parquet` |
| `02_feature_engineering.ipynb` | RNA-seq + Morgan FP + Targets + Pathways | 30 分 | `stage2b_X_joint.parquet`(4,165 維) |
| `03_strict_cv_training.ipynb` | **核心**:4 CV × 多模型 | 30–40 分 | `stage3b_all_results.csv` |
| `04_calibration_dca.ipynb` | Isotonic calibration + DCA | 15 分 | `stage4b_calibrator.joblib` |
| `05_shap_analysis.ipynb` | SHAP 解釋 + 生物學驗證 | 20 分 | `stage5_feature_importance.csv` |
| `06_drug_ranking_widget.ipynb` | 訓練 5-fold ensemble + 互動 Widget | 15–25 分 | `stage6_ensemble_models.pkl` |
| `07_pdf_report_generator.ipynb` | PDF 報告 | < 1 分 | `results/reports/*.pdf` |

### 預期主要結果

執行 `notebooks/03_strict_cv_training.ipynb` 後,應在 results 表看到:

```
Strict CV (XGBoost):  AUROC = 0.686 ± 0.018 (95% CI: [0.668, 0.705])
```

**容忍範圍**:由於 random_state=42 已鎖定,結果應與此完全一致。如果出現
± 0.005 以上的差異,請檢查:
- Python 版本(建議 3.11)
- `numpy` 版本(本研究使用 1.24+)
- `xgboost` 版本(本研究使用 2.0+)

---

## 🔒 可重現性保證

| 項目 | 處理方式 |
|------|----------|
| Random seed | `random_state = 42` 鎖定於所有 model / CV / bootstrap |
| 套件版本 | `requirements.txt` 列出版本範圍 |
| 資料版本 | GDSC2 specifically `27Oct23` release |
| 預訓練模型 | GitHub Release v1.0.0(SHA256 hash 見 Release 說明) |
| CV 策略 | Strict CV(雙盲)pre-registered,程式碼可檢視 |
| 統計推論 | Bootstrap 95% CI,n_iter=1,000,固定 seed |

---

## 🐛 常見問題

### Q1:`pip install` 失敗

確認 Python ≥ 3.10:`python3 --version`。若版本過舊請先升級。

### Q2:`shap` import 報 NumPy 衝突

本研究使用 **NumPy 2.x 相容的 shap >= 0.45**。如遇到衝突:
```bash
pip install --upgrade shap
```
**不要降 numpy**——降版會破壞其他套件。

### Q3:Colab 跑到一半 session 斷線

Colab 免費版 session 有時間限制。建議:
- 開 Colab Pro(您已訂閱)
- 中繼檔存到 Google Drive,可以分段執行

### Q4:本機跑很慢

最慢的兩個 cell:
- `03_strict_cv_training.ipynb` Cell 3(4 CV × 3 models = 30–40 分)
- `06_drug_ranking_widget.ipynb` 訓練 ensemble(15–25 分)

如果只想看結果,直接從 GitHub Release 抓 `intermediates.zip` 跳過訓練。

### Q5:我修改了程式碼,結果不一樣

正常 — 那是您的修改造成的。要嚴格重現論文結果,請使用 `git checkout v1.0.0`
回到發布版本。

---

## 📊 與 SOTA 比較

| 模型 | 報告 AUROC | 我們 Strict CV AUROC |
|------|-----------|-----------------------|
| MOLI(2019) | 0.62–0.74 | — |
| DeepCDR(2020) | 0.68–0.82 | — |
| **本研究** | — | **0.686 [0.668, 0.705]** |

**重要差異**:多數已發表模型使用 Random CV(會有 cell leakage),我們報告
的是最嚴苛的 Strict CV(雙盲)。這就是為什麼我們的數字看起來「沒比較高」,
但其實是 **更誠實** 的數字。

---

## 📜 引用

如本 repo 對您有用,請引用:

```bibtex
@misc{lin2026pediatric,
  author = {Lin, Chia-Ying and Tung, Chun-Wei},
  title = {Pediatric High-Grade Glioma Drug Sensitivity Prediction},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/otonifrio2812/pediatric-bt-drug-prediction}
}
```
