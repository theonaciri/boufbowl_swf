"""Render the French legal drafts without a third-party Markdown dependency.

Edit docs/legal/*.md, then run python3 -m tools.build_legal_pages.
The renderer intentionally supports only headings, paragraphs, lists and links.
"""
import argparse
import html
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS = (
    ('confidentialite', 'Confidentialité'),
    ('conditions-utilisation', 'Conditions d’utilisation'),
    ('mentions-legales', 'Mentions légales'),
    ('cookies', 'Cookies et stockage'),
    ('charte-communaute', 'Charte communautaire'),
    ('reglement-tournois', 'Règlement des tournois'),
)


def inline(text):
    parts = re.split(r'(\[[^\]\n]+\]\([^\s)]+\))', text)
    result = []
    for part in parts:
        match = re.fullmatch(r'\[([^\]\n]+)\]\(([^\s)]+)\)', part)
        if match:
            label, url = match.groups()
            if not (url.startswith('https://') or re.fullmatch(r'[a-z-]+\.(?:html|md)', url)):
                raise ValueError('Unsupported legal-document link: '+url)
            if url.endswith('.md'): url = url[:-3]+'.html'
            result.append('<a href="'+html.escape(url, quote=True)+'">'+html.escape(label)+'</a>')
        else:
            result.append(html.escape(part).replace('[]', '<span class="placeholder" title="Information à compléter">[]</span>'))
    return ''.join(result)


def render_markdown(source):
    blocks = re.split(r'\n\s*\n', source.strip())
    result, headings = [], []
    for block in blocks:
        lines = block.splitlines()
        if block.startswith('# '):
            continue  # The shared document header contains the title.
        if block.startswith('## '):
            label = block[3:]
            anchor = 'section-'+str(len(headings)+1)
            headings.append((anchor, label))
            result.append('<h2 id="'+anchor+'">'+inline(label)+'</h2>')
        elif all(line.startswith('- ') for line in lines):
            result.append('<ul>'+''.join('<li>'+inline(line[2:])+'</li>' for line in lines)+'</ul>')
        else:
            result.append('<p>'+inline(' '.join(line.strip() for line in lines))+'</p>')
    return '\n'.join(result), headings


def page(slug, title, body, headings=()):
    links = ''.join('<a href="'+key+'.html"'+(' aria-current="page"' if key==slug else '')+'>'+html.escape(label)+'</a>' for key,label in DOCUMENTS)
    toc = '<aside aria-label="Sommaire"><strong>Dans ce document</strong>'+''.join('<a href="#'+anchor+'">'+html.escape(label)+'</a>' for anchor,label in headings)+'</aside>' if headings else ''
    return '''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>'''+html.escape(title)+''' · Boufbowl</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="legal.css">
</head>
<body>
<a class="skip" href="#contenu">Aller au contenu</a>
<header><a class="brand" href="legal.html">BOUFBOWL <span>Informations juridiques</span></a><a href="play.html">Retour au jeu ↗</a></header>
<nav aria-label="Documents juridiques">'''+links+'''</nav>
<main id="contenu">
<div class="heading"><p class="eyebrow">Le cadre du jeu</p><h1>'''+html.escape(title)+'''</h1></div>
<p class="draft" role="note">Projet à compléter : les champs <span class="placeholder">[]</span> signalent une information ou un choix restant à renseigner par l’exploitant.</p>
<div class="layout">'''+toc+'''<article>'''+body+'''</article></div>
</main>
<footer><a href="legal.html">Tous les documents</a><a href="confidentialite.html">Confidentialité</a><a href="conditions-utilisation.html">Conditions d’utilisation</a><a href="play.html">Jouer à Boufbowl</a></footer>
</body>
</html>
'''


def outputs():
    result = {}
    cards = []
    for slug, label in DOCUMENTS:
        source = (ROOT/'docs/legal'/f'{slug}.md').read_text()
        title = source.splitlines()[0].removeprefix('# ')
        body, headings = render_markdown(source)
        result[slug+'.html'] = page(slug, title, body, headings)
        cards.append('<li><a href="'+slug+'.html">'+html.escape(title)+' <span aria-hidden="true">→</span></a></li>')
    introduction = '<p>Retrouvez les règles d’utilisation du service, les informations relatives à vos données et le cadre des échanges et des compétitions.</p>'
    result['legal.html'] = page('legal', 'Informations juridiques', introduction+'<ul class="documents">'+''.join(cards)+'</ul>')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify generated pages match their Markdown sources')
    args = parser.parse_args()
    stale = []
    for name, content in outputs().items():
        path = ROOT/name
        if args.check:
            if not path.exists() or path.read_text()!=content: stale.append(name)
        else:
            path.write_text(content)
    if stale: parser.exit(1, 'Regenerate legal pages: '+', '.join(stale)+'\n')
    print('Legal pages match their sources.' if args.check else 'Generated seven legal pages.')


if __name__ == '__main__':
    main()
