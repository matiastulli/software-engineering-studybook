# ============================================================================
# COMPREHENSIVE COMPARISON: LISTS, DICTIONARIES, SETS, AND TUPLES
# ============================================================================

# 1. CREATION
# ============================================================================
my_list = [1, 2, 3, 4]
my_dict = {'name': 'Alice', 'age': 30}
my_set = {1, 2, 3, 4}
my_tuple = (1, 2, 3, 4)

# 2. MUTABILITY (Can you modify after creation?)
# ============================================================================
# MUTABLE: Lists, Dicts, Sets
my_list[0] = 99                 # ✅ Works
my_dict['city'] = 'NYC'         # ✅ Works
my_set.add(5)                   # ✅ Works

# IMMUTABLE: Tuples
my_tuple[0] = 99                # ❌ TypeError

# 3. ORDERING (Does order matter/preserved?)
# ============================================================================
# ORDERED: Lists (always), Tuples (always), Dicts (3.7+: insertion order)
# UNORDERED: Sets (unordered, no duplicates)

list1 = [1, 2, 3]
list2 = [1, 2, 3]
print(list1 == list2)           # ✅ True (same order matters)

set1 = {1, 2, 3}
set2 = {3, 2, 1}
print(set1 == set2)             # ✅ True (order doesn't matter for sets)

# 4. INDEXING & ACCESS
# ============================================================================
my_list = [10, 20, 30]
my_tuple = (10, 20, 30)
my_dict = {'a': 10, 'b': 20}
my_set = {10, 20, 30}

# Lists: ✅ Indexable
print(my_list[0])               # 10

# Tuples: ✅ Indexable
print(my_tuple[0])              # 10

# Dicts: ✅ Key access (not positional index)
print(my_dict['a'])             # 10

# Sets: ❌ NOT indexable
# print(my_set[0])              # ❌ TypeError

# 5. MEMBERSHIP TESTING (Checking if item exists)
# ============================================================================
my_list = [1, 2, 3]
my_set = {1, 2, 3}

# Lists: O(n) - slow for large lists
if 2 in my_list:                # Check takes O(n)
    print("Found in list")

# Sets: O(1) - fast!
if 2 in my_set:                 # Check takes O(1)
    print("Found in set")

# For large datasets, ALWAYS use sets for membership testing!

# 6. ITERATION
# ============================================================================
my_list = [1, 2, 3]
my_dict = {'a': 1, 'b': 2}
my_set = {1, 2, 3}
my_tuple = (1, 2, 3)

# Lists
for item in my_list:
    print(item)                 # 1, 2, 3

# Dicts (iterate keys by default)
for key in my_dict:
    print(key)                  # 'a', 'b'

# Dict items
for key, value in my_dict.items():
    print(key, value)           # ('a', 1), ('b', 2)

# Sets
for item in my_set:
    print(item)                 # 1, 2, 3 (unordered)

# Tuples
for item in my_tuple:
    print(item)                 # 1, 2, 3

# 7. DUPLICATES
# ============================================================================
# Lists: Allow duplicates
my_list = [1, 2, 2, 3, 3, 3]    # ✅ Valid

# Dicts: Keys must be unique (values can duplicate)
my_dict = {'a': 1, 'a': 2}      # Key 'a' overwrites, final: {'a': 2}

# Sets: NO duplicates allowed
my_set = {1, 2, 2, 3, 3, 3}     # Becomes {1, 2, 3}

# Tuples: Allow duplicates
my_tuple = (1, 2, 2, 3, 3, 3)   # ✅ Valid

# 8. HASHABLE (Can be used as dict key or in set?)
# ============================================================================
# HASHABLE (✅ Can be key/in set): Tuples, Strings, Numbers
dict_with_tuple_key = {(0, 0): 'origin', (1, 1): 'point A'}
set_with_tuples = {(1, 2), (3, 4)}

# NOT HASHABLE (❌ Cannot be key/in set): Lists, Dicts, Sets
# dict_with_list_key = {[0, 0]: 'origin'}    # ❌ TypeError
# set_with_lists = {[1, 2], [3, 4]}          # ❌ TypeError

# 9. SLICING
# ============================================================================
# Lists: ✅ Support slicing
my_list = [1, 2, 3, 4, 5]
print(my_list[1:3])             # [2, 3]

# Tuples: ✅ Support slicing
my_tuple = (1, 2, 3, 4, 5)
print(my_tuple[1:3])            # (2, 3)

# Dicts: ❌ No slicing
# print(my_dict[1:3])             # ❌ TypeError

# Sets: ❌ No slicing
# print(my_set[1:3])              # ❌ TypeError

# 10. TIME COMPLEXITY COMPARISON
# ============================================================================
# ┌────────────┬──────────┬──────────┬──────────┬──────────┐
# │ Operation  │  List    │  Dict    │   Set    │  Tuple   │
# ├────────────┼──────────┼──────────┼──────────┼──────────┤
# │ Access     │  O(1)    │  O(1)    │   N/A    │  O(1)    │
# │ Search     │  O(n)    │  O(1)    │  O(1)    │  O(n)    │
# │ Insert     │  O(n)    │  O(1)    │  O(1)    │  N/A     │
# │ Delete     │  O(n)    │  O(1)    │  O(1)    │  N/A     │
# │ Iteration  │  O(n)    │  O(n)    │  O(n)    │  O(n)    │
# └────────────┴──────────┴──────────┴──────────┴──────────┘

# 11. COMMON OPERATIONS SUMMARY
# ============================================================================

# Remove duplicates
numbers = [1, 2, 2, 3, 3, 3]
unique = list(set(numbers))     # [1, 2, 3]

# Find common elements
list_a = [1, 2, 3]
list_b = [2, 3, 4]
common = set(list_a) & set(list_b)  # {2, 3}

# Group data
data = [('Alice', 25), ('Bob', 30), ('Alice', 28)]
from collections import defaultdict
grouped = defaultdict(list)
for name, age in data:
    grouped[name].append(age)   # {'Alice': [25, 28], 'Bob': [30]}

# Count occurrences
from collections import Counter
items = ['apple', 'banana', 'apple', 'cherry']
counts = Counter(items)         # {'apple': 2, 'banana': 1, 'cherry': 1}

# Return multiple values
def get_coords():
    return (10, 20)             # Return tuple

x, y = get_coords()             # Unpack tuple

# 12. WHEN TO USE EACH
# ============================================================================

# USE LISTS when:
# ✅ Order matters
# ✅ You need to modify (add/remove) items
# ✅ You might have duplicates
# ❌ You don't need fast membership testing

my_list = [1, 2, 3, 4, 5]

# USE DICTIONARIES when:
# ✅ You need key-value pairs
# ✅ You need O(1) lookup by key
# ✅ Keys are unique
# ❌ You need unordered unique values (use set instead)

my_dict = {'name': 'Alice', 'age': 30}

# USE SETS when:
# ✅ You need FAST membership testing O(1)
# ✅ You need unique values only
# ✅ You don't care about order
# ❌ You need to access by index or maintain order

my_set = {1, 2, 3, 4, 5}

# USE TUPLES when:
# ✅ Data should NOT change (immutable)
# ✅ You need to use as dict key or in a set
# ✅ You want slightly better performance than lists
# ❌ You need to modify the data

my_tuple = (1, 2, 3, 4, 5)

# 13. INTERVIEW TIPS
# ============================================================================

# Tip 1: Use sets for membership testing (avoid O(n) checks)
# BAD:  if item in my_list:        # O(n)
# GOOD: if item in my_set:         # O(1)

# Tip 2: Use dicts for fast lookups by key
# BAD:  for item in my_list if item[0] == target
# GOOD: my_dict[target]

# Tip 3: Use tuples as dict keys for coordinates/pairs
coordinates = {(0, 0): 'origin', (1, 2): 'point'}

# Tip 4: Use Counter for frequency problems
freq = Counter([1, 2, 2, 3, 3, 3])  # {3: 3, 2: 2, 1: 1}

# Tip 5: Tuple unpacking is powerful
a, b, c = (1, 2, 3)
x, *middle, z = (1, 2, 3, 4, 5)    # x=1, middle=[2,3,4], z=5

print("✅ All comparisons complete!")