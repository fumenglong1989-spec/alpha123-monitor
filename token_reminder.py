"""Operational expiry notices; never generate synthetic airdrop messages."""
import hashlib
import html
import logging
import os
from datetime import datetime, timezone
from email.message import EmailMessage
from config import RECIPIENTS, SMTP_HOST, SMTP_PORT, smtp_config
from notifier import DiagnosticSMTPSSL, classify
from state_store import GithubStore

def notice(recipient, expiry):
    user, password = smtp_config()
    msg = EmailMessage()
    msg['Subject'] = '【Alpha123监控维护】GitHub调度Token即将到期'
    msg['From'], msg['To'] = user, recipient
    text = (f'Cloudflare 调度使用的 GitHub Token 到期日期：{expiry}（UTC）。\n'
            '请在到期前创建仅限 alpha123-monitor、Actions读写权限的新Token，'
            '更新 Cloudflare 的 GITHUB_DISPATCH_TOKEN 加密Secret，并更新GitHub变量 DISPATCH_TOKEN_EXPIRES_AT。\n'
            '不要把Token发到聊天或写入代码。过期后自动调度会停止。\n'
            '仓库：https://github.com/fumenglong1989-spec/alpha123-monitor\n此邮件是维护提醒，不是空投通知。')
    msg.set_content(text, charset='utf-8')
    msg.add_alternative('<pre>' + html.escape(text) + '</pre>', subtype='html', charset='utf-8')
    client = DiagnosticSMTPSSL(timeout=30)
    client.stage = 'tcp_connect'
    try:
        client.connect(SMTP_HOST, SMTP_PORT)
        client.stage = 'ehlo'; client.ehlo()
        client.stage = 'authentication'; client.login(user, password)
        client.stage = 'submit_message'
        refused = client.send_message(msg, to_addrs=[recipient])
        if refused:
            import smtplib
            raise smtplib.SMTPRecipientsRefused(refused)
    except Exception as exc:
        raise classify(exc, client.stage) from None
    else:
        try: client.quit()
        except Exception: pass  # Already accepted: never resend because QUIT failed.
    finally: client.close()

def remind(store, expiry, today=None, sender=notice):
    if not expiry:
        logging.warning('Token expiry metadata missing; configure DISPATCH_TOKEN_EXPIRES_AT')
        return
    today = today or datetime.now(timezone.utc).date()
    remaining = (datetime.fromisoformat(expiry).date() - today).days
    threshold = next((n for n in (1, 7, 14) if remaining <= n), None)
    if threshold is None: return
    state = store.load()
    done = state.setdefault('token_reminders', {})
    for recipient in RECIPIENTS:
        key = f'{expiry}:{threshold}:' + hashlib.sha256(recipient.encode()).hexdigest()
        if key in done: continue
        try: sender(recipient, expiry)
        except Exception as exc:
            logging.error('Token reminder failed recipient=%s category=%s; retry next run', recipient, getattr(exc, 'category', 'unknown'))
        else:
            done[key] = today.isoformat(); store.save(state)
            logging.info('Token reminder SMTP accepted recipient=%s', recipient)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    remind(GithubStore(), os.getenv('DISPATCH_TOKEN_EXPIRES_AT', ''))
