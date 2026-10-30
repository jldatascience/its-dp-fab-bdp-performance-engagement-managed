"""Étape 1 — INVENTAIRE depuis Git, MONO-REPO (ce repo uniquement) : 01_inventaire_github.py lit ce qu’il y a dans Git

À lancer depuis <repo>/CICD/ref_dynamique/. Le script détecte s'il s'agit du
repo framework ou mds (d'après le nom du dossier du repo) et lit les bonnes
branches :
  - item-framework : branche 'develop' ;
  - adp-mds        : UNION de 3 branches feature/its/*, doublons retirés
                     (la version la plus récente de chaque item gagne).

Produit (À CÔTÉ de ce script) : activites_<repo>.csv, toutes_refs_<repo>.csv,
inventaire_<repo>.json.

Usage :
    python 01_inventaire_github.py                 # repo = ../.. (racine depuis ref_dynamique)
    python 01_inventaire_github.py <chemin_repo>   # autre chemin
    python 01_inventaire_github.py <chemin_repo> framework|mds   # forcer le type
"""
import json, csv, re, sys, pathlib, subprocess

BASE = pathlib.Path(__file__).resolve().parent  # sorties À CÔTÉ du script

SOURCES = {
    "item-framework": {
        "mode": "branch",
        "branches": ["feature/its/411581_industrialisation_chaine_cicd"]
    },
    "adp-mds": {"mode": "union", "branches": [
        "feature/its/1_fabric_item_synchronization",
        "feature/its/422278_variables-id-resources-mds",
        "feature/its/427462_gestion_independante_des_versions_du_framework_par_dataproduct",
    ]},
}

def detecter_label(repo: pathlib.Path, forced=None):
    if forced in ("framework", "item-framework"): return "item-framework"
    if forced in ("mds", "adp-mds"): return "adp-mds"
    nom = repo.resolve().name.lower()
    if "item-framework" in nom or "framework" in nom: return "item-framework"
    if "adp-mds" in nom or "mds" in nom: return "adp-mds"
    sys.exit(f"Impossible de déduire le type depuis '{repo}'. "
             f"Ajoute 'framework' ou 'mds' en 2e argument.")

GUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
REF_TYPES = {"InvokePipeline", "TridentNotebook"}
PREFIXES = {"42463408": "SANDBOX (à remplacer)", "a699158a": "workspace MDS DEV",
            "727cf65b": "connexion Fabric Data Pipelines (commune)",
            "d407c25a": "ancienne connexion SQL (archive)", "d219537c": "ancienne connexion pipelines (archive)",
            "deff24bb": "tenant KPMG"}
def classe(g):
    g = g.lower()
    for p, lib in PREFIXES.items():
        if g.startswith(p): return lib
    return "autre (workspace/item/connexion)"

# Dossiers hors périmètre (MODOP) : ne pas inventorier (évite de fausses alertes au recoupement).
EXCLURE = ("/Tests_", "/Flux/old/", "/Old_processing/", "/Old_sequence/", "/To_delete/")
def hors_perimetre(path):
    p = "/" + path.strip("/") + "/"
    return any(s in p for s in EXCLURE)

def git(repo, *a):
    r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr
def branch_ok(repo, b): return git(repo, "rev-parse", "--verify", "--quiet", b)[0] == 0
def ls_files(repo, b):
    c, o, _ = git(repo, "ls-tree", "-r", "--name-only", b); return o.splitlines() if c == 0 else []
def show(repo, b, p):
    c, o, _ = git(repo, "show", f"{b}:{p}"); return o if c == 0 else ""
def path_ts(repo, b, p):
    c, o, _ = git(repo, "log", "-1", "--format=%ct", b, "--", p); return int(o.strip()) if (c == 0 and o.strip()) else 0

def walk_activities(acts, pipeline, item, branche, out):
    for a in acts or []:
        tp = a.get("typeProperties", {}) or {}
        if a.get("type") in REF_TYPES:
            out.append({"item": item, "branche": branche, "activite": a.get("name"), "type": a.get("type"),
                        "workspaceId": tp.get("workspaceId"), "pipelineId": tp.get("pipelineId"),
                        "notebookId": tp.get("notebookId")})
        for key in ("activities", "ifTrueActivities", "ifFalseActivities", "defaultActivities"):
            if isinstance(tp.get(key), list): walk_activities(tp[key], pipeline, item, branche, out)
        for case in (tp.get("cases") or []):
            if isinstance(case, dict): walk_activities(case.get("activities"), pipeline, item, branche, out)

def walk_json(node, path, fichier, item, typ, branche, rows):
    if isinstance(node, dict):
        for k, v in node.items(): walk_json(v, f"{path}.{k}" if path else k, fichier, item, typ, branche, rows)
    elif isinstance(node, list):
        for i, v in enumerate(node): walk_json(v, f"{path}[{i}]", fichier, item, typ, branche, rows)
    elif isinstance(node, str) and GUID.fullmatch(node):
        rows.append({"item": item, "type": typ, "branche": branche, "fichier": fichier, "cle": path, "guid": node, "classe": classe(node)})

def scan_text(txt, fichier, item, typ, branche, rows):
    for ln in txt.splitlines():
        for g in GUID.findall(ln):
            rows.append({"item": item, "type": typ, "branche": branche, "fichier": fichier, "cle": ln.strip()[:60], "guid": g, "classe": classe(g)})

def extraire(repo, branche, meta, fichiers, acts, allrefs):
    nom, typ = meta["displayName"], meta["type"]
    for path in fichiers:
        name = path.rsplit("/", 1)[-1]
        if name == ".platform": continue
        suf = "." + name.rsplit(".", 1)[-1] if "." in name else ""
        content = show(repo, branche, path)
        if suf == ".json":
            try: doc = json.loads(content)
            except Exception: continue
            if name == "pipeline-content.json":
                walk_activities((doc.get("properties") or {}).get("activities"), name, nom, branche, acts)
            walk_json(doc, "", name, nom, typ, branche, allrefs)
        elif suf in {".py", ".tmdl", ".pbir"} or suf == "":
            scan_text(content, name, nom, typ, branche, allrefs)

def inventorier(repo, cfg):
    branches = cfg["branches"]
    choisi, platform_path = {}, {}
    for b in branches:
        for f in ls_files(repo, b):
            if f.endswith(".platform"):
                item_dir = f[:-len("/.platform")] if "/" in f else ""
                if hors_perimetre(item_dir):
                    continue
                ts = path_ts(repo, b, item_dir or f)
                if item_dir not in choisi or ts > choisi[item_dir][1]:
                    choisi[item_dir] = (b, ts); platform_path[item_dir] = f
    items, acts, allrefs = [], [], []
    files_cache = {b: ls_files(repo, b) for b in branches}
    for item_dir, (b, ts) in sorted(choisi.items()):
        meta = json.loads(show(repo, b, platform_path[item_dir]))["metadata"]
        items.append({"nom": meta["displayName"], "type": meta["type"], "branche": b, "dossier": item_dir})
        prefix = item_dir + "/" if item_dir else ""
        extraire(repo, b, meta, [f for f in files_cache[b] if f.startswith(prefix)], acts, allrefs)
    return items, acts, allrefs

def main():
    args = sys.argv[1:]
    repo = pathlib.Path(args[0]) if args else (BASE / ".." / "..")   # ../.. = racine du repo
    forced = args[1] if len(args) > 1 else None
    label = detecter_label(repo, forced)
    cfg = SOURCES[label]
    manquantes = [b for b in cfg["branches"] if not branch_ok(repo, b)]
    if manquantes:
        print(f"[{label}] branches absentes en local :"); 
        for b in manquantes: print(f"   git -C {repo} fetch origin {b}:{b}")
        sys.exit(3)
    items, acts, allrefs = inventorier(repo, cfg)
    json.dump({"repo": label, "branches": cfg["branches"], "items": items,
               "activites_ref": acts, "toutes_refs_guid": allrefs},
              open(BASE / f"inventaire_{label}.json", "w"), indent=2, ensure_ascii=False)
    with open(BASE / f"activites_{label}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";"); w.writerow(["item","branche","activite","type","workspaceId","pipelineId","notebookId"])
        for a in acts: w.writerow([a["item"],a["branche"],a["activite"],a["type"],a["workspaceId"],a["pipelineId"],a["notebookId"]])
    with open(BASE / f"toutes_refs_{label}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";"); w.writerow(["item","type_item","branche","fichier","cle","guid","classe"])
        for r in allrefs: w.writerow([r["item"],r["type"],r["branche"],r["fichier"],r["cle"],r["guid"],r["classe"]])
    src = f"union de {len(cfg['branches'])} branches" if cfg["mode"]=="union" else f"branche {cfg['branches'][0]}"
    print(f"[{label}] {src} | {len(items)} items (doublons retirés) | {len(acts)} activités | {len(allrefs)} réfs GUID")
    print(f"          -> activites_{label}.csv , toutes_refs_{label}.csv , inventaire_{label}.json")

if __name__ == "__main__":
    main()
