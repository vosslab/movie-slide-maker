# Design decisions

<!-- VENDORED HEADER: START -->
Record each durable decision about how this code and repository are shaped, once it is settled, with
the reasoning a later reader needs. Guidance Neil Voss states belongs in
[HUMAN_GUIDANCE.md](HUMAN_GUIDANCE.md), dated history in `docs/CHANGELOG.md`, open discussion in
`docs/active_plans/decisions/`. [PROPAGATED HEADER - ENTRIES BELOW ARE YOURS]
<!-- VENDORED HEADER: END -->

Write each decision as a level-three heading with these four fields. `Owner` names the
authoritative code or contract document, rather than a person.

```markdown
### <decision title>

**Decision.** <the durable direction>

**Why.** <the reason it was chosen>

**Consequence.** <the constraint a future change preserves>

**Owner.** <the authoritative code or contract doc>
```

### Adaptive rating rows

**Decision.** Prefer one rating per row when the full slide fits at a readable text size.
Compact ratings when the plot, review summary, and details make space tight, pairing RT critics
(Tomatometer) and audience (Popcornmeter) before combining other ratings. Keep provider labels
clear and each rating item together.

**Why.** Separate rows support reading; compaction preserves room for the other movie information.

**Consequence.** Choose rating rows using the whole slide content budget.

**Owner.** `slide_maker/rating_layout.py` and `slide_maker/slide_builder.py`.
