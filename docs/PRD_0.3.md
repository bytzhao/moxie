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
    - The exponential quantity $1 - e^(\lambda\Deta t)$ relates this latent time interval to a pressure score normalized between 0 and 1
        - $\lambda$ is denoted by $\frac{1}{c_s}$ where $c_s$ is a status coefficient given by:
        1. Learning - `1` (`2^0`)
        2. Familiar - `2` (`2^1`)
        3. Solid - `4` (`2^2`)
        4. Mastered - `8` (`2^3`)
        - This value allows for the time pressure to be eased depending on the user's status: higher mastery of the word implies a greater length of exposure, higher count of session encounters, and hence justifies a longer time interval before retesting. The opposite for new words is likewise true.
    - Therefore:
    $$
    T = 1 - e^-(\lambda\Delta t)
    $$
    - Immediately following the baseline calibration, the last interaction takes the timestamp of calibration, used to calculate $\Delta t$ until the first appearance has happened.
    - $\Delta t$ is stored as a decimal number of days.

2. **Relative Interaction Pressure:** score that, depending on the density of appearance in the most recent 50 FPGs, enumerates the relative priority of this word to others
    - An Encounter Density score $D_e$ is calculated as the appearance percentage in the last 50 FPGs, stored as a probability between 0 and 1 (*if the total history contains less than 50 total sessions, the maximum session total is simply taken*)
    - The Relative Interaction Pressure is simply:
    $$
    I = 1 - D_e
    $$

3. **Historical Memory:** score enumerates the user's encounter history of the word, weighing encounters based on recency
    - Given the user's history with the word (*either constant # of N most recent appearances or entire kept history*), a historical memory $M$ is constructed by the complement to the weighted sum of memory scores aggregated by dividing by the sum of the time interval weights:
    $$
    H = 1 - \frac{\sum_{i=1}^{n} w_i * E_i}{\sum_{i=1}^{n} w_i}
    $$
    - $w_i$ denotes a time interval weight applied to each term denoted by $e^-(\Delta t_i)$
    - $E_i$ denotes the memory score stored directly in the appearance database

    - *Edge case:* immediately following callibration of a word, the user has not had a formal encounter of the word. This is mediated by seeding a default, value of `H = 0.5`. This is immediately overwritten after the first interaction, after which this mechanism should work perfectly.

These three components are combined to calculate an average recency score $R$:
$$
R = \frac{T + I + H}{3}
$$

All vocabulary units are sorted based on their recency scores, and a number N are chosen from those with the N highest scores.

It is inevitable that certain characters will be represented multiple times in the AVD, both as individal units as well as parts of other compound words. To sync the user's progress passage to passage, specifically *demotions* to characters in compound words will be mirrored with exact CSM protocol on the individual char itself, and ONLY when the pinyin is an exact match. Promotions will not reflect at all, since recognizing a character in one context does not guarantee recognition in another. Likewise, the converse, namely promotion or demotion of individual characters, will not reflect at all on any compound words that char is a part of. Carrying this to the appearance database, appearances of individual characters will be logged for every appearance of a compound word containing that character, granted that the pinyin is the same. The converse is *not* true.

Phase 1 is concerned with only one user. However, the architecture of the data is designed to accommodate multiple users already. A global, static and comprehensive `vocabulary` table houses all the words of the HSK 3.0 vocabulary list, tupled with its pinyin and tone as a string. A separate `users` table stores all users and appropriate information, including ID, email, created/joined timestamp, etc. A third list serves as a junction between individual users and their personal AVDs, storing all individual, local information pertaining the status of each vocabulary unit and mapping it to a user.

**On migration posture:** eventualy it will be the case that I would like to preserve my personal AVD through development changes and feature additions. However, for this initial phase of development no migration is necessary at all. A `seed.py` notebook builds the entire DB from scratch, and changes in schema will require a full re-seed. Seeding imports the entire HSK 3.0 vocabulary list and applies the baseline calibrations.

To calibrate a baseline literacy for the user at the absolute start of usage, the user simply selects an HSK level appropriate for their level. All vocab words belonging to levels under this will be tagged as Familiar, while all those *at* this level will be tagged Learning. Those above will remain Not Encountered. No separate function-word allowlist is needed on top of this: nearly every common grammatical particle (的, 了, 是, 不, 吗, 呢, 吧, etc.) is already an individual entry in the HSK 3.0 list, so baseline calibration alone tags them Familiar/Learning from session one, provided the user actually holds real vocabulary at that level going in (see the momentum assumption in Section XIX). The one confirmed exception, 呗, is simply excluded from the AVD and will never be generated or tested — not worth a special case for one word.


## VIII. FPG Specifications
When an FPG is called by the user, the target words chosen from the ILS are determined by pre-calculated and stored recency scores. The words are sorted by recency, and depending on the user-defined passage length, a certain number are chosen for the passage:
1. **30-50 chars:** 2-3 short sentences - 4-5 chars/words
2. **50-100 chars:** succinct paragraph - 8-10 chars/words
3. **100-150 char:** intermediate, longer paragraph - 12-15 chars/words
4. **150-250 chars:** advanced, multi-paragraph text - 15-20 chars/words

New vocabulary is introduced when the number of Learning + Familiar words in the ILS falls beneath a certain, constant threshold: 8 learning words and 15 familiar words. (*Note: these thresholds are subject to change*). The number of new words introduced depends on how much below the threshold the number of words has fallen, and is capped as follows:
1. **30-50 char:** 1 new char/word
2. **50-100 chars:** 2 new chars/words
3. **100-150 chars:** 3 new chars/words
4. **150-250 chars:** 4 chars/words

For example, if a certain user's ILS has only 5 learning words and 14 familiar words, they are experiencing a deficit of 4 new words. If they choose the most advanced length of 150-250 words, all 4 new words will be chosen, and the rest of the 11-16 existing words will be pulled from the sorted-by-recency AVD. In contrast, if they choose the shortest length, only 1 new word will be chosen, respecting the cap. As appropriate, newly introduced words are simply picked randomly from the family of vocabulary of the same HSK-designed proficiency level of the user (*Note: this separate proficiency level is mostly unrelated to Moxie. It is simply a tracking tool to assist in assigning new words.*)

A stripped down dictionary of all of the user's encountered (Mastered, Solid and Familiar) words is attached along with a dictionary of chosen frontier words and new words if applicable to the model. This second dict is numbered with the *maximum* number of vocab words allowed per the user-defined passage length. Both dicts simply map characters to pinyin. The model is then prompted with a message similar to the following:

`Given ONLY the vocabulary listed here, generate a [insert length range] [Simplified/Traditional] Mandarin character text as a pinyin decoding exercise for an English-speaking Mandarin student. The second list contains "frontier" learning words that MUST be MOSTLY included in the passage (at LEAST [insert minimum value]), while the first list contains solidly learned and familiar words that the user is reasonably comfortable with - these can be used WHENEVER appropriate. Do NOT under ANY CIRCUMSTANCES introduce NEW VOCABULARY at ANY POINT in the passage. This passage should be formatted with NO SPACES.`

Following an AI-generated passage output, the output is quickly scanned for length. Then, a self-written Bidirectional Maximum Matching (BiMM) segmentation function is called to split the passage into the appropriate vocabulary units. 
Otherwise, if (1) the frontier counter minimum is not reached, the following prompt is given:

`The number of frontier words is not enough. Edit both the passage to include [integer difference] more, while also KEEPING the existing ones. The same rules from above apply for generation.`

If (2) new vocab is introduced or any vocab units are unknown/not included in the AVD, the following prompt is given:

`Vocab unit(s) [list of all vocab units not existent in AVD] do not exist in the library. Diagnose and edit the passage to fix these mistakes. The same rules apply for generation as before.`

If both failure modes are violated, a combination of both is consolidated in one prompt. If this error loop continues two times with Sonnet failing to remedy the failing passage, FPG is stopped entirely and an error message is communicated back to the user.

Once every word in the passage has been validated (no new vocabulary is introduced and the # of frontier/new words is appropriate), pinyin is assigned through dictionary mapping with the loaded `data/hsk30.txt`. Since segmented units may still be single polyphonic characters or polyphonic compounds that have multiple pinyin readings, these are then prompted to Claude to ask which of the possible readings is correct in context:

`The following words/chars have multiple possible pinyin readings:[insert word/char #1] - is it [option 1] or [option 2] or ...? [insert word/char #2] - is it [option 1] or [option 2] or ...? Depending on the context of the passage, tell me which pinyin reading is accurate.`

IMPORTANT: When the user interacts with the prompt, all punctuation and spaces on nonbearing on the real-time tracking mechanism. When the answer is submitted, all except the characters and pinyin are trimmed such that the text is in the same format as the answer key. The user's text is then parsed character-by-character alongside the answer key and the grading is done. Ultimate CSM promotions and demotions are applied on each *unit* that contains a character with flagged errors.

Immediately following the attempted submission of the user, the length of the pinyin text is immediately evaluated using the real-time tracking mechanism to ensure that an answer for all characters present have been accounted for. If the user has failed to reach the number of characters defined or has typed more than there are in the passage, a brief error will flash and the passage will not be submitted. It may be possible to conduct this screen of analysis entirely in the frontend, before the POST request is even sent through.

(*Note: in the future, it will be prudent to include a UI feature that ensures the "Submit" button is not even activated until the user has finished decoding the entire passage. Likewise, a stopper that inhibits displaying any of the user's text on the screen after all characters have been accounted for, as well as a fun Mac "rejection sound effect", can be considered.*)

*Note: no numbers or English words for proper nouns/names are accommodated at this phase, as the first confuses the pinyin tracker while the second complicates the real-time tracking mechanism.*


## IX. Answer Key Pipeline
As previously stated, during the segmentation & passage validation step of a passage, the passage will be parsed to produce a pinyin text utilizing AVD look-ups. This pinyin answer key is stored in identical format to the passage: a list of all the individual vocab units in order with punctuation cut.


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
    - as soon as user encounters and interacts with a passage containing it, the unit shifts to Learning base
2. **Learning:** preliminary stage to train user's recognition at short-term intervals
    - to promote to Familiar, users must get the pinyin and tone right **two** times in a row
3. **Familiar:** secondary stage of recognition, at slightly longer intervals
    - to promote to Solid, users must get the pinyin and tone right **three** (more) times in a row
4. **Solid:** train user only in long intervals to prevent recognition erosion
    - to promote to Mastered, users must get the pinyin and tone right **five** (more) times in a row
5. **Mastered:** user revisits only once in a while
    - the user needs to maintain perfect recognition to maintain Mastered status

Errors are tagged to individual characters, but at promotion/demotion are applied to the entire vocabulary unit (if not solo character). For slight errors, the following specific rules apply:
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
The Adaptive Vocabulary Database (AVD) is sourced from the 11,000 word long HSK 3.0 vocabulary list. In contrast with adding words appropriately as the user encounters them, the entire list is instead seeded into the library from the start. An initial baseline calibration is performed with the user's self-reported HSK level. All more advanced words are labeled "Not Encountered" until passage generation has included them, via the algorithm described above in Section VIII.


## XIII. API Surface
The application needs four primary API endpoints that facilitate the user's interaction with the backend:
1. **FPG Loop:** `POST /api/fpg` (body: passage_length)
    - upon user prompting, runs frontier vocab selection, calls + validates Claude, builds answer key
    - returns {passage_id, rendered_text, char_count}
    - answer key stays server-side, waiting for grading
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
    - `llm.py` - facilitates calling Claude
    - `generation.py` - orchestrating layer for FPG
    - `grading.py` - broad orchestrator for entire grading pipeline
    - `levenshtein.py` - conducts Levenshtein distance grading
    - `csm.py` - updates AVD using grading info
    - `segmenter.py` - segments Claude passages
2. **`frontend/`:** contains all UI
    - `index.html` - homepage and starting point for a new session
    - `decode.html` - session page
    - `results.html` - results following grading & CSM analysis
3. **`docs/:`** relevant documentation to the project
    - CRD
    - PRD iterations
4. **`data/:`** all HSK data and relevant scripts for management
    - polyphone table - individual characters with mutliple, contextual pinyin representations
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
    - ***Streak-based tier promotion at 2 / 3 / 5.*** Consecutive correct decodes for Learning → Familiar → Solid → Mastered. Initial instinct, to be tuned from use.
        - **Revisit if:** a week of sessions shows the pacing is wrong. Expected to change.
    - ***Compound-to-character mirroring is asymmetric.*** Demotions propagate to the failing character; promotions don't. Recognizing in one context isn't evidence elsewhere; failing is.
        - **Revisit if:** character-level status drifts implausibly far from compound-level.
    - ***Demotion floors soften as tier increases.*** Mastered falls to Familiar, not Learning — higher tiers mean more exposure, faster recovery.
        - **Revisit if:** high-tier words repeatedly re-fail after demotion.
    - ***Encounter density is derived from an event log, not stored per word.*** Stored density means rewriting ~11,000 rows every session, since the denominator moves for unseen words; deriving is one aggregate query, absentees zero by absence.
        - **Revisit if:** the candidate pool grows large enough for per-generation aggregation to cost measurably.
    - ***Review events are logged from day one.*** Every unit records word, session, timestamp, time since prior review, status, outcome — needed for encounter density and future-scheduler training.
        - **Revisit if:** never. The log is cheap and irreplaceable.
    - ***Scheduler is hand-designed now, fitted later.*** Half-life regression needs review history; none exists yet. Hand-design intervals, routed through named constants for later fitted values.
        - **Revisit if:** enough review history accumulates — target phase 3.

4. **Language pipeline:**
    - ***Own maximum-matching segmenter; jieba dropped.*** An HSK list is a dictionary, not a segmenter — can't resolve overlapping matches (中国人民 as 中国+人民 vs 中国人+民). Maximum matching over it is ~40–70 lines, mine, and owns the computational core.
        - **Revisit if:** segmenter error rate proves unworkable — jieba is the fallback.
    - ***Model emits raw passage plus per-character pinyin; a polyphone table bounds trust.*** Segmentation resolves most polyphony via unique compound readings; the residue — polyphones like 了, 得, 长 — a dictionary can't resolve. Dictionary pinyin applies except in a bounded table (~100 entries), where the model's reading wins.
        - **Revisit if:** the table grows unmaintainable, or model pinyin proves unreliable on polyphones.
    - ***No dedicated function-word allowlist; HSK coverage plus baseline calibration already handles it.*** 的, 了, 是, 不, 我 and nearly every other common grammatical particle are individual entries in the HSK 3.0 list already, confirmed directly against `hsk30.txt` — the sole gap being 呗, which is simply left out of the AVD entirely rather than special-cased. Combined with baseline calibration (bulk-assigning at-or-below-level words to Familiar/Learning at seed time), these words are marked encountered before FPG ever runs, under the standing assumption that phase-1 usage always starts with real vocabulary momentum (>150 encountered words) rather than a true cold start. A dedicated allowlist mechanism would only earn its keep for a genuinely new user with near-empty AVD history — deferred along with general new-user onboarding.
        - **Revisit if:** cold-start onboarding for a user without existing momentum gets built, or a future gap word (beyond 呗) turns out to be both missing from HSK and load-bearing for basic sentence formation.
    - ***Baseline calibration precedes first use.*** Seeding all words as Not Encountered takes hundreds of sessions to reach my level, and makes session one ungenerateable. Bulk-assign by HSK level: at/below → Familiar/Solid, one above → Learning, rest → Not Encountered.
        - **Revisit if:** bulk assignment proves badly miscalibrated — passages feel trivial or unreadable early on.

5. **Architecture and stack:**
    - ***FastAPI, SQLAlchemy, SQLite, vanilla frontend.*** FastAPI over Flask: typed-Python habits, legible docs, model-serving convention. SQLite: churning schema, one deletable file. SQLAlchemy: standard ORM, decoupled from SQLite.
        - **Revisit if:** concurrency or multi-user arrives — the Postgres move stays mostly mechanical.
    - ***Vanilla HTML/CSS/JS for phase 1, deliberately.*** React first means learning abstractions before understanding the problem they solve. Phase-1 UI: three screens, a keystroke handler — raw teaches requests, JSON, the DOM. React arrives in phase 2, once vanilla gets painful (tap-to-define, reactive state).
        - **Revisit if:** the cursor implementation alone becomes unmanageable in vanilla.
    - ***No migration tooling in phase 1.*** Schema churns early. `seed.py` rebuilds from scratch; changes mean deleting the `.db` and re-seeding.
        - **Revisit if:** the first AVD or review-log state worth keeping — trigger for Alembic, once real use begins.
    - ***Answer keys never leave the server.*** API responses are readable in devtools. Passage goes out; pinyin key, segmentation, frontier set stay server-side until grading.
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
