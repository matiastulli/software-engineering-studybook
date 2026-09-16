"""
Instructions

Implement the function solution(text) so that the execution of this code:

print(solution("Hello   you !"))

Output:

Hello
you
!

Warning: please note there can be multiple spaces between two words. In that case, the returned string must not contain empty lines. 

So, making a simple replacement of every space by a \n character will not work.

The function must return a string with \n characters. It must not print the words to the standard output.

The parameter text is always a string. There are never spaces at the beginning or at the end of text.

"""

# Python code below
# Use print("messages...") to debug your solution.

def solution(text):
    # Your code goes here
    return "\n".join(text.split())
        

result = solution("Hello   you !")
print(result)