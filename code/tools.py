"""에이전트 도구: (1) 버전 필터가 있는 조문 검색, (2) 공종 → 담보책임기간 계산, (3) 공종 후보 검색.
외부 라이브러리 없이 한글 글자 2-gram BM25를 사용합니다."""
import json, math, re
from collections import Counter
from config import KB_REG, KB_GJ

REG = json.load(open(KB_REG, encoding="utf-8"))
GJ = json.load(open(KB_GJ, encoding="utf-8"))
TAX = GJ["taxonomy"]


def _tok(s):
    s = re.sub(r"[^가-힣A-Za-z0-9]", "", s)
    return [s[i:i + 2] for i in range(len(s) - 1)]


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = docs
        self.toks = [_tok(d) for d in docs]
        self.avg = sum(map(len, self.toks)) / max(1, len(self.toks))
        df = Counter(t for ts in self.toks for t in set(ts))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.tf = [Counter(ts) for ts in self.toks]
        self.k1, self.b = k1, b

    def scores(self, q):
        qt = _tok(q)
        out = []
        for i, tf in enumerate(self.tf):
            L = len(self.toks[i])
            s = 0.0
            for t in qt:
                if t in tf:
                    f = tf[t]
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * L / self.avg))
            out.append(s)
        return out


_INDEX = {}


def _index(version):
    if version not in _INDEX:
        arts = [a for a in REG["articles"] if a["version"] == version]
        _INDEX[version] = (arts, BM25([a["title"] + " " + a["text"] for a in arts]))
    return _INDEX[version]


def search_articles(query, version, k=6, include_general=True):
    """해당 버전 조문만 검색. 일반 조항(정의·설계도서 적용기준 등)은 별도로 항상 붙일 수 있음."""
    arts, bm = _index(version)
    sc = bm.scores(query)
    ranked = [arts[i] for i in sorted(range(len(arts)), key=lambda i: -sc[i]) if not arts[i]["general"]][:k]
    general = [a for a in arts if a["article_key"] in ("2", "4", "5")] if include_general else []
    return general + ranked


def search_any_version(query, k=6):
    """버전 필터 없는 검색(비교 조건용): 모든 버전 조문을 섞어서 검색."""
    if "all" not in _INDEX:
        arts = REG["articles"]
        _INDEX["all"] = (arts, BM25([a["title"] + " " + a["text"] for a in arts]))
    arts, bm = _INDEX["all"]
    sc = bm.scores(query)
    seen, out = set(), []
    for i in sorted(range(len(arts)), key=lambda i: -sc[i]):
        if arts[i]["general"] or arts[i]["article"] in seen:
            continue
        seen.add(arts[i]["article"]); out.append(arts[i])
        if len(out) == k:
            break
    return out


# 검색용 보조 키워드(현상 → 공종 연결). 판정 정답과 무관한 일반 지식만 넣음
HINTS = {"방수공사": "누수 물샘 방수층 욕실 옥상 지하 천장 누수", "창문틀 및 문짝공사": "창호 결로 개폐 기밀 모헤어 풍지판 문짝",
         "단열공사": "결로 곰팡이 단열재 열화상", "도장공사": "도장 페인트 박리 들뜸 변색 오염", "타일공사": "타일 들뜸 탈락 균열 뒤채움",
         "수장공사": "마루 강마루 바닥재 들뜸 단차 경량벽체", "일반철근콘크리트공사": "콘크리트 균열 철근노출", "내력구조부": "내력벽 기둥 슬래브 보 구조 균열 철근노출",
         "배수·통기설비공사": "배수 역류 악취 오수 배관 소음", "위생기구설비공사": "수전 세면기 양변기 토출량 샤워기", "도배공사": "도배 벽지 들뜸 주름 오염 찢김",
         "옥내가구공사": "가구 수납장 붙박이장 개폐 들뜸", "주방기구공사": "싱크대 주방가구 상판", "조명설비공사": "조명 등기구 점등", "감시제어설비공사": "CCTV 카메라 사각지대"}
_GJ_BM = BM25([t["major"] + " " + t["sub"] + " " + t["examples"] + " " + HINTS.get(t["sub"], "") for t in TAX])


def search_gongjong(query, k=8):
    sc = _GJ_BM.scores(query)
    return [TAX[i] for i in sorted(range(len(TAX)), key=lambda i: -sc[i])[:k]]


_BY_SUB = {re.sub(r"\s+", "", t["sub"]): t for t in TAX}


def warranty_period(gongjong_list):
    """결정적 계산: 공종별 기간 조회, 복합 공종이면 가장 긴 기간(고시 별표1 비고)."""
    found = [_BY_SUB.get(re.sub(r"\s+", "", g)) for g in gongjong_list]
    found = [f for f in found if f]
    if not found:
        return None, []
    best = max(found, key=lambda f: f["period_years"])
    return best["period_years"], [(f["sub"], f["period_years"]) for f in found]


def format_articles(arts):
    return "\n\n".join(f"[{a['article']}({a['title']})] {a['text']}" for a in arts)
