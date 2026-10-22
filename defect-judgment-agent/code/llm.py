"""Claude / GPT 호출 래퍼. 같은 입력은 캐시해서 재실행 비용을 줄입니다.
MOCK=1 환경변수를 주면 API 없이 가짜 응답으로 파이프라인만 점검합니다."""
import os, json, time, hashlib, re
from config import MODELS, TEMPERATURE, MAX_TOKENS

CACHE_DIR = ".cache"
os.makedirs(CACHE_DIR, exist_ok=True)
USAGE = {"input_tokens": 0, "output_tokens": 0, "calls": 0}


def _key(provider, system, user):
    tag = os.getenv("RUN_TAG", "")      # 반복 실행 시 RUN_TAG=2,3 … 으로 캐시를 분리해 독립 응답을 받음
    return hashlib.sha256(f"{provider}|{MODELS[provider]}|{tag}|{system}|{user}".encode()).hexdigest()[:24]


def _parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("JSON 없음")
    return json.loads(m.group(0))


def _mock(system, user):
    # 파이프라인 점검용 가짜 응답
    if "사실을 추출" in system:
        ms = []
        m = re.search(r"균열폭\s*([\d.]+)\s*mm", user)
        if m:
            ms.append({"type": "crack_width", "value": float(m.group(1)), "material": "concrete", "leak": "누수" in user.split("[공종 후보]")[0], "along_rebar": False, "through": False})
        return json.dumps({"location": "벽체", "phenomenon": "균열", "measurements": [], "candidate_gongjong": ["일반철근콘크리트공사"], "keywords": ["균열"], "measurements_struct": ms}, ensure_ascii=False)
    return json.dumps({"label": "하자", "defect_type": "시공하자", "gongjong": ["도배공사"], "cited_articles": ["제2조", "제34조"], "reason": "mock"}, ensure_ascii=False)


def call(provider, system, user, retries=4):
    k = _key(provider, system, user)
    path = os.path.join(CACHE_DIR, k + ".json")
    if os.path.exists(path):
        rec = json.load(open(path, encoding="utf-8"))
        if not rec["output"].get("_parse_error"):
            return rec               # 해석 실패로 저장된 응답은 재사용하지 않고 다시 호출
    if os.getenv("MOCK") == "1":
        text, usage = _mock(system, user), (0, 0)
    else:
        for i in range(retries):
            try:
                text, usage = _call_api(provider, system, user)
                break
            except Exception as e:  # 네트워크/레이트리밋 등
                if i == retries - 1 or isinstance(e, TypeError) or "not_found" in str(e) or "invalid" in str(e).lower():
                    raise
                time.sleep(2 ** i * 3)
    USAGE["calls"] += 1
    USAGE["input_tokens"] += usage[0]
    USAGE["output_tokens"] += usage[1]
    try:
        out = _parse_json(text)
    except Exception:
        out = {"_parse_error": True, "_raw": text}
    rec = {"output": out, "raw": text, "usage": usage}
    json.dump(rec, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return rec


_NO_TEMP = set()   # temperature를 지원하지 않는 것으로 확인된 provider


def _call_api(provider, system, user):
    """일부 최신 모델/SDK는 temperature 인자를 받지 않으므로, 거부되면 temperature 없이 다시 호출."""
    use_temp = provider not in _NO_TEMP
    try:
        return _call_once(provider, system, user, use_temp)
    except Exception as e:
        if use_temp and "temperature" in str(e).lower():
            _NO_TEMP.add(provider)
            print(f"\n[안내] {provider}: temperature 미지원 → temperature 없이 호출합니다.")
            return _call_once(provider, system, user, False)
        raise


def _call_once(provider, system, user, use_temp):
    if provider == "claude":
        import anthropic
        client = anthropic.Anthropic()
        kw = dict(model=MODELS["claude"], max_tokens=MAX_TOKENS, system=system,
                  messages=[{"role": "user", "content": user}])
        if use_temp:
            kw["temperature"] = TEMPERATURE
        r = client.messages.create(**kw)
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return text, (r.usage.input_tokens, r.usage.output_tokens)
    if provider == "gpt":
        from openai import OpenAI
        client = OpenAI()
        kw = dict(model=MODELS["gpt"], response_format={"type": "json_object"},
                  messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        if use_temp:
            kw["temperature"] = TEMPERATURE
        r = client.chat.completions.create(**kw)
        return r.choices[0].message.content, (r.usage.prompt_tokens, r.usage.completion_tokens)
    raise ValueError(provider)
