import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import monitor
import client

ROOT = Path(__file__).resolve().parent.parent
ZONE = timezone(timedelta(hours=8))


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


class MonitorTests(unittest.TestCase):
    def test_actions_invalid_config_preserves_an_existing_private_file(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as directory:
            base = Path(directory)
            (base/'work').mkdir()
            existing = base/'work'/'client-private.json'
            existing.write_text('existing private configuration')
            subprocess.run([sys.executable, str(ROOT/'tools'/'run_monitor.py')], cwd=base, env={**os.environ,'YXY_LOGIN_CONFIG':'{}'}, capture_output=True)
            self.assertTrue(existing.exists(), '无效 Actions 配置删除了已有凭证文件')
            self.assertEqual(existing.read_text(), 'existing private configuration')

    def test_time_window_excludes_night_and_rejects_naive_time(self):
        for hour, minute, expected in [(7,29,False),(7,30,True),(22,59,True),(23,0,True),(0,59,True),(1,0,False)]:
            self.assertEqual(monitor.in_window(datetime(2026,10,4,hour,minute,tzinfo=ZONE)), expected)
            self.assertEqual(client.in_window(datetime(2026,10,4,hour,minute,tzinfo=ZONE)), expected)
        with self.assertRaises(ValueError):
            monitor.in_window(datetime(2026,10,4,12))

    def test_initial_unchanged_increase_decrease_zero_and_failure_recovery(self):
        state = monitor.new_state('account-chat')
        first = datetime(2026,10,4,12,tzinfo=ZONE)
        monitor.record_balance(state, Decimal('10.17'), first)
        self.assertEqual(state['pending'], [])
        monitor.record_balance(state, Decimal('10.17'), first+timedelta(minutes=30))
        self.assertEqual(state['pending'], [])
        monitor.record_balance(state, Decimal('12.00'), first+timedelta(hours=1))
        self.assertEqual(state['pending'][0]['text'].splitlines()[1:3], ['余额：12.00 元', '变动：+1.83 元'])
        self.assertIn('+1.83', state['pending'][0]['text'])
        monitor.record_balance(state, Decimal('8.00'), first+timedelta(hours=2))
        self.assertIn('-4.00', state['pending'][1]['text'])
        monitor.record_failure(state, 'session', first+timedelta(hours=3))
        monitor.record_failure(state, 'session', first+timedelta(hours=4))
        self.assertEqual(len(state['pending']), 3)
        self.assertEqual(state['baseline']['yuan'], '8.00')
        monitor.record_balance(state, Decimal('0.00'), first+timedelta(hours=5))
        self.assertIsNone(state['failure'])
        self.assertIn('-8.00', state['pending'][3]['text'])
        self.assertIn('2026-10-04', state['pending'][3]['text'])

    def test_state_survives_another_checkout_and_failed_push_is_explicit(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as directory:
            base = Path(directory)
            remote, repo = base/'remote.git', base/'state'
            remote.mkdir()
            git(remote, 'init', '--bare')
            repo.mkdir()
            git(repo, 'init', '-b', 'state')
            git(repo, 'config', 'user.name', 'Monitor Test')
            git(repo, 'config', 'user.email', 'monitor-test@example.invalid')
            git(repo, 'remote', 'add', 'origin', str(remote))
            state = monitor.new_state('account-chat')
            monitor.record_balance(state, Decimal('10.17'), datetime(2026,10,4,12,tzinfo=ZONE))
            monitor.record_balance(state, Decimal('8.17'), datetime(2026,10,4,13,tzinfo=ZONE))
            monitor.save_state(repo, state)
            clone = base/'next'
            subprocess.run(['git','clone','--branch','state',str(remote),str(clone)], capture_output=True, check=True)
            loaded = monitor.load_state(clone, 'account-chat')
            self.assertEqual(loaded['baseline']['yuan'], '8.17')
            self.assertEqual(len(loaded['pending']), 1)
            monitor.confirm_sent(loaded, loaded['pending'][0]['id'], 123)
            monitor.save_state(clone, loaded)
            self.assertEqual(monitor.load_state(clone, 'account-chat')['sent'][-1]['message_id'], 123)
            git(clone, 'remote', 'set-url', 'origin', str(base/'absent.git'))
            monitor.record_balance(loaded, Decimal('7.17'), datetime(2026,10,4,14,tzinfo=ZONE))
            with self.assertRaises(RuntimeError):
                monitor.save_state(clone, loaded)
            unchanged = json.loads(git(remote, 'show', 'state:state.json'))
            self.assertEqual(unchanged['baseline']['yuan'], '8.17')

    def test_existing_corrupt_wrong_identity_or_missing_state_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as directory:
            path = Path(directory)
            git(path, 'init', '-b', 'state')
            with self.assertRaises((ValueError, RuntimeError, FileNotFoundError)):
                monitor.load_state(path, 'account-chat')
            state = monitor.new_state('wrong-account')
            with self.assertRaises(ValueError):
                monitor.validate_state(state, 'account-chat')
            state['identity'] = 'account-chat'
            state['baseline'] = {'yuan':'NaN','observed_at':'2026-10-04T12:00:00+08:00'}
            with self.assertRaises(ValueError):
                monitor.validate_state(state, 'account-chat')


if __name__ == '__main__':
    unittest.main()
