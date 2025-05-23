import numpy as np
import pandas as pd
from core.base_trading_strategy import BaseTradingStrategy
from core.indicators import calculate_rsi

class RSIStrategy(BaseTradingStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.timeframes = config['strategy']['timeframes']
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
        
        # Calculate RSI for each timeframe
        rsi_values = {}
        for tf in self.timeframes:
            if tf not in data:
                continue
                
            df = data[tf]
            if len(df) < self.rsi_periods[tf]:
                continue
                
            rsi_values[tf] = self.calculate_rsi(df, self.rsi_periods[tf])
            
        # Check if we have RSI values for all timeframes
        if len(rsi_values) != len(self.timeframes):
            return signals
            
        # Get the latest RSI values
        current_rsi = {
            tf: rsi_values[tf].iloc[-1]
            for tf in self.timeframes
        }
        
        # Check for sell signals (all timeframes overbought)
        if all(current_rsi[tf] >= self.rsi_levels[tf]['overbought'] for tf in self.timeframes):
            # Use H1 timeframe for price data
            price_data = data['H1']
            signals.append({
                'type': 'SELL',
                'volume': self.config['trading']['min_position_size'],
                'price': price_data['close'].iloc[-1],
                'sl': price_data['close'].iloc[-1] + self.config['strategy']['parameters']['risk_management']['stop_loss_pips'] * 0.1,
                'tp': price_data['close'].iloc[-1] - self.config['strategy']['parameters']['risk_management']['take_profit_pips'] * 0.1
            })
            
        # Check for buy signals (all timeframes oversold)
        elif all(current_rsi[tf] <= self.rsi_levels[tf]['oversold'] for tf in self.timeframes):
            # Use H1 timeframe for price data
            price_data = data['H1']
            signals.append({
                'type': 'BUY',
                'volume': self.config['trading']['min_position_size'],
                'price': price_data['close'].iloc[-1],
                'sl': price_data['close'].iloc[-1] - self.config['strategy']['parameters']['risk_management']['stop_loss_pips'] * 0.1,
                'tp': price_data['close'].iloc[-1] + self.config['strategy']['parameters']['risk_management']['take_profit_pips'] * 0.1
            })
            
        return signals 