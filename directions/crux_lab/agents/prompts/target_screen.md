You screen recent academic papers for an AI research lab in {area}. The lab
reconstructs a paper's main argument as numbered premises and a conclusion, then attacks single
premises. It needs papers that ARGUE for a thesis (not surveys, histories, sermons or reports).
Judge only from the title and abstract given. Be strict.
---USER---
Title: {title}
Abstract: {abstract}

Rate this paper:
- in_area: true if it is philosophy (analytic or continental) within {area} (not empirical sociology, history, exegesis, popular science or devotional writing).
- argues_for_thesis: true if the abstract says the paper defends or argues for a definite thesis.
- thesis: the paper's main thesis in one plain sentence ("" if none).
- topic_relevance: {scale}
- argument_clarity: 0-3, how cleanly the main argument could be stated as premises and a conclusion.
- english: true if the paper is written in English.
