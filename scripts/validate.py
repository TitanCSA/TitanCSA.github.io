from zipfile import ZipFile
from pathlib import Path
from html.parser import HTMLParser
from hashlib import sha256
from struct import unpack
from urllib.parse import urlparse,unquote
import json,re,xml.etree.ElementTree as ET
from registry import runtime_reports

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

data=json.loads((ROOT/'projects.json').read_text(encoding='utf8'));projects=data['projects']
localized=json.loads((OUT/'projects.json').read_text(encoding='utf8'))
assert [p['url'] for p in localized['projects']] == [p['url'] for p in projects]
assert all(p['plain_purpose_fr'] and p['plain_first_step_fr'] for p in localized['projects'])
assert projects and len(projects)==len({p['url'].lower() for p in projects})
categories={p['category'] for p in projects}
for p in projects:
    assert p['name'] and p['description'] and p['first_step'] and isinstance(p['start_without_adding_driver'],bool)
    assert p['kind'] in ['Application','Driver SDK','SDK sources','Preview','Dataset']
    assert p['url'].startswith(('https://github.com/TitanCSA/','https://github.com/titanfyre/'))
for name in ['Serial-Device-Simulator','Virtual-COM-Workbench','File-Trace-Studio','Titan-File-Filter','RegistryGuard']:
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
for route in ('','fr/'):
    landing=by_canonical[BASE+route]
    project_list=next(schema for schema in landing.schemas if schema['@type']=='ItemList')
    assert project_list['numberOfItems']==len(projects)
    assert [item['url'] for item in project_list['itemListElement']]==[p['url'] for p in projects]
    html=(OUT/route/'index.html').read_text(encoding='utf8')
    assert html.count('data-project data-category=')==len(projects)
    assert html.count(' data-project-group ')==len(categories)
    assert {p['url'] for p in projects} <= set(landing.links)
    assert BASE+'rss.xml' in landing.links and '/rss.xml' in landing.links
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
audio_routes=('guides/titan-audio-link-first-run/','fr/micro-virtuel-titan-audio-link/')
audio_catalogue=json.loads((OUT/'releases.json').read_text(encoding='utf8'))
audio=next(edition for edition in audio_catalogue['editions'] if edition['slug']=='titan-audio-link')
for path, language, alternate in zip(audio_routes, ('en','fr'), reversed(audio_routes)):
    page=by_canonical[BASE+path]
    assert page.language==language and audio['demo_download_url'] in page.links
    assert '/'+alternate in page.links and '/about/evidence/#release-contact' in page.links
assert '/'+audio_routes[1] in by_canonical[BASE+'fr/'].links
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
xml_sitemap_urls = [url.findtext('{*}loc') for url in tree.getroot()]
assert set(xml_sitemap_urls) == {
    page.canonical for path,page in parsed.items() if path.name!='404.html'
}
assert len(xml_sitemap_urls)==len(set(xml_sitemap_urls))
assert (OUT/'sitemap.txt').read_text(encoding='utf8').splitlines()==xml_sitemap_urls
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
assert {row['slug'] for row in editions.values() if '/projects/' in row['overview_url']} == {path.parent.name for path in project_pages}
company_check=json.loads((OUT/'assets/company-driver-package-checks-2026-11-26.json').read_text(encoding='utf8'))
assert len({entry['project'] for entry in company_check['editions']})==len(company_check['editions'])==4
for entry in company_check['editions']:
    commercial=editions[entry['project']]['commercial']
    if entry['package_version']==commercial['package_version']:
        assert entry['driver_version']==commercial['driver_version']
    later = entry.get('later_delivery')
    if later:
        assert later['company_archive_sha256'] != entry['company_archive_sha256']
        assert later['publisher_store_manifest_agrees'] is True
    for tested_archive in ((entry, later) if later else (entry,)):
        assert tested_archive['signed_driver_packages']
        for package in tested_archive['signed_driver_packages']:
            assert package['inf_catalog_membership'] is package['kernel_catalog_membership'] is True
        reports = [tested_archive['windows_11_vm']]
        if qualified := tested_archive.get('windows_11_vm_memory_integrity'):
            assert qualified['memory_integrity_running'] is True
            assert qualified['memory_integrity_running_after_install'] is True
            assert qualified['memory_integrity_running_after_uninstall'] is True
            reports.append(qualified)
        for vm in reports:
            assert vm['secure_boot'] is True and vm['paid_key_used'] is False
            assert vm['restart_after_install_verified'] is vm['restart_after_uninstall_verified'] is True
            assert vm['install_exit_code'] == vm['uninstall_exit_code'] == 0
            assert vm['driver_service_present_after_uninstall'] is False and vm['windows_error_after_uninstall'] == 2
            running_packages = {
                package['inf'].lower() for package in tested_archive['signed_driver_packages']
                if package['kernel_sha256'] == vm['running_kernel_sha256']
            }
            assert running_packages and set(vm['installed_inf_names']) == running_packages
keyboard_mouse_evidence = next(entry for entry in company_check['editions'] if entry['project']=='interceptor-keyboard-mouse')
assert 'windows_11_vm_memory_integrity' in keyboard_mouse_evidence['later_delivery']
for edition in editions.values():
    overview=by_canonical[edition['overview_url']]
    repo=edition['repository'].rsplit('/',1)[1]
    sections={
        '#first-steps',
        f'https://github.com/TitanCSA/sdk-packages/tree/main/projects/{repo}#readme',
        'https://github.com/TitanCSA/sdk-packages/blob/main/CONTRIBUTING.md',
    }
    assert sections <= set(overview.links),edition['slug']
comparison=parsed[(OUT/'guides/windows-input-release-compare/index.html').resolve()]
french_comparison=by_canonical[BASE+'fr/pilotes-entree-windows/']
assert comparison.alternates=={'en':comparison.canonical,'fr':french_comparison.canonical}
assert editions['vdevice']['demo_assets']['examples'] in french_comparison.links
mouse_path='assets/vdevice-mouse-panel-2026-11-25.json'
mouse_panel=json.loads((OUT/mouse_path).read_text(encoding='utf8'))
assert mouse_panel['environment']['secure_boot'] is True and mouse_panel['driver']['signature_status']=='Valid'
assert mouse_panel['results']['healthy_mouse_present_after_creation'] is True
assert mouse_panel['results']['healthy_mouse_present_after_disconnect'] is False
assert mouse_panel['results']['relative_motion_requested']=={'x':32,'y':0}
if mouse_panel['demo_version']==editions['vdevice']['demo']:
    assert mouse_panel['examples']['archive_url']==editions['vdevice']['demo_assets']['examples']
    assert mouse_panel['examples']['archive_sha256']==editions['vdevice']['demo_asset_sha256']['examples']
later=mouse_panel['later_validation']
if later['demo_version']==editions['vdevice']['demo']:
    assert later['examples']['archive_url']==editions['vdevice']['demo_assets']['examples']
    assert later['examples']['archive_sha256']==editions['vdevice']['demo_asset_sha256']['examples']
    assert later['environment']['secure_boot'] is True
    assert later['results']['healthy_mouse_present_after_creation'] is True
    assert later['results']['healthy_mouse_present_after_disconnect'] is False
    assert later['results']['relative_motion_requested']=={'x':32,'y':0}
for route in ('guides/vdevice-virtual-usb-mouse/', 'fr/souris-usb-virtuelle-vdevice/'):
    assert '/'+mouse_path in by_canonical[BASE+route].links
reference=(OUT/'llms.txt').read_text(encoding='utf8')
assert BASE+'assets/company-driver-package-checks-2026-11-26.json' in reference
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
    app,=[item for item in page.schemas if item.get('@type')=='SoftwareApplication']
    assert app['softwareVersion']==edition['commercial']['package_version']
    assert all(re.fullmatch(r'\d+\.\d+\.\d+\.\d+', value) for value in edition['commercial'].values())
    assert 'offers' not in app
for public_text in [*OUT.rglob('*.html'), OUT/'llms.txt', OUT/'releases.json', OUT/'projects.json']:
    assert 'licences.configcsa.com' not in public_text.read_text(encoding='utf8').lower(), public_text
manifest = json.loads((OUT/'integration.json').read_text(encoding='utf8'))
assert manifest['schema_version'] == 1
schema=json.loads((OUT/'integration.schema.json').read_text(encoding='utf8'))
assert manifest['$schema']==schema['$id']==BASE+'integration.schema.json'
assert schema['properties']['schema_version']['const']==manifest['schema_version']
preview = json.loads((OUT/'assets/demo-install-verification-2026-11-25.json').read_text(encoding='utf8'))['setup_preview']
assert preview['preview_exit_code'] == 0 and preview['secure_boot'] is True
assert sha256((OUT/preview['screenshot_url'].removeprefix(BASE)).read_bytes()).hexdigest() == preview['screenshot_sha256']
rows = manifest['sdk_registry']
other_registries={'maven','packagist','rubygems'}
language_guide=by_canonical[BASE+'guides/windows-input-sdk-java-php-ruby/']
language_guide_fr=by_canonical[BASE+'fr/sdk-java-php-ruby/']
assert {row['ecosystem'] for row in rows} == {'npm','pypi','nuget-managed','nuget-native','powershell'} | other_registries
runtime_results={}
clean_results={}
for runtime_path, runtime_proof in runtime_reports(OUT/'assets'):
    for record in runtime_proof.get('reproduced_examples', []):
        assert sha256((OUT/'assets'/record['file']).read_bytes()).hexdigest()==record['sha256']
    checks=runtime_proof['checks']
    observed={(item['ecosystem'],item['name'],item['version']):(runtime_path,item) for item in checks}
    assert len(observed)==len(checks)
    runtime_results.update(observed)
    clean=runtime_proof.get('without_driver', {}).get('checks', [])
    checked_clean={(item['ecosystem'],item['name'],item['version']):item for item in clean}
    assert len(checked_clean)==len(clean)
    clean_results.update(checked_clean)
    if runtime_proof['environment'].get('memory_integrity_running'):
        assert runtime_proof['environment']['secure_boot'] is True
        for item in checks:
            assert item['before']==item['after']=={'windows_error':2}
            assert item['install_exit']==item['uninstall_exit']==0
            assert item['result']=={'installed':True,'active':False,'trial_state':0}
installed_driver_checks=json.loads((OUT/'assets/demo-install-verification-2026-11-25.json').read_text(encoding='utf8'))['editions']
for row in rows:
    if row['ecosystem'] in other_registries:
        assert row['package_url'] in language_guide.links and row['package_url'] in language_guide_fr.links
        assert row['first_check']['sdk_type']
        if clean := clean_results.get((row['ecosystem'],row['name'],row['version'])):
            assert clean['edition']==row['edition']
            expected = ({'windows_error':2} if row['first_check']['requires_installed_driver']
                        else {'valid':True,'keyboard':True,'mouse':False})
            assert clean['result']==expected
            if clean.get('public_consumer_install_verified'):
                assert clean['package_sha256']==row['verified_archive']['sha256']
    else:
        assert row['package_url'] in packages_en.links and row['package_url'] in packages_fr.links
    assert row['install_includes_driver_or_application'] is False
    assert row['first_check']['opens_input_context'] is False
    assert isinstance(row['first_check']['requires_installed_driver'], bool)
    assert isinstance(row['first_check']['requires_application'], bool)
    if example := row['first_check'].get('source_url'):
        assert example.startswith(BASE+'assets/')
        example_file=OUT/example.removeprefix(BASE)
        assert sha256(example_file.read_bytes()).hexdigest()==row['first_check']['source_sha256']
    if evidence := row.get('lab_verification'):
        runtime_path,observed=runtime_results[(row['ecosystem'],row['name'],row['version'])]
        assert evidence=={'source_url':BASE+runtime_path,'driver_version':observed['driver_version'],'runtime':observed['runtime']}
        assert observed['edition']==row['edition'] and observed['demo_timer_started'] is False
        if 'verified_archive' in row:
            assert observed['package_sha256']==row['verified_archive']['sha256']
        if row['ecosystem']=='packagist':
            assert observed['package_source_reference']==row['source_reference']
            assert re.fullmatch(r'[a-f0-9]{64}', observed['inspected_source_archive_sha256'])
        installation=installed_driver_checks[row['edition']]
        assert re.fullmatch(r'[a-f0-9]{64}', observed['driver_sha256'])
        if observed['driver_version']==installation['version']:
            assert observed['driver_sha256']==installation['installed_kernel_sha256']
            if 'setup_sha256' in observed:
                assert observed['setup_sha256']==installation['installer_sha256']
    if archive := row.get('verified_archive'):
        assert re.fullmatch(r'[a-f0-9]{64}', archive['sha256'])
        if row['ecosystem'].startswith('nuget-'):
            assert urlparse(archive['url']).netloc == 'api.nuget.org'
        if row['ecosystem'] == 'npm':
            assert urlparse(archive['url']).netloc == 'registry.npmjs.org'
        if row['ecosystem'] == 'maven':
            assert urlparse(archive['url']).netloc == 'repo.maven.apache.org'
            assert row['dependency_xml'].startswith('<dependency>')
        if row['ecosystem'] == 'rubygems':
            assert urlparse(archive['url']).netloc == 'rubygems.org'
assert {row['id'] for row in manifest['products']} == set(editions)
for row in manifest['products']:
    edition = editions[row['id']]
    demo, check = row['demo'], row['sdk_check']
    assert demo['version'] == edition['demo'] and demo['tag'] == edition['tag']
    assert demo['setup_download_url'] == edition['demo_download_url']
    assert set(demo['assets']) == set(edition['demo_assets']) == set(edition['demo_asset_sha256'])
    for role, asset in demo['assets'].items():
        assert asset == {'url':edition['demo_assets'][role],'sha256':edition['demo_asset_sha256'][role]}
        assert re.fullmatch(r'[a-f0-9]{64}', asset['sha256'])
    assert {'url':demo['setup_download_url'],'sha256':demo['setup_download_sha256']} in demo['assets'].values()
    assert {'url':check['archive_url'],'sha256':check['archive_sha256']} in demo['assets'].values()
    if console := demo.get('console_setup'):
        role = console['asset_role']
        assert role in demo['assets']
        assert console['requires_administrator'] and console['restart_before_check']
        assert console['install_arguments']==['/install'] and console['uninstall_arguments']==['/uninstall']
        assert console['success_exit_codes']==[0,3010] and console['restart_required_exit_code']==3010
        evidence = OUT/console['evidence_url'].removeprefix(BASE)
        assert console['evidence_url'].startswith(BASE) and evidence.is_file()
        if role == 'console_installer':
            assert console['archive_member'] is None
            assert console['installer_sha256']==demo['assets'][role]['sha256']
        else:
            member = console['archive_member']
            assert member and member.endswith('.exe') and not member.startswith('/')
            assert all(part not in ('', '.', '..') and not any(char in part for char in '\\:') for part in member.split('/'))
            archive_proof = json.loads(evidence.read_text(encoding='utf8'))['demo_archive']
            assert archive_proof['sha256']==demo['assets'][role]['sha256']
            assert archive_proof['bundled_installer_sha256']==console['installer_sha256']
            assert member==(archive_proof.get('bundled_installer_member') or demo['setup_member'])
    if evidence := demo.get('read_only_install_verification'):
        evidence_file = OUT/evidence['url'].removeprefix(BASE)
        proof = json.loads(evidence_file.read_text(encoding='utf8'))['editions'][row['id']]
        assert evidence['edition'] == row['id'] and proof['version'] == demo['version']
        assert proof['sdk_archive_sha256'] == check['archive_sha256']
        assert proof['environment']['secure_boot'] is True and proof['sample_exit_code'] == 0
        assert proof['catalogue_signature'] == 'Valid' and proof['installer_exit_code'] in (0, 3010)
        assert demo['assets']['console_installer'] == {
            'url': proof['installer_url'], 'sha256': proof['installer_sha256']}
        lifecycle=proof['reboot_and_uninstall']
        assert lifecycle['restart_after_install_verified'] is lifecycle['restart_after_uninstall_verified'] is True
        assert lifecycle['status_exit_before_install']==lifecycle['status_exit_after_uninstall_and_restart']==2
        assert lifecycle['status_exit_after_install_and_restart']==0
        assert lifecycle['uninstallation_exit'] in (0,3010)
        assert lifecycle['kernel_service_registered_after_uninstall'] is False
    if live := demo.get('live_inventory_verification'):
        proof = json.loads((OUT/live['url'].removeprefix(BASE)).read_text(encoding='utf8'))
        assert proof['edition']==row['id'] and proof['demo_version']==demo['version']
        assert proof['demo_archive']['sha256']==demo['setup_download_sha256']
        assert live['app_architectures']==check['app_architectures']
        assert live['opens_input_context'] is proof['sample']['opens_input_context'] is True
        assert check['opens_input_context'] is False
        assert live['sample_source_url']==proof['sample']['source_url']
        assert sha256((OUT/live['sample_source_url'].removeprefix(BASE)).read_bytes()).hexdigest()==proof['sample']['source_sha256']
        assert proof['environment']['secure_boot'] is True and proof['driver']['signature']=='Valid'
        assert proof['driver']['kernel_service_registered_after_uninstall'] is False
        for arch in live['app_architectures']:
            phase=proof['sample']['architectures'][arch]
            assert phase['before_installation_exit_code']==phase['after_uninstall_and_reboot_exit_code']==1
            assert phase['after_installation_and_reboot']['exit_code']==0
    if installer_evidence := demo.get('installer_verification_url'):
        proof=json.loads((OUT/installer_evidence.removeprefix(BASE)).read_text(encoding='utf8'))
        assert proof['project']==row['id']
        verified=proof['versions']['demo']
        assert verified['driver_version']==verified['package_version']==demo['version']
        assert verified['signed_driver_archive_sha256']==demo['assets']['driver']['sha256']
        assert verified['public_notes_url']==demo['notes_url']
        assert {record['windows_build'] for record in verified['installer_qualification']}=={19045,26100}
        installers = {record['installer']: record['installer_sha256']
                      for record in verified['installer_qualification']}
        assert installers == {'graphical': demo['setup_download_sha256'],
                              'console': demo['assets']['console_installer']['sha256']}
    if switch_evidence := demo.get('mouse_driver_switch_verification_url'):
        report = json.loads((OUT/switch_evidence.removeprefix(BASE)).read_text(encoding='utf8'))
        record = report['editions'][row['id']]
        assert report['environment'] == {'windows_build': 26100, 'architecture': 'x64', 'secure_boot': True}
        assert record['tag'] == demo['tag'] and record['sdk_sha256'] == check['archive_sha256']
        assert record['console_installer_sha256'] == demo['assets']['console_installer']['sha256']
        assert record['restore_original_windows_code'] in (0,3010)
        assert record['restore_interceptor_windows_code'] in (0,3010)
        observed = record['observed_bindings']
        assert [point['target']['mode'] for point in observed] == [
            'windows_inbox', 'interceptor', 'windows_inbox', 'interceptor']
        assert observed[1]['control'] == observed[2]['control'] == observed[3]['control']
    if release_evidence := row.get('commercial_install_verification'):
        proof=json.loads((OUT/release_evidence['url'].removeprefix(BASE)).read_text(encoding='utf8'))
        assert proof['project']==row['id']
        verified=proof['versions']['release']
        assert {key:verified[key] for key in ('package_version','driver_version')}==edition['commercial']
        assert verified['private_delivery']['configured_archive_sha256']==verified['company_archive_sha256']
        assert verified['private_delivery']['anonymous_http_status'] in (401,403,404)
        assert {record['windows_build'] for record in verified['installer_qualification']}=={19045,26100}
        protection=verified['secure_boot_memory_integrity_lab']
        assert protection['secure_boot'] is protection['memory_integrity_running'] is protection['activation_interface_ready'] is True
        assert protection['key_used'] is False
    assert check['archive_url'] in edition['demo_assets'].values()
    assert re.fullmatch(r'[a-f0-9]{64}', check['archive_sha256'])
    assert check['source_url'] == BASE+'assets/'+check['source_file']
    assert re.fullmatch(r'[a-z0-9-]+\.(cpp|c)', check['source_file'])
    assert sha256((OUT/'assets'/check['source_file']).read_bytes()).hexdigest() == check['source_sha256']
    assert check['opens_input_context'] is check['starts_demo_timer'] is False
    assert check['header_file'].endswith('.h')
    expected_definitions=['UNICODE','_UNICODE','NOMINMAX'] if check['implementation_file'] else []
    assert check['compile_definitions']==expected_definitions
    if check['implementation_file']:
        assert not check['runtime_file_by_architecture']
    else:
        assert set(check['runtime_file_by_architecture']) == set(check['app_architectures'])
        assert set(check['import_library_by_architecture']) == set(check['app_architectures'])
    assert check['app_architectures']==(['x86','x64'] if row['id']=='interception-v2' else ['x64'])
    for route in manifest['guides'].values():
        page = by_canonical[route]
        assert demo['setup_download_url'] in page.links
        assert check['source_url'] in page.links and check['archive_url'] in page.links
assert 'licences.configcsa.com' not in (OUT/'integration.json').read_text(encoding='utf8')
apps = manifest['applications']
assert len(apps) == len({app['id'] for app in apps}) == len({app['source'] for app in apps})
assert set(manifest['first_run_guides']) == {'en','fr'}
for app in apps:
    assert re.fullmatch(r'https://github.com/(TitanCSA|titanfyre)/[A-Za-z0-9._-]+', app['source'])
    assert re.fullmatch(r'v[0-9.]+', app['tag']) and re.fullmatch(r'[A-Za-z0-9._-]+\.zip', app['zip'])
    assert app['download_url'] == app['source']+'/releases/download/'+app['tag']+'/'+app['zip']
    for key in ('sha256','executable_sha256'):
        assert re.fullmatch(r'[a-f0-9]{64}', app[key])
    assert set(app['purpose']) == set(app['steps']) == set(app['expected']) == {'en','fr'}
    assert app['needs_input_driver_for_first_run'] is False and app['test']['exit_code'] == 0
    for guide in manifest['first_run_guides'].values():
        page = by_canonical[guide]
        assert app['download_url'] in page.links
        if 'picture' in app:
            picture = app['picture']
            assert picture['path'] in page.links
            image = (OUT/picture['path'].lstrip('/')).read_bytes()
            assert unpack('>II', image[16:24]) == (picture['width'], picture['height'])
        if 'source_url' in app['test']:
            assert app['test']['source_url'].startswith(BASE+'assets/')
            relative = app['test']['source_url'].removeprefix(BASE)
            assert '/'+relative in page.links
            assert sha256((OUT/relative).read_bytes()).hexdigest() == app['test']['source_sha256']
download=OUT/'downloads/first-sdk-checks.zip'
assert (OUT/'downloads/first-sdk-checks.zip.sha256').read_text(encoding='ascii').split()[0] == sha256(download.read_bytes()).hexdigest()
with ZipFile(download) as package:
    expected={'LICENSE','START-HERE.txt','sdk-checks.json','integration.json','integration.schema.json','dist/releases.json',
              'scripts/integration.py','scripts/test_first_sdk.py',
              *{'assets/'+row['sdk_check']['source_file'] for row in manifest['products']}}
    assert package.testzip() is None and set(package.namelist()) == expected
    bundled_metadata={'integration.json':OUT/'integration.json',
                      'integration.schema.json':OUT/'integration.schema.json',
                      'dist/releases.json':OUT/'releases.json'}
    for name in expected - {'START-HERE.txt'}:
        original=bundled_metadata.get(name,ROOT/name).read_bytes()
        if not name.startswith('assets/'):
            original=original.replace(b"\r\n", b"\n")
        assert package.read(name) == original, name
for route in manifest['guides'].values():
    assert '/downloads/first-sdk-checks.zip' in by_canonical[route].links
print('Validated',len(parsed),f'HTML files, {len(projects)} entries, {len(categories)} workflows, metadata, JSON-LD, anchors and asset budgets')
