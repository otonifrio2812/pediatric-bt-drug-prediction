# Data Directory

這個資料夾用來放原始資料,但**檔案本身不會 commit 到 git**(見根目錄 `.gitignore`)。

原因:
1. GDSC2 / Cell Model Passports 有授權條款,不能直接重新散布
2. 檔案太大(> 100 MB),GitHub 不適合
3. 使用者自己下載最新版本最乾淨

---

## 📥 需要下載的檔案

### 1. GDSC2 — 藥物反應資料

從 https://www.cancerrxgene.org/downloads/bulk_download 下載:

| 檔案 | 用途 | 放到這裡 |
|------|------|----------|
| `GDSC2_fitted_dose_response_27Oct23.xlsx` | IC50、藥物 target、pathway | `data/raw/GDSC2/` |

> ⚠️ 不同版本的 GDSC2 結果略有差異,本研究使用 **27Oct23** 版本。

### 2. Cell Model Passports — RNA-seq

從 https://cellmodelpassports.sanger.ac.uk/downloads 下載:

| 檔案 | 用途 | 放到這裡 |
|------|------|----------|
| `rnaseq_tpm_*.csv` | 細胞 RNA-seq 表現量 | `data/raw/CellModelPassports/` |
| `model_list_*.csv` | Cell line metadata | `data/raw/CellModelPassports/` |

### 3. PubChem SMILES — 藥物分子結構

**不需要手動下載** — `notebooks/02_feature_engineering.ipynb` 會自動透過
`pubchempy` 套件查詢(需要網路)。

### 4. OpenPBTA(選用,只用於臨床情境說明)

從 https://github.com/AlexsLemonade/OpenPBTA-analysis 取得相關 metadata。

---

## 📂 期望的最終結構

```
data/
├── README.md                           ← 您現在看的這個
└── raw/                                ← 您下載到這裡(被 .gitignore 排除)
    ├── GDSC2/
    │   └── GDSC2_fitted_dose_response_27Oct23.xlsx
    └── CellModelPassports/
        ├── rnaseq_tpm_*.csv
        └── model_list_*.csv
```

---

## 🌐 在 Colab 上跑時

Colab 沒有本機資料,建議:

**方式 A — Google Drive(推薦)**
1. 把上述資料放入 Google Drive 的某個資料夾
2. 在 notebook 第一個 cell:
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   DATA_DIR = '/content/drive/MyDrive/YourFolder/'
   ```

**方式 B — 直接從 URL 下載到 Colab(資料無授權限制時)**
```python
!wget -O data/raw/GDSC2/GDSC2_fitted_dose_response_27Oct23.xlsx \
    https://cog.sanger.ac.uk/cancerrxgene/.../GDSC2_fitted_dose_response_27Oct23.xlsx
```

---

## ❓ 我下載不到原始資料怎麼辦?

如果您只是想試用 Widget 與 PDF 工具,**可以直接使用我們預訓練的模型**,不需要原始資料:

1. 到 GitHub Release 頁面下載 `intermediates.zip`(約 200 MB)
2. 解壓到 `intermediates/` 目錄
3. 跳過 notebooks 01-05,直接執行 06 或 07
