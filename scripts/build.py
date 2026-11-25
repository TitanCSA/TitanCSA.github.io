"""Build a public, dependency-free static catalogue from curated project evidence."""
from pathlib import Path
from html import escape
from xml.etree import ElementTree as ET
import json,re,shutil
from integration import app_cards, make_manifest, sdk_rows, write_starter
from catalogue import catalogue_sections
from registry import registry_catalogue, registry_tables, secondary_registry_rows

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist';BASE='https://titancsa.github.io/'
data=json.loads((ROOT/'projects.json').read_text(encoding='utf8'));projects=data['projects'];checked=data['checked']
french_copy=json.loads((ROOT/'projects.fr.json').read_text(encoding='utf8'))
assert set(french_copy['projects']) == {p['name'] for p in projects}
assert set(french_copy['categories']) == {p['category'] for p in projects}
verification_file=ROOT/'site-verification.json'
verification=json.loads(verification_file.read_text())['google_site_verification'] if verification_file.exists() else None
if verification:assert re.fullmatch(r'[A-Za-z0-9_=-]{20,200}',verification)
indexnow_key=json.loads(verification_file.read_text()).get('indexnow_key') if verification_file.exists() else None
if indexnow_key:assert re.fullmatch(r'[a-f0-9]{32}',indexnow_key)
featured={
    'interceptor':("Interceptor","Interceptor | Windows keyboard, mouse and gamepad filter","Use a single C++17 SDK to observe and transform supported physical keyboard, mouse and controller input on Windows."),
    'interceptor-keyboard-mouse':("Interceptor-Keyboard-Mouse","Interceptor Keyboard & Mouse | Per-device keyboard and mouse remapping on Windows","Distinguish physical keyboards and mice and remap input from selected devices with a Windows filter and C++17 SDK."),
    'interceptor-gamepad-controller':("Interceptor-Gamepad-Controller","Interceptor Gamepad & Controller | Windows controller remapping for physical gamepads","Inspect and adjust input from compatible Windows gamepads with a controller-focused C++17 SDK, including stick curves, deadzones and button changes."),
    'vdevice':("Vdevice","Vdevice | Virtual USB keyboard, mouse and gamepad SDK for Windows","Create virtual USB devices on Windows with a C++17 SDK for descriptors, endpoints, reports and control data."),
    'interception-v2':("Interception-V2","Interception V2 | Windows keyboard and mouse driver for the original Interception C API","Evaluate legacy applications using the original Interception C SDK against TitanCSA’s independently maintained keyboard and mouse driver."),
}
featured_paths={repo:f'/projects/{slug}/' for slug,(repo,_,_) in featured.items()}
featured_paths['Titan-Audio-Link']='/guides/titan-audio-link-first-run/'
featured_date='2026-11-23'
contact_path='/about/evidence/#release-contact'
release_data=json.loads((ROOT/'releases.json').read_text(encoding='utf8'))
release_date=release_data['reviewed']
commercial_checked=release_data['commercial_checked']
editions={}
for edition in release_data['editions']:
    slug=edition['slug']
    if slug in featured:
        repo,title,_=featured[slug]
        repo_url=f'https://github.com/TitanCSA/{repo}'
        overview=f'{BASE}projects/{slug}/'
    elif slug=='titan-audio-link':
        title='Titan Audio Link'
        repo_url='https://github.com/titanfyre/Titan-Audio-Link'
        overview=f'{BASE}guides/titan-audio-link-first-run/'
    else:
        raise ValueError(f'Unknown edition {slug}')
    assets={role:f'{repo_url}/releases/download/{edition["tag"]}/{filename}' for role,filename in edition['demo_files'].items()}
    primary=assets.get('installer') or assets['archive']
    editions[slug]={
        **edition,
        'name':title.split(' | ',1)[0],
        'repository':repo_url,
        'demo_url':f'{repo_url}/releases/tag/{edition["tag"]}',
        'demo_download_url':primary,
        'demo_assets':assets,
        'overview_url':overview,
        'release_contact':{'platform':'Discord','username':'titancsa','instructions_url':BASE.rstrip('/')+contact_path},
    }
assert set(editions)==set(featured)|{'titan-audio-link'} and len(editions)==len(release_data['editions'])
input_editions={slug:editions[slug] for slug in featured}
integration=make_manifest(BASE,editions)
integration['sdk_registry']=registry_catalogue(integration,BASE)
assert projects and len({p['url'].lower() for p in projects})==len(projects)
assert all(p['url'].startswith(('https://github.com/TitanCSA/','https://github.com/titanfyre/')) for p in projects)
OUT.mkdir(exist_ok=True)
for folder in ['src','assets']:
    target=OUT/('assets' if folder=='src' else folder);target.mkdir(exist_ok=True)
    for p in (ROOT/folder).iterdir():
        if p.is_file():shutil.copyfile(p,target/p.name)
app_sections={row['repository'].split('/')[-1]:row['id'] for row in integration['applications']}
replacements={'PROJECT_COUNT':str(len(projects)), 'CHECKED_DATE':checked}
for french in (False, True):
    replacements.update(catalogue_sections(projects, french_copy, featured_paths, app_sections, french=french))
replacements['RELEASE_REVIEW_DATE']=release_date
replacements['INSTALLER_SDK_ROWS_EN']=sdk_rows(integration)
replacements['INSTALLER_SDK_ROWS_FR']=sdk_rows(integration,french=True)
replacements['REGISTRY_TABLES_EN']=registry_tables(integration['sdk_registry'])
replacements['REGISTRY_TABLES_FR']=registry_tables(integration['sdk_registry'],french=True)
browser_package=next(row for row in integration['sdk_registry'] if row['name']=='browser-control-sdk')
replacements['BROWSER_PYPI_URL']=escape(browser_package['package_url'],quote=True)
replacements['BROWSER_PYPI_INSTALL']=escape(browser_package['install_command'])
managed_package=next(row for row in integration['sdk_registry'] if row['name']=='Interceptor.MultiLang')
replacements['INTERCEPTOR_MANAGED_INSTALL']=escape(managed_package['install_command'])
for lang in ('en', 'fr'):
    replacements[f'APP_CARDS_{lang.upper()}']=app_cards(integration, lang)
    replacements[f'APP_MORE_{lang.upper()}']=app_cards(integration, lang, more=True)
replacements['COMMERCIAL_CHECK_DATE']=commercial_checked
replacements['SUPPORT_ISSUE_FORMS']=''.join(
    f'<li><a href="{e["repository"]}/issues/new?template=installation-activation.yml">{escape(e["name"])}</a></li>'
    for e in input_editions.values()
)
replacements['OTHER_SDK_REGISTRY_ROWS']=secondary_registry_rows(integration['sdk_registry'],input_editions)
for row in integration['sdk_registry']:
    if row['edition']=='vdevice' and row['ecosystem'] in ('maven','packagist','rubygems'):
        key='VDEVICE_'+row['ecosystem'].upper()+'_COMMAND'
        replacements[key]=escape(row.get('dependency_xml',row['install_command']))
    if row['edition']=='interceptor' and row['ecosystem']=='maven':
        replacements['COMBINED_JAVA_TYPE']=escape(row['first_check']['sdk_type'])
for slug, edition in editions.items():
    key=slug.upper().replace('-','_')
    replacements[f'{key}_DEMO_URL']=escape(edition['demo_download_url'],quote=True)
    replacements[f'{key}_DEMO_VERSION']=escape(edition['demo'])
    for role, url in edition['demo_assets'].items():
        replacements[f'{key}_{role.upper()}_URL']=escape(url,quote=True)
plain_by_slug={p['url'].split('#')[0].rsplit('/',1)[-1].lower():p['plain_purpose'] for p in projects}
replacements['RELEASE_COMPARISON_ROWS']='\n'.join(
    f'<tr role="row"><th scope="row" role="rowheader"><a href="{e["overview_url"]}">{escape(e["name"])}</a></th>'
    f'<td role="cell">{escape(plain_by_slug[e["slug"]])}</td>'
    f'<td role="cell"><a href="{e["demo_download_url"]}">Download {escape(e["name"])} demo {e["demo"]}</a><br>'
    f'<a href="{e["demo_url"]}">Release notes</a></td></tr>'
    for e in input_editions.values()
)
pages={
 '':('TitanCSA — Windows tools, device SDKs and practical guides','Find Windows input tools, virtual devices, diagnostics and SDKs by workflow. Clear first-run guides, project licences, public evidence and known limits.','index.html'),
 'fr/':('TitanCSA — Outils Windows, pilotes et SDK','Trouve ton outil Windows par usage. Chaque fiche explique son rôle et le premier essai, avec les liens vers les démos et les SDK.','index-fr.html'),
 'guides/first-run/':('A first Windows tool run without an input driver — TitanCSA','Start with Browser Control SDK, read-only Driver Readiness Inspector or offline fixture validation. Prerequisites, exact steps and expected results.','guides/first-run.html'),
 'fr/essayer-sans-pilote/':('Essayer un outil Windows sans installer de pilote — TitanCSA','Huit outils à essayer avec des étapes courtes, des captures et le résultat à vérifier.','guides/first-run-fr.html'),
 'guides/choose-input/':('Input interception or virtual devices? Choose the Windows path — TitanCSA','Compare physical-device filters, virtual USB creation and diagnostics. Match the SDK edition, device contract and observation path before a live test.','guides/choose-input.html'),
 'guides/read-benchmarks/':('How to read Windows input latency benchmarks — TitanCSA','Understand QPC endpoints, HID/Raw Input/XInput/WinMM receiver contracts, warm-up, tails, invalid runs and the difference between virtual and physical latency.','guides/read-benchmarks.html'),
 'guides/vdevice-virtual-usb-mouse/':('Create a virtual USB mouse on Windows with Vdevice — TitanCSA','Try a signed Windows 10/11 virtual USB mouse. Follow the mouse panel, verify movement and find the C++ example.','guides/vdevice-virtual-usb-mouse.html'),
 'guides/autohotkey-remap-second-keyboard/':('Remap a second keyboard with AutoHotkey v2 on Windows — TitanCSA','Remap A to B on one selected keyboard. Download the AutoHotkey v2 script and compare results on both keyboards.','guides/autohotkey-remap-second-keyboard.html'),
 'guides/windows-input-release-compare/':('Compare Windows input drivers and Lifetime editions — TitanCSA','Compare Interceptor, Vdevice and Interception V2. Find the matching API, signed demo, device scope and commercial edition.','guides/windows-input-release-compare.html'),
 'guides/release-activation-help/':('Install and activate a TitanCSA Windows Release — error help','Resolve missing activation interfaces, invalid keys and HTTPS failures. Find the correct Windows Release ZIP, SDK and driver version.','guides/release-activation-help.html'),
 'guides/interception-v2-migration/':('Migrate an Interception application to Interception V2 — TitanCSA','Migrate an application using interception.dll, check x86 or x64 library compatibility and list keyboard and mouse hardware IDs.','guides/interception-v2-migration.html'),
 'guides/installer-and-sdk/':('Installer, driver and SDK on Windows — TitanCSA','Understand what to install first, when to download the SDK and how to run a verified first check.','guides/installer-and-sdk.html'),
 'fr/installeur-et-sdk/':('Installateur, pilote et SDK sous Windows — TitanCSA','Choisis le bon téléchargement Windows. Essaie la démo ou compile un premier test SDK.','guides/installer-and-sdk-fr.html'),
 'guides/windows-input-sdk-packages/':('Install Windows input SDK packages for Python, Node.js, .NET, PowerShell and C++ — TitanCSA','Find verified packages for Interceptor, Vdevice and Interception V2 in PyPI, npm, PowerShell Gallery and NuGet. Match the SDK to the installed Windows driver.','guides/windows-input-sdk-packages.html'),
 'guides/windows-input-sdk-java-php-ruby/':('Java, PHP and Ruby SDKs for Windows input drivers — TitanCSA','Find the verified Maven Central, Packagist and RubyGems bindings for Interceptor, Vdevice and Interception V2, with Windows and runtime prerequisites.','guides/windows-input-sdk-java-php-ruby.html'),
 'fr/sdk-java-php-ruby/':('SDK TitanCSA pour Java, PHP et Ruby sous Windows','Choisis le paquet et le pilote Windows de la même édition. Retrouve les versions, les commandes et les premiers appels.','guides/windows-input-sdk-java-php-ruby-fr.html'),
 'guides/gamepad-controller-first-run/':('Test and remap a physical gamepad on Windows — TitanCSA','Identify HID, XUSB, XInputHID or GIP input, use the signed controller demo and try the C++ stick deadzone example.','guides/gamepad-controller-first-run.html'),
 'guides/titan-audio-link-first-run/':('Route Windows playback to a virtual microphone — Titan Audio Link','Download the signed Titan Audio Link demo, verify a stereo virtual audio pair on Windows 11, and find the matching commercial package.','guides/titan-audio-link-first-run.html'),
 'guides/verify-windows-driver-package/':('Verify a signed Windows driver package before installation — TitanCSA','Compare the published SHA-256, verify the Microsoft-signed driver catalog and check the INF package version with PowerShell and SignTool.','guides/verify-windows-driver-package.html'),
 'guides/vdevice-custom-hid-test/':('Test a custom virtual USB HID with Vdevice and hidapitester — TitanCSA','Create a vendor-defined virtual USB HID, read and return exact report bytes with hidapitester, and verify device removal on Windows.','guides/vdevice-custom-hid-test.html'),
 'fr/installer-sdk-windows/':('Installer les SDK d’entrée Windows · Python, Node.js, C++, .NET et PowerShell','Retrouvez les paquets vérifiés pour Interceptor, Vdevice et Interception V2. Commandes d’installation, versions et pilote Windows signé à associer.','guides/windows-input-sdk-packages-fr.html'),
 'fr/activation-release/':('Installer et activer une édition Release TitanCSA sous Windows','Résoudre les erreurs d’activation de Vdevice et Interceptor, vérifier les versions du pilote et du SDK et préparer un rapport de support.','guides/release-activation-fr.html'),
 'fr/souris-usb-virtuelle-vdevice/':('Créer une souris USB virtuelle sous Windows avec Vdevice','Installez la démo Vdevice signée, créez la souris USB virtuelle et testez le déplacement relatif avec le panneau et l’exemple C++.','guides/vdevice-virtual-usb-mouse-fr.html'),
 'fr/remapper-deuxieme-clavier-autohotkey/':('Remapper un deuxième clavier avec AutoHotkey v2 sous Windows','Téléchargez AutoHotInterceptor et un script AutoHotkey v2 pour remapper A vers B sur un seul des deux claviers.','guides/autohotkey-remap-second-keyboard-fr.html'),
 'about/evidence/':('About TitanCSA projects, evidence and support','Understand TitanCSA project evidence, separate SDK and driver licences, engineering previews, known issues, support and private vulnerability reporting.','about/evidence.html'),
 'fr/pilotes-entree-windows/':('Pilotes d’entrée Windows · Choisir une édition et l’essayer | TitanCSA','Comparez Interceptor, Interceptor Keyboard & Mouse, Interceptor Gamepad & Controller, Vdevice et Interception V2. Démonstrations, compatibilité et licences.','guides/windows-input-fr.html')}
for slug,(_,title,description) in featured.items():
    pages[f'projects/{slug}/']=(title,description,f'projects/{slug}.html')
updated={'','guides/choose-input/','fr/pilotes-entree-windows/',*(f'projects/{slug}/' for slug in featured)}
demo_guides={'guides/vdevice-virtual-usb-mouse/','guides/autohotkey-remap-second-keyboard/','guides/vdevice-custom-hid-test/','fr/souris-usb-virtuelle-vdevice/','fr/remapper-deuxieme-clavier-autohotkey/'}
release_guides={'guides/installer-and-sdk/','fr/installeur-et-sdk/','guides/windows-input-release-compare/','guides/release-activation-help/','guides/interception-v2-migration/','guides/windows-input-sdk-packages/','guides/windows-input-sdk-java-php-ruby/','guides/gamepad-controller-first-run/','guides/titan-audio-link-first-run/','guides/verify-windows-driver-package/','fr/activation-release/','fr/installer-sdk-windows/'}
translations=(
    {'en':'','fr':'fr/'},
    {'en':'guides/installer-and-sdk/','fr':'fr/installeur-et-sdk/'},
    {'en':'guides/first-run/','fr':'fr/essayer-sans-pilote/'},
    {'en':'guides/release-activation-help/','fr':'fr/activation-release/'},
    {'en':'guides/windows-input-sdk-packages/','fr':'fr/installer-sdk-windows/'},
    {'en':'guides/windows-input-sdk-java-php-ruby/','fr':'fr/sdk-java-php-ruby/'},
    {'en':'guides/windows-input-release-compare/','fr':'fr/pilotes-entree-windows/'},
    {'en':'guides/vdevice-virtual-usb-mouse/','fr':'fr/souris-usb-virtuelle-vdevice/'},
    {'en':'guides/autohotkey-remap-second-keyboard/','fr':'fr/remapper-deuxieme-clavier-autohotkey/'},
)
reviewed={
    **dict.fromkeys(updated,featured_date),
    **dict.fromkeys(demo_guides | {'','fr/pilotes-entree-windows/','projects/vdevice/','projects/interceptor-keyboard-mouse/','projects/interceptor-gamepad-controller/','about/evidence/','guides/read-benchmarks/'},'2026-11-24'),
    **dict.fromkeys(release_guides | {'','guides/choose-input/','about/evidence/',*(f'projects/{slug}/' for slug in editions)},release_date),
    **dict.fromkeys({'guides/first-run/','fr/essayer-sans-pilote/','guides/windows-input-sdk-packages/','guides/windows-input-sdk-java-php-ruby/','guides/gamepad-controller-first-run/','guides/release-activation-help/','fr/activation-release/','about/evidence/','fr/installer-sdk-windows/'},'2026-11-25'),
    **dict.fromkeys({'guides/windows-input-release-compare/','fr/pilotes-entree-windows/','guides/titan-audio-link-first-run/',*(f'projects/{slug}/' for slug in editions)},commercial_checked),
}
release_terms='<p><strong><a href="/about/evidence/#release-contact">Version without the one-hour demo limit</a></strong> · Add <strong>titancsa</strong> on Discord and message the project name.</p>'
publisher={
    '@type':'Organization', '@id':BASE+'#publisher', 'name':'TitanCSA', 'url':BASE,
    'sameAs':['https://github.com/TitanCSA'],
}

published_dates={route:'2026-11-25' for route in ('fr/installer-sdk-windows/','guides/installer-and-sdk/','fr/installeur-et-sdk/','fr/essayer-sans-pilote/','fr/sdk-java-php-ruby/')}
reviewed.update(published_dates)
reviewed.update(dict.fromkeys(('', 'fr/', 'guides/vdevice-virtual-usb-mouse/',
                               'fr/souris-usb-virtuelle-vdevice/'), '2026-11-25'))


def render(title,description,path,body,article=False):
    canonical=BASE+path
    language='fr' if path.startswith('fr/') else 'en'
    schema={'@context':'https://schema.org','@type':'TechArticle' if article else 'WebSite','name':title,'description':description,'url':canonical,'inLanguage':language,'publisher':publisher}
    if article:
        published='2026-11-24' if path in demo_guides | release_guides else featured_date if path.startswith(('projects/','fr/')) else '2026-11-18'
        modified=reviewed.get(path,checked)
        schema.update(datePublished=published_dates.get(path,published),dateModified=modified,author={'@id':publisher['@id']})
    schemas=[schema]
    if path.startswith('projects/'):
        edition=editions[path.split('/')[1]]
        schemas.append({
            '@context':'https://schema.org','@type':'SoftwareApplication',
            '@id':canonical+'#release','name':edition['name']+' Release','url':canonical,
            'applicationCategory':'DeveloperApplication','operatingSystem':'Microsoft Windows x64',
            'softwareVersion':edition['commercial']['package_version'],
            'description':edition['use'],
            'publisher':{'@id':publisher['@id']},
        })
    if path in ('','fr/'):
        name='Catalogue public TitanCSA' if language=='fr' else 'TitanCSA public project catalogue'
        schemas.append({'@context':'https://schema.org','@type':'ItemList','name':name,'numberOfItems':len(projects),'itemListElement':[{'@type':'ListItem','position':i,'name':p['name'],'url':p['url']} for i,p in enumerate(projects,1)]})
    structured=''.join('<script type="application/ld+json">'+json.dumps(s,ensure_ascii=True).replace('<','\\u003c')+'</script>' for s in schemas)
    for variants in translations:
        if path in variants.values():
            structured+=''.join(f'<link rel="alternate" hreflang="{lang}" href="{BASE}{route}">' for lang,route in variants.items())
    if path in ('','fr/','guides/installer-and-sdk/','fr/installeur-et-sdk/','guides/first-run/','fr/essayer-sans-pilote/') or path.startswith('projects/'):
        structured+=f'<link rel="alternate" type="application/json" href="{BASE}integration.json" title="SDK integration manifest">'
    if not path:
        structured+=f'<link rel="alternate" type="application/rss+xml" title="TitanCSA guides" href="{BASE}rss.xml">'
    if not path and verification:structured+='<meta name="google-site-verification" content="'+escape(verification,quote=True)+'">'
    skip_label,nav_label,theme_text=(
        ('Aller au contenu','Navigation principale','Mode sombre')
        if language=='fr' else ('Skip to content','Main navigation','Dark mode')
    )
    nav_links=(
        '<a href="/fr/#projects">Projets</a><a href="/fr/essayer-sans-pilote/">Premiers pas</a><a class="optional" href="/fr/pilotes-entree-windows/">Pilotes</a>'
        if language=='fr' else
        '<a href="/#projects">Projects</a><a href="/guides/first-run/">Get started</a><a class="optional" href="https://titancsa.github.io/TitanCSA-Benchmarks/">Benchmarks</a><a class="optional" href="/about/evidence/">Evidence &amp; support</a><a href="/fr/" lang="fr">Français</a>'
    )
    footer_lang=' lang="en"' if language=='fr' else ''
    home_path='/fr/' if language=='fr' else '/'
    main=f'<main id="main" tabindex="-1" class="wrap article">{body}</main>' if article else f'<main id="main" tabindex="-1">{body}</main>'
    return f'''<!doctype html><html lang="{language}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><meta name="description" content="{escape(description,quote=True)}"><link rel="canonical" href="{canonical}"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#194fd1"><link rel="icon" type="image/svg+xml" href="/assets/icon.svg"><link rel="stylesheet" href="/assets/site.css"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:site_name" content="TitanCSA"><meta property="og:title" content="{escape(title,quote=True)}"><meta property="og:description" content="{escape(description,quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}assets/social.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">{structured}<script src="/assets/catalogue.js" defer></script></head><body><a class="skip" href="#main">{skip_label}</a><header class="header"><div class="wrap"><a class="brand" href="{home_path}"><span class="brand-mark" aria-hidden="true">T</span>TitanCSA</a><nav class="nav" aria-label="{nav_label}">{nav_links}<button type="button" class="theme-toggle" data-theme-toggle hidden aria-pressed="false">{theme_text}</button></nav></div></header>{main}<footer class="footer"{footer_lang}><div class="wrap"><p>© 2026 TitanCSA. Documentation maintained with AI assistance. Individual project licences and tested limits apply. This is a publisher-operated catalogue.</p><nav aria-label="Footer"><a href="/about/evidence/">About &amp; support</a><a href="https://github.com/TitanCSA/TitanCSA">GitHub</a><a href="https://github.com/TitanCSA/sdk-packages">SDK packages</a><a href="https://github.com/TitanCSA/TitanCSA.github.io">Website source</a></nav></div></footer></body></html>'''
for path,(title,description,source) in pages.items():
    body=(ROOT/'content'/source).read_text(encoding='utf8')
    for key,value in replacements.items():body=body.replace('{{'+key+'}}',value)
    if path.startswith('projects/'):
        slug=path.split('/')[1]
        edition=editions[slug]
        demo_assets=edition['demo_assets']
        downloads=' · '.join(f'<a href="{demo_assets[role]}">{label}</a>'
                             for role,label in [('examples','Examples ZIP'),('sdk','SDK source ZIP'),('checksums','SHA-256 checksums')]
                             if role in demo_assets)
        links=(
            f'<p>Commercial package <strong>{escape(edition["commercial"]["package_version"])}</strong> contains signed driver '
            f'<strong>{escape(edition["commercial"]["driver_version"])}</strong>. Delivery verified {commercial_checked}.</p>'
            f'<p>Signed demo <a href="{edition["demo_url"]}">{edition["demo"]} release notes</a> · {downloads}.</p><p>'
            '<a href="/guides/windows-input-release-compare/">Compare editions</a> · '
            '<a href="/guides/release-activation-help/">Installation and activation help</a> · '
            '<a href="/guides/windows-input-sdk-packages/">SDK packages</a>.</p>'
        )
        label='Download demo installer' if 'installer' in demo_assets else 'Download demo ZIP'
        body=body.replace('{{DEMO_DOWNLOAD_URL}}',edition['demo_download_url']).replace('{{DEMO_DOWNLOAD_LABEL}}',label)
        body=body.replace('{{RELEASE_TERMS}}',release_terms).replace('{{RELEASE_DETAILS}}',links)
    assert '{{' not in body
    target=OUT/path/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(render(title,description,path,body,path not in ('','fr/')),encoding='utf8')
(OUT/'404.html').write_text(render('Page not found — TitanCSA','Find the TitanCSA project catalogue and first-run guides.','404.html','<h1>Page not found.</h1><p>The address may have changed. <a href="/">Open the project catalogue</a> or <a href="/guides/first-run/">read the first-run guide</a>.</p>',True).replace('index,follow,max-image-preview:large','noindex,follow'),encoding='utf8')
urls=''.join(f'<url><loc>{BASE+path}</loc><lastmod>{reviewed.get(path,checked)}</lastmod></url>' for path in pages)
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls+'</urlset>',encoding='utf8')
feed=ET.Element('rss', version='2.0')
channel=ET.SubElement(feed,'channel')
ET.SubElement(channel,'title').text='TitanCSA guides'
ET.SubElement(channel,'link').text=BASE
ET.SubElement(channel,'description').text='Practical Windows input and device SDK guides from TitanCSA.'
ET.register_namespace('atom','http://www.w3.org/2005/Atom')
ET.SubElement(channel,'{http://www.w3.org/2005/Atom}link',href=BASE+'rss.xml',rel='self',type='application/rss+xml')
for path,(title,description,_) in reversed(pages.items()):
    if path not in demo_guides | release_guides:
        continue
    item=ET.SubElement(channel,'item')
    ET.SubElement(item,'title').text=title
    ET.SubElement(item,'link').text=BASE+path
    ET.SubElement(item,'guid',isPermaLink='true').text=BASE+path
    ET.SubElement(item,'description').text=description
ET.indent(feed)
ET.ElementTree(feed).write(OUT/'rss.xml',encoding='utf-8',xml_declaration=True)
search_robots=['OAI-SearchBot','Claude-SearchBot','Claude-User']
(OUT/'robots.txt').write_text(
    'User-agent: *\nAllow: /\n\n'
    + ''.join(f'User-agent: {bot}\n' for bot in search_robots)
    + 'Allow: /\n\nSitemap: '+BASE+'sitemap.xml\nSitemap: '+BASE+'TitanCSA-Benchmarks/sitemap.xml\n',
    encoding='utf8',
)
(OUT/'integration.json').write_text(json.dumps(integration,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
shutil.copyfile(ROOT/'integration.schema.json', OUT/'integration.schema.json')
(OUT/'releases.json').write_text(
    json.dumps({'reviewed':release_date,'commercial_checked':commercial_checked,'editions':list(editions.values())},ensure_ascii=False,indent=2)+'\n',
    encoding='utf8',
)
reference_links=['# TitanCSA','', '> Public Windows input driver and SDK documentation from the publisher.', '',
    '## Choose, try and activate',
    f'- [Catalogue des projets en français]({BASE}fr/)',
    f'- [Installer, driver and SDK]({BASE}guides/installer-and-sdk/)',
    f'- [Installateur, pilote et SDK]({BASE}fr/installeur-et-sdk/)',
    f'- [SDK integration manifest]({BASE}integration.json)',
    f'- [Integration JSON schema]({BASE}integration.schema.json)',
    f'- [First Windows app runs without a driver]({BASE}guides/first-run/)',
    f'- [Essayer un outil sans ajouter de pilote]({BASE}fr/essayer-sans-pilote/)',
    f'- [Compare editions]({BASE}guides/windows-input-release-compare/)',
    f'- [Installation and activation help]({BASE}guides/release-activation-help/)',
    f'- [Dépannage de l’activation en français]({BASE}fr/activation-release/)',
    f'- [Installation des SDK Windows en français]({BASE}fr/installer-sdk-windows/)',
    f'- [Migration from the original Interception API]({BASE}guides/interception-v2-migration/)',
    f'- [Verified registry SDK packages]({BASE}guides/windows-input-sdk-packages/)',
    f'- [Java, PHP and Ruby SDK packages]({BASE}guides/windows-input-sdk-java-php-ruby/)',
    f'- [Paquets Java, PHP et Ruby]({BASE}fr/sdk-java-php-ruby/)',
    f'- [Verify a Windows driver package before installation]({BASE}guides/verify-windows-driver-package/)',
    f'- [Physical gamepad quickstart]({BASE}guides/gamepad-controller-first-run/)',
    f'- [Titan Audio Link virtual microphone]({BASE}guides/titan-audio-link-first-run/)',
    f'- [Virtual USB mouse tutorial]({BASE}guides/vdevice-virtual-usb-mouse/)',
    f'- [Souris USB virtuelle avec Vdevice]({BASE}fr/souris-usb-virtuelle-vdevice/)',
    f'- [Reproduce the Vdevice custom HID test]({BASE}guides/vdevice-custom-hid-test/)',
    f'- [Per-device AutoHotkey tutorial]({BASE}guides/autohotkey-remap-second-keyboard/)',
    f'- [Deuxième clavier avec AutoHotkey v2]({BASE}fr/remapper-deuxieme-clavier-autohotkey/)',
    f'- [Benchmark results and scope]({BASE}TitanCSA-Benchmarks/)', '', '## Products']
reference_links.extend(
    f'- [{e["name"]}]({e["overview_url"]}): {e["use"]} Signed demo notes: {e["demo_url"]}. Demo download: {e["demo_download_url"]}. Release without the one-hour demo limit: contact titancsa on Discord. {e["release_contact"]["instructions_url"]}'
    for e in editions.values()
)
(OUT/'llms.txt').write_text('\n'.join(reference_links)+'\n',encoding='utf8')
write_starter(OUT,integration)
public_projects={**data,'source_fr':french_copy['source'],'projects':[]}
for project in projects:
    purpose, first_step=french_copy['projects'][project['name']]
    public_projects['projects'].append({**project,'plain_purpose_fr':purpose,'plain_first_step_fr':first_step})
(OUT/'projects.json').write_text(json.dumps(public_projects,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
if indexnow_key:(OUT/f'{indexnow_key}.txt').write_text(indexnow_key+'\n',encoding='utf8')
print('Built',len(pages),'public pages and',len(projects),'curated project entries')
