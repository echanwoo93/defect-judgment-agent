"""사용 예:
  python run.py --provider claude --conditions direct rag agent --limit 5     # 시험 실행 5건
  python run.py --provider gpt --conditions all                              # 전체
"""
import argparse, json, os, time
from config import CASES, OUT_DIR, EDITION_DEFAULT_VERSION, CITED_TO_VERSION
from pipeline import RUNNERS
import llm


def load_cases(split):
    if split == "contrast":
        return [json.loads(l) for l in open("data/contrast.jsonl", encoding="utf-8")]
    C = [json.loads(l) for l in open(CASES, encoding="utf-8")]
    C = [c for c in C if c["section"] in ("하자심사", "재심의") and c["label"] and c["investigation"]]
    if split == "test2026":
        C = [c for c in C if c["edition"] == 2026]
    return C


def case_version(c):
    return CITED_TO_VERSION.get(c["cited_version"], EDITION_DEFAULT_VERSION.get(c["edition"], "v2025"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=["claude", "gpt"])
    ap.add_argument("--conditions", nargs="+", default=["direct", "rag", "agent"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--split", default="all", choices=["all", "test2026", "contrast"])
    a = ap.parse_args()
    conds = list(RUNNERS) if a.conditions == ["all"] else a.conditions
    cases = load_cases(a.split)
    if a.limit:
        cases = cases[:a.limit]
    os.makedirs(OUT_DIR, exist_ok=True)
    for cond in conds:
        tag = ("_contrast" if a.split == "contrast" else "") + (f"_run{os.getenv('RUN_TAG')}" if os.getenv("RUN_TAG") else "")
        path = os.path.join(OUT_DIR, f"{a.provider}_{cond}{tag}.jsonl")
        done = set()
        if os.path.exists(path):
            done = {json.loads(l)["case_id"] for l in open(path, encoding="utf-8")}
        t0 = time.time()
        with open(path, "a", encoding="utf-8") as f:
            for i, c in enumerate(cases):
                if c["case_id"] in done:
                    continue
                v = case_version(c)
                try:
                    res = RUNNERS[cond](a.provider, c, v)
                except Exception as e:
                    res = dict(pred={"_error": str(e)}, retrieved=[], usage=(0, 0))
                res.update(case_id=c["case_id"], condition=cond, provider=a.provider, version=v)
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
                print(f"[{cond}] {i+1}/{len(cases)} {c['case_id']}", end="\r")
        print(f"\n{cond}: {time.time()-t0:.0f}s, 누적 토큰 in={llm.USAGE['input_tokens']} out={llm.USAGE['output_tokens']}")


if __name__ == "__main__":
    main()
