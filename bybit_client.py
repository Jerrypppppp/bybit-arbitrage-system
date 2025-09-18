"""
Bybit API 客戶端
支援測試網和主網
"""
import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode
from typing import Dict, List, Optional, Tuple
import json

class BybitClient:
    def __init__(self, api_key: str, secret_key: str, testnet: bool = True, demo: bool = False):
        self.api_key = api_key
        self.secret_key = secret_key
        if demo:
            self.base_url = "https://api-demo.bybit.com"  # 模擬交易域名
        else:
            self.base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        self.testnet = testnet
        self.demo = demo
        
    def _generate_signature(self, params: str, timestamp: str) -> str:
        """生成API簽名"""
        param_str = f"{timestamp}{self.api_key}{5000}{params}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """發送API請求"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-BAPI-API-KEY': self.api_key,
        }
        
        if signed:
            timestamp = str(int(time.time() * 1000))
            if method.upper() == 'GET':
                # GET 請求使用 URL 編碼參數
                if params:
                    query_string = urlencode(params)
                else:
                    query_string = ""
            else:
                # POST 請求使用 URL 編碼參數
                if params:
                    query_string = urlencode(params)
                else:
                    query_string = ""
            
            signature = self._generate_signature(query_string, timestamp)
            headers.update({
                'X-BAPI-SIGN': signature,
                'X-BAPI-SIGN-TYPE': '2',
                'X-BAPI-TIMESTAMP': timestamp,
                'X-BAPI-RECV-WINDOW': '5000'
            })
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers)
            else:
                # POST 請求使用 form-data 格式
                response = requests.post(url, data=params, headers=headers)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"API請求錯誤: {e}")
            return {"retCode": -1, "retMsg": str(e)}
    
    def get_tickers(self, category: str = "linear", symbol: str = None) -> Dict:
        """獲取市場行情"""
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
        return self._make_request("GET", "/v5/market/tickers", params)
    
    def get_funding_rate(self, symbol: str = None, limit: int = 200) -> Dict:
        """獲取資金費率歷史"""
        params = {"category": "linear", "limit": limit}
        if symbol:
            params["symbol"] = symbol
        return self._make_request("GET", "/v5/market/funding/history", params)
    
    def get_account_balance(self, account_type: str = "UNIFIED") -> Dict:
        """獲取帳戶餘額"""
        params = {"accountType": account_type}
        return self._make_request("GET", "/v5/account/wallet-balance", params, signed=True)
    
    def place_order(self, symbol: str, side: str, order_type: str, qty: str, 
                   price: str = None, category: str = "linear") -> Dict:
        """下單"""
        params = {
            "category": category,
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty
        }
        if price:
            params["price"] = price
        
        # 對於現貨市價單，使用qty參數（數量）
        # 不再添加quoteQty，因為現在傳入的是數量而不是金額
            
        return self._make_request("POST", "/v5/order/create", params, signed=True)
    
    def get_open_orders(self, symbol: str = None, category: str = "linear") -> Dict:
        """獲取未成交訂單"""
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
        return self._make_request("GET", "/v5/order/realtime", params, signed=True)
    
    def cancel_order(self, symbol: str, order_id: str, category: str = "linear") -> Dict:
        """取消訂單"""
        params = {
            "category": category,
            "symbol": symbol,
            "orderId": order_id
        }
        return self._make_request("POST", "/v5/order/cancel", params, signed=True)
    
    def set_leverage(self, symbol: str, leverage: str, category: str = "linear") -> Dict:
        """設置槓桿"""
        params = {
            "category": category,
            "symbol": symbol,
            "buyLeverage": leverage,
            "sellLeverage": leverage
        }
        return self._make_request("POST", "/v5/position/set-leverage", params, signed=True)
    
    def get_instruments_info(self, category: str = "spot", symbol: str = None) -> Dict:
        """獲取交易規則信息"""
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
        return self._make_request("GET", "/v5/market/instruments-info", params, signed=False)
    
    def apply_demo_money(self, uta_demo_apply_money: list, adjust_type: int = 0) -> Dict:
        """申請 Demo 資金"""
        params = {
            "adjustType": adjust_type,
            "utaDemoApplyMoney": uta_demo_apply_money
        }
        return self._make_request("POST", "/v5/account/demo-apply-money", params, signed=True)
    
    def get_positions(self, symbol: str = None, category: str = "linear") -> Dict:
        """獲取持倉資訊"""
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
        if category == "linear":
            params["settleCoin"] = "USDT"  # 添加 settleCoin 參數
        return self._make_request("GET", "/v5/position/list", params, signed=True)
    
    def get_spot_tickers(self, symbol: str = None) -> Dict:
        """獲取現貨行情"""
        return self.get_tickers("spot", symbol)
    
    def get_linear_tickers(self, symbol: str = None) -> Dict:
        """獲取永續合約行情"""
        return self.get_tickers("linear", symbol)
