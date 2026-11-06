import json
import tempfile
import unittest
from pathlib import Path
from scripts.scaffold_language import scaffold

class ScaffoldTests(unittest.TestCase):
    def test_scaffold_creates_all_dataset_kinds_and_reviewable_benchmark(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); paths=scaffold('pt-BR',root,'pt-BR')
            self.assertTrue((root/'datasets/raw/pt/sft/.gitkeep').exists())
            self.assertTrue((root/'datasets/curated/pt/rlhf/.gitkeep').exists())
            doc=json.loads((root/'evaluation/benchmarks/pt_tasks.json').read_text(encoding='utf-8'))
            self.assertEqual(doc['language'],'pt'); self.assertEqual(doc['source_language_tags'],['pt-BR'])
            self.assertEqual(doc['status'],'requires_native_speaker_authoring'); self.assertEqual(doc['tasks'],[])
            existing=root/'evaluation/benchmarks/pt_tasks.json'; existing.write_text('{"preserve": true}')
            scaffold('pt',root)
            self.assertEqual(json.loads(existing.read_text()),{'preserve':True})

if __name__=='__main__': unittest.main()
