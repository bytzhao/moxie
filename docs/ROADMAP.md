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
- [x] `sense` column on `hsk_vocab`; sense-only duplicates collapsed at seed (`dedupe_senses`, 4 entries)
- static unit index S1 (PRD §VIII.B)
    - unit string → ((vocab_id, pinyin, sense), ...), built from `hsk_vocab` (DB, not `hsk30.txt`)
    - builder in `generation.py` takes a session (testable against the test DB); cached wrapper supplies the production session, once per server process
    - passed down as an argument to segmenter + resolution module; never built at import (`moxie.db` is gitignored, so CI has no DB)
    - document in README/CONTRIBUTING: re-seed → restart the server
    - replaces `data/polychars.txt`: remove the file and `POLY_CHARS`
- selection module *(name TBD)* — recency scoring + per-FPG structures (PRD §VII, §VIII.B)
    - Time Pressure component $T$
    - Relative Interaction Pressure $I$ (encounter density derived from `Appearances` log, PRD Decision Log §3; $D_e = 0$ with zero FPGs)
    - Historical Memory $H$ (weighted memory-score decay, 0.5-seed edge case)
    - combine into $R$, sort descending, random tie-break
    - build P1 (frontier IDs) / P2 (non-frontier IDs) / P3 (new-word ID → pinyin) / P4 (prompt rows: ID → chars, pinyin, sense)
    - tests (toy AVD rows in, sets out)
- new-word selection: pool + ordering
    - pool: lowest HSK level that still has Not Encountered words (calibration tags the user's own level Learning, so this starts at level + 1)
    - ordering within the pool is undecided; random is the placeholder
    - candidate: `frequency` column on `hsk_vocab`, populated at seed time from an external corpus list
        - jieba `dict.txt` (word / count / POS per line, simplified)
        - SUBTLEX-CH (subtitle-corpus word frequencies)
        - HSK entries missing from the list need a fallback (rank last, or random among themselves)
- `backend/segmenter.py` — rewrite as pure BiMM module (PRD §VIII.C step 4)
    - inputs: passage, S1, eligible set $E$ as arguments; no DB access
    - FMM + BMM against the whole HSK word list
    - string-level checks: hallucinated (a), word-level not encountered (b)
    - FMM/BMM choice in-module: fewer string-level errors → fewer units → fewer single-char units → BMM
    - return one segmentation + collected errors as data (not raised one at a time)
    - remove frontier count from `validate_seg`, retire `gen_pinyin`
    - fix duplicate-guard slip in the frontier branch (moot once frontier moves out, but note for tests)
    - update `tests/test_segmenter.py`
- resolution / validation module *(name TBD)* — PRD §VIII.C steps 5–6
    - per-unit resolution: single candidate → direct; same-pinyin + exactly one eligible → shortcut; else queue
    - blind resolution request: all HSK candidates, ascending `vocab_id` order, no labels, no eligibility info; separate fresh request per attempt
    - validate parsed option numbers against each unit's candidate count; map numbers → vocab IDs
    - ID-level checks in one pass: reading/sense-level not encountered (c, its own error type), distinct-frontier-ID count (d); collect both
    - serialize ordered ID sequence as answer key; derive new-word hints from P3
    - tests
- `backend/llm.py` — transport + templates only
    - prompt builders: generation (lists with pinyin + sense), edit/reprompt (from plain lists of offending units / frontier shortfall), resolution (numbered options)
    - send a message list, return text; parse resolution reply into option numbers
    - no knowledge of pipeline error types
- `backend/generation.py` — orchestration only (mirrors `grading.py`)
    - call selection → `llm.py` → segmenter → resolution/validation in order
    - own the per-request message list (append assistant replies + edit prompts, resend)
    - retry loop: string-level failures → immediate reprompt; ID-level failures → one combined reprompt; 2-strike abort
    - decide: do resolution calls count toward the retry budget? (PRD §VIII.C open item)
    - write to `Passages` table (answer key, state=SENT_TO_USER); assemble response incl. `new_word_hints`
    - fix docstring: sort by *highest* recency score
- single source of truth for HSK word strings
    - BiMM matches against `HSK_VOCAB` (from `hsk30.txt`) while S1 is built from the DB; word sets are identical today (dedupe removed no word strings)
    - point the segmenter at S1's keys so the two can't drift
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
    - fix: `UNIQUE` constraint on the columns that actually identify an entry — (word, pinyin, sense) is now unique after `dedupe_senses` — + insert-or-ignore, or a guard clause
    - see TODO in `data/seed.py`

*Deferred (post-PoC):*
- `GET /api/vocab` (open AVD endpoint)
- dashboard page, usage history page
- decoding-cost ordering for new words
    - rank candidates by how many characters/readings they add that the user doesn't already decode (学生 is ~free if 学 and 生 are known)
    - open design question: prefer low-cost (easy on-ramp) or high-cost (more new decoding material)?
    - computed at selection time from the AVD, not stored, so no upkeep as words are encountered
