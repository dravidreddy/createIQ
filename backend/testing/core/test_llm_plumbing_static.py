"""Static regression checks for the Groq-only LLM plumbing."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_prompts_do_not_request_internal_monologue():
    prompts_dir = ROOT / "app" / "prompts"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in prompts_dir.glob("*.yaml"))

    assert "internal_monologue" not in combined
    assert "step-by-step" not in combined.lower()


def test_vector_memory_is_user_scoped_not_pipeline_scoped():
    service = read("app/memory/service.py")
    vector_store = read("app/memory/vector_store.py")

    assert "user_id: str = \"\"" in service
    assert "user_id=user_id or \"pipeline\"" in service
    assert "FieldCondition(key=\"thread_id\"" not in vector_store


def test_groq_provider_filters_internal_router_kwargs():
    provider = read("app/llm/groq_provider.py")

    assert '"response_schema", "model_override"' in provider
