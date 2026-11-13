---
name: email-extraction
description: Distill email threads into structured decisions, action items, owners, deadlines, and open questions.
---

# Email Thread Extraction

Turn messy multi-reply email threads into crisp, chronological operational summaries without
losing attributions or subtle caveats.

## Output Structure

1. **Thread Metadata**: Subject, participants (`Name / Role` if visible), date range.
2. **Agreed Decisions**: explicit agreements with who confirmed and message date.
3. **Action Items**: table with `Owner`, `Action`, `Due Date`, `Status` (mark unowned items
   clearly as `UNASSIGNED`).
4. **Open Questions & Blockers**: unresolved disagreements, waiting approvals, or conflicting
   constraints quoted accurately.
5. **Exact Commitments & Numbers**: preserve prices, dates, versions, URLs, and SLAs verbatim;
   never infer deadlines not stated in the thread.
