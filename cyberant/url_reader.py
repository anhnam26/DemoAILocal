"""Public HTTPS reader: DNS-validated and pinned TCP, original TLS hostname.

The httpx 0.28/httpcore 1 adapter below is deliberately isolated. Every redirect
gets a new resolution/pool. No proxies, cookies, credentials or JS execution.
"""
import asyncio,hashlib,ipaddress,re,socket,ssl
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urlsplit,urljoin,unquote
import httpx,httpcore
from httpcore._backends.auto import AutoBackend
from cyberant import document_extractors,web_search

MAX_BODY=10_000_000


def validate_url(url):
    if not web_search.safe_url(url) or any(ord(c)<32 for c in url):raise ValueError('Chỉ đọc HTTPS công khai cổng 443, không credentials hoặc địa chỉ nội bộ.')
    host=urlsplit(url).hostname
    if host.endswith(('.localhost','.test','.invalid')):raise ValueError('Hostname không công khai.')
    return host.encode('idna').decode('ascii').lower()


def public_ip(value):
    ip=ipaddress.ip_address(value.split('%')[0])
    return ip.is_global and not (ip.is_multicast or ip.is_unspecified or ip.is_reserved or ip.is_loopback or ip.is_link_local) and not (isinstance(ip,ipaddress.IPv6Address) and (ip.ipv4_mapped or ip.sixtofour or ip.teredo))


async def resolve(host):
    results=await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(host,443,type=socket.SOCK_STREAM),5)
    ips=list(dict.fromkeys(item[4][0] for item in results))
    if not ips or not all(public_ip(ip) for ip in ips):raise ValueError('DNS có địa chỉ không công khai; từ chối kết nối.')
    return ips


class PinnedBackend(httpcore.AsyncNetworkBackend):
    def __init__(self,host,ip):self.host=host;self.ip=ip;self.backend=AutoBackend()

    async def connect_tcp(self,host,port,timeout=None,local_address=None,socket_options=None):
        if isinstance(host,bytes):host=host.decode('ascii')
        if host.lower()!=self.host or port!=443 or not public_ip(self.ip):raise ValueError('Đích kết nối không khớp địa chỉ đã duyệt.')
        return await self.backend.connect_tcp(self.ip,port,timeout,local_address,socket_options)

    async def connect_unix_socket(self,*args,**kwargs):raise ValueError('Unix sockets not allowed')
    async def sleep(self,seconds):await asyncio.sleep(seconds)


class PinnedTransport(httpx.AsyncHTTPTransport):
    def __init__(self,host,ip):
        super().__init__(trust_env=False,retries=0)
        self._pool=httpcore.AsyncConnectionPool(ssl_context=ssl.create_default_context(),network_backend=PinnedBackend(host,ip),max_connections=1,max_keepalive_connections=0,retries=0)


class PageText(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.ignored=0;self.title=[];self.in_title=False
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript','svg','template'):self.ignored+=1
        if tag=='title':self.in_title=True
        if not self.ignored and tag in ('p','div','li','h1','h2','h3','tr','br'):self.parts.append('\n')
        if not self.ignored and tag in ('td','th'):self.parts.append(' | ')
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript','svg','template'):self.ignored=max(0,self.ignored-1)
        if tag=='title':self.in_title=False
        if not self.ignored and tag in ('p','div','li','h1','h2','h3','tr'):self.parts.append('\n')
    def handle_data(self,data):
        if self.in_title:self.title.append(data)
        if not self.ignored:self.parts.append(data)
    def text(self):return '\n'.join(line for line in (re.sub(r'\s+',' ',s).strip() for s in ''.join(self.parts).splitlines()) if line)


async def download(url):
    for redirect in range(5):
        host=validate_url(url);ips=await resolve(host)
        async with httpx.AsyncClient(transport=PinnedTransport(host,ips[0]),trust_env=False,timeout=httpx.Timeout(20,connect=8),follow_redirects=False) as client:
            async with client.stream('GET',url,headers={'User-Agent':'CyberAnt/1.0 public-document-reader','Accept-Encoding':'identity'}) as response:
                if response.status_code in (301,302,303,307,308):
                    location=response.headers.get('location')
                    if not location:raise ValueError('Redirect không có URL đích.')
                    url=urljoin(url,location);validate_url(url);continue
                response.raise_for_status()
                if response.headers.get('content-encoding','identity').lower() not in ('','identity'):raise ValueError('Trang trả nội dung nén dù đã yêu cầu identity; từ chối để giới hạn giải nén.')
                length=response.headers.get('content-length')
                if length and int(length)>MAX_BODY:raise ValueError('URL vượt 10 MB.')
                raw=bytearray()
                async for chunk in response.aiter_raw():
                    raw.extend(chunk)
                    if len(raw)>MAX_BODY:raise ValueError('URL vượt 10 MB.')
                return url,response.headers.get('content-type','').lower(),bytes(raw)
    raise ValueError('Quá nhiều redirect.')


async def read(url):
    async with asyncio.timeout(60):
        final,mime,raw=await download(url)
        name=unquote(PurePosixPath(urlsplit(final).path).name) or 'web-page'
        suffix=PurePosixPath(name).suffix.lower()
        if 'text/html' in mime or 'application/xhtml+xml' in mime:
            page=PageText();encoding=re.search(r'charset=([\w-]+)',mime)
            page.feed(raw.decode(encoding.group(1) if encoding else 'utf8',errors='replace'))
            text=page.text()
            if len(text)>document_extractors.MAX_TEXT:raise ValueError('Trang có quá nhiều text; cần chọn tài liệu nhỏ hơn.')
            title=''.join(page.title).strip()[:200] or name
            parsed=await document_extractors.extract_async(text.encode(),'page.txt')
            parsed['warnings'].append('Chỉ đọc HTML tĩnh; không chạy JavaScript, không đọc nội dung yêu cầu đăng nhập hoặc ảnh.')
        elif suffix in document_extractors.SUPPORTED:
            title=name;parsed=await document_extractors.extract_async(raw,name)
        elif 'application/pdf' in mime:
            title=name;parsed=await document_extractors.extract_async(raw,'document.pdf')
        elif mime.startswith('text/plain'):
            title=name;parsed=await document_extractors.extract_async(raw,'document.txt')
        else:raise ValueError('URL không trả HTML/text/PDF hoặc Office được hỗ trợ.')
        stamp=datetime.now(timezone.utc).isoformat();prefix='WEB-'+hashlib.sha256((stamp+final).encode()).hexdigest()[:20]
        sources=[dict(id=prefix+'-'+str(i),title=title+' · '+unit['location'],body=unit['body'],url=final,retrieved_at=stamp,review_status='external_unverified',chunk=1,version='web') for i,unit in enumerate(parsed['units'],1)]
        return dict(url=final,title=title,sources=sources,warnings=parsed['warnings'],units=len(sources))