import logging
from datetime import datetime

class RiskManager:
    def __init__(self, config):
        self.config = config
        self.logger = self._setup_logger()
        self.max_open_positions = config.get('max_open_positions', 3)
        self.max_daily_loss = config.get('max_daily_loss', 100)
        self.max_position_size = config.get('max_position_size', 1.0)
        self.min_position_size = config.get('min_position_size', 0.01)
        self.daily_loss = 0
        self.open_positions = 0
        
    def _setup_logger(self):
        """Setup logger for risk manager"""
        logger = logging.getLogger('RiskManager')
        logger.setLevel(logging.INFO)
        
        # Create file handler
        fh = logging.FileHandler(f'logs/risk_manager_{datetime.now().strftime("%Y%m%d")}.log')
        fh.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(fh)
        
        return logger
    
    def can_open_position(self, volume, price):
        """Check if a new position can be opened"""
        # Check max open positions
        if self.open_positions >= self.max_open_positions:
            self.logger.warning("Cannot open position: Maximum open positions reached")
            return False
            
        # Check position size
        if volume > self.max_position_size:
            self.logger.warning(f"Cannot open position: Volume {volume} exceeds maximum {self.max_position_size}")
            return False
            
        if volume < self.min_position_size:
            self.logger.warning(f"Cannot open position: Volume {volume} below minimum {self.min_position_size}")
            return False
            
        # Check daily loss limit
        potential_loss = volume * price * 0.01  # Assuming 1% risk per trade
        if self.daily_loss + potential_loss > self.max_daily_loss:
            self.logger.warning("Cannot open position: Would exceed daily loss limit")
            return False
            
        return True
    
    def update_daily_loss(self, loss):
        """Update the daily loss amount"""
        self.daily_loss += loss
        self.logger.info(f"Updated daily loss: {self.daily_loss}")
        
    def update_open_positions(self, count):
        """Update the number of open positions"""
        self.open_positions = count
        self.logger.info(f"Updated open positions: {self.open_positions}")
        
    def reset_daily_stats(self):
        """Reset daily statistics"""
        self.daily_loss = 0
        self.logger.info("Reset daily statistics")
        
    def calculate_position_size(self, account_balance, risk_per_trade):
        """Calculate position size based on account balance and risk per trade"""
        risk_amount = account_balance * (risk_per_trade / 100)
        position_size = risk_amount / self.config.get('stop_loss_pips', 50)
        
        # Ensure position size is within limits
        position_size = min(position_size, self.max_position_size)
        position_size = max(position_size, self.min_position_size)
        
        return position_size
