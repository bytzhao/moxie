# Moxie
### A Claude-enabled Chinese literacy training platform.

**Product Phase:** 1 - initial PoC prototype
--

**Overview:** Moxie 1.0 is a Claude-enabled Mandarin decoding-fluency trainer designed to prompt the user with challenging texts. These are produced by taking into account their literacy level, which is gauged from their vocabulary arsenal, grammatical and syntactical maturity, rhetorical understanding, etc. While the desire is eventually to mature Moxie into an all-rounded language trainer that tests comprehension through translation as well, the first phase is solely concerned with the decoding of Chinese characters into pinyin. 

***For any and all information concerning phase 1 implementation, features, etc., please consult the most recent version of the Product Requirements Document, `docs/PRD_0.3.md`. Version 0.3 also serves as the dynamic version for any minute edits throughout the development of the initial PoC, and edits are cataloged at the top of the file.***

**Current Status:**
1. Segmentation & pinyin answer key generation pipeline finished, incl. `tests/test_segmenter.py`.
2. PoC database schema finalized in `backend/models.py`
3. One-user-supported seeding functionality implemented in `data/seed.py`
4. Current task: Milestone 0 — grading & CSM pipeline (no LLM yet).

**Remaining Build Roadmap** *(sequential; see PRD §XVI for milestone framing)*

*Milestone 0 — grading + CSM loop, no LLM:*
- `backend/grading.py`
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