# Moxie: Product Requirements Document

**Product Phase:** 1 - initial PoC prototype
**Document Version:** 0.3
**Date:** September 15th, 2026

*Version history note: this file serves as a dynamic version that will accompany the entirety of the first phase of development.*
- September 15th, 2026: removed func-word allow-list as Phase 1 priority:
    - Essentially all are already in the HSK 3.0 vocabulary list (static file `data/hsk30.txt`).
    - Tracking elementary users' grasp of function words is not important at this phase since Moxie is still for personal use primarily.
- September 29th, 2026: locked down grading-pipeline internals and Results Page rendering, following a CSM/Levenshtein architecture discussion:
    - Results Page (Section VI.3) now explicitly renders both the PRS and the answer key, character-colored, so the user can visually cross-reference mistakes against the correct decoding.
    - `POST /api/grade` (Section XIII) now also returns the answer key post-grading - consistent with, not a reversal of, the existing "answer keys stay server-side until grading" decision (Section XIX).
    - `levenshtein.py` split out of `grading.py` as its own file (Section XIV); `grading.py` is now the orchestrating layer only, mirroring the existing `generation.py`/`segmenter.py` split.
- October 2nd, 2026: simplified Levenshtein distance computation sub-pipeline as follows:
    - only one error is tagged and returned to the frontend following grading, therefore...
        - combination strings of multiple of the slight errors are NOT considered. Only the 4 strings (original, and one per each of the slight errors) are compared against for distance.
        - if a tone error exists, no further analysis is done.
    - typos are not considered for chars w/ pinyin less than 4 characters (not including the tone mark)
        - in these cases, simple equality is checked against the 4 strings. No Levenshtein distance computation is necessary and hence any real typos are treated as severe errors.
    - matching is exact-match-first: the user's input is checked for equality against all 4 strings before any distance is computed. Only the *original* ever gets a real distance check (for typo, pinyin 4+ chars only, after all 4 equality checks fail) - the 3 slight-error variants are equality-only, never distance-matched.
        - reasoning: an exact-match-first pass lets you conclude DEFINITIVELY that a given slight error was not made once its equality check fails. Allowing distance (not just equality) against the variants would be too lenient - it'd let a near-miss masquerade as a confirmed slight error instead of falling through to severe where it belongs.
- October 4th, 2026: finalized `calc_lev_dist`'s weighted edit-distance model (the real typo-vs-severe distance check described above, for pinyin 4+ chars):
    - substitution cost is no longer flat; it's weighted by `ch_dist`, a normalized Euclidean distance between two letters' coordinates on a QWERTY grid with realistic ANSI row stagger (`QWERTY_COORDS`).
    - added a transposition operation (Damerau-Levenshtein style: detects an adjacent swapped pair, costs it via `ch_dist` between the swapped keys) as a fourth candidate inside the same `min()` as insert/delete/substitute, rather than short-circuiting around them.
    - typo/forgot classification now compares a length-normalized distance (`calc_lev_dist(...) / max(len(py), len(user_py))`) against `LEV_DIST_THRESHOLD`, currently set to `0.25` pending further empirical calibration against real typing data.
- October 7th, 2026: slight edits to CSM framework...
    - Learning needs a streak of 3 to promote to Familiar (same as Familiar)
    - CSM protocol for newly-encountered words explicitly defined as promote to Learing base, *regardless* of whether an error was permitted.
- October 22nd, 2026: reworked the new-vocabulary introduction policy (Section VIII):
    - the trigger is now an absolute cap on Learning words only, $C_L = 25$, replacing the flat Learning + Familiar thresholds (8 / 15). Familiar words are no longer counted, since they aren't truly new and demotions already refill Learning when the user struggles.
    - a percentage-of-encountered-words cap was considered and rejected: it grows with AVD size, while the real constraint (how often each Learning word is recycled, ~$C_L / k$ passages) depends on passage throughput.
    - $C_L = 25$ targets a ~5-passage reappearance gap (3 min, 6–7 max) at ~2 passages/day for the 50–100 and 100–150 length tiers, assuming ~half of targets are Learning (to be verified against the `Appearances` log).
    - the calibration backlog (a full HSK level tagged Learning at the user's beginning seed) counts as real Learning words, so it acts as an extended placement phase before any new words are introduced.
    - new words are drawn from the lowest HSK level that still has Not Encountered words; ordering within that level is random for now (frequency-based and decoding-cost ordering logged in `ROADMAP.md`).
    - fixed the baseline calibration entry in the Decision Log (Section XIX) to match Section VII: below level → Familiar, at level → Learning.
- October 23rd, 2026: pinned down frontier-word selection and validation (Sections VII, VIII, XI, XIII, XIX):
    - **frontier words** are now defined explicitly: $M$ new words first, then the top $N - M$ encountered words by recency (any status), where $N$ is the tier maximum. The tier minimum is the validation floor.
    - recency sort is *descending* (high $R$ = most in need of review); ties are broken randomly, since `hsk30.txt` gives no order within a level. $D_e = 0$ when there have been zero FPGs.
    - the encountered list and frontier list sent to the model partition the user's known words (plus new words). Only the words are sent, without pinyin.
    - the frontier minimum is counted after segmentation; new words count toward it but are not separately required. Possible segmentation masking is logged as a known risk.
    - out-of-list validation explicitly covers both hallucinated non-HSK units and valid-but-unencountered HSK units.
    - new words that appear in the passage are sent to the frontend with their resolved pinyin as hints, a scoped exception to "answer keys never leave the server". The Not Encountered → Learning flip happens at grading, only for new words that appeared.
    - prompt wording updated: frontier words are no longer described as "learning" words, and the no-new-vocab rule now refers to the two lists.
- October 24th, 2026: rebuilt the FPG validation pipeline around vocab IDs (Sections VIII, IX, XII):
    - **reverses** the October 23rd "words only, no pinyin" decision: both lists now go to the model with pinyin, so it knows which reading of a string is allowed.
    - validation is split into string-level checks (hallucinated, not encountered; reject-only) after segmentation, and ID-level checks (ineligible reading, frontier count) after ID resolution. The frontier count now happens at the very end, on distinct frontier IDs.
    - pinyin and sense ambiguity are resolved in one model call with numbered candidates drawn from *all* HSK readings, so an ineligible reading is caught rather than silently forced into an eligible one. Sense-only ambiguity with exactly one eligible candidate is resolved without asking the model.
    - `hsk_vocab` gains a `sense` column (part of speech); sense-only duplicates are collapsed at seed time (4 entries removed).
    - the retry loop is stateless: an edited passage reruns steps 4–6 from scratch.
    - sense-aware validation deferred.
    - added the identity model, data-structure table (static unit index S1; per-FPG P1–P4) and step-by-step technical pipeline (VIII.A–C). Prompts carry pinyin *and* sense; resolution returns option numbers, never raw IDs; `polychars.txt` superseded by S1.
- October 25th, 2026: settled FPG module boundaries and error handling (Sections VIII.C, XIV):
    - `segmenter.py` becomes a pure BiMM module (passage, S1 and $E$ as arguments; no DB access) that also makes the FMM/BMM choice: validity (error type, then count, when both fail), then fewer units, then fewer single-character units, then BMM. `gen_pinyin` retired.
    - two distinct not-encountered errors: word level (step 4, no reading of the string is eligible) and reading/sense level (step 6, the resolved ID is ineligible).
    - string-level failures short-circuit straight to a reprompt; ID-level failures (ineligible reading, frontier count) are collected and reported in one combined prompt. Validators return errors as data rather than raising them one at a time.
    - ID resolution is blind: a separate fresh request with no eligibility information, options in ascending `vocab_id` order, no labels.
    - `generation.py` is orchestration only and owns the per-request message list; `llm.py` is transport + templates only; selection and resolution/validation are their own modules (names TBD).
- October 27th, 2026: revised segmenter input handling and the FMM/BMM error tie-break (Section VIII.C step 4):
    - punctuation and whitespace are no longer stripped; each is its own unit and is skipped by the string-level checks. Latin letters and digits are flagged as hallucinated.
    - when both segmentations fail, the reported error is chosen by type first (not-encountered outranks hallucinated), then by count, since hallucination is segmentation-dependent.

## I. Content & Objectives
Broadly, the purpose of Moxie is two-fold:
1. 
    I hope this application can be of actual use personally in the primary aspects of improving Mandarin literacy: reading and character recognition, as well as speaking and character recall. The advantage of an AI-integrated program like Moxie is not only the ability to rigorously and actively update and probe the user's literacy level at any given point in time, but also to specialize to the user's specific language needs. This could be in the form of familiarity with the jargon of a specific field, comfortability with a particular medium of writing (i.e. newspapers, novels, opinion articles), or training specific aspects of literacy improvement like rhetorical structures, literary allusions, idioms, cultural references, etc. Specifically given my placement into CHN 303W, I am hoping Moxie will particularly help in expanding my vocabulary and broader usage of more complex sentence structures, rhetorical devices, idioms, allusions, etc., both in character recognition while reading as well as in speaking. 

2. 
    I hope that my interest in this project will prove to be rather long term, and that its development will also serve as an invaluable opportunity for software development and project management experience. As a preemptive note on the usage of AI, it is my wish that this project can be done with limited usage of it in the actual coding. The primary goal of Claude in this endeavor will be to provide scaffolding in the realms of ideation and actual development. For example, comprehensive discussion on scope, the generation of a skeleton for PRD documentation, and stack/architecture suggestions all fall in the realm of Claude's expertise. However, it is my wish and hope that the vast majority of the actual writing of code will be my own, which will force line-by-line analysis and understanding the implementation front-to-back, end-to-end. When it comes to debugging, I aim to make equally fervent promises in the spirit of not robbing myself of the best opportunities for deep problem solving. However, the gray area here is rather more obscure, and for the tradeoff between productivity and learning I am ready to make certain sacrifices.


## II. Product Framing
Moxie 1.0 is a Claude-enabled Mandarin decoding-fluency trainer designed to prompt the user with challenging texts. These are produced by taking into account their literacy level, which is gauged from their vocabulary arsenal, grammatical and syntactical maturity, rhetorical understanding, etc. While the desire is eventually to mature Moxie into an all-rounded language trainer that tests comprehension through translation as well, the first phase is solely concerned with the decoding of Chinese characters into pinyin. 


## III. Success & Kill Criteria
The following are the goals I wish to accompish during and by the end of this phase of development, concerning both the functionality of the website and expounding on the broader meta-project objectives stated in section I.2:
- **Consistency:** in the last two weeks before the start of the fall 2026 semester, I hope for nearly daily contributions to documentation, design, and eventually the actual codebase. Following the start of the semester, a minimum commitment of 2x per week, with in-depth, 1-hr minimum long sessions per should be realistically achievable.
- **SWE Skills:** following a successful end-to-end PoC implementation, I expect to be able to trace through the entire codebase and explain each module and pipeline. To this end, I aim to be (at least) semi-literate in HTML, CSS and Javascript frontend syntax, the API surface, the vocabulary database calls, etc. Fundamentally, I should have a thorough understanding of all elements of the system's operational behavior in the state-change loop that governs Moxie's prompting, the user's response retrieval, and the program's assessment and updates to the user's literacy profile. 
- **Usage Retention:** following a successful end-to-end PoC implementation, I expect to use the website at least on a weekly weekend basis. 
- **Post-PoC Expansions:** following a successful end-to-end PoC implementation, it is my hope that I remain excited about later-phase functionality expansions and am willing to immediately undertake feature expansions.

The following are kill criteria that during or after implementation are enough to inform a full stop on the project or, at the very least, trigger a meaningful pivot:
1. **Retention:** two weeks following end-to-end loop working without voluntary usage three times
2. **Learning:** pasting Claude Code output not reconstructable from scratch
3. **Calendar:** this phase of development isn't finished by **end of September at the absolute latest** 
Development blocks caused by (1) specifically to implementation complexity and (2) persist beyond a one-week time-frame, should be addressed at the product scope level rather than remedied through increased usage of Claude for software shortcuts.


## IV. Scope
The following functionality are *included* in this phase of development, enumerated here in general and expounded on further in later sections where appropriate:
1. 
    **Adaptive Vocabulary Database (AVD):** primary tracking mechanism for user's literacy level. Contains a pre-seeded list (the HSK 3.0 vocabulary list) of both compound words and individual characters, each tagged with the user's interaction level ranging from "Not Encountered Yet" to "Mastered", as well as a time-stamp for the last encounter by the user and/or encounter density score in last few sessions compared to other characters in the database.
    - **Character Status Monitor (CSM) System:** the cohensive framework used to apply updates to characters given a user's decoding response. Consists of (1) hard rules for promotion and demotion, (2) a familiarity tiers system tagged to both compound words and individual characters and (3) a points system 
2.  
    **Frontier Passage Generation (FPG):** capability enabled by Claude, informed by the AVD as well as user-identified passage length specification.
    - **Tone Marks:** denoted 1-4 by convention with 0 representing the static tone, appended to the end of each character's pinyin.
    - **Segmentation Answer Keys:** in the interest of full flexibility, answer keys are stored using a custom segmentation algorithm.
3. 
    **Real-Time Input Tracking:** As the user types decodes the prompt, their progress per individual character is tracked via a dynamic caret that responds to individual tone mark inputs (valid numbers 1 through 4 and 0 reserved for the static tone), and a color coding mechanism that advances through characters you have completed decoding.

The following functionality are *not included* in this phase of development, enumerated here:
1. **Tone mark flexibility:** PoC will prioritize *mandatory* inclusion of tone marks for each character in the user's response. Later phases may implement a togglable setting for tone marks; for example, (1) all characters, (2) none, and (3) only frontier words above a certain CSM designated tier.  
2. **Text Medium, Theme, & Difficulty Mode:** Besides the state of the AVD and a user-desired text length, no other factors are considered in FPG. 
3. **Smart Char-by-char Analysis:** While future iterations may include algorithms to avoid over-penalizing "one-off" mistakes by the user (i.e. forgetting a tone mark for one character), this initial phase will deterministically treat tone numbers as separators between characters and match the user's pinyin char-by-char.
4. **Compound Word Analysis:** While the answer key is encoded using custom segmentation, spaces are nonbearing for the CSM system and the user is neither rewarded or penalized for their choice of organizing compound words. 
5. **Characters, Syllables & Grammatical Items Databases:** While HSK provides four lists for the core linguistical elements, the PoC prototype will only employ the vocabulary list.
6. **Real-Time Analysis & Feedback:** While the idea of real-time input tracking takes inspiration from typing games, real-time analysis and correct/incorrect inputs will not be communicated to the user in any way. The tracking serves only as a UI design inclusion that (1) helps the user keep track of their progress through the text prompt and, rather less importantly, (2) contributes aesthetic value to the page. 
7. **Traditional & Simplified Text Settings:**: This initial phase selfishly only supports simplified Mandarin characters. 


## V. Core Loop
The heart of Moxie is a loop automaton that tracks and updates the user's literacy based on defined parameters relating to Mandarin proficiency. For phase one, the sole parameter of interest is the **recognition of characters and words.** This loop has five primary components. (1) The Initial Literacy State (ILS) is captured by the state of the AVD. AI-enabled analysis informed by the ILS then facilitates (2) FPG and prompts the user for their response. The user then provides a (3) Pinyin response String (PRS) that is evaluated using (4) CSM analysis. Applying the appropriate promotions and demotions eventually yields the (5) Updated Literacy State (ULS), which like the ILS, is equivalently captured by the state of the AVD and is therefore identical in structure. 


## VI. User Interaction Specification
Moxie 1.0 carries three screens the user interacts with, listed below:
1. **FPG Initialization Page:** app's designated landing page. The user inputs a desired passage length and pushes a "Generate" button that initializes FPG.
2. **Decoding Page:** facilitates user's interaction with the frontier passage. Real-time input tracking is built in. User inputs their PRS and pushes a "Submit" button for evaluation.
    - The passage is rendered with no spaces as appropriate and consistent with conventional Mandarin texts
    - The ULS is automatically generated when the user presses "Submit"
3. **Results Page:** informs user of PRS correctness following backend answer key analysis and CSM-facilitated AVD updates through color-coded character-by-character comparisons and a passage summary enumerating words tested and all promotions/demotions.
    - Both the PRS and the answer key string will be shown, this time with spaces between vocab units. In this phase of development, the user's missed characters will simply be color-coded red while the correct characters are color-coded green. In the answer key, the corresponding, correct pinyins for each of the missed characters are highlighted in a third color (TBD), so the user can visually parse the text easily and remedy the errors.
    - An "Exit" button automaticlaly takes the user back to the FPG Initialization Page again, ending the session and mirroring the backend logic of the loop automaton.

The following pages are relevant and helpful, but de-prioritized:
1. **Dashboard:** encapsulates the FPG Initialization Page, as well as extra data on user's literacy progress and retention.
2. **User-Facing AVD:** open AVD containing all characters and compound words. Each item is expandable by the user and the list is sortable by familiarity status, recency, and alphabetical pinyin.
3. **Usage History:** page containing list of N most recent FPGs user interacted with, each expandable to include all information seen in the results page at the time, in addition to a timestamp of the FPG.


## VII. Data Model
The AVD consists of a complete compound word and character vocabulary list. The list can be conceptualized as a dictionary, where each individual hanzi character/compound is paired with a tuple encapsulating all relevant fields:
1. **Pinyin:** string representation with tone marks
2. **Status:** string tier and intra-tier points tally
- The tiers are (1) Not Encountered, (2) Learning, (3) Familiar, (4) Solid, and (5) Mastered
- The tiering and subtiering points systems are described in further detail in Section XI, "The CSM System", below
3. **Last Interaction:** timestamp signifying time and date of last passage tested containing this word, updated after each appearance

Separately, a list of complete appearance tuples - storing (1) word ID, (2) session ID, (3) timestamp, and (4) memory score - are stored for each word's appearance. The memory scores are calculated after each session as follows:
- Generally, fully correct characters = 1 pt, any slight mistake = 0.5 pts, and severe errors (including skips) = 0 pts.
- For multi-character vocab units, a, average over all characters' scores summed is taken; for example, a 3-character word with one character forgotten, another with a retroflex error, and a third fully remembered in a given session will log an error score of `(1 + 0.5 + 0) / 3` = `0.5`.  

At the beginning of the FPG process, **recency scores** are calculated for each vocabulary unit that has been encountered (excluding words carrying 'Not Encountered' status). These scores are comprised of three separate components, both quantitatively derived and intuitively motivated below. Each component is a normalized value between 0 and 1. 
1. **Time Pressure:** score that, depending on when was the last interaction, enumerates the raw priority of appearance irrespective to other words
    - Given the timestamp of the last interaction, $\Delta t$ is promptly calculated
    - The exponential quantity $1 - e^{-\lambda \Delta t}$ relates this latent time interval to a pressure score normalized between 0 and 1
        - $\lambda$ is given by $\lambda = \frac{1}{c_s}$, where $c_s$ is a status coefficient given by:
        1. Learning - $c_s = 1$ ($2^0$)
        2. Familiar - $c_s = 2$ ($2^1$)
        3. Solid - $c_s = 4$ ($2^2$)
        4. Mastered - $c_s = 8$ ($2^3$)
        - This value allows for the time pressure to be eased depending on the user's status: higher mastery of the word implies a greater length of exposure, higher count of session encounters, and hence justifies a longer time interval before retesting. The opposite for new words is likewise true.
    - Therefore:
    $$
    T = 1 - e^{-\lambda \Delta t}
    $$
    - Immediately following the baseline calibration, the last interaction takes the timestamp of calibration, used to calculate $\Delta t$ until the first appearance has happened.
    - $\Delta t$ is stored as a decimal number of days.

2. **Relative Interaction Pressure:** score that, depending on the density of appearance in the most recent 50 FPGs, enumerates the relative priority of this word to others
    - An Encounter Density score $D_e$ is calculated as the appearance percentage in the last 50 FPGs, stored as a probability between 0 and 1 (*if the total history contains less than 50 total sessions, the maximum session total is simply taken; if there have been zero FPGs in total, $D_e = 0$, so $I = 1$*)
    - The Relative Interaction Pressure is simply:
    $$
    I = 1 - D_e
    $$

3. **Historical Memory:** score enumerates the user's encounter history of the word, weighing encounters based on recency
    - Given the user's $n$ most recent appearances of the word (*capped at $n \le 10$*), a historical memory $H$ is constructed by the complement to the weighted sum of memory scores aggregated by dividing by the sum of the recency weights:
    $$
    H = 1 - \frac{\sum_{i=1}^{n} w_i E_i}{\sum_{i=1}^{n} w_i}
    $$
    - $w_i$ denotes a recency weight determined solely by the appearance's ordinal position, where $i = 1$ is the most recent appearance:
    $$
    w_i = r^{\,i-1}, \quad 0 < r < 1 \quad (\text{default } r = 0.8)
    $$
    - Each weight is a fixed fraction $r$ of the one after it, so the most recent appearance always carries $w_1 = 1$. Weights are independent of wall-clock time; the time gap is handled entirely by Time Pressure, so a long break is not penalized twice.
    - History is capped at the 10 most recent appearances. Since $\sum_{i=1}^{\infty} r^{\,i-1} = \frac{1}{1-r}$ converges, older appearances contribute little anyway: at $r = 0.8$, the 10th most recent carries $w_{10} = 0.8^{9} \approx 0.13$.
    - $E_i$ denotes the memory score stored directly in the appearance database

    - *Edge case:* immediately following callibration of a word, the user has not had a formal encounter of the word. This is mediated by seeding a default value of $H = 0.5$. This is immediately overwritten after the first interaction, after which this mechanism should work perfectly.

These three components are combined to calculate an average recency score $R$:
$$
R = \frac{T + I + H}{3}
$$

All encountered vocabulary units (every status except Not Encountered) are sorted by recency score in *descending* order, since a high $R$ means the unit most needs review. The top of this list fills the frontier slots left over after new words are allotted (Section VIII), regardless of status. Status is not filtered on, because the status coefficient $c_s$ in Time Pressure already biases the ranking toward less-mastered words. Ties are broken randomly. Ties are expected right after calibration: every calibrated word shares the same $\Delta t$, $D_e = 0$ and the seeded $H = 0.5$, so they all have the same $R$. `data/hsk30.txt` tags each entry with an HSK level only and gives no order within a level, so there is no finer HSK ordering to break ties with.

It is inevitable that certain characters will be represented multiple times in the AVD, both as individal units as well as parts of other compound words. To sync the user's progress passage to passage, specifically *demotions* to characters in compound words will be mirrored with exact CSM protocol on the individual char itself, and ONLY when the pinyin is an exact match. Promotions will not reflect at all, since recognizing a character in one context does not guarantee recognition in another. Likewise, the converse, namely promotion or demotion of individual characters, will not reflect at all on any compound words that char is a part of. Carrying this to the appearance database, appearances of individual characters will be logged for every appearance of a compound word containing that character, granted that the pinyin is the same. The converse is *not* true.

Phase 1 is concerned with only one user. However, the architecture of the data is designed to accommodate multiple users already. A global, static and comprehensive `vocabulary` table houses all the words of the HSK 3.0 vocabulary list, tupled with its pinyin and tone as a string. A separate `users` table stores all users and appropriate information, including ID, email, created/joined timestamp, etc. A third list serves as a junction between individual users and their personal AVDs, storing all individual, local information pertaining the status of each vocabulary unit and mapping it to a user.

**On migration posture:** eventualy it will be the case that I would like to preserve my personal AVD through development changes and feature additions. However, for this initial phase of development no migration is necessary at all. A `seed.py` notebook builds the entire DB from scratch, and changes in schema will require a full re-seed. Seeding imports the entire HSK 3.0 vocabulary list and applies the baseline calibrations.

To calibrate a baseline literacy for the user at the absolute start of usage, the user simply selects an HSK level appropriate for their level. All vocab words belonging to levels under this will be tagged as Familiar, while all those *at* this level will be tagged Learning. Those above will remain Not Encountered. No separate function-word allowlist is needed on top of this: nearly every common grammatical particle (的, 了, 是, 不, 吗, 呢, 吧, etc.) is already an individual entry in the HSK 3.0 list, so baseline calibration alone tags them Familiar/Learning from session one, provided the user actually holds real vocabulary at that level going in (see the momentum assumption in Section XIX). The one confirmed exception, 呗, is simply excluded from the AVD and will never be generated or tested — not worth a special case for one word.


## VIII. FPG Specifications
When an FPG is called by the user, a set of **frontier words** is chosen from the ILS. These are the words the passage is built around. The user-defined passage length sets a range of frontier words per tier, listed below. The *maximum* of the range, $N$, is how many frontier words are selected and sent to the model. The *minimum* is the floor the validated passage must reach.
1. **30-50 chars:** 2-3 short sentences - 4-5 chars/words
2. **50-100 chars:** succinct paragraph - 8-10 chars/words
3. **100-150 char:** intermediate, longer paragraph - 12-15 chars/words
4. **150-250 chars:** advanced, multi-paragraph text - 15-20 chars/words

Selection happens in two steps, new words first:
1. **New words:** $M$ new words are allotted, where $M$ is the Learning deficit capped per tier (see below). $M$ may be 0.
2. **Recency fill:** the remaining $N - M$ slots are filled from the top of the descending recency list (Section VII).

The frontier set is therefore the new words plus the top $N - M$ encountered words by recency. Frontier words come from these two groups only.

New vocabulary is introduced when the number of Learning words in the ILS falls beneath a fixed, absolute cap $C_L$. Only Learning words count toward this: Familiar words have already been seen for a while and are not truly "new" anymore. Since a severe error demotes a Familiar word back to Learning, the Learning count naturally swells when the user struggles, pausing new introductions until the backlog is consolidated. The cap is absolute rather than a percentage of encountered words, because the real constraint is how often the recency scheduler can cycle back to each Learning word, which is roughly $C_L / k$ passages for $k$ Learning slots per passage. That depends on passage size and usage frequency, not on how large the encountered vocabulary has grown. A percentage would let the Learning pool grow with the AVD and stretch those short-term intervals. The default is $C_L = 25$, derived as follows: at ~2 passages/day, a Learning word should reappear no sooner than every 3 passages and no later than every 6–7, with ~5 as the target. Assuming roughly half of a passage's target words are Learning, the 50–100 tier gives $k \approx 4.5$ (gap $\approx 5.5$) and the 100–150 tier gives $k \approx 6.5$ (gap $\approx 4$), both inside that window. (*Note: the "half are Learning" assumption is the weakest input and should be checked against the `Appearances` log once FPG is live. Because baseline calibration tags an entire HSK level as Learning (~950–1,100 words), the Learning count starts far above any reasonable $C_L$, so no new words are introduced until that backlog drains. This is accepted as an extended placement phase, and the exact value of $C_L$ can be tuned from real usage before it ever binds.*)

The number of new words introduced equals the deficit $C_L - (\text{\# Learning words})$, capped per passage length as follows:
1. **30-50 char:** 1 new char/word
2. **50-100 chars:** 2 new chars/words
3. **100-150 chars:** 3 new chars/words
4. **150-250 chars:** 4 chars/words

For example, with $C_L = 25$, if a certain user's ILS has 21 Learning words, they are experiencing a deficit of 4 new words. If they choose the most advanced length of 150-250 words, all 4 new words will be chosen, and the remaining $20 - 4 = 16$ frontier slots will be filled from the top of the recency list. In contrast, if they choose the shortest length, only 1 new word will be chosen, respecting the cap, and the remaining $5 - 1 = 4$ slots are filled by recency. As appropriate, newly introduced words are simply picked randomly from the lowest HSK level that still has Not Encountered words. (*Note: this separate proficiency level is mostly unrelated to Moxie. It is simply a tracking tool to assist in assigning new words.*)

### VIII.A Identity Model
Frontier selection, validation and the answer key all work on **vocab IDs**, never on bare Mandarin strings. A vocab ID identifies exactly one (chars, pinyin, sense) triple, where *sense* is the entry's part of speech from `hsk30.txt` (possibly blank). After the seed-time dedupe (Section XII) the mapping ID ↔ triple is a bijection. One *string*, however, can map to several IDs, for two reasons:
- **Pinyin ambiguity:** different readings, e.g. 长 `chang2` Adj / 长 `zhang3` V. A wrong pick changes the answer-key pinyin and therefore grading.
- **Sense ambiguity:** same reading, different part of speech, e.g. 会 `hui4` V / 会 `hui4` N. A wrong pick does *not* change grading, since the pinyin is identical. It only changes which `user_vocab` row CSM updates.

### VIII.B Data Structures
Structures are either **static** (identical for every user, derived from the global `hsk_vocab` table) or **per-FPG** (derived from `user_vocab` for one generation request). This mirrors the global/per-user split in the schema (Section VII).

| # | Structure | Shape | Scope | Built | Used in |
|---|---|---|---|---|---|
| S1 | Unit index | `str → tuple[(vocab_id, pinyin, sense), ...]` | static | once per server process, by a cached builder in `generation.py`, from `hsk_vocab`; passed down as an argument | steps 4, 5 |
| P1 | Frontier IDs | `set[vocab_id]`, size $N$ | per-FPG | after recency scoring | steps 3, 6 |
| P2 | Non-frontier IDs | `set[vocab_id]` | per-FPG | after recency scoring | steps 3, 6 |
| P3 | New-word pinyin | `dict[vocab_id → pinyin]`, size $M$ | per-FPG | at new-word selection | hints |
| P4 | Prompt rows | `vocab_id → (chars, pinyin, sense)` for every ID in P1 ∪ P2 | per-FPG | returned by the recency-scoring query (`user_vocab` joined to `hsk_vocab`) | step 3 |

**S1 — unit index.** Keyed by every distinct `simp_man_word` in `hsk_vocab`. Keys are whole segmented units, e.g. 长大 is its own key, not looked up character by character. Each value holds *every* HSK candidate for that string, with pinyin and sense embedded, so a single lookup supplies everything steps 4–5 need without a second query. `len(value) > 1` means the unit is ambiguous. S1 is built from the **DB**, not from `HSK_VOCAB` (the in-memory parse of `hsk30.txt`), because vocab IDs exist only in the DB and the dedupe happened only in the DB. S1 supersedes `data/polychars.txt`: a reading with no HSK entry has no vocab ID and could never be serialized anyway.

*Lifecycle.* S1 is **not** built at module import. `moxie.db` is gitignored, so an import-time query would break test collection on any fresh clone or CI run. Instead:
- `generation.py` owns a builder that reads `hsk_vocab` through a session it is *given*. That way integration tests can point it at the isolated test DB.
- A cached wrapper supplies the production session, so the query runs once per server process.
- The orchestrator passes S1 down. The segmenter and the resolution module take it as an argument and never import the builder, so their unit tests pass a hand-built toy S1.
- Because vocab IDs are reassigned on re-seed and the cache lives in server memory, **re-seeding must be followed by a server restart.** A running server would otherwise keep serving stale IDs, and may still hold the deleted `.db` file open.

**P1 / P2 — eligible ID sets.** The *eligible set* $E = P1 \cup P2$ is every encountered ID plus the $M$ new IDs. Invariants:
- $P1 \cap P2 = \emptyset$. The two prompt lists partition $E$.
- $|P1| = N$ (tier maximum). P1 contains all of P3's keys.
- P2 = encountered IDs − P1.

**P3 — new-word pinyin.** Keys are a subset of P1. Kept separately because new-word hints (below) need to know which resolved IDs are new, and that can't be recovered from P1 alone.

**Eligible strings are not stored.** Whether a string has any eligible reading is computed on the fly: look up the unit in S1 and test whether any candidate ID is in $E$. This avoids a third per-FPG structure that would have to stay consistent with P1/P2.

### VIII.C Pipeline
**Step 1: frontier selection.** $M$ new IDs are drawn (Section VIII above), filling P3. The top $N - M$ encountered IDs by descending $R$ fill the rest of P1. All remaining encountered IDs form P2.

**Step 2: prompt rows.** P4 supplies (chars, pinyin, sense) for every ID in $E$, rendered as two lists: non-frontier (P2) and frontier (P1). Blank senses are omitted from the rendering.

**Step 3: generation.** Both lists go to the model with **pinyin and sense**, so each listed item names exactly one vocab ID. Pinyin tells the model *which reading* is allowed (a frontier 长 `zhang3` is otherwise indistinguishable from 长 `chang2`). Sense keeps the partition intact: if 会 `hui4` V is frontier and 会 `hui4` N is not, dropping sense would list 会 `hui4` in *both* lists. Sending all fields for every entry was chosen over a rule for which entries need them: one uniform rule is simpler, and token cost is negligible (Section XV). The model is then prompted with a message similar to the following:

`Given ONLY the vocabulary listed here, generate a [insert length range] [Simplified/Traditional] Mandarin character text as a pinyin decoding exercise for an English-speaking Mandarin student. Each word is listed with its pinyin reading and, where given, its part of speech; use each word ONLY in that reading and sense. The second list contains "frontier" words that MUST be MOSTLY included in the passage (at LEAST [insert minimum value]), while the first list contains words the user already knows - these can be used WHENEVER appropriate. Do NOT under ANY CIRCUMSTANCES use any vocabulary, reading or sense that is not in one of these two lists, at ANY POINT in the passage. This passage should be formatted with NO SPACES.`

**Step 4: segmentation + string-level validation.** The output is quickly scanned for length. The segmenter is a **pure** module: it never touches the DB, and it receives everything it needs as arguments (the passage, S1, and the eligible set $E$). Punctuation and whitespace are **not** stripped: each such character becomes its own unit in the segmentation and is skipped by the string-level checks below. Latin letters and digits are never valid in a passage, so they are flagged as hallucinated like any non-HSK character. The self-written Bidirectional Maximum Matching (BiMM) segmenter then runs Forward (FMM) and Backward (BMM) maximum matching against the *whole* HSK 3.0 word list. For each unit $u$ of a segmentation:
- (a) **Hallucinated:** $u \notin$ S1.
- (b) **Not encountered (word level):** $u \in$ S1, but no candidate ID of $u$ is in $E$. The user has never seen this string in *any* reading.

**FMM vs. BMM is decided here, inside the segmenter**, so exactly one segmentation leaves step 4. When FMM and BMM differ, they are compared in order:
1. validity: if exactly one segmentation passes (a) and (b), it wins. If both fail, the passage is rejected and the error reported is chosen by **type first, then count**: a not-encountered (b) segmentation outranks a hallucinated (a) one; if both fail with the same type, the one with fewer offending units is reported (ties → BMM);
2. fewer units;
3. fewer single-character units;
4. BMM.

Criteria 2–4 are the standard BiMM heuristic and apply only when both segmentations pass. Criterion 1 ranks by error type before count because hallucination is segmentation-dependent: FMM and BMM match against the same word list, so a character is flagged as hallucinated only when *that* segmentation failed to cover it with an HSK unit. If the other segmentation covers every character (and fails only on (b)), the passage contains no truly hallucinated character, so the not-encountered report is the more accurate one. None of the criteria needs ID resolution or a model call.

These checks are **reject-only**. Passing (b) means only that *some* reading of $u$ is eligible, not that the one used is. No frontier check happens here: frontier membership is per ID, so it can't be counted until step 5. **If any unit fails (a) or (b), the attempt stops here**: steps 5–6 are skipped, so no resolution call is spent on a passage that is already rejected, and the passage is reprompted immediately.

**Step 5: ID resolution.** Each unit is mapped to exactly one vocab ID, using its S1 candidates $C(u)$:
1. $|C(u)| = 1$: resolved directly.
2. All of $C(u)$ share one pinyin (sense-only ambiguity) and exactly one candidate is in $E$: pick it **without** a model call. Safe because a wrong sense cannot change the answer-key pinyin.
3. Otherwise (candidates differ in pinyin, or several same-pinyin candidates are eligible): queue $u$ for the resolution call. The options are **all of $C(u)$**, not just the eligible ones. Restricting options to eligible candidates would silently force an ineligible usage (很长 `chang2` when only 长 `zhang3` is eligible) into the eligible reading. The result would be a wrong answer key, a correct user answer graded severe, and a spurious demotion.

All queued units go in **one** call. Each unit's candidates are numbered $1..k$ with pinyin and sense shown, and the model replies with **option numbers only**. The number is mapped back to a vocab ID locally. Raw IDs are never requested from the model: a mistyped ID is probably another word's valid ID and would pass silently, while an out-of-range number or non-number is caught immediately.

**Resolution is blind.** It asks what the passage *says*, not what the user *should* have seen, so it must not be biased toward eligible readings:
- It is a **separate, fresh request**, not a turn in the generation conversation. The generation prompt, and with it the eligible lists, is never in its context.
- It receives **no eligibility or frontier information**. Its only inputs are the final passage and the numbered candidates.
- Options are listed in a **user-independent order** (ascending `vocab_id`). Eligible readings never come first, since models tend to favor earlier options.
- Options carry **no labels** such as "known", "frontier" or "target". Each is shown as just pinyin + sense.

Each retry produces a new passage, so each attempt gets its own fresh resolution call (*not yet implemented*):

`The following words/chars have multiple possible readings in this passage. For each, reply ONLY with the number of the option that matches its usage in context. [word/char #1] (position [i]): (1) [pinyin] [sense] (2) [pinyin] [sense] ... [word/char #2] ...`

**Step 6: ID-level validation + serialization.** Done in one pass over the resolved ID sequence, using set membership against P1 and $E$ (O(1) each):
- (c) **Not encountered (reading/sense level):** resolved ID $\notin E$. The string is known, but this particular (pinyin, sense) entry has never been seen. This is a **separate error type** from (b), and it is reported with the reading used. This is what catches the 很长 case.
- (d) **Frontier count:** the number of *distinct* resolved IDs in P1 must be at least the tier minimum. It cannot exceed the maximum, since $|P1| = N$. New words count like any other frontier ID and are not separately required. A new word the model leaves out was never shown to the user, so it stays Not Encountered.

Both checks come out of the same pass at no extra cost, so failures are **collected, not short-circuited**. If (c) and (d) both fail, they are reported together. If both pass, the ordered ID sequence is serialized as the answer key (Section IX), and its pinyin is read off each ID's candidate entry.

(*Known risk:* segmentation may not match what the model intended. For example, a single-character frontier word 学 written inside 学生 segments as 学生, so it does not count toward the frontier minimum. How often this happens is unknown until segmentation is tested against real generated passages.)

**Retry loop.** Steps 4–6 form a stateless validator: it takes a passage and returns valid or a list of errors, and never needs to know about earlier attempts. Validation failures are returned as data, not raised one at a time, so the orchestrator can build a single reprompt from all collected errors. A failing passage is sent back to the model with an *edit* prompt. Whatever comes back is a brand-new passage that reruns steps 4–6 from scratch, including a fresh resolution call. P1–P4 and S1 do not change between attempts.

**Conversation state.** The Messages API is stateless: each request carries the full conversation as a list of alternating `user` / `assistant` turns. The **orchestrator** (`generation.py`) owns this list as a local variable scoped to one FPG request:
- it starts with the generation prompt;
- each reply is appended as an `assistant` turn and each edit prompt as a `user` turn, and the whole list is resent;
- this is what lets an edit prompt ("KEEP the existing ones") refer to the previous passage;
- the list is discarded when the request returns, since nothing about the exchange needs to persist once a passage validates.

Resolution calls (step 5) are never added to this list. Besides the message list, the only state carried between attempts is the retry count.

If (1) the frontier minimum is not reached (check d), the following prompt is given:

`The number of frontier words is not enough. Edit the passage to include [integer difference] more, while also KEEPING the existing ones. The same rules from above apply for generation.`

If (2) any unit fails checks a–c, the following prompt is given. For (a)/(b) this is sent immediately, since the attempt stopped at step 4. For (c) it is combined with (1) when both fail:

`Vocab unit(s) [list of offending units, with the reading used where relevant] are not in the allowed vocabulary. Diagnose and edit the passage to fix these mistakes. The same rules apply for generation as before.`

Combining only happens at the ID level: (c) and (d) come out of the same pass, so reporting both at once costs nothing and can save a retry from the two-retry budget. String-level failures (a, b) are never combined with (d), because checking (d) would require a resolution call on a passage that is already rejected. If this error loop continues two times with Sonnet failing to remedy the failing passage, FPG is stopped entirely and an error message is communicated back to the user. (*Open:* whether resolution calls count toward the two-retry budget.)

**New-word pinyin hints.** After step 6, the hint map is the subset of P3 whose IDs appear in the resolved sequence. Since an ID fixes its reading, the hint pinyin is exactly the reading the user will be graded against. A new word has never been seen by the user, so they just copy the hint while decoding. Hints are sent along with the rendered passage (Section XIII). New words are still graded like any other unit, but their CSM outcome is fixed at Learning +0 (Section XI).

(*Deferred:* sense-aware validation, i.e. detecting that a resolved sense doesn't fit its usage, is tabled until segmentation itself becomes sense-aware. *Also deferred:* BiMM matches against `HSK_VOCAB` (file) while S1 comes from the DB. Their word sets are currently identical, because the dedupe removed entries but no word strings, so a single source is logged as a `ROADMAP.md` TODO.)

IMPORTANT: When the user interacts with the prompt, all punctuation and spaces on nonbearing on the real-time tracking mechanism. When the answer is submitted, all except the characters and pinyin are trimmed such that the text is in the same format as the answer key. The user's text is then parsed character-by-character alongside the answer key and the grading is done. Ultimate CSM promotions and demotions are applied on each *unit* that contains a character with flagged errors.

Immediately following the attempted submission of the user, the length of the pinyin text is immediately evaluated using the real-time tracking mechanism to ensure that an answer for all characters present have been accounted for. If the user has failed to reach the number of characters defined or has typed more than there are in the passage, a brief error will flash and the passage will not be submitted. It may be possible to conduct this screen of analysis entirely in the frontend, before the POST request is even sent through.

(*Note: in the future, it will be prudent to include a UI feature that ensures the "Submit" button is not even activated until the user has finished decoding the entire passage. Likewise, a stopper that inhibits displaying any of the user's text on the screen after all characters have been accounted for, as well as a fun Mac "rejection sound effect", can be considered.*)

*Note: no numbers or English words for proper nouns/names are accommodated at this phase, as the first confuses the pinyin tracker while the second complicates the real-time tracking mechanism.*


## IX. Answer Key Pipeline
As previously stated, during the segmentation & passage validation step of a passage, the passage will be parsed to produce a pinyin text utilizing AVD look-ups. The answer key is stored as the ordered sequence of resolved vocab IDs (step 6 of Section VIII), serialized as a string, with punctuation cut. Each ID fixes the unit's characters, pinyin and sense, so the pinyin key is derived from it.


## X. Grading Specifications
Promotions are obviously recorded when full correctness is observed. Demotions are split into two different kinds of errors, one light, the other severe. Slight errors are characterized by (1) genuine keyboard 
1. **Slight Errors:** small mistakes in four categories - (1) genuine keyboard mistypes, (2) nasal swap ('n' vs. 'ng' ending), (3) the umlaut omission (u vs. ü, the latter registered as a v), and (4) retroflex blur ('zh' vs. 'z', 'ch' vs. 'c', etc.)
2. **Severe Errors:** tone mistakes or anything else not falling into the 4 error categories categorized under slight mistakes
    - **Skips:** also categorized as severe errors and receiving identical CSM treatment. However, is differentiated as its own category in the appearance database, in the case that future phases may apply different analysis in FPG recency calculations.
Under this framework, errors are evaluated under the 4 categories. If none flag, they are categorized as severe as an "else catch-all".

To check for slight errors, we use a custom Levenshtein distance algorithm to calculate typo confidence while taking into account the 3 non-typo errors:
1. **Retroflex, Umlaut & Nasal Error String Generation:**
    First, the tone is stripped from the *correct* pinyin representation of the character (before analysis even begins, a separate process checks for tonal correctless; if an error on that front is found, the error is already categorized as severe. The rest of the analysis is NOT conducted. In future phases however, further analysis is prudent to provide complete user feedback). 
    
    For each of the 3 slight errors, the correct pinyin is evaluated to see if they are genuinely possible errors (i.e. retroflux error is only possible when the first character is a consonant in set {'c', 's', 'z'}. Umlaut omission is only valid if following 'n' and 'l' consonants). The maximum number of possible error combinations is 8 (2^3). However, for the PoC we treat these cases as rare and hence only consider the four base possible strings containing these errors by themselves. 

2. **Candidate Matching & Levenshtein Distance Analysis:**
    The user's input is first checked for an *exact* match against each string generated in (1): the correct pinyin and the (up to 3) applicable slight-error variants. The three variant categories are categorical, not fuzzy - a hit requires equality, not closeness - so an exact match on a variant flags that error directly, with no distance computation involved.

    If no exact match is found, and the pinyin is 4+ characters long (not including the tone digit), typo is tested - and only tested - against the original, correct pinyin. This is the one place real Levenshtein distance is computed: a small, nonzero distance under the typo threshold flags a typo; otherwise the error is severe. None of the slight errors apply once equality has already failed for all of them.

    **NOTE:** for pinyin under 4 characters, typo is not considered at all - the exact-match step above is the entire test, and real distance computation is skipped entirely.

Following a full parsing of the entire text character-by-character, the CSM system can then assign the appropriate promotions and demotions, detailed in the next section.


## XI. The CSM System
The tiered system and promotion schema for correct recognition are awarded as follows:
1. **Not Encountered:** default status for all vocabulary that has not shown in a passage yet
    - as soon as user encounters and interacts with a passage containing it, the unit shifts to Learning base. The flip happens at grading, and only for new words that actually appeared in the graded passage; a new word chosen for a passage but left out by the model stays Not Encountered
2. **Learning:** preliminary stage to train user's recognition at short-term intervals
    - to promote to Familiar, users must get the pinyin and tone right **three** times in a row
3. **Familiar:** secondary stage of recognition, at slightly longer intervals
    - to promote to Solid, users must get the pinyin and tone right **three** (more) times in a row
4. **Solid:** train user only in long intervals to prevent recognition erosion
    - to promote to Mastered, users must get the pinyin and tone right **five** (more) times in a row
5. **Mastered:** user revisits only once in a while
    - the user needs to maintain perfect recognition to maintain Mastered status

Errors are tagged to individual characters, but at promotion/demotion are applied to the entire vocabulary unit (if not solo character). 

Regardless of the error type, a first encounter of a new word is promoted to Learning base. The grading pipeline will report any errors if the user made them, as prescribed for all words. However, this doesn't impact the default AVD promotion.

For slight errors, the following specific rules apply:
- If current status is Familiar or Learning, the streaks are lost and the user maintains status but loses their streak.
- If current status is Solid or Mastered, they are automatically demoted to Familiar +2 base points.

For severe errors, the following specific rules apply:
- If current status is Learning, the user maintains status but loses their streak.
- If current status is Familiar, the user is demoted to Learning +2 base point.
- If current status is Solid, the user is demoted to Familiar +1 base points.
- If current status is Mastered, the user is demoted to Familiar +2 base points.
*Note: an "oopsie" button clickable for specifically (1) typos and (2) tone mistakes (treated as typos) will be developed in the future so the user can litigate slight errors falling under these categories.*

The underlying idea of the demotion framework is that due to the FPG schematics & recency score framework, current status is a good indication of the user's (1) amount of interaction w/ the word, and (2) length of time of that interaction. Therefore, the higher up they are, the floor they fall to is less severe because of the expectation that recognition recovery is easier. *Note: Only exception is if user is away for an extended period of time. In that edge case, a "recovery" test can be developed similar to an initial baseline diagnostic, in which words the user has encountered are prompted again. Feature TBD.*


## XII. Seeding AVD
The Adaptive Vocabulary Database (AVD) is sourced from the 11,000 word long HSK 3.0 vocabulary list. In contrast with adding words appropriately as the user encounters them, the entire list is instead seeded into the library from the start. Each row is one (word, pinyin, sense) entry, where sense is the entry's part of speech in `hsk30.txt` (blank when the file gives none). Entries that share a word and pinyin and differ only in sense are collapsed at seed time: within such a group, a blank-sense entry is dropped if a non-blank one exists, and among entries with the *same* sense only the lowest HSK level is kept. This removes 4 of 11,091 entries (一下儿, 一会儿, 出口, 称) and leaves (word, pinyin, sense) unique. An initial baseline calibration is performed with the user's self-reported HSK level. All more advanced words are labeled "Not Encountered" until passage generation has included them, via the algorithm described above in Section VIII.


## XIII. API Surface
The application needs four primary API endpoints that facilitate the user's interaction with the backend:
1. **FPG Loop:** `POST /api/fpg` (body: passage_length)
    - upon user prompting, runs frontier vocab selection, calls + validates Claude, builds answer key
    - returns {passage_id, rendered_text, char_count, new_word_hints}
        - `new_word_hints` maps each new word that appears in the passage to its resolved pinyin (Section VIII); it is empty when no new words appear
    - answer key stays server-side, waiting for grading (new-word hints are the one scoped exception)
2. **Grading & Feedback Loop:** `POST /api/grade` (body: passage_id & user_pinyin)
    - prior to the start of the grading mechanism, a quick scan for length correctness is applied; a failure there 
    - upon user submission, runs alignment and grading, applies CSM updates to AVD
    - returns per-character verdicts + promotion/demotions summary
    - answer key is also returned for the user's comparision benefit
    - passages grade once, so this endpoint only works once per passage
3. **Health Sanity Check:** `GET /api/health`
    - trivially checks for API health
    - returns {"ok": true}

Eventually, an open, user-facing AVD will require:
4. **Open AVD:** `GET /api/vocab`

## XIV. Architecture & Stack
Need Claude help to make the following informed decisions
**Frontend:** entirely written with vanilla HTML, CSS, and Javascript implementation, for the purposes outlined in Sections I and III.
**API:** FastAPI
**Data:** SQLAlchemy as standard pairing with FastAPI. 
**Backend Logic:** Python

The repo layout is structured as follows:
1. **`backend/`:** contains (1) Claude-FPG pipeline and (2) the grading & CSM pipeline
    - `main.py` - top-most layer of control
    - `models.py` - bridges gap between Python classes and relational databases 
    - `llm.py` - **transport + prompt templates only.** Builds each prompt (generation, edit/reprompt, resolution) from plain data passed in, sends a message list, and returns plain data: passage text, or the reply parsed into option numbers. It knows nothing about the pipeline's error types or validation rules. Checking parsed option numbers against the candidates belongs to the resolution module, since only it knows how many options there were.
    - `generation.py` - **orchestrating layer for FPG only**, mirroring `grading.py`. Calls the modules below in order, owns the retry loop and the per-request message list (Section VIII.C), decides *what* to reprompt from collected errors, and assembles the response to the frontend. It is the only FPG layer, together with the selection module's query, that talks to the DB.
    - selection module *(working name TBD)* - recency scoring ($T$, $I$, $H$ → $R$), new-word selection, and construction of the per-FPG structures P1–P4 (Section VIII.B)
    - resolution / validation module *(working name TBD)* - step 5 ID resolution (direct, same-pinyin shortcut, queue for the blind model call), step 6 ID-level checks (c, d), and answer-key serialization
    - `segmenter.py` - **pure BiMM module** (step 4): FMM, BMM, the string-level checks (a, b), and the FMM/BMM choice. Takes the passage, S1 and $E$ as arguments; no DB access. Pinyin generation (`gen_pinyin`) is retired, since pinyin now comes from resolved IDs.
    - `grading.py` - broad orchestrator for entire grading pipeline
    - `levenshtein.py` - conducts Levenshtein distance grading
    - `csm.py` - updates AVD using grading info

   Rule of thumb: only orchestrators (and the selection query) touch the DB. Every module below them takes plain data in and returns plain data out, so each can be tested with hand-built toy inputs.
2. **`frontend/`:** contains all UI
    - `index.html` - homepage and starting point for a new session
    - `decode.html` - session page
    - `results.html` - results following grading & CSM analysis
3. **`docs/:`** relevant documentation to the project
    - CRD
    - PRD iterations
4. **`data/:`** all HSK data and relevant scripts for management
    - ~~polyphone table~~ (`polychars.txt`) - superseded by the static unit index S1 (Section VIII.B); to be removed
    - Full 11K HSK 3.0 vocabulary list 
    - `seed.py` - initial (hardcoded, for now) seeding of the database with appropriate baseline calibrations
    - `db.py` - establishes connection to the database
At the root is also: `.venv`, `.env`, `requirements.txt`, `README.md`, `CLAUDE.md` and `.gitignore`.

Environment handling... .venv probably? requirements.txt needed maybe.


## XV. LLM Integration
The cost for tokens is quite negligible. Therefore, we optimize constraint adherence to vocabulary limitations. We start with Sonnet and measure violation rates over 20+ trials. We expect Sonnet is suitable and an upgrade to an Opus model is not necessary. 


## XVI. Build Plan & Milestones
**Milestone #0:** no Claude, just to test AVD state update logic
- toy AVD seeded with <100 words
- toy hardcoded passage w/ respective pinyin answer key
- Build `POST /api/grading` and grading + CSM pipeline 
- Submit a test pinyin string 
**Milestone #1:** sub-in Claude FPG pipeline
- AVD is seeded with CSM mechanics wired in (general toy AVD with random level of literacy)
- FPG w/ Claude looped in and callable from basic frontend UI setup
- User can submit and AVD changes applied (no need for keyboard tracking yet)

**Milestone #2:** adding UI features
- keyboard tracking UI
- results page UI


## XVII. Work Split & Open Design Questions
As detailed above, while I am determined to *limit* the usage of Claude Code as much as possible on this project, and certainly none of the UI design, backend Python logic, API calls, socket events, etc. will be touchable by Claude, certain elements of the project **deemed both tedious and unproductive or otherwise un-beneficial to growth** can be handed of to Claude. This includes config, styling, scaffolding, etc. 

Other than the questions a reader of this document might have about the functionality for this particular phase I can't really think of anything that is open for future phases? Other than:
- multidimensional literacy model paradigm
- UI for possible dashboard/open AVD
- Possible progress data the user would want to see in a dashboard type deal


## XVIII. Deferred Functionality Backlog
**Comprehension Tier:** important, but not as crucial as decoding.
- **Translation Module:** hence, this is also delayed for similar reasons.
- **Tap-to-define:** this too.
- **Text-to-Speech/Speech-to-Text:** yup, this too.

**Chengyu & Classical Lexicon:** idea is to include dimension of literacy for classical texts and idioms - too complicated for initial phase. Complicates simple AVD sourced from HSK 3.0, which although may contain some idioms and classical lexicon, may not be as complete.
**Existing-text Library:** copyright concerns mostly. Also, the Claude-wrapper idea is a big implementation plus and important to the SWE goal.
**Mult-user Auth:** immediate usage priority is for me personally.


## XIX. Decision Log
Each entry records what was decided, why, and what evidence would justify reopening it. The revisit conditions are the load-bearing part: a decision without a stated falsifier is a preference, not a decision. Dates are enumerated by the date of this document version (August 18th).

1. **Product Scope & Framing:**
    - ***Phase 1 is a decoding trainer, not a comprehension trainer.*** Decoding (character → sound) is separable, cleanly gradeable, and plausibly my actual bottleneck: heritage background means strong listening and speaking against weak reading. Comprehension requires fuzzy grading and would have made the first loop unbuildable.
        - **Revisit if:** decoding accuracy plateaus high while reading comprehension stays weak, indicating the wrong bottleneck was targeted.
    - ***Pinyin transcription accuracy is the primitive.*** Chosen over cloze, MCQ, and flag-only reading. Continuous transcription produces retrieval on every character rather than a sampled handful, re-verifies the known set every session (guarding against the silent-rot problem where "known" words are never re-tested), and has a flow quality that survives daily use. Alternatives were rejected: flag-only has no promotion signal — words rise only by not being flagged, which is absence of evidence; cloze has clean per-word signal but stop-start pacing and a high-entropy-blank problem; MCQ constrains the answer space but reads as test-taking. 
        - **Revisit if:** transcription proves tedious in sustained use, or the decoding-only signal turns out to promote words I can sound out but can't read.
    - ***Reading is the substrate; challenge types attach to it.*** Reframes reading and translation from coordinate modes into one constant (frontier-calibrated passage) plus a swappable challenge. Blends well into additional functionality - translation, text-to-speech, speech-to-text, etc.
    - ***No explicit gamification layer.*** Points, streaks, and badges would read as cheap and get ignored. The engagement mechanism is the frontier itself — text calibrated a notch above current level. Calibration is the game. 
        - **Revisit if:** usage retention fails and post-mortem points at missing extrinsic motivation rather than miscalibration
    - ***Single user from day 1, but multi-user schema also supported.*** Only I will use this for the foreseeable future, so auth is out of scope. But separating global vocabulary from per-user status via a junction table costs nothing now and makes "add users" an auth problem later rather than a schema rewrite.
        - **Revisit if:** junction indirection measurably complicates phase-1 queries.
    - ***All text is model-generated. No Scraped or licensed library.*** Copyright exposure, scraping fragility. Generation pipeline is important to the SWE learning target.
        - **Revisit if:** generation quality proves inadequate at higher levels where authentic register, usage of advanced, specific diction, exposure to particular topics/mediums of writing, authors, etc., is important.
    - ***Simplified Characters Only.*** Matches my personal usage and coursework. Traditional support would double dictionary and answer-key pipeline.
        - **Revisit if:** classical or Taiwanese material becomes a priority.
    - ***No topic, style or difficulty parameters in phase 1.*** The loop needs only AVD state and passage length. Everything else is elaboration. Caveat worth preserving: topic control is a retention feature even though the loop doesn't require it. A passage about something I'd read anyway is the difference between daily use and abandonment. This is first in line for phase 2, not a nice-to-have. 
        - **Revisit if:** retention falters and generic subject matter is the identified cause — in which case pull it forward immediately.

2. **Interaction design:**
    - ***The cursor is driven by user intent, never by the answer key.*** Counting letters against key length leaks the answer, jumps on mistype. Terminator instead: user says "done," UI obeys, right or wrong.
        - **Revisit if:** never, without a stated reason.
    - ***Terminator is a space or a tone digit (1–5), runs collapsed.*** Covers both word-chunked (`xi3huan1`) and character-spaced (`xi huan`) input; tone becomes an orthogonal grading dial, not structural.
        - **Revisit if:** accepting both proves ambiguous in an unforeseen case.
    - ***Tone marks mandatory in phase 1.*** Punishing for most learners, near-free for a heritage speaker — the strong half. Enables word-chunking, richer signal; avoids a later migration. Neutral is `0`.
        - **Revisit if:** tone entry dominates error volume, obscuring the decoding signal.
    - ***No real-time correctness feedback.*** Live marking turns retrieval into copying. Cursor shows position only; reveal at submit.
        - **Revisit if:** never for the primary mode; a separate practice mode could relax this.
    - ***Passage rendered without spaces.*** Chinese has no word boundaries; pre-segmenting removes boundary-parsing, itself part of the skill.
        - **Revisit if:** unsegmented text overwhelms at low proficiency — make it a difficulty setting.
    - ***Dash marks an unknown character.*** Honest skip beats a guess as signal; single-user, so no incentive to game it.
        - **Revisit if:** multi-user arrives and self-report reliability matters.

3. **Grading and state:**
    - ***Promotion is on decoding only; meaning is untested.*** Correct pinyin ≠ comprehension — deliberate, named gap. A later module owns meaning, likely as a second status dimension, not a rewrite.
        - **Revisit if:** the comprehension module arrives — "Mastered" needs redefinition, not extension.
    - ***Errors split into slight and severe, with three phonologically-motivated slight categories.*** Retroflex blur (zh/z, ch/c, sh/s), nasal confusion (n/ng), umlaut omission (ü as u): systematic slips, not gaps. Keyboard mistypes are the fourth; rest is severe.
        - **Revisit if:** logs show a fifth category, or one of these is actually a knowledge gap.
    - ***Tone errors are severe.*** Reverses an earlier assumption that misses were minor: tone is a strength, so an error is real signal.
        - **Revisit if:** tone errors cluster on specific characters, looking like slips rather than gaps.
    - ***Keyboard-weighted Levenshtein scoped to the original string only; non-typo variants matched by equality, not distance.*** Edit distance is string-to-string; matching a regex directly is harder. Three independent flags originally suggested up to eight candidate combinations; PoC caps this at four (original plus one single-error string each) and drops combinations as too rare to justify the false-positive risk on pinyin this short. Of those four, the three error variants are exact-match only - they're categorical, not fuzzy - and real Levenshtein distance runs only against the original, scoped to typo detection, and only for pinyin 4+ characters (not counting tone).
        - **Revisit if:** logged data shows combinations or typo-stacked-on-a-slight-error are common enough to be worth the added ambiguity, or the length floor proves miscalibrated in practice.
    - ***Streak-based tier promotion at 3 / 3 / 5.*** Consecutive correct decodes for Learning → Familiar → Solid → Mastered. Initial instinct, to be tuned from use.
        - **Revisit if:** a week of sessions shows the pacing is wrong. Expected to change.
    - ***Compound-to-character mirroring is asymmetric.*** Demotions propagate to the failing character; promotions don't. Recognizing in one context isn't evidence elsewhere; failing is.
        - **Revisit if:** character-level status drifts implausibly far from compound-level.
    - ***Demotion floors soften as tier increases.*** Mastered falls to Familiar, not Learning — higher tiers mean more exposure, faster recovery.
        - **Revisit if:** high-tier words repeatedly re-fail after demotion.
    - ***Encounter density is derived from an event log, not stored per word.*** Stored density means rewriting ~11,000 rows every session, since the denominator moves for unseen words; deriving is one aggregate query, absentees zero by absence.
        - **Revisit if:** the candidate pool grows large enough for per-generation aggregation to cost measurably.
    - ***Review events are logged from day one.*** Every unit records word, session, timestamp, time since prior review, status, outcome — needed for encounter density and future-scheduler training.
        - **Revisit if:** never. The log is cheap and irreplaceable.
    - ***New-word introduction is gated by an absolute cap on Learning words only.*** Replaces the earlier Learning + Familiar flat thresholds (8 / 15). Familiar words aren't new, and demotions refill Learning on their own, so Learning alone works as a struggle signal. A percentage-of-encountered cap was considered and rejected: it scales with AVD size, while the binding constraint (how often each Learning word gets recycled) scales with passage throughput. The calibration backlog (a full HSK level tagged Learning) is treated as real Learning words, not excluded from the count. $C_L = 25$: targets a ~5-passage reappearance gap (3 minimum, 6–7 maximum) at ~2 passages/day for the 50–100 and 100–150 length tiers. Initial instinct, to be tuned from use.

    - ***Scheduler is hand-designed now, fitted later.*** Half-life regression needs review history; none exists yet. Hand-design intervals, routed through named constants for later fitted values.
        - **Revisit if:** enough review history accumulates — target phase 3.

4. **Language pipeline:**
    - ***Own maximum-matching segmenter; jieba dropped.*** An HSK list is a dictionary, not a segmenter — can't resolve overlapping matches (中国人民 as 中国+人民 vs 中国人+民). Maximum matching over it is ~40–70 lines, mine, and owns the computational core.
        - **Revisit if:** segmenter error rate proves unworkable — jieba is the fallback.
    - ***Model emits raw passage plus per-character pinyin; a polyphone table bounds trust.*** Segmentation resolves most polyphony via unique compound readings; the residue — polyphones like 了, 得, 长 — a dictionary can't resolve. Dictionary pinyin applies except in a bounded table (~100 entries), where the model's reading wins.
        - **Revisit if:** the table grows unmaintainable, or model pinyin proves unreliable on polyphones.
    - ***No dedicated function-word allowlist; HSK coverage plus baseline calibration already handles it.*** 的, 了, 是, 不, 我 and nearly every other common grammatical particle are individual entries in the HSK 3.0 list already, confirmed directly against `hsk30.txt` — the sole gap being 呗, which is simply left out of the AVD entirely rather than special-cased. Combined with baseline calibration (bulk-assigning at-or-below-level words to Familiar/Learning at seed time), these words are marked encountered before FPG ever runs, under the standing assumption that phase-1 usage always starts with real vocabulary momentum (>150 encountered words) rather than a true cold start. A dedicated allowlist mechanism would only earn its keep for a genuinely new user with near-empty AVD history — deferred along with general new-user onboarding.
        - **Revisit if:** cold-start onboarding for a user without existing momentum gets built, or a future gap word (beyond 呗) turns out to be both missing from HSK and load-bearing for basic sentence formation.
    - ***Baseline calibration precedes first use.*** Seeding all words as Not Encountered takes hundreds of sessions to reach my level, and makes session one ungenerateable. Bulk-assign by HSK level: at/below → Familiar/Solid, level entered → Learning, rest → Not Encountered.
        - **Revisit if:** bulk assignment proves badly miscalibrated — passages feel trivial or unreadable early on.

5. **Architecture and stack:**
    - ***FastAPI, SQLAlchemy, SQLite, vanilla frontend.*** FastAPI over Flask: typed-Python habits, legible docs, model-serving convention. SQLite: churning schema, one deletable file. SQLAlchemy: standard ORM, decoupled from SQLite.
        - **Revisit if:** concurrency or multi-user arrives — the Postgres move stays mostly mechanical.
    - ***Vanilla HTML/CSS/JS for phase 1, deliberately.*** React first means learning abstractions before understanding the problem they solve. Phase-1 UI: three screens, a keystroke handler — raw teaches requests, JSON, the DOM. React arrives in phase 2, once vanilla gets painful (tap-to-define, reactive state).
        - **Revisit if:** the cursor implementation alone becomes unmanageable in vanilla.
    - ***No migration tooling in phase 1.*** Schema churns early. `seed.py` rebuilds from scratch; changes mean deleting the `.db` and re-seeding.
        - **Revisit if:** the first AVD or review-log state worth keeping — trigger for Alembic, once real use begins.
    - ***Answer keys never leave the server.*** API responses are readable in devtools. Passage goes out; pinyin key, segmentation, frontier set stay server-side until grading.
        - *Scoped exception:* pinyin for new words that appear in the passage is sent along with it (Section VIII), because the user has never seen those words and is meant to copy them. Their CSM outcome is fixed at Learning +0 whatever the user types, so revealing their pinyin cannot be gamed.
        - **Revisit if:** never.
    - ***A passage grades exactly once.*** Re-submission would double-apply CSM updates — a refresh could silently corrupt the AVD.
        - **Revisit if:** a legitimate re-grade case appears — likely a separate non-mutating practice path.
    - ***Submit sends the raw input string, not client-tokenized input.*** Frontend could tokenize for the cursor, but that'd duplicate the rule in two languages, where it drifts — keep one implementation, server-side.
        - **Revisit if:** payload size or latency ever matters — won't, at passage scale.

6. **Process and AI usage:**
    - ***Claude is confined to passage generation within the product.*** Everything else — segmentation, alignment, grading, scheduling, state transitions — is algorithmic and mine: the core worth building.
        - **Revisit if:** a component proves genuinely intractable — comprehension grading, expected first, later phase.
    - ***Model choice: Sonnet 5 default; Haiku tested as an optimization.*** Constrained-vocabulary generation is where weak models fail, costing retries against the <10% regeneration target. ~$0.04/generation, 2/week — under $1/month; optimize for adherence, not price.
        - **Revisit if:** measured Haiku violation rate over ~20 generations proves adequate, or Sonnet proves inadequate.
    - ***Milestone 0 contains no LLM.*** Hardcode a passage and key, seed a toy AVD, build submit/grading/CSM, verify by hand via generated docs. Isolates the hardest components from the flakiest dependency; front-loads the work that's mine.
        - **Revisit if:** never — this ordering is strictly better.
    - ***I write the code; Claude Code is bounded by written contract.*** Permitted: config, scaffolding, styling, boilerplate. Not: schema design, grading/CSM logic, segmenter, cursor, generation prompts. Contract lives in `CLAUDE.md` at repo root.
        - **Revisit if:** a block persists beyond a week — response is a scope cut, not a quiet expansion.
