import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Public checkout has scripts adjacent to tests; local template has the production ancestor.
if not (ROOT / 'scripts/knowledge_cards.py').exists():
    ROOT = Path(__file__).resolve().parents[4]

def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

kc = module('knowledge_cards')
sync = module('obsidian_sync')

class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'days/2026-01-01/test').mkdir(parents=True)
        self.source = self.root / 'days/2026-01-01/test/notes.md'
        self.source.write_text('Observed output')
        (self.root / 'knowledge-cards').mkdir()
        self.card = self.root / 'knowledge-cards/example.md'
        fields = {'id':'example', 'type':'实测', 'status':'局部验证', 'created':'2026-01-01', 'updated':'2026-01-01', 'tags':['测试'], 'source_files':[str(self.source.relative_to(self.root))]}
        self.card.write_text('---\n' + '\n'.join(k + ': ' + json.dumps(v,ensure_ascii=False) for k,v in fields.items()) + '\n---\n# Example\n' + '\n'.join('## '+s+'\n'+('限定证据与可复用步骤。'*10) for s in ['适用场景','发生了什么','可复用做法','边界与反例','来源与证据','复查触发']))

    def test_source_change_requires_review(self):
        self.assertEqual(kc.build(self.root)['stale'], [])
        self.source.write_text('Changed evidence')
        self.assertEqual(kc.build(self.root)['stale'], ['example'])
        self.assertEqual(kc.build(self.root)['stale'], ['example'])

    def test_receipt_hash_rejects_unread_revision(self):
        receipt = self.root / 'receipt.json'
        receipt.write_text(json.dumps([{'path':str(self.source.relative_to(self.root)), 'sha256':kc.sha(self.source), 'disposition':'提炼', 'reason':'Reviewed original evidence', 'cards':['example']}]))
        self.source.write_text('Changed after reading')
        with self.assertRaises(ValueError):kc.review(self.root,receipt)

    def test_processed_source_reenters_queue(self):
        rel=str(self.source.relative_to(self.root)); receipt=self.root/'receipt.json'
        receipt.write_text(json.dumps([{'path':rel,'sha256':kc.sha(self.source),'disposition':'提炼','reason':'Read','cards':['example']}]))
        kc.review(self.root,receipt)
        self.assertEqual(kc.scan(self.root)['pending'],[])
        self.source.write_text('New result')
        self.assertEqual(len(kc.scan(self.root)['pending']),1)

    def test_frontmatter_preserved_and_edit_protected(self):
        vault=self.root/'vault';(vault/'.obsidian').mkdir(parents=True)
        registry=self.root/'registry.json';registry.write_text(json.dumps({'vaults':{'test':{'path':str(vault)}}}))
        config=self.root/'config.json';config.write_text(json.dumps({'registry':str(registry),'vault_id':'test','sources':[{'from':'knowledge-cards','to':'cards'}]}))
        self.card.write_text(self.card.read_text()+'\n| Link |\n|---|\n| [self](example.md) |\n')
        sync.run(self.root,config);dest=vault/'矩阵运营/cards/example.md'
        metadata,body=kc.metadata(dest)
        self.assertIn('\\|self]]', body)
        self.assertEqual(metadata['id'],'example')
        self.assertEqual(metadata['sync_managed'],True)
        self.assertIn('# Example',body)
        self.assertFalse(body.lstrip().startswith('---'))
        self.assertEqual(sync.run(self.root,config)['changed'],0)
        dest.write_text('Personal edit');self.card.write_text(self.card.read_text()+'\nNew evidence')
        self.assertEqual(sync.run(self.root,config)['status'],'conflict')
        self.assertEqual(dest.read_text(),'Personal edit')
