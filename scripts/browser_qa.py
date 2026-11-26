"""Optional visual/interaction QA with an existing Playwright/Chrome installation."""
from pathlib import Path
from datetime import datetime,timezone
from time import monotonic
from urllib.parse import urlsplit
from urllib.request import urlopen
import json,sys
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'.local/qa';out.mkdir(parents=True,exist_ok=True)
base=sys.argv[1].rstrip('/')+'/' if len(sys.argv)>1 else 'http://127.0.0.1:8778/'
with urlopen(base+'projects.json',timeout=15) as response:
    projects=json.load(response)['projects']
with urlopen(base+'releases.json',timeout=15) as response:
    editions=json.load(response)['editions']
with urlopen(base+'integration.json',timeout=15) as response:
    registry={(row['ecosystem'],row['name']):row['install_command'] for row in json.load(response)['sdk_registry']}
edition_routes={urlsplit(row['overview_url']).path.lstrip('/'):row for row in editions}
project_count=len(projects)
assert project_count
network_count=sum(row['category']=='networking' for row in projects)
network_no_driver_count=sum(row['category']=='networking' and row['start_without_adding_driver'] for row in projects)
no_driver_count=sum(row['start_without_adding_driver'] for row in projects)
audio_en='guides/titan-audio-link-first-run/'
audio_fr='fr/micro-virtuel-titan-audio-link/'
audio_download=edition_routes[audio_en]['demo_download_url']
errors=[];checks=[]
routes=['','fr/','guides/first-run/','fr/essayer-sans-pilote/','guides/choose-input/','guides/read-benchmarks/','about/evidence/',
        'guides/windows-input-release-compare/','guides/release-activation-help/',
        'guides/interception-v2-migration/','guides/windows-input-sdk-packages/','guides/installer-and-sdk/','fr/installeur-et-sdk/','fr/installer-sdk-windows/','guides/windows-input-sdk-java-php-ruby/','fr/sdk-java-php-ruby/',
        'guides/verify-windows-driver-package/','guides/vdevice-custom-hid-test/',
        'fr/activation-release/','fr/pilotes-entree-windows/',
        'fr/souris-usb-virtuelle-vdevice/','fr/remapper-deuxieme-clavier-autohotkey/',audio_fr,*edition_routes]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
    for width in [1440,390]:
        page=browser.new_page(viewport={'width':width,'height':960 if width==1440 else 844},color_scheme='light')
        page.on('pageerror',lambda e:errors.append(str(e)))
        for route in routes:
            response=page.goto(base+route,wait_until='networkidle');assert response.status==200,(route,response.status)
            assert page.locator('h1').count()==1,route
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),(route,width,'overflow')
            checks.append({'route':route,'width':width,'status':response.status,'title':page.title()})
            if route in edition_routes:
                nav=page.get_by_role('navigation',name='Project sections')
                repo=edition_routes[route]['repository'].rsplit('/',1)[1]
                assert nav.get_by_role('link').all_text_contents()==['First steps','Develop','Maintain'],route
                assert nav.get_by_role('link',name='Develop').get_attribute('href') == (
                    f'https://github.com/TitanCSA/sdk-packages/tree/main/projects/{repo}#readme'
                ),route
                nav.get_by_role('link',name='First steps').click()
                assert page.url.endswith('#first-steps') and page.locator('#first-steps').is_visible(),route
        page.goto(base,wait_until='networkidle')
        page.keyboard.press('Tab')
        assert page.locator('.skip').evaluate('link => link === document.activeElement')
        page.keyboard.press('Enter')
        assert page.locator('main').evaluate('main => main === document.activeElement')
        visible=lambda:page.locator('[data-project]:not([hidden])').count()
        assert visible()==project_count
        page.locator('#project-search').fill('browser')
        assert page.locator('#project-browser-control-sdk').is_visible() and 0<visible()<project_count
        page.locator('#project-search').fill('navigateur')
        assert page.locator('#project-browser-control-sdk').is_visible() and 0<visible()<project_count
        page.locator('#project-search').fill('zz_no_project_20261118')
        assert visible()==0 and page.locator('#empty-results').is_visible()
        page.locator('[data-reset]').click();assert visible()==project_count
        page.locator('#category-filter').select_option('networking');assert visible()==network_count
        page.locator('#no-driver-filter').check();assert visible()==network_no_driver_count
        page.locator('[data-reset]').click();page.locator('#no-driver-filter').check();assert visible()==no_driver_count
        page.locator('[data-reset]').click()
        preview=page.locator('#project-serial-device-simulator');assert preview.locator('.tag.preview').inner_text()=='Preview'
        preview.locator('summary').click();assert 'withheld' in preview.locator('details').inner_text()
        page.goto(base,wait_until='networkidle')
        page.screenshot(path=str(out/f'home-{width}.png'),full_page=False)
        if width==1440:
            theme=page.get_by_role('button',name='Dark mode',exact=True)
            assert theme.get_attribute('aria-pressed')=='false'
            theme.press('Space')
            assert page.locator('html').get_attribute('data-theme')=='dark'
            assert theme.get_attribute('aria-pressed')=='true'
            page.screenshot(path=str(out/'home-dark.png'),full_page=False)
        page.goto(base+'fr/',wait_until='domcontentloaded')
        assert visible()==project_count and f'{project_count} projets' in page.locator('#result-count').inner_text()
        page.locator('#project-search').fill('clavier')
        assert page.locator('#project-interceptor-keyboard-mouse').is_visible() and 0<visible()<project_count
        page.locator('[data-reset]').click();assert visible()==project_count
        page.locator('#no-driver-filter').check();assert visible()==no_driver_count
        page.locator('[data-reset]').click()
        page.screenshot(path=str(out/f'home-fr-{width}.png'),full_page=False)
        audio_card=page.locator('#project-titan-audio-link')
        audio_card.get_by_text('Premier essai',exact=True).click()
        assert audio_card.get_by_role('link',name='GitHub').get_attribute('href')=='https://github.com/titanfyre/Titan-Audio-Link#readme'
        audio_card.get_by_role('heading',level=3).get_by_role('link').click()
        assert page.url.endswith('/'+audio_fr)
        assert page.locator('.actions a.primary').get_attribute('href')==audio_download
        page.locator('header').get_by_role('link',name='English',exact=True).click()
        assert page.url.endswith('/'+audio_en)
        assert page.locator('.actions a.primary').get_attribute('href')==audio_download
        page.locator('header a[lang="fr"]').click()
        assert page.url.endswith('/'+audio_fr) and page.locator('html').get_attribute('lang')=='fr'
        page.close()
    page=browser.new_page(java_script_enabled=False,viewport={'width':390,'height':844})
    page.goto(base,wait_until='networkidle');assert page.locator('[data-project]:visible').count()==project_count
    assert not page.locator('[data-theme-toggle]').is_visible()
    page.locator('main a[href="/fr/"]').click()
    assert page.locator('html').get_attribute('lang')=='fr' and page.locator('[data-project]:visible').count()==project_count
    page.locator('#project-vdevice summary').click()
    assert 'Create device' in page.locator('#project-vdevice details').inner_text()
    page.locator('#project-vdevice h3 a').press('Enter')
    assert page.url.endswith('/projects/vdevice/')
    page.go_back(wait_until='domcontentloaded')
    page.locator('main a[lang="en"][href="/"]').click()
    page.locator('a[href="/guides/first-run/"]').first.click()
    assert page.url.endswith('/guides/first-run/') and page.locator('h1').inner_text().startswith('A useful first run')
    page.locator('main a[lang="fr"]').click()
    assert page.url.endswith('/fr/essayer-sans-pilote/') and page.locator('html').get_attribute('lang')=='fr'
    assert page.locator('main .guide-card:visible').count()==4
    page.locator('main details.first-run-more > summary').first.click()
    assert page.locator('main .guide-card:visible').count()==8
    page.locator('main .guide-card details > summary').first.click()
    image=page.locator('main .first-run-image').first
    image.scroll_into_view_if_needed()
    deadline=monotonic()+10
    while not image.evaluate('img => img.complete && img.naturalWidth > 0'):
        assert monotonic()<deadline, f'Screenshot did not load: {image.get_attribute("src")}'
        page.wait_for_timeout(125)
    page.goto(base+'fr/installer-sdk-windows/',wait_until='domcontentloaded')
    native_packages=page.locator('main details').filter(has=page.locator('summary').get_by_text('C/C++',exact=True))
    assert not native_packages.locator('table').is_visible()
    native_packages.locator('summary').click()
    assert native_packages.get_by_text(registry['nuget-native','Vdevice.Native'],exact=True).is_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), 'Registry table causes horizontal page scrolling'
    checks_help=page.locator('main details.first-run-more').filter(
        has=page.locator('a[href="/assets/python-interceptor-status.py"]'))
    assert not checks_help.locator('a[href="/assets/python-interceptor-status.py"]').is_visible()
    checks_help.locator('summary').click()
    assert checks_help.locator('a[href="/assets/python-interceptor-status.py"]').is_visible()
    assert checks_help.locator('a[href="/assets/dotnet-interceptor-status.cs"]').is_visible()
    assert checks_help.get_by_text('dotnet run --arch x64',exact=True).is_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), 'Example project causes horizontal page scrolling'
    page.goto(base+'fr/sdk-java-php-ruby/',wait_until='domcontentloaded')
    page.get_by_text('Voir les commandes pour Vdevice',exact=True).click()
    assert page.get_by_text(registry['packagist','titancsa/vdevice'],exact=True).is_visible()
    assert page.get_by_text(registry['rubygems','vdevice'],exact=True).is_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), 'SDK commands cause horizontal page scrolling'
    page.goto(base+'guides/windows-input-release-compare/',wait_until='domcontentloaded')
    contacts=page.locator('main a[href="/about/evidence/#release-contact"]')
    assert contacts.first.is_visible()
    assert page.locator('tbody a[href*="/releases/download/"]').count()==5
    assert 'What it does' in page.locator('thead').inner_text()
    assert page.get_by_role('table',name='Windows input driver editions').get_by_role('rowheader').count()==5
    for link in page.locator('tbody a[href*="/releases/download/"]').all():
        box=link.bounding_box()
        assert box and box['x']>=0 and box['x']+box['width']<=390, 'Contact link is clipped on mobile'
    assert page.locator('main details summary').is_visible()
    page.locator('main a[lang="fr"]').click()
    assert page.url.endswith('/fr/pilotes-entree-windows/') and page.locator('html').get_attribute('lang')=='fr'
    assert page.locator('main .guide-card a.button.primary[href*="/releases/download/"]').count()==5
    assert page.locator('main a[href="#contact-release"]').is_visible()
    first_trial=page.locator('main .guide-card details').first
    assert not first_trial.locator('p').is_visible()
    first_trial.locator('summary').click()
    assert first_trial.locator('p').is_visible()
    assert 'titancsa' in page.locator('main').inner_text()
    page.goto(base+'fr/installeur-et-sdk/',wait_until='domcontentloaded')
    page.locator('a[href="/fr/pilotes-entree-windows/#installer-interception-v2"]').click()
    v2_setup=page.locator('#installer-interception-v2')
    assert v2_setup.is_visible()
    assert v2_setup.locator('pre code').inner_text().endswith(' /install')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), 'V2 setup causes horizontal page scrolling'
    page.close();browser.close()
assert not errors,errors
report={'verified_utc':datetime.now(timezone.utc).isoformat(),'base':base,'pages':checks,'search_filter_reset':'passed desktop/mobile','preview_scope':'passed','dark_mode':'passed','javascript_disabled':f'all {project_count} entries and guides accessible','page_errors':errors,'limits':'Layout/interaction QA in existing headless Chrome; not product, driver, search indexing or real-user performance qualification'}
(out/'browser-qa.json').write_text(json.dumps(report,indent=2)+'\n')
print('Browser QA passed:',len(checks),'page views, search/filter/reset, preview limits, dark mode and no-JavaScript access')
