import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
import os
from strategies.rsi_strategy import RSIStrategy
from core.base_trading_strategy import BaseTradingStrategy

class Backtest:
    def __init__(self, config):
        self.config = config
        self.setup_logging()
        self.timeframes = {
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H2': mt5.TIMEFRAME_H2,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1
        }
        self.data_dir = 'backtest/data'
        self.results_dir = 'backtest/results'
        self.ensure_directories()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = 'backtest/logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        self.logger = logging.getLogger('Backtest')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(
            f'{log_dir}/backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
    def ensure_directories(self):
        """Ensure required directories exist"""
        for directory in [self.data_dir, self.results_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                
    def check_symbol(self, symbol: str) -> bool:
        """Check if symbol exists in MT5"""
        # Không gọi mt5.initialize() ở đây, vì đã khởi tạo trong download_data
        try:
            # Get all symbols
            symbols = mt5.symbols_get()
            if symbols is None:
                self.logger.error("Failed to get symbols from MT5")
                return False
                
            # Check if symbol exists
            symbol_exists = any(s.name == symbol for s in symbols)
            if not symbol_exists:
                self.logger.error(f"Symbol {symbol} does not exist in MT5")
                return False
                
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                self.logger.error(f"Failed to get info for symbol {symbol}")
                return False
                
            # Check if symbol is visible
            if not symbol_info.visible:
                if not mt5.symbol_select(symbol, True):
                    self.logger.error(f"Failed to select symbol {symbol}")
                    return False
                    
            self.logger.info(f"Symbol {symbol} is available for trading")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking symbol: {str(e)}")
            return False
                
    def download_data(self, days=300):
        """Download historical data for all timeframes"""
        if not mt5.initialize(
            path=r"C:\Program Files\MetaTrader 5\terminal64.exe",
            login=self.config['mt5']['account'],
            password=self.config['mt5']['password'],
            server=self.config['mt5']['server']
        ):
            error = mt5.last_error()
            self.logger.error(f"Failed to initialize MT5. Error code: {error}")
            self.logger.error("Please make sure:")
            self.logger.error("1. MetaTrader 5 terminal is installed")
            self.logger.error("2. MetaTrader 5 terminal is running")
            self.logger.error("3. You are logged in to your account")
            self.logger.error("4. The path to MT5 terminal is correct")
            return False

        # Kiểm tra trạng thái kết nối
        terminal_info = mt5.terminal_info()
        if not terminal_info:
            error = mt5.last_error()
            self.logger.error(f"Failed to connect to MT5 terminal. Error code: {error}")
            return False
        self.logger.info(f"Connected to MT5 terminal: {terminal_info.name}")

        # Kiểm tra trạng thái đăng nhập
        account_info = mt5.account_info()
        if not account_info:
            error = mt5.last_error()
            self.logger.error(f"Not logged in to MT5 account. Error code: {error}")
            return False
        self.logger.info(f"Logged in as account: {account_info.login}")

        try:
            symbol = self.config['trading']['symbol']
            if not self.check_symbol(symbol):
                return False

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                error = mt5.last_error()
                self.logger.error(f"Failed to get symbol info for {symbol}. Error code: {error}")
                return False
            
            self.logger.info(f"Symbol details:")
            self.logger.info(f"- Name: {symbol_info.name}")
            self.logger.info(f"- Point: {symbol_info.point}")
            self.logger.info(f"- Digits: {symbol_info.digits}")
            self.logger.info(f"- Volume min: {symbol_info.volume_min}")
            self.logger.info(f"- Volume max: {symbol_info.volume_max}")
            self.logger.info(f"- Volume step: {symbol_info.volume_step}")
            
            point = symbol_info.point
            self.logger.info(f"Symbol {symbol} point value: {point}")
            
            for tf_name, tf in self.timeframes.items():
                self.logger.info(f"Downloading {tf_name} data...")
                
                rates = mt5.copy_rates_range(
                    symbol,
                    tf,
                    start_date,
                    end_date
                )
                
                if rates is None:
                    error = mt5.last_error()
                    self.logger.error(f"Failed to get {tf_name} data. Error code: {error}")
                    continue
                    
                if len(rates) == 0:
                    self.logger.error(f"No data received for {tf_name}")
                    continue
                    
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                
                df['spread'] = df['ask'] - df['bid'] if 'ask' in df.columns and 'bid' in df.columns else 0
                df['point'] = point
                
                file_path = f"{self.data_dir}/{tf_name}.csv"
                df.to_csv(file_path, index=False)
                self.logger.info(f"Saved {len(df)} {tf_name} records to {file_path}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error downloading data: {str(e)}")
            return False
            
        finally:
            mt5.shutdown()
            
    def load_data(self):
        """Load historical data from files"""
        data = {}
        missing_timeframes = []
        
        # Check which timeframes are missing
        for tf_name in self.timeframes.keys():
            file_path = f"{self.data_dir}/{tf_name}.csv"
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['time'] = pd.to_datetime(df['time'])
                data[tf_name] = df
                self.logger.info(f"Loaded {tf_name} data from {file_path}")
            else:
                missing_timeframes.append(tf_name)
                self.logger.warning(f"No data file found for {tf_name}")
                
        # Download missing timeframes if any
        if missing_timeframes:
            self.logger.info(f"Downloading missing timeframes: {', '.join(missing_timeframes)}")
            if self.download_data():
                # Reload all data after downloading
                for tf_name in self.timeframes.keys():
                    file_path = f"{self.data_dir}/{tf_name}.csv"
                    if os.path.exists(file_path):
                        df = pd.read_csv(file_path)
                        df['time'] = pd.to_datetime(df['time'])
                        data[tf_name] = df
                        self.logger.info(f"Loaded {tf_name} data from {file_path}")
                        
        return data
        
    def run_backtest(self, strategy_class=RSIStrategy):
        """Run backtest for the strategy"""
        # Load data
        data = self.load_data()
        if not data:
            self.logger.error("No data available for backtest")
            return
            
        # Load strategy configuration
        strategy_config_path = os.path.join(
            self.config['strategies']['config_path'],
            'rsi_strategy.json'
        )
        with open(strategy_config_path, 'r') as f:
            strategy_config = json.load(f)
            
        # Merge configurations
        merged_config = self.config.copy()
        merged_config.update(strategy_config)
            
        # Initialize strategy
        strategy = strategy_class(merged_config)
        
        # Prepare results
        results = {
            'trades': [],
            'equity_curve': [],
            'metrics': {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'total_profit': 0,
                'total_loss': 0
            }
        }
        
        # Get the longest timeframe data for main loop
        main_tf = 'D1'  # Using D1 as main timeframe
        if main_tf not in data:
            self.logger.error(f"Main timeframe {main_tf} data not available")
            return
            
        main_data = data[main_tf]
        initial_balance = self.config['backtest']['initial_balance']
        current_balance = initial_balance
        max_balance = initial_balance
        max_drawdown = 0
        leverage = self.config['mt5']['leverage']
        
        # Run backtest
        for i in range(len(main_data)):
            current_time = main_data.iloc[i]['time']
            
            # Prepare data for current time
            current_data = {}
            for tf_name, df in data.items():
                current_data[tf_name] = df[df['time'] <= current_time].copy()
                
            # Get signals
            signals = strategy.check_signals(current_data)
            
            # Process signals
            for signal in signals:
                # Calculate position size based on leverage and risk
                risk_amount = current_balance * (self.config['trading']['risk_per_trade'] / 100)
                position_size = min(
                    risk_amount * leverage / (signal['sl'] - signal['price']),
                    self.config['trading']['max_position_size']
                )
                position_size = max(position_size, self.config['trading']['min_position_size'])
                
                trade = {
                    'time': current_time,
                    'type': signal['type'],
                    'price': signal['price'],
                    'volume': position_size,
                    'sl': signal['sl'],
                    'tp': signal['tp'],
                    'leverage': leverage
                }
                
                # Calculate profit/loss with leverage
                if signal['type'] == 'BUY':
                    profit = (signal['tp'] - signal['price']) * position_size * leverage
                    loss = (signal['price'] - signal['sl']) * position_size * leverage
                else:  # SELL
                    profit = (signal['price'] - signal['tp']) * position_size * leverage
                    loss = (signal['sl'] - signal['price']) * position_size * leverage
                    
                # Update metrics
                if profit > 0:
                    results['metrics']['winning_trades'] += 1
                    results['metrics']['total_profit'] += profit
                else:
                    results['metrics']['losing_trades'] += 1
                    results['metrics']['total_loss'] += abs(loss)
                    
                results['metrics']['total_trades'] += 1
                trade['profit'] = profit
                trade['loss'] = loss
                results['trades'].append(trade)
                
                # Update balance
                current_balance += profit - loss
                max_balance = max(max_balance, current_balance)
                max_drawdown = max(max_drawdown, (max_balance - current_balance) / max_balance)
                
                results['equity_curve'].append({
                    'time': current_time,
                    'balance': current_balance
                })
                
        # Calculate final metrics
        results['metrics']['win_rate'] = (
            results['metrics']['winning_trades'] / results['metrics']['total_trades']
            if results['metrics']['total_trades'] > 0 else 0
        )
        
        results['metrics']['profit_factor'] = (
            results['metrics']['total_profit'] / results['metrics']['total_loss']
            if results['metrics']['total_loss'] > 0 else float('inf')
        )
        
        results['metrics']['max_drawdown'] = max_drawdown
        
        # Save results
        self.save_results(results)
        
        return results
        
    def save_results(self, results):
        """Save backtest results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save trades
        trades_df = pd.DataFrame(results['trades'])
        trades_file = f"{self.results_dir}/trades_{timestamp}.csv"
        trades_df.to_csv(trades_file, index=False)
        
        # Save equity curve
        equity_df = pd.DataFrame(results['equity_curve'])
        equity_file = f"{self.results_dir}/equity_{timestamp}.csv"
        equity_df.to_csv(equity_file, index=False)
        
        # Save metrics
        metrics_file = f"{self.results_dir}/metrics_{timestamp}.json"
        with open(metrics_file, 'w') as f:
            json.dump(results['metrics'], f, indent=4)
            
        self.logger.info(f"Saved backtest results to {self.results_dir}")
        
def main():
    # Load configuration
    with open('config/config.json', 'r') as f:
        config = json.load(f)
        
    # Update symbol for Exness
    config['trading']['symbol'] = 'XAUUSDm'
        
    # Create backtest instance
    backtest = Backtest(config)
    
    # Run backtest
    backtest.logger.info("Starting backtest...")
    results = backtest.run_backtest()
    
    if results:
        backtest.logger.info("Backtest completed successfully")
        backtest.logger.info(f"Total trades: {results['metrics']['total_trades']}")
        backtest.logger.info(f"Win rate: {results['metrics']['win_rate']:.2%}")
        backtest.logger.info(f"Profit factor: {results['metrics']['profit_factor']:.2f}")
        backtest.logger.info(f"Max drawdown: {results['metrics']['max_drawdown']:.2%}")
    else:
        backtest.logger.error("Backtest failed")
        
if __name__ == "__main__":
    main()
