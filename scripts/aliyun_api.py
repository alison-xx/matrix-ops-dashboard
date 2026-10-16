#!/usr/bin/env python3
"""阿里云 OpenAPI（RPC 风格，签名 V1）最小客户端。AK/SK 在 config/.env 的 ALIYUN_AK_ID / ALIYUN_AK_SECRET。

用于：智能媒体服务 IMS（云剪辑 ice.cn-shanghai.aliyuncs.com）、STS 身份确认等。
密钥只从 .env 读，不打印、不写进日志。

用法: .venv/bin/python scripts/aliyun_api.py whoami
"""
import base64, datetime as dt, hashlib, hmac, json, sys, urllib.parse, urllib.request, uuid, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import env


def _q(s):
    return urllib.parse.quote(str(s), safe='~')


def call(endpoint, action, version, params=None, method='POST', timeout=60):
    e = env()
    p = {'Action': action, 'Version': version, 'Format': 'JSON', 'AccessKeyId': e['ALIYUN_AK_ID'],
         'SignatureMethod': 'HMAC-SHA1', 'SignatureVersion': '1.0', 'SignatureNonce': uuid.uuid4().hex,
         'Timestamp': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
    for k, v in (params or {}).items():
        p[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
    canon = '&'.join(f'{_q(k)}={_q(p[k])}' for k in sorted(p))
    sts = f'{method}&%2F&{_q(canon)}'
    p['Signature'] = base64.b64encode(hmac.new((e['ALIYUN_AK_SECRET'] + '&').encode(), sts.encode(), hashlib.sha1).digest()).decode()
    body = urllib.parse.urlencode(p).encode()
    req = urllib.request.Request(f'https://{endpoint}/', data=body if method == 'POST' else None, method=method,
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if method == 'GET':
        req = urllib.request.Request(f'https://{endpoint}/?{body.decode()}', method='GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as ex:
        return {'_http': ex.code, **json.loads(ex.read() or b'{}')}


if __name__ == '__main__':
    if sys.argv[1:] == ['whoami']:
        d = call('sts.aliyuncs.com', 'GetCallerIdentity', '2015-04-01')
        print(json.dumps({k: d.get(k) for k in ('AccountId', 'IdentityType', 'Arn', 'Code', 'Message', '_http')}, ensure_ascii=False))
