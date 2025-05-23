import numpy as np
import pandas as pd
from core.base_trading_strategy import BaseTradingStrategy
from core.indicators import calculate_rsi

class RSIStrategy(BaseTradingStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.rsi_periods = config['strategy']['parameters']['rsi_periods']
        self.rsi_levels = config['strategy']['parameters']['rsi_levels']
        
    def get_data(self, timeframe: str) -> pd.DataFrame:
        """Get historical data for the specified timeframe"""
        # This method is not used in backtesting as data is provided directly
        return pd.DataFrame()
        
    def run_strategy(self):
        """Run the strategy in live trading mode"""
        # This method is not used in backtesting
        pass
        
    def calculate_rsi(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate RSI using the same method as PineScript"""
        # Calculate price changes
        delta = data['close'].diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate average gains and losses using RMA (Relative Moving Average)
        avg_gains = gains.ewm(alpha=1/period, min_periods=period).mean()
        avg_losses = losses.ewm(alpha=1/period, min_periods=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
        
    def check_signals(self, data: dict) -> list:
        """Check for trading signals based on RSI values"""
        signals = []
        
        # Get data for each timeframe
        for tf_name, df in data.items():
            if len(df) < max(self.rsi_periods.values()):
                continue
                
            # Calculate RSI for all timeframes
            rsi_short = self.calculate_rsi(df, self.rsi_periods['short'])
            rsi_medium = self.calculate_rsi(df, self.rsi_periods['medium'])
            rsi_long = self.calculate_rsi(df, self.rsi_periods['long'])
            
            # Get the latest values
            current_rsi_short = rsi_short.iloc[-1]
            current_rsi_medium = rsi_medium.iloc[-1]
            current_rsi_long = rsi_long.iloc[-1]
            
            # Check for buy signals (oversold conditions)
            if (current_rsi_short <= self.rsi_levels['short']['oversold'] and
                current_rsi_medium <= self.rsi_levels['medium']['oversold'] and
                current_rsi_long <= self.rsi_levels['long']['oversold']):
                
                signals.append({
                    'type': 'BUY',
                    'volume': self.config['trading']['min_position_size'],
                    'price': df['close'].iloc[-1],
                    'sl': df['close'].iloc[-1] - self.config['strategy']['parameters']['risk_management']['stop_loss_pips'] * 0.1,
                    'tp': df['close'].iloc[-1] + self.config['strategy']['parameters']['risk_management']['take_profit_pips'] * 0.1
                })
                
            # Check for sell signals (overbought conditions)
            elif (current_rsi_short >= self.rsi_levels['short']['overbought'] and
                  current_rsi_medium >= self.rsi_levels['medium']['overbought'] and
                  current_rsi_long >= self.rsi_levels['long']['overbought']):
                
                signals.append({
                    'type': 'SELL',
                    'volume': self.config['trading']['min_position_size'],
                    'price': df['close'].iloc[-1],
                    'sl': df['close'].iloc[-1] + self.config['strategy']['parameters']['risk_management']['stop_loss_pips'] * 0.1,
                    'tp': df['close'].iloc[-1] - self.config['strategy']['parameters']['risk_management']['take_profit_pips'] * 0.1
                })
                
        return signals 