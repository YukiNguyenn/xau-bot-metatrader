import numpy as np
import pandas as pd
import logging
from core.base_trading_strategy import BaseTradingStrategy
from core.indicators import calculate_rsi  # Nếu bạn có sẵn, không thì dùng self.calculate_rsi()

class RSIStrategy(BaseTradingStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.timeframes = config['strategy']['timeframes']
        self.rsi_periods = config['strategy']['parameters']['rsi_periods']  # short, medium, long
        self.rsi_levels = config['strategy']['parameters']['rsi_levels']
        self.risk = config['strategy']['parameters']['risk_management']
        self.trading = config.get('trading', {})

        # Thiết lập logging
        self.logger = logging.getLogger('RSIStrategy')
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        if not self.logger.handlers:
            self.logger.addHandler(handler)


    def run_strategy(self):
        """Chạy chiến lược (chưa implement trong ví dụ này)"""
        pass

    def calculate_rsi(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Tính RSI theo chuẩn RMA như trong Pine Script"""
        src = data['close']
        change = src.diff()
        ups = np.where(change > 0, change, 0)
        downs = np.where(change < 0, -change, 0)
        ups_rma = pd.Series(ups).ewm(alpha=1 / period, min_periods=period).mean()
        downs_rma = pd.Series(downs).ewm(alpha=1 / period, min_periods=period).mean()
        rs = ups_rma / downs_rma
        rsi = np.where(downs_rma == 0, 100, np.where(ups_rma == 0, 0, 100 - (100 / (1 + rs))))
        return pd.Series(rsi, index=data.index)

    def check_signals(self, data: dict) -> list:
        """Kiểm tra tín hiệu giao dịch dựa trên 3 RSI (short/medium/long) trên mỗi timeframe"""
        signals = []

        for tf in self.timeframes:
            if tf not in data:
                self.logger.warning(f"No data for timeframe {tf}")
                continue

            df = data[tf]
            if len(df) < max(self.rsi_periods.values()):
                self.logger.warning(f"Insufficient data for timeframe {tf}")
                continue

            # Tính RSI
            rsi_short = self.calculate_rsi(df, self.rsi_periods['short']).iloc[-1]
            rsi_medium = self.calculate_rsi(df, self.rsi_periods['medium']).iloc[-1]
            rsi_long = self.calculate_rsi(df, self.rsi_periods['long']).iloc[-1]

            self.logger.info(f"{tf} RSI - Short: {rsi_short:.2f}, Medium: {rsi_medium:.2f}, Long: {rsi_long:.2f}")

            price = df['close'].iloc[-1]

            # SELL
            if (rsi_short >= self.rsi_levels['short']['overbought'] and
                rsi_medium >= self.rsi_levels['medium']['overbought'] and
                rsi_long >= self.rsi_levels['long']['overbought']):
                signals.append({
                    'type': 'SELL',
                    'volume': self.trading.get('min_position_size', 0.01),
                    'price': price,
                    'sl': price + self.risk['stop_loss_pips'] * 0.1,
                    'tp': price - self.risk['take_profit_pips'] * 0.1,
                    'timeframe': tf
                })
                self.logger.info(f"SELL signal on {tf} @ {price:.2f}")

            # BUY
            elif (rsi_short <= self.rsi_levels['short']['oversold'] and
                  rsi_medium <= self.rsi_levels['medium']['oversold'] and
                  rsi_long <= self.rsi_levels['long']['oversold']):
                signals.append({
                    'type': 'BUY',
                    'volume': self.trading.get('min_position_size', 0.01),
                    'price': price,
                    'sl': price - self.risk['stop_loss_pips'] * 0.1,
                    'tp': price + self.risk['take_profit_pips'] * 0.1,
                    'timeframe': tf
                })
                self.logger.info(f"BUY signal on {tf} @ {price:.2f}")

        return signals
