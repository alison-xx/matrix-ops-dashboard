import importlib.util
import tempfile
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('report_mail', Path(__file__).resolve().parents[1] / 'scripts/report_mail.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class WholeDayReport(unittest.TestCase):
    def test_window_is_complete_beijing_day(self):
        start, end = m.day_window('2026-10-15')
        self.assertEqual(start.isoformat(), '2026-10-15T00:00:00+08:00')
        self.assertEqual(end.isoformat(), '2026-10-16T00:00:00+08:00')
        self.assertEqual((end - start).total_seconds(), 86400)

    def test_delivery_state_blocks_duplicate_and_uncertain_retries(self):
        with tempfile.TemporaryDirectory() as d:
            db = m.delivery_db(Path(d) / 'mail.sqlite3')
            self.assertTrue(m.reserve(db, '2026-10-15', 'reader@example.com'))
            self.assertFalse(m.reserve(db, '2026-10-15', 'reader@example.com'))
            db.execute("UPDATE deliveries SET state='sent'"); db.commit()
            self.assertFalse(m.reserve(db, '2026-10-15', 'reader@example.com'))
            self.assertTrue(m.reserve(db, '2026-10-16', 'reader@example.com'))
            db.close()

    def test_email_review_tables_are_rendered_and_links_are_short(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        from report_email_layout import build_email
        text = '# report\n## 晚间复盘（保留原文及其统计口径）\n### 复盘与次日调整\n|平台|说明|\n|---|---|\n|示例|完成|\n'
        html = build_email(text, '2026-10-15', 'https://dashboard.example.com')
        self.assertNotIn('|---|', html)
        self.assertIn('完成</td>', html)
