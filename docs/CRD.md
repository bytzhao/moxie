**Overview:** This doc lays out the fundamental functionality of the desired application in broad strokes. A 2-3 week prototype scope will be decided after the first phase functionality is prioritized.

1. Supports both a Reading and Translation Mode that generate customizable AI-generated text output where...
    - Reading output is in Chinese. Translation output is in either Chinese or English, with the user task to translate the other way.
    - output is prompted by the user w/ built-in params: 
        (1) mode - reading/translation
        (2) length
        (3) difficulty level 1-10 (factoring in grammar structure, user's vocab level, etc.)
        (4) type of text (newspaper, literature, nonfiction book, scientific paper, historical document, etc.)
        (5) persistent background list of flagged words user would like to review that the model should prioritize including over other words in the DB.
        AND 
        (6) optional Claude user prompt to specify topic of discussion or other desired specifics.
    - textual output is designed to push the user's literacy, testing known/familiar words along with new additions.

2. All words and phrases generated should be easily tappable to see definition, pinyin, and example usages.

3. Adaptive vocabulary tracking database that routinely updates the user's vocabulary range and broader literacy, understanding of grammatical nuance, etc.
    - A primary database using a well-established and cohesive vocabulary set will be seeded.
    - Additional vocabulary specific to relevant domains/topics important to the user can be added via an interactive Claude prompt.
    - Status updates are done after each exercise.
        (1) Demotions happen when a user explicitly flags a phrase as unknown (relies on user's honesty)
        (2) Promotions happen when a user answers questions pertaining details necessitating understanding of that particular vocab, or successfully translates particular words/phrases.

4. In any mode, user can flag particular words/phrases to mark for review. In future outputs, the model will prioritize including this vocab in its responses (it is up to the user to update this library of flagged words & phrases to reflect their priorities).
    - User can order the list of flagged words.
    - The # of words in the flagged library is capped at 20.

5. The modes are testable to (1) push the user and (2) provide continuous feedback on the user's learning status and literacy.
    - Reading mode can have testing capability that is togglable. If user decides to be tested, a choice is presented between MCQ or FRQ testing, with testing-via-conversation built in.
    - Translation mode is always testable by default. 

6. (TBD) Conversation Mode: extends Reading Mode by allowing the user to interact with the text (best for argumentative textual outputs on substantive topics).
    - Vocabulary statuses are updated based on the user's usage of them.
    - (TBD) User's rhetorical/literary understanding/syntatical variety is also evaluated based on outputs.

## Open Questions
- Besides vocabulary, how literacy level should be determined.
    - Separate evaluations for rhetorical/literary understanding?
    - What about 4-character idioms or more advanced metaphors/literary allusions?
    - Syntactical variety?
    - Classical lexicon?
    ^Central problem: Mandarin ability seldom pertains vocabulary alone. Need other explicit knobs for delineating & consistently updating user's literacy.

- Other modes that should be considered? + What is the one mode that should be prioritized for phase 1?
    - Generally we need to find the core functionality of this website.
    - PRIMARY QUESTION: What is the sort of user experience that is most engaging & beneficial for the product goals stated above?
    - Also - is it too gamey, not gamey enough, etc.
NEW IDEA (7/25): user records reading a passage and the accuracy is decoded? 
NEW IDEA (8/3): Voice -> English translation.

- Vocabulary storage paradigm: individual words are distinct from use cases in particular phrases...
    - Do we store individual words independently from phrases?
    - Encapsulate phrases within words or words within phrases? (problem - how to deal with repeats?)
    - Pick a default database (i.e. HSK 1-6 vocabulary) and just go with that structure?

- Usage of existing materials "library" that fits user's needs?
    - Famous classic Chinese novels/free newspaper articles scraped from online?
    - Copyright concerns?
    - Later phase sort of issue?