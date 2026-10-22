"""실험 설정. API 키는 여기 쓰지 말고 환경변수(ANTHROPIC_API_KEY, OPENAI_API_KEY)로 넣으세요."""
import os

# 사용할 모델명: 각 사 문서(docs.claude.com / platform.openai.com/docs/models)에서 최신 이름을 확인해 바꿔 넣으세요.
MODELS = {
    "claude": os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5"),
    "gpt": os.getenv("OPENAI_MODEL", "gpt-5.1"),   # 예시값. 실제 사용 가능한 모델명으로 교체
}
TEMPERATURE = 0.0          # 재현성을 위해 0
MAX_TOKENS = 3000

KB_REG = "data/kb_regulation.json"
KB_GJ = "data/kb_gongjong.json"
CASES = "data/cases.jsonl"   # build/build_cases.py 로 생성 (원문 포함, 저장소에는 미포함)
OUT_DIR = "results"

TOP_K = 6                  # 검색해서 모델에 넘길 조문 수
# 판정 시점의 고시 버전: 사례에 인용 버전이 있으면 그것을, 없으면 판본별 기본값을 사용
EDITION_DEFAULT_VERSION = {2022: "v2021", 2024: "v2021", 2026: "v2025"}
CITED_TO_VERSION = {"2021. 12. 9.": "v2021", "2025. 2. 3.": "v2025"}

# 실험 조건
CONDITIONS = ["direct", "rag", "agent"]
