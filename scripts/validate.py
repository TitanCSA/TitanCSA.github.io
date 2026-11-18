from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
import json,re,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist';BASE='https://titancsa.github.io/'
class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=[];self.title='';self.description='';self.canonical='';self.h1=0;self.in_title=False;self.in_schema=False;self.schema_text='';self.schemas=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='h1':self.h1+=1
        if tag=='title':self.in_title=True
        if tag=='meta' and a.get('name')=='description':self.description=a.get('content','')
        if tag=='link' and a.get('rel')=='canonical':self.canonical=a.get('href','')
        if tag in ['a','img','link','script']:
            value=a.get('href') or a.get('src')
            if value:self.links.append(value)
        if tag=='script' and a.get('type')=='application/ld+json':self.in_schema=True;self.schema_text=''
    def handle_data(self,data):
        if self.in_title:self.title+=data
        if self.in_schema:self.schema_text+=data
    def handle_endtag(self,tag):
        if tag=='title':self.in_title=False
        if tag=='script' and self.in_schema:self.schemas.append(json.loads(self.schema_text));self.in_schema=False

data=json.loads((ROOT/'projects.json').read_text());projects=data['projects']
assert len(projects)==60==len({p['url'].lower() for p in projects})
assert len({p['category'] for p in projects})==10
for p in projects:
    assert p['name'] and p['description'] and p['first_step'] and isinstance(p['start_without_adding_driver'],bool)
    assert p['kind'] in ['Application','Driver SDK','SDK sources','Preview','Dataset']
    assert p['url'].startswith(('https://github.com/TitanCSA/','https://github.com/titanfyre/'))
for name in ['Serial-Device-Simulator','Virtual-COM-Workbench','File-Trace-Studio','RegistryGuard']:
    assert next(p for p in projects if p['name']==name)['kind']=='Preview'
parsed={}
for p in OUT.rglob('*.html'):
    page=Page();page.feed(p.read_text(encoding='utf8'));parsed[p.resolve()]=page
    assert page.h1==1 and page.title and page.description,p
    assert len(page.ids)==len(set(page.ids)),('Duplicate ID',p)
    assert page.canonical.startswith(BASE) and page.schemas,p
    assert p.stat().st_size<200_000,('HTML budget exceeded',p)
assert len({p.title for p in parsed.values()})==len(parsed)
assert len({p.description for p in parsed.values()})==len(parsed)
for path,page in parsed.items():
    for link in page.links:
        url=urlparse(link)
        if url.scheme and not link.startswith(BASE):continue
        if link.startswith(BASE+'TitanCSA-Benchmarks/'):continue
        if url.scheme and url.scheme not in ['http','https']:continue
        target=(OUT/unquote(url.path.lstrip('/'))) if url.path.startswith('/') else path.parent/unquote(url.path)
        if not url.path:target=path
        if target.is_dir():target/= 'index.html'
        target=target.resolve()
        assert target.exists(),(path.name,link)
        if url.fragment and target in parsed:assert unquote(url.fragment) in parsed[target].ids,(path.name,link)
assert (OUT/'index.html').read_text(encoding='utf8').count('data-project data-category=')==60
assert (OUT/'assets/social.png').is_file()
assert (OUT/'assets/site.css').stat().st_size<50_000
assert (OUT/'assets/catalogue.js').stat().st_size<15_000
robots=(OUT/'robots.txt').read_text();assert 'Allow: /' in robots and BASE+'sitemap.xml' in robots
tree=ET.parse(OUT/'sitemap.xml');assert len(tree.getroot())==5
print('Validated',len(parsed),'HTML files, 60 entries, 10 workflows, metadata, JSON-LD, anchors and asset budgets')
