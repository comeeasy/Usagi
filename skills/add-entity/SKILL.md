---
name: add-entity
description: Add a single entity (Concept or Individual) to a Usagi ontology. Also used as a sub-procedure by the kgcon skill.
argument-hint: [label or description of the entity]
---

# Add Entity

Add a single entity to a Usagi ontology.
Use `$ARGUMENTS` as the description of the entity to add, if provided.

---

## Step 1 — Select the Target Ontology

If an ontology is already established in the current context, use it.
Otherwise:

```
list_ontologies()
```

Present the results to the user and ask them to select one.

---

## Step 2 — Add the Entity

Follow the procedure defined in [add-entity.md](../kgcon/add-entity.md):

1. Determine the entity type (Concept or Individual)
2. Run `search_entities` to check for existing similar entries
3. Add using the appropriate tool:
   - Concept → `add_concept`
   - Individual → `add_individual`
4. Validate with SPARQL and report the result to the user
