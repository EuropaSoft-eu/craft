# Craft Apps Online

**https://europasoft-eu.github.io/craft/**

Les 13 Crafting Apps open source d'[ArtCraft](https://getartcraft.com) (PdfCraft, WordCraft, GridCraft, DeckCraft, PhotoCraft, LightCraft, VectorCraft, DesignCraft, FigCraft, FilmCraft, EffectCraft, SoundCraft, CADCraft), utilisables directement dans le navigateur, sans installation et sans droits administrateur. Chaque outil peut aussi être installé comme application (PWA) depuis Edge ou Chrome.

Site **non officiel**, sans lien avec ArtCraft : il sert aux postes et appareils où l'installation classique n'est pas possible. Merci à l'équipe d'ArtCraft pour son travail.

Les fichiers ouverts restent dans le navigateur : rien n'est envoyé sur un serveur.

## Fonctionnement

- Le dépôt ne contient pas les logiciels. À chaque publication, `build.py` télécharge la dernière version web officielle de chaque app depuis [github.com/storytold](https://github.com/storytold), la place dans un sous-dossier, récupère son icône officielle dans son dépôt et ajoute le manifeste et le service worker qui la rendent installable et utilisable hors connexion.
- La publication (`.github/workflows/publier.yml`) vérifie toutes les 3 heures si une app a publié une nouvelle version et, seulement dans ce cas, reconstruit et republie le site. Elle se lance aussi à chaque modification du dépôt ou à la main.
- La liste des apps est dans `apps.json`.

## Tester en local

```bash
python3 build.py --out _site
python3 -m http.server 8765 --directory _site
```

## Licences

Les Craft Apps sont © ArtCraft / storytold, sous licences Apache 2.0 et MIT ; leurs fichiers de licence, `NOTICE` et `ATTRIBUTION.md` sont publiés avec chaque app, sans modification. Les icônes sont celles des dépôts officiels, sous les mêmes licences. Seuls la page d'accueil, le mode PWA et un correctif d'emballage (PhotoCraft) sont ajoutés par EuropaSoft.
