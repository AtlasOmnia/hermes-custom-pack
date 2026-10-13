# Exception codes

| Code | Meaning | Usual next step |
|---|---|---|
| OVERBILLED | Statement amount due is higher than the matched EOB patient responsibility | Ask the provider to adjust to the EOB; request an itemized bill |
| BILL_BELOW_EOB | Amount due is lower than EOB responsibility | Usually a prior payment; confirm, no action |
| NO_EOB | Bill has no matching EOB and the statement is at least `--no-eob-days` old | Check the claim was filed, and filed to the right plan |
| NO_EOB_PENDING | No EOB yet, statement is recent | Wait; don't pay early unless a payment plan requires it |
| CLAIM_ID_NOT_ON_EOB | The statement prints a claim number that no loaded EOB has (or that was excluded as a duplicate; the detail says which) | Check it was filed to the right plan, or load the missing EOB. The bill may still match by date and provider |
| CLAIM_ID_MISMATCH | The cited claim is on an EOB, but this line only matched a different claim by date and provider | Confirm which claim the charge belongs to before comparing amounts |
| BILLED_MISMATCH | Gross charge on the statement differs from the EOB's billed amount | Possible extra charge not sent to insurance; ask for itemization |
| DUPLICATE_CLAIM | Same service (same CPT code) processed under two claim numbers. The second claim is excluded from matching and totals | Ask the insurer whether one should be voided |
| POSSIBLE_DUPLICATE_CLAIM | Two claims share date, provider, and billed amount but have no CPT code to tell them apart. Both are kept | Check whether these are two real services or one processed twice |
| DUPLICATE_EOB_LINE | The same claim line, with the same amounts, was loaded from two documents (usually a re-download). The copy from the EOB with the latest `eob_date` is kept | Delete the extra rows |
| REVISED_EOB_LINE | The same claim line was loaded from two documents with different amounts (a corrected or reprocessed EOB). Only the latest `eob_date` is kept | Confirm the later EOB is the final one; replace the original's rows next time |
| REPEATED_EOB_LINE | Two identical lines in one EOB document. Both are kept | Confirm two units were really billed; otherwise delete the extra row |
| DUPLICATE_CHARGE | Identical line appears twice on one statement | Ask the provider to remove the duplicate |
| OLDER_STATEMENT | An older statement for the same account; only the latest is reconciled | None; listed so you know it was ignored |
| AMBIGUOUS_MATCH | Statement lines overlap the same EOB lines in different combinations, so the split can't be determined | Compare by hand. Adding CPT codes or the claim number to both sides usually resolves it; a billed-amount difference on one line can make the whole statement ambiguous |
| PARTIAL_PAYMENT_IN_GROUP | A group's totals agree, but it contains a zero or credit line that could be offsetting an overcharge on another line | Compare line by line against the EOB |
| EOB_MATH | allowed exceeds billed, or allowed != plan paid + patient responsibility | Usually an extraction error; reread the page. If printed that way, ask the insurer |
| DEDUCTIBLE_EXCEEDED | Deductible applied across the year exceeds the plan deductible | Compare with the insurer's accumulator page; ask for reprocessing |
| OOP_MAX_EXCEEDED | Patient responsibility across the year exceeds the out-of-pocket max | Compare with the insurer's accumulator page; ask whether payments beyond the max are refundable |

## Matching order

1. Claim number, when the statement prints one, narrowed by CPT when both sides have it.
2. Otherwise patient + date of service + normalized provider (+ CPT when both have it). When several EOB lines match, lines with the same billed amount are preferred.

CPT codes are compared on the 5-character base code, so modifiers and unit suffixes (`99213-25`, `99213 x2`) still match.

When a claim covers several dates (therapy, inpatient stays), a bill line is compared only with that claim's lines on the same date of service.

Statement lines on the same account that resolve to the same set of EOB lines are compared **together**. A statement with one row per procedure therefore reconciles correctly against a claim whose EOB rows have no CPT codes, and the other way around. If those groups overlap, the result is `AMBIGUOUS_MATCH`, never a guess. Inside a group only totals are compared, so keep CPT codes on both sides whenever the documents print them.

Provider names are normalized by lowercasing, collapsing dotted initials (`P.A.`, `M.D.`, `L.L.C.`), stripping punctuation, and dropping words like LLC, PA, PC, MD, and Group. The same normalization applies to both columns of `providers.csv`, so a row like `Bayside Ortho,"Bayside Orthopedic Specialists, P.A."` works as written.

Patients are grouped case-insensitively, so `Alex` and `alex` share one accumulator.

## Known limits

- Accumulators are summed from the EOB lines you loaded, after duplicates are removed. If you load an incomplete year, the totals are low. The insurer's own accumulator page is the reference.
- Network status, family vs individual limits, and copays that don't count toward the deductible vary by plan. The script only compares against the numbers you pass in.
- Adjustments, write-offs, and payments are not modeled on the bill side. Load the latest statement's amount due; older statements for the same account are skipped automatically.
- Inside a group, an overcharge on one line can be offset by an undercharge on another. Groups containing a zero or credit line are marked `REVIEW_PARTIAL`; other offsets are not detectable without CPT codes on both sides.
- Same-day, same-price EOB lines with no CPT code under different claim numbers can't be told apart, so both are kept and flagged `POSSIBLE_DUPLICATE_CLAIM` rather than dropped.
- Without `--as-of`, the report date is today, so `NO_EOB` and `NO_EOB_PENDING` can change from one day to the next. Pass `--as-of` for repeatable output.

## Output files

`matches.csv`, one row per matched group:

| Column | Meaning |
|---|---|
| bill_id, statement_date, service_date, provider, patient | From the first statement line in the group |
| bill_lines, eob_lines | How many statement and EOB lines were compared together |
| amount_due, eob_patient_resp, difference | Group totals; difference = amount_due - eob_patient_resp |
| status | `OK`, `OVERBILLED`, `BILL_BELOW_EOB`, `REVIEW_PARTIAL`, or `REVIEW_AMBIGUOUS` |
| method | `claim_id` or `date_provider_patient` |
| claim_ids | EOB claim numbers in the group |
| bill_source, eob_sources | `file pN (row N)` for every line, separated by ` \| ` |

`exceptions.csv` columns: `code, kind, patient, service_date, provider, cpt, claim_id, bill_id, amount, detail, source`. `kind` is `eob`, `bill`, or `summary`; `amount` is the dollar figure to sort by and is blank when there isn't one.

`summary.json` keys: `as_of`, `eob_lines`, `eob_lines_used` (after duplicates are removed), `bill_lines`, `bill_lines_used` (latest statements only), `match_groups`, `exceptions` (count per code), `accumulators` (per patient: summed EOB money columns plus `deductible_remaining` / `oop_remaining` when limits are given), and `warnings`.
