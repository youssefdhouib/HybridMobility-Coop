# Archived first run (v1)

Kept for transparency, not used in the report. Two problems found after inspecting it:

1. The oracle sometimes "optimally" left an 8-year-old unaccompanied, because the declared penalty for a child
   missing school (90, same as an adult) was cheaper than a parent arriving late. Fixed by declaring
   CHILD_MISSED_PENALTY = 240 (model.py). This changes household costs, so every condition was re-run.
2. With no working car in a view, car options were still listed. They are now hidden (only affects the oracle
   in v1, since the planner never knows about text-only breakdowns).

The v1 diagnosis that the LLM's reasons mention the broken car while its choices do not change much
motivated the added `interp` engine (LLM as news interpreter, rules decide).
