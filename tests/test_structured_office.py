"""Synthetic OOXML edge cases; no installed Office, external links or model."""
import asyncio
import io
import json
import unittest
import zipfile
from unittest.mock import patch
from cyberant.document_extractors import extract,extract_async,evidence_body,excel_value,W,S,R


def archive(entries):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for name,value in entries.items():z.writestr(name,value)
    return out.getvalue()


def workbook(rows,extra='',styles='',properties='',state='visible',other=None):
    entries={'xl/workbook.xml':f'<workbook xmlns="{S[1:-1]}" xmlns:r="{R[1:-1]}">{properties}<sheets><sheet name="Quote" state="{state}" r:id="r1"/></sheets></workbook>',
             'xl/_rels/workbook.xml.rels':'<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>',
             'xl/worksheets/sheet1.xml':f'<worksheet xmlns="{S[1:-1]}" xmlns:r="{R[1:-1]}">{extra}<sheetData>{rows}</sheetData></worksheet>'}
    if styles:entries['xl/styles.xml']=f'<styleSheet xmlns="{S[1:-1]}">{styles}</styleSheet>'
    entries.update(other or {});return archive(entries)


class StructuredOffice(unittest.TestCase):
    def test_word_headings_current_revision_lists_and_notes(self):
        body='''<w:p><w:pPr><w:pStyle w:val="CustomHeading"/></w:pPr><w:r><w:t>Scope</w:t></w:r></w:p>
          <w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="4"/></w:numPr></w:pPr>
          <w:del><w:r><w:delText>OLD PRICE</w:delText></w:r></w:del><w:ins><w:r><w:t>Current</w:t><w:tab/><w:t>scope</w:t><w:br/><w:t>Confirmed</w:t></w:r></w:ins>
          <w:r><w:footnoteReference w:id="2"/></w:r><w:commentRangeStart w:id="3"/></w:p>'''
        raw=archive({'word/document.xml':f'<w:document xmlns:w="{W[1:-1]}"><w:body>{body}</w:body></w:document>',
                     'word/styles.xml':f'<w:styles xmlns:w="{W[1:-1]}"><w:style w:styleId="CustomHeading"><w:pPr><w:outlineLvl w:val="1"/></w:pPr></w:style></w:styles>',
                     'word/footnotes.xml':f'<w:footnotes xmlns:w="{W[1:-1]}"><w:footnote w:id="2"><w:p><w:r><w:t>Exclusion</w:t></w:r></w:p></w:footnote></w:footnotes>',
                     'word/comments.xml':f'<w:comments xmlns:w="{W[1:-1]}"><w:comment w:id="3"><w:p><w:r><w:t>Review proposal</w:t></w:r></w:p></w:comment></w:comments>'})
        result=extract(raw,'scope.docx');self.assertEqual(result['extraction_version'],2)
        unit=result['units'][1];self.assertEqual(unit['body'],'Current\tscope\nConfirmed')
        self.assertEqual(unit['structure']['heading_path'],['Scope'])
        self.assertEqual(unit['structure']['list']['numId'],'4')
        self.assertEqual(unit['structure']['references']['footnoteReference'],['2'])
        self.assertNotIn('OLD PRICE',json.dumps(result))
        self.assertIn('tracked changes',str(result['warnings']))
        self.assertEqual({u['structure']['kind'] for u in result['units']},{'heading','paragraph','footnotes','comments'})

    def test_word_table_header_merge_and_row_locations(self):
        body='''<w:tbl><w:tr><w:trPr><w:tblHeader/></w:trPr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr><w:p><w:r><w:t>Service</w:t></w:r></w:p></w:tc></w:tr>
        <w:tr><w:tc><w:tcPr><w:vMerge w:val="restart"/></w:tcPr><w:p><w:r><w:t>Install</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>6</w:t></w:r></w:p></w:tc></w:tr>
        <w:tr><w:tc><w:tcPr><w:vMerge/></w:tcPr><w:p/></w:tc><w:tc><w:p><w:r><w:t>2</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'''
        result=extract(archive({'word/document.xml':f'<w:document xmlns:w="{W[1:-1]}"><w:body>{body}</w:body></w:document>'}),'a.docx')
        self.assertEqual(len(result['units']),3)
        self.assertEqual(result['units'][0]['structure']['cells'][0]['span'],2)
        self.assertEqual(result['units'][2]['structure']['cells'][0]['vertical_merge'],'continue')
        self.assertEqual(result['units'][2]['structure']['cells'][0]['text'],'')
        self.assertEqual(result['units'][2]['structure']['declared_headers'],[['Service']])
        self.assertIn('hàng 3',result['units'][2]['location'])

    def test_excel_types_zero_blank_error_formula_and_identifier(self):
        rows='''<row r="1"><c r="A1"><v>0</v></c><c r="B1"/><c r="C1" t="e"><v>#DIV/0!</v></c>
        <c r="D1"><f>SUM(A1:B1)</f></c><c r="E1" s="1"><v>12</v></c><c r="F1" t="inlineStr"><is><t>00123</t></is></c>
        <c r="G1" t="b"><v>0</v></c><c r="H1"><f t="shared" si="0"/><v>0</v></c></row>'''
        styles='<numFmts><numFmt numFmtId="164" formatCode="00000"/></numFmts><cellXfs><xf/><xf numFmtId="164"/></cellXfs>'
        result=extract(workbook(rows,styles=styles),'a.xlsx');cells=result['units'][0]['structure']['cells']
        self.assertEqual(cells[0]['interpreted']['value'],'0');self.assertEqual(cells[1]['interpreted']['type'],'blank')
        self.assertEqual(cells[2]['interpreted']['type'],'error');self.assertFalse(cells[3]['formula']['cached'])
        self.assertEqual(cells[4]['raw'],'12');self.assertEqual(cells[4]['interpreted']['display'],'00012')
        self.assertEqual(cells[5]['interpreted']['value'],'00123');self.assertFalse(cells[6]['interpreted']['value'])
        self.assertTrue(cells[7]['formula']['cached']);self.assertIsNone(cells[7]['formula']['expression'])
        self.assertIn('E1: 00012',result['units'][0]['body'])
        self.assertIn('cache_missing',evidence_body(result['units'][0]))

    def test_excel_dates_percent_currency_and_unsupported_formats(self):
        self.assertEqual(excel_value('61',None,'mm-dd-yy')['value'],'1900-03-01T00:00:00')
        self.assertEqual(excel_value('1',None,'mm-dd-yy',True)['value'],'1904-01-02T00:00:00')
        self.assertIn('fictitious',excel_value('60',None,'mm-dd-yy')['status'])
        self.assertEqual(excel_value('0.15',None,'0%')['percent_value'],'15.00')
        self.assertEqual(excel_value('250.25',None,'"USD" #,##0.00')['currency_marker'],'USD')
        self.assertEqual(excel_value('5',None,'[>=0]0;[Red]-0')['status'],'complex_format_not_rendered')
        with self.assertRaises(ValueError):excel_value('1E999999',None,'General')
        result=extract(workbook('<row r="1"><c r="A1" s="1"><v>1</v></c></row>',styles='<cellXfs><xf/><xf numFmtId="14"/></cellXfs>',properties='<workbookPr date1904="1"/>'),'a.xlsx')
        self.assertEqual(result['units'][0]['structure']['cells'][0]['interpreted']['date_system'],'1904')

    def test_excel_hidden_filters_declared_headers_and_external_links(self):
        other={'xl/worksheets/_rels/sheet1.xml.rels':'<Relationships><Relationship Id="t1" Target="../tables/table1.xml"/></Relationships>',
               'xl/tables/table1.xml':f'<table xmlns="{S[1:-1]}" name="QuoteLines" ref="A1:B3" totalsRowCount="1"><tableColumns><tableColumn name="SKU"/><tableColumn name="Quantity"/></tableColumns></table>',
               'xl/externalLinks/externalLink1.xml':'<externalLink/>'}
        extra='<cols><col min="2" max="2" hidden="1"/></cols><autoFilter ref="A1:B3"><filterColumn colId="0"/></autoFilter><tableParts><tablePart r:id="t1"/></tableParts>'
        raw=workbook('<row r="2" hidden="1"><c r="A2" t="inlineStr"><is><t>PART</t></is></c><c r="B2"><v>6</v></c></row>',extra=extra,state='veryHidden',other=other)
        result=extract(raw,'a.xlsx');meta=result['units'][0]['structure']
        self.assertTrue(meta['hidden_row']);self.assertEqual(meta['sheet_state'],'veryHidden')
        self.assertTrue(meta['cells'][1]['hidden_column']);self.assertTrue(meta['filters'][0]['criteria_present'])
        self.assertEqual(meta['tables'][0]['headers'],['SKU','Quantity']);self.assertEqual(meta['tables'][0]['totals_rows'],1)
        self.assertIn('liên kết ngoài',str(result['warnings']))

    def test_async_structure_and_legacy_body(self):
        raw=workbook('<row r="1"><c r="A1"><v>6</v></c></row>')
        result=asyncio.run(extract_async(raw,'a.xlsx'));self.assertEqual(result['units'][0]['structure']['kind'],'worksheet_row')
        self.assertIn('raw_numeric',evidence_body(result['units'][0]))
        self.assertEqual(evidence_body(dict(body='Old text',location='page1')),'Old text')
        result=extract(workbook(''),'empty.xlsx');self.assertEqual(result['units'][0]['structure']['kind'],'empty_sheet')

    def test_invalid_indices_and_structured_output_bounds(self):
        for rows in ('<row r="1"><c r="A1" t="s"><v>-1</v></c></row>',
                     '<row r="1"><c r="B2"><v>6</v></c></row>',
                     '<row r="1"><c r="A1" s="-1"><v>6</v></c></row>'):
            with self.subTest(rows=rows),self.assertRaises(ValueError):extract(workbook(rows),'a.xlsx')
        with patch('cyberant.document_extractors.MAX_UNITS',1),self.assertRaises(ValueError):
            extract(workbook('<row r="1"><c r="A1"><v>1</v></c></row><row r="2"><c r="A2"><v>2</v></c></row>'),'a.xlsx')
        with patch('cyberant.document_extractors.MAX_TEXT',2),self.assertRaises(ValueError):
            extract(workbook('<row r="1"><c r="A1"><v>123</v></c></row>'),'a.xlsx')


if __name__=='__main__':unittest.main()