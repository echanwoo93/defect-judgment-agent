"""실패한 결과(오류·해석 불가)를 확인하고 지워서 다시 돌릴 수 있게 합니다.
사용: python clean_errors.py            → 오류 현황만 출력
      python clean_errors.py --remove   → 오류 건을 결과 파일에서 삭제(그다음 같은 run 명령을 다시 실행)"""
import glob, json, os, sys
from collections import Counter

remove = "--remove" in sys.argv
for path in sorted(glob.glob(os.path.join("results", "*.jsonl"))):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    bad = [r for r in rows if r["pred"].get("_error") or r["pred"].get("_parse_error")]
    if not bad:
        continue
    msgs = Counter((r["pred"].get("_error") or "JSON 해석 실패: " + str(r["pred"].get("_raw", ""))[:60])[:120] for r in bad)
    print(f"\n{os.path.basename(path)}: {len(bad)}건 실패")
    for m, n in msgs.most_common(3):
        print(f"  {n}건 | {m}")
    if remove:
        keep = [r for r in rows if r not in bad]
        with open(path, "w", encoding="utf-8") as f:
            for r in keep:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print("  → 삭제 완료. 같은 run 명령을 다시 실행하면 이 건들만 새로 돌립니다.")
