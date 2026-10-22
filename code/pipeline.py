import json
from llm import call
from tools import TAX, search_articles, search_any_version, search_gongjong, warranty_period, format_articles
from config import TOP_K
from rules import SCHEMA as RULE_SCHEMA, evaluate as rule_eval, decide as rule_decide

GJ_LIST = ", ".join(sorted({t["sub"] for t in TAX}))

OUT_SCHEMA = """다음 JSON 형식으로만 답하세요(설명 문장 금지).
{"label": "하자" 또는 "비하자",
 "defect_type": "시공하자" | "미시공하자" | "변경시공하자" | null,
 "gongjong": [하자가 발생한 주된 세부공종 1개를 맨 앞에, 관련 공종이 있으면 뒤에 최대 2개 추가, 아래 목록에서 선택],
 "composite": 하자 부위가 둘 이상 공종이 복합적으로 시공된 부위이면 true, 아니면 false,
 "warranty_years": 담보책임기간(년, 정수),
 "cited_articles": ["제N조", ...]  (판단 근거가 된 「공동주택 하자의 조사, 보수비용 산정 및 하자판정기준」 조항),
 "reason": "판단 근거 2문장 이내"}
JSON 바깥에 다른 글을 쓰지 마세요."""

SYS_JUDGE = ("당신은 국토교통부 하자심사·분쟁조정위원회의 하자 판정을 보조하는 전문가입니다. "
             "공동주택 하자 사건의 신청 내용과 현장 조사 결과를 보고 하자 여부, 하자 유형, 세부공종, 담보책임기간, 근거 조항을 판단합니다. "
             "하자 여부는 현장 조사에서 확인된 사실을 중심으로 판단합니다. 「공동주택 하자의 조사, 보수비용 산정 및 하자판정기준」 제2조에 따라 "
             "시공상 결함으로 안전상·기능상·미관상 지장을 초래하거나, 설계도서(제4조·제5조의 적용 기준 포함)와 다르게 시공되었거나 시공되지 않은 경우 하자이며, "
             "개별 조항에 해당 현상의 명시적 기준이 없다는 이유만으로 하자가 아니라고 판단하지 않습니다. "
             "반대로 조사 결과 결함이 확인되지 않거나, 입주자 사용·유지관리 문제 또는 자연재해에 의한 것이면 하자가 아닙니다.")


def case_text(c):
    return f"[하자 항목] {c['title']}\n[신청 내용] {c['claim'] or '(기재 없음)'}\n[조사 내용] {c['investigation']}"


# ---------- 조건 1: 직접 프롬프트(지식 없음) ----------
def run_direct(provider, c, version):
    user = f"{case_text(c)}\n\n[세부공종 목록] {GJ_LIST}\n\n{OUT_SCHEMA}"
    r = call(provider, SYS_JUDGE, user)
    return dict(pred=r["output"], retrieved=[], usage=r["usage"])


# ---------- 조건 2: 단순 RAG(사례 텍스트로 한 번 검색, 한 번 판정) ----------
def run_rag(provider, c, version, version_filter=True):
    q = c["title"] + " " + c["investigation"]
    arts = search_articles(q, version, TOP_K) if version_filter else search_any_version(q, TOP_K)
    user = (f"{case_text(c)}\n\n[관련 조문]\n{format_articles(arts)}\n\n[세부공종 목록] {GJ_LIST}\n\n"
            f"관련 조문을 근거로 판단하고, cited_articles에는 위 [관련 조문]에 있는 조항만 쓰세요.\n{OUT_SCHEMA}")
    r = call(provider, SYS_JUDGE, user)
    return dict(pred=r["output"], retrieved=[a["article"] for a in arts], usage=r["usage"])


# ---------- 조건 3: 제안 에이전트 ----------
SYS_EXTRACT = ("공동주택 하자 사건 기록에서 판정에 필요한 사실을 추출하는 도우미입니다. "
               "판단하지 말고 기록에 있는 사실만 구조화하세요.")
EXTRACT_SCHEMA = """다음 JSON 형식으로만 답하세요.
{"location": "부위(예: 거실 벽체)",
 "phenomenon": "현상(예: 균열, 들뜸, 누수, 결로, 미시공, 규격 미달)",
 "measurements": ["측정값과 단위(예: 균열폭 0.4mm)"],
 "design_comparison": "설계도서와의 비교 결과(없으면 null)",
 "candidate_gongjong": [후보 세부공종 1~3개, 아래 후보에서 선택],
 "keywords": ["조문 검색용 핵심어 3~6개"],
 "measurements_struct": [아래 스키마에 따른 측정값 목록]}
""" + RULE_SCHEMA


def run_agent(provider, c, version, version_filter=True, use_tool=True, use_rules=True, cite_guard=True):
    # 1) 사실 추출 + 공종 후보
    gj_cand = search_gongjong(c["title"] + " " + c["investigation"], 10)
    cand_txt = "; ".join(f"{t['sub']}({t['major']}: {t['examples']})" for t in gj_cand)
    r1 = call(provider, SYS_EXTRACT, f"{case_text(c)}\n\n[공종 후보] {cand_txt}\n\n{EXTRACT_SCHEMA}")
    facts = r1["output"] if not r1["output"].get("_parse_error") else {}
    # 2) 버전 필터 조문 검색(추출한 현상·키워드 기반)
    q = " ".join([c["title"], str(facts.get("phenomenon", "")), " ".join(facts.get("keywords", []) or [])])
    arts = search_articles(q, version, TOP_K) if version_filter else search_any_version(q, TOP_K)
    # 3) 담보책임기간: 결정적 도구
    period, detail = warranty_period(facts.get("candidate_gongjong", []) or []) if use_tool else (None, [])
    tool_txt = (f"[담보책임기간 계산 도구 결과] 후보 공종별 기간 {detail}. "
                f"최종 담보책임기간은 당신이 gongjong 맨 앞에 쓴 주된 공종의 기간으로 확정됩니다.") if detail else ""
    # 3b) 수치 기준 규칙 검사 (결정적)
    findings = rule_eval(facts.get("measurements_struct")) if use_rules else []
    rule_verdict = rule_decide(findings)
    rule_txt = ("[수치 기준 검사 결과] " + "; ".join(
        f"{f['article']} {f['detail']} → {'기준 위반(하자 요건 충족)' if f['verdict'] == '하자' else '이 수치 기준은 위반하지 않음'}" for f in findings)
        + " ※ '기준 위반'은 고시 수치 기준에 따른 계산 결과이므로 따르세요. '위반하지 않음'은 해당 수치 기준으로만 하자가 아니라는 뜻이며, "
          "다른 현상(들뜸·누수·미시공 등)에 의한 하자 여부는 별도로 판단하세요.") if findings else ""
    # 4) 판정
    user = (f"{case_text(c)}\n\n[추출된 사실] {json.dumps({k: v for k, v in facts.items() if k != 'measurements_struct'}, ensure_ascii=False)}\n{rule_txt}\n\n"
            f"[적용 고시 버전] {version}\n[관련 조문]\n{format_articles(arts)}\n\n{tool_txt}\n\n[세부공종 목록] {GJ_LIST}\n\n"
            "판단 순서: (1) 조사에서 확인된 현상과 관련 조문을 대조 (2) 하자 여부·유형 결정 (3) 공종과 담보책임기간 확정. "
            "cited_articles에는 위 [관련 조문]에 있는 조항만 쓰세요.\n" + OUT_SCHEMA)
    r2 = call(provider, SYS_JUDGE, user)
    pred = dict(r2["output"])
    pred["_llm_label"] = pred.get("label")
    if rule_verdict and not pred.get("_parse_error"):
        pred["label"] = rule_verdict          # 수치 기준이 판단을 결정하는 경우 규칙 결과로 확정
        for f in findings:
            if f["verdict"] == rule_verdict:
                pred.setdefault("cited_articles", []).append(f["article"])
    if cite_guard and not pred.get("_parse_error"):
        import re as _re
        allowed = {a["article"] for a in arts} | {_re.match(r"제\d+조(?:의\d+)?", f["article"]).group(0) for f in findings}
        keep = []
        for x in pred.get("cited_articles", []) or []:
            base = _re.match(r"제\d+조(?:의\d+)?", str(x))
            if base and base.group(0) in allowed and base.group(0) not in keep:
                keep.append(base.group(0))
        pred["cited_articles_raw"] = pred.get("cited_articles")
        pred["cited_articles"] = keep
    if use_tool and not pred.get("_parse_error"):
        gl = pred.get("gongjong", []) or []
        p2, _ = warranty_period(gl[:1])   # 주된 공종 기준 (실제 판정례도 주된 공종 기간 적용)
        if p2:
            pred["warranty_years"] = p2   # 최종 기간은 도구가 확정
    usage = tuple(a + b for a, b in zip(r1["usage"], r2["usage"]))
    return dict(pred=pred, facts=facts, rule_findings=findings, retrieved=[a["article"] for a in arts], usage=usage)


RUNNERS = {
    "direct": run_direct,
    "rag": run_rag,
    "rag_noversion": lambda p, c, v: run_rag(p, c, v, version_filter=False),
    "agent": run_agent,
    "agent_noversion": lambda p, c, v: run_agent(p, c, v, version_filter=False),
    "agent_notool": lambda p, c, v: run_agent(p, c, v, use_tool=False),
    "agent_norule": lambda p, c, v: run_agent(p, c, v, use_rules=False),
    "agent_noguard": lambda p, c, v: run_agent(p, c, v, cite_guard=False),
}
