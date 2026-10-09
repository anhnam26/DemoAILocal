"""Bounded text extraction using existing pypdf and standard-library OOXML.

No macros, external relationships, formula execution, OCR or image inference.
Each unit keeps its page/sheet/slide/section location; limits fail explicitly.
"""
import asyncio,csv,io,json,posixpath,re,sys,zipfile
import xml.etree.ElementTree as ET
from datetime import datetime,timedelta
from decimal import Decimal,InvalidOperation
from pathlib import Path
from pypdf import PdfReader

MAX_BYTES=10_000_000
MAX_TEXT=1_000_000
MAX_UNITS=2000
SUPPORTED={'.txt','.md','.csv','.pdf','.docx','.xlsx','.pptx'}
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
S='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
EXTRACTION_VERSION=2


def evidence_body(unit):
    """One canonical body for indexing, prompting and dependency digests.

    Old units contain only body/location and retain their exact prior body.
    Structure is data, never instructions or an assertion of factual verification.
    """
    structure=unit.get('structure')
    return unit['body']+('\n\nCấu trúc trích xuất (chưa xác minh nghiệp vụ): '+json.dumps(structure,ensure_ascii=False,sort_keys=True)
                         if structure else '')


def word_text(node):
    """Current revision text: excluded deletions/moveFrom are not current facts."""
    if node.tag in (W+'del',W+'moveFrom',W+'drawing',W+'pict',W+'txbxContent'):return ''
    if node.tag==W+'t':return node.text or ''
    if node.tag==W+'tab':return '\t'
    if node.tag in (W+'br',W+'cr'):return '\n'
    return ''.join(word_text(child) for child in node)


def word_units(z,tree,add,warnings):
    root=tree('word/document.xml');body=root.find(W+'body')
    if body is None:raise ValueError('DOCX thiếu body.')
    styles={}
    if 'word/styles.xml' in z.namelist():
        for style in tree('word/styles.xml').findall(W+'style'):
            level=style.find(W+'pPr/'+W+'outlineLvl');parent=style.find(W+'basedOn')
            styles[style.get(W+'styleId')]=(level.get(W+'val') if level is not None else None,parent.get(W+'val') if parent is not None else None)
    def outline(node):
        direct=node.find(W+'pPr/'+W+'outlineLvl')
        if direct is not None:return int(direct.get(W+'val','9'))
        style=node.find(W+'pPr/'+W+'pStyle');key=style.get(W+'val') if style is not None else None;seen=set()
        while key in styles and key not in seen:
            seen.add(key);level,key=styles[key]
            if level is not None:return int(level)
        return 9
    headings=[]
    for i,node in enumerate(body,1):
        if node.tag==W+'p':
            text=word_text(node);level=outline(node)
            if text.strip() and 0<=level<9:
                headings=[(n,t) for n,t in headings if n<level]+[(level,text.strip())]
            structure=dict(kind='heading' if level<9 else 'paragraph',block=i,heading_path=[t for _,t in headings])
            numbering=node.find(W+'pPr/'+W+'numPr')
            if numbering is not None:
                structure['list']={c.tag.removeprefix(W):c.get(W+'val') for c in numbering}
            notes={tag:[n.get(W+'id') for n in node.iter(W+tag)] for tag in ('footnoteReference','endnoteReference','commentRangeStart')}
            structure['references']={k:v for k,v in notes.items() if v}
            add(f'Đoạn/khối {i}',text,structure)
        elif node.tag==W+'tbl':
            headers=[]
            for row_index,row in enumerate(node.findall(W+'tr'),1):
                cells=[];column=1
                before=row.find(W+'trPr/'+W+'gridBefore')
                if before is not None:column+=int(before.get(W+'val','0'))
                for cell in row.findall(W+'tc'):
                    span=cell.find(W+'tcPr/'+W+'gridSpan');merge=cell.find(W+'tcPr/'+W+'vMerge')
                    width=int(span.get(W+'val','1')) if span is not None else 1
                    if width<1 or column+width>16385:raise ValueError('Word table grid không hợp lệ.')
                    text='\n'.join(word_text(p) for p in cell.findall(W+'p'))
                    cells.append(dict(column=column,span=width,text=text,vertical_merge=merge.get(W+'val','continue') if merge is not None else None))
                    column+=width
                    if cell.find(W+'tbl') is not None:warnings.append('DOCX: bảng lồng trong ô chưa được trích xuất; không coi bảng là đầy đủ.')
                marker=row.find(W+'trPr/'+W+'tblHeader')
                is_header=marker is not None and marker.get(W+'val','true') not in ('0','false','off')
                if is_header:headers.append([c['text'] for c in cells])
                structure=dict(kind='table_row',block=i,row=row_index,heading_path=[t for _,t in headings],
                               cells=cells,is_header=is_header,declared_headers=list(headers))
                add(f'Bảng/khối {i} · hàng {row_index}',' | '.join(c['text'] for c in cells),structure)
        elif node.tag!=W+'sectPr':
            warnings.append('DOCX: khối nội dung chưa hỗ trợ '+node.tag.removeprefix(W)+'.')
    for path in sorted(z.namelist()):
        if not re.fullmatch(r'word/(?:header\d+|footer\d+|footnotes|endnotes|comments)\.xml',path):continue
        root=tree(path);kind=Path(path).stem
        if kind in ('footnotes','endnotes','comments'):
            for item in root:
                id=item.get(W+'id','?')
                if id.startswith('-') or item.get(W+'type') in ('separator','continuationSeparator'):continue
                text='\n'.join(word_text(p) for p in item.iter(W+'p'))
                add(path+' · id '+id,text,dict(kind=kind,id=id,part=path))
        else:
            add(path,'\n'.join(word_text(p) for p in root.iter(W+'p')),dict(kind=kind,part=path))
    if any(n.tag in (W+'ins',W+'del',W+'moveFrom',W+'moveTo') for n in body.iter()):
        warnings.append('DOCX: có tracked changes; đọc bản hiện hành (gồm chèn/moveTo, loại del/moveFrom), không phải chứng nhận đã duyệt sửa đổi.')
    warnings.append('DOCX: mục/đoạn/hàng bảng không phải số trang render; ảnh, textbox, numbering hiển thị và bố cục phức tạp chưa được kiểm chứng. Comments/notes là nguồn riêng.')


BUILTIN_FORMATS={0:'General',1:'0',2:'0.00',3:'#,##0',4:'#,##0.00',9:'0%',10:'0.00%',
                 14:'mm-dd-yy',15:'d-mmm-yy',16:'d-mmm',17:'mmm-yy',18:'h:mm AM/PM',19:'h:mm:ss AM/PM',
                 20:'h:mm',21:'h:mm:ss',22:'m/d/yy h:mm',49:'@'}


def excel_value(raw,typ,format_code,date1904=False):
    """Conservative interpretation; raw OOXML values are always preserved.

    Decimal values are strings, never binary float-rounded money. This is not
    an Excel display renderer, tax engine or formula calculator.
    """
    if raw=='':return dict(type='blank',value=None)
    if typ in ('s','inlineStr','str'):return dict(type='text',value=raw)
    if typ=='e':return dict(type='error',value=raw)
    if typ=='b':
        if raw not in ('0','1'):raise ValueError('Excel boolean không hợp lệ.')
        return dict(type='boolean',value=raw=='1')
    if typ=='d':return dict(type='date_iso',value=raw,status='source_iso_not_normalized')
    if typ not in (None,'n'):return dict(type='unknown',value=raw,status='unsupported_cell_type')
    try:number=Decimal(raw)
    except InvalidOperation:raise ValueError('Excel numeric không hợp lệ.') from None
    if not number.is_finite() or len(raw)>200 or abs(number.adjusted())>100:raise ValueError('Excel numeric vượt giới hạn.')
    code=format_code or 'General'
    # Only well-known or unambiguous single-section formats are interpreted.
    # Multi-section conditional/scaled/localized formats remain explicitly raw.
    simple=re.sub(r'"[^"]*"|\\.', '',code)
    value=dict(type='number',value=str(number),status='raw_numeric')
    if ';' in code or re.search(r'\[[<>=]|\[h\]|\[m\]|\[s\]',simple,re.I):
        return {**value,'status':'complex_format_not_rendered'}
    if code in ('General','@'):return value
    if re.fullmatch(r'0{2,20}',code):
        if number==number.to_integral_value():return dict(type='formatted_identifier',value=str(number),display=format(int(number),f'0{len(code)}d'),status='leading_zero_format')
    if '%' in simple:return dict(type='percentage',value=str(number),percent_value=str(number*100),status='ratio_not_money')
    # Currency symbols/codes do not prove the transaction's authoritative currency.
    currency=re.search(r'\[\$([^\]-]+)(?:-[^\]]+)?\]|(USD|VND|EUR|GBP|JPY|₫|đ|\$|€|£|¥)',code,re.I)
    if currency:return dict(type='currency',value=str(number),currency_marker=currency[1] or currency[2],status='format_marker_not_currency_confirmation')
    cleaned=re.sub(r'\[[^\]]*\]','',simple).lower()
    if re.search(r'[ydhs]',cleaned) or re.fullmatch(r'm+[/-]d+(?:[/-]y+)?',cleaned):
        if not Decimal('0')<=number<=Decimal('2958465'):return {**value,'status':'date_serial_out_of_range'}
        if not date1904 and 60<=number<61:
            return dict(type='date_serial',value=str(number),date_system='1900',status='excel_fictitious_1900_02_29')
        days=number-(1 if not date1904 and number>=61 else 0)
        base=datetime(1904,1,1) if date1904 else datetime(1899,12,31)
        try:date=base+timedelta(microseconds=int(days*86400*1000000))
        except OverflowError:return {**value,'status':'date_serial_out_of_range'}
        return dict(type='datetime',value=date.isoformat(),serial=raw,date_system='1904' if date1904 else '1900',status='format_interpreted_no_timezone')
    return {**value,'status':'numeric_format_not_rendered'}


def excel_units(z,tree,target,rels,texts,add,warnings):
    workbook=tree('xl/workbook.xml');props=workbook.find(S+'workbookPr')
    date1904=props is not None and props.get('date1904') in ('1','true')
    formats=dict(BUILTIN_FORMATS);styles=[0]
    if 'xl/styles.xml' in z.namelist():
        root=tree('xl/styles.xml')
        formats.update({int(n.attrib['numFmtId']):n.attrib['formatCode'] for n in root.findall(S+'numFmts/'+S+'numFmt')})
        styles=[int(n.get('numFmtId','0')) for n in root.findall(S+'cellXfs/'+S+'xf')] or [0]
    strings=[]
    if 'xl/sharedStrings.xml' in z.namelist():strings=[texts(si,S) for si in tree('xl/sharedStrings.xml').findall(S+'si')]
    links=rels('xl/_rels/workbook.xml.rels')
    for sheet in workbook.findall(S+'sheets/'+S+'sheet'):
        path=target('xl',links[sheet.attrib[R+'id']]);root=tree(path);name=sheet.attrib['name'];state=sheet.get('state','visible')
        merged=[n.attrib['ref'] for n in root.findall('.//'+S+'mergeCell')]
        columns=[dict(first=int(n.attrib['min']),last=int(n.attrib['max']),hidden=n.get('hidden') in ('1','true')) for n in root.findall(S+'cols/'+S+'col')]
        filter_node=root.find(S+'autoFilter')
        filters=[]
        if filter_node is not None:
            filters.append(dict(ref=filter_node.get('ref'),criteria_present=bool(list(filter_node))))
        tables=[]
        relpath=posixpath.join(posixpath.dirname(path),'_rels',posixpath.basename(path)+'.rels');sheet_links=rels(relpath)
        for node in root.findall(S+'tableParts/'+S+'tablePart'):
            table=tree(target(posixpath.dirname(path),sheet_links[node.attrib[R+'id']]))
            table_filter=table.find(S+'autoFilter')
            if table_filter is not None:filters.append(dict(ref=table_filter.get('ref'),criteria_present=bool(list(table_filter))))
            tables.append(dict(name=table.get('name'),ref=table.attrib['ref'],header_rows=int(table.get('headerRowCount','1')),
                               totals_rows=int(table.get('totalsRowCount','0')),headers=[n.get('name','') for n in table.findall(S+'tableColumns/'+S+'tableColumn')]))
        if merged:add(f'Sheet {name} · merged ranges',', '.join(merged),dict(kind='merged_ranges',sheet=name,ranges=merged,sheet_state=state))
        for row in root.findall(S+'sheetData/'+S+'row'):
            cells=[];lines=[];row_number=int(row.attrib['r'])
            for cell in row.findall(S+'c'):
                address=cell.attrib['r'];match=re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]*)',address)
                if not match or int(match[2])!=row_number:raise ValueError('Excel địa chỉ ô không hợp lệ.')
                column=0
                for letter in match[1]:column=column*26+ord(letter)-64
                if column>16384 or row_number>1048576:raise ValueError('Excel ô vượt giới hạn.')
                raw=cell.findtext(S+'v',default='');typ=cell.get('t');resolved=raw
                if typ=='s' and raw:
                    index=int(raw)
                    if not 0<=index<len(strings):raise ValueError('Excel shared string không hợp lệ.')
                    resolved=strings[index]
                elif typ=='inlineStr':resolved=texts(cell,S)
                style=int(cell.get('s','0'))
                if not 0<=style<len(styles):raise ValueError('Excel style không hợp lệ.')
                format_id=styles[style];code=formats.get(format_id)
                parsed=excel_value(resolved,typ,code,date1904)
                if code is None:parsed['status']='unsupported_number_format'
                formula=cell.find(S+'f')
                cached=raw!='' or (typ=='inlineStr' and resolved!='')
                record=dict(address=address,raw=raw,text=resolved,data_type=typ or 'n',format_id=format_id,format_code=code,
                            interpreted=parsed,hidden_column=any(c['hidden'] and c['first']<=column<=c['last'] for c in columns))
                if formula is not None:
                    record['formula']=dict(expression=formula.text,attributes=dict(formula.attrib),cached=cached,status='cache_unverified' if cached else 'cache_missing')
                cells.append(record)
                display=parsed.get('display',resolved) if resolved!='' else 'Ô TRỐNG'
                if formula is not None:display=f'{display if cached else "CHƯA CÓ CACHED VALUE"} [công thức: {formula.text or "shared"}; cache chưa xác minh]'
                lines.append(address+': '+display)
            # Keep only explicitly declared table context, not guessed first-row headers.
            relevant=[]
            for table in tables:
                bounds=re.fullmatch(r'([A-Z]+)(\d+):([A-Z]+)(\d+)',table['ref'])
                if not bounds:raise ValueError('Excel table range không hợp lệ.')
                if int(bounds[2])<=row_number<=int(bounds[4]):relevant.append(table)
            structure=dict(kind='worksheet_row',sheet=name,row=row_number,sheet_state=state,
                           hidden_row=row.get('hidden') in ('1','true'),filters=filters,tables=relevant,cells=cells)
            add(f'Sheet {name} · hàng {row_number}',' | '.join(lines),structure)
        if state!='visible' or any(c['hidden'] for c in columns) or filters or any(row.get('hidden') in ('1','true') for row in root.findall(S+'sheetData/'+S+'row')):
            warnings.append('Excel: gồm dữ liệu ẩn/bộ lọc; không tự hiểu yêu cầu là chỉ hàng hiển thị, cần xác nhận phạm vi tính.')
        if not root.findall(S+'sheetData/'+S+'row'):
            add(f'Sheet {name} · không có hàng dữ liệu','Không có hàng dữ liệu được lưu trong sheet.',dict(kind='empty_sheet',sheet=name,sheet_state=state))
    if any(p.startswith('xl/externalLinks/') for p in z.namelist()):warnings.append('Excel: có liên kết ngoài, không truy cập hoặc tính lại dữ liệu liên kết.')
    warnings.append('Excel: không tính lại công thức; cached value có thể cũ. Giữ địa chỉ ô; merged cells không tự điền số lượng. Kiểu/định dạng chỉ là diễn giải bảo thủ, không xác nhận tiền tệ, thuế hoặc nghiệp vụ; blank khác 0, subtotal không tự cộng lại.')


def extract(raw,name):
    suffix=Path(name).suffix.lower()
    if suffix not in SUPPORTED:raise ValueError('Nhận TXT/MD/CSV/PDF/DOCX/XLSX/PPTX. DOC/XLS/PPT cũ cần chuyển định dạng; không nhận macro.')
    if not raw or len(raw)>MAX_BYTES:raise ValueError('File trống hoặc vượt 10 MB.')
    units=[];warnings=[];size=0
    def add(location,text,structure=None):
        nonlocal size
        text=text.strip()
        if not text and not structure:return
        size+=len(text)
        if size>MAX_TEXT or len(units)>=MAX_UNITS:raise ValueError('Nội dung vượt giới hạn trích xuất; chia file theo mục/sheet/trang. Không lưu bản đọc thiếu.')
        # Long units split at line boundaries with an explicit part location.
        lines=text.splitlines() or [''];part=[];length=0;number=1
        def append(location,body):
            unit=dict(location=location,body=body)
            if structure:unit['structure']=structure
            # Never repeat a large table's full metadata across split chunks.
            if len(evidence_body(unit).encode('utf8'))>100000:raise ValueError('Một phần dữ liệu cấu trúc quá lớn; chia bảng trước khi tải.')
            units.append(unit)
        for line in lines:
            if len(line)>16000:raise ValueError('Một dòng nội dung quá lớn; chia nhỏ trước khi tải.')
            if length+len(line)>16000 and part:
                append(f'{location} · phần {number}','\n'.join(part));part=[];length=0;number+=1
            part.append(line);length+=len(line)+1
            if len(units)>=MAX_UNITS:raise ValueError('Quá nhiều phần tài liệu.')
        append(location if number==1 else f'{location} · phần {number}','\n'.join(part))
    if suffix in ('.txt','.md','.csv'):
        text=raw.decode('utf-8-sig')
        if '\x00' in text:raise ValueError('File text phải là UTF-8, không chứa NUL.')
        if suffix=='.csv':
            for i,row in enumerate(csv.reader(io.StringIO(text)),1):add(f'Dòng CSV {i}',' | '.join(row))
        else:
            for i in range(0,len(text.splitlines()),60):add(f'Dòng {i+1}–{min(i+60,len(text.splitlines()))}','\n'.join(text.splitlines()[i:i+60]))
    elif suffix=='.pdf':
        reader=PdfReader(io.BytesIO(raw))
        if reader.is_encrypted:raise ValueError('PDF mã hóa cần được mở khóa trước.')
        if len(reader.pages)>500:raise ValueError('PDF vượt 500 trang; hãy chia file.')
        empty=[]
        for i,page in enumerate(reader.pages,1):
            text=page.extract_text() or ''
            if text.strip():add(f'Trang {i}',text)
            else:empty.append(i)
        if empty:warnings.append('Không có text/OCR tại trang: '+', '.join(map(str,empty))+'. Ảnh/sơ đồ chưa được đọc.')
        warnings.append('PDF: thứ tự đọc và cấu trúc bảng cần đối chiếu; không phân tích ảnh/sơ đồ.')
    else:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries=z.infolist()
            if len(entries)>3000 or sum(e.file_size for e in entries)>40_000_000:raise ValueError('OOXML quá lớn sau giải nén.')
            for entry in entries:
                if entry.flag_bits&1 or entry.file_size>8_000_000 or entry.file_size>max(1,entry.compress_size)*200:raise ValueError('OOXML mã hóa hoặc tỷ lệ giải nén không an toàn.')
                if entry.filename.startswith('/') or '\\' in entry.filename or '..' in entry.filename.split('/'):raise ValueError('Đường dẫn OOXML không hợp lệ.')
                if 'vbaproject' in entry.filename.lower():raise ValueError('Không nhận file chứa macro.')
            def tree(path):
                data=z.read(path)
                if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('XML entity/DTD không được phép.')
                return ET.fromstring(data)
            def texts(node,ns):return ''.join(t.text or '' for t in node.iter(ns+'t'))
            def rels(path):
                if path not in z.namelist():return {}
                return {r.attrib['Id']:r.attrib['Target'] for r in tree(path) if r.get('TargetMode')!='External'}
            def target(base,value):
                path=posixpath.normpath(value.lstrip('/') if value.startswith('/') else posixpath.join(base,value))
                if path.startswith('../') or path not in z.namelist():raise ValueError('Tham chiếu OOXML không hợp lệ.')
                return path
            if suffix=='.docx':
                word_units(z,tree,add,warnings)
            elif suffix=='.xlsx':
                excel_units(z,tree,target,rels,texts,add,warnings)
            else:
                links=rels('ppt/_rels/presentation.xml.rels')
                slides=tree('ppt/presentation.xml').findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sldId')
                for i,slide in enumerate(slides,1):
                    path=target('ppt',links[slide.attrib[R+'id']]);root=tree(path)
                    add(f'Slide {i}','\n'.join(texts(p,A) for p in root.iter(A+'p')))
                    relpath=posixpath.join(posixpath.dirname(path),'_rels',posixpath.basename(path)+'.rels')
                    for value in rels(relpath).values():
                        if 'notesSlide' in value:
                            note=tree(target(posixpath.dirname(path),value));add(f'Slide {i} · ghi chú','\n'.join(texts(p,A) for p in note.iter(A+'p')))
                warnings.append('PowerPoint: ảnh, biểu đồ và sơ đồ chưa được phân tích; text giữ theo slide.')
    if not units:raise ValueError('Không có text đọc được; PDF scan/ảnh cần OCR trước.')
    result=dict(format=suffix[1:],units=units,warnings=list(dict.fromkeys(warnings)),characters=size,extraction_version=EXTRACTION_VERSION)
    if len(json.dumps(result,ensure_ascii=True).encode())>8_000_000:raise ValueError('Kết quả trích xuất vượt giới hạn; chia file.')
    return result


async def extract_async(raw,name):
    """Killable parsing process: a thread timeout cannot stop a malformed PDF."""
    if len(raw)>MAX_BYTES:raise ValueError('File vượt 10 MB.')
    # -E ignores PYTHON* overrides but preserves the existing user-site packages.
    proc=await asyncio.create_subprocess_exec(sys.executable,'-E','-B',str(Path(__file__).resolve()),name,
        stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
    try:
        out,_=await asyncio.wait_for(proc.communicate(raw),30)
        if proc.returncode or len(out)>8_000_000:raise ValueError('Không đọc được file trong giới hạn an toàn.')
        result=json.loads(out)
        if 'error' in result:raise ValueError(result['error'])
        return result
    finally:
        if proc.returncode is None:
            proc.kill();await proc.wait()


if __name__=='__main__':
    try:result=extract(sys.stdin.buffer.read(MAX_BYTES+1),sys.argv[1])
    except Exception:result={'error':'File lỗi, không có text, không hỗ trợ hoặc vượt giới hạn trích xuất.'}
    sys.stdout.write(json.dumps(result,ensure_ascii=True))