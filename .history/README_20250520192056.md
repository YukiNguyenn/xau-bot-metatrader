# XAU Trading Bot

Hệ thống giao dịch tự động cho XAUUSD (Vàng) sử dụng MetaTrader 5 và chiến lược RSI đa khung thời gian.

## Cấu trúc thư mục

```
xau-bot/
├── core/                    # Các thành phần cốt lõi
│   ├── base_trading_strategy.py
│   ├── indicators.py
│   ├── risk_manager.py
│   └── trade_manager.py
├── strategies/             # Chiến lược giao dịch
│   └── rsi_strategy.py
├── config/                 # Cấu hình
│   ├── config.json
│   └── strategies/
│       └── rsi_strategy.json
├── logs/                   # Thư mục chứa log
├── requirements.txt        # Danh sách thư viện cần thiết
└── main.py                 # File chính để chạy bot
```

## Yêu cầu hệ thống

- Python 3.7+
- MetaTrader 5
- Tài khoản MT5 có quyền giao dịch XAUUSD

## Cài đặt

1. Clone repository:
```bash
git clone https://github.com/your-username/xau-bot.git
cd xau-bot
```

2. Tạo môi trường ảo (khuyến nghị):
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

4. Cấu hình MetaTrader 5:
   - Mở MetaTrader 5
   - Đăng nhập vào tài khoản của bạn
   - Cho phép giao dịch tự động (AutoTrading)

5. Cập nhật cấu hình:
   - Mở file `config/config.json`
   - Cập nhật thông tin đăng nhập MT5:
     ```json
     {
         "mt5": {
             "account": "your_account_number",
             "password": "your_password",
             "server": "your_server"
         }
     }
     ```

## Cấu hình chiến lược RSI

Chiến lược RSI sử dụng 3 khung thời gian:
- Ngắn hạn (6 chu kỳ)
- Trung hạn (14 chu kỳ)
- Dài hạn (24 chu kỳ)

Các thông số có thể điều chỉnh trong `config/strategies/rsi_strategy.json`:

```json
{
    "parameters": {
        "rsi_periods": {
            "short": 6,
            "medium": 14,
            "long": 24
        },
        "rsi_levels": {
            "short": {
                "overbought": 80,
                "oversold": 20
            },
            "medium": {
                "overbought": 70,
                "oversold": 30
            },
            "long": {
                "overbought": 60,
                "oversold": 40
            }
        }
    }
}
```

## Quản lý rủi ro

Các thông số quản lý rủi ro trong `config/config.json`:

```json
{
    "trading": {
        "max_open_positions": 3,      // Số lệnh mở tối đa
        "min_position_size": 0.01,    // Khối lượng tối thiểu
        "max_position_size": 1.0,     // Khối lượng tối đa
        "stop_loss_pips": 50,         // Stop loss (pip)
        "take_profit_pips": 100,      // Take profit (pip)
        "max_daily_loss": 100,        // Thua lỗ tối đa mỗi ngày
        "risk_per_trade": 1.0         // Rủi ro mỗi lệnh (%)
    }
}
```

## Chạy bot

1. Đảm bảo MetaTrader 5 đang chạy và đã đăng nhập
2. Chạy bot:
```bash
python main.py
```

3. Kiểm tra logs trong thư mục `logs/` để theo dõi hoạt động

## Tín hiệu giao dịch

Bot sẽ tạo tín hiệu giao dịch khi:

1. Tín hiệu MUA:
   - RSI ngắn hạn <= 20
   - RSI trung hạn <= 30
   - RSI dài hạn <= 40

2. Tín hiệu BÁN:
   - RSI ngắn hạn >= 80
   - RSI trung hạn >= 70
   - RSI dài hạn >= 60

## Dừng bot

- Nhấn `Ctrl+C` để dừng bot an toàn
- Bot sẽ đóng tất cả các lệnh đang mở và dừng giao dịch

## Lưu ý quan trọng

1. Luôn kiểm tra kỹ các thông số quản lý rủi ro trước khi chạy
2. Không nên chạy bot với số tiền lớn khi mới bắt đầu
3. Theo dõi logs thường xuyên để phát hiện vấn đề
4. Đảm bảo máy tính và internet ổn định khi chạy bot
5. Nên test chiến lược trên tài khoản demo trước

## Xử lý lỗi thường gặp

1. Lỗi kết nối MT5:
   - Kiểm tra MT5 đã chạy chưa
   - Kiểm tra thông tin đăng nhập trong config
   - Kiểm tra kết nối internet

2. Lỗi giao dịch:
   - Kiểm tra quyền giao dịch tự động
   - Kiểm tra số dư tài khoản
   - Kiểm tra giới hạn giao dịch

## Hỗ trợ

Nếu bạn gặp vấn đề hoặc cần hỗ trợ:
1. Kiểm tra logs trong thư mục `logs/`
2. Đọc kỹ thông báo lỗi
3. Kiểm tra cấu hình và thông số 