"""Read-only source checks and deterministic effort arithmetic."""
import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile
from tools import audit_service_sources as audit


class ServiceEvidenceTests(unittest.TestCase):
    def test_runtime_comparison_read_only_and_missing_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'knowledge.sqlite3'
            source=dict(id='ONE',body='text',status='approved',review_status='draft_engineer_review')
            runtime={**source,'status':'retired'}
            with closing(sqlite3.connect(path)) as c:
                with c:
                    c.execute('CREATE TABLE docs(id TEXT,payload TEXT)')
                    c.execute('INSERT INTO docs VALUES(?,?)',('ONE',json.dumps(runtime)))
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            report=audit.runtime_comparison(path,[source])
            self.assertEqual(report['changed_body'],0)
            self.assertEqual(report['preserved_retired'],1)
            self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())
            missing=Path(tmp)/'missing.sqlite3'
            self.assertFalse(audit.runtime_comparison(missing,[source])['available'])
            self.assertFalse(missing.exists())

    def test_workbook_formula_cache_and_effort_not_downtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'Dịch vụ chuyển đổi cấu hình - Thời gian ước tính.xlsx'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Effort" r:id="rId1"/></sheets></workbook>')
                z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="rId1" Target="/xl/worksheets/sheet1.xml"/></Relationships>')
                z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c r="D6"><v>0.25</v></c><c r="E6"><v>2</v></c><c r="F6"><f>D6*E6</f><v>0.5</v></c><c r="F7"><f>SUM(F6)</f><v/></c></row></sheetData></worksheet>')
            report=audit.workbook(path);sheet=report['sheets'][0]
            self.assertFalse(report['cache_freshness_verified'])
            self.assertEqual(sheet['empty_formula_caches'],1)
            self.assertEqual(sheet['effort']['man_hours'],.5)
            self.assertEqual(sheet['effort']['summed_task_hours'],.25)

    def test_evaluation_has_real_assertions_and_separate_manual_stage(self):
        root=Path(__file__).resolve().parents[1]
        data=json.loads((root/'knowledge/evaluation_services.json').read_text(encoding='utf8'))
        cases=data['cases'];self.assertGreaterEqual(len(cases),40)
        self.assertEqual(len({c['id'] for c in cases}),len(cases))
        for case in cases:
            self.assertTrue(case['question'])
            if case['stage']=='offline':
                self.assertTrue(case.get('expected_ids') or case.get('expected_types'))
            else:self.assertTrue(case['review_criteria'])


if __name__=='__main__':unittest.main()