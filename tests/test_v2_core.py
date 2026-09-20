import tempfile
import unittest
from pathlib import Path

from app.services.formula_qa import validate_formula_text
from app.services.table_qa import validate_table_text
from app.services.safe_fix import collect_safe_patches
from app.services.datapack import build_datapack


class V2CoreTests(unittest.TestCase):
    def test_formula_validator(self):
        self.assertEqual(validate_formula_text('$$x^2+y^2$$', 1), [])
        issues = validate_formula_text('$$x^2+y^2$', 1)
        self.assertTrue(issues)

    def test_table_validator(self):
        good = '| A | B |\n|---|---|\n| 1 | 2 |'
        self.assertEqual(validate_table_text(good, 1), [])
        bad = '| A | B |\n|---|---|\n| 1 | 2 | 3 |'
        self.assertTrue(validate_table_text(bad, 1))

    def test_safe_patch_requires_unique_original(self):
        results = [{
            'page': 1, 'status': 'REVIEW', 'issues': [{
                'page': 1, 'error_type': 'wrong_text', 'severity': 'low',
                'evidence': 'typo', 'original': 'abc', 'replacement': 'abd',
                'correction': 'abd', 'confidence': 0.99, 'safe_to_apply': True,
            }]
        }]
        accepted, rejected = collect_safe_patches(results, 'abc only once', 0.985)
        self.assertEqual(len(accepted), 1)
        accepted, rejected = collect_safe_patches(results, 'abc and abc twice', 0.985)
        self.assertEqual(len(accepted), 0)
        self.assertEqual(len(rejected), 1)

    def test_datapack(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            md = root / 'document.md'
            md.write_text('<!-- PAGE: 1 -->\n# Chương 1\nNội dung\n\n## Bài 1\nVí dụ\n', encoding='utf-8')
            out = root / 'dp'
            report = build_datapack(md, out, {'subject':'Toán','grade':'8','book_set':'KNTT'}, 'abc123')
            self.assertTrue((out / 'DATA_PACK_MASTER.md').exists())
            self.assertTrue((out / 'DATA_PACK_INDEX.json').exists())
            self.assertGreaterEqual(report['segment_count'], 1)


if __name__ == '__main__':
    unittest.main()
