#!/bin/bash

# GitHub部署腳本
echo "🚀 Bybit套利系統 - GitHub部署腳本"
echo "=================================="

# 檢查是否已設置遠程倉庫
if git remote -v | grep -q origin; then
    echo "✅ 遠程倉庫已設置"
    git remote -v
else
    echo "❌ 請先設置遠程倉庫"
    echo ""
    echo "請按照以下步驟操作："
    echo "1. 訪問 https://github.com/new"
    echo "2. 創建新倉庫（建議名稱：bybit-arbitrage-system）"
    echo "3. 複製倉庫的HTTPS URL"
    echo "4. 運行以下命令："
    echo "   git remote add origin <您的倉庫URL>"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    echo ""
    echo "或者直接運行："
    echo "   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git"
    echo "   git push -u origin main"
    exit 1
fi

# 推送代碼
echo ""
echo "📤 推送代碼到GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 部署成功！"
    echo "🌐 您的倉庫地址："
    git remote get-url origin
    echo ""
    echo "📋 下一步："
    echo "1. 在GitHub上查看您的倉庫"
    echo "2. 設置環境變數（在倉庫設置中添加Secrets）"
    echo "3. 可以考慮部署到Streamlit Cloud"
else
    echo "❌ 推送失敗，請檢查網絡連接和權限"
fi
