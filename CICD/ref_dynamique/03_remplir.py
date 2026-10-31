"""Étape 3 — REMPLIR les modèles templates/ du dépôt BDP Performance Engagement (aucune écriture dans le dépôt).

Lit les sorties des étapes 1 et 2 (inventaire_bdp.json, fabric_<ENV>.json) et les modèles
templates/config.yml et templates/parameter.yml, résout leurs marqueurs <<...>> et écrit,
HORS du dépôt (même dossier de sortie que 01 et 02) :
  config.rendu.yml, parameter.rendu.yml       versions remplies, à relire ;
  diff_config.txt, diff_parameter.txt         écart avec CICD/deployment/<fichier> ;
  framework_items_bdp.yml                     proposition de framework.items (dependencies.yml) ;
  references_non_converties_bdp.csv           références sans règle (et pourquoi).

Les fichiers de production CICD/deployment/*.yml ne sont JAMAIS modifiés : la recopie se fait
à la main, dans une PR revue, puis `deploy.py validate` du socle doit passer sans erreur.

Deux familles de règles (BDP, matrice v1.3 du socle) :
  - workspace courant : $workspace.$id / $items.<Type>.<nom>.$id (clé _ALL_) ;
  - workspace Framework de l'environnement cible, PAR NOM et par environnement :
    $workspace.FR - DP - <ENV> - FAB - Framework - MANAGED.$id
    $workspace.FR - DP - <ENV> - FAB - Framework - MANAGED.$items.<Type>.<nom>.$id
    (noms lus dans framework.workspace de dependencies.yml).
Toute autre référence inter-workspace est listée, jamais convertie (DEPS_CROSS_WORKSPACE_FORBIDDEN).

Marqueurs :
  <<WS_BDP_DEV>> … <<WS_BDP_PRD>>  nom relevé dans Fabric (fabric_<ENV>.json), sinon config.yml ;
  <<ITEM_TYPES_IN_SCOPE>>           types des items du dépôt (inventaire Git) ;
  <<REGLES_KEY_VALUE_REPLACE>>      règles des deux familles ci-dessus.
Aucun GUID n'est écrit dans les rendus (RULE_LITERAL_GUID, CONFIG_WORKSPACE_ID_FORBIDDEN).

Usage : python 03_remplir.py [--out <dossier>]
Code retour : 0 = tous les marqueurs résolus ; 1 = marqueurs non résolus (rendus écrits quand même).
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

REPO_NAME = "its-dp-fab-bdp-performance-engagement-managed"
LABEL = "bdp"
ENVIRONMENTS = ("DEV", "ITG", "PPR", "PRD")
PLACEHOLDER_MARK = "__A_RELEVER__"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
TEMPLATES = SCRIPT_DIR / "templates"
DEPLOYMENT = REPO_ROOT / "CICD" / "deployment"
TOKEN = re.compile(r"<<([A-Z_]+)>>")
TYPE_ATTENDU = {"pipelineId": "DataPipeline", "notebookId": "Notebook"}


def dossier_sortie(arg: str | None) -> Path:
    brut = arg or os.environ.get("REF_DYN_OUT") or str(Path(tempfile.gettempdir()) / "ref_dynamique" / REPO_NAME)
    out = Path(brut).expanduser().resolve()
    try:
        out.relative_to(REPO_ROOT.resolve())
    except ValueError:
        out.mkdir(parents=True, exist_ok=True)
        return out
    sys.exit(f"Dossier de sortie {out} situé DANS le dépôt : refusé (choisir --out hors du dépôt).")


def lire_json(chemin: Path):
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.is_file() else None


def noms_framework() -> dict:
    """framework.workspace de dependencies.yml (nom du workspace Framework par environnement)."""
    f = DEPLOYMENT / "dependencies.yml"
    if not f.is_file():
        return {}
    try:
        import yaml
        ws = (((yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("framework") or {}).get("workspace") or {})
    except ImportError:
        print("PyYAML requis pour lire dependencies.yml : pip install pyyaml", file=sys.stderr)
        return {}
    return {k: str(v) for k, v in ws.items() if v and PLACEHOLDER_MARK not in str(v)}


def noms_config() -> dict:
    f = DEPLOYMENT / "config.yml"
    if not f.is_file():
        return {}
    texte = f.read_text(encoding="utf-8")
    try:
        import yaml
        ws = ((yaml.safe_load(texte) or {}).get("core") or {}).get("workspace") or {}
    except ImportError:
        ws = {m.group(1): m.group(2) for m in re.finditer(r'^\s+(DEV|ITG|PPR|PRD):\s*"([^"]+)"', texte, re.M)}
    return {k: v for k, v in ws.items() if v and PLACEHOLDER_MARK not in str(v)}


def yaml_simple(valeur: str) -> str:
    """Chaîne YAML entre apostrophes (les find_key contiennent des guillemets)."""
    return "'" + valeur.replace("'", "''") + "'"


def regle(chemin: str, item: str, valeurs: dict) -> str:
    """Bloc YAML d'une règle key_value_replace (valeurs : {_ALL_: …} ou {DEV: …, ITG: …})."""
    if list(valeurs) == ["_ALL_"]:
        rv = f"{{_ALL_: {json.dumps(valeurs['_ALL_'], ensure_ascii=False)}}}"
    else:
        rv = "".join(f"\n      {env}: {json.dumps(v, ensure_ascii=False)}" for env, v in valeurs.items())
    return (f"  - find_key: {yaml_simple(chemin)}\n"
            f"    replace_value: {rv}\n"
            f"    item_type: DataPipeline\n"
            f"    item_name: {json.dumps(item, ensure_ascii=False)}")


def regles(inventaire: dict | None, fabric: dict, fw_noms: dict):
    """Règles justifiées (2 familles), références non converties et items Framework appelés."""
    if not inventaire:
        return [], [], set()
    git_items = {(i["type"], i["nom"]) for i in inventaire.get("items", [])}
    par_id, fw_par_id = {}, {}
    ws_bdp = {d["workspace"]["id"] for d in fabric.values()}
    ws_fw = {}
    for env, data in fabric.items():
        for it in data.get("items", []):
            par_id[it["id"]] = (it["type"], it["nom"], env, data["workspace"]["id"])
        fw = data.get("framework") or {}
        if fw.get("workspace"):
            ws_fw[fw["workspace"]["id"]] = env
            for it in fw.get("items", []):
                fw_par_id[it["id"]] = (it["type"], it["nom"], env, fw["workspace"]["id"])
    fw_complet = all(e in fw_noms for e in ENVIRONMENTS)
    blocs, rejets, fw_items, vus = [], [], set(), set()
    for a in inventaire.get("activites_ref", []):
        cle = (a["item"], a["chemin"])
        if cle in vus:
            continue
        vus.add(cle)
        prop, wsr, cid = a["propriete_cible"], a.get("workspaceId") or "", a.get("cibleId") or ""
        base = [a["item"], a["activite"], a["type"], wsr, cid]
        chemin_ws = a["chemin"] + ".typeProperties.workspaceId"
        chemin_id = a["chemin"] + ".typeProperties." + prop
        # --- famille 2 : appel d'un item du Framework ---
        if (wsr and wsr in ws_fw) or (cid in fw_par_id and cid not in par_id):
            cible = fw_par_id.get(cid)
            if not cible:
                rejets.append(base + ["FRAMEWORK_NON_IDENTIFIE", "workspace Framework, mais item appelé absent de l'inventaire Framework (02 sur le même environnement que les GUID)"])
                continue
            ctype, cnom, env, _ = cible
            if ctype != TYPE_ATTENDU.get(prop):
                rejets.append(base + ["INCOHERENCE_TYPE", f"{prop} pointe vers un {ctype} Framework ({cnom})"])
                continue
            if not fw_complet:
                rejets.append(base + ["FRAMEWORK_NOM_MANQUANT", "framework.workspace incomplet dans dependencies.yml"])
                continue
            fw_items.add((ctype, cnom))
            blocs.append(f"  # {a['item']} -> activité {a['activite']} -> Framework {ctype} {cnom} (relevé : {env})")
            blocs.append(regle(chemin_ws, a["item"], {e: f"$workspace.{fw_noms[e]}.$id" for e in ENVIRONMENTS}))
            blocs.append(regle(chemin_id, a["item"],
                               {e: f"$workspace.{fw_noms[e]}.$items.{ctype}.{cnom}.$id" for e in ENVIRONMENTS}))
            continue
        cible = par_id.get(cid)
        if wsr and wsr not in ws_bdp and not cible:
            rejets.append(base + ["INTER_WORKSPACE", "workspace ni BDP ni Framework : référence interdite au déploiement (R2-R4) ; à résoudre à l'exécution et à déclarer dans data_dependencies"])
            continue
        if not cible:
            rejets.append(base + ["NON_IDENTIFIEE", "ID appelé absent des inventaires Fabric BDP et Framework (lancer 02 sur l'environnement source des GUID, en général DEV)"])
            continue
        ctype, cnom, env, ws_id = cible
        if wsr and wsr != ws_id:
            rejets.append(base + ["INTER_WORKSPACE", "workspaceId différent du workspace de l'item appelé"])
            continue
        if ctype != TYPE_ATTENDU.get(prop):
            rejets.append(base + ["INCOHERENCE_TYPE", f"{prop} pointe vers un {ctype} ({cnom})"])
            continue
        if (ctype, cnom) not in git_items:
            rejets.append(base + ["ITEM_ABSENT_DU_DEPOT", f"{ctype} {cnom} présent dans Fabric {env} mais pas sous fabric/"])
            continue
        # --- famille 1 : item du workspace courant ---
        blocs.append(f"  # {a['item']} -> activité {a['activite']} -> {ctype} {cnom} (relevé : {env})")
        blocs.append(regle(chemin_ws, a["item"], {"_ALL_": "$workspace.$id"}))
        blocs.append(regle(chemin_id, a["item"], {"_ALL_": f"$items.{ctype}.{cnom}.$id"}))
    return blocs, rejets, fw_items


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", help="dossier des sorties 01/02 et des rendus (hors dépôt)")
    args = p.parse_args()
    out = dossier_sortie(args.out)

    inventaire = lire_json(out / f"inventaire_{LABEL}.json")
    if inventaire is None:
        print("Info : inventaire_bdp.json absent (lancer 01_inventaire_github.py) : types et règles non résolus.")
    fabric = {env: d for env in ENVIRONMENTS if (d := lire_json(out / f"fabric_{env}.json"))}
    if not fabric:
        print("Info : aucun fabric_<ENV>.json (lancer 02_fab_cli.py) : noms repris de config.yml, règles non résolues.")

    valeurs: dict[str, str] = {}
    cfg = noms_config()
    for env in ENVIRONMENTS:
        nom = (fabric.get(env) or {}).get("workspace", {}).get("nom") or cfg.get(env)
        if nom:
            valeurs[f"WS_BDP_{env}"] = nom
    types = sorted({i["type"] for i in (inventaire or {}).get("items", []) if i.get("type")})
    if types:
        valeurs["ITEM_TYPES_IN_SCOPE"] = "[" + ", ".join(types) + "]"
    blocs, rejets, fw_items = regles(inventaire, fabric, noms_framework())
    if any(b.lstrip().startswith("- ") for b in blocs):
        valeurs["REGLES_KEY_VALUE_REPLACE"] = "\n" + "\n".join(blocs)
    elif inventaire is not None and fabric and not rejets:
        valeurs["REGLES_KEY_VALUE_REPLACE"] = "[]"  # aucune activité de référence : aucune règle justifiée
    lignes_fw = ["# Proposition de framework.items pour CICD/deployment/dependencies.yml (à relire).",
                 "# Items du Framework appelés par les pipelines du BDP (relevés par 01 et 02)."]
    lignes_fw += ["items: []"] if not fw_items else ["items:"] + [
        f"  - {{type: {t}, name: {json.dumps(n, ensure_ascii=False)}}}" for t, n in sorted(fw_items)]
    (out / f"framework_items_{LABEL}.yml").write_text("\n".join(lignes_fw) + "\n", encoding="utf-8")

    non_resolus: dict[str, list[str]] = {}
    for modele in sorted(TEMPLATES.glob("*.yml")):
        manquants: list[str] = []

        def remplacer(m: re.Match) -> str:
            if m.group(1) in valeurs:
                return valeurs[m.group(1)]
            manquants.append(m.group(1))
            return m.group(0)

        # Les commentaires (lignes commençant par #) citent les marqueurs : ils ne sont pas remplacés.
        lignes = [ligne if ligne.lstrip().startswith("#") else TOKEN.sub(remplacer, ligne)
                  for ligne in modele.read_text(encoding="utf-8").splitlines(keepends=True)]
        rendu = re.sub(r"[ \t]+\n", "\n", "".join(lignes))
        cible = out / f"{modele.stem}.rendu.yml"
        cible.write_text(rendu, encoding="utf-8")
        prod = DEPLOYMENT / modele.name
        actuel = prod.read_text(encoding="utf-8").splitlines(keepends=True) if prod.is_file() else []
        (out / f"diff_{modele.stem}.txt").write_text("".join(difflib.unified_diff(
            actuel, rendu.splitlines(keepends=True), f"CICD/deployment/{modele.name}", cible.name)), encoding="utf-8")
        if manquants:
            non_resolus[modele.name] = sorted(set(manquants))
        print(f"rendu : {cible}  ({'OK' if not manquants else str(len(set(manquants))) + ' marqueur(s) non résolu(s)'})")

    with open(out / f"references_non_converties_{LABEL}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["item", "activite", "type", "workspaceId", "cibleId", "motif", "detail"])
        w.writerows(rejets)
    print(f"{sum(1 for b in blocs if b.lstrip().startswith('- '))} règle(s) proposée(s) | {len(rejets)} référence(s) non convertie(s) -> "
          f"references_non_converties_{LABEL}.csv | {len(fw_items)} item(s) Framework -> framework_items_{LABEL}.yml")

    if non_resolus:
        print("\nMarqueurs NON résolus :")
        for fichier, toks in non_resolus.items():
            for t in toks:
                print(f"   - {fichier} : <<{t}>>")
        sys.exit(1)
    print("\nTous les marqueurs ont été résolus. Relire les diff avant toute recopie dans CICD/deployment/.")


if __name__ == "__main__":
    main()
