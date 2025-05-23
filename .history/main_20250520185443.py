import json
import logging
import os
from datetime import datetime
from strategy_manager import StrategyManager
from strategies.moving_average_strategy import MovingAverageStrategy

def load_config():
    """Load configuration from file"""
    config_path = os.path.join('config', 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return None

def setup_logging(config):
    """Setup logging configuration"""
    log_dir = config['logging']['log_directory']
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    logging.basicConfig(
        level=getattr(logging, config['logging']['level']),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(
                os.path.join(log_dir, f'trading_system_{datetime.now().strftime("%Y%m%d")}.log')
            ),
            logging.StreamHandler()
        ]
    )

def main():
    """Main entry point"""
    # Load configuration
    config = load_config()
    if not config:
        return
        
    # Setup logging
    setup_logging(config)
    logger = logging.getLogger('main')
    
    try:
        # Initialize strategy manager
        strategy_manager = StrategyManager(config)
        
        # Add strategies
        if 'MovingAverageStrategy' in config['strategies']['enabled']:
            ma_strategy = MovingAverageStrategy(config)
            strategy_manager.add_strategy(ma_strategy)
            
        # Start trading
        logger.info("Starting trading system...")
        strategy_manager.start()
        
        # Keep the main thread alive
        try:
            while True:
                # Get and log strategy status
                status = strategy_manager.get_strategy_status()
                logger.info(f"Strategy status: {status}")
                
                # Sleep for a while
                import time
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            
        finally:
            # Stop trading
            logger.info("Stopping trading system...")
            strategy_manager.stop()
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        
if __name__ == '__main__':
    main()
