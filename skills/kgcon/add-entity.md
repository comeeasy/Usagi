# Shared Entity Addition Procedure

This document defines the core entity addition procedure shared by the `kgcon` and `add-entity` skills.

---

## What is a bundle?

A **bundle** is what one invocation of add-entity / one registration batch adds: **one or more** RDF nodes (Concepts and/or Individuals) **plus** the relationships between them (via `object_properties`, types, and data properties).

- **Dependency order:** Create **Concepts** first (Individuals need `types` to reference class IRIs). For Individuals linked by `object_properties`, ensure each **target** Individual exists before you reference it—either it already exists in the ontology or you create it **earlier in the same bundle**.
- **Reuse:** Prefer reusing existing Concepts or Individuals from `search_entities` instead of minting duplicates.

---

## Language Rule

**Entity labels and literal values must follow the language of the original input source.**

- Korean source → Korean labels
- English source → English labels
- IRIs must always use ASCII (kebab-case or PascalCase); never include non-ASCII characters in IRIs

---

## Entity kinds and tools

| Kind | OWL | Write tool |
|------|-----|------------|
| Concept | `owl:Class` | `add_concept` |
| Individual | `owl:NamedIndividual` | `add_individual` (and `update_individual` for fixes) |

**MCP limitation:** There is **no** `update_concept` or `delete_concept` in MCP. To avoid bad Concept axioms, rely on `search_entities(kind="concept")` before `add_concept`. If a Concept was already added incorrectly, fixing it may require the Usagi UI or REST API (`backend/api/concepts.py`); document the issue for the user instead of inventing unsupported MCP calls.

---

## Pre-addition: Understand the Ontology

Before adding any node or edge in the bundle:

1. **Similar Concepts**
   ```
   search_entities(ontology_id, query="<keyword>", kind="concept", use_vector=true)
   ```
   - Always use `use_vector=true` for hybrid search when available.
   - Reuse existing classes when they match; note parent-class candidates.

2. **Similar Individuals** (avoid duplicates)
   ```
   search_entities(ontology_id, query="<keyword>", kind="individual", use_vector=true)
   ```

3. **Properties** (when setting relationships)
   ```
   search_relations(ontology_id, query="<relationship keyword>")
   ```

---

## Adding a Concept

```
add_concept(
    ontology_id     = <ONTOLOGY_ID>,
    iri             = <base_iri + PascalCase local name>,
    label           = <label in the source language>,
    super_classes   = [<parent class IRI>],
    description     = <optional rdfs:comment in source language>
)
```

**IRI rules:** Append a PascalCase local name to the base IRI (e.g. `https://example.org/ont/` + `SpecialForces`). No spaces or non-ASCII in IRIs.

**Checklist:**

- [ ] Equivalent or very similar Concept does not already exist
- [ ] Parent class(es) are correct
- [ ] IRI matches namespace conventions

---

## Adding an Individual

```
add_individual(
    ontology_id       = <ONTOLOGY_ID>,
    iri               = <base_iri + category/kebab-case-name>,
    label             = <human-readable name in the source language>,
    types             = [<Concept IRI list>],
    data_properties   = [{"property_iri": "...", "value": "...", "datatype": "xsd:string"}],
    object_properties = [{"property_iri": "...", "target_iri": "..."}]
)
```

**IRI rules:** e.g. `https://example.org/ont/unit/3rd-armor-brigade` with categories like `unit/`, `location/`, `operation/`.

**Checklist:**

- [ ] At least one Concept in `types`
- [ ] Every `target_iri` in `object_properties` exists before this Individual is committed (or is created earlier in the bundle)
- [ ] IRI is not a duplicate

---

## Mandatory validation: `run_reasoner`

After **any** `add_concept`, `add_individual`, or `update_individual` that affects the bundle, run:

```
run_reasoner(
    ontology_id   = <ONTOLOGY_ID>,
    entity_iris   = [<all IRIs in this bundle that you created or modified>]
)
```

Interpret the result:

| Outcome | Meaning |
|---------|---------|
| `consistent: true` and no meaningful `violations` | Bundle is logically acceptable under OWL |
| `consistent: false` | Inconsistency—fix or roll back |
| `violations: [...]` | Review each item and correct Individuals via `update_individual` where possible |

**Do not treat SPARQL as the primary pass/fail gate.** Use `sparql_query` only for optional SELECT/ASK probes (mutating SPARQL is blocked by the tool).

---

## Inner Ralph loop: fix until reasoner is clean (or stop with a report)

If `run_reasoner` fails or lists violations:

1. **Re-ground context:** Call `search_entities` and `search_relations` again with focused queries so you see nearby Concepts, Individuals, and property IRIs.
2. **Individuals:** Use `update_individual` to adjust `label`, `types`, `data_properties`, `object_properties`, `same_as`, or `different_from` as needed. Only fields you pass are updated; pass `[]` for a list field to clear it (per tool semantics).
3. **Concepts:** MCP cannot update Concepts—prefer prevention via search before add. If stuck, explain the gap and point to UI/REST.
4. **Re-run** `run_reasoner` on the same `entity_iris` set (expanded if you touched neighbors).

**Iteration cap:** Prefer up to **5** full fix cycles. If there is no progress (same violations repeat), stop, summarize violations, and list options (manual edit, delete Individual via `delete_individual` if appropriate, or REST for Concepts).

---

## Optional: SPARQL checks

`sparql_query` may be used for SELECT/ASK diagnostics (e.g. listing types of an IRI). It does not replace `run_reasoner` for consistency.

---

## Summary checklist for a bundle

- [ ] Concepts before dependent Individuals; object targets exist or are created first in-bundle
- [ ] `search_entities` / `search_relations` used before minting new IRIs
- [ ] `run_reasoner` executed after writes; fix loop applied when needed
- [ ] User informed of final IRIs and reasoner outcome
