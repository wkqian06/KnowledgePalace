# Draft, revise or polish scholarly text

`write <project|materials> [section]` creates prose, develops an outline or makes
substantive revisions. `draft intro <topic>` invokes this same workflow for an
introduction. `polish <text|file|project>` improves an existing passage while
preserving the intended scientific case. Neither requires a collection or a new
project when the needed material is already supplied.

## Shared preparation

Complete or reuse [manuscript analysis](manuscript-analysis.md) before either task.
Select relevant literature and actual user results. Adopted outside papers go
through [ingest](ingest.md). A writer receives the selected evidence and analysis;
new evidence needs return to the reading flow rather than untracked citations.

Project mode reads its brief, analysis, materials, sections and chosen style.
Direct mode reads the supplied document and surrounding context without creating
a project or requiring `.palace.toml`. Use generic scientific prose unless a
venue/style is specified. Keep numbers, methods, conditions and source identities
faithful. Missing Results material permits a marked outline or planned analysis,
never completed results. Availability of material alone does not prove its claims.

## Write

Build the argument and paragraph roles before drafting. State the framing briefly;
ask only when a consequential premise is unresolved. Draft from evidence to claim,
allocate methods/supporting details according to their role, and calibrate conclusions
to the actual observations and design. Use ordinary citations from verified sources.

## Polish

Use the analysis to identify whether the issue is expression, paragraph logic or
the scientific claim. Revise only the requested passage by default. A scientific
change is explained as such; a substantial restructuring belongs to write and
requires the user's scope to include it. Keep unrequested passages unchanged.

Compare the revised passage against the original for numbers, units, terms, citations,
claim strength and boundary conditions. This is a content review, not a token-count
or field-presence test. Return the text and a short explanation of consequential
changes. If the source has a scientific problem, identify it rather than polishing
it into apparent certainty.

## Save

Use `workspace.revision.save_revision` for saved project sections and preserve earlier
revisions. Direct tasks return prose or write to the user's chosen output; never
overwrite the source manuscript by default. Keep analysis notes separate from prose.
Use one focused scientific/language review and address actual findings; at most two
automatic revisions for a section. The review is not a Python state machine and does
not need a fixed concern count. Report any unresolved substantive issue plainly.
