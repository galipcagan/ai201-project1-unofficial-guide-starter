# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

**Student reviews of Computer Science professors at Binghamton University (SUNY).**

This system answers questions about CS professors and courses at Binghamton — teaching style, exam difficulty, workload, grading fairness, and which professors or sections to take versus avoid. It's valuable because official channels don't carry this: the course catalog and faculty pages list titles, prerequisites, and research interests, but never that one professor reads monotone off slides while another records every lecture and curves fairly. That signal is scattered across hundreds of short, unstructured Rate My Professors and Coursicle reviews and Reddit threads — anecdotal, inconsistent, and tedious to aggregate by hand.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Rate My Professors — Binghamton school page | School-level reviews | https://www.ratemyprofessors.com/school/958 |
| 2 | Rate My Professors — Binghamton CS professor listing | Professor index | https://www.ratemyprofessors.com/search/professors/958?q=*&did=11 |
| 3 | Rate My Professors — Patrick Madden | Individual professor reviews | https://www.ratemyprofessors.com/professor/140813 |
| 4 | Rate My Professors — Thomas Bartenstein | Individual professor reviews | https://www.ratemyprofessors.com/professor/1789308 |
| 5 | Rate My Professors — Nael Abu-Ghazaleh | Individual professor reviews | https://www.ratemyprofessors.com/professor/152851 |
| 6 | Rate My Professors — Ping Yang | Individual professor reviews | https://www.ratemyprofessors.com/professor/1114773 |
| 7 | Rate My Professors — Mike Lewis | Individual professor reviews | https://www.ratemyprofessors.com/professor/166445 |
| 8 | Rate My Professors — Adnan Rakin | Individual professor reviews | https://www.ratemyprofessors.com/professor/2905662 |
| 9 | Coursicle — CS 220 | Course-level reviews | https://www.coursicle.com/binghamton/courses/CS/220/ |
| 10 | Coursicle — CS 320 | Course-level reviews | https://www.coursicle.com/binghamton/courses/CS/320/ |
| 11 | Coursicle — CS 350 | Course-level reviews | https://www.coursicle.com/binghamton/courses/CS/350/ |
| 12 | Coursicle — CS 471 | Course-level reviews | https://www.coursicle.com/binghamton/courses/CS/471/ |
| 13 | Coursicle — Thomas Bartenstein professor page | Per-professor aggregation | https://www.coursicle.com/binghamton/professors/Thomas+Bartenstein/ |
| 14 | College Confidential — "Binghamton Computer Science Major" | Discussion thread | https://talk.collegeconfidential.com/t/binghamton-computer-science-major/1081373 |
| 15 | Quora — "Is CS at Binghamton challenging?" | Q&A thread | https://www.quora.com/Is-computer-science-in-Binghamton-university-challenging |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:** 512 characters maximum per chunk (≈ 110–130 tokens).

**Overlap:** 50 characters, applied **only** when a single record is longer than 512 characters and must be split.

**Why these choices fit your documents:**
The corpus is *review-aware, mixed-granularity*. Most RateMyProfessors entries are short, self-contained reviews (the mean chunk is 354 chars; min 87, max 511), so the ingestion pipeline ([ingest.py](ingest.py)) treats **one review as one atomic chunk** and never splits it — splitting a short review would orphan the opinion ("avoid him") from the professor and course it refers to. Each review chunk is given a context prefix (`Professor X — COURSE (RateMyProfessors review, date). Student rating: quality, difficulty.`) so it is interpretable standalone even when the review text itself doesn't repeat the professor's name. The aggregate stats line for each professor becomes its own `profile_summary` chunk. Only the long-form College Confidential forum posts exceed 512 chars; those are split with 50-char overlap so a sentence spanning a boundary isn't lost. The 512 cap is also bounded by the embedding model (`all-MiniLM-L6-v2` truncates at 256 tokens), guaranteeing no silent truncation.

**Preprocessing before chunking:** `clean_text()` decodes HTML entities (`&amp;`, `&#39;`, `&nbsp;`), strips any HTML tags, drops known page boilerplate (Helpful / Report / Share / "Read more" / "N helpful"), and collapses redundant blank lines. (Because sources were captured as text, the HTML path is mostly a safety net for any pages later saved as raw `.html`.)

**Final chunk count:** **67 chunks** across 11 source documents (10 RateMyProfessors professor pages + 1 College Confidential thread). This sits comfortably inside the healthy 50–2,000 range; 4 of the 67 are split pieces of long forum posts.

---

## Sample Chunks

<!-- Paste 5 representative chunks from your document collection after running your ingestion pipeline.
     For each chunk, note which source document it came from.
     These must be actual text — not screenshots. -->

These are actual chunks emitted by [ingest.py](ingest.py) (and stored in `chunks.json`). Each is a complete, retrievable thought — the context prefix keeps it interpretable on its own.

**Chunk 1** — source: `documents/rmp_madden.txt` (review, CS375, 391 chars)
```
Professor Patrick Madden — CS375 (RateMyProfessors review, 2024-10-29). Student rating: quality 5.0/5, difficulty 3.0/5.
Professor Madden sets the standard! His lectures are clear, easy to follow, and all recorded for your reference. His tests are very fair, and if you pay attention in class and use the study guide, you'll be set up for success. He genuinely wants his students to succeed!
```

**Chunk 2** — source: `documents/rmp_bartenstein.txt` (review, CS220, 473 chars)
```
Professor Thomas Bartenstein — CS220 (RateMyProfessors review, 2025-10-19). Student rating: quality 1.0/5, difficulty 5.0/5.
Extremely monotone and boring lectures, he mostly reads off the slides, so it's impossible to understand what's important or not. Pop quizzes are memorization-based, so it's hard to do well. He's slightly passive-aggressive when you ask questions via email, so it's hard to approach him. His exams are difficult and will tank your grade. Avoid him.
```

**Chunk 3** — source: `documents/rmp_weinschenk.txt` (profile_summary, 136 chars)
```
George Weinschenk — overall rating 3.0/5 based on 179 ratings; 32% would take again; average difficulty 3.2/5. Frequently teaches CS101.
```

**Chunk 4** — source: `documents/rmp_sikdar.txt` (review, CS436, 411 chars)
```
Professor Sujoy Sikdar — CS436 (RateMyProfessors review, 2026-04-05). Student rating: quality 1.0/5, difficulty 5.0/5.
Possibly the worst class I've taken in all 4 years here. Terribly long and difficult hws, pop quizzes nearly everyday that has questions scattered across the entire lecture, and not even gonna mention exams. Incredibly difficult to follow lecture material. Grades harshly. Avoid at all costs.
```

**Chunk 5** — source: `documents/forum_collegeconfidential_cs_major.txt` (forum_post, part 2/4, 509 chars)
```
b if my degree was in English. You can always take CS110/140 (Intro Programming Courses) and see what you think of them. I don't feel that the classes get more difficult than those, you mainly just keep building at a similar pace from there.

Professors to avoid: Foreman and Steflik. Foreman teaches a pass/fail required 2 credit course CS 101. You don't need to/can't avoid him there, but don't take him for a real 3/4 credit course like Operating Systems. Neither teaches anything in lecture and then often
```
> *Note on Chunk 5:* this is one piece of a long forum post that was split. The leading fragment "b if my degree was in English. You can always take" is the **50-character overlap** carried over from the previous chunk (part 1/4) — included deliberately so the split doesn't sever the sentence about intro courses. This is the one place where a chunk isn't perfectly clean on its own; for short reviews (Chunks 1–4) no splitting occurs, so they read as complete standalone thoughts.

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dim sentence embeddings), loaded with `SentenceTransformer("all-MiniLM-L6-v2")` in [retrieval.py](retrieval.py). It runs locally with no API key and no rate limits, embeddings are L2-normalized, and they are stored in a persistent **ChromaDB** collection configured for **cosine** distance. Chosen because the corpus is short English reviews, iteration is fast and free locally, and 384-dim vectors are plenty to separate professors/courses.

**Production tradeoff reflection:** If cost weren't a constraint I'd weigh a larger hosted embedder (e.g. OpenAI `text-embedding-3-large`, Voyage, or Cohere). Tradeoffs: **(1) accuracy on domain text** — MiniLM is general-purpose and, as my retrieval test showed, matches sentiment words ("best", "easy A") more strongly than the abstract concept of "highest aggregate rating"; a stronger model separates these better. **(2) context length** — MiniLM truncates at 256 tokens, which forces splitting the long forum posts; an 8k-token embedder could embed a whole thread as one unit and avoid boundary loss. **(3) latency / local vs API** — MiniLM is instant, free, and keeps student reviews off third-party servers; a hosted model adds per-call cost, network latency, and a privacy consideration. **(4) multilingual** — not needed here (English-only), so paying for it would be wasted. Conclusion: MiniLM is the right fit for this project; I'd only upgrade if eval showed retrieval consistently missing relevant reviews.

---

## Retrieval Test Results

<!-- Run these 3 queries through your retrieval system and record the top returned chunks.
     For at least 2 of the 3, explain why the returned chunks are relevant to the query.
     Results must be text — not screenshots. -->

Run with `python retrieval.py` (k=5, cosine distance — lower is more similar). Showing top 3 of 5 per query.

**Query 1:** *What do students say about Patrick Madden's lectures and exams?*

Top returned chunks:
- (dist 0.272, `rmp_madden.txt`) "Professor Madden sets the standard! His lectures are clear, easy to follow, and all recorded for your reference. His tests are very fair…"
- (dist 0.314, `rmp_madden.txt`) "If you have the option to take a class with him, take it. He grades easily, and there are no surprises on tests and assignments."
- (dist 0.387, `rmp_madden.txt`) "The exams are pretty hard and you aren't exactly prepared well for them. He is a fun guy, but he really just reads the slides…"

Relevance explanation: All 5 returned chunks are Madden reviews (correct source), with low distances (0.27–0.39). They directly cover both halves of the query — lecture style ("clear… all recorded", "reads the slides") and exams ("tests are very fair" vs. "exams are pretty hard"). The spread captures the real disagreement among reviewers, which is exactly what a grounded answer should summarize.

---

**Query 2:** *Is Thomas Bartenstein a good professor to take for CS 220?*

Top returned chunks:
- (dist 0.344, `rmp_bartenstein.txt`) "If you have to take him he's really not that bad. Lectures can be boring but just listen to what he says. Tests have gotten much easier over the years…"
- (dist 0.378, `rmp_rakin.txt`) "one of the best CS professors at Bing imo, hes the goat. exams felt hard… but were graded fairly…"  ← off-target
- (dist 0.382, `rmp_bartenstein.txt`) "He's okay for 220, but isn't as good for this class. The class felt disorganized…"

Relevance explanation: 4 of 5 results are Bartenstein reviews tagged CS220/CS320 (correct), covering his lectures, pop quizzes, and exams. The exception is rank 2 — an **Adnan Rakin** review (CS436) that matched on the generic phrase "one of the best CS professors" rather than on Bartenstein or CS220. It's a moderate distance (0.378) and a good illustration of the contradictory/loosely-related retrieval risk noted in planning.md: semantic similarity on "good professor" language pulled in the wrong professor. It's mitigated downstream because the chunk's metadata names Rakin, so generation can ignore it.

---

**Query 3:** *Which CS professor has the highest student ratings and an easy class?*

Top returned chunks:
- (dist 0.272, `rmp_rakin.txt`) "one of the best CS professors at Bing imo, hes the goat…"
- (dist 0.322, `rmp_abughazaleh.txt`) "This is one of the best professors for computer science. The class is hard but one of the most fair…"
- (dist 0.348, `rmp_lewis.txt`) "Breaks down the material and makes it easy to understand… he is the head of the CS department…"

Relevance explanation: Partially relevant. The query has two intents — *highest rating* (a numeric aggregate) and *easy class* — and retrieval matched the second well (reviews using "best"/"easy") but **missed** the first: the `profile_summary` chunks that actually carry aggregate ratings (e.g. Ping Yang 4.7/5, the genuine highest) were not retrieved, because MiniLM keys on praise words rather than the concept of a numeric rating. Distances are still low (0.27–0.37), so the failure is one of *intent coverage*, not weak matching — a candidate to revisit by boosting profile-summary chunks or splitting the query. (Tracked for the Failure Case Analysis section.)

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

**How source attribution is surfaced in the response:**

---

## Example Responses

<!-- Provide at least 2 grounded responses (query + response + source attribution)
     and 1 out-of-scope query showing your system's refusal.
     All entries must be text — not screenshots. -->

**Grounded response 1**

Query:

Response:

Source attribution:

---

**Grounded response 2**

Query:

Response:

Source attribution:

---

**Out-of-scope query**

Query:

System response (refusal):

---

## Query Interface

<!-- Describe your query interface: what are the input fields, what does the output look like?
     Then provide a complete sample interaction transcript showing a real exchange. -->

**Input fields:**

**Output format:**

---

**Sample Interaction Transcript**

<!-- Show a complete query → response exchange as it actually appears in your interface.
     Must be text — not a screenshot. -->

> **User:** 

> **System:** 

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

**What the system returned:**

**Root cause (tied to a specific pipeline stage):**

**What you would change to fix it:**

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

**One way your implementation diverged from the spec, and why:**

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*

**Instance 2**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
