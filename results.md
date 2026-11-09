| Date | Change | Questions | hit@1 | hit@3 | hit@5 | hit@8 | MRR |
|---|---|---|---|---|---|---|---|
| 2026-10-05 | Eval v1: 26 easy questions (old baseline, with the leak) | 26 | 85% | 96% | 100% | 100% | 0.901 |
| 2026-10-05 | Eval v2 (52 questions), before removing the leak | 52 | 75% | 87% | 88% | 92% | 0.802 |
| 2026-10-05 | Leak removed: typo-fix vocabulary no longer reads eval_questions.json | 52 | 73% | 87% | 92% | 92% | 0.796 |
| 2026-10-09 | Calendar month regex fixed (fev, avril): 6 missing lines indexed, 498 chunks | 52 | 73% | 87% | 92% | 92% | 0.796 |
| 2026-10-09 | Enumeration questions get 25 chunks; archived documents (2017 brochure) excluded by default | 52 | 73% | 87% | 92% | 92% | 0.796 |
| 2026-11-09 | Clean env rebuild: chunks + embeddings regenerated with status field (pre-FastAPI checkpoint) | 52 | 73% | 87% | 92% | 92% | 0.796 |
| 2026-11-09 | Gemini client timeout 30 s in ask.py, models reordered (flash-lite first, 3.8-flash removed): generation only | 52 | 73% | 87% | 92% | 92% | 0.796 |
