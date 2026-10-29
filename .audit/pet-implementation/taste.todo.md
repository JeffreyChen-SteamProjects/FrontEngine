- [x] Ground: profile schema owns validation; CompanionState owns completion; customization owns detached edits.
- [x] Sketch: compare optional favorite/disliked selections with a per-food score map. Independent taste_design review recommends candidate A with the same data and ownership contract.
- [x] Agree: skip: implementation is authorized without a checkpoint.
- [x] Implement: persist independent choices, snapshot taste at feeding start, apply bounded mood-only reaction on completion, expose controls and validate.
- [x] Scrap: discard the score map because it introduces preference strength without a requested consumer.

Candidate A uses optional preferences.taste with two nullable choices. It matches the requested simple preference UI and preserves profiles that omit the field.
Candidate B uses a score for every food. It supports gradients but needs additional UI and policy for unspecified values; no requirement currently needs numerical preference strength.

Proposed contract: favorite/disliked differ; each is null or one of four fictional treats. Missing taste means neutral. Feeding captures the selected taste when accepted. Fullness, affection and cooldown are unchanged. Favorite adds four mood points; disliked subtracts six from the food mood benefit, floored at zero. Completion displays a two-second food_like/food_dislike presentation, interrupted through the existing presentation rules. No reward on cancellation. UI Cancel/reset remain staged. A taste edit during feeding applies only to the next accepted feeding.
