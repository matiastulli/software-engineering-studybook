"""
Python Collections Module - Advanced Data Structures

The collections module provides specialized data types beyond the built-in dict, list, tuple, set.
These are essential for efficient coding in technical interviews.
"""

# ============================================================================
# 1. defaultdict - Dictionary with default values for missing keys
# ============================================================================

from collections import defaultdict

print("=" * 70)
print("1. DEFAULTDICT - Automatic default values for missing keys")
print("=" * 70)

# Regular dict raises KeyError
regular_dict = {}
# regular_dict['key1']  # KeyError!

# defaultdict returns a default value
int_dict = defaultdict(int)  # Default value: 0
list_dict = defaultdict(list)  # Default value: []
str_dict = defaultdict(str)  # Default value: ''
set_dict = defaultdict(set)  # Default value: set()

# Example 1: Counting with defaultdict
words = ["apple", "banana", "apple", "cherry", "banana", "apple"]

word_count = defaultdict(int)
for word in words:
    word_count[word] += 1

print(f"Word count: {dict(word_count)}")
# Output: {'apple': 3, 'banana': 2, 'cherry': 1}

# Example 2: Grouping by key
students = [
    {"name": "Alice", "grade": "A"},
    {"name": "Bob", "grade": "B"},
    {"name": "Charlie", "grade": "A"},
    {"name": "Diana", "grade": "B"},
]

grade_groups = defaultdict(list)
for student in students:
    grade_groups[student["grade"]].append(student["name"])

print(f"Students by grade: {dict(grade_groups)}")
# Output: {'A': ['Alice', 'Charlie'], 'B': ['Bob', 'Diana']}

# Example 3: Graph adjacency list (common in coding problems)
graph = defaultdict(list)
edges = [(1, 2), (1, 3), (2, 3), (3, 4)]

for u, v in edges:
    graph[u].append(v)
    graph[v].append(u)

print(f"Graph adjacency list: {dict(graph)}")
# Output: {1: [2, 3], 2: [1, 3], 3: [2, 4], 4: [3]}

# ============================================================================
# 2. Counter - Count hashable objects
# ============================================================================

from collections import Counter

print("\n" + "=" * 70)
print("2. COUNTER - Count occurrences of elements")
print("=" * 70)

# Example 1: Count characters in a string
text = "mississippi"
char_count = Counter(text)
print(f"Character counts: {char_count}")
# Output: Counter({'i': 4, 's': 4, 'p': 2, 'm': 1})

# Example 2: Most common elements
most_common = char_count.most_common(3)
print(f"Top 3 most common: {most_common}")
# Output: [('i', 4), ('s', 4), ('p', 2)]

# Example 3: Combine counters
list1 = [1, 2, 2, 3, 3, 3]
list2 = [2, 3, 3, 4, 4, 4, 4]

counter1 = Counter(list1)
counter2 = Counter(list2)

print(f"Counter1: {counter1}")  # Counter({3: 3, 2: 2, 1: 1})
print(f"Counter2: {counter2}")  # Counter({4: 4, 3: 2, 2: 1})

# Addition (combine counts)
combined = counter1 + counter2
print(f"Combined (addition): {combined}")
# Output: Counter({3: 5, 4: 4, 2: 3, 1: 1})

# Subtraction
difference = counter1 - counter2
print(f"Difference (counter1 - counter2): {difference}")
# Output: Counter({3: 1, 2: 1, 1: 1})

# Intersection (keep minimum)
intersection = counter1 & counter2
print(f"Intersection (min): {intersection}")
# Output: Counter({3: 2, 2: 1})

# Union (keep maximum)
union = counter1 | counter2
print(f"Union (max): {union}")
# Output: Counter({4: 4, 3: 3, 2: 2, 1: 1})

# ============================================================================
# 3. deque - Double-ended queue (efficient for popping from both ends)
# ============================================================================

from collections import deque

print("\n" + "=" * 70)
print("3. DEQUE - Double-ended queue for efficient operations")
print("=" * 70)

# Regular list: O(n) for popleft(), O(1) for pop()
# deque: O(1) for both popleft() and pop()

dq = deque([1, 2, 3, 4, 5])

print(f"Original deque: {dq}")

# Pop from right (end)
right_val = dq.pop()
print(f"Popped from right: {right_val}, deque: {dq}")
# Output: 5, deque([1, 2, 3, 4])

# Pop from left (beginning) - O(1) operation!
left_val = dq.popleft()
print(f"Popped from left: {left_val}, deque: {dq}")
# Output: 1, deque([2, 3, 4])

# Append to both ends
dq.append(10)  # Add to right
dq.appendleft(0)  # Add to left
print(f"After append operations: {dq}")
# Output: deque([0, 2, 3, 4, 10])

# Rotate
dq2 = deque([1, 2, 3, 4, 5])
dq2.rotate(2)  # Rotate right by 2
print(f"Rotated right by 2: {dq2}")
# Output: deque([4, 5, 1, 2, 3])

# Use case: Sliding window
print("\nSliding window example:")
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9]
window_size = 3
window = deque(maxlen=window_size)  # Auto removes oldest when full

for num in numbers:
    window.append(num)
    if len(window) == window_size:
        print(f"Window: {list(window)}, sum: {sum(window)}")

# ============================================================================
# 4. OrderedDict - Dictionary that remembers insertion order
# ============================================================================

from collections import OrderedDict

print("\n" + "=" * 70)
print("4. ORDEREDDICT - Preserves insertion order (mostly historical)")
print("=" * 70)

# Note: In Python 3.7+, regular dicts preserve insertion order!
# OrderedDict is mainly for compatibility or specialized operations

regular_dict = {"z": 1, "a": 2, "m": 3}
ordered_dict = OrderedDict([("z", 1), ("a", 2), ("m", 3)])

print(f"Regular dict keys: {list(regular_dict.keys())}")
print(f"OrderedDict keys: {list(ordered_dict.keys())}")

# Useful feature: move_to_end()
ordered_dict.move_to_end("a")  # Move "a" to the end
print(f"After move_to_end('a'): {list(ordered_dict.keys())}")
# Output: ['z', 'm', 'a']

# ============================================================================
# 5. namedtuple - Lightweight immutable class
# ============================================================================

from collections import namedtuple

print("\n" + "=" * 70)
print("5. NAMEDTUPLE - Lightweight immutable objects")
print("=" * 70)

# Create a namedtuple class
Point = namedtuple("Point", ["x", "y"])
Color = namedtuple("Color", ["r", "g", "b"])

# Create instances
p1 = Point(3, 4)
p2 = Point(x=10, y=20)

print(f"Point p1: {p1}")
print(f"Access p1.x: {p1.x}, p1.y: {p1.y}")

# Can unpack like tuples
x, y = p1
print(f"Unpacked p1: x={x}, y={y}")

# Can be used as dict keys (unlike regular objects)
locations = {p1: "first location", p2: "second location"}
print(f"Points as dict keys: {locations}")

# Useful for parsing data
csv_line = "red,255,0,0"
color = Color(*csv_line.split(",")[1:])
print(f"Color from CSV: {color}")

# ============================================================================
# 6. groupby - Group consecutive elements with same key
# ============================================================================

from itertools import groupby

print("\n" + "=" * 70)
print("6. GROUPBY - Group consecutive elements")
print("=" * 70)

# Example 1: Group consecutive identical elements
data = "aabbccddaa"
grouped = groupby(data)

print("Grouped characters:")
for key, group in grouped:
    print(f"  {key}: {list(group)}")
# Output:
# a: ['a', 'a']
# b: ['b', 'b']
# c: ['c', 'c']
# d: ['d', 'd']
# a: ['a', 'a']

# Example 2: Group by function result
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
grouped = groupby(numbers, key=lambda x: x % 2)  # Group by odd/even

print("\nGrouped by odd/even:")
for is_even, group in grouped:
    parity = "even" if is_even == 0 else "odd"
    print(f"  {parity}: {list(group)}")

# Example 3: Compress consecutive runs
def compress_runs(data):
    """Compress consecutive identical characters: 'aaabbbbaa' -> 'a3b4a2'"""
    result = []
    for key, group in groupby(data):
        count = len(list(group))
        result.append(f"{key}{count}")
    return "".join(result)

compressed = compress_runs("aaabbbbaa")
print(f"\nCompressed 'aaabbbbaa': {compressed}")
# Output: a3b4a2

# ============================================================================
# PRACTICAL EXERCISE: Use multiple collections together
# ============================================================================

print("\n" + "=" * 70)
print("EXERCISE: Using multiple collections together")
print("=" * 70)

# Problem: Analyze word frequency in a sentence
sentence = "the quick brown fox jumps over the lazy dog the fox"

# Split and convert to lowercase
words = sentence.lower().split()

# Use Counter to count frequencies
word_freq = Counter(words)

# Use defaultdict to group words by frequency
freq_groups = defaultdict(list)
for word, freq in word_freq.items():
    freq_groups[freq].append(word)

# Use deque for efficient processing
freq_deque = deque(sorted(freq_groups.keys(), reverse=True))

print(f"Word frequencies: {word_freq}")
print(f"\nWords grouped by frequency:")
while freq_deque:
    freq = freq_deque.popleft()
    print(f"  Frequency {freq}: {freq_groups[freq]}")

print("\n" + "=" * 70)
