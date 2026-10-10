import os
from datetime import timezone, timedelta
from pathlib import Path

URL = 'https://alpha123.uk/zh/'
RECIPIENTS = ('270114311@qq.com', '249446251@qq.com')
BEIJING = timezone(timedelta(hours=8))
STATE_PATH = Path(os.getenv('STATE_PATH', 'state.json'))
SMTP_HOST = 'smtp.163.com'
SMTP_PORT = 465

def smtp_config():
    user, password = os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD')
    if not user or not password:
        raise ValueError('缺少 SMTP_USER 或 SMTP_PASSWORD')
    return user.strip(), password
