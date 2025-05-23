from abc import ABC, abstractmethod

class BaseTradeManager(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def place_order(self, order_type, volume, price=None, sl=None, tp=None):
        pass

    @abstractmethod
    def close_position(self, position_id):
        pass

    @abstractmethod
    def get_open_positions(self):
        pass
