import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import video_scene

class VideoSceneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        (self.work / 'assets').mkdir()
        self.source = self.work / 'shot.mp4'
        self.source.write_bytes(b'video version one')
        self.sc = {'video':str(self.source),'source_kind':'ai','_start':10,'_end':12}
    def tearDown(self):
        self.tmp.cleanup()
    def approve(self):
        self.source.with_suffix('.review.json').write_text(json.dumps({'approved':True,'sha256':hashlib.sha256(self.source.read_bytes()).hexdigest()}))
    def test_changed_media_invalidates_review(self):
        self.approve()
        self.source.write_bytes(b'replacement video')
        with self.assertRaisesRegex(ValueError,'视觉复核'):
            video_scene.scene(self.sc, 1, self.work)
    def test_too_short_clip_is_not_looped(self):
        self.approve()
        with patch.object(video_scene,'probe',return_value={'duration':1.0}), patch.object(video_scene.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'短于场景'):
                video_scene.scene(self.sc,1,self.work)
            run.assert_not_called()
    def test_muted_timed_media(self):
        self.approve()
        with patch.object(video_scene,'probe',return_value={'duration':6.0}),patch.object(video_scene.subprocess,'run') as run:
            result=video_scene.scene(self.sc,1,self.work)
            self.assertIn('data-start="10.000"',result)
            self.assertIn('data-duration="2.000"',result)
            self.assertIn('data-volume="0"',result)
            self.assertIn('-an',run.call_args.args[0])
if __name__=='__main__': unittest.main()
