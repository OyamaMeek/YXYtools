import argparse
import copy
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from client import load_config, parse_balance, query_balance, sign_form


def main():
    parser = argparse.ArgumentParser(description='使用真实登录及余额证据检查客户端；会发起一次本人只读查询')
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--login-evidence', required=True, type=Path)
    parser.add_argument('--success-evidence', required=True, type=Path)
    parser.add_argument('--failure-evidence', required=True, type=Path)
    parser.add_argument('--expected-yuan', required=True, type=Decimal)
    args = parser.parse_args()
    config = load_config(args.config)
    login = json.loads(args.login_evidence.read_text())[0]
    form = {key:value[0] for key,value in login['body'].items()}
    assert sign_form(form) == login['headers']['sign'], '完整登录签名与真实证据不一致'
    success = json.loads(args.success_evidence.read_text())
    assert parse_balance(success, config['wallet_no']) == args.expected_yuan
    failure = json.loads(args.failure_evidence.read_text())['response']
    for value, wallet in [(failure, config['wallet_no']), (success, 'invalid-wallet')]:
        try:
            parse_balance(value, wallet)
        except ValueError:
            pass
        else:
            raise AssertionError('错误响应或卡片被接受')
    altered = copy.deepcopy(success)
    card = next(item for item in altered['data']['authCardMoneyList'] if item['walletNo'] == config['wallet_no'])
    card['cardMoney'] = '0.00'
    assert parse_balance(altered, config['wallet_no']) == Decimal('0')
    for invalid in ['NaN', 'Infinity', '-1', '1.001', None, 10.17]:
        card['cardMoney'] = invalid
        try:
            parse_balance(altered, config['wallet_no'])
        except ValueError:
            pass
        else:
            raise AssertionError('非法金额被接受')
    assert query_balance(config) == args.expected_yuan, '新签名实时查询余额不同'
    print('真实登录签名、余额解析、错误拒绝及新签名实时查询通过')


if __name__ == '__main__':
    main()
