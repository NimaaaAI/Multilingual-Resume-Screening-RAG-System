from api.app.llm import generate

EXPLANATION_PROMPT = """You are helping a recruiter evaluate a candidate for a job. \
Based ONLY on the resume excerpt below, write a short (2-3 sentence) explanation of why this \
candidate could be a good fit for the job description. Do not invent qualifications not present \
in the excerpt. Respond in {language}.

Job description:
{job_text}

Candidate: {candidate_name}
Resume excerpt:
{snippet}
"""

LANGUAGE_NAMES = {"en": "English", "fa": "Persian"}


def generate_explanation(job_text: str, candidate_name: str, snippet: str, language: str) -> str:
    language_name = LANGUAGE_NAMES.get(language, language)
    prompt = EXPLANATION_PROMPT.format(
        job_text=job_text, candidate_name=candidate_name, snippet=snippet, language=language_name
    )
    return generate(prompt).strip()
