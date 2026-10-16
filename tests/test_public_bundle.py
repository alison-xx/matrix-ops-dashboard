import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]


def module(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


class PublicBundleTests(unittest.TestCase):
    def test_scanner_rejects_credentials_without_echo(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / 'scripts').mkdir()
            script = root / 'scripts/check_public_tree.py'
            script.write_bytes((ROOT / 'scripts/check_public_tree.py').read_bytes())
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            secret = 'sk' + '-' + 'syntheticfixture' * 3
            (root / 'leak.txt').write_text(secret)
            r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('api-key', r.stdout)
            self.assertNotIn(secret, r.stdout)
            (root / 'leak.txt').unlink()
            r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_lint_blocks_hype_and_accepts_plain_copy(self):
        lint = module('content_lint', 'scripts/lint_content.py')
        # Exercise without optional host-installed prose skills.
        with mock.patch.object(lint, 'prose_checks', return_value=([], {})):
            with tempfile.TemporaryDirectory() as td:
                p = pathlib.Path(td) / 'payload.json'
                obj = {'platforms': ['新浪微博'], 'publishType': 'imageText', 'publishArgs': {'accountForms': [{'contentPublishForm': {'title': '工具笔记', 'description': '我把同一份文件交给两个工具处理，分别记录输入和输出。一个能保留表格，另一个需要重新排版。你更看重哪一项？ #工具实测#'}}]}}
                p.write_text(json.dumps(obj))
                self.assertFalse(lint.lint(p)['errors'])
                obj['publishArgs']['accountForms'][0]['contentPublishForm']['title'] = '震惊，一键搞定'
                p.write_text(json.dumps(obj))
                self.assertTrue(lint.lint(p)['errors'])

    def test_sessions_reject_tampering_expiry_and_removed_users(self):
        server = module('dashboard_server', 'dashboard/server.py')
        # Deliberately synthetic format-valid phone for pure in-memory tests.
        phone = '1' + '0' * 10
        server.AUTH = {'secret': 'synthetic-session-key-' * 3, 'allow': [phone]}
        token, _ = server.make_session(phone)
        self.assertIsNotNone(server.read_session(server.COOKIE + '=' + token))
        self.assertIsNone(server.read_session(server.COOKIE + '=' + token + 'x'))
        with mock.patch.object(server.time, 'time', return_value=10 ** 12):
            self.assertIsNone(server.read_session(server.COOKIE + '=' + token))
        server.AUTH['allow'] = []
        self.assertIsNone(server.read_session(server.COOKIE + '=' + token))

    def test_unknown_phone_never_calls_provider(self):
        server = module('dashboard_auth', 'dashboard/server.py')
        server.AUTH = {'secret': 'synthetic-session-key-' * 3, 'allow': ['1' + '0' * 10]}
        with mock.patch.object(server, 'provider_call', side_effect=AssertionError('must not call provider')):
            status, _, _ = server.auth_login('1' + '2' * 10, '123456')
            self.assertEqual(status, 403)


if __name__ == '__main__':
    unittest.main()
