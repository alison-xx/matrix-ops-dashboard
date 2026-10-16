import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ai_video as v


class VideoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'shot.json'
        self.shot = {k: '镜头描述' for k in ('subject', 'action', 'camera', 'lighting', 'composition', 'continuity')}
        self.shot.update(seconds=6, aspect_ratio='9:16')
        self.path.write_text(json.dumps(self.shot))
        self.patches = [patch.object(v, 'config', return_value={'AGNES_API_KEY': 'demo', 'DUOMI_API_KEY': 'demo'}), patch.object(v, 'reserve')]
        for p in self.patches: p.start()

    def tearDown(self):
        for p in self.patches: p.stop()
        self.tmp.cleanup()

    def test_flash_and_veo_contract(self):
        self.assertEqual(v.payload(self.shot, 'agnes')['size'], '720P')
        self.assertEqual(v.payload(self.shot, 'agnes')['model'], 'agnes-video-2.5-flash')
        self.assertEqual(v.payload(self.shot, 'duomi')['quality'], '1080p')

    def test_reject_then_fallback_only_once(self):
        error = urllib.error.HTTPError('url', 403, 'denied', {}, None)
        with patch.object(v, 'request', side_effect=[error, {'id': 'duomi-1'}]) as req:
            a = v.run(self.path)
            v.run(self.path)
        self.assertEqual(req.call_count, 2)
        self.assertEqual(a['attempts'][-1]['provider'], 'duomi')

    def test_timeout_never_resubmits(self):
        with patch.object(v, 'request', side_effect=TimeoutError) as req:
            self.assertEqual(v.run(self.path)['status'], 'uncertain')
            v.run(self.path, poll=True)
        self.assertEqual(req.call_count, 1)

    def test_query_failure_never_falls_back(self):
        with patch.object(v, 'request', side_effect=[{'video_id': 'v1'}, TimeoutError]):
            v.run(self.path)
            a = v.run(self.path, poll=True)
        self.assertEqual(len(a['attempts']), 1)

    def test_download_failure_resumes_same_task(self):
        with patch.object(v, 'request', side_effect=[{'video_id': 'v1'}, {'status': 'completed', 'url': 'https://example.com/v.mp4'}, {'status': 'completed', 'url': 'https://example.com/v.mp4'}]), patch.object(v, 'download', side_effect=[TimeoutError, {'duration': 6}]):
            v.run(self.path)
            with self.assertRaises(TimeoutError): v.run(self.path, poll=True)
            a = v.run(self.path, poll=True)
        self.assertEqual(a['status'], 'downloaded')
        self.assertEqual(len(a['attempts']), 1)

    def test_modified_prompt_blocked(self):
        with patch.object(v, 'request', return_value={'video_id': 'v1'}): v.run(self.path)
        self.shot['camera'] = '新镜头'
        self.path.write_text(json.dumps(self.shot))
        with self.assertRaises(ValueError): v.run(self.path)

    def test_unsupported_references_blocked(self):
        with self.assertRaises(ValueError): v.payload(dict(self.shot, images=['https://example.com/a.png']), 'agnes')

    def test_explicit_task_failure_falls_back(self):
        with patch.object(v, 'request', side_effect=[{'video_id': 'v1'}, {'status': 'failed'}, {'id': 'v2'}]):
            v.run(self.path)
            a = v.run(self.path, poll=True)
        self.assertEqual(a['attempts'][0]['status'], 'failed')
        self.assertEqual(a['attempts'][1]['provider'], 'duomi')

if __name__ == '__main__': unittest.main()
