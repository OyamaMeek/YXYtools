import copy
import http.client
import json
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import client
import monitor
from test_monitor import git

FIXTURE = Path(__file__).parent/'fixtures'/'transactions.json'
CONFIG = {'school_name':'杭州电子科技大学信息工程学院', 'ym_id':'123456789',
          'device_id':'ym-'+'0'*32, 'token':'offline-test', 'session_secret':'offline-secret',
          'wallet_no':'redacted-wallet'}


@contextmanager
def replay_api(transaction_response, moment):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
            requests.append((self.path, form, self.headers['sign']))
            if self.path.endswith('/getMultiCardMoney'):
                response = {'success':True, 'statusCode':0, 'data':{'authCardMoneyList':[
                    {'walletNo':'redacted-wallet', 'cardMoney':'10.17'}]}}
            else:
                response = transaction_response
            body = json.dumps(response).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(('127.0.0.1',0), Handler)
    worker = threading.Thread(target=server.serve_forever)
    original_connection, original_client_now, original_monitor_now = http.client.HTTPSConnection, client.now, monitor.now
    worker.start()
    try:
        http.client.HTTPSConnection = lambda host, timeout: http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=timeout)
        client.now = monitor.now = lambda: moment
        yield requests
    finally:
        http.client.HTTPSConnection, client.now, monitor.now = original_connection, original_client_now, original_monitor_now
        server.shutdown()
        worker.join()
        server.server_close()


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.response = json.loads(FIXTURE.read_text())

    def test_real_capture_projects_amounts_and_two_times(self):
        rows = client.parse_transactions(self.response)
        self.assertEqual([(row['project'], row['amount']) for row in rows], [
            ('寝室热水', Decimal('-2.85')),
            ('寝室热水1-2', Decimal('0.00')),
            ('西区餐厅', Decimal('-13.59')),
        ])
        self.assertEqual(rows[0]['transaction_at'].isoformat(), '2026-10-08T22:31:13+08:00')
        self.assertEqual(rows[0]['posted_at'].isoformat(), '2026-10-08T22:31:48+08:00')
        self.assertEqual(rows[1]['kind'], '补助圈存')

    def test_invalid_or_incomplete_response_is_rejected(self):
        invalid = [None, {**self.response, 'success':False}, {**self.response, 'statusCode':True},
                   {**self.response, 'total':4}, {**self.response, 'rows':None}]
        for field, value in [('money','NaN'), ('money','1.001'), ('money',2.85),
                             ('time','2026-02-30 12:00:00'), ('dealtime',''),
                             ('address',''), ('feeName',None), ('serialno','')]:
            response = copy.deepcopy(self.response)
            response['rows'][0][field] = value
            invalid.append(response)
        for response in invalid:
            with self.subTest(response=response), self.assertRaises(ValueError):
                client.parse_transactions(response)
        self.assertEqual(client.parse_transactions({'success':True, 'statusCode':0, 'total':0, 'rows':[]}), [])

    def test_notification_filters_posted_time_and_displays_projects(self):
        state = monitor.new_state('account-chat')
        first = datetime(2026,10,8,22,23,48,tzinfo=client.BEIJING)
        last = datetime(2026,10,8,22,36,tzinfo=client.BEIJING)
        monitor.record_balance(state, Decimal('100.00'), first)
        monitor.record_balance(state, Decimal('97.15'), last, client.parse_transactions(self.response))
        text = state['pending'][0]['text']
        self.assertIn('寝室热水（消费）：-2.85 元', text)
        self.assertIn('交易：2026-10-08 22:31:13', text)
        self.assertIn('到账：2026-10-08 22:31:48', text)
        self.assertNotIn('西区餐厅', text)
        self.assertNotIn('寝室热水1-2', text)
        monitor.validate_state(state, 'account-chat')
        monitor.record_balance(state, Decimal('97.15'), last, client.parse_transactions(self.response))
        self.assertEqual(len(state['pending']), 1)

    def test_empty_details_are_explicit_and_long_messages_preserve_records(self):
        state = monitor.new_state('account-chat')
        first = datetime(2026,10,8,12,tzinfo=client.BEIJING)
        last = datetime(2026,10,8,22,36,tzinfo=client.BEIJING)
        monitor.record_balance(state, Decimal('100.00'), first)
        monitor.record_balance(state, Decimal('97.15'), last, [])
        self.assertIn('暂无已到账交易明细', state['pending'][0]['text'])
        state = monitor.new_state('account-chat')
        monitor.record_balance(state, Decimal('100.00'), first)
        rows = client.parse_transactions(self.response)*70
        monitor.record_balance(state, Decimal('80.00'), last, rows)
        messages = [item['text'] for item in state['pending']]
        self.assertGreater(len(messages), 1)
        self.assertTrue(all(len(text) <= 4096 for text in messages))
        self.assertEqual('\n'.join(messages).count('寝室热水（消费）：-2.85 元'), 70)
        self.assertEqual('\n'.join(messages).count('西区餐厅（消费）：-13.59 元'), 70)
        monitor.validate_state(state, 'account-chat')

    def test_cross_day_query_uses_beijing_dates_and_deduplicates_rows(self):
        start = datetime.fromisoformat('2026-10-07T14:36:00+00:00')
        end = datetime.fromisoformat('2026-10-08T07:36:00+08:00')
        with replay_api(self.response, end) as requests:
            rows = client.query_transactions(CONFIG, start, end)
        self.assertEqual([form['queryTime'] for _,form,_ in requests], [['20261007'], ['20261008']])
        self.assertTrue(all(path == '/routeauth/auth/route/user/cardQuerynoPage' and sign for path,_,sign in requests))
        self.assertEqual([row['project'] for row in rows], ['西区餐厅','寝室热水1-2','寝室热水'])
        with self.assertRaises(ValueError):
            client.query_transactions(CONFIG, end, start)
        with replay_api(self.response, end.replace(hour=1)) as requests:
            with self.assertRaises(client.OutsideWindowError):
                client.query_transactions(CONFIG, start, end)
        self.assertEqual(requests, [])

    def test_incomplete_details_preserve_remote_baseline_in_real_run(self):
        moment = datetime(2026,10,8,22,36,tzinfo=client.BEIJING)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent/'work') as directory:
            base = Path(directory)
            remote, repo = base/'remote.git', base/'state'
            remote.mkdir()
            git(remote, 'init', '--bare')
            repo.mkdir()
            git(repo, 'init', '-b', 'state')
            git(repo, 'config', 'user.name', 'Monitor Test')
            git(repo, 'config', 'user.email', 'monitor-test@example.invalid')
            git(repo, 'remote', 'add', 'origin', str(remote))
            state = monitor.new_state(monitor.identity(CONFIG, '123'))
            monitor.record_balance(state, Decimal('110.17'), moment.replace(hour=12))
            monitor.save_state(repo, state)
            config_path, env_path = base/'config.json', base/'telegram.env'
            config_path.write_text(json.dumps(CONFIG))
            env_path.write_text('TELEGRAM_BOT_TOKEN=123:offline\nTELEGRAM_CHAT_ID=123\n')
            with replay_api({**self.response, 'total':4}, moment) as requests:
                self.assertEqual(monitor.run(config_path, repo, env_path), 1)
            loaded = monitor.load_state(repo, state['identity'])
            self.assertEqual(loaded['baseline'], state['baseline'])
            self.assertEqual(loaded['failure']['count'], 1)
            self.assertEqual(loaded['pending'], [])
            self.assertEqual(len(requests), 2)


if __name__ == '__main__':
    unittest.main()
