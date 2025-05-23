import MetaTrader5 as mt5
import json
import logging
from datetime import datetime
from strategy_manager import StrategyManager
from strategies.rsi_strategy import RSIStrategy

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/main_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('Main')

def load_config():
    """Load configuration from config file"""
    try:
        with open('config/config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"Failed to load config: {str(e)}")

def initialize_mt5(config):
    """Initialize MetaTrader 5 connection"""
    if not mt5.initialize():
        raise Exception("Failed to initialize MT5")
        
    # Login to MT5 account
    if not mt5.login(
        login=config['mt5']['account'],
        password=config['mt5']['password'],
        server=config['mt5']['server']
    ):
        raise Exception("Failed to login to MT5 account")
        
    return True

def main():
    # Setup logging
    logger = setup_logging()
    logger.info("Starting XAU Trading Bot")
    
    try:
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Initialize MT5
        initialize_mt5(config)
        logger.info("MT5 initialized successfully")
        
        # Create strategy manager
        strategy_manager = StrategyManager(config)
        
        # Add RSI strategy
        with open("config/strategies/rsi_strategy.json", "r") as f:
            strategy_config = json.load(f)
        config["strategy"] = strategy_config
        rsi_strategy = RSIStrategy(config)
        strategy_manager.add_strategy(rsi_strategy)
        logger.info("RSI Strategy added successfully")
        
        # Start trading
        strategy_manager.start()
        logger.info("Trading started")
        
        # Keep the main thread running
        try:
            while True:
                pass
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            strategy_manager.stop()
            logger.info("Trading stopped")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise
    finally:
        # Shutdown MT5
        mt5.shutdown()
        logger.info("MT5 shutdown complete")

if __name__ == "__main__":
    main()
