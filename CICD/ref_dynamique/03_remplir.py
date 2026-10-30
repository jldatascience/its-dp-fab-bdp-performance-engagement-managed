"""Étape 3 — REMPLIR les placeholders (local VS Code) : 03_remplir.py remplit parameter.yml à partir de ces valeurs

Prend guids_dev.json (étape 2) et remplace chaque <<...>> dans les 4 fichiers
modèles (templates/) -> écrit les versions complètes dans sortie/.
Signale tout placeholder NON résolu (ex. item introuvable = hypothèse MODOP à lever).

Usage : python 03_remplir.py        (depuis CICD/ref_dynamique/, templates/ à côté)
"""
import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
guids = json.loads((ROOT / "guids_dev.json").read_text(encoding="utf-8"))
WS = guids["workspaces"]; FW = guids["framework_items"]; MDS = guids["mds_items"]

# Table nom d'item -> (source, type) pour résoudre <<ID_<nom>_DEV>>
FW_NB = ["nb_get_ws_lh_ids","nb_run_table","nb_log_load_start","nb_log_load_end_ok","nb_log_load_end_ko",
         "nb_log_processing_start","nb_log_processing_end_ok","nb_log_processing_end_ko",
         "nb_log_sequence_start","nb_log_sequence_end_ok","nb_log_sequence_end_ko"]
FW_PL = ["pl_run_table","log_processing_start","log_processing_end_ok","log_processing_end_ko",
         "log_load_start","log_load_end_ok","log_load_end_ko","pl_src_to_stg","pl_src_to_arc","pl_stg_to_str",
         "pl_get_ws_lh_ids","log_sequence_start","log_sequence_ok","log_sequence_ko","pl_load_object"]
MDS_PL = ["pl_load_tables"]; MDS_LH = ["lh_storage"]

def resolve_id(nom):
    if nom in FW_NB:  return FW.get(f"Notebook/{nom}")
    if nom in FW_PL:  return FW.get(f"DataPipeline/{nom}")
    if nom in MDS_PL: return MDS.get(f"DataPipeline/{nom}")
    if nom in MDS_LH: return MDS.get(f"Lakehouse/{nom}")
    return None

def resolve_token(tok):                       # tok = contenu entre << >>
    if tok in WS: return WS[tok]              # WS_FRAMEWORK_DEV / WS_ADP_MDS_DEV
    m = re.fullmatch(r"ID_(.+)_DEV", tok)
    return resolve_id(m.group(1)) if m else None

# ne capter QUE les vrais placeholders (pas le "<<...>>" littéral des commentaires)
TOKEN = re.compile(r"<<(WS_[A-Z_]+|ID_[A-Za-z0-9_]+_DEV)>>")
sortie = ROOT / "sortie"; non_resolus = {}
for f in sorted((ROOT / "templates").rglob("*.yml")):
    txt = f.read_text(encoding="utf-8")
    manquants = []
    def repl(m):
        tok = m.group(1); val = resolve_token(tok)
        if val is None: manquants.append(tok); return m.group(0)
        return val
    new = TOKEN.sub(repl, txt)
    rel = f.relative_to(ROOT / "templates")
    dst = sortie / rel; dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(new, encoding="utf-8")
    if manquants: non_resolus[str(rel)] = sorted(set(manquants))
    print(f"écrit : sortie/{rel}  ({'OK' if not manquants else str(len(set(manquants)))+' non résolus'})")

if non_resolus:
    print("\n⚠️  Placeholders NON résolus (item absent du workspace DEV ou nom à confirmer) :")
    for fichier, toks in non_resolus.items():
        for t in toks: print(f"   - {fichier} : <<{t}>>")
    print("   (ex. <<ID_log_sequence_start_DEV>> = hypothèse MODOP 2.2 à lever.)")
else:
    print("\n✅ Tous les placeholders ont été remplis.")
