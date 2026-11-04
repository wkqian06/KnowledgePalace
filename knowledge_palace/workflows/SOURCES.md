# Workflow design sources

The workflows are Palace-specific guidance sharing its existing source, card and
project formats. They are independently written from the user's requirements and
the following design references, reviewed on 2026-09-13. No upstream scripts or
runtime dependencies are bundled.

- [nature-paper-card](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-paper-card): analysis-to-claim evidence, source coverage and author/analysis distinction.
- [nature-reader](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-reader): structural source locations and reading depth.
- [nature-writing workflow](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-writing/static/core/workflow.md): argument before prose and targeted revision.
- [nature-polishing](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-polishing) and [terminology ledger](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-shared/core/terminology-ledger.md): intent-preserving edits and consistent manuscript terminology.
- [domain review guidance](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-reviewer/references/domain-specific-review-gates.md): evidence-dependent sampling, mechanism and validation questions.
- [research idea guidance](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-paper-card/references/research-idea-gates.md): discriminating comparisons and falsifiable research extensions.
- [papergraph](https://github.com/wangyuer1-lang/papergraph) (reviewed 2026-10-05): a manuscript as propositions and the relations between them, with evidence attached to the proposition. The argument-graph page in `workspace/argument_graph.py` takes its design from papergraph's canvas (propositions as points, relations as arrows whose head shows the relation, paragraphs as boxes, drag-to-connect, arrange inside a box) and is written independently; no papergraph code or file format is used.
- [review-agent](https://github.com/Combjellyshen/review-agent) (reviewed 2026-10-05): one take-away sentence per paragraph, evidence a paragraph must carry versus evidence merely available, and stated links between paragraphs.
