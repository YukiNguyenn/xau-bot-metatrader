
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

    def load_data(self):
        data = {}
        for tf_name in self.timeframes.keys():
            file_path = f"{self.data_dir}/{tf_name}.csv"
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['time'] = pd.to_datetime(df['time'])
                data[tf_name] = df
                self.logger.info(f"Loaded {tf_name} data from {file_path}")
        return data

    def run_backtest(self, strategy_class=RSIStrategy):
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

        data = self.load_data()
        if not data:
            self.logger.error("No data available for backtest")
            return None

        strategy_config_path = os.path.join(
            self.config['strategies']['config_path'],
            'rsi_strategy.json'
        )
        with open(strategy_config_path, 'r') as f:
            strategy_config = json.load(f)

        merged_config = self.config.copy()
        merged_config['strategy'] = strategy_config['strategy']
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

        main_tf = 'M5'
        if main_tf not in data:
            self.logger.error(f"Main timeframe {main_tf} data not available")
            return None

        main_data = data[main_tf]
        initial_balance = self.config['backtest']['initial_balance']
        current_balance = initial_balance
        max_balance = initial_balance
        max_drawdown = 0
        open_trades = []

        for i in range(1, len(main_data)):
            current_time = main_data.iloc[i]['time']
            current_data = {tf: df[df['time'] <= current_time].copy() for tf, df in data.items()}
            signals = strategy.check_signals(current_data)

            for signal in signals:
                price = signal['price']
                volume = signal['volume']

                if not risk_manager.can_open_position(volume, price):
                    continue

                trade = {
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
                self.logger.info(f"Opened {signal['type']} trade @ {price:.2f}")

            current_price = main_data.iloc[i]['close']
            for trade in open_trades[:]:
                entry = trade['price']
                sl = trade['sl']
                tp = trade['tp']
                volume = trade['volume']
                trade_type = trade['type']
                is_closed = False

                if trade_type == 'BUY':
                    if current_price >= tp:
                        profit = (tp - entry) / point * pip_value * volume
                        current_balance += profit
                        is_closed = True
                    elif current_price <= sl:
                        loss = (entry - sl) / point * pip_value * volume
                        current_balance -= loss
                        risk_manager.update_daily_loss(loss)
                        is_closed = True
                elif trade_type == 'SELL':
                    if current_price <= tp:
                        profit = (entry - tp) / point * pip_value * volume
                        current_balance += profit
                        is_closed = True
                    elif current_price >= sl:
                        loss = (sl - entry) / point * pip_value * volume
                        current_balance -= loss
                        risk_manager.update_daily_loss(loss)
                        is_closed = True

                if is_closed:
                    trade.update({'exit_time': current_time, 'exit_price': current_price, 'profit': current_balance - initial_balance})
                    results['trades'].append(trade)
                    open_trades.remove(trade)
                    risk_manager.update_open_positions(len(open_trades))

            results['equity_curve'].append({
                'time': current_time,
                'balance': current_balance
            })
            max_balance = max(max_balance, current_balance)
            max_drawdown = max(max_drawdown, (max_balance - current_balance) / max_balance if max_balance > 0 else 0)

        self.calculate_metrics(results, max_drawdown)
        self.save_results(results)
        self.logger.info("Backtest completed successfully")
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
