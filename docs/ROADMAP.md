**Remaining Build Roadmap** *(sequential; see PRD §XVI for milestone framing)*

**Status:** Milestone 0 grading pipeline (`levenshtein.py`, `csm.py`, `grading.py`) complete with test suites. Remaining for Milestone 0: FastAPI routes in `main.py`.

*Milestone 0 — grading + CSM loop, no LLM:*
- [x] `backend/levenshtein.py`
    - tone-strip + tonal-correctness check (severe if wrong)
    - retroflex/umlaut/nasal candidate-string generator (PRD §X.1)
    - keyboard-weighted Levenshtein distance vs. candidate set, slight/severe threshold classification
    - char-by-char alignment of submitted PRS against stored answer key
    - tests (structure by hand, oracles hand-traced)
- [x] `backend/csm.py`
    - streak-based promotion logic (3/3/5 consecutive-correct thresholds)
    - slight-error demotion rules (streak loss vs. Solid/Mastered → Familiar+2)
    - severe-error demotion rules (per-tier floors, PRD §XI)
    - compound→character mirroring (demotion-only, exact-pinyin-match)
    - DB writes: `UserVocab` status/points/timestamp, `Appearances` rows (multi-char memory-score averaging)
    - tests
- [x] `backend/grading.py`
    - main.py callee orchestrating Levenshtein distance grading and CSM
    - entire grading pipeline tests
- [x] `backend/main.py`
    - `GET /api/health`
    - `POST /api/grade` (toy hardcoded passage + key, wired to grading.py + csm.py)
    - manual test: submit toy pinyin, inspect DB state before/after

*Milestone 1 — Claude FPG pipeline:*
- `backend/generation.py` — recency scoring
    - Time Pressure component $T$
    - Relative Interaction Pressure $I$ (encounter density derived from `Appearances` log, PRD Decision Log §3)
    - Historical Memory $H$ (weighted memory-score decay, 0.5-seed edge case)
    - combine into $R$, sort AVD, select frontier + new-word set per length-tier caps (PRD §VIII)
- new-word selection: pool + ordering
    - pool: lowest HSK level that still has Not Encountered words (calibration tags the user's own level Learning, so this starts at level + 1)
    - ordering within the pool is undecided; random is the placeholder
    - candidate: `frequency` column on `hsk_vocab`, populated at seed time from an external corpus list
        - jieba `dict.txt` (word / count / POS per line, simplified)
        - SUBTLEX-CH (subtitle-corpus word frequencies)
        - HSK entries missing from the list need a fallback (rank last, or random among themselves)
- `backend/llm.py`
    - thin Claude API call wrapper
- `backend/generation.py` — orchestration
    - prompt construction from encountered/frontier dicts (PRD §VIII template)
    - validation loop: length check, frontier-count check, hallucination check, retry prompts, 2-strike abort
    - polyphone resolution pass (bounded table + Claude disambiguation call)
    - write to `Passages` table (answer key, state=SENT_TO_USER)
- `data/polychars.txt` provenance
    - current table (389 entries) was Claude-generated and is unverified; PRD §XIX.4 scopes a bounded ~100-entry table
    - derive it from multi-reading entries in `hsk30.txt` via a prep script (same pattern as `prepare_hsk30.py`), so the table has provenance by construction
    - add tests for the derivation
- answer-key serialization: same-reading / different-sense resolution
    - `hsk_vocab` splits entries by sense, not just reading (e.g. 好 → 3384 hao3 L1 Adj, 3385 hao3 L2 Adv, 3386 hao4 L4 V)
    - grading treats same-reading IDs as equivalent, but CSM tracks each `vocab_id` separately in `user_vocab`
    - designated frontier/new words already carry a known `vocab_id`; ambiguity only arises for words Claude uses incidentally
    - decide a deterministic tie-break rule for picking the ID
- `Passages` table: add a passage-text column
    - `answer_key` is punctuation-stripped vocab IDs, so the displayed passage (with punctuation) can't be reconstructed from it
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

*Tech debt (address before `user_vocab` holds real progress):*
- `data/seed.py` is not idempotent: re-running duplicated the entire `hsk_vocab` table (22,182 rows vs. 11,091)
    - fix: `UNIQUE` constraint on the columns that actually identify an entry (word + reading alone isn't enough, see 好 above) + insert-or-ignore, or a guard clause
    - see TODO in `data/seed.py`

*Deferred (post-PoC):*
- `GET /api/vocab` (open AVD endpoint)
- dashboard page, usage history page
- decoding-cost ordering for new words
    - rank candidates by how many characters/readings they add that the user doesn't already decode (学生 is ~free if 学 and 生 are known)
    - open design question: prefer low-cost (easy on-ramp) or high-cost (more new decoding material)?
    - computed at selection time from the AVD, not stored, so no upkeep as words are encountered
