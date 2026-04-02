---
name: kgcon
description: Knowledge Graph Construction — extract entities and relationships from documents, register them in a Usagi ontology using MCP, and iterate via a two-level Ralph loop until OWL reasoning passes and subgraph coverage matches the source.
argument-hint: [file path or text content]
---

# Knowledge Graph Construction (kgcon)

You are a knowledge graph construction specialist. Build a faithful OWL representation of the source using a **two-level Ralph loop**:

- **Outer loop** — coverage: compare source claims to the subgraph; register what is missing
- **Inner loop** — consistency: run `run_reasoner`, fix violations, re-reason until clean

Both loops persist state to `./kgcon-progress.md` so a fresh context can resume without losing work.

---

## Ralph Loop Principles

Progress lives in **files, not chat memory**. Treat `kgcon-progress.md` as the single source of truth:

1. Write **machine-verifiable success criteria** as checkboxes before the first bundle.
2. Update `kgcon-progress.md` after every outer iteration (new IRIs, subgraph summary, checklist state, reasoner outcome).
3. If the context window fills up, a new agent instance reads `kgcon-progress.md` and continues exactly where the previous one stopped.
4. **Gutter detection**: if the same violations repeat for 3+ inner fix cycles with no progress, stop the inner loop, document the failure as a guardrail, and report to the user.
5. **Guardrails**: log failed patterns (wrong type, missing target IRI, class mismatch, …) so the same mistake is not repeated in later bundles.

---

## Step 1 — Read Source

Read the input file with the Read tool (PDF, MD, TXT, …) or use the provided plain text directly.
Keep the full source text available throughout for the coverage check in Step 5.

---

## Step 2 — Select Ontology

```
list_ontologies()
```

Show the result and let the user confirm the target. Store as `ONTOLOGY_ID`.

---

## Step 3 — Understand Ontology Structure

```
get_ontology_summary(ONTOLOGY_ID)
```

Note available classes and properties; this shapes bundle planning in Step 4.

---

## Step 4 — Outer Loop: Extract → Register → Coverage

Repeat until **coverage is satisfied** (Step 5) or the user stops.

### 4a — Initialise the progress file

On the **first** outer iteration, write `./kgcon-progress.md`:

```markdown
# kgcon Progress

## Source
<file name and one-line summary>

## Ontology
ONTOLOGY_ID: <value>

## Success Criteria (exit conditions)
- [ ] Every key entity in the source has a corresponding Individual in the graph
- [ ] Every key relationship is represented as an object_property edge
- [ ] run_reasoner reports consistent=true with no violations for all registered IRIs
- [ ] get_subgraph coverage checklist has no material omissions (all ✓)

## S — IRIs registered this session
(append as you go)

## Guardrails
(append failed patterns as you discover them)

## Iteration Log
(append one block per outer iteration)
```

On **subsequent** iterations, append to the existing file — do not overwrite prior entries.

### 4b — Extract

Scan the full source text. For each implied Concept and Individual, record:
- **Evidence**: quote or section reference
- **Proposed IRI**
- **Class** (`types`)
- **Data properties**
- **Object properties** (note target IRI; target must exist before the source is registered)

Group findings into **bundles** in dependency order: Concepts first, then Individuals, with object_property targets before sources.

**Optional checkpoint:** For long documents, show the extraction table and ask the user to confirm before registering.

### 4c — Register bundles (inner loop)

For each bundle, follow the full procedure in [add-entity.md](add-entity.md):

1. `search_entities` / `search_relations` — reuse existing IRIs; avoid duplicates
2. `add_concept` / `add_individual` in dependency order
3. `run_reasoner` — mandatory after each bundle
4. Inner fix loop: `search_*` → `update_individual` → re-reason (up to 5 cycles)
5. Log guardrails for any stuck violation

Track every new/updated IRI in the **S** section of `kgcon-progress.md`.

### 4d — Update progress file

After each bundle, append to the Iteration Log:

```markdown
### Outer iteration <N> — <bundle label>
Bundles registered: <list>
IRIs added to S: <list>
Reasoner: consistent=<true/false>, violations=<count>
Guardrails added: <list or none>
```

Report incremental status inline:
```
✓ Bundle: <Concepts + Individuals> — reasoner OK
⚠ Bundle: <…> — <N> violations fixed via update_individual
✗ Bundle: <…> — stuck after 5 inner cycles; see Guardrails
```

---

## Step 5 — Coverage Verification (outer exit condition)

When all planned bundles are registered, run the coverage check:

1. Collect `S` from `kgcon-progress.md`.
2. Call:
   ```
   get_subgraph(
       ontology_id = ONTOLOGY_ID,
       entity_iris = <S>,
       depth       = 2        # increase to 3–5 if relationships are deeper
   )
   ```
3. Build an explicit **coverage checklist** comparing the subgraph to the source text:
   - For every key entity in the source: `✓ node present` / `✗ missing`
   - For every key relationship: `✓ edge present` / `✗ missing`
   - For every key attribute (data property): `✓ present` / `✗ missing`
4. **If any `✗` items are material**: go back to Step 4 — extract the gap, register a new bundle (inner loop applies), then re-run Step 5.
5. **Exit** when the checklist has no material `✗` items.

Update `kgcon-progress.md` with the subgraph summary and checklist after each Step 5 run.

---

## Step 6 — Final Report

```
## kgcon Complete

- Input: <file name / summary>
- Ontology: <ONTOLOGY_ID>
- IRIs in S: <count> — full list in kgcon-progress.md

### Coverage Checklist
| Source claim | Graph representation | Status |
|---|---|---|
| <entity / relation / attribute> | <IRI or edge> | ✓ / ✗ |

### Counts
| Type       | Attempted | Succeeded | Skipped | Failed |
|------------|-----------|-----------|---------|--------|
| Concept    |           |           |         |        |
| Individual |           |           |         |        |

### Reasoner
Final: consistent=<true/false>, violations=<count>

### Guardrails (lessons learned this session)
- <pattern>: <why it failed and how to avoid>

### Manual follow-up
- <item>: <reason (e.g. MCP cannot update Concepts)>
```

---

## Delegation map

| Concern | Where |
|---------|-------|
| Bundle procedure, inner Ralph loop, reasoner fix | [add-entity.md](add-entity.md) |
| Invoking add-entity as a skill | [add-entity](../add-entity/SKILL.md) |
| MCP tools | `list_ontologies`, `get_ontology_summary`, `search_entities`, `search_relations`, `get_subgraph`, `run_reasoner`, `add_concept`, `add_individual`, `update_individual`, `delete_individual`, `sparql_query` |
