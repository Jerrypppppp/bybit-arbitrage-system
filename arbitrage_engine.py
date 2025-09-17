"""
資金費率套利引擎
核心套利邏輯和機會計算
"""
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from bybit_client import BybitClient
from config import Config
from trading_rules import TradingRulesManager

@dataclass
class ArbitrageOpportunity:
    """套利機會數據結構"""
    symbol: str
    spot_price: float
    futures_price: float
    funding_rate: float
    price_difference: float
    price_difference_percent: float
    potential_profit: float
    risk_score: float
    timestamp: float

@dataclass
class Position:
    """持倉數據結構"""
    symbol: str
    spot_qty: float
    futures_qty: float
    spot_avg_price: float
    futures_avg_price: float
    unrealized_pnl: float
    funding_paid: float
    entry_time: float
    leverage: int = 1  # 槓桿倍數
    total_investment: float = 0.0  # 總投資金額
    spot_investment: float = 0.0  # 現貨投資金額
    futures_investment: float = 0.0  # 合約投資金額

@dataclass
class TradingResult:
    """交易結果數據結構"""
    success: bool
    message: str
    spot_order_id: Optional[str] = None
    futures_order_id: Optional[str] = None
    spot_qty: float = 0.0
    futures_qty: float = 0.0
    spot_price: float = 0.0
    futures_price: float = 0.0
    total_cost: float = 0.0

@dataclass
class ClosedPosition:
    """已平倉持倉歷史記錄"""
    symbol: str
    spot_qty: float
    futures_qty: float
    spot_avg_price: float
    futures_avg_price: float
    close_spot_qty: float
    close_futures_qty: float
    close_spot_price: float
    close_futures_price: float
    total_pnl: float
    entry_time: float
    close_time: float
    leverage: int
    total_investment: float
    spot_investment: float
    futures_investment: float
    funding_paid: float

class ArbitrageEngine:
    def __init__(self, client: BybitClient):
        self.client = client
        self.positions: Dict[str, Position] = {}
        self.opportunities: List[ArbitrageOpportunity] = []
        self.closed_positions: List[ClosedPosition] = []  # 歷史記錄
        self.rules_manager = TradingRulesManager(client)
        
    def get_funding_rate(self, symbol: str) -> Optional[float]:
        """獲取指定交易對的當前實時資金費率"""
        try:
            # 將 USDT 交易對轉換為 PERP 格式用於資金費率查詢
            # 例如：BTCUSDT -> BTCPERP, ETHUSDT -> ETHPERP
            if symbol.endswith('USDT'):
                perp_symbol = symbol.replace('USDT', 'PERP')
            else:
                perp_symbol = symbol
            
            # 使用 Tickers API 獲取實時資金費率
            response = self.client.get_tickers("linear", perp_symbol)
            if response.get("retCode") == 0 and response.get("result", {}).get("list"):
                ticker_data = response["result"]["list"][0]
                if "fundingRate" in ticker_data:
                    funding_rate = float(ticker_data["fundingRate"])
                    next_funding_time = int(ticker_data.get("nextFundingTime", 0))
                    
                    # 計算距離下次結算的時間
                    import time
                    current_time = int(time.time() * 1000)
                    time_to_next = (next_funding_time - current_time) / (1000 * 3600)  # 轉換為小時
                    
                    print(f"📊 實時資金費率 {symbol}:")
                    print(f"   當前費率: {funding_rate:.6f} ({funding_rate*100:.4f}%)")
                    print(f"   下次結算: {time_to_next:.2f} 小時後")
                    
                    return funding_rate
        except Exception as e:
            print(f"獲取實時資金費率失敗 {symbol} (PERP: {perp_symbol}): {e}")
        return None
    
    def get_spot_price(self, symbol: str) -> Optional[float]:
        """獲取現貨價格"""
        try:
            # 確保交易對格式正確（USDT 結尾）
            if not symbol.endswith('USDT'):
                symbol = symbol + 'USDT'
            
            response = self.client.get_spot_tickers(symbol)
            if response.get("retCode") == 0 and response.get("result", {}).get("list"):
                last_price = float(response["result"]["list"][0]["lastPrice"])
                return last_price
        except Exception as e:
            print(f"獲取現貨價格失敗 {symbol}: {e}")
        return None
    
    def get_futures_price(self, symbol: str) -> Optional[float]:
        """獲取永續合約價格"""
        try:
            # 確保交易對格式正確（USDT 結尾）
            if not symbol.endswith('USDT'):
                symbol = symbol + 'USDT'
            
            response = self.client.get_linear_tickers(symbol)
            if response.get("retCode") == 0 and response.get("result", {}).get("list"):
                last_price = float(response["result"]["list"][0]["lastPrice"])
                return last_price
        except Exception as e:
            print(f"獲取合約價格失敗 {symbol}: {e}")
        return None
    
    def calculate_arbitrage_opportunity(self, symbol: str) -> Optional[ArbitrageOpportunity]:
        """計算套利機會"""
        try:
            # 獲取價格和資金費率
            spot_price = self.get_spot_price(symbol)
            futures_price = self.get_futures_price(symbol)
            funding_rate = self.get_funding_rate(symbol)
            
            if not all([spot_price, futures_price, funding_rate is not None]):
                return None
            
            # 計算價格差異
            price_difference = futures_price - spot_price
            price_difference_percent = (price_difference / spot_price) * 100
            
            # 計算潛在利潤（8小時資金費率）
            daily_funding = funding_rate * 3  # 每天3次資金費率結算
            potential_profit = daily_funding * 100  # 假設100 USDT倉位
            
            # 計算風險評分
            risk_score = self._calculate_risk_score(price_difference_percent, funding_rate)
            
            opportunity = ArbitrageOpportunity(
                symbol=symbol,
                spot_price=spot_price,
                futures_price=futures_price,
                funding_rate=funding_rate,
                price_difference=price_difference,
                price_difference_percent=price_difference_percent,
                potential_profit=potential_profit,
                risk_score=risk_score,
                timestamp=time.time()
            )
            
            return opportunity
            
        except Exception as e:
            print(f"計算套利機會失敗 {symbol}: {e}")
            return None
    
    def _calculate_risk_score(self, price_diff_percent: float, funding_rate: float) -> float:
        """計算風險評分 (0-1, 越低越安全)"""
        # 價格差異風險
        price_risk = min(abs(price_diff_percent) / 2.0, 1.0)  # 2%以上視為高風險
        
        # 資金費率風險（負費率風險較高）
        funding_risk = max(0, -funding_rate * 100)  # 負費率增加風險
        
        # 綜合風險評分
        risk_score = (price_risk * 0.7 + funding_risk * 0.3)
        return min(risk_score, 1.0)
    
    def scan_opportunities(self, symbols: List[str]) -> List[ArbitrageOpportunity]:
        """掃描所有交易對的套利機會"""
        opportunities = []
        
        for symbol in symbols:
            opportunity = self.calculate_arbitrage_opportunity(symbol)
            if opportunity and opportunity.funding_rate > Config.MIN_FUNDING_RATE:
                opportunities.append(opportunity)
        
        # 按潛在利潤排序
        opportunities.sort(key=lambda x: x.potential_profit, reverse=True)
        self.opportunities = opportunities
        return opportunities
    
    def execute_arbitrage(self, symbol: str, amount: float) -> bool:
        """執行套利交易"""
        try:
            # 獲取當前價格
            spot_price = self.get_spot_price(symbol)
            futures_price = self.get_futures_price(symbol)
            
            if not spot_price or not futures_price:
                print(f"無法獲取 {symbol} 的價格")
                return False
            
            # 計算數量
            spot_qty = amount / spot_price
            futures_qty = amount / futures_price
            
            # 下現貨買單
            spot_order = self.client.place_order(
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=str(round(spot_qty, 6)),
                category="spot"
            )
            
            if spot_order.get("retCode") != 0:
                print(f"現貨買單失敗: {spot_order.get('retMsg')}")
                return False
            
            # 下合約空單
            futures_order = self.client.place_order(
                symbol=symbol,
                side="Sell",
                order_type="Market", 
                qty=str(round(futures_qty, 6)),
                category="linear"
            )
            
            if futures_order.get("retCode") != 0:
                print(f"合約空單失敗: {futures_order.get('retMsg')}")
                # 如果合約下單失敗，嘗試取消現貨訂單
                self.client.cancel_order(symbol, spot_order["result"]["orderId"], "spot")
                return False
            
            # 記錄持倉
            position = Position(
                symbol=symbol,
                spot_qty=spot_qty,
                futures_qty=futures_qty,
                spot_avg_price=spot_price,
                futures_avg_price=futures_price,
                unrealized_pnl=0.0,
                funding_paid=0.0,
                entry_time=time.time()
            )
            self.positions[symbol] = position
            
            print(f"套利交易執行成功: {symbol}")
            print(f"現貨買入: {spot_qty:.6f} @ {spot_price}")
            print(f"合約做空: {futures_qty:.6f} @ {futures_price}")
            
            return True
            
        except Exception as e:
            print(f"執行套利交易失敗 {symbol}: {e}")
            return False
    
    # 舊的close_position函數已移除，使用新的TradingResult版本

    def calculate_capital_allocation(self, total_amount: float, leverage: int) -> Tuple[float, float]:
        """
        計算資金分配
        對於對衝套利，現貨和合約應該買入相同數量的幣，但合約使用槓桿
        
        Args:
            total_amount: 總投資金額
            leverage: 槓桿倍數
            
        Returns:
            (spot_amount, futures_amount): 現貨投資金額, 合約保證金
        """
        # 對衝套利邏輯：
        # 1. 現貨：用一半資金買入現貨
        # 2. 合約：用另一半資金作為保證金，通過槓桿做空相同數量的幣
        
        # 現貨投資：直接買入現貨
        spot_amount = total_amount / 2
        
        # 合約保證金：用於做空相同價值的合約
        # 由於合約有槓桿，保證金 = 現貨價值 / 槓桿
        futures_amount = spot_amount / leverage
        
        return spot_amount, futures_amount

    def one_click_arbitrage(self, symbol: str, total_amount: float, leverage: int = 2) -> TradingResult:
        """
        一鍵套利下單：現貨做多 + 合約做空
        
        Args:
            symbol: 交易對
            total_amount: 總投資金額 (USDT)
            leverage: 槓桿倍數 (1-5)
            
        Returns:
            TradingResult: 交易結果
        """
        try:
            # 獲取交易規則和提示
            tips = self.rules_manager.get_trading_tips(symbol)
            
            # 檢查槓桿倍數
            max_leverage = tips['linear_rules']['max_leverage']
            if leverage < 1 or leverage > max_leverage:
                return TradingResult(False, f"槓桿倍數必須在 1-{max_leverage} 之間，當前設置: {leverage}")
            
            # 檢查最小投資金額
            min_investment = tips['min_investment']
            if total_amount < min_investment:
                return TradingResult(False, f"投資金額 {total_amount:.2f} USDT 小於最小要求 {min_investment:.2f} USDT")
            
            # 計算資金分配
            spot_amount, futures_amount = self.calculate_capital_allocation(total_amount, leverage)
            
            # 獲取當前價格
            spot_price = self.get_spot_price(symbol)
            futures_price = self.get_futures_price(symbol)
            
            if not spot_price or not futures_price:
                return TradingResult(False, f"無法獲取 {symbol} 的價格信息")
            
            # 計算交易數量並調整精度
            # 對衝套利：現貨和合約應該買入相同數量的幣
            # 現貨：用spot_amount買入現貨
            # 合約：用futures_amount做空合約
            spot_qty = spot_amount / spot_price  # 現貨數量 = 現貨投資金額 / 現貨價格
            futures_qty = futures_amount / futures_price  # 合約數量 = 合約保證金 / 合約價格
            
            # 調整數量以符合步長要求
            spot_step = tips['spot_rules']['qty_step']
            futures_step = tips['linear_rules']['qty_step']
            
            # 將數量調整為步長的倍數
            spot_qty = round(spot_qty / spot_step) * spot_step
            futures_qty = round(futures_qty / futures_step) * futures_step
            
            # 使用交易規則的精度設置
            spot_precision = tips['spot_rules']['qty_precision']
            futures_precision = tips['linear_rules']['qty_precision']
            
            spot_qty = round(spot_qty, spot_precision)
            futures_qty = round(futures_qty, futures_precision)
            
            # 檢查數量是否為0或負數
            if spot_qty <= 0 or futures_qty <= 0:
                return TradingResult(False, f"計算的交易數量無效: 現貨 {spot_qty}, 合約 {futures_qty}")
            
            # 驗證現貨訂單參數
            spot_valid, spot_error = self.rules_manager.validate_order_params(
                symbol, spot_qty, spot_price, "spot"
            )
            if not spot_valid:
                return TradingResult(False, f"現貨訂單參數無效: {spot_error}")
            
            # 驗證合約訂單參數
            futures_valid, futures_error = self.rules_manager.validate_order_params(
                symbol, futures_qty, futures_price, "linear"
            )
            if not futures_valid:
                return TradingResult(False, f"合約訂單參數無效: {futures_error}")
            
            print(f"📊 對衝套利資金分配:")
            print(f"   總投資: {total_amount:.2f} USDT")
            print(f"   槓桿: {leverage}x")
            print(f"   現貨投資: {spot_amount:.2f} USDT → 買入 {spot_qty:.6f} {symbol.replace('USDT', '')} (價值: {spot_qty * spot_price:.2f} USDT)")
            print(f"   合約保證金: {futures_amount:.2f} USDT → 做空 {futures_qty:.6f} {symbol.replace('USDT', '')} (價值: {futures_qty * futures_price:.2f} USDT)")
            print(f"   現貨價格: {spot_price:.4f} USDT")
            print(f"   合約價格: {futures_price:.4f} USDT")
            print(f"   對衝效果: 現貨 {spot_qty:.6f} 個 vs 合約 {futures_qty:.6f} 個 (數量相等，完全對衝)")
            print(f"   槓桿效果: 合約保證金 {futures_amount:.2f} USDT 通過 {leverage}x 槓桿控制 {futures_qty * futures_price:.2f} USDT 價值的合約")
            
            # 執行現貨買入訂單（使用市價單，傳入USDT金額）
            spot_result = self.client.place_order(
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=str(spot_amount),  # 傳入USDT金額，不是數量
                category="spot"
            )
            
            if spot_result.get("retCode") != 0:
                error_msg = spot_result.get('retMsg', '未知錯誤')
                print(f"❌ 現貨買入失敗: {error_msg}")
                print(f"   訂單參數: symbol={symbol}, side=Buy, qty={spot_qty}, category=spot")
                print(f"   完整響應: {spot_result}")
                return TradingResult(False, f"現貨買入失敗: {error_msg}")
            
            spot_order_id = spot_result.get("result", {}).get("orderId")
            print(f"✅ 現貨買入成功: 訂單ID {spot_order_id}")
            
            # 設置合約槓桿
            leverage_result = self.client.set_leverage(
                symbol=symbol,
                leverage=str(leverage),
                category="linear"
            )
            
            if leverage_result.get("retCode") != 0:
                print(f"⚠️ 設置槓桿失敗: {leverage_result.get('retMsg')}")
                # 繼續執行，可能槓桿已經設置過
            
            # 執行合約賣出訂單（使用市價單，完全用USDT計價）
            futures_result = self.client.place_order(
                symbol=symbol,
                side="Sell",
                order_type="Market",
                qty=str(futures_qty),
                category="linear"
            )
            
            if futures_result.get("retCode") != 0:
                error_msg = futures_result.get('retMsg', '未知錯誤')
                print(f"❌ 合約賣出失敗: {error_msg}")
                print(f"   訂單參數: symbol={symbol}, side=Sell, qty={futures_qty}, category=linear")
                print(f"   完整響應: {futures_result}")
                # 如果合約下單失敗，嘗試取消現貨訂單
                if spot_order_id:
                    print(f"🔄 嘗試取消現貨訂單: {spot_order_id}")
                    cancel_result = self.client.cancel_order(symbol, spot_order_id, "spot")
                    print(f"   取消結果: {cancel_result}")
                return TradingResult(False, f"合約賣出失敗: {error_msg}")
            
            futures_order_id = futures_result.get("result", {}).get("orderId")
            print(f"✅ 合約賣出成功: 訂單ID {futures_order_id}")
            
            # 計算開倉手續費（根據Bybit實際費率）
            SPOT_FEE_RATE = 0.001  # 0.1% (現貨Taker/Maker)
            FUTURES_FEE_RATE = 0.00055  # 0.055% (衍生品Taker，市價單)
            
            spot_fees = spot_amount * SPOT_FEE_RATE
            futures_fees = (futures_qty * futures_price) * FUTURES_FEE_RATE
            total_entry_fees = spot_fees + futures_fees
            
            print(f"💰 開倉手續費計算:")
            print(f"   現貨手續費: {spot_amount:.2f} × {SPOT_FEE_RATE:.3f} = {spot_fees:.2f} USDT")
            print(f"   合約手續費: {futures_qty:.6f} × {futures_price:.4f} × {FUTURES_FEE_RATE:.3f} = {futures_fees:.2f} USDT")
            print(f"   總開倉手續費: {total_entry_fees:.2f} USDT")
            
            # 創建持倉記錄
            position = Position(
                symbol=symbol,
                spot_qty=spot_qty,
                futures_qty=futures_qty,
                spot_avg_price=spot_price,
                futures_avg_price=futures_price,
                unrealized_pnl=0.0,
                funding_paid=0.0,
                entry_time=time.time(),
                leverage=leverage,
                total_investment=total_amount,
                spot_investment=spot_amount,
                futures_investment=futures_amount
            )
            
            self.positions[symbol] = position
            
            return TradingResult(
                success=True,
                message=f"✅ 一鍵套利成功！現貨買入 {spot_qty:.6f}，合約賣出 {futures_qty:.6f}",
                spot_order_id=spot_order_id,
                futures_order_id=futures_order_id,
                spot_qty=spot_qty,
                futures_qty=futures_qty,
                spot_price=spot_price,
                futures_price=futures_price,
                total_cost=total_amount
            )
            
        except Exception as e:
            return TradingResult(False, f"一鍵套利失敗: {str(e)}")

    def close_position(self, symbol: str) -> TradingResult:
        """
        平倉：賣出現貨，買入合約
        
        Args:
            symbol: 交易對
            
        Returns:
            TradingResult: 平倉結果
        """
        try:
            # 先更新持倉信息，確保獲取最新數據
            self.get_positions_summary()
            
            if symbol not in self.positions:
                return TradingResult(False, f"未找到 {symbol} 的持倉")
            
            position = self.positions[symbol]
            
            # 獲取當前價格
            spot_price = self.get_spot_price(symbol)
            futures_price = self.get_futures_price(symbol)
            
            if not spot_price or not futures_price:
                return TradingResult(False, f"無法獲取 {symbol} 的價格信息")
            
            # 獲取交易規則以確定正確的精度
            tips = self.rules_manager.get_trading_tips(symbol)
            spot_precision = tips['spot_rules']['qty_precision']
            
            # 根據合約倉位決定現貨賣出數量
            # 合約有多少倉位就賣多少現貨
            futures_qty = abs(position.futures_qty)  # 合約倉位數量
            close_spot_qty = min(position.spot_qty, futures_qty)  # 賣出現貨數量不超過合約倉位
            
            print(f"📊 平倉計算:")
            print(f"   合約倉位: {futures_qty:.6f}")
            print(f"   現貨持倉: {position.spot_qty:.6f}")
            print(f"   賣出現貨: {close_spot_qty:.6f}")
            
            # 賣出現貨（使用qty參數，傳入數量）
            spot_result = self.client.place_order(
                symbol=symbol,
                side="Sell",
                order_type="Market",
                qty=str(round(close_spot_qty, spot_precision)),  # 傳入數量
                category="spot"
            )
            
            if spot_result.get("retCode") != 0:
                return TradingResult(False, f"現貨賣出失敗: {spot_result.get('retMsg')}")
            
            # 買入合約（平空倉）
            futures_precision = tips['linear_rules']['qty_precision']
            close_futures_qty = abs(position.futures_qty)  # 平倉合約數量（絕對值）
            
            print(f"   平倉合約: {close_futures_qty:.6f}")
            
            futures_result = self.client.place_order(
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=str(round(close_futures_qty, futures_precision)),  # 使用正確的精度
                category="linear"
            )
            
            if futures_result.get("retCode") != 0:
                return TradingResult(False, f"合約買入失敗: {futures_result.get('retMsg')}")
            
            # 計算盈虧（對衝套利，包含手續費）
            # Bybit手續費率：現貨0.1%，衍生品市價單0.055%
            SPOT_FEE_RATE = 0.001  # 0.1% (現貨Taker/Maker)
            FUTURES_FEE_RATE = 0.00055  # 0.055% (衍生品Taker，市價單)
            
            # 現貨：買入現貨，賣出現貨 → 盈虧 = (賣出價格 - 買入價格) × 數量 - 手續費
            spot_gross_pnl = (spot_price - position.spot_avg_price) * close_spot_qty
            
            # 現貨手續費：開倉時買入手續費 + 平倉時賣出手續費
            spot_buy_amount = position.spot_avg_price * close_spot_qty  # 開倉時買入金額
            spot_sell_amount = spot_price * close_spot_qty  # 平倉時賣出金額
            spot_fees = (spot_buy_amount + spot_sell_amount) * SPOT_FEE_RATE
            
            spot_pnl = spot_gross_pnl - spot_fees
            
            # 合約：做空合約，買入平倉 → 盈虧 = (做空價格 - 平倉價格) × 數量 - 手續費
            futures_gross_pnl = (position.futures_avg_price - futures_price) * abs(position.futures_qty)
            
            # 合約手續費：開倉時做空手續費 + 平倉時買入手續費
            futures_short_amount = position.futures_avg_price * abs(position.futures_qty)  # 開倉時做空金額
            futures_buy_amount = futures_price * abs(position.futures_qty)  # 平倉時買入金額
            futures_fees = (futures_short_amount + futures_buy_amount) * FUTURES_FEE_RATE
            
            futures_pnl = futures_gross_pnl - futures_fees
            
            # 計算資金費率收益
            # 資金費率每8小時收取一次，做空合約收取正資金費率
            funding_income = self.calculate_funding_income(position, close_spot_qty)
            
            total_pnl = spot_pnl + futures_pnl + funding_income
            total_fees = spot_fees + futures_fees
            
            print(f"📊 盈虧計算詳情（含手續費）:")
            print(f"   現貨毛利: ({spot_price:.4f} - {position.spot_avg_price:.4f}) × {close_spot_qty:.6f} = {spot_gross_pnl:.2f} USDT")
            print(f"   現貨手續費: ({spot_buy_amount:.2f} + {spot_sell_amount:.2f}) × {SPOT_FEE_RATE:.3f} = {spot_fees:.2f} USDT")
            print(f"   現貨淨利: {spot_pnl:.2f} USDT")
            print(f"   合約毛利: ({position.futures_avg_price:.4f} - {futures_price:.4f}) × {abs(position.futures_qty):.6f} = {futures_gross_pnl:.2f} USDT")
            print(f"   合約手續費: ({futures_short_amount:.2f} + {futures_buy_amount:.2f}) × {FUTURES_FEE_RATE:.3f} = {futures_fees:.2f} USDT")
            print(f"   合約淨利: {futures_pnl:.2f} USDT")
            print(f"   總手續費: {total_fees:.2f} USDT")
            print(f"   資金費率收益: {funding_income:.2f} USDT")
            print(f"   總淨利: {total_pnl:.2f} USDT")
            
            # 更新持倉記錄
            position.spot_qty -= close_spot_qty
            position.futures_qty = 0  # 合約完全平倉
            
            # 創建歷史記錄
            closed_position = ClosedPosition(
                symbol=symbol,
                spot_qty=position.spot_qty + close_spot_qty,  # 原始現貨持倉
                futures_qty=position.futures_qty,  # 原始合約持倉
                spot_avg_price=position.spot_avg_price,
                futures_avg_price=position.futures_avg_price,
                close_spot_qty=close_spot_qty,
                close_futures_qty=close_futures_qty,
                close_spot_price=spot_price,
                close_futures_price=futures_price,
                total_pnl=total_pnl,
                entry_time=position.entry_time,
                close_time=time.time(),
                leverage=position.leverage,
                total_investment=position.total_investment,
                spot_investment=position.spot_investment,
                futures_investment=position.futures_investment,
                funding_paid=position.funding_paid
            )
            
            # 添加到歷史記錄
            self.closed_positions.append(closed_position)
            
            # 如果合約已完全平倉，且現貨持倉接近0，則移除整個持倉記錄
            # 這樣可以避免在持倉畫面中顯示只有現貨的"假"持倉
            if position.futures_qty == 0 and position.spot_qty < 0.001:
                del self.positions[symbol]
                position_closed = True
            elif position.futures_qty == 0:
                # 合約已平倉但還有現貨，也移除記錄（避免誤導）
                del self.positions[symbol]
                position_closed = True
            else:
                position_closed = False
            
            return TradingResult(
                success=True,
                message=f"✅ 平倉成功！總盈虧: {total_pnl:.2f} USDT" + ("，持倉已完全關閉" if position_closed else f"，剩餘現貨: {position.spot_qty:.6f}"),
                spot_qty=close_spot_qty,  # 返回實際賣出的現貨數量
                futures_qty=close_futures_qty,  # 返回平倉的合約數量
                spot_price=spot_price,
                futures_price=futures_price,
                total_cost=0.0
            )
            
        except Exception as e:
            return TradingResult(False, f"平倉失敗: {str(e)}")
    
    def get_positions_summary(self) -> Dict:
        """獲取持倉摘要"""
        # 從 API 獲取實際持倉
        actual_positions = {}
        
        # 獲取合約持倉
        try:
            linear_result = self.client.get_positions(category="linear")
            if linear_result.get("retCode") == 0:
                for position_data in linear_result.get("result", {}).get("list", []):
                    symbol = position_data.get("symbol")
                    size = float(position_data.get("size", 0))
                    if size > 0:  # 只處理有持倉的
                        side = position_data.get("side")
                        avg_price = float(position_data.get("avgPrice", 0))
                        unrealized_pnl = float(position_data.get("unrealisedPnl", 0))
                        
                        # 檢查是否在我們的持倉記錄中
                        if symbol in self.positions:
                            # 更新現有持倉
                            pos = self.positions[symbol]
                            pos.futures_qty = size if side == "Buy" else -size
                            pos.futures_avg_price = avg_price
                            pos.unrealized_pnl = unrealized_pnl
                            actual_positions[symbol] = pos
                        else:
                            # 創建新的持倉記錄（可能是手動開的倉）
                            pos = Position(
                                symbol=symbol,
                                spot_qty=0.0,  # 現貨持倉需要從錢包餘額推斷
                                futures_qty=size if side == "Buy" else -size,
                                spot_avg_price=0.0,
                                futures_avg_price=avg_price,
                                unrealized_pnl=unrealized_pnl,
                                funding_paid=0.0,
                                entry_time=time.time(),
                                leverage=1,
                                total_investment=0.0,
                                spot_investment=0.0,
                                futures_investment=0.0
                            )
                            actual_positions[symbol] = pos
        except Exception as e:
            print(f"獲取合約持倉失敗: {e}")
        
        # 獲取現貨持倉（從錢包餘額推斷）
        try:
            balance_result = self.client.get_account_balance()
            if balance_result.get("retCode") == 0:
                for account in balance_result.get("result", {}).get("list", []):
                    for coin in account.get("coin", []):
                        coin_name = coin.get("coin")
                        balance = float(coin.get("walletBalance", 0))
                        
                        # 檢查是否有對應的交易對
                        if coin_name != "USDT" and balance > 0:
                            symbol = f"{coin_name}USDT"
                            if symbol in actual_positions:
                                actual_positions[symbol].spot_qty = balance
                            elif symbol in self.positions:
                                self.positions[symbol].spot_qty = balance
                                actual_positions[symbol] = self.positions[symbol]
        except Exception as e:
            print(f"獲取現貨持倉失敗: {e}")
        
        # 更新內部持倉記錄
        self.positions = actual_positions
        
        total_positions = len(actual_positions)
        total_value = sum(pos.spot_qty * pos.spot_avg_price + abs(pos.futures_qty) * pos.futures_avg_price 
                         for pos in actual_positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in actual_positions.values())
        total_funding_paid = sum(pos.funding_paid for pos in actual_positions.values())
        
        return {
            'total_positions': total_positions,
            'total_value': total_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_funding_paid': total_funding_paid,
            'positions': actual_positions
        }
    
    def get_closed_positions(self) -> List[ClosedPosition]:
        """獲取已平倉的歷史記錄"""
        return self.closed_positions
    
    def get_closed_positions_summary(self) -> Dict:
        """獲取已平倉持倉摘要"""
        if not self.closed_positions:
            return {
                'total_closed': 0,
                'total_pnl': 0.0,
                'total_investment': 0.0,
                'positions': []
            }
        
        total_pnl = sum(pos.total_pnl for pos in self.closed_positions)
        total_investment = sum(pos.total_investment for pos in self.closed_positions)
        
        return {
            'total_closed': len(self.closed_positions),
            'total_pnl': total_pnl,
            'total_investment': total_investment,
            'positions': self.closed_positions
        }
    
    def calculate_funding_income(self, position: Position, close_quantity: float) -> float:
        """
        計算資金費率收益
        
        Args:
            position: 持倉記錄
            close_quantity: 平倉數量
            
        Returns:
            資金費率收益 (USDT)
        """
        try:
            # 獲取當前資金費率
            symbol = position.symbol
            funding_rate = self.get_funding_rate(symbol)
            
            if not funding_rate:
                print(f"⚠️ 無法獲取 {symbol} 的資金費率")
                return 0.0
            
            # 計算持倉時間（小時）
            current_time = time.time()
            holding_hours = (current_time - position.entry_time) / 3600
            
            # 資金費率每8小時收取一次
            funding_periods = int(holding_hours / 8)
            
            if funding_periods <= 0:
                print(f"📊 資金費率計算: 持倉時間 {holding_hours:.2f} 小時，未達到8小時收取週期")
                return 0.0
            
            # 計算資金費率收益
            # 做空合約收取正資金費率（當資金費率為正時）
            futures_value = abs(position.futures_qty) * position.futures_avg_price
            funding_income = futures_value * funding_rate * funding_periods
            
            print(f"📊 資金費率計算:")
            print(f"   持倉時間: {holding_hours:.2f} 小時")
            print(f"   收取週期: {funding_periods} 次 (每8小時)")
            print(f"   合約價值: {futures_value:.2f} USDT")
            print(f"   資金費率: {funding_rate:.6f} ({funding_rate*100:.4f}%)")
            print(f"   資金費率收益: {futures_value:.2f} × {funding_rate:.6f} × {funding_periods} = {funding_income:.2f} USDT")
            
            return funding_income
            
        except Exception as e:
            print(f"❌ 計算資金費率收益失敗: {e}")
            return 0.0
