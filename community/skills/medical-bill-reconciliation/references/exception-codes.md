# Exception codes

| Code | Meaning | Usual next step |
|---|---|---|
| OVERBILLED | Statement amount due is higher than the matched EOB patient responsibility | Ask the provider to adjust to the EOB; request an itemized bill |
| BILL_BELOW_EOB | Amount due is lower than EOB responsibility | Usually a prior payment; confirm, no action |
| NO_EOB | Bill has no matching EOB and the statement is at least `--no-eob-days` old | Check the claim was filed, and filed to the right plan |
| NO_EOB_PENDING | No EOB yet, statement is recent | Wait; don't pay early unless a payment plan requires it |
| CLAIM_ID_NOT_ON_EOB | The statement prints a claim number that no loaded EOB has | Check it was filed to the right plan, or load the missing EOB. The bill may still match by date and provider |
| BILLED_MISMATCH | Gross charge on the statement differs from the EOB's billed amount | Possible extra charge not sent to insurance; ask for itemization |
| DUPLICATE_CLAIM | Same service processed under two claim numbers. The second claim is excluded from matching and totals | Ask the insurer whether one should be voided |
| DUPLICATE_EOB_LINE | The same claim line was loaded from two different documents (corrected/reissued EOB or a re-download). The later copy is excluded | Keep one copy. For a corrected EOB, replace the original's rows instead of adding to them |
| REPEATED_EOB_LINE | Two identical lines in one EOB document. Both are kept | Confirm two units were really billed; otherwise delete the extra row |
| DUPLICATE_CHARGE | Identical line appears twice on one statement | Ask the provider to remove the duplicate |
| OLDER_STATEMENT | An older statement for the same account; only the latest is reconciled | None; listed so you know it was ignored |
| AMBIGUOUS_MATCH | Statement lines overlap the same EOB lines in different combinations, so the split can't be determined | Compare by hand; adding CPT codes to both sides usually resolves it |
| EOB_MATH | allowed exceeds billed, or allowed != plan paid + patient responsibility | Usually an extraction error; reread the page. If printed that way, ask the insurer |
| DEDUCTIBLE_EXCEEDED | Deductible applied across the year exceeds the plan deductible | Compare with the insurer's accumulator page; ask for reprocessing |
| OOP_MAX_EXCEEDED | Patient responsibility across the year exceeds the out-of-pocket max | Compare with the insurer's accumulator page; ask whether payments beyond the max are refundable |

## Matching order

1. Claim number, when the statement prints one, narrowed by CPT when both sides have it.
2. Otherwise patient + date of service + normalized provider (+ CPT when both have it). When several EOB lines match, lines with the same billed amount are preferred.

CPT codes are compared on the 5-character base code, so modifiers and unit suffixes (`99213-25`, `99213 x2`) still match.

Statement lines on the same account that resolve to the same set of EOB lines are compared **together**. A statement with one row per procedure therefore reconciles correctly against a claim whose EOB rows have no CPT codes, and the other way around. If those groups overlap, the result is `AMBIGUOUS_MATCH`, never a guess.

Provider names are normalized by lowercasing, collapsing dotted initials (`P.A.`, `M.D.`, `L.L.C.`), stripping punctuation, and dropping words like LLC, PA, PC, MD, and Group. The same normalization applies to both columns of `providers.csv`, so a row like `Bayside Ortho,"Bayside Orthopedic Specialists, P.A."` works as written.

Patients are grouped case-insensitively, so `Alex` and `alex` share one accumulator.

## Known limits

- Accumulators are summed from the EOB lines you loaded, after duplicates are removed. If you load an incomplete year, the totals are low. The insurer's own accumulator page is the reference.
- Network status, family vs individual limits, and copays that don't count toward the deductible vary by plan. The script only compares against the numbers you pass in.
- Adjustments, write-offs, and payments are not modeled on the bill side. Load the latest statement's amount due; older statements for the same account are skipped automatically.
- Without `--as-of`, the report date is today, so `NO_EOB` and `NO_EOB_PENDING` can change from one day to the next. Pass `--as-of` for repeatable output.
