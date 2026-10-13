# Exception codes

| Code | Meaning | Usual next step |
|---|---|---|
| OVERBILLED | Statement amount due is higher than the matched EOB patient responsibility | Ask the provider to adjust to the EOB; request itemized bill |
| BILL_BELOW_EOB | Amount due is lower than EOB responsibility | Usually a prior payment; confirm, no action |
| NO_EOB | Bill has no matching EOB and the statement is older than `--no-eob-days` | Check the claim was filed, and filed to the right plan |
| NO_EOB_PENDING | No EOB yet, statement is recent | Wait; do not pay early unless a payment plan requires it |
| BILLED_MISMATCH | Gross charge on the statement differs from the EOB's billed amount | Possible extra charge not sent to insurance; ask for itemization |
| DUPLICATE_CLAIM | Same service processed under two claim numbers | Ask insurer whether one should be voided |
| DUPLICATE_CHARGE | Identical line appears twice on one statement | Ask provider to remove the duplicate |
| EOB_MATH | allowed exceeds billed, or allowed != plan paid + patient responsibility | Usually an extraction error; reread the page. If printed that way, ask the insurer |
| DEDUCTIBLE_EXCEEDED | Deductible applied across the year exceeds the plan deductible | Compare with insurer accumulator page; ask for reprocessing |
| OOP_MAX_EXCEEDED | Patient responsibility across the year exceeds the out-of-pocket max | Same; payments beyond the max should be refunded |

## Matching order

1. Claim number, when the statement prints one. Narrowed by CPT when both sides have it.
2. Otherwise patient + date of service + normalized provider (+ CPT when both have it). When several EOB lines match, lines with the same billed amount are preferred.

Provider names are normalized by lowercasing, stripping punctuation, and dropping words like LLC, PC, MD, Group. Anything still different goes in `providers.csv` as `alias,canonical`, for example `bayside ortho,bayside orthopedic specialists`.

## Known limits

- Accumulators are summed from the EOB lines you loaded. If you load an incomplete year, the totals are low. The insurer's own accumulator page is the reference.
- Network status, family vs individual limits, and copays that don't count toward the deductible vary by plan. The script only compares against the numbers you pass in.
- Adjustments, write-offs, and payments are not modeled on the bill side. Load the current amount due only.
