# Gombo Opportunities

Plateforme personnelle de veille remote pour les opportunites data, BI, dashboards, suivi-evaluation, developpement d'application et communication.

Le site public est publie ici :

```text
https://noetanoh.github.io/
```

Le workflow GitHub Actions `Gombo Opportunities` lance un scan chaque matin a `05:30 UTC`, genere les donnees statiques dans `data/opportunities.json`, puis met a jour le site.

## Lancer localement

```powershell
.\run.ps1
```

Puis ouvrir :

```text
http://127.0.0.1:5188
```

## Rebuild statique manuel

```powershell
python scripts/build_static_site.py
```
