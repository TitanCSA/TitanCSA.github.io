"""Optional visual/interaction QA with an existing Playwright/Chrome installation."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'.local/qa';out.mkdir(parents=True,exist_ok=True)
base=sys.argv[1].rstrip('/')+'/' if len(sys.argv)>1 else 'http://127.0.0.1:8778/'
errors=[];checks=[]
routes=['','guides/first-run/','guides/choose-input/','guides/read-benchmarks/','about/evidence/',
        'guides/windows-input-release-compare/','guides/release-activation-help/',
        'guides/interception-v2-migration/','guides/windows-input-sdk-packages/','fr/installer-sdk-windows/','guides/windows-input-sdk-java-php-ruby/',
        'guides/verify-windows-driver-package/','guides/vdevice-custom-hid-test/',
        'fr/activation-release/','fr/pilotes-entree-windows/',
        'fr/souris-usb-virtuelle-vdevice/','fr/remapper-deuxieme-clavier-autohotkey/']
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
        page.goto(base,wait_until='networkidle')
        visible=lambda:page.locator('[data-project]:not([hidden])').count()
        assert visible()==60
        page.locator('#project-search').fill('browser')
        assert page.locator('#project-browser-control-sdk').is_visible() and 0<visible()<60
        page.locator('#project-search').fill('zz_no_project_20261118')
        assert visible()==0 and page.locator('#empty-results').is_visible()
        page.locator('[data-reset]').click();assert visible()==60
        page.locator('#category-filter').select_option('networking');assert visible()==7
        page.locator('#no-driver-filter').check();assert visible()==0
        page.locator('[data-reset]').click();page.locator('#no-driver-filter').check();assert visible()==6
        page.locator('[data-reset]').click()
        preview=page.locator('#project-serial-device-simulator');assert preview.locator('.tag.preview').inner_text()=='Preview'
        preview.locator('summary').click();assert 'withheld' in preview.locator('details').inner_text()
        page.goto(base,wait_until='networkidle')
        page.screenshot(path=str(out/f'home-{width}.png'),full_page=False)
        if width==1440:
            page.locator('[data-theme-toggle]').click();assert page.locator('html').get_attribute('data-theme')=='dark'
            page.screenshot(path=str(out/'home-dark.png'),full_page=False)
        page.close()
    page=browser.new_page(java_script_enabled=False,viewport={'width':390,'height':844})
    page.goto(base,wait_until='networkidle');assert page.locator('[data-project]:visible').count()==60
    page.locator('a[href="/guides/first-run/"]').first.click()
    assert page.url.endswith('/guides/first-run/') and page.locator('h1').inner_text().startswith('A useful first run')
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
    assert page.locator('main .guide-card a[href*="/releases/download/"]').count()==5
    assert page.locator('main a[href="#contact-release"]').is_visible()
    assert 'titancsa' in page.locator('main').inner_text()
    page.close();browser.close()
assert not errors,errors
report={'verified_utc':datetime.now(timezone.utc).isoformat(),'base':base,'pages':checks,'search_filter_reset':'passed desktop/mobile','preview_scope':'passed','dark_mode':'passed','javascript_disabled':'all 60 entries and guides accessible','page_errors':errors,'limits':'Layout/interaction QA in existing headless Chrome; not product, driver, search indexing or real-user performance qualification'}
(out/'browser-qa.json').write_text(json.dumps(report,indent=2)+'\n')
print('Browser QA passed:',len(checks),'page views, search/filter/reset, preview limits, dark mode and no-JavaScript access')
