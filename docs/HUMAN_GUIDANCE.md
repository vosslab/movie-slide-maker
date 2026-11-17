# Movie slide design

<!-- VENDORED HEADER: START -->
Record the durable guidance Neil Voss states, or approves for preservation here, in his own words:
first person or close paraphrase, one to three lines per bullet. Material he supplies as a source
may inform [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) once it is settled, and an entry of uncertain
origin belongs there too. Rules: [REPO_STYLE.md](REPO_STYLE.md).
[PROPAGATED HEADER - ENTRIES BELOW ARE YOURS]
<!-- VENDORED HEADER: END -->

- Make the most useful slide possible from the information available. Missing metadata changes
  the slide's content and layout; it does not impose a completeness threshold.
- Keep usable facts independently. A missing rating, vote count, review, or descriptive
  field must not discard other information or prevent a slide.
- Require a poster for generated movie slides. Try alternate TMDB posters when the primary image
  is missing or fails; stop and report the failure if no usable poster can be retrieved.
- Use the smallest coherent implementation; add complexity only for demonstrated needs.
- Ask for clarification when the intended movie is ambiguous. Omit information belonging to a
  different movie and report source problems in the console.
- Display the original language only when known and non-English, using its English name.
  Do not list additional spoken languages or infer subtitle or dubbing availability.
- Use Atkinson Hyperlegible Next for movie-slide text, with a bold title.
- Welcome non-coders in the README and show uses beyond teaching, including film clubs,
  presentations, and movie nights. Lead with the benefit; keep recent changes in the changelog.
- Show README slide examples as compact previews linked to full-size WebP images encoded at
  quality 90 (`cwebp -q 90`).
- Keep slides editable and retain the lecture page size of 28 by 17.5 cm.
- Include available parental guidance after the movie summary. Keep Common Sense Media and IMDb
  Parents' Guide ratings separate, use editable native tables, and preserve their distinct scales.
- Present a brief Common Sense Media overview and selected non-spoiler IMDb examples. If a source
  is unavailable, identify that gap in the deck rather than implying that no content warning exists.
- Add the resolved TMDB movie URL as a small clickable footer on each original movie summary slide.
