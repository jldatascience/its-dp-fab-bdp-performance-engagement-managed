"""Étape 2 — VALEURS via Fabric CLI (fab), MONO-REPO : 02_fab_cli.py lit ce qu’il y a dans Fabric DEV

Détecte si ce repo est framework ou mds (nom du dossier ../..) et relève :
  - framework : le workspace Framework DEV + le GUID de chacun de ses items ;
  - mds       : les DEUX workspaces (Framework + MDS) DEV + leurs items
                (le parameter.yml du MDS référence des items du Framework).
Plus, dans les deux cas : connexions + gateways, et les activités InvokePipeline /
TridentNotebook lues dans le tenant (getDefinition) pour ce ou ces workspace(s).

Pré-requis : pip install ms-fabric-cli  ;  fab auth login
Sorties (À CÔTÉ du script) : guids_dev.json , connexions_gateways.json , activites_fabric_<repo>.csv
"""
import json, base64, csv, subprocess, sys, pathlib

BASE = pathlib.Path(__file__).resolve().parent

# Noms EXACTS des workspaces DEV (copier depuis le portail, ponctuation sensible)
WS_FRAMEWORK_DEV = "FR - DP - DEV - FAB - Framework - MANAGED"
WS_ADP_MDS_DEV   = "FR - DP - DEV - FAB - ADP - MDS - MANAGED"
REF_TYPES = {"InvokePipeline", "TridentNotebook"}

def detecter_label():
    nom = (BASE / ".." / "..").resolve().name.lower()
    if "item-framework" in nom or "framework" in nom: return "item-framework"
    if "adp-mds" in nom or "mds" in nom: return "adp-mds"
    # repli : si un inventaire existe déjà, s'en servir
    invs = list(BASE.glob("inventaire_*.json"))
    if invs: return invs[0].stem.replace("inventaire_", "")
    sys.exit("Impossible de déduire framework/mds depuis le dossier parent. "
             "Renomme le repo ou lance 01 d'abord.")

def _run(args):
    try: return subprocess.run(["fab", *args], capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError: sys.exit("Fabric CLI introuvable. pip install ms-fabric-cli, puis `fab auth login`.")

def _body(stdout, ctx):
    try: data = json.loads(stdout)
    except json.JSONDecodeError: sys.exit(f"Sortie `fab api {ctx}` non JSON (adapter à ta version de fab) :\n{stdout[:400]}")
    if isinstance(data, dict) and "text" in data and isinstance(data["text"], (dict, list)): data = data["text"]
    return data

def fab_get(endpoint):
    r = _run(["api", "-X", "get", endpoint])
    if r.returncode != 0: sys.exit(f"Echec `fab api get {endpoint}` : {r.stderr.strip() or r.stdout.strip()}")
    d = _body(r.stdout, endpoint); return d.get("value", d) if isinstance(d, dict) else d

def fab_post(endpoint):
    r = _run(["api", "-X", "post", endpoint]); return (r.returncode, _body(r.stdout, endpoint) if r.stdout.strip() else {})

def find_ws(nom):
    for ws in fab_get("workspaces"):
        if ws.get("displayName", "").strip() == nom.strip(): return ws["id"]
    sys.exit(f"Workspace introuvable (nom exact ? droits ?) : {nom!r}")

def items(ws_id): return fab_get(f"workspaces/{ws_id}/items")
def items_map(its): return {f'{it["type"]}/{it["displayName"]}': it["id"] for it in its}

def walk(acts, pipeline, out):
    for a in acts or []:
        tp = a.get("typeProperties", {}) or {}
        if a.get("type") in REF_TYPES:
            conn = None
            for v in (tp.get("externalReferences") or {}).values(): conn = v if isinstance(v, str) else conn
            out.append({"pipeline": pipeline, "activite": a.get("name"), "type": a.get("type"),
                        "workspaceId": tp.get("workspaceId"), "pipelineId": tp.get("pipelineId"),
                        "notebookId": tp.get("notebookId"), "connection": conn})
        for key in ("activities", "ifTrueActivities", "ifFalseActivities", "defaultActivities"):
            if isinstance(tp.get(key), list): walk(tp[key], pipeline, out)
        for case in (tp.get("cases") or []):
            if isinstance(case, dict): walk(case.get("activities"), pipeline, out)

def activites(ws_id, its):
    out = []
    for it in its:
        if it.get("type") != "DataPipeline": continue
        code, body = fab_post(f"workspaces/{ws_id}/items/{it['id']}/getDefinition")
        parts = ((body or {}).get("definition") or {}).get("parts") or []
        if not parts:
            print(f"   (def. indisponible pour {it['displayName']} — getDefinition async/202 ? à vérifier)"); continue
        for p in parts:
            if p.get("path", "").endswith("pipeline-content.json"):
                try: doc = json.loads(base64.b64decode(p["payload"]).decode("utf-8"))
                except Exception: continue
                walk((doc.get("properties") or {}).get("activities"), it["displayName"], out)
    return out

label = detecter_label()
fw_id = find_ws(WS_FRAMEWORK_DEV); fw_items = items(fw_id)
workspaces = {"WS_FRAMEWORK_DEV": fw_id}
guids = {"workspaces": workspaces, "framework_items": items_map(fw_items), "mds_items": {}}
scopes = [("item-framework", fw_id, fw_items)]   # pipelines framework à lire dans le tenant

if label == "adp-mds":
    mds_id = find_ws(WS_ADP_MDS_DEV); mds_items = items(mds_id)
    workspaces["WS_ADP_MDS_DEV"] = mds_id
    guids["mds_items"] = items_map(mds_items)
    scopes.append(("adp-mds", mds_id, mds_items))
    print(f"[mds] workspaces relevés : Framework + MDS")
else:
    print(f"[framework] workspace relevé : Framework uniquement")

json.dump(guids, open(BASE / "guids_dev.json", "w"), indent=2, ensure_ascii=False)

try: conns = [{"id": c.get("id"), "displayName": c.get("displayName"), "connectivityType": c.get("connectivityType")} for c in fab_get("connections")]
except SystemExit: conns = []
try: gws = [{"id": g.get("id"), "displayName": g.get("displayName"), "type": g.get("type")} for g in fab_get("gateways")]
except SystemExit: gws = []
json.dump({"connections": conns, "gateways": gws}, open(BASE / "connexions_gateways.json", "w"), indent=2, ensure_ascii=False)

for lbl, ws_id, its in scopes:
    acts = activites(ws_id, its)
    with open(BASE / f"activites_fabric_{lbl}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["pipeline","activite","type","workspaceId","pipelineId","notebookId","connection"])
        for a in acts: w.writerow([a["pipeline"],a["activite"],a["type"],a["workspaceId"],a["pipelineId"],a["notebookId"],a["connection"]])
    print(f"   {lbl}: {len(its)} items | {len(acts)} activités InvokePipeline/Notebook (tenant) -> activites_fabric_{lbl}.csv")

print(f"Framework DEV = {fw_id} | connexions={len(conns)} gateways={len(gws)}")
print("-> guids_dev.json , connexions_gateways.json , activites_fabric_*.csv")
