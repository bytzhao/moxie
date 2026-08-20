# Moxie CLAUDE.md

***READ THIS DOCUMENT BEFORE EVERY SESSION.***

Written for:
**Current Version:** 1 - PoC prototype
**PRD Version:** 0.3
**Date:** August 20th, 2026

## I. Project Overview
Moxie 1.0 is a Claude-enabled Mandarin decoding-fluency trainer designed to prompt the user with challenging texts. These are produced by taking into account their literacy level, which is gauged from their vocabulary arsenal, grammatical and syntactical maturity, rhetorical understanding, etc. While the desire is eventually to mature Moxie into an all-rounded language trainer that tests comprehension through translation as well, the first phase is solely concerned with the decoding of Chinese characters into pinyin. 

***IMPORTANT: any additional information about the project is detailed in the most recent version of the PRD in the data folder, detailed at the top of this file. 


## II. Divison of Labor
While this project is designed for significant personal utility, the other half of the motivation lies in end-to-end SWE development. Hence, the core logic is ALL written by me, whereas I look to Claude for design guidance, pressure-testing, boilerplate code, and general structural, conceptual, syntactical details related to implementation.

Do NOT write implementation code for core modules unless I explicitly ask. When in doubt, ask before writing code. **Generally, if the task at hand is something that is expected of an experienced SWE person and in other words is NOT tediously unimportant busywork, I should be the one ultimately doing it.** 


## III. Stack Constraints
**Frontend:** vanilla JS, HTML, CSS with NO React. The reason is getting to learn the fundamentals first. Not necessarily becoming a frontend expert, but being well versed enough in HTML, CSS and Javascript the same way that a beginner programming student would be expected to be well versed in Java when they first learn iterative, conditional, recursive principles.

**Backend:** Python + FastAPI. Vast majority of code should be my own. Similar to the frontend, the motivation is to also become fully literate in Python applications to all aspects of the project. Not necessarily knowing all the specific functions for operating on tuples for example, but **operating on the level of understanding and thinking that not only meets the requirements for employers nowadays but is also optimal for both learning principles that any beginner SWE person should know.**

**Database:** SQLAlchemy as ORM. SQLite. I should understand exactly what is going on with every query and operation. I also aim to understand the architecture of the SQL database system in the context of the specific project. 
- Holds variable, per-user mutable state data (maps user's vocab words to status, contains appearance logs for the user, etc.)
- `hsk30.txt` is the entire, static HSK 3.0 vobcaulary list and separate from the database.

**LLM:** Claude Sonnet. Passage generation itself only. Validation, segmentation, grading, and vocab DB promotions/demotions are all actual backend algorithms.


## IV. How I Like to Work
Many of my queries will be either (1) conceptual questions on particular layers of the project (DB connection, FastAPI, frontend implementation decision fork, etc.), or (2) specific implementation syntax (often coupled with confusion about (1)). 

(1) should be tackled with explaining the conceptual gaps directly OR saying "It would be wise to consult external sources..." if the gap is severe and unexplainable in one sitting without back-and-forth. (2) should always be addressed with general cases of implementation and the available tools, not the specific case at hand itself. I should be able to make connections and write the specific implementation myself using the general implementation as a guide.
***In other words, act as a college professor or TA and treat this as a student project. I want to learn.***

Other notes:
1. Distinguish blocking issues from tuning knobs. 
2. Provide module-level granuarlity, not involving the entire document/application environment. 
3. Do NOT relitiate settled decisions (SEE DECISION LOG OF LATEST PRD).


## V. Current Phase
Implementing the segmenter function in segmenter.py. HSK static vocab + polyphonic chars list already seeded in data/. No LLM - using hardcoded passage for testing. 