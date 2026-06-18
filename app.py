"""
app.py — Milestone 5: query interface (Gradio web UI).

The Unofficial Guide to Binghamton University CS professors.
Type a question; the system retrieves relevant student-review chunks, answers
strictly from them, and shows which source documents the answer came from.

Run:
    python app.py
    # then open http://localhost:7860
"""

import gradio as gr

from query import ask


def handle_query(question: str):
    question = (question or "").strip()
    if not question:
        return "Please enter a question.", ""
    result = ask(question)
    sources = "\n".join(f"• {s}" for s in result["sources"]) or "(no sources — outside the guide's scope)"
    return result["answer"], sources


EXAMPLES = [
    "What do students say about Patrick Madden's lectures and exams?",
    "Is Thomas Bartenstein a good professor to take for CS 220?",
    "Which professor should I take for CS 220?",
    "How hard is Sujoy Sikdar's machine learning class?",
]

with gr.Blocks(title="Unofficial Guide — Binghamton CS Professors") as demo:
    gr.Markdown(
        "# Unofficial Guide — Binghamton CS Professors\n"
        "Ask about teaching style, exam difficulty, workload, or which professor to take. "
        "Answers come **only** from collected student reviews (Rate My Professors, forums) — "
        "if the guide doesn't cover something, it will say so."
    )
    inp = gr.Textbox(label="Your question", placeholder="e.g. What are Professor Madden's exams like?")
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)

    gr.Examples(examples=EXAMPLES, inputs=inp)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

if __name__ == "__main__":
    demo.launch()
