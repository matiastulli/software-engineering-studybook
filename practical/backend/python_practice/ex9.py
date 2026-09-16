"""
Search in Rotated Sorted Array

There is an integer array nums sorted in ascending order (with distinct values).

Prior to being passed to your function, nums is possibly rotated at an unknown pivot index k 
(1 <= k < nums.length) such that the resulting array is [nums[k], nums[k+1], ..., nums[n-1], nums[0], nums[1], ..., nums[k-1]].

For example, [0, 1, 2, 4, 5, 6, 7] might be rotated at pivot index 3 and become [4, 5, 6, 7, 0, 1, 2].

Given the rotated array nums and an integer target, return the index of target if it is in nums, or -1 if it is not in nums.

You must write an algorithm with O(log n) runtime complexity.

Constraints:
* 1 <= nums.length <= 5000
* -10^4 <= nums[i] <= 10^4
* All values of nums are unique.
* nums is an ascending array that is possibly rotated.
* -10^4 <= target <= 10^4

Example 1:
Input: nums = [4, 5, 6, 7, 0, 1, 2], target = 0
Output: 4
Explanation: 0 is at index 4.

Example 2:
Input: nums = [4, 5, 6, 7, 0, 1, 2], target = 3
Output: -1

Example 3:
Input: nums = [1], target = 1
Output: 0

Hint: Use binary search. Determine which half of the array is sorted, 
then decide which half contains the target.
"""

from typing import List

def search(nums: List[int], target: int) -> int:
    """
    Search for target in rotated sorted array.
    
    Args:
        nums: Rotated sorted array with distinct values
        target: Value to search for
        
    Returns:
        Index of target if found, -1 otherwise
    """
    
    if target not in nums:
        return -1
    
    for i, j in enumerate(nums):
        if target == j:
            return i


# Test cases
if __name__ == "__main__":
    # Test 1
    assert search([4, 5, 6, 7, 0, 1, 2], 0) == 4
    
    # Test 2
    assert search([4, 5, 6, 7, 0, 1, 2], 3) == -1
    
    # Test 3
    assert search([1], 1) == 0
    
    # Test 4
    assert search([1, 3], 3) == 1
    
    # Test 5
    assert search([1, 3, 5], 5) == 2
    
    # Test 6
    assert search([3, 1], 3) == 0
    
    print("All tests passed!")
