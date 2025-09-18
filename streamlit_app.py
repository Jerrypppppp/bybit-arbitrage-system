"""
Bybit 資金費率套利系統 - Streamlit 版本
"""
import streamlit as st
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import threading
from bybit_client import BybitClient
from arbitrage_engine import ArbitrageEngine
# from risk_manager import RiskManager  # 已移除風險管理模組
from config import Config

# 頁面配置
st.set_page_config(
    page_title="Bybit 資金費率套利系統",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 添加自定義 CSS 來抑制 ResizeObserver 警告
st.markdown("""
<style>
    /* 抑制 ResizeObserver 警告 */
    .stApp > div {
        overflow: hidden;
    }
    
    /* 優化圖表渲染 */
    .js-plotly-plot {
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# 自定義 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-message {
        color: #28a745;
        font-weight: bold;
    }
    .error-message {
        color: #dc3545;
        font-weight: bold;
    }
    .warning-message {
        color: #ffc107;
        font-weight: bold;
    }
    
    /* 優化 ResizeObserver 性能 */
    .stApp > div > div > div > div {
        contain: layout style;
    }
    
    /* 減少不必要的重渲染 */
    .stDataFrame {
        contain: layout;
    }
    
    /* 優化圖表性能 */
    .plotly-graph-div {
        contain: layout style;
    }
</style>
""", unsafe_allow_html=True)

# 初始化 session state
if 'client' not in st.session_state:
    st.session_state.client = None
if 'engine' not in st.session_state:
    st.session_state.engine = None
# if 'risk_manager' not in st.session_state:
#     st.session_state.risk_manager = None  # 已移除風險管理模組
if 'is_connected' not in st.session_state:
    st.session_state.is_connected = False
if 'opportunities' not in st.session_state:
    st.session_state.opportunities = []
if 'positions' not in st.session_state:
    st.session_state.positions = {}
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False

def main():
    """主函數"""
    # 標題
    st.markdown('<h1 class="main-header">💰 Bybit 資金費率套利系統</h1>', unsafe_allow_html=True)
    
    # 側邊欄 - API 配置
    with st.sidebar:
        st.header("🔧 API 配置")
        
        # 網路選擇
        network = st.selectbox(
            "選擇網路",
            ["demo", "mainnet"],
            index=0,
            help="demo: 模擬交易, mainnet: 主網"
        )
        
        # API 配置
        api_key = st.text_input(
            "API Key",
            type="password",
            help="請輸入您的 Bybit API Key"
        )
        
        secret_key = st.text_input(
            "Secret Key", 
            type="password",
            help="請輸入您的 Bybit Secret Key"
        )
        
        # 連接按鈕
        if st.button("🔌 連接 API", type="primary"):
            if api_key and secret_key:
                is_demo = network == "demo"
                is_testnet = False  # 不再支援 testnet
                connect_api(api_key, secret_key, is_testnet, is_demo)
            else:
                st.error("請輸入 API Key 和 Secret Key")
        
        # 連接狀態
        if st.session_state.is_connected:
            st.success("✅ 已連接")
        else:
            st.error("❌ 未連接")
        
        st.divider()
        
        # 系統設置
        st.header("⚙️ 系統設置")
        
        # 掃描間隔
        scan_interval = st.slider(
            "掃描間隔 (秒)",
            min_value=10,
            max_value=300,
            value=30,
            help="自動掃描套利機會的間隔時間"
        )
        
        # 自動刷新開關
        auto_refresh = st.toggle(
            "自動刷新",
            value=st.session_state.auto_refresh,
            help="開啟後會自動掃描套利機會"
        )
        
        if auto_refresh != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto_refresh
            if auto_refresh:
                st.success("自動刷新已開啟")
            else:
                st.success("自動刷新已關閉")
        
        # 最小資金費率
        min_funding_rate = st.number_input(
            "最小資金費率",
            min_value=0.0001,
            max_value=0.01,
            value=0.0001,
            step=0.0001,
            format="%.4f",
            help="只顯示高於此值的資金費率機會"
        )
    
    # 主內容區域
    if st.session_state.is_connected:
        # 創建選項卡
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 套利機會", "💼 持倉管理", "⚠️ 風險監控", "📈 歷史數據", "📋 交易對管理"])
        
        with tab1:
            show_opportunities_tab(min_funding_rate)
        
        with tab2:
            show_positions_tab()
        
        with tab3:
            show_risk_tab()
        
        with tab4:
            show_history_tab()
        
        with tab5:
            show_trading_pairs_tab()
    else:
        # 未連接時的歡迎頁面
        show_welcome_page()

def connect_api(api_key, secret_key, is_testnet, is_demo):
    """連接 API"""
    try:
        with st.spinner("正在連接 API..."):
            client = BybitClient(api_key, secret_key, is_testnet, is_demo)
            
            # 測試連接
            response = client.get_account_balance()
            if response.get("retCode") == 0:
                st.session_state.client = client
                st.session_state.engine = ArbitrageEngine(client)
                # st.session_state.risk_manager = RiskManager(st.session_state.engine)  # 已移除風險管理模組
                st.session_state.is_connected = True
                
                # 顯示連接成功信息
                if is_demo:
                    network_name = "模擬交易"
                else:
                    network_name = "主網"
                
                st.success(f"✅ 成功連接到 {network_name}")
                
                # 顯示賬戶餘額（只顯示 USDT）
                result = response.get("result", {})
                if result.get("list"):
                    account = result["list"][0]
                    # 查找 USDT 餘額
                    usdt_balance = "0"
                    if account.get("coin"):
                        for coin in account["coin"]:
                            if coin.get("coin") == "USDT":
                                usdt_balance = coin.get("walletBalance", "0")
                                break
                    st.info(f"💰 賬戶餘額: {usdt_balance} USDT")
            else:
                st.error(f"❌ 連接失敗: {response.get('retMsg', '未知錯誤')}")
    except Exception as e:
        st.error(f"❌ 連接失敗: {str(e)}")

def show_welcome_page():
    """顯示歡迎頁面"""
    st.markdown("""
    ## 🎯 歡迎使用 Bybit 資金費率套利系統
    
    ### 📋 使用步驟：
    1. **配置 API** - 在左側輸入您的 Bybit API 金鑰
    2. **選擇網路** - 建議先在測試網環境測試
    3. **開始掃描** - 系統會自動尋找套利機會
    4. **執行交易** - 選擇合適的機會進行套利
    
    ### ⚠️ 重要提醒：
    - 請先在測試網環境中充分測試
    - 了解相關風險後再使用主網
    - 建議從小額資金開始
    - 密切監控持倉狀況
    
    ### 🔗 獲取 API 金鑰：
    - 測試網：https://testnet.bybit.com
    - 主網：https://www.bybit.com
    """)

def show_opportunities_tab(min_funding_rate):
    """顯示套利機會選項卡"""
    st.header("📊 套利機會掃描")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🔄 手動刷新", type="primary"):
            scan_opportunities(min_funding_rate)
    
    with col2:
        if st.button("⏹️ 停止掃描"):
            st.session_state.auto_refresh = False
            st.success("掃描已停止")
    
    with col3:
        if st.session_state.auto_refresh:
            st.info("🔄 自動掃描中...")
        else:
            st.info("⏸️ 掃描已停止")
    
    # 顯示機會列表
    if st.session_state.opportunities:
        st.subheader("🎯 發現的套利機會")
        
        # 創建 DataFrame
        df = pd.DataFrame([
            {
                "交易對": opp.symbol,
                "現貨價格": f"${opp.spot_price:.4f}",
                "合約價格": f"${opp.futures_price:.4f}",
                "資金費率": f"{opp.funding_rate:.6f}",
                "價差%": f"{opp.price_difference_percent:.2f}%",
                "潛在利潤": f"${opp.potential_profit:.2f}",
                "風險評分": f"{opp.risk_score:.2f}",
                "時間": datetime.fromtimestamp(opp.timestamp).strftime("%H:%M:%S")
            }
            for opp in st.session_state.opportunities
        ])
        
        # 顯示表格
        st.dataframe(df, use_container_width=True)
        
        # 執行套利按鈕
        st.subheader("🚀 執行套利")
        
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            # 搜尋和選擇交易對
            all_symbols = Config.load_all_trading_pairs()
            
            # 搜尋框
            search_term = st.text_input(
                "🔍 搜尋交易對",
                placeholder="輸入幣種名稱，如 BTC, ETH, SOL...",
                help="輸入幣種名稱來搜尋交易對"
            )
            
            # 根據搜尋條件過濾交易對
            if search_term:
                filtered_symbols = [symbol for symbol in all_symbols 
                                  if search_term.upper() in symbol.upper()]
                if not filtered_symbols:
                    st.warning(f"未找到包含 '{search_term}' 的交易對")
                    filtered_symbols = all_symbols[:20]  # 顯示前20個
            else:
                # 顯示常用交易對
                common_pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT', 
                              'LINKUSDT', 'UNIUSDT', 'LTCUSDT', 'BCHUSDT', 'XRPUSDT',
                              'AVAXUSDT', 'ATOMUSDT', 'NEARUSDT', 'MATICUSDT', 'FTMUSDT']
                filtered_symbols = [pair for pair in common_pairs if pair in all_symbols]
                filtered_symbols.extend([symbol for symbol in all_symbols if symbol not in filtered_symbols][:10])
            
            # 顯示搜尋結果數量
            if search_term:
                st.caption(f"找到 {len(filtered_symbols)} 個交易對")
            else:
                st.caption(f"顯示常用交易對，共 {len(all_symbols)} 個可用")
            
            selected_symbol = st.selectbox(
                "選擇交易對",
                filtered_symbols,
                help="選擇要執行套利的交易對"
            )
        
        with col2:
            # 動態獲取最小投資金額
            min_amount = 50000.0  # Demo API 默認值
            if st.session_state.engine and selected_symbol:
                try:
                    tips = st.session_state.engine.rules_manager.get_trading_tips(selected_symbol)
                    min_amount = tips['min_investment']
                except:
                    pass
            
            amount = st.number_input(
                "總投資金額 (USDT)",
                min_value=min_amount,
                max_value=1000000.0,
                value=max(min_amount, 100000.0),
                step=1000.0,
                help=f"Demo API 最小投資金額: {min_amount:,.0f} USDT"
            )
        
        with col3:
            # 動態獲取最大槓桿
            max_leverage = 5  # 默認值
            if st.session_state.engine and selected_symbol:
                try:
                    tips = st.session_state.engine.rules_manager.get_trading_tips(selected_symbol)
                    max_leverage = int(tips['linear_rules']['max_leverage'])
                except:
                    pass
            
            leverage_options = list(range(1, max_leverage + 1))
            leverage = st.selectbox(
                "槓桿倍數",
                leverage_options,
                index=min(1, len(leverage_options) - 1),  # 默認選擇 2 倍槓桿或最大可用
                help=f"選擇槓桿倍數 (1-{max_leverage}x)"
            )
        
        with col4:
            st.write("")  # 空行
            st.write("")  # 空行
            if st.button("🚀 一鍵套利", type="primary"):
                execute_one_click_arbitrage(selected_symbol, amount, leverage)
        
        # 顯示交易提示
        if st.session_state.engine and selected_symbol:
            try:
                tips = st.session_state.engine.rules_manager.get_trading_tips(selected_symbol)
                
                # 顯示交易規則信息
                with st.expander(f"📋 {selected_symbol} 交易規則", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("現貨規則")
                        st.write(f"最小數量: {tips['spot_rules']['min_qty']}")
                        st.write(f"最小金額: {tips['spot_rules']['min_amount']} USDT")
                        st.write(f"數量精度: {tips['spot_rules']['qty_precision']} 位小數")
                        st.write(f"價格精度: {tips['spot_rules']['price_precision']} 位小數")
                    
                    with col2:
                        st.subheader("合約規則")
                        st.write(f"最小數量: {tips['linear_rules']['min_qty']}")
                        st.write(f"最小金額: {tips['linear_rules']['min_amount']} USDT")
                        st.write(f"最大槓桿: {tips['linear_rules']['max_leverage']}x")
                        st.write(f"數量精度: {tips['linear_rules']['qty_precision']} 位小數")
                        st.write(f"價格精度: {tips['linear_rules']['price_precision']} 位小數")
                
                # 顯示建議
                if tips['recommendations']:
                    for recommendation in tips['recommendations']:
                        if "⚠️" in recommendation:
                            st.warning(recommendation)
                        elif "ℹ️" in recommendation:
                            st.info(recommendation)
                        else:
                            st.success(recommendation)
                            
            except Exception as e:
                st.warning(f"無法獲取 {selected_symbol} 的交易規則: {str(e)}")
        
        # 顯示資金分配預覽
        if amount and leverage:
            spot_amount, futures_amount = st.session_state.engine.calculate_capital_allocation(amount, leverage)
            st.info(f"📊 對衝套利資金分配: 現貨 {spot_amount:.2f} USDT | 合約保證金 {futures_amount:.2f} USDT (現貨和合約買入相同數量，合約使用{leverage}x槓桿)")
        
        # 顯示選中交易對的實時信息
        if selected_symbol:
            st.subheader(f"📊 {selected_symbol} 實時信息")
            
            col1, col2, col3, col4 = st.columns(4)
            
            try:
                # 獲取現貨價格
                spot_price = st.session_state.engine.get_spot_price(selected_symbol)
                with col1:
                    if spot_price:
                        st.metric("現貨價格", f"${spot_price:.4f}")
                    else:
                        st.metric("現貨價格", "N/A")
                
                # 獲取合約價格
                futures_price = st.session_state.engine.get_futures_price(selected_symbol)
                with col2:
                    if futures_price:
                        st.metric("合約價格", f"${futures_price:.4f}")
                    else:
                        st.metric("合約價格", "N/A")
                
                # 獲取資金費率
                funding_rate = st.session_state.engine.get_funding_rate(selected_symbol)
                with col3:
                    if funding_rate is not None:
                        st.metric("資金費率", f"{funding_rate:.6f}")
                    else:
                        st.metric("資金費率", "N/A")
                
                # 計算價差
                with col4:
                    if spot_price and futures_price:
                        price_diff = ((futures_price - spot_price) / spot_price) * 100
                        st.metric("價差%", f"{price_diff:.2f}%")
                    else:
                        st.metric("價差%", "N/A")
                        
            except Exception as e:
                st.error(f"獲取 {selected_symbol} 信息時發生錯誤: {str(e)}")
    else:
        st.info("🔍 暫無套利機會，請點擊「手動刷新」開始掃描")
        
        # 即使沒有套利機會，也提供選擇幣種交易的功能
        st.subheader("🚀 手動選擇交易對")
        
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            # 搜尋和選擇交易對
            all_symbols = Config.load_all_trading_pairs()
            
            # 搜尋框
            search_term = st.text_input(
                "🔍 搜尋交易對",
                placeholder="輸入幣種名稱，如 BTC, ETH, SOL...",
                help="輸入幣種名稱來搜尋交易對",
                key="manual_search"
            )
            
            # 根據搜尋條件過濾交易對
            if search_term:
                filtered_symbols = [symbol for symbol in all_symbols 
                                  if search_term.upper() in symbol.upper()]
                if not filtered_symbols:
                    st.warning(f"未找到包含 '{search_term}' 的交易對")
                    filtered_symbols = all_symbols[:20]  # 顯示前20個
            else:
                # 顯示常用交易對
                common_pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT', 
                              'LINKUSDT', 'UNIUSDT', 'LTCUSDT', 'BCHUSDT', 'XRPUSDT',
                              'AVAXUSDT', 'ATOMUSDT', 'NEARUSDT', 'MATICUSDT', 'FTMUSDT']
                filtered_symbols = [pair for pair in common_pairs if pair in all_symbols]
                filtered_symbols.extend([symbol for symbol in all_symbols if symbol not in filtered_symbols][:10])
            
            # 顯示搜尋結果數量
            if search_term:
                st.caption(f"找到 {len(filtered_symbols)} 個交易對")
            else:
                st.caption(f"顯示常用交易對，共 {len(all_symbols)} 個可用")
            
            selected_symbol = st.selectbox(
                "選擇交易對",
                filtered_symbols,
                help="選擇要執行套利的交易對",
                key="manual_symbol"
            )
        
        with col2:
            amount = st.number_input(
                "總投資金額 (USDT)",
                min_value=50.0,
                max_value=10000.0,
                value=100.0,
                step=10.0,
                help="API 最小投資金額: 50 USDT (約 0.01 ETH)",
                key="manual_amount"
            )
        
        with col3:
            leverage = st.selectbox(
                "槓桿倍數",
                [1, 2, 3, 4, 5],
                index=1,  # 默認選擇 2 倍槓桿
                help="選擇槓桿倍數 (1-5x)",
                key="manual_leverage"
            )
        
        with col4:
            st.write("")  # 空行
            st.write("")  # 空行
            if st.button("🚀 一鍵套利", type="primary", key="manual_execute"):
                execute_one_click_arbitrage(selected_symbol, amount, leverage)
        
        # 顯示資金分配預覽
        if amount and leverage:
            spot_amount, futures_amount = st.session_state.engine.calculate_capital_allocation(amount, leverage)
            st.info(f"📊 對衝套利資金分配: 現貨 {spot_amount:.2f} USDT | 合約保證金 {futures_amount:.2f} USDT (現貨和合約買入相同數量，合約使用{leverage}x槓桿)")
        
        # 顯示選中交易對的實時信息
        if selected_symbol:
            st.subheader(f"📊 {selected_symbol} 實時信息")
            
            col1, col2, col3, col4 = st.columns(4)
            
            try:
                # 獲取現貨價格
                spot_price = st.session_state.engine.get_spot_price(selected_symbol)
                with col1:
                    if spot_price:
                        st.metric("現貨價格", f"${spot_price:.4f}")
                    else:
                        st.metric("現貨價格", "N/A")
                
                # 獲取合約價格
                futures_price = st.session_state.engine.get_futures_price(selected_symbol)
                with col2:
                    if futures_price:
                        st.metric("合約價格", f"${futures_price:.4f}")
                    else:
                        st.metric("合約價格", "N/A")
                
                # 獲取資金費率
                funding_rate = st.session_state.engine.get_funding_rate(selected_symbol)
                with col3:
                    if funding_rate is not None:
                        st.metric("資金費率", f"{funding_rate:.6f}")
                    else:
                        st.metric("資金費率", "N/A")
                
                # 計算價差
                with col4:
                    if spot_price and futures_price:
                        price_diff = ((futures_price - spot_price) / spot_price) * 100
                        st.metric("價差%", f"{price_diff:.2f}%")
                    else:
                        st.metric("價差%", "N/A")
                        
            except Exception as e:
                st.error(f"獲取 {selected_symbol} 信息時發生錯誤: {str(e)}")

def scan_opportunities(min_funding_rate):
    """掃描套利機會"""
    if not st.session_state.engine:
        st.error("請先連接 API")
        return
    
    with st.spinner("正在掃描套利機會..."):
        opportunities = st.session_state.engine.scan_opportunities(Config.load_all_trading_pairs())
        
        # 過濾最小資金費率
        filtered_opportunities = [
            opp for opp in opportunities 
            if opp.funding_rate > min_funding_rate
        ]
        
        st.session_state.opportunities = filtered_opportunities
        
        if filtered_opportunities:
            st.success(f"✅ 發現 {len(filtered_opportunities)} 個套利機會")
        else:
            st.warning("⚠️ 未發現符合條件的套利機會")

def execute_arbitrage(symbol, amount):
    """執行套利交易（舊版本，保留兼容性）"""
    if not st.session_state.engine:
        st.error("請先連接 API")
        return
    
    try:
        with st.spinner(f"正在執行 {symbol} 的套利交易..."):
            success = st.session_state.engine.execute_arbitrage(symbol, amount)
            
            if success:
                st.success(f"✅ {symbol} 套利交易執行成功！")
                st.balloons()
            else:
                st.error(f"❌ {symbol} 套利交易執行失敗")
    except Exception as e:
        st.error(f"❌ 執行套利時發生錯誤: {str(e)}")

def execute_one_click_arbitrage(symbol: str, total_amount: float, leverage: int):
    """執行一鍵套利交易"""
    if not st.session_state.engine:
        st.error("請先連接 API")
        return
    
    try:
        with st.spinner(f"正在執行 {symbol} 一鍵套利交易..."):
            # 調用一鍵套利方法
            result = st.session_state.engine.one_click_arbitrage(symbol, total_amount, leverage)
            
            if result.success:
                st.success(result.message)
                st.balloons()
                
                # 顯示詳細交易信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("現貨買入", f"{result.spot_qty:.6f}")
                with col2:
                    st.metric("合約賣出", f"{result.futures_qty:.6f}")
                with col3:
                    st.metric("總成本", f"{result.total_cost:.2f} USDT")
                
                # 顯示資金分配
                spot_amount, futures_amount = st.session_state.engine.calculate_capital_allocation(total_amount, leverage)
                st.info(f"📊 對衝套利資金分配: 現貨 {spot_amount:.2f} USDT | 合約保證金 {futures_amount:.2f} USDT (現貨和合約買入相同數量，合約使用{leverage}x槓桿)")
                
            else:
                st.error(f"❌ {result.message}")
            
            # 刷新持倉信息
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ 一鍵套利失敗: {str(e)}")

def show_positions_tab():
    """顯示持倉管理選項卡"""
    st.header("💼 持倉管理")
    
    if st.session_state.engine:
        # 獲取持倉摘要
        summary = st.session_state.engine.get_positions_summary()
        
        # 顯示持倉摘要
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("總持倉數", summary['total_positions'])
        
        with col2:
            st.metric("總價值 (USDT)", f"{summary['total_value']:.2f}")
        
        with col3:
            st.metric("未實現盈虧 (USDT)", f"{summary['total_unrealized_pnl']:.2f}")
        
        with col4:
            st.metric("已支付資金費 (USDT)", f"{summary['total_funding_paid']:.6f}")
        
        # 顯示詳細持倉
        if summary['positions']:
            st.subheader("📋 持倉詳情")
            
            for symbol, position in summary['positions'].items():
                with st.expander(f"📊 {symbol}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**現貨持倉:** {position.spot_qty:.6f}")
                        st.write(f"**現貨均價:** ${position.spot_avg_price:.4f}")
                        st.write(f"**合約持倉:** {position.futures_qty:.6f}")
                        st.write(f"**合約均價:** ${position.futures_avg_price:.4f}")
                        st.write(f"**槓桿倍數:** {position.leverage}x")
                    
                    with col2:
                        st.write(f"**未實現盈虧:** {position.unrealized_pnl:.2f} USDT")
                        st.write(f"**已支付資金費:** {position.funding_paid:.6f} USDT")
                        st.write(f"**總投資:** {position.total_investment:.2f} USDT")
                        st.write(f"**現貨投資:** {position.spot_investment:.2f} USDT")
                        st.write(f"**合約投資:** {position.futures_investment:.2f} USDT")
                        st.write(f"**開倉時間:** {datetime.fromtimestamp(position.entry_time).strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # 平倉按鈕
                    if st.button(f"平倉 {symbol}", key=f"close_{symbol}"):
                        close_position(symbol)
        else:
            st.info("📭 暫無持倉")
        
        # 平倉所有持倉
        if summary['positions']:
            st.divider()
            if st.button("🗑️ 平倉所有持倉", type="secondary"):
                close_all_positions()
        
    # 顯示歷史記錄
    show_closed_positions()

# 添加 JavaScript 來抑制 ResizeObserver 警告
st.markdown("""
<script>
    // 抑制 ResizeObserver 警告
    const originalError = console.error;
    console.error = function(...args) {
        if (args[0] && args[0].includes && args[0].includes('ResizeObserver loop completed with undelivered notifications')) {
            return; // 忽略 ResizeObserver 警告
        }
        originalError.apply(console, args);
    };
    
    // 優化 ResizeObserver 性能
    if (window.ResizeObserver) {
        const originalResizeObserver = window.ResizeObserver;
        window.ResizeObserver = class extends originalResizeObserver {
            constructor(callback) {
                super((entries, observer) => {
                    // 使用 requestAnimationFrame 來延遲回調
                    requestAnimationFrame(() => {
                        callback(entries, observer);
                    });
                });
            }
        };
    }
</script>
""", unsafe_allow_html=True)

def close_position(symbol):
    """平倉單個持倉"""
    try:
        with st.spinner(f"正在平倉 {symbol}..."):
            result = st.session_state.engine.close_position(symbol)
            
            if result.success:
                st.success(result.message)
                st.balloons()
                
                # 顯示平倉詳情
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("現貨賣出", f"{result.spot_qty:.6f}")
                with col2:
                    st.metric("合約買入", f"{result.futures_qty:.6f}")
                with col3:
                    st.metric("平倉價格", f"現貨: ${result.spot_price:.4f}")
                
            else:
                st.error(f"❌ {result.message}")
            
            # 刷新持倉信息
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ 平倉時發生錯誤: {str(e)}")

def close_all_positions():
    """平倉所有持倉"""
    try:
        with st.spinner("正在平倉所有持倉..."):
            success_count = 0
            total_count = len(st.session_state.engine.positions)
            
            for symbol in list(st.session_state.engine.positions.keys()):
                result = st.session_state.engine.close_position(symbol)
                if result.success:
                    success_count += 1
                    st.success(f"✅ {symbol} 平倉成功: {result.message}")
                else:
                    st.error(f"❌ {symbol} 平倉失敗: {result.message}")
            
            if success_count == total_count:
                st.success(f"✅ 所有持倉平倉成功 ({success_count}/{total_count})")
                st.balloons()
            else:
                st.warning(f"⚠️ 部分持倉平倉失敗 ({success_count}/{total_count})")
    except Exception as e:
        st.error(f"❌ 平倉時發生錯誤: {str(e)}")

def show_closed_positions():
    """顯示已平倉的歷史記錄"""
    if not st.session_state.engine:
        return
    
    # 獲取歷史記錄摘要
    closed_summary = st.session_state.engine.get_closed_positions_summary()
    
    if closed_summary['total_closed'] > 0:
        st.divider()
        st.subheader("📚 歷史記錄")
        
        # 顯示歷史記錄摘要
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("已平倉數", closed_summary['total_closed'])
        
        with col2:
            st.metric("總盈虧 (USDT)", f"{closed_summary['total_pnl']:.2f}")
        
        with col3:
            st.metric("總投資 (USDT)", f"{closed_summary['total_investment']:.2f}")
        
        # 顯示詳細歷史記錄
        st.subheader("📋 平倉詳情")
        
        for i, position in enumerate(reversed(closed_summary['positions'])):  # 最新的在前
            with st.expander(f"📊 {position.symbol} - {datetime.fromtimestamp(position.close_time).strftime('%Y-%m-%d %H:%M:%S')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**原始持倉:**")
                    st.write(f"  現貨: {position.spot_qty:.6f} @ ${position.spot_avg_price:.4f}")
                    st.write(f"  合約: {position.futures_qty:.6f} @ ${position.futures_avg_price:.4f}")
                    st.write(f"**平倉數量:**")
                    st.write(f"  現貨賣出: {position.close_spot_qty:.6f} @ ${position.close_spot_price:.4f}")
                    st.write(f"  合約買入: {position.close_futures_qty:.6f} @ ${position.close_futures_price:.4f}")
                
                with col2:
                    st.write(f"**投資信息:**")
                    st.write(f"  總投資: {position.total_investment:.2f} USDT")
                    st.write(f"  現貨投資: {position.spot_investment:.2f} USDT")
                    st.write(f"  合約投資: {position.futures_investment:.2f} USDT")
                    st.write(f"  槓桿倍數: {position.leverage}x")
                    st.write(f"**時間信息:**")
                    st.write(f"  開倉時間: {datetime.fromtimestamp(position.entry_time).strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"  平倉時間: {datetime.fromtimestamp(position.close_time).strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**盈虧:**")
                    pnl_color = "green" if position.total_pnl >= 0 else "red"
                    st.markdown(f"<span style='color: {pnl_color}; font-weight: bold;'>總盈虧: {position.total_pnl:.2f} USDT</span>", unsafe_allow_html=True)
    else:
        st.info("📭 暫無歷史記錄")

def show_risk_tab():
    """顯示風險監控選項卡"""
    st.header("⚠️ 風險監控")
    
    # 簡化版風險監控（不依賴 risk_manager）
    if st.session_state.engine:
        # 獲取持倉摘要
        summary = st.session_state.engine.get_positions_summary()
        
        # 顯示基本風險指標
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("總持倉數", summary['total_positions'])
        
        with col2:
            st.metric("總價值 (USDT)", f"{summary['total_value']:.2f}")
        
        with col3:
            st.metric("未實現盈虧 (USDT)", f"{summary['total_unrealized_pnl']:.2f}")
        
        with col4:
            # 計算風險比率（簡化版）
            risk_ratio = abs(summary['total_unrealized_pnl']) / max(summary['total_value'], 1)
            st.metric("風險比率", f"{risk_ratio:.2%}")
        
        # 基本風險建議
        st.subheader("💡 風險建議")
        
        if risk_ratio > 0.05:
            st.warning("⚠️ 風險比率較高，建議減少倉位")
        elif risk_ratio < 0.02:
            st.success("✅ 風險狀況良好")
        else:
            st.info("ℹ️ 風險狀況正常")
        
        if summary['total_unrealized_pnl'] < -100:
            st.error("🚨 虧損較大，請考慮止損")
        elif summary['total_unrealized_pnl'] > 100:
            st.success("💰 盈利良好，可考慮部分獲利了結")
        
        # 持倉分散度建議
        if summary['total_positions'] > 5:
            st.warning("⚠️ 持倉過於分散，建議集中優勢品種")
        elif summary['total_positions'] == 0:
            st.info("ℹ️ 暫無持倉，可尋找套利機會")
        else:
            st.success("✅ 持倉分散度適中")
    else:
        st.info("請先連接 API 以查看風險監控信息")

def show_history_tab():
    """顯示歷史數據選項卡"""
    st.header("📈 歷史數據")
    
    # 這裡可以添加歷史數據分析功能
    st.info("📊 歷史數據功能開發中...")

def show_trading_pairs_tab():
    """顯示交易對管理選項卡"""
    st.header("📋 交易對管理")
    
    # 載入所有交易對
    all_symbols = Config.load_all_trading_pairs()
    
    st.info(f"📊 總共找到 {len(all_symbols)} 個可用的交易對")
    
    # 搜尋功能
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input(
            "🔍 搜尋交易對",
            placeholder="輸入幣種名稱，如 BTC, ETH, SOL...",
            help="輸入幣種名稱來搜尋交易對"
        )
    
    with col2:
        if st.button("🔄 刷新交易對列表", help="重新獲取最新的交易對列表"):
            st.rerun()
    
    # 根據搜尋條件過濾交易對
    if search_term:
        filtered_symbols = [symbol for symbol in all_symbols 
                          if search_term.upper() in symbol.upper()]
        st.success(f"找到 {len(filtered_symbols)} 個包含 '{search_term}' 的交易對")
    else:
        filtered_symbols = all_symbols
        st.info("顯示所有可用的交易對")
    
    # 分頁顯示
    items_per_page = 50
    total_pages = (len(filtered_symbols) - 1) // items_per_page + 1
    
    if total_pages > 1:
        page = st.selectbox("選擇頁面", range(1, total_pages + 1), index=0)
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_symbols = filtered_symbols[start_idx:end_idx]
        
        st.caption(f"第 {page} 頁，共 {total_pages} 頁 (顯示 {len(page_symbols)} 個交易對)")
    else:
        page_symbols = filtered_symbols
    
    # 顯示交易對列表
    if page_symbols:
        # 創建表格顯示
        import pandas as pd
        
        # 將交易對分組顯示
        symbols_data = []
        for i, symbol in enumerate(page_symbols):
            base_currency = symbol.replace('USDT', '')
            symbols_data.append({
                '序號': i + 1 + (page - 1) * items_per_page if total_pages > 1 else i + 1,
                '交易對': symbol,
                '基礎幣種': base_currency,
                '狀態': '✅ 可用'
            })
        
        df = pd.DataFrame(symbols_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 顯示統計信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("總交易對數", len(all_symbols))
        with col2:
            st.metric("搜尋結果", len(filtered_symbols))
        with col3:
            st.metric("當前頁面", len(page_symbols))
        
        # 常用交易對快捷選擇
        st.subheader("🚀 常用交易對快捷選擇")
        
        common_pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT', 
                       'LINKUSDT', 'UNIUSDT', 'LTCUSDT', 'BCHUSDT', 'XRPUSDT',
                       'AVAXUSDT', 'ATOMUSDT', 'NEARUSDT', 'MATICUSDT', 'FTMUSDT']
        
        available_common = [pair for pair in common_pairs if pair in all_symbols]
        
        cols = st.columns(5)
        for i, pair in enumerate(available_common):
            with cols[i % 5]:
                if st.button(f"📊 {pair}", key=f"quick_{pair}"):
                    st.session_state.selected_quick_pair = pair
                    st.success(f"已選擇 {pair}")
        
        if hasattr(st.session_state, 'selected_quick_pair'):
            st.info(f"🎯 已選擇交易對: {st.session_state.selected_quick_pair}")
    
    else:
        st.warning("未找到符合條件的交易對")
    
    # 顯示最後更新時間
    try:
        import json
        with open('available_trading_pairs.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_updated = data.get('last_updated', '未知')
            st.caption(f"📅 最後更新時間: {last_updated}")
    except:
        st.caption("📅 更新時間: 未知")
    
    # 可以添加圖表、統計分析等
    st.write("未來將支持：")
    st.write("- 📊 資金費率歷史趨勢")
    st.write("- 💰 盈虧統計分析")
    st.write("- 📈 價格走勢圖表")
    st.write("- 📋 交易記錄查詢")

# 自動刷新邏輯
if st.session_state.auto_refresh and st.session_state.is_connected:
    if st.session_state.engine:
        scan_opportunities(0.0001)
    
    # 使用 time.sleep 來控制刷新間隔
    time.sleep(30)  # 30秒刷新一次
    st.rerun()

if __name__ == "__main__":
    main()
