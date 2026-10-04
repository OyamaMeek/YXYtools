import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from client import load_config
from monitor import in_window, now, run


def main():
    if not in_window(now()):
        print('北京时间夜间，未读取凭证或发起业务请求')
        return 0
    value = os.environ.get('YXY_LOGIN_CONFIG')
    if not value:
        raise ValueError('YXY_LOGIN_CONFIG 未配置')
    retry = os.environ.get('RETRY_BLOCKED', 'false')
    if retry not in {'true','false'}:
        raise ValueError('RETRY_BLOCKED 需为 true 或 false')
    config = json.loads(value)
    directory = Path('work')
    directory.mkdir(exist_ok=True)
    path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory, delete=False) as stream:
            path = Path(stream.name)
            json.dump(config, stream, ensure_ascii=False)
        load_config(path)
        return run(path, Path(os.environ['MONITOR_STATE_DIR']), retry_blocked=retry=='true')
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        code = main()
    except (ValueError, RuntimeError, OSError) as error:
        print(json.dumps({'status':'failed','type':type(error).__name__,'message':'Actions 监测终止','suggestion':'检查 Secrets、state 分支及网络'},ensure_ascii=False))
        code = 1
    raise SystemExit(code)
