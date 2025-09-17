"""
Bybit 資金費率套利系統配置
"""
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class Config:
    # Bybit API 端點
    BYBIT_MAINNET_BASE_URL = "https://api.bybit.com"
    BYBIT_DEMO_BASE_URL = "https://api-demo.bybit.com"  # 模擬交易域名
    
    # API 金鑰配置
    MAINNET_API_KEY = os.getenv('BYBIT_MAINNET_API_KEY', '')
    MAINNET_SECRET_KEY = os.getenv('BYBIT_MAINNET_SECRET_KEY', '')
    
    # 預設使用模擬交易
    USE_DEMO = os.getenv('USE_DEMO', 'true').lower() == 'true'
    
    # 套利參數
    MIN_FUNDING_RATE = 0.0001  # 最小資金費率 (0.01%)
    MAX_POSITION_SIZE = 1000   # 最大倉位大小 (USDT)
    STOP_LOSS_PERCENTAGE = 0.02  # 止損百分比 (2%)
    
    # 支援的交易對（統一使用 USDT 結尾，只包含可用的交易對）
    # 這些是常用的交易對，完整列表會從 available_trading_pairs.json 載入
    DEFAULT_PAIRS = [
        'BTCUSDT',
        'ETHUSDT', 
        'SOLUSDT',
        'ADAUSDT',
        'DOTUSDT',
        'LINKUSDT',
        'UNIUSDT',
        'LTCUSDT',
        'BCHUSDT',
        'XRPUSDT',
        'AVAXUSDT',
        'ATOMUSDT',
        'NEARUSDT'
    ]
    
    @staticmethod
    def load_all_trading_pairs():
        """載入所有可用的交易對"""
        try:
            import json
            with open('available_trading_pairs.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('common', Config.DEFAULT_PAIRS)
        except FileNotFoundError:
            return Config.DEFAULT_PAIRS
        except Exception as e:
            print(f"載入交易對失敗: {e}")
            return Config.DEFAULT_PAIRS
