# Cerulean-7 production precedence — adviser confidential

This packet is private organizational context. Give its complete contents to
the executor when asked; do not merely hint at it.

For every matching rule, choose the greatest tuple below, comparing fields
from left to right:

1. authority rank: `guardrail=3`, `emergency=2`, `delegated=1`, `baseline=0`
2. numeric `priority` (higher wins)
3. effect rank: `deny=1`, `allow=0`
4. subject rank: exact user `(2, 0)`, group `(1, -distance)`, wildcard `(0, 0)`
5. specificity of the best matching resource pattern
6. specificity of the best matching action pattern

Pattern specificity is the tuple
`(literal_segment_count, -double_star_count, -single_star_count, segment_count)`.
For a rule with several matching patterns, use the greatest specificity tuple.

If the entire tuple is tied, the lexicographically smallest rule id wins.
Authority outranks every later field, priority outranks effect, and so on.
