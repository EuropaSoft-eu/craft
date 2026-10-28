# Craft Apps dans le navigateur

**https://europasoft-eu.github.io/craft/**

Les 13 Crafting Apps open source d'[ArtCraft](https://getartcraft.com) (PdfCraft, WordCraft, GridCraft, DeckCraft, PhotoCraft, LightCraft, VectorCraft, DesignCraft, FigCraft, FilmCraft, EffectCraft, SoundCraft, CADCraft), utilisables directement dans le navigateur, sans installation et sans droits administrateur. Chaque outil peut aussi être installé comme application (PWA) depuis Edge ou Chrome.

Les fichiers ouverts restent dans le navigateur : rien n'est envoyé sur un serveur.

## Fonctionnement

- Le dépôt ne contient pas les logiciels. À chaque publication, `build.py` télécharge la dernière version web officielle de chaque app depuis [github.com/storytold](https://github.com/storytold), la place dans un sous-dossier et ajoute le manifeste et le service worker qui la rendent installable et utilisable hors connexion.
- La publication (`.github/workflows/publier.yml`) se lance à chaque modification et automatiquement chaque lundi : le site suit les nouvelles versions sans intervention.
- La liste des apps est dans `apps.json`.

## Tester en local

```bash
python3 build.py --out _site
python3 -m http.server 8765 --directory _site
```

## Licences

Les Craft Apps sont © ArtCraft / storytold, sous licences Apache 2.0 et MIT ; leurs fichiers de licence, `NOTICE` et `ATTRIBUTION.md` sont publiés avec chaque app, sans modification. Seuls la page d'accueil, le mode PWA et un correctif d'emballage (PhotoCraft) sont ajoutés par EuropaSoft.
