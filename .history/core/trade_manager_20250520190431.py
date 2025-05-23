import logging
from datetime import datetime
import MetaTrader5 as mt5

class TradeManager:
    def __init__(self, config):
        self.config = config
        self.logger = self._setup_logger()
        self.symbol = "XAUUSD"
        self.initialize_mt5()
        
    def _setup_logger(self):
        """Setup logger for trade manager"""
        logger = logging.getLogger('TradeManager')
        logger.setLevel(logging.INFO)
        
        # Create file handler
        fh = logging.FileHandler(f'logs/trade_manager_{datetime.now().strftime("%Y%m%d")}.log')
        fh.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(fh)
        
        return logger
        
    def initialize_mt5(self):
        """Initialize MetaTrader 5 connection"""
        if not mt5.initialize():
            self.logger.error("Failed to initialize MT5")
            return False
            
        # Login to MT5 account
        login = self.config.get('mt5_login')
        password = self.config.get('mt5_password')
        server = self.config.get('mt5_server')
        
        if not mt5.login(login, password, server):
            self.logger.error("Failed to login to MT5 account")
            return False
            
        self.logger.info("Successfully connected to MT5")
        return True
        
    def place_order(self, order_type, volume, price=None, sl=None, tp=None):
        """Place a new order"""
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "deviation": 20,
            "magic": 234000,
            "comment": "python script",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        if price:
            request["price"] = price
        if sl:
            request["sl"] = sl
        if tp:
            request["tp"] = tp
            
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self.logger.error(f"Order failed: {result.comment}")
            return None
            
        self.logger.info(f"Order placed successfully: {result.order}")
        return result.order
        
    def close_position(self, position_id):
        """Close an existing position"""
        position = mt5.positions_get(ticket=position_id)
        if not position:
            self.logger.error(f"Position {position_id} not found")
            return False
            
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": position[0].volume,
            "type": mt5.ORDER_TYPE_SELL if position[0].type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "position": position_id,
            "deviation": 20,
            "magic": 234000,
            "comment": "python script close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self.logger.error(f"Close position failed: {result.comment}")
            return False
            
        self.logger.info(f"Position {position_id} closed successfully")
        return True
        
    def get_open_positions(self):
        """Get all open positions"""
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            self.logger.error("Failed to get positions")
            return []
            
        return positions
        
    def get_position_info(self, position_id):
        """Get information about a specific position"""
        position = mt5.positions_get(ticket=position_id)
        if not position:
            return None
            
        return {
            'ticket': position[0].ticket,
            'type': position[0].type,
            'volume': position[0].volume,
            'price_open': position[0].price_open,
            'price_current': position[0].price_current,
            'sl': position[0].sl,
            'tp': position[0].tp,
            'profit': position[0].profit
        }
        
    def __del__(self):
        """Cleanup when object is destroyed"""
        mt5.shutdown() 