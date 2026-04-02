# Shared Entity Addition Procedure

This document defines the core entity addition procedure shared by the `kgcon` and `add-entity` skills.

---

## Language Rule

**Entity labels and literal values must follow the language of the original input source.**
- If the source document is written in Korean → use Korean labels
- If the source document is written in English → use English labels
- IRIs must always use ASCII (kebab-case or PascalCase); never include non-ASCII characters in IRIs

---

## Determine Entity Type

Decide which type the entity belongs to before proceeding:

- **Concept (owl:Class)**: An abstract category or class that multiple individuals can belong to.
  - Examples: "ArmoredUnit", "OperationalArea", "CommandRelationship"
  - Use `add_concept`
- **Individual (owl:NamedIndividual)**: A specific, named instance of a concept.
  - Examples: a specific brigade, a specific operation, a specific person
  - Use `add_individual`

---

## Pre-Addition: Understand the Ontology

Before adding any entity, always perform these lookups:

1. **Search for similar Concepts**
   ```
   search_entities(ontology_id, query="<keyword related to the entity>", kind="concept")
   ```
   - If a matching class already exists, reuse it instead of creating a new Concept
   - Identify candidate parent classes

2. **Search for relevant Properties** (when linking relationships)
   ```
   search_relations(ontology_id, query="<relationship description keyword>")
   ```

---

## Adding a Concept

```
add_concept(
    ontology_id  = <selected ontology IRI>,
    iri          = <base_iri + PascalCase local name>,
    label        = <label in the source language>,
    super_classes = [<parent class IRI, omit if none>],
    description  = <optional: class description in source language>
)
```

**IRI rules:**
- Append a PascalCase local name to the base IRI using `/`
- Example: `https://infiniq.co.kr/jc3iedm/` + `SpecialForces`
- No spaces, non-ASCII characters, or special characters in IRIs

**Checklist:**
- [ ] Does an equivalent or highly similar Concept already exist?
- [ ] Is the parent class appropriate?
- [ ] Does the IRI follow the ontology namespace convention?

---

## Adding an Individual

```
add_individual(
    ontology_id       = <selected ontology IRI>,
    iri               = <base_iri + category/kebab-case-name>,
    label             = <human-readable name in the source language>,
    types             = [<mapped Concept IRI list>],
    data_properties   = [{"property_iri": "...", "value": "...", "datatype": "xsd:string"}],
    object_properties = [{"property_iri": "...", "target_iri": "..."}]
)
```

**IRI rules:**
- Format: `<base_iri><category>/<kebab-case-name>`
- Example: `https://infiniq.co.kr/jc3iedm/unit/3rd-armor-brigade`
- Category examples: `unit/`, `location/`, `operation/`, `person/`, `equipment/`

**Checklist:**
- [ ] At least one Concept IRI is specified in `types`
- [ ] Any Individual referenced in `object_properties` already exists (verify with `search_entities`)
- [ ] The IRI is not a duplicate

---

## Post-Addition Validation

After adding an entity, run the reasoner scoped to the newly added IRI:

```
run_reasoner(
    ontology_id  = <ontology_id>,
    entity_iris  = [<added IRI>]
)
```

Interpret the result as follows and report back to the user:

| Field | Meaning |
|-------|---------|
| `consistent: true`, `violations: []` | Entity is coherent — addition is valid |
| `consistent: false` | Ontology is now inconsistent — the addition likely contains a logical error |
| `violations: [...]` | Constraint violations found — review each violation and decide whether to fix or remove the entity |
| `inferred_axioms_count` | Number of axioms the reasoner derived from this entity — higher counts indicate richer inference |

**If violations are found**, report them clearly:
```
⚠ Violation: <violation description>
  → Suggested fix: <what to correct>
```

**If the ontology is inconsistent**, offer to remove the entity and explain which part of the definition caused the conflict.
