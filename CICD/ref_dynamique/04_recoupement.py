"""Étape 4 — RECOUPEMENT GitHub x Fabric (mono-repo, template aplati) : 04_recoupement.py compare Git et tenant

Lit templates/parameter.yml (le modèle de CE repo), guids_dev.json (étape 2) et
inventaire_<repo>.json (étape 1), et produit :
  - recoupement_<repo>.csv : chaque règle -> réf sandbox (repo) -> GUID DEV cible + statut ;
  - alertes_<repo>.csv : réfs sandbox du repo couvertes par AUCUNE règle.

Usage : python 04_recoupement.py
"""
import json, csv, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
TPL  = ROOT / "templates"
SANDBOX_PREFIXES = ("42463408", "a699158a")

FW_NB = ["nb_get_ws_lh_ids","nb_run_table","nb_log_load_start","nb_log_load_end_ok","nb_log_load_end_ko",
         "nb_log_processing_start","nb_log_processing_end_ok","nb_log_processing_end_ko",
         "nb_log_sequence_start","nb_log_sequence_end_ok","nb_log_sequence_end_ko"]
FW_PL = ["pl_run_table","log_processing_start","log_processing_end_ok","log_processing_end_ko",
         "log_load_start","log_load_end_ok","log_load_end_ko","pl_src_to_stg","pl_src_to_arc","pl_stg_to_str",
         "pl_get_ws_lh_ids","log_sequence_start","log_sequence_ok","log_sequence_ko","pl_load_object"]
MDS_PL = ["pl_load_tables"]; MDS_LH = ["lh_storage"]

def charger_guids():
    f = ROOT / "guids_dev.json"
    if not f.exists(): sys.exit("guids_dev.json manquant : lance d'abord 02_fab_cli.py.")
    return json.loads(f.read_text(encoding="utf-8"))

def resolveur(guids):
    WS, FW, MDS = guids["workspaces"], guids["framework_items"], guids["mds_items"]
    def resolve(tok):
        if tok in WS: return WS[tok]
        m = re.fullmatch(r"ID_(.+)_DEV", tok)
        if not m: return None
        n = m.group(1)
        if n in FW_NB:  return FW.get(f"Notebook/{n}")
        if n in FW_PL:  return FW.get(f"DataPipeline/{n}")
        if n in MDS_PL: return MDS.get(f"DataPipeline/{n}")
        if n in MDS_LH: return MDS.get(f"Lakehouse/{n}")
        return None
    return resolve

TOKEN = re.compile(r"<<(WS_[A-Z_]+|ID_[A-Za-z0-9_]+_DEV)>>")
def lire_regles(param_path):
    txt = param_path.read_text(encoding="utf-8"); regles = []
    for bloc in re.split(r"\n\s*-\s+find_key:", txt)[1:]:
        bloc = "- find_key:" + bloc
        fk = re.search(r"find_key:\s*'([^']+)'", bloc) or re.search(r'find_key:\s*"([^"]+)"', bloc) or re.search(r"find_key:\s*(\S.*)", bloc)
        iname = re.search(r'item_name:\s*"?([^"\n]+)"?', bloc)
        tok = TOKEN.search(bloc)
        if not (fk and iname and tok): continue
        fkv = fk.group(1).strip()
        act = re.search(r'@\.name==\s*"([^"]+)"', fkv)
        prop = fkv.rstrip().rsplit(".", 1)[-1]
        regles.append({"item": iname.group(1).strip(), "activite": act.group(1) if act else "(shortcut)",
                       "propriete": prop, "placeholder": tok.group(1)})
    return regles

def detecter_label():
    invs = sorted(ROOT.glob("inventaire_*.json"))
    if not invs: sys.exit("inventaire_*.json manquant : lance d'abord 01_inventaire_github.py.")
    return invs[0].stem.replace("inventaire_", ""), invs[0]

def charger_inventaire(inv_path):
    d = json.loads(inv_path.read_text(encoding="utf-8"))
    present = {(a["item"], a["activite"]): a for a in d.get("activites_ref", [])}
    sandbox = [r for r in d.get("toutes_refs_guid", []) if r["guid"].lower().startswith(SANDBOX_PREFIXES)]
    return present, sandbox

def guid_actuel(ref, prop):
    return ref.get(prop) if ref and prop in ("workspaceId","pipelineId","notebookId") else None

def main():
    param = TPL / "parameter.yml"
    if not param.exists(): sys.exit("templates/parameter.yml manquant dans ce dossier.")
    guids = charger_guids(); resolve = resolveur(guids)
    label, inv_path = detecter_label()
    regles = lire_regles(param)
    present, sandbox = charger_inventaire(inv_path)

    lignes, couverts = [], set()
    for r in regles:
        cible = resolve(r["placeholder"]); ref = present.get((r["item"], r["activite"]))
        if ref: couverts.add((r["item"], r["activite"]))
        actuel = guid_actuel(ref, r["propriete"])
        statut = "VALEUR_MANQUANTE (item absent en DEV / nom à confirmer)" if cible is None \
                 else ("ABSENT_REPO (règle sans activité correspondante)" if ref is None else "OK")
        lignes.append([r["item"], r["activite"], r["propriete"], r["placeholder"],
                       cible or "", actuel or "", "oui" if ref else "non", statut])
    with open(ROOT / f"recoupement_{label}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["item","activite","propriete","placeholder","guid_cible_dev","guid_actuel_repo","present_repo","statut"])
        w.writerows(lignes)

    items_couverts = {it for (it, _ac) in couverts}
    alertes = [[s["item"], s["type"], s["fichier"], s["cle"], s["guid"]]
               for s in sandbox if s["item"] not in items_couverts]
    with open(ROOT / f"alertes_{label}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["item","type_item","fichier","cle","guid_sandbox"]); w.writerows(alertes)

    ok = sum(1 for l in lignes if l[7] == "OK")
    manque = sum(1 for l in lignes if l[7].startswith("VALEUR"))
    absent = sum(1 for l in lignes if l[7].startswith("ABSENT"))
    print(f"[{label}] {len(regles)} règles | OK={ok} | valeur manquante={manque} | absent du repo={absent} | alertes={len(alertes)}")
    print(f"          -> recoupement_{label}.csv , alertes_{label}.csv")
    print("À traiter : 'VALEUR_MANQUANTE' et 'alertes_*.csv' non vide avant de déployer.")

if __name__ == "__main__":
    main()
