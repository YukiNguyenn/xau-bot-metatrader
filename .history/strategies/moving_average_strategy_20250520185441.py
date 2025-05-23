import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from core.base_trading_strategy import BaseTradingStrategy
import time

class MovingAverageStrategy(BaseTradingStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.fast_period = config.get('fast_period', 10)
        self.slow_period = config.get('slow_period', 20)
        
    def get_data(self, timeframe='1h', limit=1000):
        """Get historical data and calculate indicators"""
        # Convert timeframe string to MT5 timeframe
        tf_map = {
            '1m': mt5.TIMEFRAME_M1,
            '5m': mt5.TIMEFRAME_M5,
            '15m': mt5.TIMEFRAME_M15,
            '30m': mt5.TIMEFRAME_M30,
            '1h': mt5.TIMEFRAME_H1,
            '4h': mt5.TIMEFRAME_H4,
            '1d': mt5.TIMEFRAME_D1
        }
        
        mt5_timeframe = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
        
        # Get historical data
        rates = mt5.copy_rates_from_pos(self.config['trading']['symbol'], mt5_timeframe, 0, limit)
        if rates is None:
            self.logger.error("Failed to get historical data")
            return None
            
        # Convert to pandas DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Calculate moving averages
        df['fast_ma'] = df['close'].rolling(window=self.fast_period).mean()
        df['slow_ma'] = df['close'].rolling(window=self.slow_period).mean()
        
        return df
        
    def check_signals(self, data):
        """Check for trading signals based on moving average crossover"""
        if data is None or len(data) < self.slow_period:
            return []
            
        signals = []
        
        # Get the last two rows for crossover detection
        current = data.iloc[-1]
        previous = data.iloc[-2]
        
        # Check for bullish crossover
        if (previous['fast_ma'] <= previous['slow_ma'] and 
            current['fast_ma'] > current['slow_ma']):
            signals.append({
                'type': mt5.ORDER_TYPE_BUY,
                'volume': self.calculate_position_size(),
                'price': current['close'],
                'sl': current['close'] - self.config['trading']['stop_loss_pips'] * 0.1,
                'tp': current['close'] + self.config['trading']['take_profit_pips'] * 0.1
            })
            
        # Check for bearish crossover
        elif (previous['fast_ma'] >= previous['slow_ma'] and 
              current['fast_ma'] < current['slow_ma']):
            signals.append({
                'type': mt5.ORDER_TYPE_SELL,
                'volume': self.calculate_position_size(),
                'price': current['close'],
                'sl': current['close'] + self.config['trading']['stop_loss_pips'] * 0.1,
                'tp': current['close'] - self.config['trading']['take_profit_pips'] * 0.1
            })
            
        return signals
        
    def calculate_position_size(self):
        """Calculate position size based on risk management"""
        account_info = mt5.account_info()
        if account_info is None:
            return self.config['trading']['min_position_size']
            
        balance = account_info.balance
        risk_amount = balance * (self.config['trading']['risk_per_trade'] / 100)
        position_size = risk_amount / (self.config['trading']['stop_loss_pips'] * 0.1)
        
        # Ensure position size is within limits
        position_size = min(position_size, self.config['trading']['max_position_size'])
        position_size = max(position_size, self.config['trading']['min_position_size'])
        
        return position_size
        
    def run_strategy(self):
        """Run the strategy"""
        while True:
            try:
                # Get market data
                data = self.get_data()
                
                # Check for signals
                signals = self.check_signals(data)
                
                # Process signals
                for signal in signals:
                    self.logger.info(f"Signal detected: {signal}")
                    
                # Sleep for the configured interval
                time.sleep(self.config['strategies']['interval'])
                
            except Exception as e:
                self.logger.error(f"Error in strategy: {str(e)}")
                time.sleep(5)  # Wait before retrying 