"""Étape 1 — INVENTAIRE GIT du dépôt BDP Performance Engagement (lecture seule).

Lit, dans UNE branche Git (aucune fusion de branches, aucun checkout), les items Fabric
présents sous fabric/ et relève pour chacun :
  - son type et son nom affiché (.platform) ;
  - les activités InvokePipeline / TridentNotebook de ses pipelines, avec le chemin JSON
    complet de l'activité (activités imbriquées comprises : ForEach, If, Switch…) ;
  - tous les GUID présents dans ses fichiers de définition (JSON et texte).

Dépôt attendu : its-dp-fab-bdp-performance-engagement-managed (contrôlé par le remote
origin ou le nom du dossier ; --force pour passer outre).
Branche par défaut : feature/its/411581_industrialisation_chaine_cicd.

Sorties (HORS du dépôt, dossier --out, variable REF_DYN_OUT ou, par défaut,
<dossier temporaire système>/ref_dynamique/its-dp-fab-bdp-performance-engagement-managed) :
  inventaire_bdp.json, activites_bdp.csv, toutes_refs_bdp.csv

Usage (depuis CICD/ref_dynamique/) :
    python 01_inventaire_github.py
    python 01_inventaire_github.py --branch develop
    python 01_inventaire_github.py --repo ~/projects/its-dp-fab-bdp-performance-engagement-managed --out /tmp/bdp
Code retour : 0 = inventaire écrit (même vide) ; 2 = mauvais dépôt ; 3 = branche absente.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_NAME = "its-dp-fab-bdp-performance-engagement-managed"
LABEL = "bdp"
DEFAULT_BRANCH = "feature/its/411581_industrialisation_chaine_cicd"
ITEMS_DIR = "fabric"
CONFIG_PATH = "CICD/deployment/config.yml"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REPO = SCRIPT_DIR.parent.parent

GUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
# Activité -> propriété qui porte l'ID de l'item appelé.
REF_TYPES = {"InvokePipeline": "pipelineId", "TridentNotebook": "notebookId"}
NESTED_KEYS = ("activities", "ifTrueActivities", "ifFalseActivities", "defaultActivities")
TEXT_SUFFIXES = {".py", ".sql", ".tmdl", ".pbir", ".pbism", ".kql", ".r", ".scala", ".txt", ".yml", ".yaml", ".md", ""}


# --------------------------------------------------------------------------- utilitaires
def dossier_sortie(arg: str | None, repo: Path) -> Path:
    """Dossier de sortie hors dépôt (aucune écriture dans l'arborescence suivie)."""
    brut = arg or os.environ.get("REF_DYN_OUT") or str(Path(tempfile.gettempdir()) / "ref_dynamique" / REPO_NAME)
    out = Path(brut).expanduser().resolve()
    try:
        out.relative_to(repo.resolve())
    except ValueError:
        out.mkdir(parents=True, exist_ok=True)
        return out
    sys.exit(f"Dossier de sortie {out} situé DANS le dépôt : refusé (choisir --out hors du dépôt).")


def git(repo: Path, *args: str) -> tuple[int, str, str]:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


def verifier_depot(repo: Path, force: bool) -> None:
    code, top, err = git(repo, "rev-parse", "--show-toplevel")
    if code != 0:
        sys.exit(f"{repo} n'est pas un dépôt Git : {err.strip()}")
    _, url, _ = git(repo, "remote", "get-url", "origin")
    nom = Path(top.strip()).name.lower()
    if REPO_NAME in url.strip().lower() or nom == REPO_NAME:
        return
    message = (f"Dépôt inattendu ({nom}, origin={url.strip() or 'aucun'}) : ce script ne traite que "
               f"{REPO_NAME}.")
    if not force:
        print(message + " Relancer avec --force pour passer outre.", file=sys.stderr)
        sys.exit(2)
    print("ATTENTION : " + message + " (--force)", file=sys.stderr)


def resoudre_branche(repo: Path, branche: str) -> str:
    """Branche locale, sinon origin/<branche> ; jamais de checkout ni de fetch automatique."""
    for ref in (branche, f"origin/{branche}"):
        if git(repo, "rev-parse", "--verify", "--quiet", ref)[0] == 0:
            return ref
    print(f"Branche absente en local : {branche}\n   git -C {repo} fetch origin {branche}:{branche}", file=sys.stderr)
    sys.exit(3)


def lire_exclusion(repo: Path, ref: str) -> re.Pattern | None:
    """folder_exclude_regex de config.yml (même branche), appliqué aux chemins relatifs à fabric/."""
    code, texte, _ = git(repo, "show", f"{ref}:{CONFIG_PATH}")
    if code != 0:
        return None
    try:
        import yaml  # PyYAML, présent dans l'environnement du socle
        valeur = ((yaml.safe_load(texte) or {}).get("publish") or {}).get("folder_exclude_regex")
    except ImportError:
        m = re.search(r'^\s*folder_exclude_regex:\s*["\']?(.+?)["\']?\s*$', texte, re.M)
        valeur = m.group(1) if m else None
    if isinstance(valeur, dict):  # forme par environnement : identique partout (socle)
        valeur = next(iter(valeur.values()), None)
    return re.compile(valeur) if valeur else None


def charger_registre(chemin: str | None, repo: Path) -> list[dict]:
    """Registre des GUID connus du socle (classement indicatif), si disponible."""
    candidats = [Path(chemin)] if chemin else [
        repo.resolve().parent / "its-dp-fab-cicd-common" / "CICD" / "registry" / "known_guids.yml"]
    for f in candidats:
        if f.is_file():
            try:
                import yaml
                return (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("guids") or []
            except ImportError:
                return []
    return []


def classer(guid: str, registre: list[dict]) -> str:
    g = guid.lower()
    for entree in registre:
        valeur = str(entree.get("value", "")).lower()
        if valeur and (g == valeur or (len(valeur) < 36 and g.startswith(valeur))):
            return f"{entree.get('category', '?')} : {entree.get('label', '')}"
    return "non classé"


# --------------------------------------------------------------------------- extraction
def parcourir_activites(acts, chemin: str, item: str, out: list[dict]) -> None:
    for a in acts or []:
        if not isinstance(a, dict):
            continue
        nom = a.get("name")
        tp = a.get("typeProperties") or {}
        filtre = f'{chemin}[?(@.name=="{nom}")]'
        typ = a.get("type")
        if typ in REF_TYPES:
            connexion = None
            for v in (a.get("externalReferences") or tp.get("externalReferences") or {}).values():
                connexion = v if isinstance(v, str) else connexion
            prop = REF_TYPES[typ]
            out.append({"item": item, "activite": nom, "type": typ, "chemin": filtre,
                        "workspaceId": tp.get("workspaceId"), "propriete_cible": prop,
                        "cibleId": tp.get(prop), "connexion": connexion})
        for key in NESTED_KEYS:
            if isinstance(tp.get(key), list):
                parcourir_activites(tp[key], f"{filtre}.typeProperties.{key}", item, out)
        for i, case in enumerate(tp.get("cases") or []):
            if isinstance(case, dict):
                parcourir_activites(case.get("activities"), f"{filtre}.typeProperties.cases[{i}].activities", item, out)


def guids_json(node, chemin: str, base: dict, registre: list[dict], rows: list[dict]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            guids_json(v, f"{chemin}.{k}" if chemin else k, base, registre, rows)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            guids_json(v, f"{chemin}[{i}]", base, registre, rows)
    elif isinstance(node, str):
        for g in GUID.findall(node):
            rows.append({**base, "cle": chemin, "guid": g, "classe": classer(g, registre)})


def inventorier(repo: Path, ref: str, exclusion: re.Pattern | None, registre: list[dict]):
    code, sortie, _ = git(repo, "ls-tree", "-r", "--name-only", ref, "--", f"{ITEMS_DIR}/")
    fichiers = sortie.splitlines() if code == 0 else []
    items, activites, refs, exclus = [], [], [], []
    for plat in sorted(f for f in fichiers if f.endswith("/.platform")):
        dossier = plat[: -len("/.platform")]
        relatif = "/" + dossier[len(ITEMS_DIR) + 1:]
        if exclusion and exclusion.search(relatif):
            exclus.append(dossier)
            continue
        try:
            meta = json.loads(git(repo, "show", f"{ref}:{plat}")[1]).get("metadata") or {}
        except json.JSONDecodeError:
            print(f"   .platform illisible : {plat}", file=sys.stderr)
            continue
        nom, typ = meta.get("displayName"), meta.get("type")
        items.append({"nom": nom, "type": typ, "dossier": dossier})
        for chemin in (f for f in fichiers if f.startswith(dossier + "/") and f != plat):
            fichier = chemin[len(dossier) + 1:]
            suffixe = Path(fichier).suffix.lower()
            contenu = git(repo, "show", f"{ref}:{chemin}")[1]
            base = {"item": nom, "type_item": typ, "fichier": fichier}
            if suffixe == ".json":
                try:
                    doc = json.loads(contenu)
                except json.JSONDecodeError:
                    continue
                if fichier.endswith("pipeline-content.json"):
                    parcourir_activites((doc.get("properties") or {}).get("activities"),
                                        "$.properties.activities", nom, activites)
                guids_json(doc, "", base, registre, refs)
            elif suffixe in TEXT_SUFFIXES:
                for ligne in contenu.splitlines():
                    for g in GUID.findall(ligne):
                        refs.append({**base, "cle": ligne.strip()[:80], "guid": g, "classe": classer(g, registre)})
    return items, activites, refs, exclus


# --------------------------------------------------------------------------- main
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", default=str(DEFAULT_REPO), help="racine du dépôt BDP (défaut : ../..)")
    p.add_argument("--branch", default=DEFAULT_BRANCH, help=f"branche lue (défaut : {DEFAULT_BRANCH})")
    p.add_argument("--out", help="dossier de sortie hors dépôt (défaut : dossier temporaire système)")
    p.add_argument("--registre", help="known_guids.yml du socle (défaut : ../its-dp-fab-cicd-common/…)")
    p.add_argument("--force", action="store_true", help="accepter un autre dépôt que BDP Performance Engagement")
    args = p.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    verifier_depot(repo, args.force)
    out = dossier_sortie(args.out, repo)
    ref = resoudre_branche(repo, args.branch)
    _, courante, _ = git(repo, "branch", "--show-current")
    if courante.strip() and courante.strip() != args.branch:
        print(f"Info : branche courante « {courante.strip()} », inventaire lu sur « {ref} » (sans checkout).")
    _, commit, _ = git(repo, "rev-parse", ref)

    registre = charger_registre(args.registre, repo)
    items, activites, refs, exclus = inventorier(repo, ref, lire_exclusion(repo, ref), registre)
    workspaces = sorted({a["workspaceId"] for a in activites if a.get("workspaceId")})

    (out / f"inventaire_{LABEL}.json").write_text(json.dumps({
        "depot": REPO_NAME, "branche": ref, "commit": commit.strip(), "dossier_items": ITEMS_DIR,
        "items": items, "items_exclus": exclus, "activites_ref": activites,
        "workspaces_references": workspaces, "toutes_refs_guid": refs,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(out / f"activites_{LABEL}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["item", "activite", "type", "chemin", "workspaceId", "propriete_cible", "cibleId", "connexion"])
        for a in activites:
            w.writerow([a[k] for k in ("item", "activite", "type", "chemin", "workspaceId",
                                       "propriete_cible", "cibleId", "connexion")])
    with open(out / f"toutes_refs_{LABEL}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["item", "type_item", "fichier", "cle", "guid", "classe"])
        for r in refs:
            w.writerow([r[k] for k in ("item", "type_item", "fichier", "cle", "guid", "classe")])

    print(f"[{LABEL}] {ref} @ {commit.strip()[:8]} | {len(items)} items | {len(exclus)} exclus | "
          f"{len(activites)} activités | {len(refs)} réfs GUID | {len(workspaces)} workspace(s) référencé(s)")
    if not items:
        print(f"          Aucun item Fabric (.platform) sous {ITEMS_DIR}/ : rien à inventorier.")
    if len(workspaces) > 1:
        print("          Plusieurs workspaces référencés par les activités : appels au Framework (admis, R1) "
              "ou références croisées interdites (voir 02_fab_cli.py et 04_recoupement.py).")
    print(f"          -> {out}")


if __name__ == "__main__":
    main()
