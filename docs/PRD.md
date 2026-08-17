# Moxie: Product Requirements Document

*Note: while Claude was consulted in the finalization of scope details, the appropriate skeletal structure of this document, and technical consultation on architecture and stack considerations, all elements of this document's language and framing are my own.*

**Product Phase:** 1 - initial PoC prototype
**Document Version:** 0.0
**Date:** August 11th, 2026


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
1. 
    Development blocks that are (1) specifically to complexity of implementing a particular feature of reasonable granularity and (2) persist beyond a one-week time-frame, should be addressed at the product scope level rather than remedied through increased usage of Claude for software shortcuts. A thorough re-examination of this document in its most recent version, alongside any relevant, subsequent functionality or UIUX designs, should be conducted to locate feasible scope cuts or reframes.

[Note for Claude: curious to know your thoughts on this. My main other concern here is w/ the consistency criteria outlined above. I don't want this to drag into October w/out meaningful progress. That's the main problem. But are there other reasonable, common, and note-worthy kill criteria that I should also be aware of?]


## IV. Scope
The following functionality are *included* in this phase of development, enumerated here in general and expounded on further in later sections where appropriate:
1. 
    **Adaptive Vocabulary Database (AVD):** primary tracking mechanism for user's literacy level. Contains a pre-seeded list (the HSK 3.0 vocabulary list) of both compound words and individual characters, each tagged with the user's interaction level ranging from "Not Encountered Yet" to "Mastered", as well as a time-stamp for the last encounter by the user and/or encounter density score in last few sessions compared to other characters in the database.
    - **Character Status Monitor (CSM) System:** the cohensive framework used to apply updates to characters given a user's decoding response. Consists of (1) hard rules for promotion and demotion, (2) a familiarity tiers system tagged to both compound words and individual characters and (3) a points system 
2.  
    **Frontier Passage Generation (FPG):** capability enabled by Claude, informed by the AVD as well as user-identified passage length specification.
    - **Tone Marks:** denoted 1-4 by convention with 0 representing the static tone, appended to the end of each character's pinyin.
    - **Jieba Segmentation Answer Keys:** in the interest of full flexibility, answer keys are stored in jieba segmentation format using the `jsrpy/Chinese-NLP-Jieba` library, along with other appropriate pre-existing repositories.
3. 
    **Real-Time Input Tracking:** As the user types decodes the prompt, their progress per individual character is tracked via a dynamic caret that responds to individual tone mark inputs (valid numbers 1 through 5), and a color coding mechanism that advances through characters you have completed decoding.

The following functionality are *not included* in this phase of development, enumerated here:
1. **Tone mark flexibility:** PoC will prioritize *mandatory* inclusion of tone marks for each character in the user's response. Later phases may implement a togglable setting for tone marks; for example, (1) all characters, (2) none, and (3) only frontier words above a certain CSM designated tier.  
2. **Text Medium, Theme, & Difficulty Mode:** Besides the state of the AVD and a user-desired text length, no other factors are considered in FPG. 
3. **Smart Char-by-char Analysis:** While future iterations may include algorithms to avoid over-penalizing "one-off" mistakes by the user (i.e. forgetting a tone mark for one character), this initial phase will deterministically treat tone numbers as separators between characters and match the user's pinyin char-by-char.
4. **Jieba Compound Word Analysis:** While the answer key is encoded using jieba segmentation, spaces are nonbearing for the CSM system and the user is neither rewarded or penalized for their choice of organizing compound words. 
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
3. **Last Interaction:** timestamp signifying time and date of last passage tested containing this word, updated after each FPG
4. **Encounter Density:** appearance percentage in last N FPGs (*Note: N to be defined*)
5. **Recency Score:** derived from timestamp date and encounter density, and scaled given the status of the word
- The scaling factor corresponding status is derived from the principle that the more familiar a word is, the more time should be elapsed before retesting
    - Lower status (i.e. Learning) corresponds to a strong boost, while higher status (i.e. Mastered) corresponds to a de-boost
- The char/words' recency scores are sorted, and targetted **frontier** words are picked from the top during each FPG

It is inevitable that certain characters will be represented multiple times in the AVD, both as individal units as well as parts of other compound words. To sync the user's progress passage to passage, specifically *demotions* to compound words will be mirrored with exact CSM protocol on the individual char itself. Promotions will not reflect at all, since recognizing a character in one context does not guarantee recognition in another. Likewise, the converse, namely promotion or demotion of individual characters, will not reflect at all on any compound words that char is a part of.

Necessary data used to calculate the Encounter Density is taken after each successful passage attempt for *every* unit of the AVD regardless of appearance to properly and continuously update it. Otherwise, no other information is necessary to the maintenance of the AVD and is therefore discarded. *Note: eventually, new pages such as a Dashboard, Usage History or any similar user-facing screens aggregating their literacy progress data will most likely introduce new requirements for data collection after each session.*

Phase 1 is concerned with only one user. However, the architecture of the data is designed to accommodate multiple users already. A global, static and comprehensive `vocabulary` table houses all the words of the HSK 3.0 vocabulary list, tupled with its pinyin and tone as a string. A separate `users` table stores all users and appropriate information, including ID, email, created/joined timestamp, etc. A third list serves as a junction between individual users and their personal AVDs, storing all individual, local information pertaining the status of each vocabulary unit and mapping it to a user.


## VIII. FPG Specifications
When an FPG is called by the user, the target words chosen from the ILS are determined by pre-calculated and stored recency scores. The words are sorted by recency, and depending on the user-defined passage length, a certain number are chosen for the passage:
1. **30-50 words:** 2-3 short sentences - 4-5 chars/words
2. **50-100 words:** succinct paragraph - 8-10 chars/words
3. **100-150 words:** intermediate, longer paragraph - 12-15 chars/words
4. **150-250 words:** advanced, multi-paragraph text - 15-20 chars/words

New vocabulary is introduced when the number of Learning + Familiar words in the ILS falls beneath a certain, constant threshold: 8 learning words and 15 familiar words. (*Note: these thresholds are subject to change*). The number of new words introduced depends on how much below the threshold the number of words has fallen, and is capped as follows:
1. **30-50 words:** 1 new char/word
2. **50-100 words:** 2 new chars/words
3. **100-150 words:** 3 new chars/words
4. **150-250 words:** 4 chars/words

For example, if a certain user's ILS has only 5 learning words and 14 familiar words, they are experiencing a deficit of 4 new words. If they choose the most advanced length of 150-250 words, all 4 new words will be chosen, and the rest of the 11-16 existing words will be pulled from the sorted-by-recency AVD. In contrast, if they choose the shortest length, only 1 new word will be chosen, respecting the cap. As appropriate, newly introduced words are simply picked randomly from the family of vocabulary of the same HSK-designed proficiency level of the user (*Note: this separate proficiency level is mostly unrelated to Moxie. It is simply a tracking tool to assist in assigning new words.*)

A stripped down dictionary of all of the user's Mastered, Solid and Familiar words is attached along with a dictionary of chosen frontier words and new words if applicable to the model. This second dict is numbered with the *maximum* number of vocab words allowed per the user-defined passage length. Both dicts simply map The model is then prompted with a message similar to the following:

`Given ONLY the vocabulary listed here, generate a [insert length range] [Simplified/Traditional] Mandarin character text as a pinyin decoding exercise for an English-speaking Mandarin student. The second list contains "frontier" learning words that MUST be MOSTLY included in the passage (at LEAST [insert minimum value]), while the first list contains solidly learned and familiar words that the user is reasonably comfortable with - these can be used WHENEVER appropriate. Do NOT under ANY CIRCUMSTANCES introduce NEW VOCABULARY at ANY POINT in the passage. This passage should be formatted with NO SPACES. Then, format the entire passage in a SECOND output structure, this time as a list where each element is a vocab units in the passage, in order. In this list, OMIT ALL punctuation and trim all spaces. It should only be the characters of the text.`

The first string will be shown to the user, while the second is used for CSM analysis down the line. Following an AI-generated passage output, the two outputs are quickly evaluated to ensure reasonable and equal length.

Secondly, the text is rigorously parsed element-by-element to ensure (1) no extra new vocabulary is introduced and (2) the number of frontier words included passes the *minimum* threshold defined above. One parse per vocab unit easily handles it. If the prompt fits these criteria, FPG is concluded.

Otherwise, if (1) the frontier counter minimum is not reached, the following prompt is given:

`The number of frontier words is not enough. Edit both the passage to include [integer difference] more, while also KEEPING the existing ones. The same rules from above apply for generation.`

If (2) new vocab is introduced or any vocab units are unknown/not included in the AVD, the following prompt is given:

`Vocab unit(s) [list of all vocab units not existent in AVD] didn't match their pinyin words given because the jieba segmentation either doesn't exist/these words are new and not in the provided lists above. Diagnose and edit the passage to fix these mistakes. The same rules apply for generation.`

If both failure modes are violated, a combination of both is consolidated in one prompt.

*Note: no numbers or English words for proper nouns/names are accommodated at this phase.*


## IX. Answer Key Pipeline
*Note: unsure here after more thought whether to use jieba segmentation or not. Sticking to the HSK vocabulary list should provide a comprehensive inventory of characters and compound words that naturally brings its own segmentation. CSM analysis is also done on these vocab units. For the sole purpose of accommodating polyphonic pinyin, jieba seems redundant.*

Following successful FPG yielding a passage separable into individual HSK vocab units or during validation of said passage, the passage will be parsed to produce a pinyin text utilizing AVD look-ups. *Note: TBD whether the pinyin should be produced after or during the validation of the characters passage (latter risks uneccessary work for flawed passage).* This pinyin answer key is stored in identical format to the passage: a list of all the individual vocab units in order with punctuation cut.


## X. Grading Specifications
Promotions are obviously recorded when full correctness is observed. Demotions are split into two different kinds of errors, one light, the other severe. Slight errors are characterized by (1) genuine keyboard 
1. **Slight Errors:** small mistakes in four categories - (1) genuine keyboard mistypes, (2) nasal swap ('n' vs. 'ng' ending), (3) the umlaut omission (u vs. ü, the latter registered as a v), and (4) retroflex blur ('zh' vs. 'z', 'ch' vs. 'c', etc.)
2. **Severe Errors:** tone mistakes or anything else not falling into the 4 error categories categorized under slight mistakes
Under this framework, errors are evaluated under the 4 categories. If none flag, they are categorized as severe as an "else catch-all".

To check for slight errors, we use a mix of a custom Regex-Weighted Levenshtein distance algorithm, as well as subsequent, individual regex Finite State Automata to check the non-typo cases:
1. **Typo Analysis & User-Pinyin Normalization:**
    First, the tone is stripped from the *correct* pinyin representation of the character, under which is the 3 non-typo cases are evaluated to see if they are genuinely possible errors (i.e. retroflux error is only possible when the first character is a consonant in set {'c', 's', 'z'}. Umlaut omission is only valid if following 'n' and 'l' consonants). A regex is then developed that accounts for the applicable errors (each regex described in detail in (2), where a combination is easily constructable).
    
    The Levenshtein distance algorithm is applied on the user's input in comparison with this regex after mapping the keyboard with spatial coordinates. 
    
    The regex string that minimizes the distance score is chosen, and if is under a threshold that qualifies the user's input as a typo, the other 3 non-typo checks are then done in (2). Additionally, if the distance between the user's input and the chosen regex string is *nonzero*, a typo flag is also recorded. The user's string is promptly replaced by this typo-normalized regex string for further analysis.
    
    Otherwise, if the user's input is too far from any of the possible regex strings to be considered a typo at all, it is automatically assumed to be a severe mistake and (2) is skipped.

    *Note: at this point the system has enough information to perform the demotion since the slight/severe distinction has been made. Step (2) is mostly a formality done for full transparency and to complete the analysis full circle. It is also presumably not costly to perform given that the combination error regex was defined here in (1) already.**

2. **Retroflex, Umlaut, and Nasal Error Checks:**
    The normalized pinyin is evaluated further against the individual FSAs for each error:
        - The retroflex error regex is defined by the optionality of an 'h' following the first consonant. For example, the regex for 'chun' or 'cun' taking into account retroflex error is `^c(h)?un$`. 
        - The umlaut omission regex is defined by the OR operator for u and ü (expectedly denoted with 'v' by the user). For example, the regex for 'lv' or 'lu' taking into account umlaut omission is `^l(u | v)$`. 
        - The nasal error regex is defined by the optionality of a 'g' at the very end of the pinyin. For example, the regex for 'zeng' or zen' taking into account nasal error is `^zen(g)?$`.
    For each automaton that the normalized string passes, the flag is raised for that error.

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
The Adaptive Vocabulary Database (AVD) is sourced from the 11,000 word long HSK 3.0 vocabulary list. In contrast with adding words appropriately as the user encounters them, the entire list is instead seeded into the library from the start and words are labeled as "Not Encountered" until passage generation has included them, via the algorithm described above in Section VIII.


## XIII. API Surface
No idea here. Have absolutely no experience w/ API stuff and would really appreciate both guidance as well as maybe help/external tools so I can understand how this works.


## XIV. Architecture & Stack
Need Claude help to make the following informed decisions
**Frontend:** entirely written with vanilla HTML, CSS, and Javascript implementation, for the purposes outlined in Sections I and III.
**API:** FastAPI because...
**SQL:** not entirely sure which package is best
**Repo Layout:** docs, api, frontend, backend?

Environment handling... .venv probably? requirements.txt needed maybe.


## XV. LLM Integration
I would like to use Claude. Not sure which model is most appropriate in terms of balancing accuracy w/ efficiency. I would like a very low fail rate in terms of needing regeneration being less than 10%. Wait time for passage generation is most important on the time parameter - less than 10 seconds would be nice but 20 secs would be the absolute max.

Cost estimate per session - no idea. I would like for phase 1 to append the usage to my existing Claude Pro subscription if there are any tokens given there. If not, oh well.

UI can just flash a loading bar. 

Passages eventually would be nice to be cached for full transparency and revisiting purposes if user wants to review progress or retry old passages. But for this phase, there's no reason to.

Rate limit and failure handling? Dunno tbh.


## XVI. Build Plan & Milestones
**Milestone #1:** end-to-end loop defined by...
- AVD is seeded with CSM mechanics wired in (general toy AVD with random level of literacy)
- FPG w/ Claude looped in and callable from basic frontend UI setup
- User can submit and AVD changes applied (no need for keyboard tracking yet)
^idk if there's a more bitesized version of this.
I just need need to make sure: 
1. AVD updating logic is sound = testing the CSM given some toy initial state
2. calling Claude + FPG loop is sound

HOWEVER, it is in my interest to make Milestone 1 perhaps a little more slim but still preserving most of the core, computational, algorithmic flair and impressiveness. For short-term resume purposes.

Key dependencies: 
1. I cannot test AVD state update until we have wired Claude in and are able to both do FPG successfully (consistently without errors). 
2. I cannot do the latter (Claude FPG) until we are able to get HSK 3.0 and the SQL DB format figured out. Also, figuring out how to seed a hard-coded literacy level (appropriate Claude responsibility?)

**Milestone #2:** adding features...
- keyboard tracking UI
- results page UI


## XVII. Work Split & Open Design Questions
As detailed above, while I am determined to *limit* the usage of Claude Code as much as possible on this project, and certainly none of the UI design, backend Python logic, API calls, socket events, etc. will be touchable by Claude, certain elements of the project **deemed both tedious and unproductive or otherwise un-beneficial to growth** can be handed of to Claude. This includes config, styling, scaffolding, etc. 

^Needs to be more specific.

Other than the questions a reader of this document might have about the functionality for this particular phase I can't really think of anything that is open for future phases? Other than:
- multidimensional literacy model paradigm
- UI for possible dashboard/open AVD
- Possible progress data the user would want to see in a dashboard type deal

The risks are enumerated as follows:
- This might take too long - it is kind of a lot, especially to write without the assistance of Claude (for the most part). But we accept that.
    - Only issue is that I lose interest. But that's usually because of other reasons or seriously abnormally challenging circumstances. If we break it down into implementation modules, should be fine.
- AI costs too much (using it for a month for example on a weekly basis shouldn't cost more than... 5 bucks? 10 bucks?) - LMAO I REALLY HOPE NOT


## XVIII. Deferred Functionality Backlog
**Comprehension Tier:** important, but not as crucial as decoding.
- **Translation Module:** hence, this is also delayed for similar reasons.
- **Tap-to-define:** this too.
- **Text-to-Speech/Speech-to-Text:** yup, this too.


**Chengyu & Classical Lexicon:** idea is to include dimension of literacy for classical texts and idioms - too complicated for initial phase. Complicates simple AVD sourced from HSK 3.0, which although may contain some idioms and classical lexicon, may not be as complete.
**Existing-text Library:** copyright concerns mostly. Also, the Claude-wrapper idea is a big implementation plus and important to the SWE goal.
**Mult-user Auth:** immediate usage priority is for me personally.


## XIX. Decision Log


# QUESTIONS FOR CLAUDE RIGHT NOW:
- I'm not quite familiar with the concept of data migration posture and all that. I only know generally it deals with "expanding features => data gets more complicated, so how do we deal with that." Not familiar with exact strategy on this front. Also generally with the seeding vocab. Not familiar with the specifics here. But I think I've elucidated the general mental model I have in Section 8 and Section 12.
- Issue with jieba - wondering if it's really necessary. by default if HSK vocab is comprehensive then the polyphonic issue is resolved naturally. Also the compound words inherently provide a way of segmentation, no? I'm considering abandoning jieba if HSK vocab list is seriously good enough. 
- I want Moxie to generally be more computational for resume reasons. I'm already applying regex somewhat + Levenshtein distance to the typo analysis  but maybe the recency score can be more... impressive? Also related - my idea of boundary for Claude for this phase is ONLY passage generation, even though the LLM can genuinely handle literally everything else. My reason is (1) less API calls the better for compute/efficiency reasons and (2) for my resume I think it's more impressive to use algorithms for specific things

