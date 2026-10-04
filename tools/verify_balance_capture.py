import argparse
import hashlib
import http.client
import io
import json
import subprocess
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs


def captured_body(data, offset, event):
    end = data.index(b"\r\n\r\n", offset) + 4
    session = data[offset - 4:offset]
    if int.from_bytes(data[offset - 8:offset - 5], "big") != end - offset:
        raise ValueError("HTTP 头部长度不符")
    marker = bytes([event]) + session
    # ponytail: 仅验证指定样本的单段正文，其他导出格式需要使用对应格式的工具。
    start = data.index(marker, end, end + 1024 * 1024) - 3
    size = int.from_bytes(data[start:start + 3], "big")
    body = data[start + 8:start + 8 + size]
    if len(body) != size:
        raise ValueError("正文不完整")
    line_end = data.index(b"\r\n", offset)
    headers = http.client.parse_headers(io.BytesIO(data[line_end + 2:end]))
    return session, headers, body


def main():
    parser = argparse.ArgumentParser(description="离线核验本次余额抓包，不发送网络请求或输出凭证")
    parser.add_argument("capture", type=Path)
    parser.add_argument("--expected-yuan", required=True, type=Decimal)
    args = parser.parse_args()
    data = args.capture.read_bytes()
    if hashlib.sha256(data).hexdigest() != "eb282a6b92261895e3fb117a317cc0e28a3ba7aa5f26855238b22138183d376e":
        raise ValueError("样本哈希不同，固定证据偏移不适用")
    req_id, req_headers, body = captured_body(data, 16508084, 4)
    res_id, res_headers, compressed = captured_body(data, 16537017, 7)
    if req_id != res_id or len(body) != int(req_headers["Content-Length"]):
        raise ValueError("请求与响应会话或长度不符")
    if res_headers["Content-Encoding"] != "br":
        raise ValueError("响应压缩类型不符")
    decoded = subprocess.run(["/opt/homebrew/bin/brotli", "-d", "-c"], input=compressed, capture_output=True, check=True).stdout
    response = json.loads(decoded)
    if response.get("success") is not True or response.get("statusCode") != 0:
        raise ValueError("余额业务查询失败")
    payload = response["data"]
    cards = payload["authCardMoneyList"]
    if len(cards) != 1 or payload["firstWalletNo"] != cards[0]["walletNo"]:
        raise ValueError("目标卡片无法唯一关联")
    money = Decimal(cards[0]["cardMoney"])
    if not money.is_finite() or money < 0 or money * 100 != (money * 100).to_integral_value():
        raise ValueError("余额金额非法")
    if not args.expected_yuan.is_finite() or money != args.expected_yuan:
        raise ValueError("接口余额与同期 App 余额不一致")
    if Decimal(payload["availableBalance"]) != money:
        raise ValueError("可用余额与指定卡余额不一致")
    params = parse_qs(body.decode("ascii"), strict_parsing=True)
    print(json.dumps({"status": "passed", "request_fields": list(params), "cookie_present": "Cookie" in req_headers, "sign_present": "sign" in req_headers, "card_count": len(cards), "app_balance_matches": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
