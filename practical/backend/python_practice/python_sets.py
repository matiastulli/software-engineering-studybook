# Sets
# mutable + unique elements + O(1) average lookup
# duplicates are not allowed, order is not guaranteed, and elements must be hashable (immutable types like int, str, tuple)

# Creation and access
my_set = set()
my_set = {1, 2, 3, 4, 5}
print(my_set)          # Output: {1, 2, 3, 4, 5}

# Modification
my_set.add(6)          # Add element
my_set.remove(3)       # Remove element (raises KeyError if not found)
my_set.discard(7)      # Remove element (no error if not found)
my_set.pop()           # Remove and return arbitrary element

# Common operations
len(my_set)            # Length
3 in my_set            # Membership check (returns True or False)

# Set operations
set1 = {1, 2, 3}
set2 = {3, 4, 5}
print(set1.union(set2))        # Union: {1, 2, 3, 4, 5}
print(set1.intersection(set2)) # Intersection: {3}
print(set1.difference(set2))    # Difference: {1, 2}
print(set1.symmetric_difference(set2)) # Symmetric difference: {1, 2, 4, 5}

# How to iterate?
# 1.
for item in my_set:
    print(item)

# 2.

for index, item in enumerate(my_set):
    print(index, item)  # Note: order not guaranteed

# 3.

for item in sorted(my_set, reverse=True):
    print(item)  # Sorted in descending order

# Fast membership test using a set
nums = [1,2,3,1,4]
seen = set()

for x in nums:
    if x in seen:
        print("duplicate")
    seen.add(x)

# Why set and not list?
# Sets are unordered collections of unique elements. 
# They are useful when you need to eliminate duplicates or perform mathematical set operations.

# Remove duplicates from a list using a set
my_list = [1, 2, 2, 3, 4, 4, 5]
unique_set = set(my_list)
print(unique_set)  # Output: {1, 2, 3, 4, 5}


