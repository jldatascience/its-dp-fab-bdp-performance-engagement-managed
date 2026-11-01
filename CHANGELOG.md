# Changelog

Toutes les évolutions notables du dépôt `its-dp-fab-bdp-performance-engagement-managed` (configuration de déploiement,
pipelines, outillage, documentation) sont consignées ici, de la plus récente à la plus ancienne.

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Ce dépôt n'est pas versionné
par tag : chaque entrée est datée (`## AAAA-MM-JJ`). Les évolutions du socle commun sont décrites
dans le `CHANGELOG.md` de `its-dp-fab-cicd-common`, versionné par tag `vX.Y.Z`.

## 2026-10-31

### Changed

- Fichiers issus d'une copie du dépôt Framework (commit `c0f6da2`), réécrits pour le BDP
  Performance Engagement (socle `its-dp-fab-cicd-common`, tag `v1.5.0`, catégorie `bdp` ;
  références : dépôt MDS pour la dépendance Framework, dépôt UCS pour la forme et l'outillage) :
  - `CICD/pipelines/CI.yml` : template KPMG conservé (le socle n'a pas de template CI pour les
    consommateurs) ; SonarQube repris de l'ancienne CI BDP ; déclencheurs `develop`, `release/*`,
    `main` ; filtre d'artefact `"!/*.json"` (l'ancien `!**/*.json` non quoté est écarté).
  - `CICD/pipelines/CD.yml` : `repository: its-dp-fab-bdp-performance-engagement-managed`,
    `role: consumer`, source CI `its-dp-fab-bdp-performance-engagement-managed-ci`,
    `frameworkGate: ado` (Framework seul prérequis, R1), `frameworkPipelineName` en marqueur,
    coffre `frfrkvdevdp0001`, 3 service connections ARM distinctes ITG, PPR, PRD (décision du 31/10/2026).
  - `CICD/pipelines/PR-Validation.yml` : en-tête BDP, contenu inchangé.
  - `CICD/deployment/config.yml` : workspaces `FR - DP - <ENV> - FAB - BDP - Performance Engagement - MANAGED`
    pour DEV, ITG, PPR et PRD (confirmés le 31/10/2026, tiret simple) ; `item_types_in_scope` vide ;
    clé `core.parameter`, `folder_exclude_regex` et `features` retirés.
  - `CICD/deployment/dependencies.yml` : `role: consumer`, `category: bdp`, `framework.required: true`
    (workspaces Framework, `items: []`, `ado_gate`) ; connexion `DP-Fabric-Global-APR`, Variable
    Library `vl_core_config` et `guid_policy` du Framework retirés.
  - `CICD/deployment/parameter.yml` : 56 règles Framework retirées ; aucune règle ; en-tête décrivant
    les deux familles admises (workspace courant, workspace Framework par environnement).
  - `CICD/ref_dynamique/01_inventaire_github.py` à `04_recoupement.py` : repris de l'outillage UCS
    (dépôt seul, une branche, sorties hors du dépôt, activités imbriquées) et étendus au Framework :
    `02` relève aussi le workspace Framework du même environnement ; `03` propose les règles
    Framework par environnement et `framework_items_bdp.yml` ; `04` traite les références Framework
    comme légitimes et signale `FRAMEWORK_NON_DECLARE`.
  - `CICD/ref_dynamique/templates/config.yml` et `parameter.yml` : modèles BDP au format du socle
    (noms de workspaces, aucun GUID, aucune clé en minuscules).
  - `.gitignore` : remplacé par celui des dépôts MDS, Alexandrie et UCS, à l'identique
    (`.gitattributes` était déjà identique).
  - README réécrit pour le BDP ; ce journal remplace celui du Framework, copié par erreur.

### Removed

- `fabric/test.md` (contenu « test », référencé par aucun pipeline ni script ; suppression validée).

### Added

- `fabric/.gitkeep` : dossier des items suivi par Git avant la première synchronisation.

### Vérifié

- `yamllint` (règles du socle) sur `CICD/deployment` et `CICD/pipelines` : sans erreur.
- `python -m compileall CICD/ref_dynamique` : sans erreur ; syntaxe compatible Python 3.9.
- `deploy.py validate` (socle `v1.5.0`) : code 4 attendu (« Aucun item Fabric »). Sur une copie de
  travail munie d'un item fictif : 0 erreur, `repository_directory` résolu vers `fabric/`, matrice
  `bdp` acceptée.
- Scripts 01 à 04 exécutés sur le dépôt (vide) et sur un jeu d'essai hors dépôt (appel d'un
  notebook BDP, d'un pipeline Framework et d'un workspace tiers) : règles des deux familles
  acceptées par `deploy.py validate`, référence tierce écartée, aucune écriture dans le dépôt.

### À confirmer

- Organisation et service connection GitHub ; noms des 3 service connections ARM ITG, PPR et PRD (création prévue).
- Casse exacte du pipeline CI dans Azure DevOps ; nom exact de la CD Framework.
- Types d'items, règles, `framework.items`, connexions Fabric, Variable Libraries, `guid_policy` et
  `data_dependencies`, après synchronisation Git Integration.
- Point V-01 : le filtre `contents: "!/*.json"` de l'artefact CI ne doit pas exclure les fichiers d'items.
