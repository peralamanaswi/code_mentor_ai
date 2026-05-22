"""Prompt engineering templates for all CodeMentor AI features.

Gen AI techniques used:
- Prompt Engineering: structured sections and output format in every template
- Context-Aware Reasoning: language, error, and code passed together
- Natural Language Generation: beginner-friendly tone instructions
- Error Interpretation: bug explainer prompts
- AI-based Recommendations: optimization and interview feedback
- Rule + LLM Hybrid: static tool results injected into prompts
- Structured Step-by-Step Reasoning: numbered analysis steps in full report
"""

from __future__ import annotations


def bug_explainer_prompt(code: str, error_msg: str, language: str = "auto") -> str:
    """Build prompt for AI Bug Explainer."""
    error_section = error_msg.strip() if error_msg.strip() else "No error message provided — infer likely bugs."
    return f"""You are CodeMentor AI, a friendly coding tutor for beginners.

Analyze this code and error. Use simple English. No jargon without explanation.

Language hint: {language}

CODE:
```
{code}
```

ERROR MESSAGE:
{error_section}

Respond in EXACTLY this structure (use these headings):

## Error Explanation
(What went wrong in one short paragraph)

## Why This Happened
(Plain reason a beginner can understand)

## Corrected Code
``` 
(Full fixed code in a fenced block)
```

## Beginner Explanation
(Teach the concept like talking to a first-year student)

## Best Practices
(3-5 bullet points)

## Optimization Suggestions
(2-4 practical tips)
"""


def interview_question_prompt(language: str, difficulty: str) -> str:
    """Build prompt to generate ONE theory‑focused interview question.

    The AI must NOT include any code snippets, examples, or sample solutions.
    It should ask about concepts, best practices, or language features.
    Ensure the wording varies each call.
    Keep the output under 80 words.
    """
    return f"""You are a coding interview coach for beginners.

    Generate ONE {difficulty}-level interview question about {language}.
    Focus on theory, concepts, or best‑practice discussion.
    Do NOT include any code examples.
    Keep under 80 words.
    """


def interview_evaluate_prompt(
    language: str,
    difficulty: str,
    question: str,
    answer: str,
) -> str:
    """Build prompt to evaluate interview answer."""
    return f"""You are a supportive interview evaluator for {language} ({difficulty} level).

QUESTION:
{question}

CANDIDATE ANSWER:
{answer}

Respond in EXACTLY this structure:

## Score
X/10 (single line, e.g. 7/10)

## Feedback
(What they did well and what to improve — beginner friendly)

## Mistakes
(Bullet list, or "None major" if good)

## Suggested Improvements
(2-4 bullets)

## Ideal Answer
(Short model answer a beginner could learn from)
"""


def voice_interview_evaluate_prompt(
    language: str,
    difficulty: str,
    question: str,
    transcript: str,
) -> str:
    """Evaluate spoken interview answer with communication analysis."""
    return f"""You are a supportive voice interview coach for {language} ({difficulty} level).

The candidate SPOKE their answer. Below is the speech-to-text transcript (may have minor errors).

QUESTION:
{question}

TRANSCRIPT (spoken answer):
{transcript}

Evaluate:
1. Technical accuracy
2. Completeness
3. Communication clarity
4. Missing concepts
5. Confidence level (from wording and completeness)

Respond in EXACTLY this structure:

## Score
X/10 (e.g. 6.5/10)

## Feedback
(Encouraging, beginner-friendly)

## Mistakes
(Bullet list)

## Missing Concepts
(Key topics they should have mentioned)

## Better Answer
(Ideal answer they could learn from)

## Confidence Analysis
(Low / Medium / High — brief why based on transcript)

## Communication Suggestions
(2-4 tips to speak more clearly and confidently in interviews)
"""


def complexity_ai_prompt(code: str, static_report: str) -> str:
    """Enhance radon/pylint static results with AI suggestions."""
    return f"""You are CodeMentor AI helping beginners understand code quality.

STATIC ANALYSIS (from Radon/Pylint):
{static_report}

CODE:
```
{code}
```

Respond in EXACTLY this structure:

## Complexity Level
(Low / Medium / High — one word with brief why)

## Readability Score
X/10 with one sentence why

## Maintainability
(Short paragraph for beginners)

## Optimization Suggestions
(4-6 bullet points)

## Better Coding Practices
(4-6 bullet points for this specific code)
"""


def security_ai_prompt(code: str, bandit_report: str) -> str:
    """Explain Bandit findings in beginner-friendly language."""
    return f"""You are a security mentor for beginner programmers.

BANDIT SCAN RESULTS:
{bandit_report}

CODE:
```
{code}
```

For each issue found (or common risks if scan is clean), respond in EXACTLY this structure:

## Security Summary
(One paragraph overview)

## Issues Found
For each issue use:
### Issue: [name]
- **Why Dangerous:** ...
- **Real-World Impact:** ...
- **Recommended Fix:** ...
- **Secure Practice:** ...

If no issues: explain what was checked and 3 prevention tips.

## Overall Recommendation
(2-3 sentences)
"""


def full_analysis_prompt(
    code: str,
    error_msg: str,
    bug_static: str,
    security_static: str,
    complexity_static: str,
    source_type: str = "text",
    extra_context: str = "",
) -> str:
    """Combined analyze-everything report prompt."""
    multimodal_note = ""
    if source_type != "text":
        multimodal_note = f"\nMULTIMODAL SOURCE: {source_type}\nEXTRACTED CONTEXT:\n{extra_context[:4000]}\n"
    return f"""You are CodeMentor AI. Create ONE professional combined report for a beginner.

INPUT TYPE: {source_type}
{multimodal_note}
CODE:
```
{code}
```

ERROR (if any):
{error_msg or "None provided"}

BUG / STATIC NOTES:
{bug_static}

SECURITY (Bandit):
{security_static}

COMPLEXITY (Radon/Pylint):
{complexity_static}

Also include brief **Interview / Learning Tips** if the upload was audio, video, or document.

Output EXACTLY in this format:

=========================
CODEMENTOR AI REPORT
=========================

## 1. Summary Score
Overall: X/100
Brief one-line verdict.

## 2. Bug Analysis
(Structured: errors, fixes, beginner tips)

## 3. Security Analysis
(Issues, fixes, practices)

## 4. Complexity Analysis
(Level, readability, maintainability)

## 5. Optimization Suggestions
(Bulleted actionable list)

## 6. Final Recommendation
(Encouraging next steps for the student)
"""


def context_retrieval_prompt(retrieved_hits: list) -> str:
    """Inject semantically similar past sessions into the LLM prompt.

    Gen AI technique: Context-Aware Reasoning — reuse prior bug fixes,
    code patterns, and mentor explanations from ChromaDB cosine search.
    """
    if not retrieved_hits:
        return ""

    blocks = [
        "You are CodeMentor AI. Use the following RELEVANT PAST SESSIONS "
        "as reference (similar bugs, code, or mentor answers). "
        "Do not copy blindly — adapt to the user's current input."
    ]
    for i, hit in enumerate(retrieved_hits[:5], start=1):
        doc = hit.get("document", "")
        meta = hit.get("metadata", {})
        sim = hit.get("similarity")
        topic = meta.get("topic", "unknown")
        lang = meta.get("language", "auto")
        err = meta.get("error_type", "")
        sim_note = f" (similarity: {sim})" if sim is not None else ""
        blocks.append(
            f"\n### Memory {i} — topic: {topic}, language: {lang}, "
            f"error: {err}{sim_note}\n{doc[:1200]}"
        )
    return "\n".join(blocks)


def static_only_notice() -> str:
    """Message when AI APIs are unavailable."""
    return (
        "_AI services are temporarily unavailable. "
        "Showing static analysis results only. Add API keys in `.env` for full AI explanations._"
    )
