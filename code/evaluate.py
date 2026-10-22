"""results/*.jsonl 을 읽어 조건별 지표 표를 만듭니다.  python evaluate.py"""
import json, glob, os, re, csv
from config import CASES, OUT_DIR
from tools import REG

GOLD = {c["case_id"]: c for c in (json.loads(l) for l in open("data/labels.jsonl", encoding="utf-8"))}
if os.path.exists("data/contrast.jsonl"):
    GOLD.update({c["case_id"]: c for c in (json.loads(l) for l in open("data/contrast.jsonl", encoding="utf-8"))})
GENERAL = {"1", "2", "3", "4", "5", "6", "6의2", "127", "128"}
VALID = {(a["version"], a["article_key"]) for a in REG["articles"]}


def akey(x):
    m = re.search(r"(\d+)\s*조(?:\s*의\s*(\d+))?", str(x))
    return None if not m else (m.group(1) + (f"의{m.group(2)}" if m.group(2) else ""))


def norm_gj(x):
    return re.sub(r"\s+", "", str(x))


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


SUBSET = None   # --subset 2026 이면 2026년판 사례만 집계 (ablation 비교용)


def evaluate(path):
    R = [json.loads(l) for l in open(path, encoding="utf-8")]
    if SUBSET:
        R = [r for r in R if GOLD[r["case_id"]]["edition"] in (SUBSET, 0)]
    m = dict(n=0, parse_err=0, label_ok=0, neg_n=0, neg_ok=0, type_n=0, type_ok=0, gj_n=0, gj_top1=0, gj_any=0,
             per_n=0, per_ok=0, near_n=0, near_ok=0, llm_ok=0, ex_n=0, ex_ok=0, cit_n=0, tp=0, fp=0, fn=0, gen_hit=0, invalid=0, outside=0, cites=0)
    for r in R:
        g = GOLD[r["case_id"]]; p = r["pred"]; m["n"] += 1
        if p.get("_parse_error") or p.get("_error"):
            m["parse_err"] += 1; continue
        m["label_ok"] += p.get("label") == g["label"]
        m["llm_ok"] += p.get("_llm_label", p.get("label")) == g["label"]
        cv = g.get("contrast_value")
        if isinstance(cv, (int, float)) and r.get("facts") is not None:
            m["ex_n"] += 1
            vals = [x.get("value") for x in (r["facts"].get("measurements_struct") or [])]
            m["ex_ok"] += any(isinstance(x, (int, float)) and abs(x - cv) < 1e-6 for x in vals)
        if g.get("near_threshold"):
            m["near_n"] += 1; m["near_ok"] += p.get("label") == g["label"]
        if g["label"] == "비하자":
            m["neg_n"] += 1; m["neg_ok"] += p.get("label") == "비하자"
        if g["label"] == "하자" and g.get("defect_type"):
            m["type_n"] += 1; m["type_ok"] += p.get("defect_type") == g["defect_type"]
        gold_gj = {norm_gj(x) for x in g.get("gongjong_canonical") or []}
        pred_gj = [norm_gj(x) for x in p.get("gongjong") or []]
        if gold_gj:
            m["gj_n"] += 1
            m["gj_top1"] += bool(pred_gj) and pred_gj[0] in gold_gj
            m["gj_any"] += bool(gold_gj & set(pred_gj))
        gold_per = g.get("period_gold") or g.get("period_taxonomy")
        if gold_per:
            m["per_n"] += 1
            try: m["per_ok"] += int(p.get("warranty_years")) == gold_per
            except Exception: pass
        pk = [akey(x) for x in p.get("cited_articles") or []]
        pk = [k for k in pk if k]
        retrieved = {akey(x) for x in r.get("retrieved") or []}
        for k in pk:
            m["cites"] += 1
            m["invalid"] += (r["version"], k) not in VALID           # 존재하지 않는 조항(환각)
            if retrieved: m["outside"] += k not in retrieved         # 검색 결과 밖 인용
        if g["has_gold_citation"] and not g.get("short_form"):
            gs = {akey(x) for x in g["cited_articles"]} - GENERAL
            ps = set(pk) - GENERAL
            if gs:
                m["cit_n"] += 1
                m["tp"] += len(gs & ps); m["fp"] += len(ps - gs); m["fn"] += len(gs - ps)
    P, Rc, F = prf(m["tp"], m["fp"], m["fn"])
    d = lambda a, b: round(a / b, 3) if b else None
    return {"n": m["n"], "parse_err": m["parse_err"],
            "label_acc": d(m["label_ok"], m["n"]), "label_acc_LLM판단만": d(m["llm_ok"], m["n"]), "경계사례_acc": d(m["near_ok"], m["near_n"]), "측정값추출_acc": d(m["ex_ok"], m["ex_n"]), "비하자_recall": d(m["neg_ok"], m["neg_n"]),
            "defect_type_acc": d(m["type_ok"], m["type_n"]),
            "공종_top1": d(m["gj_top1"], m["gj_n"]), "공종_any": d(m["gj_any"], m["gj_n"]),
            "담보기간_acc": d(m["per_ok"], m["per_n"]),
            "조항_P": round(P, 3), "조항_R": round(Rc, 3), "조항_F1": round(F, 3), "조항_평가사례": m["cit_n"],
            "환각조항_비율": d(m["invalid"], m["cites"]), "검색밖인용_비율": d(m["outside"], m["cites"])}


if __name__ == "__main__":
    import sys
    if "--subset" in sys.argv:
        SUBSET = int(sys.argv[sys.argv.index("--subset") + 1])
    rows = []
    for path in sorted(glob.glob(os.path.join(OUT_DIR, "*.jsonl"))):
        name = os.path.basename(path)[:-6]
        rows.append({"run": name, **evaluate(path)})
    if not rows:
        print("results 폴더에 결과가 없습니다."); raise SystemExit
    keys = list(rows[0].keys())
    with open(os.path.join(OUT_DIR, f"summary{'_' + str(SUBSET) if SUBSET else ''}.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    for r in rows:
        print(r)
