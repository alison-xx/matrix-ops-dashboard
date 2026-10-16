import datetime as dt
import importlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))


class CreatorWatchTests(unittest.TestCase):
    def setUp(self):
        self.w = importlib.import_module('creator_watch')
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.when = dt.datetime(2026, 10, 17, 12, tzinfo=dt.timezone(dt.timedelta(hours=8)))
        self.author = {'key': 'one', 'name': '讲AI', 'platform': 'douyin',
                       'endpoint': '/api/v1/douyin/app/v3/fetch_user_post_videos',
                       'method': 'GET', 'params': {'sec_user_id': 'public-id'},
                       'interval_minutes': 60, 'cost_usd': 0.01, 'enabled': True}
        self.config = {'enabled': True, 'max_calls_per_run': 20,
                       'max_cost_usd_per_day': 0.02, 'lookback_hours': 72,
                       'authors': [self.author]}
        self.lock = patch.object(self.w, 'LOCK_PATH', self.root / 'global.lock')
        self.lock.start()

    def tearDown(self):
        self.lock.stop()
        self.tmp.cleanup()

    def post(self, id='recent', age=1):
        return {'aweme_id': id, 'desc': '实际讲解AI', 'is_top': age > 72,
                'create_time': int((self.when - dt.timedelta(hours=age)).timestamp()),
                'statistics': {'digg_count': 3, 'play_count': 0}}

    def run_watch(self, response=None, **kwargs):
        fetch = kwargs.pop('fetcher', Mock(return_value=response or {'data': {'aweme_list': []}}))
        return self.w.run(self.config, self.root / 'state', self.root / 'out',
                          at=kwargs.pop('at', self.when), fetcher=fetch, **kwargs)

    def test_initial_window_second_run_and_persistent_candidates(self):
        payload = {'data': {'aweme_list': [self.post(), self.post('old-pin', 200),
                                           {'aweme_id': 'unknown', 'desc': '无时间'}]}}
        first = self.run_watch(payload)
        self.assertEqual([p['id'] for p in first['new']], ['recent'])
        self.assertEqual(first['candidates'][0]['status'], 'pending_review')
        second = self.run_watch(payload, at=self.when + dt.timedelta(hours=2))
        self.assertEqual(second['new'], [])
        self.assertEqual(len(second['candidates']), 1)
        state = json.loads((self.root / 'state/state.json').read_text())
        self.assertEqual(len(state['seen']), 3)
        self.assertTrue(pathlib.Path(first['candidates'][0]['evidence_path']).is_file())

    def test_same_id_cross_author_is_one_candidate_and_seen_dedup(self):
        self.config['authors'].append(dict(self.author, key='two'))
        out = self.run_watch({'data': {'aweme_list': [self.post()]}})
        self.assertEqual(len(out['new']), 1)
        self.assertEqual(len(out['candidates']), 1)
        self.assertEqual(set(out['candidates'][0]['source_author_keys']), {'one', 'two'})

    def test_failed_fetch_keeps_history_and_does_not_advance_success_time(self):
        self.run_watch({'data': {'aweme_list': [self.post()]}})
        fetcher = Mock(side_effect=RuntimeError('Bearer secret should never persist'))
        out = self.run_watch(fetcher=fetcher, at=self.when + dt.timedelta(hours=2))
        self.assertEqual(out['sources'][0]['status'], 'error')
        self.assertEqual(len(out['candidates']), 1)
        self.assertEqual(out['sources'][0]['last_fetch_at'], self.when.isoformat())
        self.assertNotIn('secret', (self.root / 'state/state.json').read_text())
        self.assertNotIn('secret', (self.root / 'out/latest.json').read_text())

    def test_budget_is_reserved_before_network_failure_and_rolls_by_shanghai_day(self):
        def crash(author):
            state = json.loads((self.root / 'state/state.json').read_text())
            self.assertEqual(state['budget']['2026-10-17']['reserved_usd'], '0.01')
            raise TimeoutError('no response')
        self.run_watch(fetcher=crash)
        self.run_watch(fetcher=Mock(side_effect=TimeoutError()), at=self.when + dt.timedelta(hours=2))
        fetcher = Mock()
        out = self.run_watch(fetcher=fetcher, at=self.when + dt.timedelta(hours=4))
        fetcher.assert_not_called()
        self.assertEqual(out['sources'][0]['status'], 'budget_exhausted')
        next_day = self.run_watch(at=self.when + dt.timedelta(days=1))
        self.assertEqual(next_day['calls'], 1)

    def test_budget_uses_request_day_if_run_crosses_midnight(self):
        self.config['authors'].append(dict(self.author, key='two'))
        self.config['max_cost_usd_per_day'] = 0.01
        midnight = self.when.replace(hour=23, minute=59)
        moments = iter([midnight, midnight, midnight + dt.timedelta(minutes=2), midnight + dt.timedelta(minutes=2)])
        out = self.run_watch(clock=lambda: next(moments))
        self.assertEqual(out['calls'], 2)
        state = json.loads((self.root / 'state/state.json').read_text())
        self.assertEqual(state['budget']['2026-10-17']['reserved_usd'], '0.01')
        self.assertEqual(state['budget']['2026-10-18']['reserved_usd'], '0.01')

    def test_pending_retention_expiry_does_not_reintroduce_seen(self):
        payload = {'data': {'aweme_list': [self.post()]}}
        self.run_watch(payload)
        out = self.run_watch(payload, at=self.when + dt.timedelta(days=8))
        self.assertEqual(out['candidates'], [])
        self.assertEqual(out['new'], [])

    def test_missing_or_future_time_can_be_rechecked_but_old_processed_posts_do_not_return(self):
        unknown = {'aweme_id': 'later-time', 'desc': '无时间'}
        future = self.post('scheduled')
        future['create_time'] = int((self.when + dt.timedelta(minutes=2)).timestamp())
        first = self.run_watch({'data': {'aweme_list': [unknown, future, self.post('old', 200)]}})
        self.assertEqual(first['new'], [])
        unknown['create_time'] = int(self.when.timestamp())
        # 已按旧时间处理的作品即使上游改时间，也不能再次灌进新作候选。
        old_changed = self.post('old', 1)
        second = self.run_watch({'data': {'aweme_list': [unknown, future, old_changed]}},
                                at=self.when + dt.timedelta(hours=2))
        self.assertEqual({p['id'] for p in second['new']}, {'later-time', 'scheduled'})

    def test_post_published_during_fetch_uses_completion_clock(self):
        moment = [self.when]
        post = self.post('during-fetch')
        post['create_time'] = int((self.when + dt.timedelta(minutes=2)).timestamp())
        def fetch(author):
            moment[0] = self.when + dt.timedelta(minutes=3)
            return {'data': {'aweme_list': [post]}}
        out = self.run_watch(fetcher=fetch, clock=lambda: moment[0])
        self.assertEqual([p['id'] for p in out['new']], ['during-fetch'])
        self.assertEqual(out['new'][0]['observed_at'], moment[0].isoformat())

    def test_twenty_failed_sources_cannot_starve_fifteen_never_attempted_sources(self):
        self.config['authors'] = [dict(self.author, key='source-%02d' % i) for i in range(35)]
        self.config['max_cost_usd_per_day'] = 2
        failed = Mock(side_effect=TimeoutError('timeout'))
        first = self.run_watch(fetcher=failed)
        self.assertEqual(first['calls'], 20)
        fetched = Mock(return_value={'data': {'aweme_list': []}})
        second = self.run_watch(fetcher=fetched, at=self.when + dt.timedelta(minutes=1))
        self.assertEqual(second['calls'], 15)
        self.assertEqual({call[0][0]['key'] for call in fetched.call_args_list},
                         {'source-%02d' % i for i in range(20, 35)})

    def test_due_order_limits_and_dry_run_never_load_credentials_or_write(self):
        self.config['authors'].append(dict(self.author, key='two'))
        with patch.object(self.w, 'load_credentials', side_effect=AssertionError('must not load')):
            out = self.run_watch(dry_run=True, limit=1)
        self.assertEqual([p['key'] for p in out['plan']], ['one'])
        self.assertFalse((self.root / 'state/state.json').exists())
        self.assertFalse((self.root / 'out/latest.json').exists())
        self.run_watch(limit=1)
        fetch = Mock(return_value={'data': {'aweme_list': []}})
        out = self.run_watch(fetcher=fetch, at=self.when + dt.timedelta(hours=2), limit=1)
        self.assertEqual(fetch.call_args[0][0]['key'], 'two')
        self.assertEqual(out['calls'], 1)

    def test_longest_overdue_deadline_precedes_older_but_not_overdue_fetch(self):
        self.config['authors'] = [dict(self.author, interval_minutes=240),
                                  dict(self.author, key='two', interval_minutes=60)]
        state = {'version': 1, 'authors': {
            'one': {'last_fetch_at': (self.when - dt.timedelta(hours=4)).isoformat()},
            'two': {'last_fetch_at': (self.when - dt.timedelta(hours=3)).isoformat()}},
            'seen': {}, 'candidates': {}, 'budget': {}}
        self.w.atomic_json(self.root / 'state/state.json', state)
        fetch = Mock(return_value={'data': {'aweme_list': []}})
        self.run_watch(fetcher=fetch, limit=1)
        self.assertEqual(fetch.call_args[0][0]['key'], 'two')

    def test_lock_prevents_second_process_equivalent_without_requests(self):
        fetcher = Mock()
        with self.w.process_lock():
            with self.assertRaisesRegex(RuntimeError, 'lock'):
                self.run_watch(fetcher=fetcher)
        fetcher.assert_not_called()

    def test_endpoint_domain_method_and_cost_fail_closed(self):
        for endpoint in ['https://evil.test/api/v1/x', '/api/v1/douyin/write',
                         '/api/v1/douyin/app/v3/fetch_user_post_videos?x=1']:
            with self.subTest(endpoint=endpoint):
                self.config['authors'][0] = dict(self.author, endpoint=endpoint)
                with self.assertRaises(ValueError):
                    self.run_watch()
        self.config['authors'] = [self.author]
        for change in [{'method': 'POST'}, {'cost_usd': 0}, {'cost_usd': float('nan')},
                       {'interval_minutes': -1}, {'params': {'api_key': 'secret'}}]:
            self.config['authors'] = [dict(self.author, **change)]
            with self.assertRaises(ValueError):
                self.run_watch()
        with self.assertRaises(ValueError):
            self.w.validate_base('https://api.tikhub.io.evil.test')
        with self.assertRaises(ValueError):
            self.w.validate_base('http://api.tikhub.io')

    def test_reposts_keep_outer_id_and_explicit_origin_without_invented_originality(self):
        cases = [
            ('weibo', {'idstr': 'outer', 'text': '我转发的评论',
                       'retweeted_status': {'idstr': 'original', 'text': '原作者内容'}},
             'repost', 'original'),
            ('twitter', {'tweet_id': 'outer', 'text': 'RT 内容',
                         'retweeted': {'id': 'original'},
                         'retweeted_tweet': {'tweet_id': 'original'}}, 'retweet', 'original'),
            ('twitter', {'tweet_id': 'outer', 'text': '引用附带自己的观点',
                         'quoted': {'tweet_id': 'quote'}, 'retweets': 1000}, 'unknown', None),
            ('twitter', {'tweet_id': 'outer', 'text': 'metadata', 'post_type': 'original'},
             'original', 'outer'),
            ('weibo', {'idstr': 'outer', 'text': '未有转发字段'}, 'unknown', None),
        ]
        for platform, item, expected, origin in cases:
            payload = {'data': {'items': [{'category': 'feed', 'data': item}]}} if platform == 'weibo' else {'data': {'timeline': [item]}}
            post = self.w.parse_posts(payload, dict(self.author, platform=platform), self.when)[0]
            self.assertEqual(post['id'], 'outer')
            self.assertEqual(post['type'], expected)
            self.assertEqual(post['original_id'], origin)
            self.assertEqual(post['evidence_level'], 'metadata')

    def test_nonempty_idless_response_is_error_not_empty_success(self):
        self.run_watch({'data': {'aweme_list': [self.post()]}})
        out = self.run_watch({'data': {'aweme_list': [{'desc': '结构变化'}]}},
                             at=self.when + dt.timedelta(hours=2))
        self.assertEqual(out['sources'][0]['status'], 'error')
        self.assertEqual(out['sources'][0]['last_fetch_at'], self.when.isoformat())
        self.assertEqual(len(out['candidates']), 1)
        self.assertEqual(out['new'], [])
        self.assertEqual(self.w.parse_posts({'data': {'aweme_list': []}}, self.author, self.when), [])

    def test_wechat_message_group_and_article_index_are_separate_ids(self):
        author = dict(self.author, platform='wechat_mp',
                      endpoint='/api/v1/wechat_mp/v2/fetch_account_articles', method='POST',
                      params={'username': 'gh_demo', 'page_size': 20, 'raw': False})
        self.w.validate_config(dict(self.config, authors=[author]))
        payload = {'data': {'biz_username': 'gh_demo', 'articles': [
            {'app_msg_id': 123, 'idx': 1, 'title': 'first', 'create_time': 1792190000},
            {'app_msg_id': 123, 'idx': 2, 'title': 'second', 'create_time': 1792190000}]}}
        posts = self.w.parse_posts(payload, author, self.when)
        self.assertEqual([p['id'] for p in posts], ['gh_demo:123:1', 'gh_demo:123:2'])
        self.assertTrue(all(p['published_at'] for p in posts))

    def test_channels_post_is_allowlisted_read_only_list(self):
        author = dict(self.author, platform='wechat_channels', method='POST',
                      endpoint='/api/v1/wechat_channels/v2/fetch_user_videos')
        self.w.validate_config(dict(self.config, authors=[author]))

    def test_real_nested_parser_shapes_and_missing_time(self):
        samples = [
            ('douyin', {'data': {'aweme_list': [self.post('1')]}}),
            ('xiaohongshu', {'data': {'code': 0, 'data': {'notes': [
                {'id': '2', 'title': 'AI', 'create_time': 1792190000000}]}}}),
            ('bilibili', {'data': {'code': 0, 'data': {'list': {'vlist': [
                {'bvid': 'BVtest', 'title': 'AI', 'created': 1792190000}]}}}}),
            ('weibo', {'data': {'items': [{'category': 'card', 'data': {'text': 'header'}},
                {'category': 'feed', 'data': {'idstr': '4', 'text': '<b>AI</b>',
                 'created_at': 'Sat Oct 17 01:00:00 +0800 2026'}}]}}),
            ('wechat_mp', {'data': {'items': [{'url': 'https://mp.weixin.qq.com/s/example',
                        'title': 'AI', 'pub_time': 1792190000}]}}),
            ('wechat_mp', {'data': {'articles': [{'id': '5', 'title': 'AI'}]}}),
            ('wechat_channels', {'data': {'videos': [{'id': '6', 'title': 'AI', 'create_time': 1792190000}]}}),
            ('twitter', {'data': {'timeline': [{'tweet_id': '7', 'text': 'AI',
                            'created_at': 'Fri Oct 16 17:00:00 +0000 2026'}]}}),
            ('zhihu', {'data': {'data': [{'id': '8', 'question': {'id': 'q', 'title': 'AI'},
                                              'created_time': 1792190000}]}}),
            ('kuaishou', {'data': {'result': 1, 'feeds': [{'photo_id': '9', 'caption': 'AI',
                                                       'timestamp': 1792190000000}]}}),
        ]
        for platform, payload in samples:
            with self.subTest(platform=platform):
                posts = self.w.parse_posts(payload, dict(self.author, platform=platform), self.when)
                self.assertEqual(len(posts), 1)
                self.assertEqual(posts[0]['title'], 'AI' if platform != 'douyin' else '实际讲解AI')
                self.assertIn('published_at', posts[0])
        posts = self.w.parse_posts(samples[5][1], dict(self.author, platform='wechat_mp'), self.when)
        self.assertIsNone(posts[0]['published_at'])
        for bad in [{'code': 400, 'data': {'aweme_list': []}}, {'data': {'status_code': 4}},
                    {'data': {}}, {'error': 500}]:
            with self.assertRaises(ValueError):
                self.w.parse_posts(bad, self.author, self.when)


if __name__ == '__main__':
    unittest.main()
