import json
import tempfile
import unittest
from pathlib import Path
from scripts.filter_data import screen
from scripts.deduplicate import fingerprint
from scripts.score_quality import score

BASE = {"id":"x","text":"This is a sufficiently long educational sentence about language data and agent evaluation.","lang_code":"en","source":"test","source_url":"https://example.org/item","license":"CC0-1.0","quality_score":0.5,"human_review_status":"unreviewed"}

class PipelineTests(unittest.TestCase):
    def test_filter_requires_provenance_and_removes_email(self):
        row = dict(BASE, text=BASE['text'] + ' Contact user@example.org for more information.')
        kept, reason = screen(row, min_chars=30)
        self.assertIsNone(reason); self.assertNotIn('user@example.org', kept['text']); self.assertIn('[EMAIL_REDACTED]',kept['text'])
        row.pop('license'); self.assertTrue(screen(row, min_chars=30)[1].startswith('missing_metadata'))
    def test_dedup_is_unicode_and_language_scoped(self):
        self.assertEqual(fingerprint('en','Hello   WORLD!'),fingerprint('en','hello world'))
        self.assertNotEqual(fingerprint('en','hello'),fingerprint('fr','hello'))
    def test_quality_score_bounded_and_provenance_weighted(self):
        value, parts=score(BASE); self.assertGreaterEqual(value,0); self.assertLessEqual(value,1); self.assertEqual(parts['provenance'],1.0)
        value2,_=score({"text":BASE['text']}); self.assertLess(value2,value)
    def test_filter_supports_per_language_profiles(self):
        row=dict(BASE,text='A sufficiently long sample for generic filtering.',lang_code='fr')
        kept,reason=screen(row,language_profiles={'fr':{'min_characters':100}},default_min_chars=10)
        self.assertIsNone(kept); self.assertEqual(reason,'too_short')

if __name__=='__main__': unittest.main()
