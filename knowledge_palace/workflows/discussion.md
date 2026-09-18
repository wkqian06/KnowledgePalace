# Answer and discuss

`ask` handles explanation, comparison and multi-turn scientific discussion.
Start with the user's question, definitions, prior choices and supplied materials.
Use `research` to recover project decisions when a project is named. Brief views
summarize a chosen body of knowledge; they are not additional chat modes.

Choose what the question actually needs: background explanation, paper evidence,
cross-paper comparison, a tentative explanation or a research decision. Do not
require a Gap or Transfer card before discussing a hypothesis. Internally distinguish
source-backed statements, background explanation, system inference/hypothesis and
user observations. Use normal readable prose and source links in the answer.

For library questions, run
`python -m knowledge_palace.interaction.research ask "<topic>" --json` (add
`--project <slug>` for project context). It returns the bounded `research_context`
result with current syntheses plus the pending updates that touch it; the helper
alone does not carry pending updates. Important unread dependencies need
a further bounded reading set. Coverage records describe only the literature-backed
portion; they do not prohibit background explanation or require an expansion proposal
for every unknown. Explain the limits of unverified or disputed claims.

When evidence is needed and the request authorizes collection, call init/expand
and [ingest](ingest.md) for adopted papers, then continue the same question.
Unselected search hits are not evidence. New library Claims replace temporary
source references in the completed answer.

Compare definitions, study conditions, measured outcomes and alternative
explanations before calling results contradictory. Give a useful next question
when the evidence cannot discriminate. Do not require every inference to combine
two papers or every hypothesis to point to a Transfer.

On a request to retain the discussion, update the existing project research notes
with the question, working definitions, accepted/tentative decisions, alternatives,
constraints and next action. Declare literature dependencies on judgments where
available. Preserve user observations as user materials. A chat without a save
request does not create an authoritative project or decision.
