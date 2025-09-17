#!/bin/bash

# 快速同步到GitHub腳本
echo "🔄 同步代碼到GitHub..."

# 檢查是否有修改
if git diff --quiet && git diff --cached --quiet; then
    echo "✅ 沒有修改需要同步"
    exit 0
fi

# 顯示修改狀態
echo "📋 修改狀態："
git status --short

# 添加所有修改
echo "📤 添加修改..."
git add .

# 提交修改
echo "💾 提交修改..."
read -p "請輸入提交信息: " commit_message
git commit -m "$commit_message"

# 推送到GitHub
echo "🚀 推送到GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ 同步成功！"
    echo "🌐 GitHub倉庫: https://github.com/Jerrypppppp/bybit-arbitrage-system"
    echo "⏰ Streamlit Cloud將在幾分鐘內自動更新"
else
    echo "❌ 推送失敗，請檢查網絡連接"
fi
