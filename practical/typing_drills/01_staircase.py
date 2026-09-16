# ============================================================
# DRILL: "La Escalera" — Climbing Stairs
# ============================================================
# Rules: AI off, autocomplete off. Read the comment, say out loud what
# you're about to write, then type it yourself below the comment.
# Don't scroll ahead — each step only makes sense once the previous
# one runs. Target: ~15-20 min for the whole file.
#
# Problem: a staircase has n steps. Each move you take either 1 or 2
# steps. How many DISTINCT ways can you reach the top?
# Example: n = 3 -> [1,1,1], [1,2], [2,1] = 3 ways.


# --- STEP 1: Brute force recursion ---
# Write climb_stairs_recursive(n) -> int.
# Base cases: n == 0 -> 1 (already at the top). n < 0 -> 0.
# Recurrence: ways(n) = ways(n-1) + ways(n-2)
# Say out loud why this recurrence is true before you type it.


# (type it below)

def climb_stairs_recursive(n: int) -> int:
    
    
    
    return 0
    
    

# --- STEP 2: Sanity check ---
# Call climb_stairs_recursive(9) and print it.
# Guess the number out loud BEFORE running, then compare.


# (type it below)


# --- STEP 3: Feel the cost ---
# Time climb_stairs_recursive(30) with time.perf_counter().
# It should be noticeably slow. Say out loud why: which subproblems
# are being recomputed, and how many times?


# (type it below)


# --- STEP 4: Memoize it ---
# Write climb_stairs_memo(n, cache=None) -> int.
# Same recurrence as Step 1, but check the cache dict before
# recursing, and store the result before returning.
# (Careful with the mutable-default-argument trap — decide out loud
# how you're handling it.)


# (type it below)


# --- STEP 5: Bottom-up, O(1) space ---
# Write climb_stairs_dp(n) -> int using a plain loop and two rolling
# variables (no recursion, no cache dict) — same shape as a Fibonacci
# iterative solution.


# (type it below)


# --- STEP 6: "The better combination" ---
# Instead of counting ways, return ONE valid combination of moves
# (e.g. [2, 2, 2, 2, 1]) that reaches n using the FEWEST total moves —
# i.e. as many 2-steps as possible, with a single leftover 1-step if
# n is odd.
# Write min_moves_combination(n) -> list[int].


# (type it below)


# --- STEP 7: Wire it together ---
# For n = 9, print:
#   - total distinct ways         -> climb_stairs_dp(9)
#   - the minimum-move combination -> min_moves_combination(9)
#   - how many moves it takes      -> len(...)


# (type it below)
