import asyncio,io,unittest,zipfile
from cyberant.document_extractors import extract,extract_async,W,S,A,R
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject


def archive(entries):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as z:
        for name,value in entries.items():z.writestr(name,value)
    return output.getvalue()


class Extractors(unittest.TestCase):
    def test_docx_table_order(self):
        data=archive({'word/document.xml':f'<w:document xmlns:w="{W[1:-1]}"><w:body><w:p><w:r><w:t>Intro</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>SKU</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>12</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'})
        result=extract(data,'a.docx')
        self.assertEqual([u['body'] for u in result['units']],['Intro','SKU | 12'])

    def test_excel_formula_merged_sheet(self):
        data=archive({'xl/workbook.xml':f'<workbook xmlns="{S[1:-1]}" xmlns:r="{R[1:-1]}"><sheets><sheet name="BOM" r:id="r1"/></sheets></workbook>',
          'xl/_rels/workbook.xml.rels':'<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>',
          'xl/worksheets/sheet1.xml':f'<worksheet xmlns="{S[1:-1]}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Part</t></is></c><c r="B1"><f>2*3</f><v>6</v></c></row></sheetData><mergeCells><mergeCell ref="A1:A2"/></mergeCells></worksheet>'})
        result=extract(data,'a.xlsx');text=str(result)
        for value in ('BOM','A1:A2','A1: Part','B1: 6','2*3','cache'):self.assertIn(value,text)

    def test_slides_and_notes(self):
        ns='http://schemas.openxmlformats.org/presentationml/2006/main'
        data=archive({'ppt/presentation.xml':f'<p:presentation xmlns:p="{ns}" xmlns:r="{R[1:-1]}"><p:sldIdLst><p:sldId r:id="r1"/></p:sldIdLst></p:presentation>',
          'ppt/_rels/presentation.xml.rels':'<Relationships><Relationship Id="r1" Target="slides/slide1.xml"/></Relationships>',
          'ppt/slides/slide1.xml':f'<root xmlns:a="{A[1:-1]}"><a:p><a:r><a:t>Slide content</a:t></a:r></a:p></root>',
          'ppt/slides/_rels/slide1.xml.rels':'<Relationships><Relationship Id="note" Target="../notesSlides/notesSlide1.xml"/></Relationships>',
          'ppt/notesSlides/notesSlide1.xml':f'<root xmlns:a="{A[1:-1]}"><a:p><a:r><a:t>Speaker note</a:t></a:r></a:p></root>'})
        self.assertEqual([u['body'] for u in extract(data,'a.pptx')['units']],['Slide content','Speaker note'])

    def test_pdf_over_thirty_pages(self):
        writer=PdfWriter()
        for i in range(35):
            page=writer.add_blank_page(width=600,height=800)
            font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
            stream=DecodedStreamObject();stream.set_data(f'BT /F1 12 Tf 50 700 Td (Page {i+1}) Tj ET'.encode())
            page[NameObject('/Contents')]=writer._add_object(stream)
        buf=io.BytesIO();writer.write(buf)
        result=extract(buf.getvalue(),'a.pdf');self.assertEqual(len(result['units']),35)
        self.assertIn('35',result['units'][-1]['body'])

    def test_invalid_and_untrusted_files(self):
        for name,data in [('a.doc',b'old'),('a.txt',b'\x00bad'),('a.pdf',b'bad'),('a.docx',archive({'../word/document.xml':'bad'})),('a.docx',archive({'word/document.xml':'<!DOCTYPE x><root/>'})),('a.docx',archive({'word/vbaProject.bin':'macro'}))]:
            with self.subTest(name=name),self.assertRaises(Exception):extract(data,name)
        result=asyncio.run(extract_async(b'Part,Count\nSwitch,2','a.csv'))
        self.assertEqual(len(result['units']),2)
        with self.assertRaises(ValueError):asyncio.run(extract_async(b'bad','a.pdf'))