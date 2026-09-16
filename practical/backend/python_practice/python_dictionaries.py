# Dictionaries
# mutable + key/value + unique keys + O(1) average lookup
# Keys must be unique and immutable (e.g., strings, numbers, tuples), while values can be of any data type and can be duplicated.
# O(1) = constant time — the operation takes roughly the same amount of time no matter how much data exists.

# Creation and access
my_dict = {'name': 'Alice', 'age': 30}
print(my_dict['name'])          # Access: 'Alice'
print(my_dict.get('age', 0))    # Safe access with default
print(my_dict.get('city'))      # Returns None if key doesn't exist

# Modification
my_dict['city'] = 'NYC'        # Add/update
my_dict.update({'age': 31})    # Bulk update
my_dict.pop('age')             # Remove & return value
del my_dict['city']            # Remove key

# Common operations
my_dict.keys()                 # All keys
my_dict.values()               # All values
my_dict.items()                # Key-value pairs
'name' in my_dict              # Check key existence
len(my_dict)                   # Count items

# how to iterate?
for key, value in my_dict.items():
    print(key, value)            # Iterate key-value pairs

# enumerate + dict
for index, (key, value) in enumerate(my_dict.items()):
    print(index, key, value)     # Iterate with index



