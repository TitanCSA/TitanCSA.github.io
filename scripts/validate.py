from pathlib import Path
from html.parser import HTMLParser
from hashlib import sha256
from urllib.parse import urlparse,unquote
import json,re,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist';BASE='https://titancsa.github.io/'
class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=[];self.title='';self.description='';self.canonical='';self.h1=0;self.in_title=False;self.in_schema=False;self.schema_text='';self.schemas=[];self.google_verification=None;self.language=None;self.alternates={}
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='h1':self.h1+=1
        if tag=='title':self.in_title=True
        if tag=='meta' and a.get('name')=='description':self.description=a.get('content','')
        if tag=='meta' and a.get('name')=='google-site-verification':self.google_verification=a.get('content')
        if tag=='link' and a.get('rel')=='canonical':self.canonical=a.get('href','')
        if tag=='html':self.language=a.get('lang')
        if tag=='link' and a.get('rel')=='alternate' and 'hreflang' in a:
            assert a['hreflang'] not in self.alternates
            self.alternates[a['hreflang']]=a['href']
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
by_canonical={p.canonical:p for path,p in parsed.items() if path.name!='404.html'}
for page in by_canonical.values():
    if page.alternates:
        assert page.alternates[page.language]==page.canonical
        for language,url in page.alternates.items():
            target=by_canonical[url]
            assert target.language==language and target.alternates==page.alternates
if (ROOT/'site-verification.json').exists():
    verification=json.loads((ROOT/'site-verification.json').read_text())
    assert parsed[(OUT/'index.html').resolve()].google_verification==verification['google_site_verification']
    if key:=verification.get('indexnow_key'):
        assert (OUT/f'{key}.txt').read_text().strip()==key
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
hid_result=json.loads((OUT/'assets/vdevice-hid-test-20261124.json').read_text(encoding='utf8'))
assert hid_result['source_sha256']==sha256((OUT/'assets/vdevice-hid-test.cpp').read_bytes()).hexdigest()
robots=(OUT/'robots.txt').read_text();assert 'Allow: /' in robots and BASE+'sitemap.xml' in robots
for bot in ('OAI-SearchBot','Claude-SearchBot','Claude-User'):
    assert f'User-agent: {bot}\n' in robots
tree=ET.parse(OUT/'sitemap.xml')
assert {url.findtext('{*}loc') for url in tree.getroot()} == {
    page.canonical for path,page in parsed.items() if path.name!='404.html'
}
project_pages={path for path in parsed if path.parent.parent.name=='projects'}
assert len(project_pages)==5
editions={row['slug']:row for row in json.loads((OUT/'releases.json').read_text(encoding='utf8'))['editions']}
assert set(editions)=={path.parent.name for path in project_pages}
comparison=parsed[(OUT/'guides/windows-input-release-compare/index.html').resolve()]
french_comparison=by_canonical[BASE+'fr/pilotes-entree-windows/']
assert comparison.alternates=={'en':comparison.canonical,'fr':french_comparison.canonical}
reference=(OUT/'llms.txt').read_text(encoding='utf8')
for path in project_pages:
    edition=editions[path.parent.name]
    page=parsed[path]
    assert page.canonical==edition['overview_url']
    assert edition['demo_url'] in page.links and edition['demo_url'] in comparison.links
    assert edition['purchase_url'] in page.links and edition['purchase_url'] in comparison.links
    assert edition['demo_url'] in french_comparison.links and edition['purchase_url'] in french_comparison.links
    assert edition['overview_url'] in reference and edition['demo_url'] in reference
    app,=[item for item in page.schemas if item.get('@type')=='SoftwareApplication']
    assert app['offers']['url']==edition['purchase_url'] and app['offers']['price']==edition['price_eur']
    assert app['offers']['priceCurrency']=='EUR' and f'€{edition["price_eur"]}' in path.read_text(encoding='utf8')
print('Validated',len(parsed),'HTML files, 60 entries, 10 workflows, metadata, JSON-LD, anchors and asset budgets')
