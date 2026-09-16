# Problem:
# You have a staircase with n steps.
# Each move, you can climb either 1 step or 2 steps.
# How many distinct ways are there to reach the top?


# ── WHY THIS IS FIBONACCI ────────────────────────────────────────────────────
# To reach step n you came from either:
#   - step n-1 (took 1 step)  → ways(n-1) paths lead here
#   - step n-2 (took 2 steps) → ways(n-2) paths lead here
#
# So: ways(n) = ways(n-1) + ways(n-2)
#
# Base cases:
#   ways(0) = 1  → one way to "be" at the ground (do nothing)
#   ways(1) = 1  → one way: take 1 step
#   ways(2) = 2  → two ways: (1+1) or (2)


# ── SOLUTION 1: Bottom-up DP (optimal for interviews) ────────────────────────
# Time: O(n)  |  Space: O(n)  →  can reduce to O(1) (see Solution 2)

def reach_top(staircase):
    if staircase <= 1:
        return 1

    dp = [0] * (staircase + 1)
    dp[0] = 1   # base: one way to stand at ground
    dp[1] = 1   # base: one way to reach step 1

    for step in range(2, staircase + 1):
        dp[step] = dp[step - 1] + dp[step - 2]

    return dp[staircase]


# ── SOLUTION 2: Space-optimized (O(1) space) ──────────────────────────────────
# You only ever need the previous two values — no need for the full array.

def reach_top_optimized(staircase):
    if staircase <= 1:
        return 1

    prev2, prev1 = 1, 1     # dp[0], dp[1]

    for _ in range(2, staircase + 1):
        current = prev1 + prev2
        prev2 = prev1
        prev1 = current

    return prev1


# ── SOLUTION 3: General — any set of allowed moves ────────────────────────────
# moves = [1, 2] → same as above
# moves = [1, 2, 3] → you can take 1, 2, or 3 steps at a time
# This is the pattern to reach for when the interviewer changes the moves.

def reach_top_general(staircase, moves):
    dp = [0] * (staircase + 1)
    dp[0] = 1   # base: one way to be at the ground

    for step in range(1, staircase + 1):
        for move in moves:
            if step - move >= 0:
                dp[step] += dp[step - move]

    return dp[staircase]


# ── TESTS ─────────────────────────────────────────────────────────────────────
# n=1 → 1 way:  (1)
# n=2 → 2 ways: (1+1), (2)
# n=3 → 3 ways: (1+1+1), (1+2), (2+1)
# n=4 → 5 ways: (1+1+1+1), (1+1+2), (1+2+1), (2+1+1), (2+2)
# n=5 → 8 ways  ← Fibonacci sequence: 1,1,2,3,5,8,13...

for n, expected in [(1,1),(2,2),(3,3),(4,5),(5,8),(10,89)]:
    r1 = reach_top(n)
    r2 = reach_top_optimized(n)
    r3 = reach_top_general(n, [1, 2])
    assert r1 == r2 == r3 == expected, f"n={n}: got {r1}, expected {expected}"
    print(f"n={n:2d} → {r1} ways  ✓")

# General with 3 moves
print()
print(f"n=4, moves=[1,2,3] → {reach_top_general(4, [1, 2, 3])} ways")  # 7
print(f"n=5, moves=[1,2,3] → {reach_top_general(5, [1, 2, 3])} ways")  # 13


# ── INTERVIEW CHEAT SHEET ─────────────────────────────────────────────────────
# Pattern: dp[i] = sum of dp[i - move] for each allowed move
# Base:    dp[0] = 1  (one way to be at start)
# Answer:  dp[n]
#
# This same pattern solves:
#   - Coin change (count combinations)   → moves = coin denominations
#   - Word break                         → moves = word lengths
#   - Decode ways                        → moves = [1, 2] with digit constraints
