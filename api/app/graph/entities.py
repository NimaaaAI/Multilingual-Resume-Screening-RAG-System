import json

from api.app.db.models import Entity, EntityEdge
from api.app.graph.llm import generate

EXTRACTION_PROMPT = """Extract structured information from this resume text. \
Respond with ONLY valid JSON, no markdown fences, no other text, in this exact shape:
{{
  "skills": ["skill1", "skill2"],
  "companies": [{{"name": "Company Name", "title": "Job Title"}}],
  "institutions": ["Institution Name"]
}}

Resume text:
{text}
"""


def extract_entities(text: str) -> dict:
    response = generate(EXTRACTION_PROMPT.format(text=text)).strip()
    response = response.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(response)


def get_or_create_entity(session, name: str, type: str, candidate_id: int | None = None) -> Entity:
    entity = session.query(Entity).filter_by(name=name, type=type).first()
    if entity is None:
        entity = Entity(name=name, type=type, candidate_id=candidate_id)
        session.add(entity)
        session.flush()
    return entity


def save_entities(session, candidate_id: int, extracted: dict, source_chunk_id: int | None = None) -> None:
    candidate_entity = get_or_create_entity(
        session, name=f"candidate:{candidate_id}", type="candidate", candidate_id=candidate_id
    )

    for skill in extracted.get("skills", []):
        skill_entity = get_or_create_entity(session, name=skill, type="skill")
        session.add(
            EntityEdge(
                entity_id_a=candidate_entity.id,
                entity_id_b=skill_entity.id,
                relation="has_skill",
                source_chunk_id=source_chunk_id,
            )
        )

    for company in extracted.get("companies", []):
        company_entity = get_or_create_entity(session, name=company["name"], type="company")
        session.add(
            EntityEdge(
                entity_id_a=candidate_entity.id,
                entity_id_b=company_entity.id,
                relation="worked_at",
                source_chunk_id=source_chunk_id,
            )
        )
        title = company.get("title")
        if title:
            title_entity = get_or_create_entity(session, name=title, type="title")
            session.add(
                EntityEdge(
                    entity_id_a=candidate_entity.id,
                    entity_id_b=title_entity.id,
                    relation="has_title",
                    source_chunk_id=source_chunk_id,
                )
            )

    for institution in extracted.get("institutions", []):
        institution_entity = get_or_create_entity(session, name=institution, type="institution")
        session.add(
            EntityEdge(
                entity_id_a=candidate_entity.id,
                entity_id_b=institution_entity.id,
                relation="studied_at",
                source_chunk_id=source_chunk_id,
            )
        )
