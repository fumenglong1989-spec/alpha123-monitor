import html
import logging
import smtplib
import socket
import ssl
from email.message import EmailMessage
from email.utils import formatdate
from config import URL, RECIPIENTS, SMTP_HOST, SMTP_PORT, smtp_config

def message(events, detected, recipient, user, test=False):
    msg = EmailMessage()
    msg['Subject'] = '【Alpha123空投提醒】163邮箱配置测试' if test else '【Alpha123空投提醒】' + '；'.join(e['kind'] + '：' + e['item']['name'] for e in events)
    msg['From'], msg['To'], msg['Date'] = user, recipient, formatdate(localtime=False)
    text = '网易163邮箱 SMTP SSL 配置测试（smtp.163.com:465），用于验证向QQ收件邮箱投递。' if test else '发现新的币安 Alpha 空投或信息更新！\n\n' + '\n\n'.join(
        f"{e['kind']}\n项目名称：{e['item']['name']}\n所需积分：{e['item']['points']}\n空投数量：{e['item']['amount']}\n空投时间：{e['item']['time']}（北京时间）" for e in events)
    text += f'\n\n检测时间：{detected}\n查看网站：{URL}'
    msg.set_content(text, charset='utf-8')
    msg.add_alternative('<html><body><pre style="white-space:pre-wrap">' + html.escape(text) + '</pre></body></html>', subtype='html', charset='utf-8')
    return msg

class DeliveryError(Exception):
    def __init__(self, category, stage, smtp_code=None):
        self.category, self.stage, self.smtp_code = category, stage, smtp_code
        super().__init__(f'{category} stage={stage} smtp_code={smtp_code}')


def classify(exc, stage):
    if isinstance(exc, ssl.SSLError) or (stage == 'tls_handshake' and isinstance(exc, OSError)): category = 'tls_handshake_failed'
    elif isinstance(exc, smtplib.SMTPAuthenticationError): category = 'authentication_rejected'
    elif isinstance(exc, smtplib.SMTPServerDisconnected): category = 'server_disconnected'
    elif isinstance(exc, smtplib.SMTPRecipientsRefused): category = 'recipient_rejected'
    elif isinstance(exc, smtplib.SMTPException): category = 'smtp_protocol_failed'
    elif isinstance(exc, (OSError, TimeoutError)): category = 'network_connection_failed'
    else: category = 'unexpected_failure'
    code = getattr(exc, 'smtp_code', None)
    return DeliveryError(category, stage, code if isinstance(code, int) else None)


class DiagnosticSMTPSSL(smtplib.SMTP_SSL):
    def __init__(self, *, timeout=30, context=None):
        self.tls_context = context if context is not None else ssl.create_default_context()
        super().__init__(timeout=timeout, context=self.tls_context)

    def _get_socket(self, host, port, timeout):
        self.stage = 'tcp_connect'
        raw = socket.create_connection((host, port), timeout, self.source_address)
        self.stage = 'tls_handshake'
        try:
            wrapped = self.tls_context.wrap_socket(raw, server_hostname=host)
        except Exception:
            raw.close()
            raise
        self.stage = 'smtp_greeting'
        return wrapped


def send(recipient, events, detected, test=False):
    user, password = smtp_config()
    client = DiagnosticSMTPSSL(timeout=30, context=ssl.create_default_context())
    client.stage = 'tcp_connect'
    try:
        logging.info('SMTP host=%s port=%s stage=tcp_connect recipient=%s', SMTP_HOST, SMTP_PORT, recipient)
        code, _ = client.connect(SMTP_HOST, SMTP_PORT)
        if code != 220: raise smtplib.SMTPConnectError(code, b'')
        client.stage = 'ehlo'
        code, _ = client.ehlo()
        if code != 250: raise smtplib.SMTPHeloError(code, b'')
        client.stage = 'authentication'
        logging.info('SMTP stage=authentication recipient=%s', recipient)
        client.login(user, password)
        client.stage = 'submit_message'
        logging.info('SMTP stage=submit_message recipient=%s', recipient)
        refused = client.send_message(message(events, detected, recipient, user, test), to_addrs=[recipient])
        if refused: raise smtplib.SMTPRecipientsRefused(refused)
        logging.info('SMTP accepted=true recipient=%s', recipient)
    except Exception as exc:
        raise classify(exc, client.stage) from None
    else:
        # DATA accepted: QUIT failure must not trigger resend.
        try: client.quit()
        except Exception as exc:
            error = classify(exc, 'quit_after_accept')
            logging.warning('SMTP cleanup category=%s stage=%s accepted=true', error.category, error.stage)
    finally:
        client.close()

def test_mail():
    from datetime import datetime
    from config import BEIJING
    failures = 0
    for recipient in RECIPIENTS:
        try:
            send(recipient, [], datetime.now(BEIJING).strftime('%Y-%m-%d %H:%M:%S'), test=True)
            logging.info('测试邮件 SMTP 已接受 recipient=%s', recipient)
        except DeliveryError as exc:
            failures += 1
            logging.error('测试失败 recipient=%s category=%s stage=%s smtp_code=%s', recipient, exc.category, exc.stage, exc.smtp_code)
        except Exception as exc:
            failures += 1
            logging.error('测试失败 recipient=%s category=configuration_or_unexpected error_type=%s', recipient, type(exc).__name__)
    return failures

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(1 if test_mail() else 0)
