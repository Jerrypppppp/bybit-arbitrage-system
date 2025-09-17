"""
交易規則管理模組
自動獲取和緩存各幣種的交易限制
"""

import json
import time
from typing import Dict, Optional, Tuple
from bybit_client import BybitClient

class TradingRulesManager:
    """交易規則管理器"""
    
    def __init__(self, client: BybitClient):
        self.client = client
        self.rules_cache = {}
        self.cache_time = 0
        self.cache_duration = 3600  # 1小時緩存
        
    def get_trading_rules(self, symbol: str, force_refresh: bool = False) -> Dict:
        """
        獲取交易規則
        
        Args:
            symbol: 交易對
            force_refresh: 強制刷新緩存
            
        Returns:
            交易規則字典
        """
        # 檢查緩存
        if not force_refresh and self._is_cache_valid():
            if symbol in self.rules_cache:
                return self.rules_cache[symbol]
        
        # 獲取現貨規則
        spot_rules = self._get_spot_rules(symbol)
        
        # 獲取合約規則
        linear_rules = self._get_linear_rules(symbol)
        
        # 合併規則
        rules = {
            'symbol': symbol,
            'spot': spot_rules,
            'linear': linear_rules,
            'last_updated': time.time()
        }
        
        # 更新緩存
        self.rules_cache[symbol] = rules
        self.cache_time = time.time()
        
        return rules
    
    def _get_spot_rules(self, symbol: str) -> Dict:
        """獲取現貨交易規則"""
        try:
            result = self.client.get_instruments_info("spot", symbol)
            if result.get("retCode") == 0 and result.get("result", {}).get("list"):
                instrument = result["result"]["list"][0]
                lot_filter = instrument.get('lotSizeFilter', {})
                price_filter = instrument.get('priceFilter', {})
                
                # 計算精度
                base_precision = lot_filter.get('basePrecision', '0.00001')
                qty_precision = len(base_precision.split('.')[-1]) if '.' in base_precision else 0
                price_precision = len(price_filter.get('tickSize', '0.01').split('.')[-1]) if '.' in price_filter.get('tickSize', '0.01') else 0
                
                return {
                    'min_order_qty': float(lot_filter.get('minOrderQty', '0')),
                    'max_order_qty': float(lot_filter.get('maxOrderQty', '0')),
                    'qty_step': float(lot_filter.get('basePrecision', '0.00001')),
                    'min_order_amt': float(lot_filter.get('minOrderAmt', '0')),
                    'max_order_amt': float(lot_filter.get('maxOrderAmt', '0')),
                    'price_precision': price_precision,
                    'qty_precision': qty_precision,
                    'status': instrument.get('status', 'Unknown')
                }
        except Exception as e:
            print(f"獲取現貨規則失敗 {symbol}: {e}")
        
        return self._get_default_rules()
    
    def _get_linear_rules(self, symbol: str) -> Dict:
        """獲取合約交易規則"""
        try:
            result = self.client.get_instruments_info("linear", symbol)
            if result.get("retCode") == 0 and result.get("result", {}).get("list"):
                instrument = result["result"]["list"][0]
                lot_filter = instrument.get('lotSizeFilter', {})
                price_filter = instrument.get('priceFilter', {})
                
                # 計算精度
                qty_step = lot_filter.get('qtyStep', '0.01')
                qty_precision = len(qty_step.split('.')[-1]) if '.' in qty_step else 0
                price_precision = len(price_filter.get('tickSize', '0.01').split('.')[-1]) if '.' in price_filter.get('tickSize', '0.01') else 0
                
                return {
                    'min_order_qty': float(lot_filter.get('minOrderQty', '0')),
                    'max_order_qty': float(lot_filter.get('maxOrderQty', '0')),
                    'qty_step': float(qty_step),
                    'min_order_amt': float(lot_filter.get('minNotionalValue', '0')),  # 合約使用 minNotionalValue
                    'max_order_amt': float(lot_filter.get('maxOrderQty', '0')) * 100000,  # 估算最大金額
                    'price_precision': price_precision,
                    'qty_precision': qty_precision,
                    'max_leverage': float(instrument.get('leverageFilter', {}).get('maxLeverage', '1')),
                    'status': instrument.get('status', 'Unknown')
                }
        except Exception as e:
            print(f"獲取合約規則失敗 {symbol}: {e}")
        
        return self._get_default_rules()
    
    def _get_default_rules(self) -> Dict:
        """獲取默認規則（當API失敗時使用）"""
        return {
            'min_order_qty': 0.001,
            'max_order_qty': 1000.0,
            'qty_step': 0.001,
            'min_order_amt': 5.0,
            'max_order_amt': 100000.0,
            'price_precision': 2,
            'qty_precision': 3,
            'max_leverage': 5.0,
            'status': 'Trading'
        }
    
    def _get_demo_min_qty(self, symbol: str) -> float:
        """獲取 Demo API 的實際最小交易數量"""
        # 基於實際測試結果的 Demo API 限制
        demo_limits = {
            'BTCUSDT': 5.0,   # 實際測試：需要 5 BTC 以上
            'ETHUSDT': 5.0,   # 實際測試：5 ETH 成功
            'SOLUSDT': 5.0,   # 實際測試：5 SOL 成功
            'ADAUSDT': 10.0,  # 實際測試：10 ADA 成功
            'DOTUSDT': 5.0,   # 估算
            'LINKUSDT': 5.0,  # 估算
            'UNIUSDT': 5.0,   # 估算
            'LTCUSDT': 5.0,   # 估算
            'BCHUSDT': 5.0,   # 估算
            'XRPUSDT': 10.0,  # 估算
            'AVAXUSDT': 5.0,  # 估算
            'ATOMUSDT': 5.0,  # 估算
            'NEARUSDT': 10.0, # 估算
        }
        return demo_limits.get(symbol, 5.0)  # 默認 5.0
    
    def _is_cache_valid(self) -> bool:
        """檢查緩存是否有效"""
        return time.time() - self.cache_time < self.cache_duration
    
    def get_min_investment_amount(self, symbol: str, leverage: int = 1) -> float:
        """
        計算最小投資金額
        
        Args:
            symbol: 交易對
            leverage: 槓桿倍數
            
        Returns:
            最小投資金額 (USDT)
        """
        rules = self.get_trading_rules(symbol)
        
        # 如果是 Demo API，使用實際的最小交易數量
        if self.client.demo:
            demo_min_qty = self._get_demo_min_qty(symbol)
            # 估算價格（使用當前價格或默認價格）
            estimated_price = 4500 if 'ETH' in symbol else 50000 if 'BTC' in symbol else 100
            demo_min_amount = demo_min_qty * estimated_price
            
            # 現貨投資比例
            spot_ratio = leverage / (leverage + 1)
            min_amount = demo_min_amount / spot_ratio * 1.2  # 加上安全邊際
            
            return round(min_amount, 2)
        
        # 非 Demo API 使用規則中的限制
        spot_min = rules['spot']['min_order_amt']
        linear_min = rules['linear']['min_order_amt'] / leverage
        min_amount = max(spot_min, linear_min) * 1.2
        
        return round(min_amount, 2)
    
    def validate_order_params(self, symbol: str, qty: float, price: float, 
                            category: str = "spot") -> Tuple[bool, str]:
        """
        驗證訂單參數
        
        Args:
            symbol: 交易對
            qty: 數量
            price: 價格
            category: 類別 (spot/linear)
            
        Returns:
            (是否有效, 錯誤信息)
        """
        rules = self.get_trading_rules(symbol)
        rule = rules[category]
        
        # 檢查數量
        if qty < rule['min_order_qty']:
            return False, f"數量 {qty} 小於最小要求 {rule['min_order_qty']}"
        
        if qty > rule['max_order_qty']:
            return False, f"數量 {qty} 超過最大限制 {rule['max_order_qty']}"
        
        # 檢查數量步長（使用浮點數比較）
        if rule['qty_step'] > 0:
            remainder = qty % rule['qty_step']
            if abs(remainder) > 1e-10 and abs(remainder - rule['qty_step']) > 1e-10:
                return False, f"數量必須是 {rule['qty_step']} 的倍數"
        
        # 檢查金額
        amount = qty * price
        if amount < rule['min_order_amt']:
            return False, f"訂單金額 {amount:.2f} USDT 小於最小要求 {rule['min_order_amt']} USDT"
        
        if amount > rule['max_order_amt']:
            return False, f"訂單金額 {amount:.2f} USDT 超過最大限制 {rule['max_order_amt']} USDT"
        
        return True, "參數有效"
    
    def get_trading_tips(self, symbol: str) -> Dict:
        """
        獲取交易提示
        
        Args:
            symbol: 交易對
            
        Returns:
            交易提示字典
        """
        rules = self.get_trading_rules(symbol)
        
        tips = {
            'symbol': symbol,
            'min_investment': self.get_min_investment_amount(symbol),
            'spot_rules': {
                'min_qty': rules['spot']['min_order_qty'],
                'min_amount': rules['spot']['min_order_amt'],
                'qty_precision': rules['spot']['qty_precision'],
                'price_precision': rules['spot']['price_precision'],
                'qty_step': rules['spot']['qty_step']
            },
            'linear_rules': {
                'min_qty': rules['linear']['min_order_qty'],
                'min_amount': rules['linear']['min_order_amt'],
                'max_leverage': rules['linear']['max_leverage'],
                'qty_precision': rules['linear']['qty_precision'],
                'price_precision': rules['linear']['price_precision'],
                'qty_step': rules['linear']['qty_step']
            },
            'recommendations': []
        }
        
        # 生成建議
        if self.client.demo:
            demo_min_qty = self._get_demo_min_qty(symbol)
            estimated_price = 4500 if 'ETH' in symbol else 50000 if 'BTC' in symbol else 100
            demo_min_amount = demo_min_qty * estimated_price
            tips['recommendations'].append(f"⚠️ Demo API 最小交易數量: {demo_min_qty} {symbol.replace('USDT', '')} (約 {demo_min_amount:,.0f} USDT)")
            tips['recommendations'].append(f"💡 建議投資金額: {tips['min_investment']:,.0f} USDT 以上")
        else:
            if rules['spot']['min_order_amt'] > 10:
                tips['recommendations'].append(f"⚠️ {symbol} 現貨最小交易金額較高: {rules['spot']['min_order_amt']} USDT")
            
            if rules['linear']['min_order_amt'] > 10:
                tips['recommendations'].append(f"⚠️ {symbol} 合約最小交易金額較高: {rules['linear']['min_order_amt']} USDT")
            
            if rules['linear']['max_leverage'] < 5:
                tips['recommendations'].append(f"ℹ️ {symbol} 最大槓桿限制: {rules['linear']['max_leverage']}x")
            
            if not tips['recommendations']:
                tips['recommendations'].append("✅ 交易參數正常，可以進行套利")
        
        return tips
