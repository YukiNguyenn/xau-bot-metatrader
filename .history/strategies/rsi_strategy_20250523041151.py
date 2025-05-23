import numpy as np
import pandas as pd
import logging
from core.base_trading_strategy import BaseTradingStrategy
from core.indicators import calculate_rsi  # Nếu có sẵn
from datetime import datetime

class RSIStrategy(BaseTradingStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.rsi_periods = config['strategy']['parameters']['rsi_periods']  # short, medium, long
        self.rsi_levels = config['strategy']['parameters']['rsi_levels']
        self.risk = config['strategy']['parameters']['risk_management']
        self.trading = config.get('trading', {})

        # Logging
        self.logger = logging.getLogger('RSIStrategy')
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def get_data(self, timeframe: str) -> pd.DataFrame:
        """Lấy dữ liệu thị trường theo timeframe"""
        return self.data_manager.fetch_data(timeframe)

    def run_strategy(self):
        """Fetch dữ liệu và kiểm tra tín hiệu giao dịch"""
        try:
            data = {}
            for tf in self.timeframes:
                df = self.get_data(tf)
                if df is not None and not df.empty:
                    data[tf] = df
                else:
                    self.logger.warning(f"No data returned for {tf}")

            signals = self.check_signals(data)
            for signal in signals:
                entry_price = signal['price']
                sl = signal['sl']
                tp = self.risk_manager.calculate_take_profit(entry_price, sl)
                volume = self.risk_manager.calculate_position_size(entry_price, sl)

                order_type = (
                    mt5.ORDER_TYPE_BUY if signal['type'] == 'BUY'
                    else mt5.ORDER_TYPE_SELL
                )

                self.trade_manager.place_order(
                    order_type=order_type,
                    volume=volume,
                    price=entry_price,
                    sl=sl,
                    tp=tp,
                    strategy_name=self.__class__.__name__
                )

        except Exception as e:
            self.logger.error(f"Error running strategy: {str(e)}")

    def calculate_rsi(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Tính RSI chuẩn RMA (giống Pine Script)"""
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
        """Kiểm tra tín hiệu giao dịch trên các timeframe"""
        signals = []

        for tf in self.timeframes:
            if tf not in data:
                self.logger.warning(f"No data for timeframe {tf}")
                continue

            df = data[tf]
            if len(df) < max(self.rsi_periods.values()):
                self.logger.warning(f"Insufficient data for timeframe {tf}")
                continue

            rsi_short = self.calculate_rsi(df, self.rsi_periods['short']).iloc[-1]
            rsi_medium = self.calculate_rsi(df, self.rsi_periods['medium']).iloc[-1]
            rsi_long = self.calculate_rsi(df, self.rsi_periods['long']).iloc[-1]

            self.logger.info(f"{tf} RSI - Short: {rsi_short:.2f}, Medium: {rsi_medium:.2f}, Long: {rsi_long:.2f}")
            price = df['close'].iloc[-1]

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
