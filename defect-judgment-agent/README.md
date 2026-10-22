# Regulation-Grounded LLM Agent for Apartment Defect Assessment

Data and code for the paper *A Regulation-Grounded Large Language Model Agent for Defect Assessment in Korean Apartment Housing: Combining Retrieval, Executable Rules, and a Warranty-Period Tool* (C. Lee, 2026, under review).

The agent judges apartment defect cases against the Korean defect-criteria notice (MOLIT) and Table 4 of the Enforcement Decree of the Multi-Family Housing Management Act. It combines LLM fact extraction and judgment with version-filtered article retrieval, an executable rule engine for numeric criteria, and a deterministic warranty-period lookup.

## Contents

| Path | Description |
| --- | --- |
| `data/labels.jsonl` | 287 cases from the 2022, 2024 and 2026 casebooks (262 judgments + 25 mediations): casebook edition and page, title, defect label, defect type, cited articles and notice version, trade, warranty period. **Case texts are not included.** |
| `data/contrast.jsonl` | 67 contrast cases varying a measured value around six mandatory numeric criteria, with gold labels. |
| `data/kb_regulation.json` | Article-level knowledge base of the defect-criteria notice, three versions (2021-1262, 2025-58, 2026-360). Long articles are stored in condensed form that keeps all paragraphs, items and numeric values. |
| `data/kb_gongjong.json` | 95 sub-works (trades) with examples and warranty periods. |
| `code/` | Agent (`pipeline.py`, `tools.py`, `rules.py`, `llm.py`), runner (`run.py`), evaluation (`evaluate.py`), statistics and figures (`analyze.py`, `figs.py`, `extra.py`). |
| `build/` | Scripts that rebuild case texts from the official casebook PDFs. |
| `results/` | Raw outputs of every model and condition reported in the paper. |
| `figures/` | Figures, result tables and statistical tests. |

## Reproducing the reported metrics (no API key needed)

```bash
pip install -r requirements.txt
python code/evaluate.py --subset 2026   # metrics on the 2026 test set and contrast set
python code/analyze.py                  # bootstrap CIs and McNemar tests
```

## Re-running the experiments

1. Download the three casebooks published by MOLIT's Defect Review and Dispute Mediation Committee (freely available from the MOLIT website and the defect management information system) and save them as `data/raw/casebook_2022.pdf`, `casebook_2024.pdf`, `casebook_2026.pdf`.
2. Install poppler (`pdftotext`) and run `python build/build_cases.py`. This writes `data/cases.jsonl` and checks that every label matches `data/labels.jsonl`.
3. Set `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY`, then run for example:
```bash
python code/run.py --provider gpt --conditions direct rag agent
python code/run.py --provider gpt --conditions direct rag agent --split contrast
```
Model names are set in `code/config.py` (paper: `gpt-5.1-2025-11-13`, `claude-sonnet-5-5`, October 2026). Responses are cached in `.cache/`; set `RUN_TAG` for independent repeat runs.

## Conditions

| Condition | Description |
| --- | --- |
| `direct` | LLM only, no regulatory text |
| `rag` | one retrieval of articles, one judgment call |
| `agent` | fact extraction → version-filtered retrieval → rule engine → warranty tool → judgment → citation guard |
| `agent_notool`, `agent_norule`, `agent_noversion`, `agent_noguard`, `rag_noversion` | ablations |

## License

Code: MIT. Annotations, knowledge bases and contrast set: CC BY 4.0. The casebooks and regulations are not redistributed.

## Citation

Lee, C. A Regulation-Grounded Large Language Model Agent for Defect Assessment in Korean Apartment Housing. *Buildings* (under review), 2026.
