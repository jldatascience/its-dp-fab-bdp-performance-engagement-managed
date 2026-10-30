# Changelog

Toutes les évolutions notables du dépôt `its-dp-fab-item-framework-managed` (configuration de déploiement, pipelines,
documentation) sont consignées ici, de la plus récente à la plus ancienne.

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Ce dépôt n'est pas versionné
par tag : chaque entrée est datée (`## AAAA-MM-JJ`). Les évolutions du socle commun sont décrites
dans le `CHANGELOG.md` de `its-dp-fab-cicd-common`, versionné par tag `vX.Y.Z`.

## 2026-10-29

### Fixed

- `CICD/pipelines/CD.yml` : template `pipelines/templates/cd-pipeline.yml@cicd_common` →
  `CICD/pipelines/templates/cd-pipeline.yml@cicd_common` (emplacement réel dans le socle).
- `CICD/pipelines/PR-Validation.yml` : template `pipelines/templates/validate-pipeline.yml@cicd_common` →
  `CICD/pipelines/templates/validate-pipeline.yml@cicd_common`.
- `CICD/deployment/config.yml` : `repository_directory` `".."` → `"../../fabric"`. Le chemin est
  résolu depuis le dossier de `config.yml` (`CICD/deployment/`) : `".."` désignait `CICD/`.
  - Items découverts sous `fabric/` ; dossiers exclus inchangés (`folder_exclude_regex` relatif à `fabric/`).
- `CICD/ref_dynamique/templates/config.yml` : même correction de `repository_directory`.
- En-têtes des fichiers `CICD/deployment/*.yml` et README alignés sur l'arborescence `CICD/`.
- README : arborescence de `fabric/` relevée sur le contenu réel du dépôt, et non plus reprise de
  l'inventaire du MODOP.

### Changed

- Socle commun épinglé sur `refs/tags/v1.5.0` (après `v1.4.1`) dans `CICD/pipelines/CD.yml`,
  `CICD/pipelines/PR-Validation.yml` et le README.
- `CHANGES.md` renommé `CHANGELOG.md` (convention commune aux trois dépôts), au format du
  changelog du socle, avec des entrées datées.

### Added

- Journal des changements du dépôt (ce fichier).
