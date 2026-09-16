"""
The name of the module to generate permutations, combinations, and Cartesian products, etc

"""

# itertools is a standard library module that provides functions for creating iterators for efficient looping.

from itertools import product

prefixes = ["pre", "post"]
middles = ["fix", "mix"]
suffixes = ["ing", "ed"]

for pref, mid, suff in product(prefixes, middles, suffixes):
    complete_word = pref + mid + suff
    print(complete_word)

from itertools import permutations

letters = "abc"

for perm in permutations(letters):
    print("".join(perm))

from itertools import combinations

letters = "abc"
for comb in combinations(letters, 2):
    print("".join(comb))