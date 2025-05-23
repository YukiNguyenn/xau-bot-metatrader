
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
import os
import time

from strategies.rsi_strategy import RSIStrategy
from core.base_trading_strategy import BaseTradingStrategy
from core.risk_manager import RiskManager
from core.simulated_trade_manager import SimulatedTradeManager
from core.trade_manager import TradeManager as LiveTradeManager

class Backtest:
    def __init__(self, config):
        self.config = config
        self.setup_logging()
        self.timeframes = {
            'M1': mt5.TIMEFRAME_M1,
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
        log_dir = 'backtest/logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.logger = logging.getLogger('Backtest')
        self.logger.setLevel(logging.INFO)
        fh = logging.FileHandler(f'{log_dir}/backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        fh.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def ensure_directories(self):
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

    @staticmethod
    def generate_m1_date_ranges(total_days=300, parts=5):
        end = datetime.now()
        start = end - timedelta(days=total_days)
        delta_per_part = (end - start) / parts

        ranges = []
        for i in range(parts):
            part_start = start + i * delta_per_part
            part_end = start + (i + 1) * delta_per_part
            ranges.append((part_start, part_end))

        return ranges
                
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

        # Thêm độ trễ để đảm bảo kết nối ổn định
        time.sleep(1)  # Chờ 1 giây sau khi khởi tạo

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
            
            # Thêm độ trễ trước khi gọi symbol_info
            time.sleep(0.5)  # Chờ 0.5 giây
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
                all_data = []

                if tf_name == 'M1':
                    ranges = self.generate_m1_date_ranges(total_days=days, parts=5)
                    for i, (start, end) in enumerate(ranges):
                        self.logger.info(f" - M1 part {i+1}/{len(ranges)}: {start} -> {end}")
                        self.logger.info(f"Downloaded {len(rates)} bars for part {i+1}")

                        rates = mt5.copy_rates_range(symbol, tf, start, end)
                        if rates is None or len(rates) == 0:
                            self.logger.warning(f"No M1 data received for range {start} to {end}")
                            continue
                        part_df = pd.DataFrame(rates)
                        part_df['time'] = pd.to_datetime(part_df['time'], unit='s')
                        part_df['spread'] = part_df['ask'] - part_df['bid'] if 'ask' in part_df.columns and 'bid' in part_df.columns else 0
                        part_df['point'] = point
                        all_data.append(part_df)
                    if all_data:
                        df = pd.concat(all_data).drop_duplicates(subset='time').sort_values('time')
                    else:
                        self.logger.warning("No M1 data collected in total.")
                        continue
                else:
                    rates = mt5.copy_rates_range(symbol, tf, start_date, end_date)
                    if rates is None or len(rates) == 0:
                        self.logger.warning(f"No data received for {tf_name}")
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
        # Initialize MT5 to get symbol info
        if not mt5.initialize(
            path=r"C:\Program Files\MetaTrader 5\terminal64.exe",
            login=self.config['mt5']['account'],
            password=self.config['mt5']['password'],
            server=self.config['mt5']['server']
        ):
            self.logger.error("Failed to initialize MT5 for symbol info")
            return None

        symbol_info = mt5.symbol_info(self.config['trading']['symbol'])
        if symbol_info is None:
            self.logger.error(f"Failed to get symbol info for {self.config['trading']['symbol']}")
            mt5.shutdown()
            return None

        point = symbol_info.point
        pip_value = symbol_info.trade_tick_value
        mt5.shutdown()

        # Load data
        data = self.load_data()
        if not data:
            self.logger.error("No data available for backtest")
            return None

        # Load strategy configuration
        strategy_config_path = os.path.join(
            self.config['strategies']['config_path'],
            'rsi_strategy.json'
        )
        with open(strategy_config_path, 'r') as f:
            strategy_config = json.load(f)

        # Merge configurations
        merged_config = self.config.copy()
        merged_config['strategy'] = strategy_config['strategy']

        # Initialize strategy
        strategy = strategy_class(merged_config)

        risk_manager = RiskManager(self.config['trading'])
        if self.config.get("mode", "backtest") == "live":
            trade_manager = LiveTradeManager(self.config['mt5'])
        else:
            trade_manager = SimulatedTradeManager(self.config['trading'])

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

        main_tf = 'M1'
        if main_tf not in data:
            self.logger.error(f"Main timeframe {main_tf} data not available")
            return None

        main_data = data[main_tf]
        initial_balance = self.config['backtest']['initial_balance']
        current_balance = initial_balance
        max_balance = initial_balance
        max_drawdown = 0
        open_trades = []

        # Run backtest
        for i in range(1, len(main_data)):
            current_time = main_data.iloc[i]['time']
            # Prepare data for current time
            current_data = {tf: df[df['time'] <= current_time].copy() for tf, df in data.items()}

            # Get signals
            signals = strategy.check_signals(current_data)

            min_required_bars = max(strategy.rsi_periods.values())
            if any(len(df) < min_required_bars for df in current_data.values()):
                continue
            
            # Process new signals
            for signal in signals:
                price = signal['price']
                pip_distance = abs(signal['sl'] - price) / point
                if pip_distance == 0:
                    continue

                risk_amount = current_balance * (self.config['trading']['risk_per_trade'] / 100)
                volume = min(
                    risk_amount / (pip_distance * pip_value),
                    self.config['trading']['max_position_size']
                )
                volume = max(volume, self.config['trading']['min_position_size'])

                if not risk_manager.can_open_position(volume, price):
                    continue

                order_id = trade_manager.place_order(
                    order_type=signal['type'],
                    volume=volume,
                    price=price,
                    sl=signal['sl'],
                    tp=signal['tp']
                )

                if order_id:
                    trade = {
                        'order_id': order_id,
                        'time': current_time,
                        'type': signal['type'],
                        'price': price,
                        'volume': volume,
                        'sl': signal['sl'],
                        'tp': signal['tp'],
                        'leverage': self.config['mt5']['leverage']
                    }
                    open_trades.append(trade)
                    risk_manager.update_open_positions(len(open_trades))
                    self.logger.info(f"Simulated trade Opened {signal['type']} @: Time={current_time}, Price={signal['price']:.2f}, Volume={volume:.2f}, SL={signal['sl']:.2f}, TP={signal['tp']:.2f}")

            current_price = main_data.iloc[i]['close']

            # Check open trades
            for trade in open_trades[:]:
                entry = trade['price']
                sl = trade['sl']
                tp = trade['tp']
                volume = trade['volume']
                trade_type = trade['type']

                if trade_type == 'BUY':
                    if current_price >= tp:
                        profit = (tp - entry) / point * pip_value * volume
                        current_balance += profit
                        trade.update({'exit_price': tp, 'exit_time': current_time, 'profit': profit})
                        results['trades'].append(trade)
                        open_trades.remove(trade)
                        self.logger.info(f"Closed BUY trade: Profit={profit:.2f}, Balance={current_balance:.2f}")
                    elif current_price <= sl:
                        loss = (entry - sl) / point * pip_value * volume
                        current_balance -= loss
                        trade.update({'exit_price': sl, 'exit_time': current_time, 'profit': -loss})
                        results['trades'].append(trade)
                        open_trades.remove(trade)
                        self.logger.info(f"Closed BUY trade: Loss={loss:.2f}, Balance={current_balance:.2f}")

                elif trade_type == 'SELL':
                    if current_price <= tp:
                        profit = (entry - tp) / point * pip_value * volume
                        current_balance += profit
                        trade.update({'exit_price': tp, 'exit_time': current_time, 'profit': profit})
                        results['trades'].append(trade)
                        open_trades.remove(trade)
                        self.logger.info(f"Closed SELL trade: Profit={profit:.2f}, Balance={current_balance:.2f}")
                    elif current_price >= sl:
                        loss = (sl - entry) / point * pip_value * volume
                        current_balance -= loss
                        trade.update({'exit_price': sl, 'exit_time': current_time, 'profit': -loss})
                        results['trades'].append(trade)
                        open_trades.remove(trade)
                        self.logger.info(f"Closed SELL trade: Loss={loss:.2f}, Balance={current_balance:.2f}")

                # Cập nhật lại số lệnh mở sau khi xử lý
                risk_manager.update_open_positions(len(open_trades))


            results['equity_curve'].append({
                'time': current_time,
                'balance': current_balance
            })

            if current_balance <= 0:
                self.logger.warning(f"Account balance depleted at {current_time}. Backtest stopped.")
                break

            max_balance = max(max_balance, current_balance)
            max_drawdown = max(max_drawdown, (max_balance - current_balance) / max_balance if max_balance > 0 else 0)

        self.calculate_metrics(results, max_drawdown)
        self.save_results(results)
        return results

    def calculate_metrics(self, results, max_drawdown):
        results['metrics']['total_trades'] = len(results['trades'])
        results['metrics']['winning_trades'] = len([t for t in results['trades'] if t['profit'] > 0])
        results['metrics']['losing_trades'] = len([t for t in results['trades'] if t['profit'] < 0])
        results['metrics']['total_profit'] = sum(t['profit'] for t in results['trades'] if t['profit'] > 0)
        results['metrics']['total_loss'] = abs(sum(t['profit'] for t in results['trades'] if t['profit'] < 0))
        results['metrics']['win_rate'] = (
            results['metrics']['winning_trades'] / results['metrics']['total_trades']
            if results['metrics']['total_trades'] > 0 else 0
        )
        results['metrics']['profit_factor'] = (
            results['metrics']['total_profit'] / results['metrics']['total_loss']
            if results['metrics']['total_loss'] > 0 else float('inf')
        )
        results['metrics']['max_drawdown'] = max_drawdown

    def save_results(self, results):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trades_df = pd.DataFrame(results['trades'])
        trades_df.to_csv(f"{self.results_dir}/trades_{timestamp}.csv", index=False)
        equity_df = pd.DataFrame(results['equity_curve'])
        equity_df.to_csv(f"{self.results_dir}/equity_{timestamp}.csv", index=False)
        with open(f"{self.results_dir}/metrics_{timestamp}.json", 'w') as f:
            json.dump(results['metrics'], f, indent=4)
        self.logger.info(f"Saved backtest results to {self.results_dir}")

def main():
    with open('config/config.json', 'r') as f:
        config = json.load(f)
    config['trading']['symbol'] = 'XAUUSDm'
    backtest = Backtest(config)
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
