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
        issue=f'<a class="known-issue" href="{escape(p["known_issue_url"])}">Open WDF stability finding ↗</a>' if p['known_issue_url'] else ''
        ident='project-'+re.sub(r'[^a-z0-9-]','-',p['name'].lower())
        items.append(f'''<article id="{ident}" class="project" data-project data-category="{escape(key)}" data-no-driver="{str(p['start_without_adding_driver']).lower()}" data-search="{search}">
<div class="project-title"><h3><a href="{escape(p['url'])}">{escape(p['name'])} <span aria-hidden="true">↗</span></a></h3><span class="{tag}">{kind}</span>{note}</div>
<div><p>{escape(p['description'])}</p><details><summary>Start and scope</summary><p>{escape(p['first_step'])}</p></details>{issue}</div></article>''')
    cards.append(f'<section id="{escape(key)}" class="project-group" data-project-group aria-labelledby="heading-{escape(key)}"><div class="group-heading"><h2 id="heading-{escape(key)}">{escape(title)}</h2><span class="group-count" data-group-count>{len(entries)} entries</span></div>'+''.join(items)+'</section>')
replacements={'PROJECT_COUNT':str(len(projects)),'CHECKED_DATE':checked,'PROJECTS':'\n'.join(cards),'CATEGORY_OPTIONS':''.join(f'<option value="{escape(key)}">{escape(title)}</option>' for key,title in groups),'CATEGORY_LINKS':''.join(f'<a href="#{escape(key)}" data-category-jump>{escape(title)}</a>' for key,title in groups)}
pages={
 '':('TitanCSA — Windows tools, device SDKs and practical guides','Find Windows input tools, virtual devices, diagnostics and SDKs by workflow. Clear first-run guides, project licences, public evidence and known limits.','index.html'),
 'guides/first-run/':('A first Windows tool run without an input driver — TitanCSA','Start with Browser Control SDK, read-only Driver Readiness Inspector or offline fixture validation. Prerequisites, exact steps and expected results.','guides/first-run.html'),
 'guides/choose-input/':('Input interception or virtual devices? Choose the Windows path — TitanCSA','Compare physical-device filters, virtual USB creation and diagnostics. Match the SDK edition, device contract and observation path before a live test.','guides/choose-input.html'),
 'guides/read-benchmarks/':('How to read Windows input latency benchmarks — TitanCSA','Understand QPC endpoints, HID/Raw Input/XInput/WinMM receiver contracts, warm-up, tails, invalid runs and the difference between virtual and physical latency.','guides/read-benchmarks.html'),
 'about/evidence/':('About TitanCSA projects, evidence and support','Understand TitanCSA project evidence, separate SDK and driver licences, engineering previews, known issues, support and private vulnerability reporting.','about/evidence.html')}
def render(title,description,path,body,article=False):
    canonical=BASE+path
    schema={'@context':'https://schema.org','@type':'TechArticle' if article else 'WebSite','name':title,'description':description,'url':canonical,'inLanguage':'en','publisher':{'@type':'Organization','name':'TitanCSA','url':BASE}}
    if article:schema.update(datePublished='2026-11-18',dateModified=checked,author={'@type':'Organization','name':'TitanCSA'})
    schemas=[schema]
    if not path:schemas.append({'@context':'https://schema.org','@type':'ItemList','name':'TitanCSA public project catalogue','numberOfItems':len(projects),'itemListElement':[{'@type':'ListItem','position':i,'name':p['name'],'url':p['url']} for i,p in enumerate(projects,1)]})
    structured=''.join('<script type="application/ld+json">'+json.dumps(s,ensure_ascii=True).replace('<','\\u003c')+'</script>' for s in schemas)
    if not path and verification:structured+='<meta name="google-site-verification" content="'+escape(verification,quote=True)+'">'
    main=f'<main id="main" class="wrap article">{body}</main>' if article else f'<main id="main">{body}</main>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><meta name="description" content="{escape(description,quote=True)}"><link rel="canonical" href="{canonical}"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#194fd1"><link rel="icon" type="image/svg+xml" href="/assets/icon.svg"><link rel="stylesheet" href="/assets/site.css"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:site_name" content="TitanCSA"><meta property="og:title" content="{escape(title,quote=True)}"><meta property="og:description" content="{escape(description,quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}assets/social.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">{structured}<script src="/assets/catalogue.js" defer></script></head><body><a class="skip" href="#main">Skip to content</a><header class="header"><div class="wrap"><a class="brand" href="/" aria-label="TitanCSA home"><span class="brand-mark" aria-hidden="true">T</span>TitanCSA</a><nav class="nav" aria-label="Main navigation"><a href="/#projects">Projects</a><a href="/guides/first-run/">Get started</a><a class="optional" href="https://titancsa.github.io/TitanCSA-Benchmarks/">Benchmarks</a><a class="optional" href="/about/evidence/">Evidence &amp; support</a><a href="https://github.com/TitanCSA/TitanCSA/blob/main/DEMARRER.md" lang="fr">FR</a><button type="button" class="theme-toggle" data-theme-toggle aria-label="Switch color theme">Theme</button></nav></div></header>{main}<footer class="footer"><div class="wrap"><p>© 2026 TitanCSA. Documentation maintained with AI assistance. Individual project licences and tested limits apply. This is a publisher-operated catalogue.</p><nav aria-label="Footer"><a href="/about/evidence/">About &amp; support</a><a href="https://github.com/TitanCSA/TitanCSA">GitHub</a><a href="https://github.com/TitanCSA/sdk-packages">SDK packages</a><a href="https://github.com/TitanCSA/TitanCSA.github.io">Website source</a></nav></div></footer></body></html>'''
for path,(title,description,source) in pages.items():
    body=(ROOT/'content'/source).read_text(encoding='utf8')
    for key,value in replacements.items():body=body.replace('{{'+key+'}}',value)
    assert '{{' not in body
    target=OUT/path/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(render(title,description,path,body,bool(path)),encoding='utf8')
(OUT/'404.html').write_text(render('Page not found — TitanCSA','Find the TitanCSA project catalogue and first-run guides.','404.html','<h1>Page not found.</h1><p>The address may have changed. <a href="/">Open the project catalogue</a> or <a href="/guides/first-run/">read the first-run guide</a>.</p>',True).replace('index,follow,max-image-preview:large','noindex,follow'),encoding='utf8')
urls=''.join(f'<url><loc>{BASE+path}</loc><lastmod>{checked}</lastmod></url>' for path in pages)
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls+'</urlset>',encoding='utf8')
(OUT/'robots.txt').write_text('User-agent: *\nAllow: /\n\nSitemap: '+BASE+'sitemap.xml\nSitemap: '+BASE+'TitanCSA-Benchmarks/sitemap.xml\n',encoding='utf8')
(OUT/'projects.json').write_bytes((ROOT/'projects.json').read_bytes())
print('Built',len(pages),'public pages and',len(projects),'curated project entries')
