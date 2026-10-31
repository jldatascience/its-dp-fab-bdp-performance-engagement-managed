# its-dp-fab-bdp-performance-engagement-managed — BDP Performance Engagement

Dépôt GitHub des items Microsoft Fabric du workspace **BDP Performance Engagement**, et de leur configuration de déploiement. Un BDP (*business data product*) s'appuie sur les fonctions mutualisées du Framework, qui est son **unique prérequis de déploiement**.

Ce dépôt ne contient **aucun code de déploiement**. Il décrit *quoi* déployer et *où*. La logique (contrôles, publication, vérification, rapport) se trouve dans le dépôt socle commun `its-dp-fab-cicd-common`, appelé par le tag `v1.5.0`.

> **État au 31/10/2026 : le dépôt ne contient encore aucun item Fabric, et rien n'est déployable.**
> `fabric/` ne contient que `.gitkeep`. `deploy.py validate` s'arrête en code 4 (« Aucun item Fabric ») avant les contrôles statiques, et la CD refuserait de toute façon toute publication (`inventory_status: pending`, marqueurs à relever).

| Rubrique | Valeur |
|---|---|
| Catégorie | `bdp` ; rôle `consumer` dans le socle |
| Workspaces | `FR - DP - <ENV> - FAB - BDP - Performance Engagement - MANAGED` (DEV, ITG, PPR, PRD, confirmés le 31/10/2026, tiret simple) |
| Prérequis de déploiement | Framework : `FR - DP - <ENV> - FAB - Framework - MANAGED` |
| Branches | `develop` (par défaut) · `release/*` · `main` |
| Pipelines Azure DevOps | CI : `its-dp-fab-bdp-performance-engagement-managed-ci` (nom repris de l'ancienne CD, casse à confirmer) · CD : à créer depuis `CICD/pipelines/CD.yml` · validation de PR : à créer depuis `CICD/pipelines/PR-Validation.yml` |
| Socle commun | `its-dp-fab-cicd-common`, tag `v1.5.0` |
| Statut d'inventaire | `pending` : la CD refuse toute publication tant que l'inventaire n'est pas validé sur la branche réelle |

## Dépendances

**Prérequis de déploiement unique : le Framework** (`its-dp-fab-item-framework-managed`), matrice v1.3 du socle, règles R1 à R4.

- Avant chaque déploiement sur ITG, PPR ou PRD, la CD vérifie que le Framework est **disponible** sur cet environnement :
  - le workspace Framework de l'environnement existe (pré-vol, `PRE_FRAMEWORK_WORKSPACE`) ;
  - les items Framework utilisés par Performance Engagement sont présents (pré-vol, `PRE_FRAMEWORK_ITEM`). Ils sont à déclarer dans `framework.items`, aujourd'hui vide ;
  - le dernier stage `Deploy_<ENV>` de la CD Framework a réussi et aucun n'est en cours (porte Azure DevOps). La porte lit l'historique **sur la même branche** : `develop` pour ITG, `release/*` pour PPR, `main` pour PRD.
- Tant que la **nouvelle** CD Framework n'a pas tourné au moins une fois sur l'environnement visé, la porte renvoie `GATE_NEVER_DEPLOYED`. Un Framework publié par l'ancienne CD est présent dans Fabric, mais il est invisible pour la porte.
- La CD **n'exige jamais de redéployer le Framework** : s'il est déjà disponible, le BDP se déploie immédiatement.
- **Aucune dépendance vers les ADP ni vers les autres BDP** : ordre libre, déploiement possible en parallèle (R3, R4).
- Une **consommation de données** d'un autre Data Product se résout à l'exécution (shortcut, Variable Library) et se déclare dans `data_dependencies` : documentaire, jamais bloquante (R6).

| Nature de dépendance | Déclarée où | Bloquante | État au 31/10/2026 |
|---|---|---|---|
| Déploiement : Framework | `framework` (`required: true`, workspaces, items, `ado_gate`) et `frameworkGate: ado` dans `CD.yml` | Oui (pré-vol + porte) | Workspaces renseignés ; items et nom de la CD Framework à relever |
| Déploiement : ADP, BDP, UCS | — (interdite) | — | Aucune |
| Données, technique, exécution | `data_dependencies` | Non | Aucune confirmée |
| Connexions Fabric | `connections` (vérifiées au pré-vol) | Oui, au pré-vol | À relever |
| Variable Libraries | `variable_libraries` | Oui, après publication | À relever |

| Item Framework utilisé | Appelé depuis |
|---|---|
| À relever à l'inventaire (`03_remplir.py` → `framework_items_bdp.yml`) | — |

## Arborescence

```text
its-dp-fab-bdp-performance-engagement-managed/   branches develop (défaut) · release/* · main
│
├── .gitattributes                       # normalisation des fins de ligne (identique aux autres dépôts)
├── .gitignore                           # identique aux dépôts MDS, Alexandrie et UCS
├── CHANGELOG.md                         # journal des changements du dépôt (entrées datées)
├── README.md                            # ce fichier
│
│  ── Déploiement (lu par Azure DevOps, jamais publié dans Fabric) ──
├── CICD/
│   ├── deployment/
│   │   ├── config.yml                   # workspaces BDP DEV, ITG, PPR, PRD (confirmés),
│   │   │                                #   repository_directory: "../../fabric", types (vide)
│   │   ├── dependencies.yml             # category bdp : Framework seul prérequis (workspaces, porte ADO),
│   │   │                                #   items, connexions, Variable Libraries, guid_policy à relever
│   │   └── parameter.yml                # aucune règle (en-tête : les deux familles admises)
│   ├── pipelines/
│   │   ├── CD.yml                       # pipeline ADO de CD → CICD/pipelines/templates/cd-pipeline.yml@cicd_common
│   │   ├── CI.yml                       # pipeline ADO de CI (template KPMG) : version, SonarQube, artefact « fabric »
│   │   └── PR-Validation.yml            # check obligatoire des PR → CICD/pipelines/templates/validate-pipeline.yml@cicd_common
│   └── ref_dynamique/                   # référencement dynamique : inventaire et proposition de règles
│       ├── templates/
│       │   ├── config.yml               #   modèle de config.yml (noms de workspaces, types)
│       │   └── parameter.yml            #   modèle de parameter.yml (règles BDP + Framework)
│       ├── 01_inventaire_github.py      # inventaire Git (une branche)
│       ├── 02_fab_cli.py                # inventaire Fabric d'un environnement : BDP + Framework (Fabric CLI)
│       ├── 03_remplir.py                # rendu des modèles et de framework.items, hors dépôt
│       └── 04_recoupement.py            # recoupement Git × Fabric × parameter.yml × dependencies.yml
│
│  ── Contenu du workspace BDP (Git Integration DEV + publication fabric-cicd) ──
└── fabric/
    └── .gitkeep                         # fichier vide de maintien du dossier (aucun item Fabric)
```

`CICD/pipelines/templates/` n'existe **pas** dans ce dépôt : les chemins `CICD/pipelines/templates/*.yml@cicd_common` désignent les templates du socle.

`repository_directory` est résolu **relativement au dossier de `config.yml`** (`CICD/deployment/`), par fabric-cicd 1.4.0 comme par le socle : `"../../fabric"` désigne le dossier `fabric/` à la racine du dépôt.

`fabric/.gitkeep` est un fichier vide qui maintient le dossier dans Git tant qu'aucun item n'est synchronisé (Git ne suit pas les dossiers vides). Il remplace `fabric/test.md` (contenu « test », référencé nulle part), avec validation le 31/10/2026. Il n'est pas un item Fabric : le socle et fabric-cicd ne découvrent que les dossiers munis d'un `.platform`.

## Pipelines

### `CI.yml`

- Template KPMG `PipelineTemplate.yaml@CICD` (dépôt « Plateforme Technologique/CICD ») **conservé** : le socle v1.5.0 ne fournit aucun template CI pour les consommateurs.
- Déclencheurs : `develop`, `release/*`, `main` (et non plus la branche `feature/its/1_fabric_item_synchronization`).
- SonarQube : projet `Discovery_DP-FAB-BDP-Performance-Engagement-Managed`, repris de l'ancienne CI.
- Artefact `fabric` : copie du dépôt (sous-dossier `binaries`, lu par la CD), filtre `contents: "!/*.json"` aligné sur les autres dépôts. L'ancien filtre `!**/*.json` non quoté était une étiquette YAML et, comme motif, aurait exclu tous les JSON des items. Point V-01 à vérifier au premier run.

### `CD.yml`

- `extends` du template `CICD/pipelines/templates/cd-pipeline.yml@cicd_common`, tag `v1.5.0`.
- `repository: its-dp-fab-bdp-performance-engagement-managed`, `role: consumer` (le template n'accepte que `framework` ou `consumer`).
- `devMode: skip` : aucun stage DEV.
- `frameworkGate: ado` : porte Framework à chaque stage. `frameworkPipelineName` reste un marqueur tant que le nom exact de la CD Framework n'est pas confirmé (`GATE_PIPELINE`).
- Un run ne déploie qu'**un seul environnement**, celui de la branche source de l'artefact CI : `develop` → ITG, `release/*` → PPR, `main` → PRD. Toute autre branche est refusée.
- Stages : `Validate_Artifact` (route, contrôles statiques rejoués, empreinte SHA-256), puis `Deploy_<ENV>` : intégrité de l'artefact, secrets lus dans le coffre, pré-vol Fabric (workspace, Framework, connexions, références), porte Framework, publication fabric-cicd, vérification après publication, rapport `deployment-report-<ENV>`.
- Approbations PPR et PRD : Environments ADO `fabric-ppr` et `fabric-prd` (Approvals and checks), pas dans le YAML.

### `PR-Validation.yml`

- `extends` du template `CICD/pipelines/templates/validate-pipeline.yml@cicd_common`, sans paramètre (`cicdRoot: CICD` par défaut).
- Contrôles bloquants, sans accès au tenant ni secret :
  - `yamllint` de `CICD/deployment` et `CICD/pipelines` ;
  - `deploy.py validate` : structure, JSON des items, `config.yml` et `parameter.yml` validés par fabric-cicd, règles sans effet, GUID en dur, secrets, matrice de dépendances.
- Les scripts de `CICD/ref_dynamique/` ne sont pas contrôlés par ce template.
- À déclarer comme *Required status check* sur `develop`, `release/*` et `main`. **Le check sera rouge tant que `fabric/` ne contient aucun item** (attendu).

## Configuration de déploiement

### `config.yml`

```yaml
core:
  workspace:
    DEV: "FR - DP - DEV - FAB - BDP - Performance Engagement - MANAGED"
    ITG: "FR - DP - ITG - FAB - BDP - Performance Engagement - MANAGED"
    PPR: "FR - DP - PPR - FAB - BDP - Performance Engagement - MANAGED"
    PRD: "FR - DP - PRD - FAB - BDP - Performance Engagement - MANAGED"
  repository_directory: "../../fabric"
  item_types_in_scope: []
```

- Workspaces désignés par leur **nom exact** (le socle refuse `workspace_id`), avec le tiret simple `-` partout : le pré-vol compare les noms caractère par caractère.
- `item_types_in_scope` est **vide** car aucun item n'existe : la liste se remplit uniquement avec les types relevés dans les `.platform` de `fabric/`. Vide, elle est bloquante (voulu) ; ne pas retirer la clé, sinon fabric-cicd publierait tous les types.
- Clé `parameter` absente tant que `parameter.yml` n'a aucune règle.
- `publish.skip` à `false` partout : DEV est exclu par la CD (`devMode: skip`), pas par fabric-cicd. `unpublish.skip` à `true` partout : aucune suppression automatique d'items orphelins.

### `dependencies.yml`

`schema_version: 1`, `role: consumer`, `category: bdp`, `inventory_status: pending`.

- `framework.required: true`, avec les 4 workspaces Framework, `items: []` (avertissement `DEPS_FRAMEWORK_ITEMS` en `pending`, bloquant une fois `validated`) et `ado_gate` (branches `develop`, `release/*`, `main`, préfixe `Deploy_`).
- `data_dependencies`, `connections`, `variable_libraries` et `guid_policy` sont vides et à relever à l'inventaire. La connexion `DP-Fabric-Global-APR` et la Variable Library `vl_core_config` du Framework ne sont pas reprises sans preuve d'usage par un item BDP.

### `parameter.yml`

Aucune règle. Les 56 règles du Framework ne s'appliquent pas à ce dépôt. Deux familles de règles sont admises, pour chaque activité InvokePipeline ou TridentNotebook :

```yaml
# 1. Item du workspace courant (BDP)
- find_key: $.properties.activities[?(@.name=="<activité>")].typeProperties.workspaceId
  replace_value: {_ALL_: "$workspace.$id"}
  item_type: DataPipeline
  item_name: <pipeline appelant>
# 2. Item du Framework de l'environnement cible (par nom, une clé par environnement)
- find_key: $.properties.activities[?(@.name=="<activité>")].typeProperties.pipelineId
  replace_value:
    DEV: "$workspace.FR - DP - DEV - FAB - Framework - MANAGED.$items.DataPipeline.<nom>.$id"
    ITG: "$workspace.FR - DP - ITG - FAB - Framework - MANAGED.$items.DataPipeline.<nom>.$id"
    PPR: "$workspace.FR - DP - PPR - FAB - Framework - MANAGED.$items.DataPipeline.<nom>.$id"
    PRD: "$workspace.FR - DP - PRD - FAB - Framework - MANAGED.$items.DataPipeline.<nom>.$id"
  item_type: DataPipeline
  item_name: <pipeline appelant>
```

Tout item Framework visé doit figurer dans `framework.items` (`DEPS_FRAMEWORK_ITEM_UNDECLARED`). Toute autre référence inter-workspace est refusée (`DEPS_CROSS_WORKSPACE_FORBIDDEN`). Aucun GUID littéral.

## Référencement dynamique (`CICD/ref_dynamique/`)

Les items synchronisés par Git Integration contiennent les GUID de leur workspace d'origine et ceux du Framework DEV. Les règles de `parameter.yml` les remplacent, au déploiement, par les ID du workspace BDP et du workspace Framework de l'environnement cible. Les quatre scripts aident à établir ces règles. Ils sont **en lecture seule** : ils n'écrivent rien dans le dépôt ni dans Fabric.

| Script | Lit | Produit (hors dépôt) |
|---|---|---|
| `01_inventaire_github.py` | une branche Git (défaut `feature/its/411581_industrialisation_chaine_cicd`, sans checkout ni fusion de branches) | `inventaire_bdp.json`, `activites_bdp.csv`, `toutes_refs_bdp.csv` |
| `02_fab_cli.py` | le workspace BDP **et** le workspace Framework d'un environnement via Fabric CLI (`--env`, défaut ITG ; `--workspace`, `--workspace-id`, `--sans-framework`) | `fabric_<ENV>.json`, `activites_fabric_<ENV>.csv` |
| `03_remplir.py` | sorties 01 et 02, `templates/`, `dependencies.yml` | `config.rendu.yml`, `parameter.rendu.yml`, `diff_*.txt`, `framework_items_bdp.yml`, `references_non_converties_bdp.csv` |
| `04_recoupement.py` | sorties 01 et 02, `CICD/deployment/parameter.yml` (ou `--parameter`), `dependencies.yml` | `recoupement_bdp.csv`, `rapport_recoupement_bdp.md` |

- **Dossier de sortie** : `--out`, sinon la variable `REF_DYN_OUT`, sinon `<dossier temporaire système>/ref_dynamique/its-dp-fab-bdp-performance-engagement-managed`. Un dossier situé dans le dépôt est refusé. Aucun dossier `sortie/` n'est créé.
- `03_remplir.py` ne propose que des règles **justifiées** : activité relevée dans Git, item appelé identifié dans l'inventaire Fabric BDP (et présent sous `fabric/`) ou dans l'inventaire Framework du même environnement. Les références vers un autre workspace ou non identifiées sont listées, jamais converties.
- `04_recoupement.py` traite les références au Framework comme **légitimes** et classe les constats : `COUVERTE`, `NON_COUVERTE`, `GUID_INCONNU`, `REGLE_INUTILE`, `REFERENCE_OBSOLETE`, `INCOHERENCE_WORKSPACE`, `INCOHERENCE_TYPE`, `FRAMEWORK_NON_DECLARE` (code retour 1 s'il reste un constat bloquant).
- Les fichiers produits contiennent des ID Fabric, **jamais de secret**.

Enchaînement, depuis `CICD/ref_dynamique/`, avec l'environnement Python du socle (qui fournit PyYAML) :

```bash
source ~/projects/its-dp-fab-cicd-common/.venv/bin/activate
fab auth login
python 01_inventaire_github.py
python 02_fab_cli.py --env DEV      # environnement source des GUID (BDP DEV + Framework DEV)
python 02_fab_cli.py                # ITG
python 03_remplir.py
python 04_recoupement.py
```

Le dossier `templates/` contient les **modèles** de `config.yml` et `parameter.yml` au format du socle v1.5.0 (noms de workspaces, aucun GUID). Leurs marqueurs `<<WS_BDP_<ENV>>>`, `<<ITEM_TYPES_IN_SCOPE>>` et `<<REGLES_KEY_VALUE_REPLACE>>` sont résolus par `03_remplir.py`. Le rendu se recopie à la main dans `CICD/deployment/`, avec `framework_items_bdp.yml` dans `framework.items`, dans une PR revue, puis `deploy.py validate` doit passer sans erreur.

Pour vérifier un nom exact (tirets compris) : les ID des workspaces BDP ITG, PPR et PRD de l'ancien `deploy.py` figurent dans le registre du socle (`CICD/registry/known_guids.yml`). `python 02_fab_cli.py --env PRD --workspace-id <id>` affiche le nom tel qu'il est dans Fabric.

## Environnements, branches et déploiement

| Branche | Rôle | Déploiement | Réglage |
|---|---|---|---|
| `feature/*` | Développement | Aucun | PR vers `develop` |
| `develop` | Branche par défaut ; intégration des features | DEV par Git Integration ; ITG par la CD | Protégée ; workspace DEV connecté à `develop`, dossier Git `fabric` |
| `release/*` | Une branche par release, créée depuis `develop` au besoin | PPR par la CD, après approbation | Protégée (PR obligatoire, check PR-Validation) |
| `main` | Reflet de la production | PRD par la CD, après approbation | Protégée (PR obligatoire depuis `release/*`) |

La CD déploie des **définitions d'items** : elle n'exécute aucun pipeline et ne charge aucune donnée.

## Secrets et service connections

- Identité qui publie dans Fabric : le SPN de l'environnement. Ses trois secrets `<ENV>-AZURE-CLIENT-ID`, `-CLIENT-SECRET` et `-TENANT-ID` sont lus dans le **coffre unique `frfrkvdevdp0001`** (commun aux 11 dépôts, décision du 22/10/2026) par la tâche `AzureKeyVault@2` du template imposé.
- Accès au coffre : **une service connection Azure Resource Manager distincte par environnement**, créée par Ops en fédération d'identité. Trois sont prévues (ITG, PPR, PRD, décision du 31/10/2026), aucune pour DEV. Le socle refuse à la compilation une service connection partagée entre deux environnements. Les marqueurs `__A_CONFIRMER_SERVICE_CONNECTION_ARM_<ENV>__` sont imposés par le socle : c'est la chaîne que détecte sa garde de compilation.
- Le groupe de variables `Fabric-CD-Secrets` de l'ancienne CD n'est plus utilisé. Il ne doit pas être supprimé tant que les anciennes CD ne sont pas désactivées (backlog B33).
- Aucun secret n'est versionné. L'ancien `deployment/deploy.py` (ID de workspaces, capacités et SPN en dur) n'existe pas dans ce dépôt et ne doit pas y revenir : le socle le refuse (`STRUCT_LEGACY_DEPLOY_HARDCODED_IDS`).

## Contribuer

1. Travailler dans le workspace BDP DEV, puis enregistrer sur une branche `feature/*` (Source control de Fabric, dossier `fabric`).
2. Lancer les scripts de `CICD/ref_dynamique/`, puis reporter dans `CICD/deployment/` les types d'items, les règles et `framework.items`.
3. Pour appeler un item du Framework, utiliser la famille de règles Framework (une clé par environnement) et le déclarer dans `framework.items`. Aucune autre référence inter-workspace.
4. Ouvrir une PR vers `develop` et corriger jusqu'à ce que le check PR-Validation soit vert.

Pour contrôler le dépôt en local, à partir d'un clone du socle :

```bash
python ../its-dp-fab-cicd-common/CICD/tools/deploy.py validate --repo .
```

## Marqueurs à relever

| Fichier | Paramètre | Valeur attendue | Comment l'obtenir | Bloquant |
|---|---|---|---|---|
| `CICD/pipelines/CD.yml`, `PR-Validation.yml` | `endpoint` | Service connection GitHub du projet Data Platform | Azure DevOps → Project settings → Service connections | Oui (compilation) |
| `CICD/pipelines/CD.yml`, `PR-Validation.yml` | `name` (organisation) | Organisation GitHub du socle | GitHub / Plateforme Technologique | Oui (compilation) |
| `CICD/pipelines/CD.yml` | `serviceConnections.ITG/PPR/PRD` | Noms des 3 service connections ARM distinctes (création prévue) | Ops (fédération d'identité) | Oui (stage concerné) |
| `CICD/pipelines/CD.yml` | `source` du pipeline CI | Nom exact du pipeline CI | Azure DevOps → Pipelines | Oui (déclenchement) |
| `CICD/pipelines/CD.yml`, `dependencies.yml` | `frameworkPipelineName`, `ado_gate.pipeline_name` | Nom exact de la CD Framework (attendu `its-dp-fab-item-framework-managed-cd`) | Azure DevOps → Pipelines | Oui (porte, `GATE_PIPELINE`) |
| `CICD/deployment/config.yml` | `item_types_in_scope` | Types des items | `01_inventaire_github.py` | Oui |
| `CICD/deployment/dependencies.yml` | `framework.items` | Items Framework appelés | `03_remplir.py` → `framework_items_bdp.yml` | Oui une fois `validated` |
| `CICD/deployment/dependencies.yml` | `connections`, `variable_libraries`, `guid_policy`, `data_dependencies` | Relevés d'inventaire | Scripts 01, 02 et 04 | Selon contenu |

## Avant le premier déploiement

- [x] `fabric/test.md` remplacé par `fabric/.gitkeep` (31/10/2026).
- [x] Noms des workspaces BDP DEV, ITG, PPR et PRD confirmés (31/10/2026).
- [ ] Connecter la Git Integration du workspace DEV au dossier `fabric` de `develop`.
- [ ] Synchroniser les items, lancer les scripts 01 à 04, puis renseigner `item_types_in_scope`, `parameter.yml`, la clé `parameter` et `framework.items`.
- [ ] Créer les 3 service connections ARM (ITG, PPR, PRD) et remplacer les marqueurs de `CD.yml`.
- [ ] Remplacer les marqueurs GitHub de `CD.yml` et `PR-Validation.yml`.
- [ ] Confirmer le nom exact de la CD Framework (`frameworkPipelineName`, `ado_gate.pipeline_name`) et accorder au service de build le droit « View builds » sur cette définition.
- [ ] Vérifier qu'un **premier run de la nouvelle CD Framework** a eu lieu sur chaque environnement visé (sinon `GATE_NEVER_DEPLOYED`).
- [ ] Créer les pipelines ADO de CD et de validation de PR ; déclarer PR-Validation comme check obligatoire.
- [ ] Configurer les approbations sur les Environments ADO `fabric-ppr` et `fabric-prd`.
- [ ] Vérifier le point V-01 (contenu de l'artefact CI) au premier run.
- [ ] Faire passer `deploy.py validate` sans erreur, puis passer `inventory_status` à `validated` dans une PR revue.
- [ ] Désactiver l'ancienne CD BDP (groupe `Fabric-CD-Secrets`) une fois la nouvelle CD opérationnelle.
