#!/usr/bin/env python3
"""Construit le site : récupère la dernière version web officielle de chaque Craft App,
la dépose dans un sous-dossier, ajoute ce qui manque pour la rendre installable (PWA),
puis génère la page d'accueil.

Usage :
  python3 build.py --out _site              (télécharge les versions avec la CLI gh)
  python3 build.py --out _site --zips DIR   (utilise des zips déjà téléchargés, pour tester en local)
"""
import argparse
import datetime
import glob
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))


def latest_web_zip(repo, zips_dir, work):
    """Renvoie (version, chemin du zip) pour la dernière release de storytold/<repo>."""
    if zips_dir:
        found = sorted(glob.glob(os.path.join(zips_dir, f"{repo}-web-*.zip")))
        if not found:
            raise SystemExit(f"Zip introuvable pour {repo} dans {zips_dir}")
        path = found[-1]
        return re.search(r"-web-(.+)\.zip$", path).group(1), path
    info = json.loads(subprocess.check_output(
        ["gh", "release", "view", "-R", f"storytold/{repo}", "--json", "tagName,assets"]))
    names = [a["name"] for a in info["assets"] if re.search(r"-web-.*\.zip$", a["name"])]
    if not names:
        raise SystemExit(f"Pas de version web pour {repo} ({info['tagName']})")
    subprocess.check_call(["gh", "release", "download", info["tagName"], "-R", f"storytold/{repo}",
                           "-p", names[0], "-D", work, "--clobber"])
    return info["tagName"].lstrip("v"), os.path.join(work, names[0])


def official_icon(repo, version, dest_png):
    """Télécharge l'icône officielle de l'app (512 px) depuis son dépôt, à la version publiée.
    Renvoie False si elle est introuvable : l'icône de secours est alors générée."""
    path = f"assets/app-icon/hicolor/512x512/apps/ai.storyteller.{repo}.png"
    for ref in (f"v{version}", version, "HEAD"):
        try:
            data = subprocess.check_output(
                ["gh", "api", "-H", "Accept: application/vnd.github.raw",
                 f"repos/storytold/{repo}/contents/{path}?ref={ref}"], stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            continue
        if data.startswith(b"\x89PNG"):
            with open(dest_png, "wb") as f:
                f.write(data)
            return True
    return False


def resize_png(src, size, dest):
    from PIL import Image
    Image.open(src).convert("RGBA").resize((size, size), Image.LANCZOS).save(dest, optimize=True)


def extract(zip_path, dest):
    """Décompresse le zip en retirant son dossier racine (ex. gridcraft-web-0.13.0/)."""
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        entries = os.listdir(tmp)
        inner = os.path.join(tmp, entries[0]) if len(entries) == 1 and os.path.isdir(os.path.join(tmp, entries[0])) else tmp
        shutil.copytree(inner, dest, dirs_exist_ok=True)


def icon_svg(abbr, color):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
            f'<rect width="512" height="512" rx="112" fill="{color}"/>'
            f'<text x="256" y="256" dy=".35em" text-anchor="middle" font-family="system-ui,-apple-system,Segoe UI,sans-serif" '
            f'font-weight="700" font-size="220" fill="#fff">{html.escape(abbr)}</text></svg>')


def icon_png(abbr, color, size, path):
    """Icône PNG pour les navigateurs qui n'acceptent pas le SVG à l'installation."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=color)
    font = None
    for candidate in ["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                      "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]:
        try:
            font = ImageFont.truetype(candidate, int(size * 0.42))
            break
        except OSError:
            continue
    font = font or ImageFont.load_default(size=int(size * 0.42))
    draw.text((size / 2, size / 2), abbr, fill="white", font=font, anchor="mm")
    img.save(path)
    return True


def write_pwa(folder, name, short, color, abbr, cache_name, sw_template, root_only=False, official=None):
    """official : chemin de l'icône officielle 512 px ; sinon, icône de secours (initiales)."""
    if official:
        icons = []
        for size in (192, 512):
            resize_png(official, size, os.path.join(folder, f"icon-{size}.png"))
            icons.append({"src": f"icon-{size}.png", "sizes": f"{size}x{size}", "type": "image/png", "purpose": "any"})
    else:
        with open(os.path.join(folder, "icon.svg"), "w") as f:
            f.write(icon_svg(abbr, color))
        icons = [{"src": "icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}]
        for size in (192, 512):
            if icon_png(abbr, color, size, os.path.join(folder, f"icon-{size}.png")):
                icons.append({"src": f"icon-{size}.png", "sizes": f"{size}x{size}", "type": "image/png", "purpose": "any"})
    manifest = {"name": name, "short_name": short, "lang": "fr", "start_url": "./", "scope": "./",
                "display": "standalone", "background_color": "#16161A", "theme_color": color, "icons": icons}
    with open(os.path.join(folder, "manifest.webmanifest"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    with open(os.path.join(folder, "sw.js"), "w") as f:
        f.write(sw_template.replace("{{CACHE}}", cache_name)
                .replace("{{ROOT_ONLY}}", "true" if root_only else "false"))


def inject_pwa(index_path, color):
    """Ajoute le manifeste et l'enregistrement du service worker à la page d'une app."""
    with open(index_path, encoding="utf-8") as f:
        page = f.read()
    if 'rel="manifest"' in page:
        return False  # l'app gère déjà son mode PWA (EffectCraft)
    head = (f'<link rel="manifest" href="./manifest.webmanifest">\n'
            f'<meta name="theme-color" content="{color}">\n'
            f'<link rel="apple-touch-icon" href="./icon-192.png">\n')
    if 'rel="icon"' not in page and "rel='icon'" not in page:
        head += '<link rel="icon" href="./icon-192.png" type="image/png">\n'
    body = '<script>if ("serviceWorker" in navigator) navigator.serviceWorker.register("./sw.js");</script>\n'
    page = page.replace("</head>", head + "</head>", 1).replace("</body>", body + "</body>", 1)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(page)
    return True


def check(apps, site_url):
    """Compare les versions publiées sur le site avec les dernières versions officielles.
    Affiche « changed=true » ou « changed=false » (format GITHUB_OUTPUT)."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{site_url.rstrip('/')}/versions.json", timeout=30) as r:
            live = json.load(r)
    except Exception as error:  # site pas encore publié ou injoignable : on reconstruit
        print(f"Site injoignable ({error}) : reconstruction.", file=sys.stderr)
        live = {}
    changed = False
    listed = {a["slug"] for a in apps}
    if set(live) != listed:
        changed = True
    for app in apps:
        tag = subprocess.check_output(["gh", "release", "view", "-R", f"storytold/{app['repo']}",
                                       "--json", "tagName", "-q", ".tagName"], text=True).strip().lstrip("v")
        if live.get(app["slug"]) != tag:
            print(f"{app['name']} : {live.get(app['slug'], 'absent')} → {tag}", file=sys.stderr)
            changed = True
    print(f"changed={'true' if changed else 'false'}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="_site")
    parser.add_argument("--zips", help="dossier de zips déjà téléchargés (test local)")
    parser.add_argument("--check", metavar="URL_DU_SITE", help="vérifier seulement si une app a une nouvelle version")
    args = parser.parse_args()

    apps = json.load(open(os.path.join(ROOT, "apps.json"), encoding="utf-8"))
    if args.check:
        check(apps, args.check)
        return
    sw_template = open(os.path.join(ROOT, "template", "sw.js"), encoding="utf-8").read()
    out = os.path.abspath(args.out)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    work = tempfile.mkdtemp()
    versions = {}
    os.makedirs(os.path.join(out, "icons"))

    for app in apps:
        version, zip_path = latest_web_zip(app["repo"], args.zips, work)
        dest = os.path.join(out, app["slug"])
        extract(zip_path, dest)
        # Correctif d'emballage (PhotoCraft 0.17) : le chargeur app/*.js importe ./snippets/…
        # mais le zip ne fournit snippets/ qu'à la racine.
        app_dir, snippets = os.path.join(dest, "app"), os.path.join(dest, "snippets")
        if os.path.isdir(app_dir) and os.path.isdir(snippets) and not os.path.exists(os.path.join(app_dir, "snippets")):
            shutil.copytree(snippets, os.path.join(app_dir, "snippets"))
        official = os.path.join(work, f"{app['repo']}-512.png")
        if official_icon(app["repo"], version, official):
            resize_png(official, 96, os.path.join(out, "icons", f"{app['slug']}.png"))
            app["icon"] = f"./icons/{app['slug']}.png"
        else:
            official = None
            print(f"{app['name']} : icône officielle introuvable, icône de secours", file=sys.stderr)
        index = os.path.join(dest, "index.html")
        if inject_pwa(index, app["color"]):
            write_pwa(dest, app["name"], app["name"], app["color"], app["abbr"],
                      f"craft-{app['slug']}@{version}", sw_template, official=official)
        versions[app["slug"]] = version
        print(f"{app['name']:12} {version}")

    # Page d'accueil
    groups = []
    for app in apps:
        if app["group"] not in groups:
            groups.append(app["group"])
    cards = []
    for group in groups:
        cards.append(f'  <h2>{html.escape(group)}</h2>\n  <div class="grid">')
        for app in (a for a in apps if a["group"] == group):
            icon = (f'<img class="ico" src="{app["icon"]}" alt="" width="44" height="44">' if app.get("icon") else
                    f'<span class="ico" style="background:{app["color"]}" aria-hidden="true">{html.escape(app["abbr"])}</span>')
            cards.append(
                f'    <a class="card" href="./{app["slug"]}/">{icon}'
                f'<span><span class="name">{html.escape(app["name"])}</span> '
                f'<span class="rep">· remplace {html.escape(app["replaces"])}</span>'
                f'<span class="desc" style="display:block">{html.escape(app["desc"])}</span>'
                f'<span class="ver" style="display:block">version {html.escape(versions[app["slug"]])}</span></span></a>')
        cards.append("  </div>")
    today = datetime.date.today().strftime("%d/%m/%Y")
    page = open(os.path.join(ROOT, "template", "index.html"), encoding="utf-8").read()
    page = page.replace("{{CARDS}}", "\n".join(cards)).replace("{{DATE}}", today)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    write_pwa(out, "Craft Apps", "Craft", "#1D4ED8", "Cr", f"craft-home@{today}", sw_template, root_only=True)
    with open(os.path.join(out, "versions.json"), "w") as f:
        json.dump(versions, f, indent=2)
    open(os.path.join(out, ".nojekyll"), "w").close()
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
