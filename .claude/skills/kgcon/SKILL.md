---
name: kgcon
description: Knowledge Graph Construction — extract entities and relationships from documents (PDF, Markdown, plain text) or user input, then register them into a Usagi ontology. Handles both Concepts (classes) and Individuals (instances).
argument-hint: [file path or text description]
---

# Knowledge Graph Construction (kgcon)

You are a knowledge graph construction specialist.
Your task is to extract ontology entities and relationships from a given source and register them using Usagi MCP tools.

---

## Step 1 — Identify the Input Source

Use `$ARGUMENTS` as the input if provided.

Handle each input type as follows:
- **File path** (`.pdf`, `.md`, `.txt`, etc.): Read the file content with the Read tool
- **URL**: Fetch the content
- **Plain text / sentence**: Use it directly as the analysis target
- **No argument**: Ask the user: "Please provide a document or content to analyze."

---

## Step 2 — Select the Target Ontology

```
list_ontologies()
```

Present the results to the user and ask them to choose which ontology to add entities to.

Example output:
```
Available ontologies:
1. JC3IEDM (https://infiniq.co.kr/jc3iedm/) — Military operations ontology
2. ...

Which ontology would you like to add entities to?
```

Store the selected ontology IRI as `ONTOLOGY_ID`.

---

## Step 3 — Understand the Ontology Structure

Before extracting entities, get familiar with the existing ontology:

```
get_ontology_summary(ONTOLOGY_ID)
```

Note the key Concept classes and Properties available for mapping during extraction.

---

## Step 4 — Extract Entities

Analyze the input source and extract the following two types of entities.

### Extraction Criteria

**Concept (class/category):**
- A new kind or category not yet present in the ontology
- An abstract classification that multiple Individuals can belong to
- Examples: a new unit type, a new equipment category

**Individual (specific instance):**
- A concrete, named entity
- Dates, locations, persons, units, equipment with unique identity
- Examples: "3rd Marine Regiment", "Operation Iron Wing", "Colonel John Kim"

### Language Rule

**Entity labels and literal values must follow the language of the source document.**
- Korean source → Korean labels (e.g., `label="제3해병연대"`)
- English source → English labels (e.g., `label="3rd Marine Regiment"`)
- IRIs must always be ASCII regardless of source language

### Present Extraction Results

After extracting, show the following table to the user and wait for approval:

```
## Extracted Entities

### Concepts (new classes to add)
| Label | Proposed IRI | Parent Class | Evidence |
|-------|-------------|--------------|----------|
| ...   | ...         | ...          | ...      |

### Individuals (new instances to add)
| Label | Proposed IRI | Type (Concept) | Properties | Relationships |
|-------|-------------|----------------|------------|---------------|
| ...   | ...         | ...            | ...        | ...           |

Total: X Concepts, Y Individuals to be added.
Shall I proceed? (Let me know if you want to modify anything.)
```

Wait for user confirmation before proceeding to Step 5.

---

## Step 5 — Register Entities

Follow the procedure in [add-entity.md](add-entity.md) to register each entity.

### Registration Order (important)

1. **Concepts first** — must exist before Individuals can reference them in `types`
2. **Independent Individuals** — those with no `object_properties` dependencies
3. **Related Individuals** — those linked via `object_properties` go last

### Per-Entity Steps

- Before adding: run `search_entities(..., use_vector=true)` to check for duplicates or near-matches
- After adding: validate with `run_reasoner`

### Report Progress

Report progress in real time:
```
✓ [1/5] Concept "SpecialForces" added
✓ [2/5] Individual "707th Special Mission Battalion" added
⚠ [3/5] Individual "Colonel Hong" — already exists, skipped
...
```

---

## Step 6 — Final Report

Once all registrations are complete, provide a summary:

```
## kgcon Complete

- Input source: <file name or text summary>
- Target ontology: <ONTOLOGY_ID>

### Results
| Type       | Attempted | Succeeded | Skipped | Failed |
|------------|-----------|-----------|---------|--------|
| Concept    | X         | X         | X       | X      |
| Individual | X         | X         | X       | X      |

### Added Entities
- **Concepts**: <IRI list>
- **Individuals**: <IRI list>

### Skipped / Failed
- <IRI>: <reason>
```
