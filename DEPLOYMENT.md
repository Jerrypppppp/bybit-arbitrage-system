# 🚀 部署指南

## GitHub部署

### 步驟1：創建GitHub倉庫

1. 訪問 [GitHub新建倉庫](https://github.com/new)
2. 倉庫設置：
   - **倉庫名稱**：`bybit-arbitrage-system`
   - **描述**：`Bybit funding rate arbitrage trading system`
   - **可見性**：建議設為私有（包含交易邏輯）
   - **不要**勾選"Add a README file"（我們已經有了）

### 步驟2：推送代碼

```bash
# 添加遠程倉庫（替換為您的實際URL）
git remote add origin https://github.com/YOUR_USERNAME/bybit-arbitrage-system.git

# 設置主分支
git branch -M main

# 推送代碼
git push -u origin main
```

### 步驟3：設置環境變數

在GitHub倉庫中設置Secrets：

1. 進入倉庫 → Settings → Secrets and variables → Actions
2. 添加以下Secrets：
   - `BYBIT_MAINNET_API_KEY`：您的Bybit API Key
   - `BYBIT_MAINNET_SECRET_KEY`：您的Bybit Secret Key
   - `USE_DEMO`：`true`（使用Demo模式）

## Streamlit Cloud部署

### 步驟1：連接GitHub

1. 訪問 [Streamlit Cloud](https://share.streamlit.io/)
2. 使用GitHub帳號登錄
3. 點擊"New app"

### 步驟2：配置應用

1. **Repository**：選擇您的GitHub倉庫
2. **Branch**：`main`
3. **Main file path**：`streamlit_app.py`
4. **App URL**：自定義URL（可選）

### 步驟3：設置環境變數

在Streamlit Cloud設置中添加：
- `BYBIT_MAINNET_API_KEY`
- `BYBIT_MAINNET_SECRET_KEY`
- `USE_DEMO=true`

## 本地部署

### 安裝依賴

```bash
pip install -r requirements.txt
```

### 設置環境變數

創建`.env`文件：
```env
BYBIT_MAINNET_API_KEY=your_api_key
BYBIT_MAINNET_SECRET_KEY=your_secret_key
USE_DEMO=true
```

### 運行應用

```bash
streamlit run streamlit_app.py --server.port 8501
```

## 安全注意事項

⚠️ **重要提醒**：
- 永遠不要在代碼中硬編碼API金鑰
- 使用環境變數或GitHub Secrets
- 建議先在Demo模式測試
- 定期輪換API金鑰
- 設置適當的API權限（只允許交易，不允許提現）

## 故障排除

### 常見問題

1. **API連接失敗**：
   - 檢查API金鑰是否正確
   - 確認網絡連接
   - 檢查API權限設置

2. **訂單失敗**：
   - 檢查賬戶餘額
   - 確認交易對是否可用
   - 檢查最小交易金額

3. **部署失敗**：
   - 檢查requirements.txt
   - 確認所有文件都已提交
   - 檢查環境變數設置

### 獲取幫助

如果遇到問題，請檢查：
1. GitHub Issues
2. Streamlit文檔
3. Bybit API文檔
