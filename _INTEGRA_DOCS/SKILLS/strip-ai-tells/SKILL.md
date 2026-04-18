---
name: strip-ai-tells
description: De-AI-ify text by fixing AI formatting habits. Use when reviewing or cleaning up AI-generated text, comments, docs, commit messages, or markdown. Fixes dashes, arrows, bullet styles, over-bolding, and other AI tells.
---

## When to trigger

- User asks to "de-AI" or "clean up" AI-generated text
- Reviewing AI-written comments, docs, or markdown for formatting issues
- Any post-generation cleanup pass

## Formatting rules

These are formatting-only changes. Don't rewrite prose, change meaning, or alter tone.

### Dashes

- Replace m-dashes (`—`) with a spaced single hyphen (` - `)
- AI loves m-dashes. Humans writing plain text use ` - ` or restructure into two sentences.
- Exception: leave m-dashes alone in code comments where the author's style already uses them (check existing code first)

### Arrows

- Replace `→` and emoji arrows with `=>`
- `EC P-256 => ES256` not `EC P-256 → ES256`

### Bullets and lists

- Use `-` for unordered lists, not `*` or `•`
- Don't add trailing periods to list items unless every item is a full sentence
- Don't mix periods and no-periods in the same list

### Bold and emphasis

- Don't bold every key term on first mention
- Don't bold list item leads unless it's a definition list pattern
- Prefer backticks for code/identifiers over bold

### Headers

- Don't add unnecessary section headers for short content
- A 3-line answer doesn't need an `## Answer` header

### Sentence spacing

- One space after periods, not two

### Quotes and punctuation

- Use straight quotes (`"`, `'`), not curly/smart quotes
- Commas and periods go inside quotes (American English)

### Emoji

- Don't use emoji in technical writing
- No checkmarks, warning signs, or decorative emoji in lists or headings

### Other AI tells

- Don't start responses with "Great question!" or "Certainly!"
- Don't start bullet points with "**Word:** explanation" unless it's genuinely a definition list
- Don't pad with "Let me know if you have any questions"
- Don't use "Note:" or "Important:" callouts unless genuinely needed
- Avoid "This is because..." as a sentence opener (just state the reason)
