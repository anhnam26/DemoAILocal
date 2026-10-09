import asyncio,unittest
from unittest.mock import AsyncMock,patch
import httpx
from cyberant import url_reader,document_extractors


class URLReader(unittest.TestCase):
    def test_urls_and_ips(self):
        for url in ['http://example.com','https://127.0.0.1','https://example.com:444','https://user:pass@example.com','https://x.local','https://x.localhost','https://example.com\n/']:
            with self.subTest(url=url),self.assertRaises(ValueError):url_reader.validate_url(url)
        for ip in ['127.0.0.1','10.0.0.1','169.254.169.254','::1','::ffff:8.8.8.8','224.0.0.1','0.0.0.0']:
            self.assertFalse(url_reader.public_ip(ip),ip)
        self.assertTrue(url_reader.public_ip('8.8.8.8'))

    def test_pinned_backend_never_resolves_host_again(self):
        async def run():
            backend=url_reader.PinnedBackend('example.com','8.8.8.8')
            backend.backend.connect_tcp=AsyncMock(return_value='stream')
            self.assertEqual(await backend.connect_tcp('example.com',443),'stream')
            backend.backend.connect_tcp.assert_awaited_once_with('8.8.8.8',443,None,None,None)
            with self.assertRaises(ValueError):await backend.connect_tcp('evil.com',443)
        asyncio.run(run())

    def test_structured_public_document_evidence(self):
        parsed=dict(units=[dict(location='Sheet Quote · hàng 2',body='B2: 6',structure=dict(kind='worksheet_row',hidden_row=True))],warnings=[],extraction_version=2)
        async def run():
            with patch('cyberant.url_reader.download',AsyncMock(return_value=('https://example.com/file.xlsx','application/octet-stream',b'synthetic'))),patch('cyberant.document_extractors.extract_async',AsyncMock(return_value=parsed)):
                result=await url_reader.read('https://example.com/file.xlsx')
                source=result['sources'][0]
                self.assertEqual(source['body'],document_extractors.evidence_body(parsed['units'][0]))
                self.assertTrue(source['extraction_structure']['hidden_row'])
        asyncio.run(run())

    def test_mixed_dns_is_rejected(self):
        async def run():
            loop=asyncio.get_running_loop()
            records=[(2,1,6,'',('8.8.8.8',443)),(2,1,6,'',('10.0.0.1',443))]
            with patch.object(loop,'getaddrinfo',AsyncMock(return_value=records)):
                with self.assertRaises(ValueError):await url_reader.resolve('example.com')
        asyncio.run(run())

    def test_download_redirect_and_limits(self):
        calls=[]
        def handler(request):
            calls.append(str(request.url))
            return httpx.Response(302,headers={'location':'https://127.0.0.1/secret'})
        async def run():
            with patch('cyberant.url_reader.resolve',AsyncMock(return_value=['8.8.8.8'])),patch('cyberant.url_reader.PinnedTransport',side_effect=lambda *a:httpx.MockTransport(handler)):
                with self.assertRaises(ValueError):await url_reader.download('https://example.com')
        asyncio.run(run());self.assertEqual(len(calls),1)
        for headers in ({'content-length':'10000001'},{'content-encoding':'gzip'}):
            async def check():
                with patch('cyberant.url_reader.resolve',AsyncMock(return_value=['8.8.8.8'])),patch('cyberant.url_reader.PinnedTransport',side_effect=lambda *a:httpx.MockTransport(lambda r:httpx.Response(200,headers=headers))):
                    with self.assertRaises(ValueError):await url_reader.download('https://example.com')
            asyncio.run(check())

    def test_html_and_document_extraction(self):
        async def run():
            with patch('cyberant.url_reader.download',AsyncMock(return_value=('https://example.com','text/html',b'<title>Official</title><script>SECRET</script><p>Public fact</p><table><tr><td>SKU</td><td>2</td></tr></table>'))):
                result=await url_reader.read('https://example.com')
                text=str(result);self.assertIn('Public fact',text);self.assertNotIn('SECRET',text);self.assertIn('SKU | 2',text)
                self.assertTrue(result['sources'][0]['id'].startswith('WEB-'))
            with patch('cyberant.url_reader.download',AsyncMock(return_value=('https://example.com/file.csv','text/csv',b'Part,Count\nSwitch,2'))):
                result=await url_reader.read('https://example.com/file.csv')
                self.assertEqual(result['units'],2)
        asyncio.run(run())