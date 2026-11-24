"""Build a public, dependency-free static catalogue from curated project evidence."""
from pathlib import Path
from collections import OrderedDict
from html import escape
import json,re,shutil

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist';BASE='https://titancsa.github.io/'
data=json.loads((ROOT/'projects.json').read_text(encoding='utf8'));projects=data['projects'];checked=data['checked']
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
featured_date='2026-11-23'
shop='https://licences.configcsa.com/'
release_data=json.loads((ROOT/'releases.json').read_text(encoding='utf8'))
release_date=release_data['reviewed']
editions={}
for edition in release_data['editions']:
    slug=edition['slug']
    repo,title,_=featured[slug]
    editions[slug]={
        **edition,
        'name':title.split(' | ',1)[0],
        'repository':f'https://github.com/TitanCSA/{repo}',
        'demo_url':f'https://github.com/TitanCSA/{repo}/releases/tag/{edition["tag"]}',
        'overview_url':f'{BASE}projects/{slug}/',
        'purchase_url':shop+slug,
        'price_eur':400,
    }
assert set(editions)==set(featured) and len(editions)==len(release_data['editions'])
assert len(projects)==60 and len({p['url'].lower() for p in projects})==60
assert all(p['url'].startswith(('https://github.com/TitanCSA/','https://github.com/titanfyre/')) for p in projects)
OUT.mkdir(exist_ok=True)
for folder in ['src','assets']:
    target=OUT/('assets' if folder=='src' else folder);target.mkdir(exist_ok=True)
    for p in (ROOT/folder).iterdir():
        if p.is_file():shutil.copyfile(p,target/p.name)
groups=OrderedDict()
for project in projects:groups.setdefault((project['category'],project['category_title']),[]).append(project)
cards=[]
for (key,title),entries in groups.items():
    items=[]
    for p in entries:
        search=escape(' '.join(str(p[k]) for k in ['name','description','first_step','kind','category_title']),quote=True)
        tag='tag preview' if p['kind']=='Preview' else 'tag'
        kind=escape(p['kind']);note=f'<span class="start-tag">{escape(p["start_mode"])}</span>' if p['start_without_adding_driver'] else ''
        issue=f'<a class="known-issue" href="{escape(p["known_issue_url"])}">WDF-001 status by edition ↗</a>' if p['known_issue_url'] else ''
        ident='project-'+re.sub(r'[^a-z0-9-]','-',p['name'].lower())
        overview=featured_paths.get(p['url'].rsplit('/',1)[-1])
        if p['name']=='Titan-Audio-Link':
            overview='/guides/titan-audio-link-first-run/'
        overview_link=f'<p><a href="{overview}">Project overview</a></p>' if overview else ''
        items.append(f'''<article id="{ident}" class="project" data-project data-category="{escape(key)}" data-no-driver="{str(p['start_without_adding_driver']).lower()}" data-search="{search}">
<div class="project-title"><h3><a href="{escape(p['url'])}">{escape(p['name'])} <span aria-hidden="true">↗</span></a></h3><span class="{tag}">{kind}</span>{note}</div>
<div><p>{escape(p['description'])}</p><details><summary>Start and scope</summary><p>{escape(p['first_step'])}</p></details>{issue}{overview_link}</div></article>''')
    cards.append(f'<section id="{escape(key)}" class="project-group" data-project-group aria-labelledby="heading-{escape(key)}"><div class="group-heading"><h2 id="heading-{escape(key)}">{escape(title)}</h2><span class="group-count" data-group-count>{len(entries)} entries</span></div>'+''.join(items)+'</section>')
replacements={'PROJECT_COUNT':str(len(projects)),'CHECKED_DATE':checked,'PROJECTS':'\n'.join(cards),'CATEGORY_OPTIONS':''.join(f'<option value="{escape(key)}">{escape(title)}</option>' for key,title in groups),'CATEGORY_LINKS':''.join(f'<a href="#{escape(key)}" data-category-jump>{escape(title)}</a>' for key,title in groups)}
replacements['RELEASE_REVIEW_DATE']=release_date
replacements['RELEASE_COMPARISON_ROWS']='\n'.join(
    f'<tr><th scope="row"><a href="{e["overview_url"]}">{escape(e["name"])}</a></th>'
    f'<td>{escape(e["use"])} <strong>{escape(e["api"])}</strong> {escape(e["note"])}</td>'
    f'<td><a href="{e["demo_url"]}">{escape(e["name"])} demo {e["demo"]}</a></td>'
    f'<td><a href="{e["purchase_url"]}">Buy {escape(e["name"])} Release</a> · €{e["price_eur"]} Lifetime</td></tr>'
    for e in editions.values()
)
pages={
 '':('TitanCSA — Windows tools, device SDKs and practical guides','Find Windows input tools, virtual devices, diagnostics and SDKs by workflow. Clear first-run guides, project licences, public evidence and known limits.','index.html'),
 'guides/first-run/':('A first Windows tool run without an input driver — TitanCSA','Start with Browser Control SDK, read-only Driver Readiness Inspector or offline fixture validation. Prerequisites, exact steps and expected results.','guides/first-run.html'),
 'guides/choose-input/':('Input interception or virtual devices? Choose the Windows path — TitanCSA','Compare physical-device filters, virtual USB creation and diagnostics. Match the SDK edition, device contract and observation path before a live test.','guides/choose-input.html'),
 'guides/read-benchmarks/':('How to read Windows input latency benchmarks — TitanCSA','Understand QPC endpoints, HID/Raw Input/XInput/WinMM receiver contracts, warm-up, tails, invalid runs and the difference between virtual and physical latency.','guides/read-benchmarks.html'),
 'guides/vdevice-virtual-usb-mouse/':('Create a virtual USB mouse on Windows with Vdevice — TitanCSA','Try a signed Windows 10/11 virtual USB mouse. Follow the mouse panel, verify movement and find the C++ example.','guides/vdevice-virtual-usb-mouse.html'),
 'guides/autohotkey-remap-second-keyboard/':('Remap a second keyboard with AutoHotkey v2 on Windows — TitanCSA','Remap A to B on one selected keyboard. Download the AutoHotkey v2 script and compare results on both keyboards.','guides/autohotkey-remap-second-keyboard.html'),
 'guides/windows-input-release-compare/':('Compare Windows input drivers and Lifetime editions — TitanCSA','Compare Interceptor, Vdevice and Interception V2. Find the matching API, signed demo, device scope and commercial edition.','guides/windows-input-release-compare.html'),
 'guides/release-activation-help/':('Install and activate a TitanCSA Windows Release — error help','Resolve missing activation interfaces, invalid keys and HTTPS failures. Find the correct Windows Release ZIP, SDK and driver version.','guides/release-activation-help.html'),
 'guides/interception-v2-migration/':('Migrate an Interception application to Interception V2 — TitanCSA','Migrate an application using interception.dll, check x86 or x64 library compatibility and list keyboard and mouse hardware IDs.','guides/interception-v2-migration.html'),
 'guides/windows-input-sdk-packages/':('Install Windows input SDK packages for Node.js, PowerShell and C++ — TitanCSA','Find registry-verified Interceptor, Vdevice and Interception V2 SDK packages. Match the SDK to the installed Windows driver.','guides/windows-input-sdk-packages.html'),
 'guides/gamepad-controller-first-run/':('Test and remap a physical gamepad on Windows — TitanCSA','Identify HID, XUSB, XInputHID or GIP input, use the signed controller demo and try the C++ stick deadzone example.','guides/gamepad-controller-first-run.html'),
 'guides/titan-audio-link-first-run/':('Route Windows playback to a virtual microphone — Titan Audio Link','Try a signed virtual audio pair, test stereo playback and recording, and find the matching Titan Audio Link commercial package.','guides/titan-audio-link-first-run.html'),
 'fr/activation-release/':('Installer et activer une édition Release TitanCSA sous Windows','Résoudre les erreurs d’activation de Vdevice et Interceptor, vérifier les versions du pilote et du SDK et préparer un rapport de support.','guides/release-activation-fr.html'),
 'about/evidence/':('About TitanCSA projects, evidence and support','Understand TitanCSA project evidence, separate SDK and driver licences, engineering previews, known issues, support and private vulnerability reporting.','about/evidence.html'),
 'fr/pilotes-entree-windows/':('Pilotes d’entrée Windows · Choisir, essayer et acheter | TitanCSA','Comparez Interceptor, Interceptor Keyboard & Mouse, Interceptor Gamepad & Controller, Vdevice et Interception V2. Démonstrations, compatibilité et licences.','guides/windows-input-fr.html')}
for slug,(_,title,description) in featured.items():
    pages[f'projects/{slug}/']=(title,description,f'projects/{slug}.html')
updated={'','guides/choose-input/','fr/pilotes-entree-windows/',*(f'projects/{slug}/' for slug in featured)}
demo_guides={'guides/vdevice-virtual-usb-mouse/','guides/autohotkey-remap-second-keyboard/'}
release_guides={'guides/windows-input-release-compare/','guides/release-activation-help/','guides/interception-v2-migration/','guides/windows-input-sdk-packages/','guides/gamepad-controller-first-run/','guides/titan-audio-link-first-run/','fr/activation-release/'}
activation_translations={'en':'guides/release-activation-help/','fr':'fr/activation-release/'}
reviewed={
    **dict.fromkeys(updated,featured_date),
    **dict.fromkeys(demo_guides | {'','fr/pilotes-entree-windows/','projects/vdevice/','projects/interceptor-keyboard-mouse/','projects/interceptor-gamepad-controller/','about/evidence/','guides/read-benchmarks/'},'2026-11-24'),
    **dict.fromkeys(release_guides | {'','guides/choose-input/','about/evidence/',*(f'projects/{slug}/' for slug in editions)},release_date),
}
purchase_terms='<p class="subtle">Licensed Release at €400 per edition, paid once. Online activation is required after installation and again after a driver reload or Windows restart.</p>'

def render(title,description,path,body,article=False):
    canonical=BASE+path
    language='fr' if path.startswith('fr/') else 'en'
    schema={'@context':'https://schema.org','@type':'TechArticle' if article else 'WebSite','name':title,'description':description,'url':canonical,'inLanguage':language,'publisher':{'@type':'Organization','name':'TitanCSA','url':BASE}}
    if article:
        published='2026-11-24' if path in demo_guides | release_guides else featured_date if path.startswith(('projects/','fr/')) else '2026-11-18'
        modified=reviewed.get(path,checked)
        schema.update(datePublished=published,dateModified=modified,author={'@type':'Organization','name':'TitanCSA'})
    schemas=[schema]
    if path.startswith('projects/'):
        edition=editions[path.split('/')[1]]
        schemas.append({
            '@context':'https://schema.org','@type':'SoftwareApplication',
            '@id':canonical+'#release','name':edition['name']+' Release','url':canonical,
            'applicationCategory':'DeveloperApplication','operatingSystem':'Microsoft Windows x64',
            'description':edition['use'],
            'offers':{'@type':'Offer','url':edition['purchase_url'],'price':edition['price_eur'],'priceCurrency':'EUR'},
            'publisher':{'@type':'Organization','name':'TitanCSA','url':BASE},
        })
    if not path:schemas.append({'@context':'https://schema.org','@type':'ItemList','name':'TitanCSA public project catalogue','numberOfItems':len(projects),'itemListElement':[{'@type':'ListItem','position':i,'name':p['name'],'url':p['url']} for i,p in enumerate(projects,1)]})
    structured=''.join('<script type="application/ld+json">'+json.dumps(s,ensure_ascii=True).replace('<','\\u003c')+'</script>' for s in schemas)
    if path in activation_translations.values():
        structured+=''.join(f'<link rel="alternate" hreflang="{lang}" href="{BASE}{route}">' for lang,route in activation_translations.items())
    if not path and verification:structured+='<meta name="google-site-verification" content="'+escape(verification,quote=True)+'">'
    skip_label,home_label,nav_label,theme_label=(
        ('Aller au contenu','Accueil TitanCSA','Navigation principale','Changer le th?me')
        if language=='fr' else ('Skip to content','TitanCSA home','Main navigation','Switch color theme')
    )
    nav_links=(
        '<a href="/#projects">Projets</a><a href="/guides/choose-input/">Comparatif EN</a>'
        if language=='fr' else
        '<a href="/#projects">Projects</a><a href="/guides/first-run/">Get started</a><a class="optional" href="https://titancsa.github.io/TitanCSA-Benchmarks/">Benchmarks</a><a class="optional" href="/about/evidence/">Evidence &amp; support</a><a href="https://github.com/TitanCSA/TitanCSA/blob/main/DEMARRER.md" lang="fr">FR</a>'
    )
    theme_text='Th?me' if language=='fr' else 'Theme'
    footer_lang=' lang="en"' if language=='fr' else ''
    main=f'<main id="main" class="wrap article">{body}</main>' if article else f'<main id="main">{body}</main>'
    return f'''<!doctype html><html lang="{language}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><meta name="description" content="{escape(description,quote=True)}"><link rel="canonical" href="{canonical}"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#194fd1"><link rel="icon" type="image/svg+xml" href="/assets/icon.svg"><link rel="stylesheet" href="/assets/site.css"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:site_name" content="TitanCSA"><meta property="og:title" content="{escape(title,quote=True)}"><meta property="og:description" content="{escape(description,quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}assets/social.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">{structured}<script src="/assets/catalogue.js" defer></script></head><body><a class="skip" href="#main">{skip_label}</a><header class="header"><div class="wrap"><a class="brand" href="/" aria-label="{home_label}"><span class="brand-mark" aria-hidden="true">T</span>TitanCSA</a><nav class="nav" aria-label="{nav_label}">{nav_links}<button type="button" class="theme-toggle" data-theme-toggle aria-label="{theme_label}">{theme_text}</button></nav></div></header>{main}<footer class="footer"{footer_lang}><div class="wrap"><p>© 2026 TitanCSA. Documentation maintained with AI assistance. Individual project licences and tested limits apply. This is a publisher-operated catalogue.</p><nav aria-label="Footer"><a href="/about/evidence/">About &amp; support</a><a href="https://github.com/TitanCSA/TitanCSA">GitHub</a><a href="https://github.com/TitanCSA/sdk-packages">SDK packages</a><a href="https://github.com/TitanCSA/TitanCSA.github.io">Website source</a></nav></div></footer></body></html>'''
for path,(title,description,source) in pages.items():
    body=(ROOT/'content'/source).read_text(encoding='utf8')
    for key,value in replacements.items():body=body.replace('{{'+key+'}}',value)
    if path.startswith('projects/'):
        slug=path.split('/')[1]
        edition=editions[slug]
        links=(
            f'<p>Signed demo <a href="{edition["demo_url"]}">{edition["demo"]}</a>. '
            '<a href="/guides/windows-input-release-compare/">Compare editions</a> · '
            '<a href="/guides/release-activation-help/">Installation and activation help</a> · '
            '<a href="/guides/windows-input-sdk-packages/">SDK packages</a>.</p>'
        )
        body=body.replace('{{PURCHASE_URL}}',edition['purchase_url']).replace('{{PURCHASE_TERMS}}',purchase_terms+links)
    assert '{{' not in body
    target=OUT/path/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(render(title,description,path,body,bool(path)),encoding='utf8')
(OUT/'404.html').write_text(render('Page not found — TitanCSA','Find the TitanCSA project catalogue and first-run guides.','404.html','<h1>Page not found.</h1><p>The address may have changed. <a href="/">Open the project catalogue</a> or <a href="/guides/first-run/">read the first-run guide</a>.</p>',True).replace('index,follow,max-image-preview:large','noindex,follow'),encoding='utf8')
urls=''.join(f'<url><loc>{BASE+path}</loc><lastmod>{reviewed.get(path,checked)}</lastmod></url>' for path in pages)
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls+'</urlset>',encoding='utf8')
search_robots=['OAI-SearchBot','Claude-SearchBot','Claude-User']
(OUT/'robots.txt').write_text(
    'User-agent: *\nAllow: /\n\n'
    + ''.join(f'User-agent: {bot}\n' for bot in search_robots)
    + 'Allow: /\n\nSitemap: '+BASE+'sitemap.xml\nSitemap: '+BASE+'TitanCSA-Benchmarks/sitemap.xml\n',
    encoding='utf8',
)
(OUT/'releases.json').write_text(
    json.dumps({'reviewed':release_date,'editions':list(editions.values())},ensure_ascii=False,indent=2)+'\n',
    encoding='utf8',
)
reference_links=['# TitanCSA','', '> Public Windows input driver and SDK documentation from the publisher.', '',
    '## Choose, try and activate',
    f'- [Compare editions]({BASE}guides/windows-input-release-compare/)',
    f'- [Installation and activation help]({BASE}guides/release-activation-help/)',
    f'- [Dépannage de l’activation en français]({BASE}fr/activation-release/)',
    f'- [Migration from the original Interception API]({BASE}guides/interception-v2-migration/)',
    f'- [Verified registry SDK packages]({BASE}guides/windows-input-sdk-packages/)',
    f'- [Physical gamepad quickstart]({BASE}guides/gamepad-controller-first-run/)',
    f'- [Titan Audio Link virtual microphone]({BASE}guides/titan-audio-link-first-run/)',
    f'- [Virtual USB mouse tutorial]({BASE}guides/vdevice-virtual-usb-mouse/)',
    f'- [Per-device AutoHotkey tutorial]({BASE}guides/autohotkey-remap-second-keyboard/)',
    f'- [Benchmark results and scope]({BASE}TitanCSA-Benchmarks/)', '', '## Products']
reference_links.extend(
    f'- [{e["name"]}]({e["overview_url"]}): {e["use"]} Signed demo: {e["demo_url"]}. Release checkout: {e["purchase_url"]}.'
    for e in editions.values()
)
(OUT/'llms.txt').write_text('\n'.join(reference_links)+'\n',encoding='utf8')
(OUT/'projects.json').write_bytes((ROOT/'projects.json').read_bytes())
if indexnow_key:(OUT/f'{indexnow_key}.txt').write_text(indexnow_key+'\n',encoding='utf8')
print('Built',len(pages),'public pages and',len(projects),'curated project entries')
