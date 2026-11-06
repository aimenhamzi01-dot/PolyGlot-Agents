import json
import tempfile
import unittest
from pathlib import Path
from scripts.language_codes import canonical_iso639, is_iso639
from scripts.language_report import summarize
from scripts.lang_id import run
from scripts.filter_data import screen

class FakeModel:
    def __init__(self, label, confidence): self.label, self.confidence = label, confidence
    def predict(self, text, k=1): return ([f'__label__{self.label}'], [self.confidence])
    def get_labels(self): return ['__label__en','__label__fr']

class MultilingualTests(unittest.TestCase):
    def test_region_tags_canonicalize_but_variants_are_preserved_elsewhere(self):
        self.assertEqual(canonical_iso639('pt-BR'), 'pt')
        self.assertEqual(canonical_iso639('uk-UA'), 'uk')
        self.assertTrue(is_iso639('ar'))
        self.assertFalse(is_iso639('zz'))
        row={'text':'Portuguese sample sentence with enough content for an import.','lang_code':'pt-BR','source':'test','license':'CC0-1.0'}
        normalized, reason=screen(row,min_chars=10)
        self.assertIsNone(reason); self.assertEqual(normalized['lang_code'],'pt'); self.assertEqual(normalized['source_lang_tag'],'pt-BR')
    def test_low_confidence_is_routed_for_review_and_never_guessed_as_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); inp=root/'in.jsonl'; out=root/'out.jsonl'
            inp.write_text(json.dumps({'text':'Short sample','source':'test','license':'CC0-1.0'},ensure_ascii=False)+'\n',encoding='utf-8')
            # Exercise decision behavior without downloading the model by patching model loading.
            from unittest.mock import patch
            with patch('scripts.lang_id.get_model', return_value=FakeModel('en', .4)):
                counts=run(inp,out,root/'unused-model.ftz',min_confidence=.55)
            row=json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(row['lang_code'],'und'); self.assertEqual(row['routing_status'],'needs_review'); self.assertEqual(counts['needs_review'],1)
            _, reason=screen({**row,'source':'test','license':'CC0-1.0'},min_chars=1)
            self.assertEqual(reason,'language_requires_review')
    def test_conflict_preserves_declared_code_for_auditing(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); inp=root/'in.jsonl'; out=root/'out.jsonl'
            inp.write_text(json.dumps({'text':'Bonjour, ceci est un court texte français.','lang_code':'en'},ensure_ascii=False)+'\n',encoding='utf-8')
            from unittest.mock import patch
            with patch('scripts.lang_id.get_model', return_value=FakeModel('fr', .99)):
                run(inp,out,root/'unused-model.ftz')
            row=json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(row['lang_code'],'en'); self.assertEqual(row['detected_lang_code'],'fr'); self.assertTrue(row['language_conflict'])
    def test_source_tag_outside_fasttext_coverage_is_not_overwritten_by_guess(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); inp=root/'in.jsonl'; out=root/'out.jsonl'
            inp.write_text(json.dumps({'text':'Swahili sample','lang_code':'sw','source_lang_tag':'sw','source':'test'},ensure_ascii=False)+'\n',encoding='utf-8')
            from unittest.mock import patch
            with patch('scripts.lang_id.get_model', return_value=FakeModel('en', .99)):
                run(inp,out,root/'unused-model.ftz')
            row=json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(row['lang_code'],'sw'); self.assertEqual(row['routing_status'],'source_tag_only')
            self.assertFalse(row['detector_covers_declared_language'])
    def test_unlabelled_high_confidence_is_reviewed_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); inp=root/'in.jsonl'; out=root/'out.jsonl'
            inp.write_text(json.dumps({'text':'A sufficiently long sentence to identify a language.'},ensure_ascii=False)+'\n',encoding='utf-8')
            from unittest.mock import patch
            with patch('scripts.lang_id.get_model', return_value=FakeModel('en', .99)):
                run(inp,out,root/'unused-model.ftz')
            row=json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(row['lang_code'],'en'); self.assertEqual(row['routing_status'],'needs_review')
    def test_language_report_groups_quality_and_duplicates_per_language(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'sample.jsonl'
            rows=[{'lang_code':'pt-BR','text':'Olá mundo','quality_score':.8,'human_review_status':'reviewed','source':'fixture'}, {'lang_code':'pt','text':'Olá mundo','quality_score':.6,'human_review_status':'unreviewed','source':'fixture'}, {'lang_code':'fr','text':'Bonjour','quality_score':.9,'human_review_status':'reviewed','source':'fixture'}]
            f.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
            report=summarize([f])
            self.assertEqual(report['languages']['pt']['records'],2)
            self.assertEqual(report['languages']['pt']['exact_duplicate_rate'],.5)
            self.assertEqual(report['languages']['fr']['records'],1)

if __name__=='__main__': unittest.main()
