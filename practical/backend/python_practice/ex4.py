"""
Given a file named module.py containing the following code:
"""

def funcA():
    pass
def __funcB__():
    pass
def funcC():
    pass

if __name__ == "__main__":
    del funcC

# What functions are available in the module when it is imported?

# When the module is imported, the available functions are funcA and __funcB__. 
# The function funcC is deleted when the module is run as the main program.
# __ does not make a function private, it just indicates that it is intended for internal use.