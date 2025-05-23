# import MetaTrader5 as mt5
# from datetime import datetime, timedelta

# mt5.initialize()
# symbol = "XAUUSDm"
# end_date = datetime.now() - timedelta(days=120)
# start_date = end_date - timedelta(days=60)
# rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start_date, end_date)
# print(f"Retrieved {len(rates) if rates is not None else 'None'} M5 bars for {symbol} from {start_date} to {end_date}")

# mt5.shutdown()

import MetaTrader5 as mt5
from datetime import datetime

mt5.initialize()
symbol = "XAUUSDm"
rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, datetime.now(), 99990)
print(f"Received {len(rates)} bars")
mt5.shutdown()