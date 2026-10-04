import argparse
import base64
import gzip
import hashlib
import hmac
import http.client
import json
import re
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode


def load_config(path):
    config = json.loads(Path(path).read_text())
    fields = {'school_name', 'ym_id', 'device_id', 'token', 'session_secret', 'wallet_no'}
    if not isinstance(config, dict) or not fields.issubset(config):
        raise ValueError('登录配置字段不完整')
    if any(not isinstance(config[key], str) or not config[key] for key in fields):
        raise ValueError('登录配置字段必须为非空字符串')
    if config['school_name'] != '杭州电子科技大学信息工程学院':
        raise ValueError('登录配置学校不符')
    if not re.fullmatch(r'[0-9]{3,20}', config['ym_id']) or int(config['ym_id']) >= 2**64:
        raise ValueError('账户标识非法')
    if not re.fullmatch(r'ym-[0-9a-f]{32}', config['device_id']):
        raise ValueError('设备标识非法')
    return config


def sign_form(form, session_secret=None):
    if not isinstance(form, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k,v in form.items()):
        raise ValueError('签名参数必须为字符串映射')
    device = form['deviceId']
    if session_secret is None:
        seed = device[:6]
    else:
        if not isinstance(session_secret, str) or not session_secret:
            raise ValueError('会话密钥缺失')
        user = form['ymId']
        if not user.isascii() or not user.isdigit() or len(user) < 3:
            raise ValueError('签名账户标识非法')
        seed = user[int(user[-2]):] + device[int(user[-3]):] + session_secret
    key = hashlib.sha256(seed.encode()).hexdigest()[32:].encode()
    message = '|'.join(form[key] for key in sorted(form) if key not in {'sign', 'qqfile', 'file'} and form[key])
    return base64.b64encode(hmac.digest(key, message.encode(), 'sha256')).decode()


def parse_balance(response, wallet_no):
    if not isinstance(response, dict) or response.get('success') is not True or type(response.get('statusCode')) is not int or response['statusCode'] != 0:
        raise ValueError('余额业务查询失败；请检查会话凭证')
    data = response.get('data')
    if not isinstance(data, dict) or not isinstance(data.get('authCardMoneyList'), list):
        raise ValueError('余额响应字段缺失')
    cards = data['authCardMoneyList']
    if any(not isinstance(card, dict) for card in cards):
        raise ValueError('卡片响应结构非法')
    selected = [card for card in cards if card.get('walletNo') == wallet_no]
    if len(selected) != 1:
        raise ValueError('指定卡片缺失或重复')
    value = selected[0].get('cardMoney')
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]{1,2})?', value):
        raise ValueError('余额必须为以元计的十进制字符串')
    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise ValueError('余额金额非法') from error
    if not amount.is_finite() or amount < 0:
        raise ValueError('余额金额非法')
    return amount


def query_balance(config):
    form = {'appVersion':'740', 'deviceId':config['device_id'], 'nt':str(time.time_ns() // 1_000_000), 'platform':'YUNMA_APP', 'token':config['token'], 'ymId':config['ym_id']}
    headers = {'Content-Type':'application/x-www-form-urlencoded; charset=utf-8', 'Accept-Encoding':'identity', 'sign':sign_form(form, config['session_secret'])}
    connection = http.client.HTTPSConnection('compus.xiaofubao.com', timeout=20)
    try:
        connection.request('POST', '/routeauth/auth/route/auth/user/getMultiCardMoney', urlencode(form), headers)
        response = connection.getresponse()
        payload = response.read(1_048_577)
        if response.status != 200:
            raise ValueError(f'余额 HTTP 查询失败：{response.status}')
        if len(payload) > 1_048_576:
            raise ValueError('余额响应超过大小限制')
        encoding = response.getheader('Content-Encoding')
        if encoding == 'gzip':
            payload = gzip.decompress(payload)
        elif encoding not in (None, 'identity'):
            raise ValueError('服务端未遵守响应压缩协商')
        if len(payload) > 1_048_576:
            raise ValueError('解压后的余额响应超过大小限制')
        return parse_balance(json.loads(payload), config['wallet_no'])
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='查询本人指定校园卡余额')
    parser.add_argument('--config', required=True, type=Path)
    args = parser.parse_args()
    print(format(query_balance(load_config(args.config)), '.2f'))
