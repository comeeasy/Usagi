# Shared Entity Addition Procedure

This document defines the core bundle-registration procedure shared by the `kgcon` and `add-entity` skills.

---

## What is a bundle?

A **bundle** is a set of one or more RDF nodes (Concepts and/or Individuals) **plus all relationships between them** (via `object_properties`, `types`, and `data_properties`) that are registered together in a single pass.

- **Concepts before Individuals**: Individuals need `types` that reference class IRIs, so Concepts must exist first.
- **Target Individuals before source Individuals**: For any `object_property`, the target IRI must already exist in the ontology *or* be created earlier in the same bundle.
- **Reuse before minting**: Use `search_entities` to find existing Concepts or Individuals; prefer reuse over creating duplicates.

---

## Language Rule

**Entity labels and literal values must follow the language of the original input source.**

- Korean source → Korean labels
- English source → English labels
- IRIs must always use ASCII (kebab-case for Individuals, PascalCase for Concepts); never include non-ASCII characters in IRIs.

---

## Entity kinds and tools

| Kind | OWL | Write tool |
|------|-----|------------|
| Concept | `owl:Class` | `add_concept` |
| Individual | `owl:NamedIndividual` | `add_individual` (fixes via `update_individual`) |

**MCP limitation:** There is **no** `update_concept` or `delete_concept`. To avoid bad Concept axioms, always `search_entities(kind="all")` before calling `add_concept`. If a Concept was added incorrectly, document the issue for the user and point to the Usagi UI or REST API for correction.

---

## Pre-registration: search before creating

Before adding any node or edge in the bundle:

1. **Find similar entities** (Concepts and Individuals together)
   ```
   search_entities(ontology_id, query="<keyword>", kind="all", use_vector=true)
   ```
   Reuse existing classes when they match; note parent-class candidates and avoid duplicate Individuals.

2. **Find properties** (when setting relationships or data attributes)
   ```
   search_relations(ontology_id, query="<keyword>")
   ```

**`kind` rule — always use `"all"`:** `search_entities` must always be called with `kind="all"`. Never pass `kind="concept"` or `kind="individual"`; using `"all"` ensures both Concepts and Individuals are considered in a single pass and prevents missed matches.

**Query rule — one keyword per call:** `query` must be a **single word** (e.g. `"unit"`, `"location"`, `"isPartOf"`). Never pass multi-word phrases or sentences. If you need to explore multiple concepts, call the tool multiple times with one keyword each.

---

## Adding a Concept

```
add_concept(
    ontology_id   = <ONTOLOGY_ID>,
    iri           = <base_iri + PascalCase local name>,
    label         = <label in source language>,
    super_classes = [<parent class IRI>],
    description   = <optional rdfs:comment in source language>
)
```

**IRI rules:** Append a PascalCase local name to the base IRI (e.g. `https://example.org/ont/SpecialForces`). No spaces or non-ASCII characters.

Checklist before calling:
- [ ] Equivalent or very similar Concept does not already exist
- [ ] Parent class(es) confirmed via `search_entities`
- [ ] IRI matches namespace conventions

---

## Adding an Individual

```
add_individual(
    ontology_id       = <ONTOLOGY_ID>,
    iri               = <base_iri + category/kebab-case-name>,
    label             = <human-readable name in source language>,
    types             = [<Concept IRI list>],
    data_properties   = [{"property_iri": "...", "value": "...", "datatype": "xsd:string"}],
    object_properties = [{"property_iri": "...", "target_iri": "..."}]
)
```

**IRI rules:** Use a category prefix followed by a kebab-case local name, e.g. `https://example.org/ont/unit/3rd-armor-brigade`. Common categories: `unit/`, `location/`, `operation/`, `event/`.

Checklist before calling:
- [ ] At least one valid Concept in `types`
- [ ] Every `target_iri` in `object_properties` exists before this call (or is created earlier in the bundle)
- [ ] IRI is not a duplicate (verified via `search_entities`)

---

## Mandatory validation: `run_reasoner`

After **every** `add_concept`, `add_individual`, or `update_individual` that affects the bundle, run:

```
run_reasoner(
    ontology_id  = <ONTOLOGY_ID>,
    entity_iris  = [<all IRIs created or modified in this bundle>]
)
```

Interpret the result:

| Outcome | Meaning |
|---------|---------|
| `consistent: true`, no meaningful violations | Bundle is logically acceptable |
| `consistent: false` | Ontology-level inconsistency — must fix or roll back |
| `violations: [...]` | Review each; correct Individuals via `update_individual` |

**Do not use SPARQL as the pass/fail gate.** `sparql_query` (SELECT/ASK only) is for optional diagnostic probes; the OWL reasoner is the authoritative validator.

---

## Inner Ralph loop: fix until reasoner is clean

If `run_reasoner` returns violations or `consistent: false`:

1. **Re-ground**: call `search_entities` and `search_relations` with focused **single-keyword** queries to see nearby Concepts, Individuals, and property IRIs.
2. **Fix Individuals**: use `update_individual` to adjust `label`, `types`, `data_properties`, `object_properties`, `same_as`, or `different_from`. Pass `[]` to a list field to clear it entirely (per tool semantics). Only provided fields are updated.
3. **Fix Concepts**: MCP cannot update Concepts. Prevent errors via search first. If stuck, document the issue as a guardrail and instruct the user to use the Usagi UI or REST API.
4. **Re-run** `run_reasoner` on the same `entity_iris` set (expand the set if you touched neighbours).

**Iteration cap:** Up to **5** full fix cycles. If the same violations repeat with no progress (gutter detected), stop the inner loop, summarise the violations, log a guardrail, and report to the user with options (manual edit, `delete_individual`, REST for Concepts).

**Guardrail format:**
```
GUARDRAIL: <short pattern label>
  Cause: <what went wrong>
  Fix: <how to avoid in future bundles>
```
Write these to the caller's progress file (or inline if standalone).

---

## Coverage check for the bundle (post-reasoner)

After the reasoner is clean, verify the bundle against its source claims:

```
get_subgraph(
    ontology_id = <ONTOLOGY_ID>,
    entity_iris = [<bundle IRIs>],
    depth       = 2
)
```

Check that every node and edge you intended to register appears in the subgraph. If anything is missing, create a follow-up bundle.

---

## Optional: SPARQL diagnostics

`sparql_query` may be used for SELECT/ASK probes (e.g., listing the types of an IRI, checking if a property link exists). It does not replace `run_reasoner` for consistency validation, and mutating SPARQL is blocked by the tool.

---

## Summary checklist for a bundle

- [ ] Concepts registered before dependent Individuals
- [ ] Object_property targets exist before their sources in the bundle
- [ ] `search_entities` / `search_relations` used before minting any new IRI
- [ ] `run_reasoner` executed after all writes; inner fix loop applied if needed
- [ ] `get_subgraph` confirms all intended nodes and edges are present
- [ ] Guardrails logged for any stuck violations
- [ ] Caller's progress file (e.g. `kgcon-progress.md`) updated with new IRIs and reasoner outcome
