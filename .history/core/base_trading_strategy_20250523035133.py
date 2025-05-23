from abc import ABC, abstractmethod
import pandas as pd
import logging
from datetime import datetime
import os

class BaseTradingStrategy(ABC):
    def __init__(self, config):
        self.config = config
        self.logger = self._setup_logger()
        self.trade_log = []
        
    def _setup_logger(self):
        """Setup logger for the strategy"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # Create file handler
        fh = logging.FileHandler(f'logs/{self.__class__.__name__}_{datetime.now().strftime("%Y%m%d")}.log')
        fh.setLevel(logging.INFO)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def get_data(self, merged_data):
        """
        Lấy dữ liệu theo các timeframe được cấu hình trong config['strategy']['timeframes'].
        """
        timeframes = self.config.get('strategy', {}).get('timeframes', [])
        result = {}
        for tf in timeframes:
            if tf in merged_data:
                result[tf] = merged_data[tf]
            else:
                self.logger.warning(f"Timeframe '{tf}' không có trong dữ liệu được nạp.")
        return result
    
    def init_trade_log(self):
        """Initialize trade log"""
        self.trade_log = []
        
    def save_trade_log(self):
        """Save trade log to file"""
        if not self.trade_log:
            return
            
        log_dir = 'logs/trades'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        filename = f'{log_dir}/{self.__class__.__name__}_{datetime.now().strftime("%Y%m%d")}.csv'
        df = pd.DataFrame(self.trade_log)
        df.to_csv(filename, index=False)
        self.logger.info(f"Trade log saved to {filename}")
    
    @abstractmethod
    def check_signals(self, data):
        """Check for trading signals in the data"""
        pass
    
    @abstractmethod
    def run_strategy(self):
        """Run the trading strategy"""
        pass
    
    def calculate_priority(self, signal):
        """Calculate the priority of a trading signal"""
        # Base implementation - can be overridden by child classes
        return 1.0
    
    def add_trade_log(self, trade_info):
        """Add a trade to the log"""
        trade_info['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trade_info['strategy'] = self.__class__.__name__
        self.trade_log.append(trade_info)
        self.logger.info(f"Trade logged: {trade_info}")
