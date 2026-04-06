# 🚀 CreatorIQ — Strict Architecture (Alpha-Stable v2.2)

## Overview

CreatorIQ is a **project-based AI content operating system** that generates and manages content using a **graph-orchestrated, multi-stage pipeline** with strict execution rules, controlled memory, and reliability safeguards.

This architecture is **strictly defined** to eliminate ambiguity and ensure:

* No runtime crashes
* Predictable execution
* Controlled state growth
* Safe multi-user operation (Alpha scale)

---

# 🧠 Core Principles (NON-NEGOTIABLE)

1. **Graph-first execution (LangGraph)**
2. **Strict state schema (no free-form dicts)**
3. **Every node is fail-safe (never crashes)**
4. **Validation is mandatory at every stage**
5. **Memory is controlled (write rules enforced)**
6. **All side effects are isolated (LLM, DB, memory)**
7. **No hidden dependencies (explicit injection only)**

---

# 🏗️ High-Level Architecture

```id="arch_v22"
Frontend (React / Next.js)
        ↓
FastAPI API Layer (Async नियंत्रक)
        ↓
Execution Layer (LangGraph Engine - Controlled Sync)
        ↓
AI Layer (Agents + LLM Router + Circuit Breaker)
        ↓
Memory Layer (Qdrant + Session State)
        ↓
Data Layer (MongoDB)
```

---

# ⚙️ EXECUTION MODEL (CRITICAL)

| Layer     | Execution Mode  |
| --------- | --------------- |
| FastAPI   | Async           |
| LLM Calls | Async           |
| LangGraph | Controlled Sync |
| MongoDB   | Async           |
| Qdrant    | Async           |

### RULE:

> LangGraph execution must NOT spawn uncontrolled async tasks

---

# 🔁 ORCHESTRATION LAYER (LangGraph)

## Graph Structure (MANDATORY)

```id="graph_v22"
START
  ↓
[Idea Node]
  ↓
[Hook Node]
  ↓
[Script Node]
  ↓
[Screenplay Node]
  ↓
[Validation Loop ↺]
  ↓
[Summarize + Prune Node]
  ↓
END
```

---

## 🔁 VALIDATION LOOP (MANDATORY)

Each stage follows:

```id="validation_pattern"
Generate → Validate → Fix (if invalid) → Return
```

### RULES:

* Max retries: 2
* If still invalid → return best-effort output + error flag
* NEVER block execution

---

## 🔀 CONDITIONAL EDGES (STRICT)

Every conditional edge MUST have:

```python id="router_pattern"
def router_fn(state) -> str:
    return "valid_path"
```

```python id="edge_pattern"
graph.add_conditional_edges(
    "node",
    router_fn,
    {
        "path_a": "next_node",
        "path_b": END
    }
)
```

### RULES:

* Router must NEVER return None
* Must match mapping keys exactly

---

# 🧾 STATE MANAGEMENT (STRICT SCHEMA)

## STATE SCHEMA (MANDATORY)

```python id="state_schema"
state = {
    "user_input": str,
    "current_stage": str,

    "messages": list,  # capped history

    "outputs": {
        "idea": str | None,
        "hook": str | None,
        "script": str | None,
        "screenplay": str | None
    },

    "metadata": {
        "user_id": str,
        "thread_id": str,
        "project_id": str
    },

    "memory_context": list,

    "validation": {
        "is_valid": bool,
        "errors": list
    },

    "error": str | None,
    "failed_node": str | None
}
```

---

## STATE RULES

* Max size: **200KB**
* Messages capped: **last 5 interactions**
* No raw LLM responses stored
* No uncontrolled key additions

---

# 🤖 NODE CONTRACT (MANDATORY)

Every node MUST follow:

```python id="node_contract"
def node_fn(state: dict) -> dict:
    try:
        # 1. Read state
        # 2. Generate (LLM call)
        # 3. Validate
        # 4. Update state
        return updated_state

    except Exception as e:
        return {
            **state,
            "error": str(e),
            "failed_node": "node_name"
        }
```

---

## NODE RULES

* No direct DB writes
* No global state mutation
* No assumptions about missing keys
* All outputs go into `state["outputs"]`

---

# 🔀 LLM ROUTING LAYER

## Structure

```python id="llm_router"
class LLMRouter:
    def route(self, request):
        pass

    def fallback(self, request):
        pass
```

---

## RULES

* Usage tracking = optional injection
* No hard dependency on observability
* All failures handled internally

---

# 🛡️ CIRCUIT BREAKER (STRICT PLACEMENT)

## Location:

> ONLY inside LLM Router

## RULES:

* Cooldown: 10s (Alpha)
* On failure → fallback model
* If all fail → return safe response

---

# 🧠 MEMORY ARCHITECTURE (QDRANT — STRICT)

## MEMORY TYPES

### 1. Short-Term (State)

* Stored in `state`
* Always pruned

---

### 2. Long-Term (Qdrant)

## COLLECTION DESIGN

* Single collection: `creatoriq_memory`
* Payload:

```json id="memory_payload"
{
  "user_id": "...",
  "thread_id": "...",
  "project_id": "...",
  "type": "idea|hook|script|summary"
}
```

---

## RETRIEVAL

* Top-K: 3–5
* Filtered by:

  * user_id
  * thread_id

---

## MEMORY WRITE POLICY (CRITICAL)

### ✅ STORE ONLY:

* Final outputs
* User edits
* Summarized insights

### ❌ DO NOT STORE:

* Raw prompts
* Intermediate outputs
* Full state dumps

---

# 💾 DATA LAYER (MongoDB)

## COLLECTIONS

* Users
* Projects
* Versions
* Strategy

---

## CONFIG (ALPHA SAFE)

```python id="mongo_config"
maxPoolSize = 10
minPoolSize = 2
timeout = 5000
```

---

# 🔄 VERSIONING SYSTEM

## Temporary

* TTL: 48h

## Saved

* Persistent

---

# 🌐 WEB SEARCH & CACHE

## RULES

* Cache before scraping
* Deduplicate queries
* TTL-based invalidation

---

# 🔐 SECURITY (ALPHA)

* Input validation (pattern-based)
* Prompt injection detection (basic)
* Data isolation via Qdrant filters

---

# 🧪 OBSERVABILITY

## REQUIRED

* Request ID per execution
* Node-level logs
* Error tracking

---

# ⚡ PERFORMANCE LIMITS (ALPHA)

* Safe concurrency: 5–10 users
* No background workers
* No distributed queue

---

# 🚨 HARD CONSTRAINTS

* No infinite loops
* No unbounded memory
* No blocking calls in async layer
* No silent failures

---

# 🧭 EXECUTION FLOW SUMMARY

1. API receives request
2. State initialized (strict schema)
3. LangGraph executes nodes sequentially
4. Each node:

   * Generates
   * Validates
   * Updates state
5. Memory retrieved + injected
6. Final output returned
7. Selective memory write to Qdrant

---

# 🎯 ALPHA SUCCESS CRITERIA

* ✅ Zero runtime crashes
* ✅ Full pipeline executes
* ✅ State remains bounded
* ✅ Memory isolation works
* ✅ 5–10 concurrent users stable

---

# 🔥 FINAL SUMMARY

CreatorIQ v2.2 is now:

> A **strict, graph-orchestrated AI system** with:

* Deterministic execution
* Controlled state
* Safe memory (Qdrant)
* Robust failure handling

---

This architecture eliminates:

* Hidden failures
* State explosion
* Fragile execution

And provides a **solid foundation for Alpha → Beta → Production scaling**.

---
