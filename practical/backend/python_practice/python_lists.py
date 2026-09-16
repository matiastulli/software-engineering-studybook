# Lists
# ordered + mutable + duplicates allowed

# Creation and access
my_list = [1, 2, 3, 4, 5]
print(my_list[0])      # Access: 1
print(my_list[-1])     # Last element: 5
print(my_list[1:3])    # Slicing: [2, 3]

# Modification
my_list.append(6)      # Add to end
my_list.insert(0, 0)   # Insert at index
my_list.remove(3)      # Remove by value
my_list.pop()          # Remove & return last
my_list.pop(0)         # Remove & return first element
my_list.extend([7, 8]) # Add multiple items

# Common operations
len(my_list)           # Length
3 in my_list           # Membership check (returns True or False)
my_list.sort()         # sort() modifies the list in-place and returns None
sorted(my_list)        # sorted() returns a new sorted list without modifying the original
my_list.reverse()      # Reverse in-place


# Copying lists
new_list = my_list.copy()  # Shallow copy
new_list = my_list[:]     # Another way to copy


# List comprehensions
# [new_value for item in iterable] = [x**2 for x in my_list]
squared = [x**2 for x in my_list]  # Create a new list with squared values
even_numbers = [x for x in my_list if x % 2 == 0]  # Filter even numbers

# How to iterate?
# 1.
for item in my_list:
    print(item)

# 2.
values = [1, 2, 3, 4, 5]

for i, j in enumerate(values):
    print(i, j)

# 3.
for i in range(1, len(values) - 1):
    print(i)

# 4.

list1 = [1, 2, 3]
list2 = ['a', 'b', 'c']
for num, letter in zip(list1, list2):
    print(num, letter)

# 5.

for item in reversed(values):
    print(item)

# Search for specific value:

numbers = [10, 20, 30, 40]

if 20 in numbers:
    print("Exists")

# Why list and not set?
# Lists maintain order and allow duplicates, while sets do not maintain order and do not allow duplicates.

# Why list and not tuple?
# Lists are mutable (can be changed), while tuples are immutable (cannot be changed). 
# Use lists when you need to modify the data, and tuples when you want to ensure the data remains constant.

# Complexity of pop(0)?
# The complexity of pop(0) is O(n) because it requires shifting all the remaining elements one position to the left after removing the first element.
