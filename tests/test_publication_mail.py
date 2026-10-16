import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

class PublicationMailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Public bundle has example config only; do not create a production config.
        from unittest.mock import patch
        import json
        original = Path.read_text
        def fixture_read(path, *args, **kwargs):
            if path.name == 'schedule.json' and not path.exists():
                return json.dumps({'accounts':{'channels':{'publish_via':'email'},'x':{'account_id':'123','handle':'sample'}}})
            return original(path, *args, **kwargs)
        with patch.object(Path,'read_text',autospec=True,side_effect=fixture_read):
            import ops

    def test_package_contains_copy_video_and_cover_with_correct_mime(self):
        import publication_mail as m
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'clip.mp4').write_bytes(b'video')
            (root/'cover.jpg').write_bytes(b'image')
            import json
            p=root/'post.json'; p.write_text(json.dumps({'title':'演示标题','description':'演示正文','video':'clip.mp4','cover':'cover.jpg'}))
            post, assets, revision = m.load_package(p)
            msg=m.build_message(post, assets, 'operator@example.com', 'sender@example.com', 'test-1')
            self.assertIn('演示正文', msg.get_body(preferencelist=('plain',)).get_content())
            parts={x.get_filename():x.get_content_type() for x in msg.iter_attachments()}
            self.assertEqual(parts['clip.mp4'],'video/mp4')
            self.assertEqual(parts['cover.jpg'],'image/jpeg')
            self.assertIn('发布文案.txt', parts)
            (root/'clip.mp4').write_bytes(b'changed-video')
            self.assertNotEqual(revision,m.load_package(p)[2])

    def test_missing_audio_qc_stops_before_smtp(self):
        import publication_mail as m
        from unittest.mock import patch
        import json
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'clip.mp4').write_bytes(b'video'); (root/'cover.jpg').write_bytes(b'cover')
            p=root/'post.json';p.write_text(json.dumps({'title':'demo','description':'copy','video':'clip.mp4','cover':'cover.jpg'}))
            with patch('ops.video_gate',return_value=None), patch.object(m,'delivery_db',side_effect=AssertionError('must stop before mail database')):
                with self.assertRaisesRegex(ValueError,'声音质检'):
                    m.send(p,'item')

    def test_uncertain_delivery_cannot_be_automatically_resent(self):
        import publication_mail as m
        with tempfile.TemporaryDirectory() as d:
            c=m.delivery_db(Path(d)/'mail.sqlite3')
            self.assertTrue(m.reserve(c,'item','operator@example.com','revision','<test>'))
            self.assertFalse(m.reserve(c,'item','operator@example.com','revision','<new>'))
            c.execute("UPDATE deliveries SET state='sent'");c.commit()
            self.assertFalse(m.reserve(c,'item','operator@example.com','revision','<new>'))
            c.close()

    def test_manual_email_route_blocks_platform_submit(self):
        import ops
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            with patch.object(ops,'DB',Path(d)/'ops.sqlite3'):
                c=ops.connect()
                c.execute("INSERT INTO items(id,slot,status) VALUES('item','channels','ready')")
                with patch.dict(ops.SCHED['accounts']['channels'],{'publish_via':'email'}):
                    with self.assertRaisesRegex(ValueError,'邮件|手动'):
                        ops.submit(c,'item')
                self.assertEqual(c.execute("SELECT status FROM items WHERE id='item'").fetchone()[0],'ready')
                c.close()

    def test_web_route_blocks_cli_before_any_submission(self):
        from unittest.mock import patch
        import ops
        with tempfile.TemporaryDirectory() as d:
            with patch.object(ops, 'DB', Path(d)/'ops.sqlite3'):
                c=ops.connect()
                c.execute("INSERT INTO items(id,slot,status) VALUES('web-item','kuaishou','ready')")
                with patch.dict(ops.SCHED['accounts'], {'kuaishou':{'publish_via':'web'}}), patch.object(ops,'cli',side_effect=AssertionError('must not send')):
                    with self.assertRaisesRegex(ValueError,'网页'):
                        ops.submit(c,'web-item')
                c.close()

if __name__=='__main__':unittest.main()
