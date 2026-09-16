"""
Two Sum II - Input Array Is Sorted

Given a 1-indexed array of integers numbers that is already sorted in non-decreasing order, 
find two numbers such that they add up to a specific target number.

You may assume that each input has exactly one solution and you cannot use the same element twice.

Constraints:
* 2 <= numbers.length <= 3 * 10^4
* -1000 <= numbers[i] <= 1000
* numbers is sorted in non-decreasing order
* -1000 <= target <= 1000
* The tests are generated such that there is exactly one solution.

Return an array of the two indices (1-indexed) as [index1, index2] where index1 < index2.

Example:
Input: numbers = [2, 7, 11, 15], target = 9
Output: [1, 2]
Explanation: The sum of 2 and 7 is 9. Therefore, index1 = 1, index2 = 2. We return [1, 2].

Example 2:
Input: numbers = [2, 3, 4], target = 6
Output: [1, 3]
Explanation: The sum of 2 and 4 is 6. Therefore, index1 = 1, index2 = 3. We return [1, 3].

Example 3:
Input: numbers = [-1, 0], target = -1
Output: [1, 2]

Hint: Use two pointers approach for O(n) time complexity and O(1) space complexity.
"""

from typing import List

def twoSum(numbers: List[int], target: int) -> List[int]:
    """
    Find two numbers that add up to target using two-pointer technique.
    
    Args:
        numbers: Sorted list of integers
        target: Target sum
        
    Returns:
        List of two 1-indexed positions [index1, index2]
    """
    print(numbers, target)

    for i, j in enumerate(numbers):
        for i2, j2 in enumerate(numbers):
            if j + j2 == target:
                return [i + 1, i2 + 1]

# Test cases
if __name__ == "__main__":

    # Test 1
    assert twoSum([2, 7, 11, 15], 9) == [1, 2]
    
    # Test 2
    assert twoSum([2, 3, 4], 6) == [1, 3]
    
    # Test 3
    assert twoSum([-1, 0], -1) == [1, 2]
    
    # Test 4
    assert twoSum([1, 2, 3, 4, 5, 6, 7], 11) == [4, 7]
    
    print("All tests passed!")
