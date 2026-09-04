# Evaluation notes

ReviewerIQ should be evaluated as a **resource-allocation system**.

Key questions:

1. Does the policy stay within the analyst-hour budget?
2. How many severe cases are caught?
3. How much synthetic risk is captured per analyst hour?
4. How much uncertainty/novelty is represented for learning?
5. How many severe cases remain in the queue?

All policies are compared against the same generated case population and the same capacity constraint.

The default implementation uses a transparent greedy utility-per-minute allocator. A production extension could replace it with an integer-programming or contextual-bandit policy while keeping the same outcome metrics and human-review guardrails.
