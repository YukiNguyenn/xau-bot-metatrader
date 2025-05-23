import pandas as pd
import numpy as np

def calculate_ma(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """
    Calculate Simple Moving Average (MA)
    
    Args:
        df (pd.DataFrame): DataFrame containing price data
        period (int): Period for MA calculation
        column (str): Column name to calculate MA for (default: 'close')
        
    Returns:
        pd.Series: Series containing MA values
    """
    return df[column].rolling(window=period).mean()

def calculate_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA)
    
    Args:
        df (pd.DataFrame): DataFrame containing price data
        period (int): Period for EMA calculation
        column (str): Column name to calculate EMA for (default: 'close')
        
    Returns:
        pd.Series: Series containing EMA values
    """
    return df[column].ewm(span=period, adjust=False).mean()

def calculate_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = 'close'
) -> tuple:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    
    Args:
        df (pd.DataFrame): DataFrame containing price data
        fast (int): Fast period (default: 12)
        slow (int): Slow period (default: 26)
        signal (int): Signal period (default: 9)
        column (str): Column name to calculate MACD for (default: 'close')
        
    Returns:
        tuple: (MACD line, Signal line, Histogram)
    """
    # Calculate fast and slow EMAs
    fast_ema = calculate_ema(df, fast, column)
    slow_ema = calculate_ema(df, slow, column)
    
    # Calculate MACD line
    macd_line = fast_ema - slow_ema
    
    # Calculate signal line
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    
    # Calculate histogram
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
    """
    Calculate Relative Strength Index (RSI)
    
    Args:
        df (pd.DataFrame): DataFrame containing price data
        period (int): Period for RSI calculation (default: 14)
        column (str): Column name to calculate RSI for (default: 'close')
        
    Returns:
        pd.Series: Series containing RSI values
    """
    # Calculate price changes
    delta = df[column].diff()
    
    # Separate gains and losses
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # Calculate RS
    rs = gain / loss
    
    # Calculate RSI
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    column: str = 'close'
) -> tuple:
    """
    Calculate Bollinger Bands
    
    Args:
        df (pd.DataFrame): DataFrame containing price data
        period (int): Period for calculation (default: 20)
        std_dev (float): Number of standard deviations (default: 2.0)
        column (str): Column name to calculate bands for (default: 'close')
        
    Returns:
        tuple: (Middle band, Upper band, Lower band)
    """
    # Calculate middle band (SMA)
    middle_band = calculate_ma(df, period, column)
    
    # Calculate standard deviation
    std = df[column].rolling(window=period).std()
    
    # Calculate upper and lower bands
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    
    return middle_band, upper_band, lower_band

def calculate_stochastic(
    df: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
    slowing: int = 3
) -> tuple:
    """
    Calculate Stochastic Oscillator
    
    Args:
        df (pd.DataFrame): DataFrame containing price data
        k_period (int): %K period (default: 14)
        d_period (int): %D period (default: 3)
        slowing (int): Slowing period (default: 3)
        
    Returns:
        tuple: (%K line, %D line)
    """
    # Calculate highest high and lowest low
    highest_high = df['high'].rolling(window=k_period).max()
    lowest_low = df['low'].rolling(window=k_period).min()
    
    # Calculate %K
    k = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
    
    # Apply slowing
    k = k.rolling(window=slowing).mean()
    
    # Calculate %D
    d = k.rolling(window=d_period).mean()
    
    return k, d

def calculate_atr(
    df: pd.DataFrame,
    period: int = 14
) -> pd.Series:
    """
    Calculate Average True Range (ATR)
    
    Args:
        df (pd.DataFrame): DataFrame containing price data
        period (int): Period for ATR calculation (default: 14)
        
    Returns:
        pd.Series: Series containing ATR values
    """
    # Calculate True Range
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift())
    tr3 = abs(df['low'] - df['close'].shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate ATR
    atr = tr.rolling(window=period).mean()
    
    return atr

def calculate_ichimoku(
    df: pd.DataFrame,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_span_b_period: int = 52,
    displacement: int = 26
) -> tuple:
    """
    Calculate Ichimoku Cloud
    
    Args:
        df (pd.DataFrame): DataFrame containing price data
        tenkan_period (int): Tenkan-sen period (default: 9)
        kijun_period (int): Kijun-sen period (default: 26)
        senkou_span_b_period (int): Senkou Span B period (default: 52)
        displacement (int): Displacement period (default: 26)
        
    Returns:
        tuple: (Tenkan-sen, Kijun-sen, Senkou Span A, Senkou Span B)
    """
    # Calculate Tenkan-sen (Conversion Line)
    tenkan_high = df['high'].rolling(window=tenkan_period).max()
    tenkan_low = df['low'].rolling(window=tenkan_period).min()
    tenkan_sen = (tenkan_high + tenkan_low) / 2
    
    # Calculate Kijun-sen (Base Line)
    kijun_high = df['high'].rolling(window=kijun_period).max()
    kijun_low = df['low'].rolling(window=kijun_period).min()
    kijun_sen = (kijun_high + kijun_low) / 2
    
    # Calculate Senkou Span A (Leading Span A)
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(displacement)
    
    # Calculate Senkou Span B (Leading Span B)
    senkou_high = df['high'].rolling(window=senkou_span_b_period).max()
    senkou_low = df['low'].rolling(window=senkou_span_b_period).min()
    senkou_span_b = ((senkou_high + senkou_low) / 2).shift(displacement)
    
    return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b
