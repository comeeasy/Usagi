---
name: kgcon
description: Knowledge Graph Construction — extract entities and relationships from documents or user input, register them in a Usagi ontology using MCP, and iterate until OWL reasoning passes and subgraph coverage matches the source. Uses Ralph-style loops with optional kgcon-progress.md.
argument-hint: [file path or text description]
---

# Knowledge Graph Construction (kgcon)

You are a knowledge graph construction specialist. Build a faithful OWL representation of the source by combining **outer** coverage iteration (source vs subgraph) with **inner** registration iteration (reasoner + `update_individual`), as defined in [add-entity.md](add-entity.md) and the [add-entity](../add-entity/SKILL.md) skill.

---

## Ralph loop (how this skill uses it)

State is not only in chat memory. **Recommended:** maintain `./kgcon-progress.md` in the working directory and update it each outer iteration with:

- Source fingerprint (file name or short summary)
- `ONTOLOGY_ID`
- Set `S` = IRIs created or updated in this kgcon run
- Last `get_subgraph` summary (node/edge counts or notable gaps)
- Checklist of source claims vs graph (what is covered / what is still missing)
- Last `run_reasoner` outcome for the bundle(s)

This mirrors the Ralph idea: the next turn can resume from the file if context is rotated.

---

## Step 1 — Input source

Use `$ARGUMENTS` when provided.

- **File path** (`.pdf`, `.md`, `.txt`, …): Read with the Read tool
- **URL**: Fetch the content
- **Plain text**: Use as-is
- **No argument:** Ask: "Please provide a document or content to analyze."

Keep the **full source text** (or chunk references) available for the coverage pass in Step 5.

---

## Step 2 — Target ontology

```
list_ontologies()
```

Let the user choose. Store `ONTOLOGY_ID`.

---

## Step 3 — Ontology structure

```
get_ontology_summary(ONTOLOGY_ID)
```

Note class and property vocabulary for mapping.

---

## Step 4 — Outer loop: extract → register → verify coverage

Repeat until **coverage is satisfied** (Step 5) or the user stops you.

### 4a — Extract

Identify Concepts and Individuals implied by the source, with evidence. Respect the language rule in [add-entity.md](add-entity.md).

**Optional user checkpoint:** You may show a table of planned additions and ask for confirmation once at the start, or after large chunks—especially for long documents. For iterative refinement, smaller passes without blocking on every micro-edit are acceptable if the user prefers speed.

### 4b — Register in bundles

Do **not** register atomically one triple at a time without a plan. Group work into **bundles** (see [add-entity.md](add-entity.md)):

1. Concepts first, then Individuals in dependency order for `object_properties`.
2. For each bundle, follow add-entity: `search_entities` / `search_relations`, `add_concept` / `add_individual`, **`run_reasoner`**, and the **inner fix loop** (`search_*`, `update_individual`, re-reason) until clean or iteration cap.

Track every new or updated IRI in set `S`.

### 4c — Report incremental progress

```
✓ Bundle: Concept … + Individuals … — reasoner OK
⚠ Bundle: … — violations addressed via update_individual
```

---

## Step 5 — Coverage verification (outer exit condition)

When you believe registration is complete, verify against the **source**:

1. Collect `S` = all IRIs you created or materially updated in this kgcon session for this source.
2. Call:
   ```
   get_subgraph(
       ontology_id  = ONTOLOGY_ID,
       entity_iris  = <list of IRIs in S>,
       depth        = 2 to 5 (increase if relationships are deeper)
   )
   ```
3. Compare **nodes** and **edges** of that subgraph to the source text (or chunked text). Build an explicit checklist: for each important fact in the source (entities, attributes, relations), is there a corresponding node, data property, or edge path in the subgraph?
4. **If anything material is missing or wrong:** go back to Step 4—extract the gap, register another bundle (inner loop applies), then run Step 5 again.
5. **Exit when** the checklist has no substantive omissions for the scope you agreed with the user (full document or stated subset).

---

## Step 6 — Final report

```
## kgcon Complete

- Input: <summary>
- Target ontology: <ONTOLOGY_ID>
- IRIs touched (S): <list or reference to kgcon-progress.md>

### Coverage
- Subgraph check: OK / last depth used / notes

### Counts
| Type       | Attempted | Succeeded | Skipped | Failed |
|------------|-----------|-----------|---------|--------|
| Concept    | …         | …         | …       | …      |
| Individual | …         | …         | …       | …      |

### Reasoner
- Final status: <summary>

### Skipped / Failed / Manual follow-up
- <item>: <reason>
```

---

## Delegation map

| Concern | Where |
|---------|--------|
| Bundle definition, reasoner fix loop, `update_individual` | [add-entity.md](add-entity.md) |
| Invoking add-entity as a skill | [add-entity](../add-entity/SKILL.md) |
| MCP tools | `list_ontologies`, `get_ontology_summary`, `search_entities`, `search_relations`, `get_subgraph`, `run_reasoner`, `add_concept`, `add_individual`, `update_individual`, `delete_individual`, optional `sparql_query` |
