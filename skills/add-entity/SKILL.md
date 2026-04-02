---
name: add-entity
description: Add a single entity (Concept or Individual) to an ontology. Also used as a sub-procedure by the kgcon skill.
argument-hint: [label or description of the entity]
---

# Add Entity

Add a single entity to an ontology.
Use `$ARGUMENTS` as the description of the entity to add, if provided.

---

## Step 1 — Determine the Target Ontology

Check in the following order:

1. **Ontology specified in `$ARGUMENTS`** (e.g., `/add-entity ontology=https://... "label"`) → use it directly
2. **Ontology already established in the current context** (e.g., set by a parent skill like `kgcon`) → use it directly
3. **Neither** → ask the user:

   ```
   list_ontologies()
   ```

   Show the list and ask: "Which ontology would you like to add the entity to?"

Store the selected ontology IRI as `ONTOLOGY_ID`.

---

## Step 2 — Add the Entity

Follow the procedure defined in [add-entity.md](../kgcon/add-entity.md):

1. Determine the entity type (Concept or Individual)
2. Run `search_entities` to check for existing similar entries
3. Add using the appropriate tool:
   - Concept → `add_concept`
   - Individual → `add_individual`
4. Validate with SPARQL and report the result to the user
