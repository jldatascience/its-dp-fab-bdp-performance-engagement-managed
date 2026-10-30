# its-dp-fab-item-framework-managed — Framework

Dépôt GitHub des items Microsoft Fabric du workspace **Framework**, et de leur configuration de déploiement. Le workspace Framework est le workspace mutualisé des « fonctions sur étagère » : des pipelines et notebooks communs (chargement, journalisation) que les Data Products appellent.

Ce dépôt ne contient **aucun code de déploiement**. Il décrit *quoi* déployer et *où*. La logique (contrôles, publication, vérification, rapport) se trouve dans le dépôt socle commun `its-dp-fab-cicd-common`, appelé par le tag `v1.5.0`.

| Rubrique | Valeur |
|---|---|
| Catégorie | `framework` |
| Workspaces | `FR - DP - <ENV> - FAB - Framework - MANAGED` (DEV, ITG, PPR, PRD) |
| Branches | `develop` (par défaut) · `release/*` · `main` |
| Pipelines Azure DevOps | CI : `its-dp-fab-item-framework-managed-CI` · CD : à créer depuis `CICD/pipelines/CD.yml`, nom attendu `its-dp-fab-item-framework-managed-cd` · validation de PR : à créer depuis `CICD/pipelines/PR-Validation.yml` |
| Socle commun | `its-dp-fab-cicd-common`, tag `v1.5.0` |
| Statut d'inventaire | `pending` : la CD refuse toute publication tant que l'inventaire n'est pas validé sur la branche réelle |

Ne pas confondre ce dépôt avec le **core framework** : c'est le dépôt du code Python/PySpark, qui produit des wheels publiés dans Azure Artifacts et n'est relié à aucun workspace. Ce dépôt-ci ne contient que les **items Fabric** du workspace Framework.

## Dépendances

**Aucun prérequis de déploiement.**

- Le Framework est déployé en premier quand il est absent d'un environnement. Il n'est **pas redéployé systématiquement** quand un Data Product change.
- Sa CD n'a **aucune porte** : le rapport indique `GATE_NOT_APPLICABLE`.
- Il ne référence aucun autre workspace. Ses 56 règles `parameter.yml` visent toutes le **workspace courant** (`_ALL_`), car chaque pipeline appelle un item du même workspace.

**Il est le seul prérequis des ADP et des BDP.** Avant de déployer, la CD d'un ADP ou d'un BDP vérifie que le Framework est **disponible** sur l'environnement cible :
- le workspace Framework existe ;
- les items Framework que l'ADP ou le BDP utilise sont présents ;
- le **dernier** stage `Deploy_<ENV>` de cette CD Framework a réussi, et aucun déploiement n'est en cours.

Conséquences pratiques pour ce dépôt :
- **Le nom de la CD Framework dans Azure DevOps doit rester celui attendu par les autres dépôts** (`its-dp-fab-item-framework-managed-cd`, à confirmer).
- **L'historique des runs de cette CD doit être conservé** : vérifier la rétention, ou poser un retention lease sur le dernier run réussi par environnement.
- **Un Framework en cours de déploiement ou en échec sur un environnement bloque les ADP et BDP de cet environnement** jusqu'au prochain run réussi.
- **Ne jamais supprimer puis recréer un item appelé par un Data Product.** Un item recréé change d'ID, et les ADP et BDP déjà déployés pointeraient vers l'ancien. Une mise à jour normale conserve l'ID.

| Item Framework | Appelé par |
|---|---|
| `pl_get_ws_lh_ids` | ADP MDS (`pl_master_load`) |
| `log_sequence_start`, `log_sequence_ok`, `log_sequence_ko` | ADP MDS (`pl_master_load`) |
| `pl_load_object` | ADP MDS (`pl_load_tables`) |
| Autres items | Usages des autres ADP et BDP à inventorier |

Connexion Fabric déclarée dans `CICD/deployment/dependencies.yml` et vérifiée au pré-vol : `DP-Fabric-Global-APR` (connexion « Fabric Data Pipelines » des activités InvokePipeline, nom exact à confirmer).

## Arborescence

```text
its-dp-fab-item-framework-managed/         branches develop (défaut) · release/* · main
│
├── CHANGELOG.md                         # journal des changements du dépôt (entrées datées)
├── README.md                            # ce fichier
│
│  ── Déploiement (lu par Azure DevOps, jamais publié dans Fabric) ──
├── CICD/
│   ├── pipelines/
│   │   ├── CI.yml                       # pipeline ADO its-dp-fab-item-framework-managed-CI
│   │   ├── CD.yml                       # pipeline ADO de CD → CICD/pipelines/templates/cd-pipeline.yml@cicd_common
│   │   └── PR-Validation.yml            # check obligatoire des PR → CICD/pipelines/templates/validate-pipeline.yml@cicd_common
│   ├── deployment/
│   │   ├── config.yml                   # workspaces « FR - DP - <ENV> - FAB - Framework - MANAGED »,
│   │   │                                #   repository_directory: "../../fabric", types, exclusions
│   │   ├── parameter.yml                # 56 règles (28 activités) : $workspace.$id / $items…
│   │   └── dependencies.yml             # category framework : aucun prérequis ; data_dependencies,
│   │                                    #   connexions, politique des GUID
│   └── ref_dynamique/                   # inventaire des références (01_… à 04_….py, lancés depuis ce dossier)
│       ├── README_resultats_inventaire_framework.md
│       └── templates/                   #   modèles config.yml / parameter.yml (solution temporaire DEV)
│
│  ── Contenu du workspace Framework (Git Integration DEV + publication fabric-cicd) ──
└── fabric/
    ├── Flux/
    │   ├── 30b76367-6f62-88fd-40ca-0a7a289c3fee.DataPipeline/   # pl_src_to_stg
    │   ├── 4918bdb7-c84c-8844-455f-f9d2c6c0d5fc.DataPipeline/   # pl_run_table
    │   ├── 4adc1b70-a524-b462-44de-afca42c73be5.Notebook/       # nb_run_table
    │   ├── 713e3adf-9d79-b741-4191-8fa01a236557.DataPipeline/   # pl_stg_to_str
    │   ├── 75ffc0fd-5ffb-8f5b-4fcd-4cfa1cb7b46f.DataPipeline/   # pl_src_to_arc
    │   └── old/                              # EXCLU (5 items *_v1)
    ├── Log_load/
    │   ├── log_load_end_ko.DataPipeline/
    │   ├── log_load_end_ok.DataPipeline/
    │   ├── log_load_start.DataPipeline/
    │   ├── nb_log_load_end_ko.Notebook/
    │   ├── nb_log_load_end_ok.Notebook/
    │   └── nb_log_load_start.Notebook/
    ├── Log_processing/
    │   ├── Old_processing/                   # EXCLU (6 items *_v1)
    │   ├── log_processing_end_ko.DataPipeline/
    │   ├── log_processing_end_ok.DataPipeline/
    │   ├── log_processing_start.DataPipeline/
    │   ├── nb_log_processing_end_ko.Notebook/
    │   ├── nb_log_processing_end_ok.Notebook/
    │   └── nb_log_processing_start.Notebook/
    ├── Log_sequence/
    │   ├── Old_sequence/                     # EXCLU (6 items *_v1)
    │   ├── log_sequence_ko.DataPipeline/     # invoqué par ADP MDS
    │   ├── log_sequence_ok.DataPipeline/     # invoqué par ADP MDS
    │   ├── log_sequence_start.DataPipeline/  # invoqué par ADP MDS
    │   ├── nb_log_sequence_end_ko.Notebook/
    │   ├── nb_log_sequence_end_ok.Notebook/
    │   └── nb_log_sequence_start.Notebook/
    ├── Testing_notebook.Notebook/
    │   ├── .platform
    │   └── notebook-content.py
    ├── Tests_Intégration/                    # EXCLU
    │   ├── integration_scd2.Notebook/
    │   └── testing_notebook Copy.Notebook/
    ├── env_spark.Environment/
    │   ├── .platform
    │   ├── Libraries/
    │   └── Setting/
    ├── env_spark_new.Environment/
    │   ├── .platform
    │   ├── Libraries/
    │   └── Setting/
    ├── nb_generate_dso_views_loop.Notebook/
    │   ├── .platform
    │   └── notebook-content.py
    ├── nb_view_generator.Notebook/
    │   ├── .platform
    │   └── notebook-content.py
    ├── pipelines/                            # fichiers YAML, aucun item Fabric
    │   ├── ci.yml
    │   └── ci_v2.yml
    ├── pl_load_object.DataPipeline/          # invoqué par ADP MDS (pl_load_tables)
    │   ├── .platform
    │   └── pipeline-content.json
    ├── pl_load_object_v1.DataPipeline/
    │   ├── .platform
    │   └── pipeline-content.json
    └── test.md
```

Cette arborescence reflète le contenu du dépôt au 29/10/2026 (`find fabric -maxdepth 2 | sort`), et non l'inventaire du MODOP. Les noms sont ceux du disque. Les items de `Flux/` sont rangés dans des dossiers nommés par GUID : leur nom affiché, lu dans `.platform`, figure en commentaire. Cités par le MODOP mais absents du dépôt à cette date : `pl_get_ws_lh_ids`, `nb_get_ws_lh_ids`, `vl_core_config`, `env_dev`.

`repository_directory` est résolu **relativement au dossier de `config.yml`** (`CICD/deployment/`), par fabric-cicd 1.4.0 comme par le socle : `"../../fabric"` désigne le dossier `fabric/` à la racine du dépôt.

## Exclusions (`CICD/deployment/config.yml`)

```yaml
item_types_in_scope: [VariableLibrary, Notebook, DataPipeline, Environment]
folder_exclude_regex: "^/(Tests_|Flux/old|Log_processing/Old_processing|Log_sequence/Old_sequence|To_delete)"
features: [enable_experimental_features, enable_exclude_folder]
```

- Les chemins sont relatifs à `fabric/`. Les dossiers exclus restent dans Git mais ne sont **jamais déployés** :
  - `Tests_Intégration/` (motif `Tests_`) ;
  - `Flux/old/` ;
  - `Log_processing/Old_processing/` ;
  - `Log_sequence/Old_sequence/` ;
  - `To_delete/`.
- `folder_exclude_regex` ne fonctionne qu'avec les deux feature flags ci-dessus.
- Aucune suppression automatique : `unpublish` est désactivé sur les 4 environnements. Supprimer un item en ITG, PPR ou PRD reste une action manuelle validée, après avoir vérifié qu'aucun ADP ou BDP ne l'appelle.

## `parameter.yml` : références internes

Les 28 activités InvokePipeline et Notebook des pipelines du Framework donnent 56 règles : pour chaque activité, une règle pour le workspace et une pour l'item appelé. Toutes visent le workspace courant :

```yaml
- find_key: $.properties.activities[?(@.name=="nb_get_ws_lh_ids")].typeProperties.workspaceId
  replace_value: { _ALL_: "$workspace.$id" }
  item_type: DataPipeline
  item_name: pl_get_ws_lh_ids
- find_key: $.properties.activities[?(@.name=="nb_get_ws_lh_ids")].typeProperties.notebookId
  replace_value: { _ALL_: "$items.Notebook.nb_get_ws_lh_ids.$id" }
  item_type: DataPipeline
  item_name: pl_get_ws_lh_ids
```

Au déploiement, fabric-cicd remplace les GUID de DEV par les ID du workspace Framework de l'environnement cible. La vérification après publication relit chaque référence et s'assure qu'aucun GUID de DEV ne reste.

## Fichiers par type d'item

Chaque item est un dossier `<nom>.<Type>/`. Il contient toujours `.platform` (type, nom affiché, identifiant logique) et ses fichiers de définition.

| Type | Fichiers de définition | Déployé |
|---|---|---|
| DataPipeline | `pipeline-content.json` | Oui |
| Notebook | `notebook-content.py` | Oui |
| VariableLibrary | `variables.json`, `settings.json`, `valueSets/<value set>.json` | Oui (jeu de valeurs actif vérifié : `ITG` en ITG, etc.) |
| Environment | `Setting/Sparkcompute.yml`, `Libraries/…` (si bibliothèques) | Oui |

## Branches et déploiement

| Branche | Rôle | Déploiement | Réglage |
|---|---|---|---|
| `feature/*` | Développement | Aucun | PR vers `develop` |
| `develop` | Branche par défaut ; intégration des features | DEV par Git Integration ; ITG par la CD | Protégée ; workspace DEV connecté à `develop`, dossier Git `fabric` |
| `release/*` | Une branche par release (lot de features), créée depuis `develop` au besoin | PPR par la CD, après approbation | Protégée (PR obligatoire, check PR-Validation) |
| `main` | Reflet de la production | PRD par la CD, après approbation | Protégée (PR obligatoire depuis `release/*`) |

Un run de CD ne déploie qu'**un seul environnement** : celui de la branche d'où vient l'artefact CI. Toute autre branche est refusée. La porte des ADP et BDP lit l'historique de cette CD **sur la même branche** : `develop` pour ITG, `release/*` pour PPR, `main` pour PRD.

## Déroulement de la chaîne

1. **Pull Request** vers `develop`, `release/*` ou `main` : `PR-Validation.yml` exécute les contrôles bloquants du socle. Ces contrôles portent sur :
   - la syntaxe YAML et le JSON des items ;
   - `config.yml` et `parameter.yml`, validés par fabric-cicd ;
   - les 56 règles (aucune sans effet) ;
   - les GUID en dur et les secrets en clair ;
   - la matrice de dépendances.

   Un check rouge empêche la fusion.
2. **Fusion** : `CI.yml` (template KPMG) calcule la version, lance SonarQube et publie l'artefact `fabric`.
3. **CD** (`CD.yml` → socle), stage `Validate_Artifact` : calcul de l'environnement cible selon la branche, contrôles rejoués sur l'artefact, empreinte SHA-256.
4. **Environment ADO** `fabric-<env>` : approbation (PPR, PRD), verrou, branche autorisée, template obligatoire.
5. **Stage `Deploy_<ENV>`** :
   - intégrité de l'artefact ;
   - secrets de l'environnement lus dans `frfrkvdevdp0001` ;
   - pré-vol Fabric (workspace, capacité, connexions, références).

   Il n'y a **pas de porte** pour le Framework.
6. **Publication** par fabric-cicd : les items sont créés ou mis à jour dans le workspace cible, **sans changer leur ID**, avec les références internes remplacées.
7. **Vérification après publication** : les items, les références et le jeu de valeurs actif de `vl_core_config` sont relus ; aucun GUID de DEV ne doit rester.
8. **Rapport de déploiement** `deployment-report-<ENV>`, en JSON et Markdown, publié dans le run ADO, même en cas d'échec. Un run vert devient la référence que liront les portes des ADP et BDP de cet environnement.

La CD déploie des **définitions d'items** : elle n'exécute aucun pipeline et ne charge aucune donnée.

## Contribuer

1. Travailler dans le workspace Framework DEV, puis enregistrer sur une branche `feature/*` (Source control de Fabric).
2. Pour toute nouvelle activité InvokePipeline ou Notebook, ajouter ses deux règles (workspace + item) dans `CICD/deployment/parameter.yml`, en `_ALL_` vers le workspace courant.
3. Avant de **renommer ou supprimer** un item, vérifier qu'aucun ADP ou BDP ne l'appelle :
   - chercher son nom dans `framework.items` de leurs `dependencies.yml` ;
   - chercher les références `$workspace…Framework…` dans leurs `parameter.yml`.

   Sinon leur pré-vol échouera (`PRE_FRAMEWORK_ITEM`, `PRE_REF_ITEM`).
4. Les anciennes versions vont dans un dossier exclu (`old/`, `Old_*`, `To_delete/`), pas à la racine de `fabric/`.
5. Ouvrir une PR vers `develop` et corriger jusqu'à ce que le check PR-Validation soit vert.

Pour contrôler le dépôt en local, à partir d'un clone du socle :

```bash
python ../its-dp-fab-cicd-common/CICD/tools/deploy.py validate --repo .
```

## Ce qui ne doit pas figurer dans ce dépôt

| Élément | Pourquoi |
|---|---|
| `.github/workflows/CI.yml`, `.github/workflows/CD.yml` | Remplacés par `CI.yml`, `CD.yml` et `PR-Validation.yml` sous `CICD/pipelines/` (pipelines Azure DevOps) |
| `deploy.py` dans `deployment/` ou `CICD/deployment/` | Remplacé par `CICD/tools/deploy.py` du socle (l'ancien script contenait des ID en dur) |
| `check_connection.py` dans `deployment/` ou `CICD/deployment/` (si présent) | Contrôle des connexions intégré au pré-vol du socle |
| `fabric/pipelines/ci.yml`, `fabric/pipelines/ci_v2.yml` | Anciens pipelines ADO, remplacés par `CICD/pipelines/CI.yml` (encore présents : à retirer) |
| Items à la racine du dépôt | Déplacés sous `fabric/` |
| Code Python/PySpark du core framework | Dépôt séparé (wheels publiés dans Azure Artifacts) |

## Avant le premier déploiement

- [ ] Remplacer les marqueurs de `CICD/pipelines/CD.yml` et `CICD/pipelines/PR-Validation.yml` :
  - `__A_RELEVER__` : organisation et service connection GitHub ;
  - `__A_CONFIRMER_SERVICE_CONNECTION_ARM_<ENV>__` : une service connection Azure Resource Manager distincte par environnement, créée par Ops en fédération d'identité, autorisée à lire les 3 secrets de son environnement dans le coffre unique `frfrkvdevdp0001`.
- [x] Items sous `fabric/` et `repository_directory` à `"../../fabric"` dans `CICD/deployment/config.yml`.
- [ ] Rediriger la Git Integration du workspace DEV vers le dossier `fabric`.
- [ ] Lancer `deploy.py validate` sur la branche réelle et confirmer le dossier des notebooks `nb_log_*`.
- [x] Noms des workspaces PPR et PRD confirmés le 22/10/2026 : `FR - DP - PPR - FAB - Framework - MANAGED`, `FR - DP - PRD - FAB - Framework - MANAGED`.
- [ ] Passer `inventory_status` à `validated` dans une PR revue.
- [ ] Créer la CD sous le nom attendu par les autres dépôts, et accorder au service de build le droit « View builds » sur cette définition (lu par les portes des ADP et BDP).
- [ ] Faire un **premier run de cette nouvelle CD sur chaque environnement** avant de basculer les ADP et BDP. Un Framework publié par l'ancienne CD est bien présent dans Fabric, mais la porte ne le voit pas (`GATE_NEVER_DEPLOYED`).
