**Remaining Build Roadmap** *(sequential; see PRD §XVI for milestone framing)*

**Status:** full grading pipeline, test suite and orchestration in main left for Milestone 0.

*Milestone 0 — grading + CSM loop, no LLM:*
- `backend/levenshtein.py`
    - tone-strip + tonal-correctness check (severe if wrong)
    - retroflex/umlaut/nasal candidate-string generator (PRD §X.1)
    - keyboard-weighted Levenshtein distance vs. candidate set, slight/severe threshold classification
    - char-by-char alignment of submitted PRS against stored answer key
    - tests (structure by hand, oracles hand-traced)
- `backend/csm.py`
    - streak-based promotion logic (2/3/5 consecutive-correct thresholds)
    - slight-error demotion rules (streak loss vs. Solid/Mastered → Familiar+2)
    - severe-error demotion rules (per-tier floors, PRD §XI)
    - compound→character mirroring (demotion-only, exact-pinyin-match)
    - DB writes: `UserVocab` status/points/timestamp, `Appearances` rows (multi-char memory-score averaging)
    - tests
- `backend/grading.py`
    - main.py callee orchestrating Levenshtein distance grading and CSM
    - entire grading pipeline tests
- `backend/main.py`
    - `GET /api/health`
    - `POST /api/grade` (toy hardcoded passage + key, wired to grading.py + csm.py)
    - manual test: submit toy pinyin, inspect DB state before/after

*Milestone 1 — Claude FPG pipeline:*
- `backend/generation.py` — recency scoring
    - Time Pressure component $T$
    - Relative Interaction Pressure $I$ (encounter density derived from `Appearances` log, PRD Decision Log §3)
    - Historical Memory $H$ (weighted memory-score decay, 0.5-seed edge case)
    - combine into $R$, sort AVD, select frontier + new-word set per length-tier caps (PRD §VIII)
- `backend/llm.py`
    - thin Claude API call wrapper
- `backend/generation.py` — orchestration
    - prompt construction from encountered/frontier dicts (PRD §VIII template)
    - validation loop: length check, frontier-count check, hallucination check, retry prompts, 2-strike abort
    - polyphone resolution pass (bounded table + Claude disambiguation call)
    - write to `Passages` table (answer key, state=SENT_TO_USER)
- `backend/main.py`
    - `POST /api/fpg` route
    - integration test: real Claude passage generation end to end into DB
- `frontend/index.html`
    - length selector, Generate button, fetch to `/api/fpg`
- `frontend/decode.html`
    - render passage, basic submit (no caret yet), fetch to `/api/grade`

*Milestone 2 — UI polish:*
- `frontend/decode.html`
    - real-time caret + color-coding keystroke handler (space/tone-digit terminator, PRD Decision Log §2)
- `frontend/results.html`
    - color-coded char comparison + promotion/demotion summary render
- shared CSS pass across all three pages
- optional: frontend length-precheck before POST (PRD §VIII)

*Deferred (post-PoC):*
- `GET /api/vocab` (open AVD endpoint)
- dashboard page, usage history page
