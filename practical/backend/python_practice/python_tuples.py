# Tuples
# Immutable ordered collections of elements


# Creation
my_tuple = (1, 2, 3, 4, 5)
single_item = (42,)             # Comma required for single-item tuple!
single_item = (42)              # This is just 42 (integer, not tuple)
empty_tuple = ()

# Access (like lists)
print(my_tuple[0])              # 1
print(my_tuple[-1])             # 5
print(my_tuple[1:3])            # (2, 3)

# Length and membership
len(my_tuple)                   # 5
3 in my_tuple                   # True


# Immutability
# Lists are mutable (can change)
my_list = [1, 2, 3]
my_list[0] = 99                 # Works fine

# Tuples are immutable (cannot change)
my_tuple = (1, 2, 3)
my_tuple[0] = 99                # TypeError: 'tuple' object does not support item assignment

# You can reassign the variable, but not modify the tuple
my_tuple = (99, 2, 3)           # This creates a new tuple

# Operations
my_tuple = (1, 2, 3, 2)

# What you CAN do
len(my_tuple)                   # 4
my_tuple.count(2)               # 2 (how many times 2 appears)
my_tuple.index(2)               # 1 (first position of 2)
my_tuple + (4, 5)               # (1, 2, 3, 2, 4, 5) (creates new tuple)
my_tuple * 2                    # (1, 2, 3, 2, 1, 2, 3, 2) (repeats)
tuple([1, 2, 3])                # Convert list to tuple

# What you CANNOT do
my_tuple.append(4)              # AttributeError
my_tuple[0] = 99                # TypeError
my_tuple.pop()                  # TypeError


# Why use tuples?
# 1. Immutability: Tuples cannot be changed after creation, which can help prevent bugs and make code safer.
# 2. Performance: Tuples are generally faster than lists for certain operations due to their immutability.
# 3. Hashability: Tuples can be used as keys in dictionaries or elements of sets, while lists cannot.
# 4. Namedtuples: The collections.namedtuple class allows you to create tuple subclasses with named fields, improving code readability.

from collections import namedtuple

Person = namedtuple('Person', ['name', 'age', 'city'])
alice = Person('Alice', 30, 'NYC')
print(alice.name)               # 'Alice' (more readable than [0])
print(alice[0])                 # Also works: 'Alice'

# How to iterate?

# 1.
for index, item in enumerate(my_tuple):
    print(index, item)

# 2.

for item in sorted(my_tuple, reverse=True):
    print(item)  # Sorted in descending order