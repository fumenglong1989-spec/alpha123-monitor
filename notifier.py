import html
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate
from config import URL, RECIPIENTS, smtp_config

def message(events, detected, recipient, user, test=False):
    msg = EmailMessage()
    msg['Subject'] = '【Alpha123空投提醒】配置测试' if test else '【Alpha123空投提醒】' + '；'.join(e['kind'] + '：' + e['item']['name'] for e in events)
    msg['From'], msg['To'], msg['Date'] = user, recipient, formatdate(localtime=False)
    text = 'QQ SMTP 配置测试。' if test else '发现新的币安 Alpha 空投或信息更新！\n\n' + '\n\n'.join(
        f"{e['kind']}\n项目名称：{e['item']['name']}\n所需积分：{e['item']['points']}\n空投数量：{e['item']['amount']}\n空投时间：{e['item']['time']}（北京时间）" for e in events)
    text += f'\n\n检测时间：{detected}\n查看网站：{URL}'
    msg.set_content(text, charset='utf-8')
    msg.add_alternative('<html><body><pre style="white-space:pre-wrap">' + html.escape(text) + '</pre></body></html>', subtype='html', charset='utf-8')
    return msg

def send(recipient, events, detected, test=False):
    user, password, mode = smtp_config()
    context = ssl.create_default_context()
    client = smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=30, context=context) if mode == 'ssl' else smtplib.SMTP('smtp.qq.com', 587, timeout=30)
    with client:
        if mode == 'starttls':
            client.ehlo(); client.starttls(context=context); client.ehlo()
        client.login(user, password)
        refused = client.send_message(message(events, detected, recipient, user, test), to_addrs=[recipient])
        if refused:
            raise RuntimeError('SMTP 收件人被拒绝')

def test_mail():
    from datetime import datetime
    from config import BEIJING
    failures = 0
    for recipient in RECIPIENTS:
        try:
            send(recipient, [], datetime.now(BEIJING).strftime('%Y-%m-%d %H:%M:%S'), test=True)
            logging.info('测试邮件 SMTP 已接受 recipient=%s', recipient)
        except Exception as exc:
            failures += 1
            logging.error('测试失败 recipient=%s error_type=%s', recipient, type(exc).__name__)
    return failures

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(1 if test_mail() else 0)
