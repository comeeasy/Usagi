---
name: add-entity
description: Add a bundle of ontology entities (Concepts and/or Individuals) and their relations to an ontology. Used as a sub-procedure by kgcon. Full procedure is in add-entity.md.
argument-hint: [description of the graph fragment to add]
---

# Add Entity Bundle

Add a **graph fragment (bundle)** to an ontology: one or more Concepts and/or Individuals, including all relationships (object_properties) and attributes (data_properties) between them. Uses an inner Ralph loop to guarantee the bundle is OWL-consistent before returning.

Use `$ARGUMENTS` as the description of the bundle to add, if provided.

---

## Step 1 — Determine the Target Ontology

Check in order:

1. **Ontology specified in `$ARGUMENTS`** (e.g., `ontology=https://…`) → use it directly
2. **Ontology already established in the current context** (e.g., set by a parent `kgcon` run) → use it directly
3. **Neither** → call `list_ontologies()`, show the result, ask the user to choose

Store as `ONTOLOGY_ID`.

---

## Step 2 — Plan the Bundle

Before touching MCP, list every node and edge you intend to register:

| # | Kind | IRI (proposed) | Label | Types / Parent | Relations to other nodes |
|---|------|---------------|-------|----------------|--------------------------|
| 1 | Concept | … | … | parent IRI | — |
| 2 | Individual | … | … | Concept IRI | op → node #1 |
| … | | | | | |

Dependency order: Concepts before Individuals; object_property targets before sources.

---

## Step 3 — Register (inner Ralph loop)

Follow the full procedure in [add-entity.md](../kgcon/add-entity.md):

1. **Search before creating**: `search_entities` (use_vector=true) and `search_relations` for each candidate IRI. Reuse existing nodes; do not mint duplicates. **Query must be a single keyword per call** (e.g. `"unit"`, `"isPartOf"`); never pass multi-word phrases.
2. **Register**: `add_concept` and/or `add_individual` in dependency order.
3. **Validate**: `run_reasoner(ontology_id, entity_iris=[<all bundle IRIs>])` — mandatory; do not substitute SPARQL for pass/fail.
4. **Fix loop** (inner Ralph):
   - Re-ground via `search_*`
   - Fix via `update_individual`
   - Re-run `run_reasoner`
   - Up to **5 cycles**; if stuck (gutter), document a guardrail and stop
5. **Subgraph check**: `get_subgraph(ontology_id, entity_iris=[<bundle IRIs>], depth=2)` — confirm all intended nodes and edges appear.

---

## Step 4 — Report

Return to the caller (or the user if standalone):

- IRIs created or updated (the bundle's contribution to set S)
- Reasoner outcome: `consistent=<true/false>`, violations count
- Subgraph check: pass / gap description
- Guardrails added (patterns to avoid in future bundles)
