# Draft, revise or polish scholarly text

`write <project|materials> [section]` creates prose, develops an outline or makes
substantive revisions. `draft intro <topic>` invokes this same workflow for an
introduction. `polish <text|file|project>` improves an existing passage while
preserving the intended scientific case. Neither requires a collection or a new
project when the needed material is already supplied.

## Shared preparation

The author supplies three things, each of which may be brief: the framing of the
article (what it argues), its motivation (why the work is needed) and its design
(what was done). With these the workflow drafts in one pass. Read them from the
request and the project materials first; ask, once and together, only for
whichever is missing.

Complete or reuse [manuscript analysis](manuscript-analysis.md) before either task.
Select relevant literature and actual user results. Adopted outside papers go
through [ingest](ingest.md). Drafting uses the selected evidence and analysis;
new evidence needs return to the reading flow rather than untracked citations.

Project mode reads its brief, analysis, materials, sections and chosen style.
Direct mode reads the supplied document and surrounding context without creating
a project or requiring `.palace.toml`. Use generic scientific prose unless a
venue/style is specified. Keep numbers, methods, conditions and source identities
faithful. Missing Results material permits a marked outline or planned analysis,
never completed results. Availability of material alone does not prove its claims.

## Plan

The text is written from the argument graph in the manuscript analysis. The graph
comes before the text and guides it: short nodes joined by labelled links, one
node per paragraph at the section level and a chain from opening to landing
inside each paragraph. It is kept light and is never the article in other words.
Build it from the author's framing, motivation and design. Do not stop to have
it approved: it is delivered with the text.

Read the graph before writing. Every link has to hold between its two nodes, and
each chain has to run unbroken from its opening to its landing.

When the author supplies a new revision of the section, rebuild the argument
graph from its paragraphs before any further writing (see
[manuscript analysis](manuscript-analysis.md)); the text is not assumed to be
written against an old graph.

What a section argues, and what it leaves to another section, is decided for
each manuscript and recorded in its analysis. Such a decision never becomes a
writing rule, and a correction from the author is recorded as one or the other.

## Write

Follow the graph. Allocate methods/supporting details according to their role,
and calibrate conclusions to the actual observations and design. Use ordinary
citations from verified sources. When the text needs a node or a link the graph
lacks, change the graph first and the text after it.

## Writing rules

These rules bind write and polish, and the review reports against them by
number. "Generally" marks the usual case, which a manuscript may leave for a
reason its analysis states.

Section

1. An Introduction generally runs general, particular, general: an opening
   paragraph on the broad topic, middle paragraphs that advance or stand
   parallel, and a closing part of one or two paragraphs on this paper's own
   work, which distils the scientific question and says which questions the
   paper answers. Whether the closing part also states what was found, and
   whether it lays out the structure of the article, follows the selected
   journal style: some venues expect the findings stated there, others a
   roadmap of the sections. With no style selected, it gives the structure of
   the article and leaves the findings to the Results.
2. Paragraphs stand in a planned relation. An advancing paragraph starts from
   the landing of the one before; parallel paragraphs generally need not.

Paragraph

3. One point per paragraph, which a reader can state after one reading.
4. The opening and the landing are fixed first. The landing closes the paragraph
   with the conclusion the reader takes away, and the section decides what that
   conclusion is: in an Introduction, generally the gap or difficulty reached;
   in Results, the finding the paragraph establishes; in a Discussion, the
   consequence or limit it draws. A Methods paragraph that describes a
   procedure may end on its last step. A paragraph never trails off on an
   example.
5. A paragraph generally opens on its topic, stated positively: what its
   subject is or offers.

Between sentences

6. Adjacent sentences connect, and the reader supplies no step. The later
   sentence picks up something the earlier one stated. Each item of a parallel
   series (an enumeration, or cases treated alike) picks up the sentence that
   introduced the series, and the items stand parallel to one another. A
   paragraph does not return to a subject it has left. A connective never
   stands in for a missing step. A new subject never enters in a trailing
   clause.
7. The argument graph is laid out before the text, and the text follows it.

Sentences

8. A sentence reads in one pass, with its subject near the front and no long
   phrase before it.
9. The sentence fits the thought. Two clauses share a sentence when the
   relation between them (a cause, a contrast, a condition) is what the sentence
   says. Clause stacking fails, and so does a run of one-clause sentences whose
   relations are left unstated.

Literature

10. Sources are never piled: no semicolons, comma series or numbered runs that
    string together the findings of several studies.
11. Sources that together support one statement are cited together at that
    statement, which goes no higher than EVIDENCE.md allows for them.
12. Where a general statement needs particulars, it is illustrated briefly with
    the one or two strongest sources. Often the finding alone is enough; the
    setting is named only where the finding would otherwise read as wider than
    the study.
13. A relevant source is not left out because it fails to support the
    statement. A disagreement between sources is itself an open question and is
    named as one; its full discussion belongs in the Discussion.

Wording

14. Claims supply the evidence, never the wording. Findings are restated in the
    manuscript's own words; the verbatim quote belongs to the card. Two short
    quotations are allowed, marked and cited: a term coined or borrowed by a
    source, in quotation marks on first use, and a verdict of a named source
    that the text quotes in order to answer it.
15. The text reads as continuous prose, never as scaffolding. It does not pose a
    question and then announce its answer ("the first question is …" followed
    by "we answer it with …"), announce its own moves instead of making them
    ("two questions follow", "the argument proceeds in three steps") or report
    through people ("the authors claim", "the authors suggest"). A count of the
    things discussed that introduces an enumeration delivered at once in the
    same paragraph ("three conditions must hold: …", "four results stand out.
    First, …") belongs to that enumeration and is allowed. The subject of a
    sentence is the thing studied or the work done, and the citation carries
    the attribution. An abstract or compact
    phrase ("what X contributes", "the effect of Y") is used only when it is
    common knowledge in the field, is defined in the text, or picks up
    something already stated. Otherwise the sentence names the specific thing
    compared, measured or claimed. Fluency never buys vagueness.

Style

16. Where a journal style or a language style is specified, the text follows it
    throughout, in every paragraph and in its apparatus (headings, citations,
    notation, units), not only at the start. Where a profile's rule conflicts
    with a rule above or with a standard the author has stated, the author's
    prevails and the analysis records the conflict.

## Polish

Use the analysis to identify whether the issue is expression, paragraph logic or
the scientific claim. Revise only the requested passage by default. A scientific
change is explained as such; a substantial restructuring belongs to write and
requires the user's scope to include it. Keep unrequested passages unchanged.
The writing rules apply to the revised passage, and rules 1 and 2 only as far as
the requested scope reaches.

Compare the revised passage against the original for numbers, units, terms, citations,
claim strength and boundary conditions. This is a content review, not a token-count
or field-presence test. Return the text and a short explanation of consequential
changes. If the source has a scientific problem, identify it rather than polishing
it into apparent certainty.

## Review and save

Use one focused review and address actual findings; at most two automatic
revisions for a section. The review is palace-reviewer, in a context separate
from the drafting, given the absolute paths of the draft, for a polish the text
before it, the paper cards of the sources the draft cites, this workflow, the
manuscript analysis and the section's argument graph, neighbouring sections, the
brief and any selected style profile. Without a separate context, review here
under `knowledge_palace/agents/palace-reviewer.md`, which gives the order and the
severity rules, and treat it as a same-session review. The review is not a
Python state machine and does not need a fixed concern count.
Text rewritten after the review is checked again against the rules before it is
delivered, by reading what each sentence says; a scan for forbidden strings or
punctuation is not that check.

Deliver the text itself, preceded by its argument graph; in a project the graph
is the page `outline/graph-<section>.html`, which the author can open and edit. The review and the
revisions happen before delivery and are not part of what is delivered: no draft
stage is handed over and no account of the process is attached. State only what
the author has to decide or supply. An author who is not satisfied changes a
node or a link, or supplies a new chain; the graph is updated first and the
affected paragraphs are rewritten from it, while the others keep their text.

Use `workspace.revision.save_revision` for saved project sections and preserve earlier
revisions. Direct tasks return prose or write to the user's chosen output; never
overwrite the source manuscript by default. Keep analysis notes separate from prose.
