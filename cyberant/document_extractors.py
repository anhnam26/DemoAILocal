"""Bounded text extraction using existing pypdf and standard-library OOXML.

No macros, external relationships, formula execution, OCR or image inference.
Each unit keeps its page/sheet/slide/section location; limits fail explicitly.
"""
import asyncio,csv,io,json,posixpath,re,sys,zipfile
import xml.etree.ElementTree as ET
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


def extract(raw,name):
    suffix=Path(name).suffix.lower()
    if suffix not in SUPPORTED:raise ValueError('Nhận TXT/MD/CSV/PDF/DOCX/XLSX/PPTX. DOC/XLS/PPT cũ cần chuyển định dạng; không nhận macro.')
    if not raw or len(raw)>MAX_BYTES:raise ValueError('File trống hoặc vượt 10 MB.')
    units=[];warnings=[];size=0
    def add(location,text):
        nonlocal size
        text=text.strip()
        if not text:return
        size+=len(text)
        if size>MAX_TEXT or len(units)>=MAX_UNITS:raise ValueError('Nội dung vượt giới hạn trích xuất; chia file theo mục/sheet/trang. Không lưu bản đọc thiếu.')
        # Long units split at line boundaries with an explicit part location.
        lines=text.splitlines();part=[];length=0;number=1
        for line in lines:
            if len(line)>16000:raise ValueError('Một dòng nội dung quá lớn; chia nhỏ trước khi tải.')
            if length+len(line)>16000 and part:
                units.append(dict(location=f'{location} · phần {number}',body='\n'.join(part)));part=[];length=0;number+=1
            part.append(line);length+=len(line)+1
            if len(units)>=MAX_UNITS:raise ValueError('Quá nhiều phần tài liệu.')
        units.append(dict(location=location if number==1 else f'{location} · phần {number}',body='\n'.join(part)))
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
                root=tree('word/document.xml');body=root.find(W+'body')
                if body is None:raise ValueError('DOCX thiếu body.')
                for i,node in enumerate(body,1):
                    if node.tag==W+'tbl':
                        rows=[' | '.join(texts(cell,W) for cell in row.findall(W+'tc')) for row in node.findall(W+'tr')]
                        add(f'Bảng/khối {i}','\n'.join(rows))
                    else:add(f'Đoạn/khối {i}',texts(node,W))
                for path in sorted(z.namelist()):
                    if re.fullmatch(r'word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml',path):add(path,texts(tree(path),W))
                warnings.append('DOCX: ảnh, textbox và bố cục phức tạp chưa được kiểm chứng.')
            elif suffix=='.xlsx':
                strings=[]
                if 'xl/sharedStrings.xml' in z.namelist():strings=[texts(si,S) for si in tree('xl/sharedStrings.xml').findall(S+'si')]
                links=rels('xl/_rels/workbook.xml.rels')
                for sheet in tree('xl/workbook.xml').findall(S+'sheets/'+S+'sheet'):
                    path=target('xl',links[sheet.attrib[R+'id']]);root=tree(path);name=sheet.attrib['name']
                    merged=[n.attrib['ref'] for n in root.findall('.//'+S+'mergeCell')]
                    if merged:add(f'Sheet {name} · merged ranges',', '.join(merged))
                    for row in root.findall('.//'+S+'row'):
                        cells=[]
                        for cell in row.findall(S+'c'):
                            value=cell.findtext(S+'v',default='');typ=cell.get('t')
                            if typ=='s' and value:value=strings[int(value)]
                            elif typ=='inlineStr':value=texts(cell,S)
                            formula=cell.find(S+'f')
                            if formula is not None:value=f'{value or "CHƯA CÓ CACHED VALUE"} [công thức: {formula.text or "shared"}; cache chưa xác minh]'
                            if value:cells.append(f'{cell.attrib["r"]}: {value}')
                        add(f'Sheet {name} · hàng {row.get("r","?")}',' | '.join(cells))
                warnings.append('Excel: không tính lại công thức; cached value có thể cũ. Giữ địa chỉ ô; merged cells không tự điền số lượng.')
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
    return dict(format=suffix[1:],units=units,warnings=warnings,characters=size,extraction_version=1)


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