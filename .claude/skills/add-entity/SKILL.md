---
name: add-entity
description: Add one or more ontology entities (Concepts and/or Individuals) and their relations to an ontology. Used as a sub-procedure by the kgcon skill; full procedure is in add-entity.md.
argument-hint: [label or description of the graph fragment to add]
---

# Add Entity

Add a **graph fragment (bundle)** to an ontology: one or more Concepts and/or Individuals, including relationships expressed via `object_properties` and property IRIs from `search_relations`.

Use `$ARGUMENTS` as the description of what to add, if provided.

---

## Step 1 — Determine the Target Ontology

Check in the following order:

1. **Ontology specified in `$ARGUMENTS`** (e.g., `/add-entity ontology=https://... "…"`) → use it directly
2. **Ontology already established in the current context** (e.g., set by a parent skill like `kgcon`) → use it directly
3. **Neither** → ask the user:

   ```
   list_ontologies()
   ```

   Show the list and ask: "Which ontology would you like to add to?"

Store the selected ontology IRI as `ONTOLOGY_ID`.

---

## Step 2 — Add the Bundle

Follow the full procedure in [add-entity.md](../kgcon/add-entity.md):

1. Plan the bundle (ordering, dependencies, reuse vs new IRIs).
2. For each node and relationship, use `search_entities` and `search_relations` (`use_vector=true` for entity search).
3. Call `add_concept` and/or `add_individual` in dependency order.
4. **Validate with `run_reasoner`** on all IRIs in the bundle — this is mandatory; do not substitute SPARQL for pass/fail.
5. If the reasoner reports inconsistency or violations, run the **fix loop** in add-entity.md (`search_*`, `update_individual`, re-run reasoner) until resolved or you must stop and report.

Optional: use `sparql_query` (SELECT/ASK only) for auxiliary checks; main validation remains the OWL reasoner.

Report outcomes (added IRIs, reasoner status, any remaining issues) to the user.
