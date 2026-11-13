# Agent Instagram Élan Français

Publie automatiquement les Reels, carrousels et stories de `schedule.json` sur @learnfrenchwith_elanfrancais.

- `docs/` : les fichiers (servis par GitHub Pages, qu'Instagram vient chercher).
- `schedule.json` : quoi publier, et quand (heure de l'Inde).
- `published.json` : ce qui a déjà été publié (mis à jour par l'agent).
- `.github/workflows/publish.yml` : se lance toutes les 10 minutes.

Secrets à créer (Settings › Secrets and variables › Actions) : `IG_TOKEN`, `IG_USER_ID`.
Test sans publier : onglet Actions › « Publier sur Instagram » › Run workflow › mode `check`.
Mettre en pause : Actions › « Publier sur Instagram » › ⋯ › Disable workflow.
