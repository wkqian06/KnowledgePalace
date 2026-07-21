# Concept Registry (fixture)

## domain
| Slug | Parents | Status | Aliases | Definition | Notes |
|---|---|---|---|---|---|
| alpha-domain | - | canonical | - | Alpha fixture domain root. | - |
| beta-domain | - | canonical | - | Beta fixture domain root. | - |

## task
| Slug | Parents | Status | Aliases | Definition | Notes |
|---|---|---|---|---|---|
| concept-echo | alpha-domain | canonical | echo cancel | Echo task. | - |
| concept-foxtrot | beta-domain | canonical | - | Foxtrot task. | - |
| concept-gamma | alpha-domain, beta-domain | canonical | - | Multi-parent bridge task. | - |

## method
| Slug | Parents | Status | Aliases | Definition | Notes |
|---|---|---|---|---|---|
| method-delta | concept-echo | canonical | - | Delta method. | - |

## pattern
| Slug | Parents | Status | Aliases | Definition | Notes |
|---|---|---|---|---|---|
| concept-shared-pattern | - | canonical | - | Shared cross-domain pattern (fixture). | - |
