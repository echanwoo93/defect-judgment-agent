"""하자판정기준 고시의 수치 기준을 실행 가능한 규칙으로 옮긴 모듈.
LLM은 사례에서 측정값만 구조화해 넘기고, 하자 요건 충족 여부는 여기서 결정적으로 계산한다.
각 규칙은 근거 조항(article, paragraph)을 함께 반환한다. 수치 기준은 v2021~v2026 동일."""

# LLM 추출 단계에 제시하는 측정값 스키마
SCHEMA = """measurements_struct: 조사 내용에 '구체적인 측정 숫자'가 있고 아래 type의 정의에 정확히 해당할 때만 기록(없으면 []).
주의: "80% 미만", "30cm 초과"처럼 기준과 비교한 결론만 있고 실제 측정값이 없으면 기록하지 마세요.
joint_spacing/joint_width는 옥상 또는 지하주차장 '바닥'의 신축줄눈·조절줄눈에만 사용(벽체 이음부·문짝 틈새·단열재 틈새 등에는 사용 금지).
crack_width는 콘크리트 균열에만 사용(material이 plaster/paint면 판정에 쓰지 않음).
design_compare는 설계도서에 명시된 규격(두께·폭·크기·수량 등)과 같은 단위의 실측값을 비교할 때만 사용하고, higher_is_better는 값이 클수록 설계를 충족하는 항목(두께, 폭, 수량 등)이면 true, 작을수록 좋은 항목(열관류율 등)이면 false. 방향이 분명하지 않으면 기록하지 마세요.
- {"type":"crack_width","value":mm,"material":"concrete|plaster|paint","leak":bool,"along_rebar":bool,"through":bool}
- {"type":"tile_backfill","value":%,"method":"mortar|adhesive"}
- {"type":"tile_bond","value":MPa}
- {"type":"faucet_flow","value":ℓ/min,"fixture":"세면기|샤워기|욕조|싱크대"}
- {"type":"hot_water_temp","value":℃,"design_value":℃ 또는 null}
- {"type":"joint_spacing","value":m,"location":"roof|parking","insulated_or_cold":bool,"in_design":bool}
- {"type":"joint_width","value":mm,"in_design":bool}
- {"type":"bath_threshold","value":mm,"design_value":mm 또는 null}
- {"type":"tree_size","value":측정 규격,"design_value":설계 규격}
- {"type":"tree_dead_ratio","value":고사 가지 비율(0~1)}
- {"type":"wiring_length","value":cm,"contact_risk":bool}
- {"type":"design_compare","item":"항목명","value":측정값,"design_value":설계값,"higher_is_better":bool}"""


def _f(m, k):
    try:
        return float(m.get(k))
    except (TypeError, ValueError):
        return None


def evaluate(measurements):
    """반환: [{rule, article, verdict('하자'|'비하자'), detail}]  (판단 불가 항목은 생략)"""
    out = []
    for m in measurements or []:
        t, v = m.get("type"), _f(m, "value")
        if v is None:
            continue
        R = lambda rule, art, verdict, detail: out.append(dict(rule=rule, article=art, verdict=verdict, detail=detail))
        if t == "crack_width" and m.get("material", "concrete") == "concrete":
            if v >= 0.3:
                R("R7-1", "제7조①", "하자", f"콘크리트 균열폭 {v}mm ≥ 0.3mm")
            elif m.get("leak") or m.get("along_rebar") or m.get("through"):
                why = "누수 동반" if m.get("leak") else ("철근 방향" if m.get("along_rebar") else "관통균열")
                R("R7-2", "제7조②", "하자", f"균열폭 {v}mm < 0.3mm이나 {why}")
            else:
                R("R7-1", "제7조①", "비하자", f"콘크리트 균열폭 {v}mm < 0.3mm, 누수·철근방향·관통 아님")
        elif t == "tile_backfill" and m.get("method", "mortar") == "mortar":
            R("R18-2", "제18조②", "하자" if v < 80 else "비하자", f"떠붙이기 뒤채움 {v}% {'<' if v < 80 else '≥'} 80%")
        elif t == "tile_bond":
            R("R18-3", "제18조③", "비하자" if v >= 0.392 else "하자", f"접착강도 {v}MPa {'≥' if v >= 0.392 else '<'} 0.392MPa")
        elif t == "faucet_flow":
            lim = 3.0 if m.get("fixture") == "세면기" else 4.0
            R("R27-4a", "제27조제4호", "하자" if v <= lim else "비하자", f"{m.get('fixture','수전')} 토출량 {v}ℓ/min {'≤' if v <= lim else '>'} {lim}ℓ/min")
        elif t == "hot_water_temp":
            d = _f(m, "design_value")
            if d:
                lim = 0.8 * d
                R("R27-4b", "제27조제4호", "하자" if v <= lim else "비하자", f"급탕온도 {v}℃ {'≤' if v <= lim else '>'} 설계온도의 80%({lim:.1f}℃)")
            else:
                R("R27-4b", "제27조제4호", "하자" if v < 43 else "비하자", f"급탕온도 {v}℃ {'<' if v < 43 else '≥'} 43℃(설계기준 없음)")
        elif t == "joint_spacing" and not m.get("in_design", False):
            if m.get("location") == "parking":
                lim = 6.0
            else:
                lim = 2.5 if m.get("insulated_or_cold") else 4.0
            R("R11-3", "제11조③", "하자" if v > lim else "비하자", f"줄눈 간격 {v}m {'>' if v > lim else '≤'} {lim}m")
        elif t == "joint_width" and not m.get("in_design", False):
            R("R11-3", "제11조③", "하자" if v < 3 else "비하자", f"줄눈 폭 {v}mm {'<' if v < 3 else '≥'} 3mm")
        elif t == "bath_threshold":
            d = _f(m, "design_value")
            lim = d if d else 50.0
            R("R17-1", "제17조①", "하자" if v < lim else "비하자", f"욕실 문턱 {v}mm {'<' if v < lim else '≥'} {lim:g}mm")
        elif t == "tree_size":
            d = _f(m, "design_value")
            if d:
                lim = 0.9 * d
                R("R33", "제33조", "하자" if v < lim else "비하자", f"조경수 규격 {v} {'<' if v < lim else '≥'} 설계의 90%({lim:g})")
        elif t == "tree_dead_ratio":
            R("R30-1", "제30조①", "하자" if v >= 2 / 3 else "비하자", f"고사 가지 비율 {v:.2f} {'≥' if v >= 2/3 else '<'} 2/3")
        elif t == "wiring_length":
            ok = v <= 30 and not m.get("contact_risk", False)
            R("R23-2", "제23조②", "비하자" if ok else "하자", f"노출 배선 {v}cm, 접촉 우려 {'없음' if not m.get('contact_risk') else '있음'}")
        elif t == "design_compare":
            d = _f(m, "design_value")
            if d is None:
                continue
            hib = m.get("higher_is_better", True)
            bad = v < d if hib else v > d
            R("R-design", "제2조제1항제6호", "하자" if bad else "비하자",
              f"{m.get('item','항목')} 측정 {v} vs 설계 {d} → {'설계 미달' if bad else '설계 충족'}")
    return out


def decide(findings):
    """규칙 결과 종합(단방향): 수치 기준 위반이 하나라도 있으면 '하자'로 확정.
    기준을 위반하지 않았다는 결과는 '그 기준으로는 하자가 아니다'는 뜻일 뿐 다른 사유의 하자를 배제하지 않으므로
    판정을 강제하지 않고 판정 단계(LLM)에 정보로만 전달한다."""
    if any(f["verdict"] == "하자" for f in findings or []):
        return "하자"
    return None


if __name__ == "__main__":
    print(evaluate([{"type": "crack_width", "value": 0.2, "leak": True}, {"type": "faucet_flow", "value": 3.0, "fixture": "세면기"},
                    {"type": "design_compare", "item": "고무칩 두께", "value": 85, "design_value": 95}]))
