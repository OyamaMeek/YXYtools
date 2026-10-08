import argparse
import hashlib
import http.client
import json
import os
import re
import shlex
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from client import OutsideWindowError, in_window, load_config, now, query_balance, query_transactions


def telegram_config(env_file=None):
    values = dict(os.environ)
    if env_file is not None:
        for line in Path(env_file).read_text().splitlines():
            fields = shlex.split(line, comments=True)
            if not fields:
                continue
            if len(fields) != 1 or '=' not in fields[0]:
                raise ValueError('.env 需使用单行 KEY=VALUE 格式')
            key, value = fields[0].split('=', 1)
            if key not in {'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'} or key in values:
                raise ValueError('.env 存在未知或重复的配置字段')
            values[key] = value
    token, chat = values.get('TELEGRAM_BOT_TOKEN', ''), values.get('TELEGRAM_CHAT_ID', '')
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+', token) or not re.fullmatch(r'-?[0-9]+', chat):
        raise ValueError('Telegram Token 或 Chat ID 格式非法')
    return token, chat


def identity(config, chat):
    value = [config['ym_id'], config['device_id'], config['wallet_no'], chat]
    return hashlib.sha256(json.dumps(value).encode()).hexdigest()


def new_state(account_chat):
    return {'version':1, 'identity':account_chat, 'baseline':None, 'failure':None, 'pending':[], 'sent':[]}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('状态时间字段非法')
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('状态时间缺少时区')
    return result


def validate_state(state, expected):
    if not isinstance(state, dict) or state.get('version') != 1 or state.get('identity') != expected:
        raise ValueError('状态版本、账户或接收目标不符')
    if set(state) != {'version','identity','baseline','failure','pending','sent'}:
        raise ValueError('状态字段不完整')
    baseline = state['baseline']
    if baseline is not None:
        if not isinstance(baseline, dict) or set(baseline) != {'yuan','observed_at'} or not isinstance(baseline['yuan'], str) or not re.fullmatch(r'[0-9]+\.[0-9]{2}', baseline['yuan']):
            raise ValueError('状态余额非法')
        timestamp(baseline['observed_at'])
    failure = state['failure']
    if failure is not None:
        if not isinstance(failure, dict) or set(failure) != {'kind','count','since','alerted'} or failure['kind'] not in {'query','session'} or type(failure['count']) is not int or failure['count'] < 1 or type(failure['alerted']) is not bool:
            raise ValueError('故障状态非法')
        timestamp(failure['since'])
    if not isinstance(state['pending'], list) or not isinstance(state['sent'], list):
        raise ValueError('待发或已发送状态非法')
    ids = set()
    for item in state['pending']:
        if not isinstance(item, dict) or set(item) != {'id','text','attempts','retry_at','blocked'} or not isinstance(item['id'], str) or not item['id'] or item['id'] in ids or not isinstance(item['text'], str) or not 1 <= len(item['text']) <= 4096 or type(item['attempts']) is not int or item['attempts'] < 0:
            raise ValueError('待发消息非法')
        ids.add(item['id'])
        if item['retry_at'] is not None:
            timestamp(item['retry_at'])
        if item['blocked'] is not None and (not isinstance(item['blocked'], str) or not re.fullmatch(r'[0-9a-f]{64}', item['blocked'])):
            raise ValueError('待发消息阻塞字段非法')
    for item in state['sent']:
        if not isinstance(item, dict) or set(item) != {'id','message_id'} or not isinstance(item['id'], str) or not item['id'] or item['id'] in ids or type(item['message_id']) is not int or item['message_id'] <= 0:
            raise ValueError('发送结果非法')
        ids.add(item['id'])
    return state


def git(repo, *args):
    result = subprocess.run(['git','-C',str(repo), *args], capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError('状态 Git 操作失败：'+args[0])
    return result.stdout.strip()


def load_state(repo, expected):
    if git(repo, 'branch', '--show-current') != 'state':
        raise ValueError('状态 checkout 必须使用 state 分支')
    git(repo, 'fetch', 'origin', 'state')
    if git(repo, 'rev-parse', 'HEAD') != git(repo, 'rev-parse', 'FETCH_HEAD'):
        raise RuntimeError('状态 checkout 未与远端同步，请从远端重新检出')
    if git(repo, 'status', '--porcelain'):
        raise RuntimeError('状态 checkout 存在未保存改动')
    path = Path(repo)/'state.json'
    if path.stat().st_size > 8_000_000:
        raise ValueError('状态文件超限')
    return validate_state(json.loads(path.read_text()), expected)


def save_state(repo, state):
    validate_state(state, state['identity'])
    if git(repo, 'branch', '--show-current') != 'state':
        raise ValueError('状态 checkout 必须使用 state 分支')
    path = Path(repo)/'state.json'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=repo, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(repo, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    git(repo, 'add', 'state.json')
    changed = subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--','state.json'], capture_output=True, timeout=45).returncode
    if changed not in (0,1):
        raise RuntimeError('状态暂存检查失败')
    if changed:
        git(repo, '-c','user.name=YXYtools Monitor','-c','user.email=monitor@users.noreply.github.com','commit','-m','chore: persist monitor state','--','state.json')
    git(repo, 'push', 'origin', 'HEAD:refs/heads/state')


def queue_message(state, text):
    state['pending'].append({'id':uuid.uuid4().hex, 'text':text, 'attempts':0, 'retry_at':None, 'blocked':None})


def record_balance(state, amount, moment, transactions=None):
    if not isinstance(amount, Decimal) or not amount.is_finite() or amount < 0 or amount * 100 != (amount * 100).to_integral_value():
        raise ValueError('观察余额非法')
    timestamp(moment.isoformat())
    previous = state['baseline']
    if previous is not None and Decimal(previous['yuan']) != amount:
        difference = amount - Decimal(previous['yuan'])
        text = f"校园卡余额变化\n余额：{amount:.2f} 元\n变动：{difference:+.2f} 元\n上次余额：{previous['yuan']} 元\n观察间隔：{previous['observed_at']} 至 {moment.isoformat()}\n检测时间为查询时间，不代表交易时间。"
        if transactions is not None:
            rows = [row for row in transactions if timestamp(previous['observed_at']) < row['posted_at'] <= moment]
            text += '\n交易明细（按到账时间筛选；延迟到账可能与净变动不一致）：'
            if not rows:
                text += '\n暂无已到账交易明细'
            for row in rows:
                detail = f"\n{row['project']}（{row['kind']}）：{row['amount']:+.2f} 元\n交易：{row['transaction_at']:%Y-%m-%d %H:%M:%S}\n到账：{row['posted_at']:%Y-%m-%d %H:%M:%S}"
                if len((text+detail).encode('utf-16-le')) // 2 > 4096:
                    queue_message(state, text)
                    text = '校园卡交易明细（续）'
                text += detail
        queue_message(state, text)
    state['baseline'] = {'yuan':format(amount,'.2f'), 'observed_at':moment.isoformat()}
    state['failure'] = None


def record_failure(state, kind, moment):
    if state['failure'] is None or state['failure']['kind'] != kind:
        state['failure'] = {'kind':kind, 'count':0, 'since':moment.isoformat(), 'alerted':False}
    failure = state['failure']
    failure['count'] += 1
    if not failure['alerted'] and (kind == 'session' or failure['count'] >= 3):
        queue_message(state, f"校园卡余额查询故障\n开始时间：{failure['since']}\n连续失败：{failure['count']} 次\n有效余额基准已保留。请检查网络及本人登录配置，必要时在 App 重新登录并更新 token 与 uuToken。")
        failure['alerted'] = True


def confirm_sent(state, event_id, message_id):
    if not state['pending'] or state['pending'][0]['id'] != event_id or type(message_id) is not int or message_id <= 0:
        raise ValueError('发送结果不能关联待发消息')
    state['pending'].pop(0)
    state['sent'].append({'id':event_id,'message_id':message_id})
    # ponytail: 保留最近 128 个确认结果，历史审计可从 state 分支提交记录读取。
    state['sent'] = state['sent'][-128:]


class TelegramError(RuntimeError):
    def __init__(self, code, retry_after=None):
        super().__init__(f'Telegram 请求失败：{code}')
        self.code = code
        self.retry_after = retry_after


def send_message(token, chat, text):
    if not in_window(now()):
        raise OutsideWindowError('当前时间不允许发送')
    connection = http.client.HTTPSConnection('api.telegram.org', timeout=20)
    try:
        payload = json.dumps({'chat_id':chat, 'text':text}, ensure_ascii=False).encode()
        if not in_window(now()):
            raise OutsideWindowError('当前时间不允许发送')
        connection.request('POST','/bot'+token+'/sendMessage',payload,{'Content-Type':'application/json'})
        response = connection.getresponse()
        body = response.read(1_048_577)
        if len(body) > 1_048_576:
            raise TelegramError('response-too-large')
        try:
            value = json.loads(body)
        except (ValueError, UnicodeError) as error:
            raise TelegramError('invalid-json') from error
        if not isinstance(value, dict) or response.status != 200 or value.get('ok') is not True:
            code = value.get('error_code', response.status) if isinstance(value, dict) else response.status
            wait = value.get('parameters', {}).get('retry_after') if isinstance(value, dict) and isinstance(value.get('parameters', {}), dict) else None
            if wait is not None and (type(wait) is not int or wait < 1):
                wait = None
            raise TelegramError(code, wait)
        result = value.get('result')
        if not isinstance(result, dict) or type(result.get('message_id')) is not int or result['message_id'] <= 0 or not isinstance(result.get('chat'), dict) or str(result['chat'].get('id')) != chat:
            raise TelegramError('invalid-result')
        return result['message_id']
    finally:
        connection.close()


def drain_pending(repo, state, token, chat, retry_blocked=False):
    fingerprint = hashlib.sha256((token+'|'+chat).encode()).hexdigest()
    for attempt in range(3):
        if not state['pending'] or not in_window(now()):
            return
        item = state['pending'][0]
        if item['blocked'] == fingerprint and not retry_blocked:
            print('Telegram 凭证或权限故障仍未解除；待发消息已保留')
            return
        if item['retry_at'] is not None and timestamp(item['retry_at']) > now():
            return
        try:
            message_id = send_message(token, chat, item['text'])
        except OutsideWindowError:
            return
        except (TelegramError, OSError, http.client.HTTPException) as error:
            item['attempts'] += 1
            permanent = isinstance(error, TelegramError) and error.code in (400,401,403,404)
            wait = error.retry_after if isinstance(error, TelegramError) and error.retry_after is not None else min(300, 2**min(item['attempts'], 8))
            item['blocked'] = fingerprint if permanent else None
            item['retry_at'] = None if permanent else (now()+timedelta(seconds=wait)).isoformat()
            save_state(repo, state)
            print('Telegram 发送失败；待发消息已持久保存')
            if permanent or wait > 5 or attempt == 2:
                return
            time.sleep(wait)
        else:
            confirm_sent(state, item['id'], message_id)
            save_state(repo, state)
            print('Telegram 消息已确认并保存结果')
    # ponytail: 每次执行最多处理 3 次发送或重试，剩余消息由下次定时任务继续处理。


def run(config_path, repo, env_file=None, retry_blocked=False):
    if not in_window(now()):
        print('当前为北京时间夜间，已跳过查询和发送')
        return 0
    config = load_config(config_path)
    token, chat = telegram_config(env_file)
    state = load_state(repo, identity(config, chat))
    if not in_window(now()):
        return 0
    failed = False
    try:
        amount = query_balance(config)
        moment = now()
        previous = state['baseline']
        transactions = None
        # ponytail: 仅随净余额变化查询明细；补发延迟到账记录需要独立交易游标。
        if previous is not None and Decimal(previous['yuan']) != amount:
            transactions = query_transactions(config, timestamp(previous['observed_at']), moment)
    except OutsideWindowError:
        return 0
    except (ValueError, OSError, http.client.HTTPException):
        record_failure(state, 'query', now())
        print('余额或交易明细查询失败；有效基准保留')
        failed = True
    else:
        record_balance(state, amount, moment, transactions)
        print('余额查询成功，观察结果已生成')
    save_state(repo, state)
    drain_pending(repo, state, token, chat, retry_blocked)
    if failed or state['pending']:
        return 1
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='本人校园卡单次查询与 Telegram 变化通知')
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--state-dir', required=True, type=Path)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--retry-blocked', action='store_true')
    args = parser.parse_args()
    try:
        code = run(args.config, args.state_dir, args.env_file, args.retry_blocked)
    except (ValueError, RuntimeError, OSError, http.client.HTTPException) as error:
        print(json.dumps({'status':'failed','type':type(error).__name__,'message':'监测终止，未清空有效状态','suggestion':'检查配置、远端状态和网络；状态 checkout 异常时重新检出 state 分支'},ensure_ascii=False))
        code = 1
    raise SystemExit(code)
