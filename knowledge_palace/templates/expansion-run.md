---
run: <run-id>                       # caller-assigned, stable
scope: <domain, topic, paper, or gap the decisions are judged against>
seeds: [<work-slugs or explicit user roots>]
depth: <1|2>                        # external citation hops, never >2
max_new: <n ≤ 50>                   # budget = unique verified non-Vault candidates
provider: <metadata provider name>
started: <YYYY-MM-DD>
stop_reason: <budget_reached|frontier_exhausted|user_stop>
---

# expansion-run <run-id>

<!-- Compact by contract: stable identities, occurrences,
     decisions, vault hits — never full candidate metadata, abstracts, or
     provider dumps. Written to the Vault ONLY through the packaged
     confirmation. Scope-specific rejections never become global. -->

## Candidates (stable identities)

| Key | Title | Year | Verified | Decision (<scope>) | Reason |
|---|---|---|---|---|---|

## Discovery occurrences

| Candidate | Via | Direction | Depth |
|---|---|---|---|

## Vault hits

| Work | Via | Direction | Depth |
|---|---|---|---|
