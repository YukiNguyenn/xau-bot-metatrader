import uuid
import logging
from datetime import datetime
from core.base_trade_manager import BaseTradeManager

class SimulatedTradeManager(BaseTradeManager):
    def __init__(self, config):
        super().__init__(config)
        self.logger = self._setup_logger()
        self.positions = []

    def _setup_logger(self):
        logger = logging.getLogger('SimulatedTradeManager')
        logger.setLevel(logging.INFO)
        return logger

    def place_order(self, order_type, volume, price=None, sl=None, tp=None):
        order_id = str(uuid.uuid4())  # Random order ID
        position = {
            'id': order_id,
            'type': order_type,
            'volume': volume,
            'price_open': price,
            'sl': sl,
            'tp': tp,
            'open_time': datetime.now(),
        }
        self.positions.append(position)
        self.logger.info(f"[SIM] Order placed: {order_type} @ {price} Vol={volume}")
        return order_id

    def close_position(self, position_id):
        self.positions = [p for p in self.positions if p['id'] != position_id]
        self.logger.info(f"[SIM] Closed position {position_id}")
        return True

    def get_open_positions(self):
        return self.positions
