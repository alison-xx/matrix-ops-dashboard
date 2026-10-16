import importlib.util
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('dashboard_server', Path(__file__).resolve().parents[1] / 'dashboard/server.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

class PublicationEvidence(unittest.TestCase):
    def test_material_email_is_waiting_for_operator_not_published(self):
        item = s.enrich_items([{'id':'mail','status':'manual_pending','mode':'email'}], {})[0]
        self.assertEqual(item['bucket'], 'warn')
        self.assertEqual(item['status_label'], '待本人手动发布')

    def test_elapsed_schedule_still_needs_confirmation(self):
        rows = [{'id': 'scheduled', 'status': 'scheduled', 'day': '2020-01-01', 'due': '2020-01-01T09:00:00+08:00', 'slot': 'demo'}]
        item = s.enrich_items(rows, {})[0]
        self.assertEqual(item['bucket'], 'warn')
        self.assertEqual(item['flag'], 'unconfirmed')

    def test_platform_success_and_verified_public_are_distinct(self):
        rows = [{'id': st, 'status': st} for st in ('success', 'public', 'web')]
        self.assertEqual([i['bucket'] for i in s.enrich_items(rows, {})], ['done'] * 3)

    def test_withdrawn_is_excluded_from_live_queue(self):
        item = s.enrich_items([{'id': 'old', 'status': 'withdrawn'}], {})[0]
        self.assertEqual(item['bucket'], 'muted')
        self.assertEqual(item['status_label'], '已撤销')

    def test_report_list_prefers_full_day_and_omits_regenerated_drafts(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            original = s.REPORTS
            try:
                s.REPORTS = Path(d)
                for name in ('2026-10-15.md', '2026-10-15.full.md', '2026-10-15.regen.md'):
                    (Path(d) / name).write_text('# report')
                reports = s.reports_list()
                self.assertEqual(len(reports), 1)
                self.assertEqual(reports[0]['date'], '2026-10-15')
                self.assertTrue(reports[0]['full_day'])
                self.assertEqual(s.report_path('2026-10-15').name, '2026-10-15.full.md')
            finally:
                s.REPORTS = original

    def test_scheduled_zhihu_answer_is_not_public(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            original = s.DAYS
            try:
                s.DAYS = Path(d)
                folder = Path(d) / '2099-01-01'; folder.mkdir()
                (folder / 'zhihu-answers.md').write_text('|时间|问题|链接|备注|\n|---|---|---|---|\n|21:00（定时）|测试问题|https://www.zhihu.com/question/1/answer/2|原生定时|')
                item = s.zhihu_answers('2099-01-01')[0]
                self.assertEqual(item['bucket'], 'queue')
                self.assertEqual(item['status'], 'scheduled')
            finally:
                s.DAYS = original

    def test_stale_web_queue_is_resolved_by_actual_success(self):
        rows = [
            {'id': 'old', 'status': 'web_pending', 'day': '2020-01-01', 'due': '2020-01-01T09:00:00+08:00', 'slot': 'demo', 'title': '同一篇'},
            {'id': 'new', 'status': 'public', 'day': '2020-01-01', 'slot': 'demo', 'title': '同一篇'}]
        self.assertEqual(s.enrich_items(rows, {})[0]['superseded_by'], 'new')
