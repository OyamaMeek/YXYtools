import hashlib
import http.client
import json
import os
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import monitor
import client
from test_monitor import git
from test_transactions import CONFIG

ROOT = Path(__file__).resolve().parent.parent
MOMENT = datetime.fromisoformat('2026-10-21T00:10:00+08:00')


@contextmanager
def telegram_receiver(reply_topic=86, moment=MOMENT):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            raw = self.rfile.read(int(self.headers['Content-Length']))
            if self.path.endswith('/getMultiCardMoney'):
                response = {'success':True, 'statusCode':0, 'data':{'authCardMoneyList':[
                    {'walletNo':CONFIG['wallet_no'], 'cardMoney':'10.17'}]}}
            else:
                payload = json.loads(raw)
                requests.append((self.path, payload))
                result = {'message_id':101, 'chat':{'id':int(payload['chat_id'])}}
                if reply_topic is not None:
                    result['message_thread_id'] = reply_topic
                response = {'ok':True, 'result':result}
            body = json.dumps(response).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(('127.0.0.1',0), Handler)
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    try:
        with patch.object(http.client, 'HTTPSConnection', lambda host, timeout: http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=timeout)), patch.object(monitor, 'now', lambda: moment), patch.object(client, 'now', lambda: moment):
            yield requests
    finally:
        server.shutdown()
        worker.join()
        server.server_close()


class TelegramTopicTests(unittest.TestCase):
    def test_topic_config_is_optional_and_rejects_invalid_ids(self):
        with patch.dict(os.environ, {}, clear=True), tempfile.TemporaryDirectory(dir=ROOT/'work') as directory:
            path = Path(directory)/'telegram.env'
            base = 'TELEGRAM_BOT_TOKEN=123:offline\nTELEGRAM_CHAT_ID=-100123\n'
            for value, expected in [('', None), ('86', 86)]:
                path.write_text(base+'TELEGRAM_MESSAGE_THREAD_ID='+value+'\n')
                self.assertEqual(monitor.telegram_config(path), ('123:offline','-100123',expected))
            path.write_text(base)
            self.assertEqual(monitor.telegram_config(path)[2], None)
            for value in ['0','-1','1.5','abc',' 86','2147483648']:
                path.write_text(base+"TELEGRAM_MESSAGE_THREAD_ID='"+value+"'\n")
                with self.subTest(value=value), self.assertRaises(ValueError):
                    monitor.telegram_config(path)

    def test_topic_identity_isolated_and_legacy_identity_unchanged(self):
        config = {'ym_id':'account', 'device_id':'device', 'wallet_no':'card'}
        legacy = hashlib.sha256(json.dumps(['account','device','card','-100123']).encode()).hexdigest()
        self.assertEqual(monitor.identity(config, '-100123'), legacy)
        topic = monitor.identity(config, '-100123', 86)
        self.assertNotEqual(topic, legacy)
        self.assertNotEqual(topic, monitor.identity(config, '-100123', 87))
        with self.assertRaises(ValueError):
            monitor.validate_state(monitor.new_state(legacy), topic)

    def test_send_topic_payload_receipt_and_night_guard(self):
        with telegram_receiver() as requests:
            self.assertEqual(monitor.send_message('123:offline', '-100123', '话题通知', 86), 101)
        self.assertEqual(requests, [('/bot123:offline/sendMessage', {'chat_id':'-100123','text':'话题通知','message_thread_id':86})])
        with telegram_receiver(None) as requests:
            self.assertEqual(monitor.send_message('123:offline', '-100123', '群组通知'), 101)
        self.assertNotIn('message_thread_id', requests[0][1])
        for reply in [None, 87, '86']:
            with telegram_receiver(reply), self.assertRaises(monitor.TelegramError):
                monitor.send_message('123:offline', '-100123', '话题通知', 86)
        with telegram_receiver(moment=MOMENT.replace(hour=1)) as requests:
            with self.assertRaises(monitor.OutsideWindowError):
                monitor.send_message('123:offline', '-100123', '话题通知', 86)
        self.assertEqual(requests, [])

    def test_pending_delivery_uses_topic_and_persists_confirmation(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as directory:
            base = Path(directory)
            remote, repo = base/'remote.git', base/'state'
            remote.mkdir()
            git(remote, 'init', '--bare')
            repo.mkdir()
            git(repo, 'init', '-b', 'state')
            git(repo, 'remote', 'add', 'origin', str(remote))
            state = monitor.new_state(monitor.identity(CONFIG, '-100123', 86))
            monitor.queue_message(state, '待发话题通知')
            state['pending'][0]['blocked'] = hashlib.sha256(b'123:offline|-100123').hexdigest()
            monitor.save_state(repo, state)
            config_path, env_path = base/'config.json', base/'telegram.env'
            config_path.write_text(json.dumps(CONFIG))
            env_path.write_text('TELEGRAM_BOT_TOKEN=123:offline\nTELEGRAM_CHAT_ID=-100123\nTELEGRAM_MESSAGE_THREAD_ID=86\n')
            with telegram_receiver() as requests, patch.dict(os.environ, {}, clear=True):
                self.assertEqual(monitor.run(config_path, repo, env_path), 0)
            self.assertEqual(requests[0][1]['message_thread_id'], 86)
            saved = monitor.load_state(repo, state['identity'])
            self.assertEqual(saved['pending'], [])
            self.assertEqual(saved['sent'][0]['message_id'], 101)


if __name__ == '__main__':
    unittest.main()
