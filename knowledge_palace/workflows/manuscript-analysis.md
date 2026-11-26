# Understand a manuscript before changing its prose

This is the shared analysis step for write and polish, not a public command.

Read the supplied manuscript, relevant surrounding sections and existing project
brief. Establish the research question, intended contribution, evidence and scope,
the whole-paper argument, section roles, target reader and the user's writing intent.
Identify the role of the requested passage within that argument. Separate missing
evidence from a problem of wording or organization. For a new section the
author's framing, motivation and design are the starting material; record them
as given, however brief, and build the argument graph from them.

Reuse an existing analysis if its cited passages, claims and user intent still
match. Update the affected parts after a substantive revision or changed intent;
do not repeat a full analysis solely because another polish was requested. For
a standalone paragraph, use the available title/outline/context. Ask for missing
context only when it could change what the paragraph means or should do.

Keep a compact analysis with: source document/version, research question, central
claim and evidence, the argument graph, target passage and its job, user intent,
the author's decisions and corrections, canonical terms/abbreviations/units, and
unresolved inputs. This is a working note, not a scored form. No minimum counts,
mandatory empty sections or Python validator.

## Argument graph

The argument graph guides the writing and comes before the text. It is a graph,
not prose: nodes joined by labelled links. Keep it light. Whatever the text will
say in full belongs in the text, and a graph written in finished sentences is the
article written twice.

A node is a short phrase for one thing the text will say: a claim, a fact, a
question, a gap. A link names the relation between two nodes and uses one of six
labels: `supports` (evidence or an example for a claim), `opposes` (a contrast or
a disagreement), `infers` (a consequence), `qualifies` (a limit or a condition),
`defines` (says what something is, or names it) and `associates` (continues with
a related node). Evidence is attached to a node as Claim references. A Claim that
contradicts a node is attached too, by an `opposes` link, because the manuscript
names a disagreement between sources instead of dropping one of them (rule 13).

The graph has two levels, and the writing rules in [writing.md](writing.md)
shape both.

- The section graph has one node per paragraph: its point in a few words
  (rule 3) and its role, which for an Introduction is generally opening, middle
  or closing (rule 1). Links between paragraph nodes show whether a paragraph
  advances from another or stands parallel to it (rule 2).
- Each paragraph graph runs from an opening node to a landing node, both fixed
  first (rules 4 and 5), through the nodes in between. A link may reach a node in
  another paragraph where the text picks something up from it.

In conversation, write a chain on one line, node by node, with the label on the
arrow:

    cheap sensor —qualifies→ noisy signal —infers→ needs a model [alpha-2020 C1]

Read the graph before writing: every link has to hold between its two nodes as
they stand, and the chain from opening to landing has to be complete. The
sentences that carry the links are written in the text, under rules 6 to 9. For a
polish, the graph of the target passage and its neighbours suffices.

For a saved project the graph of a section is a page of its own,
`outline/graph-<section>.html`, and nothing else is kept in it: no history, no
notes. The page is a canvas in the manner of papergraph: the paragraphs are boxes
stacked in reading order, the nodes are phrases placed inside them, and the
relations are arrows whose head shows the relation. The author drags nodes, also
from one paragraph to another, draws an arrow from a node's handle, picks the
relation on an arrow, edits phrases in place and saves; "arrange" lays a
paragraph out along its arrows. `workspace.argument_graph.render_view(graph,
written)` writes the page and `read_view(page)` reads it back; `paragraphs(graph)`
gives the graph in reading order for writing from it. The page holds two copies
of the graph: the one being edited, and `written`, the one the current text was
written from; it marks each paragraph where the two differ, and positions never
count as a difference.

The author revises the text through the graph: by editing the page, or by
handing over a new chain. Read the page, take the paragraphs to rewrite from
`changed_paragraphs(graph, written)`, rewrite only those, and write the page
again with `written` set to the graph the new text follows.

## When the author supplies a new draft

A supplied revision reverses the order: the graph is derived from the text, not
the text from the graph. Read the latest revision, split it into paragraphs, and
for each paragraph state its point, role, opening and landing, the node chain and
links, the citations it already carries, and whether it advances or stands
parallel to the previous paragraph. Write that graph to the section page and
leave the text as written from it; do not rewrite the prose in the same pass.
Report what does not hold — a missing opening or landing, a broken link, a
paragraph with no citation, or an unclear relation between paragraphs — as
findings for the review. If the draft arrives in conversation, save it as the
next revision (append-only, after confirmation) before analysing it.

## The author's decisions and corrections

Record what the author decides for this manuscript: what a section argues, what
it leaves to another section, which terms and framings are theirs. Record
corrections with their date and what they changed. Keep the two kinds apart. A
decision about this manuscript stays in its analysis and binds only this
manuscript. A correction that the author states as a general standard is a
writing rule, and it changes writing.md only when the author says so.

## Storage and terms

For a saved project, keep the analysis in `outline/manuscript-analysis.md` and
make it available with the project context. Keep it short: the manuscript's
facts, the author's starting material and decisions, what waits on the author,
terms and unresolved inputs. The graph has its own page, and a running history
of drafts and reviews does not belong in either. For a short direct-material task, keep it in conversation
unless the user requests a file. Analysis is project material, never a paper Claim.

The terminology record defines this manuscript's usage. It may draw on the domain
registry but does not rename global concepts automatically.
