import datetime as dt
import importlib
import json
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
x=importlib.import_module('x_api')

class XApiTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.temp.name)
  self.db=sqlite3.connect(':memory:',isolation_level=None);self.db.row_factory=sqlite3.Row
  self.db.executescript('CREATE TABLE items(id TEXT PRIMARY KEY,day TEXT,slot TEXT,platform TEXT,account_id TEXT,publish_type TEXT,due TEXT,mode TEXT,status TEXT,payload TEXT,content_file TEXT,hash TEXT,title TEXT,updated TEXT,detail TEXT,url TEXT,url_verified INTEGER DEFAULT 0,task_id TEXT); CREATE TABLE events(n INTEGER PRIMARY KEY,at TEXT,item TEXT,kind TEXT,data TEXT);')
  self.policy={'enabled':True,'daily_usd_limit':1,'cycle_usd_limit':5,'cycle_start':'2026-10-16','max_writes_per_day':2,'ai_reply_approved':False}
  self.when=dt.datetime(2026,10,18,12,0,tzinfo=dt.timezone(dt.timedelta(hours=8)))
  self.p=self.root/'post.json'; self.post={'id':'x-20261018-case','day':'2026-10-18','time':'12:00','account':'sample','kind':'text','title':'验收条件','column':'抄作业','score':8,'body':'把任务交给 AI 前，先说明交付格式和验收条件。'}
  self.p.write_text(json.dumps(self.post,ensure_ascii=False)); self.review()
 def tearDown(self):self.db.close();self.temp.cleanup()
 def review(self):
  (self.root/'review.md').write_text('human-writing / humanizer-zh / content-compliance-checker: pass')
  (self.root/'review.json').write_text(json.dumps({'status':'pass','sha256':x.digest(self.p),'checks':['human-writing','humanizer-zh','content-compliance-checker']}))
 def add(self):return x.add(self.db,self.post['id'],'12:00',str(self.p),account={'account_id':'123','handle':'sample'},at=self.when)
 def test_prepared_draft_does_not_send_and_existing_schedule_is_not_overwritten(self):
  r=self.add();self.assertEqual(r['status'],'ready'); self.db.execute("UPDATE items SET status='scheduled' WHERE id=?",(self.post['id'],))
  with self.assertRaisesRegex(ValueError,'已存在'):self.add()
 def test_edited_post_invalidates_review(self):
  self.post['body']='正文被修改';self.p.write_text(json.dumps(self.post))
  with self.assertRaisesRegex(ValueError,'审核'):self.add()
 def test_content_duplicate_under_different_id_is_blocked(self):
  self.add();self.post['id']='x-20261018-second';self.p.write_text(json.dumps(self.post));self.review()
  with self.assertRaisesRegex(ValueError,'重复'):self.add()
 def test_disabled_config_never_calls_api(self):
  self.add();client=unittest.mock.Mock()
  out=x.submit(self.db,self.post['id'],client=client,policy={**self.policy,'enabled':False},at=self.when)
  self.assertEqual(out['status'],'blocked');client.request.assert_not_called()
 def test_wrong_identity_blocks_before_write(self):
  self.add();client=unittest.mock.Mock();client.request.return_value={'data':{'id':'999','username':'other'}}
  out=x.submit(self.db,self.post['id'],client=client,policy=self.policy,at=self.when)
  self.assertEqual(out['status'],'blocked');self.assertEqual(client.request.call_count,1)
 def test_post_timeout_is_uncertain_and_never_retried(self):
  self.add();client=unittest.mock.Mock();client.request.side_effect=[{'data':{'id':'123','username':'sample'}},TimeoutError('network')]
  out=x.submit(self.db,self.post['id'],client=client,policy=self.policy,at=self.when)
  self.assertEqual(out['status'],'uncertain');self.assertEqual(client.request.call_count,2)
  with self.assertRaisesRegex(ValueError,'ready'):x.submit(self.db,self.post['id'],client=client,policy=self.policy,at=self.when)
  self.assertEqual(client.request.call_count,2)
 def test_success_requires_matching_get_and_records_public(self):
  self.add();client=unittest.mock.Mock();client.request.side_effect=[{'data':{'id':'123','username':'sample'}},{'data':{'id':'888','text':self.post['body']}},{'data':{'id':'888','author_id':'123','text':self.post['body']}}]
  out=x.submit(self.db,self.post['id'],client=client,policy=self.policy,at=self.when)
  self.assertEqual(out['status'],'public');self.assertEqual(out['url'],'https://x.com/sample/status/888')
 def test_budget_stops_before_network(self):
  self.add();client=unittest.mock.Mock()
  out=x.submit(self.db,self.post['id'],client=client,policy={**self.policy,'daily_usd_limit':0.1},at=self.when)
  self.assertEqual(out['status'],'blocked');client.request.assert_not_called()
 def test_unapproved_ai_reply_and_mentions_are_blocked(self):
  with self.assertRaisesRegex(ValueError,'回复'):x.validate_post({**self.post,'reply_to':'456'},policy=self.policy)
  with self.assertRaisesRegex(ValueError,'@'):x.validate_post({**self.post,'body':'@someone 请看这个工作流'},policy=self.policy)
 def test_dispatch_routes_x_before_yixiaoer_proxy_checks(self):
  original_read=pathlib.Path.read_text
  def fixture_read(path,*args,**kwargs):
   if path.name=='schedule.json' and not path.exists():
    return json.dumps({'accounts':{'x':{'account_id':'123','handle':'sample'}}})
   return original_read(path,*args,**kwargs)
  with patch.object(pathlib.Path,'read_text',autospec=True,side_effect=fixture_read):
   import ops
  self.add()
  with patch.object(ops,'now',return_value=self.when),patch('playbook.proxy_health',side_effect=AssertionError('X must not probe yxer')),patch.object(x,'submit',return_value={'status':'blocked'}) as send:
   out=ops.dispatch(self.db)
  send.assert_called_once();self.assertEqual(out,[{'status':'blocked'}])

if __name__=='__main__':unittest.main()
