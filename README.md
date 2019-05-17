# PrintScanBot

simple telegram bot for printing and scanning

utilizes python3.7

### Install

```bash
pip3 install -r requirements.txt
```

### Usage

Create `config.ini` with such data:
```ini
[Bot]
token = TELEGRAM_BOT_TOKEN
proxy_url = https://PROXY_LOGIN:PASS@OPTIONAL_PROXY:PORT
white_ids = CHAT_ID1,CHAT_ID2
```