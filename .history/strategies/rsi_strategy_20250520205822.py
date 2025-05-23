import numpy as np
  import pandas as pd
  import logging
  from core.base_trading_strategy import BaseTradingStrategy
  from core.indicators import calculate_rsi

  class RSIStrategy(BaseTradingStrategy):
      def __init__(self, config):
          super().__init__(config)
          self.timeframes = config['strategy']['timeframes']
          self.rsi_periods = config['strategy']['parameters']['rsi_periods']
          self.rsi_levels = config['strategy']['parameters']['rsi_levels']
          # Thiết lập logging
          self.logger = logging.getLogger('RSIStrategy')
          self.logger.setLevel(logging.INFO)
          handler = logging.StreamHandler()
          handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
          self.logger.addHandler(handler)
          
      def get_data(self, timeframe: str) -> pd.DataFrame:
          """Get historical data for the specified timeframe"""
          return pd.DataFrame()
          
      def run_strategy(self):
          """Run the strategy in live trading mode"""
          pass
          
      def calculate_rsi(self, data: pd.DataFrame, period: int) -> pd.Series:
          """Calculate RSI using the same method as PineScript (RMA)"""
          src = data['close']
          # Tính giá thay đổi
          change = src.diff()
          # Tách gains và losses
          ups = np.where(change > 0, change, 0)
          downs = np.where(change < 0, -change, 0)
          # Tính RMA (Relative Moving Average)
          ups_rma = pd.Series(ups).ewm(alpha=1/period, min_periods=period).mean()
          downs_rma = pd.Series(downs).ewm(alpha=1/period, min_periods=period).mean()
          # Tính RS và RSI
          rs = ups_rma / downs_rma
          rsi = np.where(downs_rma == 0, 100, np.where(ups_rma == 0, 0, 100 - (100 / (1 + rs))))
          return pd.Series(rsi, index=data.index)
          
      def check_signals(self, data: dict) -> list:
          """Check for trading signals based on RSI values"""
          signals = []
          
          # Calculate RSI for each timeframe
          rsi_values = {}
          for tf in self.timeframes:
              if tf not in data:
                  self.logger.warning(f"No data available for timeframe {tf}")
                  return signals
                  
              if tf not in self.rsi_periods:
                  self.logger.warning(f"No RSI period defined for timeframe {tf}")
                  return signals
                  
              df = data[tf]
              if len(df) < self.rsi_periods[tf]:
                  self.logger.warning(f"Insufficient data for RSI calculation on {tf} (need {self.rsi_periods[tf]} bars, got {len(df)})")
                  return signals
                  
              rsi_values[tf] = self.calculate_rsi(df, self.rsi_periods[tf])
              self.logger.info(f"RSI for {tf}: {rsi_values[tf].iloc[-1]:.2f}")
          
          # Get the latest RSI values
          current_rsi = {tf: rsi_values[tf].iloc[-1] for tf in self.timeframes}
          
          # Check for sell signals (M5 >= 80, M15 >= 70, H1 >= 60)
          if (current_rsi.get('M5', 0) >= self.rsi_levels['M5']['overbought'] and
              current_rsi.get('M15', 0) >= self.rsi_levels['M15']['overbought'] and
              current_rsi.get('H1', 0) >= self.rsi_levels['H1']['overbought']):
              price_data = data['H1']
              signals.append({
                  'type': 'SELL',
                  'volume': self.config['trading']['min_position_size'],
                  'price': price_data['close'].iloc[-1],
                  'sl': price_data['close'].iloc[-1] + self.config['strategy']['parameters']['risk_management']['stop_loss_pips'] * 0.1,
                  'tp': price_data['close'].iloc[-1] - self.config['strategy']['parameters']['risk_management']['take_profit_pips'] * 0.1
              })
              self.logger.info(f"SELL signal generated: Price={price_data['close'].iloc[-1]}, SL={signals[-1]['sl']}, TP={signals[-1]['tp']}")
          
          # Check for buy signals (M5 <= 20, M15 <= 30, H1 <= 40)
          elif (current_rsi.get('M5', 100) <= self.rsi_levels['M5']['oversold'] and
                current_rsi.get('M15', 100) <= self.rsi_levels['M15']['oversold'] and
                current_rsi.get('H1', 100) <= self.rsi_levels['H1']['oversold']):
              price_data = data['H1']
              signals.append({
                  'type': 'BUY',
                  'volume': self.config['trading']['min_position_size'],
                  'price': price_data['close'].iloc[-1],
                  'sl': price_data['close'].iloc[-1] - self.config['strategy']['parameters']['risk_management']['stop_loss_pips'] * 0.1,
                  'tp': price_data['close'].iloc[-1] + self.config['strategy']['parameters']['risk_management']['take_profit_pips'] * 0.1
              })
              self.logger.info(f"BUY signal generated: Price={price_data['close'].iloc[-1]}, SL={signals[-1]['sl']}, TP={signals[-1]['tp']}")
          
          return signals