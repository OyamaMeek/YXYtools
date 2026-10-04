import http.client
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from monitor import in_window, now, telegram_config


def main():
    if not in_window(now()):
        print('北京时间夜间，跳过 Telegram 连接检查')
        return
    token, _ = telegram_config()
    connection = http.client.HTTPSConnection('api.telegram.org', timeout=20)
    try:
        connection.request('POST','/bot'+token+'/getMe')
        response = connection.getresponse()
        body = response.read(1_048_577)
        if response.status != 200 or len(body) > 1_048_576:
            raise ValueError('Telegram 连接检查失败')
        value = json.loads(body)
        if not isinstance(value, dict) or value.get('ok') is not True or not isinstance(value.get('result'), dict) or value['result'].get('is_bot') is not True or str(value['result'].get('id')) != token.split(':',1)[0]:
            raise ValueError('Telegram 身份检查失败')
        print('Telegram 托管运行器连接检查通过；未发送消息')
    finally:
        connection.close()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, http.client.HTTPException):
        print('Telegram 连接检查失败，请检查 Bot 配置或网络')
        raise SystemExit(1)
