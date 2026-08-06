# UI quality loop

Run the automated checker with:

```bash
npm run ui:check
```

It audits every screen for missing image alt text, unlabeled controls, implicit form-button submits, missing `:focus-visible` rules, and horizontal overflow at a 375px viewport. Placeholder links are printed as advisory warnings so unfinished product destinations remain visible to reviewers.

## Prioritized enhancement backlog

The independent reviewer passes recommended these improvements, ordered by user impact:

1. Add a compact mobile navigation drawer and convert the leaderboard to a mobile-friendly card list.
2. Add skeleton, empty, and retry states to query-backed screens instead of rendering blank sections while data loads.
3. Add a small toast/feedback layer for saved quotes, check-ins, posts, and room actions.
4. Replace emoji-only mood/game affordances with visible text plus consistent iconography where the action matters.
5. Add opt-in streak celebrations and subtle entrance transitions while respecting `prefers-reduced-motion`.
6. Replace remaining placeholder links with real privacy, terms, support, and “view all” destinations.

The current pass already adds hover/active transitions, disabled affordances, reduced-motion handling, and labels for the Daily Check-In text fields. The checker is intentionally independent of the reviewer suggestions so it can catch regressions on future screen changes.
