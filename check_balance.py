#!/usr/bin/env python3
"""
檢查賬戶餘額
"""
from bybit_client import BybitClient

def check_balance():
    """檢查賬戶餘額"""
    # 使用您的API金鑰
    api_key = "t50HiMBxhU7s8Tx5Es"
    secret_key = "UwsGcbFvsqpLTc1rSHlaQ54RWOLHTD7YE8qm"
    
    # 創建客戶端
    client = BybitClient(api_key, secret_key, testnet=False, demo=True)
    
    print("💰 檢查賬戶餘額...")
    
    # 獲取賬戶餘額
    result = client.get_account_balance()
    
    if result.get("retCode") == 0:
        print("✅ 賬戶餘額獲取成功")
        
        for account in result.get("result", {}).get("list", []):
            print(f"\n📊 賬戶類型: {account.get('accountType')}")
            
            for coin in account.get("coin", []):
                coin_name = coin.get("coin")
                balance = float(coin.get("walletBalance", 0))
                
                if balance > 0:
                    print(f"  {coin_name}: {balance:.6f}")
    else:
        print(f"❌ 獲取賬戶餘額失敗: {result.get('retMsg')}")
    
    print("\n🔍 檢查持倉...")
    
    # 獲取現貨持倉
    spot_result = client.get_positions(category="spot")
    if spot_result.get("retCode") == 0:
        print("✅ 現貨持倉:")
        for position in spot_result.get("result", {}).get("list", []):
            symbol = position.get("symbol")
            size = float(position.get("size", 0))
            if size > 0:
                print(f"  {symbol}: {size:.6f}")
    
    # 獲取合約持倉
    linear_result = client.get_positions(category="linear")
    if linear_result.get("retCode") == 0:
        print("✅ 合約持倉:")
        for position in linear_result.get("result", {}).get("list", []):
            symbol = position.get("symbol")
            size = float(position.get("size", 0))
            side = position.get("side")
            if size > 0:
                print(f"  {symbol}: {size:.6f} ({side})")

if __name__ == "__main__":
    check_balance()
