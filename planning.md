# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

**Student reviews of Computer Science professors at Binghamton University (SUNY).**

This guide covers firsthand student experiences of CS professors and courses at Binghamton — teaching style, exam difficulty, workload, grading fairness, and which professors or sections to take versus avoid. This knowledge is hard to find through official channels because the university's course catalog and faculty pages list only course titles, prerequisites, and research interests; they never reveal that one professor reads monotone off slides while another records every lecture and curves fairly. That signal lives instead in hundreds of short, unstructured Rate My Professors and Coursicle reviews and Reddit threads, where it is anecdotal, inconsistent, and tedious to aggregate by hand — exactly the gap a retrieval system can fill.

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

The sources below were chosen for *coverage*, not redundancy: school-level reviews, individual-professor pages (teaching style + exam difficulty), course-level pages (workload + what to expect in a specific class), and discussion threads (comparisons and major-level advice).

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Rate My Professors — Binghamton school page | School-wide reviews and overall reputation/ratings context | https://www.ratemyprofessors.com/school/958 |
| 2 | Rate My Professors — Binghamton CS professor listing | Index of CS professors with ratings, difficulty, would-take-again % | https://www.ratemyprofessors.com/search/professors/958?q=*&did=11 |
| 3 | Rate My Professors — Patrick Madden | Individual reviews: clear/recorded lectures, fair tests (4.2, 85% take again) | https://www.ratemyprofessors.com/professor/140813 |
| 4 | Rate My Professors — Thomas Bartenstein | Individual reviews: monotone lectures, hard exams (CS 220/240/350) | https://www.ratemyprofessors.com/professor/1789308 |
| 5 | Rate My Professors — Nael Abu-Ghazaleh | Individual reviews: strong CS 220 teacher, demanding, great office hours | https://www.ratemyprofessors.com/professor/152851 |
| 6 | Rate My Professors — Ping Yang | Individual reviews: highly rated (4.7), low difficulty | https://www.ratemyprofessors.com/professor/1114773 |
| 7 | Rate My Professors — Mike Lewis | Individual reviews: another core CS instructor for contrast | https://www.ratemyprofessors.com/professor/166445 |
| 8 | Rate My Professors — Adnan Rakin | Individual reviews: ML/newer-faculty perspective | https://www.ratemyprofessors.com/professor/2905662 |
| 9 | Coursicle — CS 220 (Computer Systems / Architecture) | Course-level reviews comparing professors for the same course | https://www.coursicle.com/binghamton/courses/CS/220/ |
| 10 | Coursicle — CS 320 (Computer Architecture) | Course-level reviews: workload and instructor quality | https://www.coursicle.com/binghamton/courses/CS/320/ |
| 11 | Coursicle — CS 350 (Operating Systems) | Course-level reviews (57+) on difficulty and pacing | https://www.coursicle.com/binghamton/courses/CS/350/ |
| 12 | Coursicle — CS 471 (Programming Languages) | Course-level reviews: Hallahan, hard-but-curved tests | https://www.coursicle.com/binghamton/courses/CS/471/ |
| 13 | Coursicle — Thomas Bartenstein professor page | Per-professor review aggregation across his courses | https://www.coursicle.com/binghamton/professors/Thomas+Bartenstein/ |
| 14 | College Confidential — "Binghamton Computer Science Major" thread | Long-form discussion: major difficulty, professor/course advice | https://talk.collegeconfidential.com/t/binghamton-computer-science-major/1081373 |
| 15 | Quora — "Is computer science in Binghamton university challenging?" | Q&A perspective on program rigor | https://www.quora.com/Is-computer-science-in-Binghamton-university-challenging |

> **Note on Reddit (r/SUNYBinghamton):** Reddit threads are a valuable source for professor comparisons, but `reddit.com` blocks automated crawlers, so these can't be fetched programmatically. For breadth, relevant threads should be collected by manually copying the post + comment text into a `.txt`/`.md` file under `documents/` during Milestone 2 (ingestion).

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** 512 characters (≈ 110–130 tokens) maximum per chunk.

**Overlap:** 50 characters, applied **only** when a long document has to be split.

**Reasoning:**
The corpus is *mixed-granularity*. Most RateMyProfessors and Coursicle entries are short, self-contained reviews (typically 100–500 characters) where a single review carries one coherent opinion — sentiment + professor + course + exam/workload detail all in 1–2 sentences. The long-form College Confidential and Quora threads are the opposite: multi-paragraph posts where a point is spread out.

So the strategy is **review-aware, not blind fixed-window**:
1. **Split each source into atomic reviews/posts first** (one review = one record), using the natural delimiters in the saved text (blank lines between reviews, or a `---` separator I insert during ingestion).
2. **If a review/post is ≤ 512 chars, keep it as a single chunk** — never split a short review, because cutting it would orphan the sentiment from the professor/course it refers to.
3. **If a post exceeds 512 chars** (forum threads), split into 512-char chunks with 50-char overlap so a sentence spanning a boundary isn't lost.
4. **Attach metadata to every chunk** — `source_url`, `source_type` (rmp/coursicle/forum), `professor`, `course` — because Coursicle reviews often name the professor only in the page context, not the review text. Metadata preserves attribution and lets us answer "who teaches X."

The 512-char cap is also bounded by the embedding model: `all-MiniLM-L6-v2` truncates input at **256 tokens**, so staying well under that guarantees no silent truncation.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dim), stored and queried in **ChromaDB** (cosine similarity). Generation uses **Groq** (Llama 3.x) per `requirements.txt`.

**Top-k:** 5. Reviews are short and noisy, and any single professor draws contradictory opinions, so retrieving 5 chunks gives the LLM enough corroborating/dissenting reviews to summarize a *consensus* rather than parroting one outlier. (Will tune 4–6 during Milestone 4 if context gets noisy.)

**Production tradeoff reflection:**
If cost weren't a constraint I'd weigh moving to a larger hosted embedding model (e.g., OpenAI `text-embedding-3-large` or Voyage/Cohere embeddings). Tradeoffs:
- **Accuracy on domain text:** MiniLM is general-purpose and may weakly separate near-synonyms that matter here ("curves generously" vs "harsh grader," professor nicknames/misspellings). A larger model embeds these distinctions better.
- **Context length:** MiniLM's 256-token cap is fine for short reviews but forces splitting on long threads; a long-context embedder (8k tokens) could embed a whole forum post as one unit and avoid boundary loss.
- **Latency / local vs API:** MiniLM runs locally in milliseconds with no per-call cost or rate limits — ideal for a class project and for iterating on chunking. A hosted model adds network latency, API cost, and a privacy consideration (sending student reviews to a third party).
- **Multilingual:** Not needed here (English-only corpus), so paying for a multilingual model would be wasted.
Conclusion: MiniLM is the right call for this project; I'd only upgrade if eval showed retrieval missing relevant reviews due to weak semantic separation.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What do students say about Patrick Madden's lectures and exams? | Lectures are clear and recorded for later reference; generally well-liked (≈4.2 overall, ~85% would take again), but some warn the exams are hard and you can feel underprepared for them. |
| 2 | Is Thomas Bartenstein a good professor to take for CS 220? | Mostly negative: monotone lectures read off slides, memorization-based pop quizzes, difficult exams; many students would not take him again. |
| 3 | Which professor is recommended for CS 220 (Computer Systems / Architecture)? | Nael Abu-Ghazaleh is praised — knows the material, explains in detail, strong office-hours help — but expects a solid systems background. Recommended over Bartenstein for the same course. |
| 4 | How highly rated is Ping Yang, and is her class hard? | Highly rated (≈4.7/5) with relatively low difficulty (~2.4); positive reviews. |
| 5 | How challenging is the Binghamton CS major / a course like CS 350 (Operating Systems)? | Students describe the major as genuinely challenging; CS 350 has a large review volume and is regarded as demanding. (Tests grounding on the forum/Quora long-form sources, not just RMP.) |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. **Contradictory reviews for the same professor.** Almost every professor has both "awesome" and "awful" reviews. With top-k=5, retrieval could surface a one-sided slice (e.g., only the harsh reviews), and the LLM would then report a skewed consensus. Mitigation: retrieve enough chunks to capture the spread, and prompt the model to acknowledge disagreement ("opinions are mixed: some say…, others say…") rather than asserting a single verdict.

2. **Lost professor/course context when chunking.** On Coursicle, a review's text often doesn't repeat the professor's name — the name is page context. If I chunk only the visible review text, a retrieved chunk becomes un-attributable ("the tests were brutal" — whose?). Mitigation: store `professor` and `course` as chunk metadata during ingestion and include them in the context passed to the LLM.

3. **Noisy / unfetchable sources skewing coverage.** RMP and Coursicle are JS-heavy and Reddit blocks crawlers, so the saved corpus may over-represent whatever was easiest to capture. This could make some professors look more discussed than they are. Mitigation: track per-source chunk counts and note coverage gaps honestly in the eval.

4. **Out-of-scope / name-mismatch queries.** A question about a professor not in the corpus, or using a misspelling/nickname, may retrieve loosely-related chunks instead of returning "I don't know." Mitigation: enforce grounding in the system prompt and consider a similarity-score floor below which we refuse to answer.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 1. DOCUMENT INGESTION                                                      │
│    Saved review text + forum posts in  documents/*.txt / *.md             │
│    (RMP, Coursicle saved manually; forum threads pasted in)               │
│    Tools: Python stdlib file I/O  (pdfplumber only if any .pdf added)     │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 2. CHUNKING                                                                │
│    Split into atomic reviews (≤512 chars kept whole); long posts split     │
│    at 512 chars w/ 50-char overlap. Attach metadata:                       │
│    {source_url, source_type, professor, course}                            │
│    Tools: custom  chunk_text()  in Python                                  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 3. EMBEDDING + VECTOR STORE                                                │
│    Embed each chunk → 384-dim vector; persist with metadata                │
│    Tools: sentence-transformers (all-MiniLM-L6-v2)  →  ChromaDB            │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 4. RETRIEVAL                                                               │
│    Embed user query → ChromaDB cosine search → top-k = 5 chunks            │
│    (+ optional similarity floor to refuse low-confidence matches)          │
│    Tools: ChromaDB query API                                               │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 5. GENERATION                                                              │
│    Build prompt = grounding system prompt + retrieved chunks + question;   │
│    LLM answers ONLY from context and cites source_url                      │
│    Tools: Groq (Llama 3.x)  →  Gradio/Streamlit UI (Milestone 5)          │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**
Tool: Claude (Claude Code). Input: the **Chunking Strategy** and **Architecture** sections above, plus a sample saved review file from `documents/`. Ask it to implement `load_documents()` (read every file in `documents/`, capture filename → `source_url`/`source_type`) and `chunk_text()` matching my spec — split on review delimiters, keep ≤512-char reviews whole, split longer posts at 512 chars with 50-char overlap, and emit `{text, metadata}` records. Verify: run on the real corpus, print total chunk count and 5 sample chunks, and manually confirm no short review was split and every chunk carries `professor`/`course` metadata.

**Milestone 4 — Embedding and retrieval:**
Tool: Claude. Input: the **Retrieval Approach** section and the chunk-record format from Milestone 3. Ask it to implement `build_index()` (embed chunks with `all-MiniLM-L6-v2`, persist to ChromaDB with metadata) and `retrieve(query, k=5)`. Verify: run my 5 evaluation questions through `retrieve()` and check by eye that the top chunks are about the right professor/course (e.g., Q2 returns Bartenstein/CS 220 reviews), and that an off-topic query returns low similarity scores.

**Milestone 5 — Generation and interface:**
Tool: Claude. Input: the **Generation** stage from Architecture plus my grounding requirements (answer only from retrieved chunks, surface disagreement, cite `source_url`, refuse when unsupported). Ask it to implement the Groq call with a grounding system prompt and a Gradio/Streamlit front end (query box → answer + cited sources). Verify: confirm a known-answer query (Q1 Madden) is grounded and cited, and that an out-of-scope query (e.g., a non-Binghamton professor) triggers refusal instead of a hallucinated answer.
