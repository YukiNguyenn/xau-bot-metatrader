"""
Strategy Manager

This module provides a centralized manager for running multiple trending strategies
concurrently in separate threads. It handles strategy initialization, data fetching,
execution, and proper cleanup of resources.
"""

import logging
from datetime import datetime
import threading
import time
import json
import os
from typing import List, Dict
from core.base_trading_strategy import BaseTradingStrategy
from strategies.rsi_strategy import RSIStrategy

from core.trade_manager import TradeManager
from core.risk_manager import RiskManager

class StrategyManager:
    def __init__(self, config):
        self.config = config
        self.logger = self._setup_logger()
        self.strategies: Dict[str, BaseTradingStrategy] = {}
        self.trade_manager = TradeManager(config)
        self.risk_manager = RiskManager(config)
        self.running = False
        self.threads = []

        self.data_manager = DataManager(
            symbol=config['trading']['symbol'],
            timeframes=config['support_timeframes'],
            logger=self.logger
        )
        
    def _setup_logger(self):
        """Setup logger for strategy manager"""
        logger = logging.getLogger('StrategyManager')
        logger.setLevel(logging.INFO)
        
        # Create file handler
        fh = logging.FileHandler(f'logs/strategy_manager_{datetime.now().strftime("%Y%m%d")}.log')
        fh.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(fh)
        
        return logger
        
    def _load_strategy_config(self, strategy_name: str) -> dict:
        """Load configuration for a specific strategy"""
        config_path = os.path.join(
            self.config['strategies']['config_path'],
            f"{strategy_name.lower()}.json"
        )
        
        try:
            with open(config_path, 'r') as f:
                strategy_config = json.load(f)
                
            # Merge with main config
            merged_config = self.config.copy()
            merged_config['strategy'] = strategy_config
            
            return merged_config
            
        except Exception as e:
            self.logger.error(f"Failed to load config for {strategy_name}: {str(e)}")
            return self.config
        
    def add_strategy(self, strategy_name: str):
        """Add a trading strategy to the manager"""
        strategy_config = self._load_strategy_config(strategy_name)
        self.logger.info(strategy_config)
        # Import và khởi tạo class từ tên
        if strategy_name == "rsi_strategy":
            strategy_instance = RSIStrategy(strategy_config)
        else:
            raise ValueError(f"Unsupported strategy: {strategy_name}")

        self.strategies[strategy_name] = strategy_instance
        self.logger.info(f"Strategy '{strategy_name}' loaded and initialized.")
        
        self.logger.info(f"Added strategy: {strategy_name}")
        
    def remove_strategy(self, strategy_name: str):
        """Remove a trading strategy from the manager"""
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            self.logger.info(f"Removed strategy: {strategy_name}")

    def fetch_all_data(self):
        """
        Lấy toàn bộ dữ liệu từ data_manager (tất cả timeframe)
        """
        return self.data_manager.fetch_all()

    def _run_strategy(self, strategy: BaseTradingStrategy):
        """Run a single strategy in a loop"""
        while self.running:
            try:
                all_data = self.fetch_all_data()  # ✅ lấy toàn bộ dữ liệu mới nhất
                data = {tf: all_data[tf] for tf in strategy.timeframes if tf in all_data}
                strategy.run_strategy(data)
                
                # Sleep for the strategy's interval
                time.sleep(strategy.config.get('interval', 60))
                
            except Exception as e:
                self.logger.error(f"Error in strategy {strategy.__class__.__name__}: {str(e)}")
                time.sleep(5)  # Wait before retrying
                
    def start(self):
        """Start all strategies"""
        if self.running:
            self.logger.warning("Strategy manager is already running")
            return
            
        self.running = True
        self.threads = []
        
        for strategy in self.strategies.values():
            thread = threading.Thread(
                target=self._run_strategy,
                args=(strategy,),
                name=strategy.__class__.__name__
            )
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
            self.logger.info(f"Started strategy: {strategy.__class__.__name__}")
            
    def stop(self):
        """Stop all strategies"""
        if not self.running:
            self.logger.warning("Strategy manager is not running")
            return
            
        self.running = False
        
        # Wait for all threads to finish
        for thread in self.threads:
            thread.join()
            
        self.threads = []
        self.logger.info("All strategies stopped")
        
    def get_strategy_status(self) -> Dict:
        """Get the status of all strategies"""
        return {
            name: {
                'running': self.running,
                'thread_alive': thread.is_alive() if thread else False
            }
            for name, thread in zip(self.strategies.keys(), self.threads)
        }