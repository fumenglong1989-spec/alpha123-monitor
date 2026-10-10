import os
import socket
import ssl
import smtplib
import unittest
from unittest.mock import patch, MagicMock
from notifier import send, classify, DiagnosticSMTPSSL, DeliveryError
from config import smtp_config

class NotifierTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, SMTP_USER='sender@163.com', SMTP_PASSWORD='test-authorization-secret')
        self.env.start()
        self.mock = patch('notifier.DiagnosticSMTPSSL')
        self.client = self.mock.start().return_value
        self.client.connect.return_value = (220, b'ok')
        self.client.ehlo.return_value = (250, b'ok')
        self.client.send_message.return_value = {}
    def tearDown(self): self.mock.stop(); self.env.stop()
    def test_163_ssl_and_secrets(self):
        send('270114311@qq.com', [], '2026-10-10', test=True)
        self.client.connect.assert_called_once_with('smtp.163.com', 465)
        self.client.login.assert_called_once_with('sender@163.com', 'test-authorization-secret')
        self.assertEqual(self.client.send_message.call_args.kwargs['to_addrs'], ['270114311@qq.com'])
        msg = self.client.send_message.call_args.args[0]
        self.assertIn('网易163', msg.get_body(preferencelist=('plain',)).get_content())
    def test_auth_rejection_redacted(self):
        self.client.login.side_effect = smtplib.SMTPAuthenticationError(535, b'test-authorization-secret')
        with self.assertRaises(DeliveryError) as result: send('249446251@qq.com', [], 'now')
        self.assertEqual((result.exception.category, result.exception.stage, result.exception.smtp_code), ('authentication_rejected', 'authentication', 535))
        self.assertNotIn('test-authorization-secret', str(result.exception))
        self.client.send_message.assert_not_called()
    def test_ehlo_disconnect_is_not_auth_failure(self):
        self.client.ehlo.side_effect = smtplib.SMTPServerDisconnected('sensitive server response')
        with self.assertRaises(DeliveryError) as result: send('270114311@qq.com', [], 'now')
        self.assertEqual((result.exception.category, result.exception.stage), ('server_disconnected', 'ehlo'))
        self.client.login.assert_not_called()
    def test_quit_disconnect_after_accept_is_success(self):
        self.client.quit.side_effect = smtplib.SMTPServerDisconnected()
        send('270114311@qq.com', [], 'now')
        self.client.send_message.assert_called_once()
    def test_network_tls_and_server_disconnect_categories(self):
        for exc, stage, expected in [(socket.gaierror(), 'tcp_connect', 'network_connection_failed'), (ssl.SSLError(), 'tls_handshake', 'tls_handshake_failed'), (TimeoutError(), 'tls_handshake', 'tls_handshake_failed'), (smtplib.SMTPServerDisconnected(), 'smtp_greeting', 'server_disconnected')]:
            self.assertEqual(classify(exc, stage).category, expected)
    def test_missing_secret(self):
        with patch.dict(os.environ, SMTP_PASSWORD=''):
            with self.assertRaises(ValueError): smtp_config()

class SocketStagesTests(unittest.TestCase):
    def test_tcp_and_tls_use_verified_163_host(self):
        context = MagicMock(); client = DiagnosticSMTPSSL(context=context); raw = MagicMock()
        with patch('notifier.socket.create_connection', return_value=raw) as connect:
            client._get_socket('smtp.163.com', 465, 30)
        connect.assert_called_once_with(('smtp.163.com', 465), 30, None)
        context.wrap_socket.assert_called_once_with(raw, server_hostname='smtp.163.com')
        self.assertEqual(client.stage, 'smtp_greeting')
    def test_raw_socket_closed_when_tls_fails(self):
        context = MagicMock(); context.wrap_socket.side_effect = ssl.SSLError()
        client = DiagnosticSMTPSSL(context=context); raw = MagicMock()
        with patch('notifier.socket.create_connection', return_value=raw):
            with self.assertRaises(ssl.SSLError): client._get_socket('smtp.163.com', 465, 30)
        raw.close.assert_called_once(); self.assertEqual(client.stage, 'tls_handshake')
