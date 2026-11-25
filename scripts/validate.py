from zipfile import ZipFile
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
for page in parsed.values():
    content=[item for item in page.schemas if item.get('@type') in ('WebSite','TechArticle')]
    publisher=content[0]['publisher']
    assert publisher['@id']==BASE+'#publisher' and publisher['sameAs']==['https://github.com/TitanCSA']
by_canonical={p.canonical:p for path,p in parsed.items() if path.name!='404.html'}
for page in by_canonical.values():
    if page.alternates:
        assert page.alternates[page.language]==page.canonical
        for language,url in page.alternates.items():
            target=by_canonical[url]
            assert target.language==language and target.alternates==page.alternates
packages_en=by_canonical[BASE+'guides/windows-input-sdk-packages/']
packages_fr=by_canonical[BASE+'fr/installer-sdk-windows/']
package_hosts={'www.npmjs.com','pypi.org','www.nuget.org','www.powershellgallery.com'}
for host in package_hosts:
    refs_en={link for link in packages_en.links if urlparse(link).netloc==host}
    refs_fr={link for link in packages_fr.links if urlparse(link).netloc==host}
    assert refs_en and refs_en==refs_fr, ('Mismatch in bilingual SDK package URLs',host)
assert packages_en.alternates['fr']==packages_fr.canonical
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
hvci_result=json.loads((OUT/'assets/vdevice-hid-test-20261125-hvci.json').read_text(encoding='utf8'))
assert hvci_result['driver_version']==hid_result['driver']
assert hvci_result['driver_sha256']==hid_result['driver_sha256'].lower()
assert hvci_result['platform']['secure_boot'] is True and hvci_result['platform']['memory_integrity'] is True
assert 2 in hvci_result['platform']['device_guard_running_security_services']
assert hvci_result['observed']['producer_exit']==0
assert hvci_result['observed']['receiver_found_no_matching_device_after_removal'] is True
assert all(hvci_result['observed'][f'{direction}_payload_length']==16 for direction in ('input','output'))
robots=(OUT/'robots.txt').read_text();assert 'Allow: /' in robots and BASE+'sitemap.xml' in robots
for bot in ('OAI-SearchBot','Claude-SearchBot','Claude-User'):
    assert f'User-agent: {bot}\n' in robots
tree=ET.parse(OUT/'sitemap.xml')
assert {url.findtext('{*}loc') for url in tree.getroot()} == {
    page.canonical for path,page in parsed.items() if path.name!='404.html'
}
feed=ET.parse(OUT/'rss.xml').getroot()
entries=feed.findall('channel/item')
assert feed.tag=='rss' and feed.get('version')=='2.0' and len(entries)>=10
assert len(entries)==len({item.findtext('guid') for item in entries})
for item in entries:
    url=item.findtext('link')
    assert item.findtext('guid')==url and url in by_canonical
    assert item.findtext('title')==by_canonical[url].title
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
    assert '/about/evidence/#release-contact' in page.links and '/about/evidence/#release-contact' in comparison.links
    assert edition['demo_download_url'] in page.links and edition['demo_download_url'] in comparison.links
    assert edition['demo_download_url'] in french_comparison.links and '#contact-release' in french_comparison.links
    assert set(edition['demo_assets'].values()) <= set(page.links)
    for role, filename in edition['demo_files'].items():
        assert re.fullmatch(r'[A-Za-z0-9._-]+',filename)
        assert edition['demo_assets'][role] == f'{edition["repository"]}/releases/download/{edition["tag"]}/{filename}'
    assert edition['overview_url'] in reference and edition['demo_url'] in reference
    assert '<h2>Try it</h2>' in path.read_text(encoding='utf8')
    app,=[item for item in page.schemas if item.get('@type')=='SoftwareApplication']
    assert app['softwareVersion']==edition['commercial']['package_version']
    assert all(re.fullmatch(r'\d+\.\d+\.\d+\.\d+', value) for value in edition['commercial'].values())
    assert 'offers' not in app
for public_text in [*OUT.rglob('*.html'), OUT/'llms.txt', OUT/'releases.json', OUT/'projects.json']:
    assert 'licences.configcsa.com' not in public_text.read_text(encoding='utf8').lower(), public_text
manifest = json.loads((OUT/'integration.json').read_text(encoding='utf8'))
assert manifest['schema_version'] == 1
assert {row['id'] for row in manifest['products']} == set(editions)
for row in manifest['products']:
    edition = editions[row['id']]
    demo, check = row['demo'], row['sdk_check']
    assert demo['version'] == edition['demo'] and demo['tag'] == edition['tag']
    assert demo['setup_download_url'] == edition['demo_download_url']
    assert check['archive_url'] in edition['demo_assets'].values()
    assert re.fullmatch(r'[a-f0-9]{64}', check['archive_sha256'])
    assert check['source_url'] == BASE+'assets/'+check['source_file']
    assert re.fullmatch(r'[a-z0-9-]+\.(cpp|c)', check['source_file'])
    assert sha256((OUT/'assets'/check['source_file']).read_bytes()).hexdigest() == check['source_sha256']
    assert check['opens_input_context'] is check['starts_demo_timer'] is False
    assert check['app_architectures']==(['x86','x64'] if row['id']=='interception-v2' else ['x64'])
    for route in manifest['guides'].values():
        page = by_canonical[route]
        assert demo['setup_download_url'] in page.links
        assert check['source_url'] in page.links and check['archive_url'] in page.links
assert 'licences.configcsa.com' not in (OUT/'integration.json').read_text(encoding='utf8')
download=OUT/'downloads/first-sdk-checks.zip'
assert (OUT/'downloads/first-sdk-checks.zip.sha256').read_text(encoding='ascii').split()[0] == sha256(download.read_bytes()).hexdigest()
with ZipFile(download) as package:
    expected={'LICENSE','START-HERE.txt','sdk-checks.json','integration.json','dist/releases.json',
              'scripts/integration.py','scripts/test_first_sdk.py',
              *{'assets/'+row['sdk_check']['source_file'] for row in manifest['products']}}
    assert package.testzip() is None and set(package.namelist()) == expected
    assert package.read('integration.json') == (OUT/'integration.json').read_bytes()
    assert package.read('dist/releases.json') == (OUT/'releases.json').read_bytes()
    for name in expected - {'START-HERE.txt','integration.json','dist/releases.json'}:
        assert package.read(name) == (ROOT/name).read_bytes()
for route in manifest['guides'].values():
    assert '/downloads/first-sdk-checks.zip' in by_canonical[route].links
print('Validated',len(parsed),'HTML files, 60 entries, 10 workflows, metadata, JSON-LD, anchors and asset budgets')
