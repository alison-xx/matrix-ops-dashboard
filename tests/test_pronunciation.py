import pathlib, sys, unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import common

class PronunciationTests(unittest.TestCase):
    def test_tts_boundary_rewrites_only_known_phrase(self):
        with patch.object(common, 'tts_bailian', return_value=1.0) as synth:
            common.tts('国行版本，银行正常运行。', '/tmp/unused.wav', voice='bailian:Ethan')
        self.assertEqual(synth.call_args.args[0], '中国大陆版本，银行正常运行。')

    def test_does_not_rewrite_other_country_or_industry(self):
        from pronunciation import spoken_text
        self.assertEqual(spoken_text('美国行业，中国行业，银行运行。'), '美国行业，中国行业，银行运行。')

    def test_cache_changes_when_pronunciation_policy_changes(self):
        from pronunciation import audio_cache_key
        self.assertNotEqual(audio_cache_key('国行', 'v', '+8%', revision='a'),
                            audio_cache_key('国行', 'v', '+8%', revision='b'))
        self.assertNotEqual(audio_cache_key('国行', 'v', '+8%'),
                            audio_cache_key('国行', 'v', '+10%'))

    def test_script_uses_spoken_not_display_text(self):
        from audio_qc import script_text
        spec = {'scenes':[{'lines':[{'say':'国行版本', 'show':'国行'}, '银行[停0.3]开门']} ]}
        self.assertEqual(script_text(spec), '中国大陆版本银行开门')

    def test_risk_report_preserves_context_and_known_reading(self):
        from pronunciation import inspect_text
        report = inspect_text('国行版本和银行业务，重新运行。')
        self.assertEqual(report['spoken'], '中国大陆版本和银行业务，重新运行。')
        self.assertIn('银行', [x['word'] for x in report['review']])
        self.assertEqual(inspect_text(report['spoken'])['spoken'], report['spoken'])

if __name__ == '__main__': unittest.main()
