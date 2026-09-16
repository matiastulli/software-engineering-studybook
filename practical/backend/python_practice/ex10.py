"""
Container With Most Water

You are given an integer array height of length n. There are n vertical lines drawn 
such that the two endpoints of the i-th line are (i, 0) and (i, height[i]).

Find two lines that together with the x-axis form a container, such that the container 
contains the most water.

Return the maximum area of water the container can store.

Notice: You may not slant the container.

Constraints:
* n == height.length
* 2 <= n <= 10^5
* 0 <= height[i] <= 10^4

Example 1:
Input: height = [1, 8, 6, 2, 5, 4, 8, 3, 7]
Output: 49
Explanation: The vertical lines are at indices 1 and 8. 
The width between them is 7 (8 - 1 = 7) and height is min(8, 7) = 7, 
so the area is 7 * 7 = 49.

Example 2:
Input: height = [1, 1]
Output: 1

Example 3:
Input: height = [2, 3, 4, 5, 6, 7, 8, 9, 10]
Output: 36
Explanation: The max area is between indices 0 and 8 (rightmost). 
Area = 8 * min(10, 2) = 8 * 2 = 16. But max is at indices 7 and 8: 
Area = 1 * min(9, 10) = 9. Actually at 0 and 8: Area = 8 * min(10, 2) = 16.
Check the last two at 8 and 9: Area = 1 * min(10, 9) = 9. 
The true answer: area = min(4, 2) * width = 2 * 8 = 16 (indices 0-8).

Hint: Use two pointers approach. Start from the widest container and move 
the pointer pointing to the shorter line inward.
"""

from typing import List

def maxArea(height: List[int]) -> int:
    """
    Find the maximum area of water that can be contained using two pointers.
    
    Time Complexity: O(n)
    Space Complexity: O(1)
    
    Args:
        height: List of integers representing the heights of vertical lines
        
    Returns:
        Maximum area of water that can be contained
    """
    max_area = 0
    left, right = 0, len(height) - 1
    
    while left < right:
        # Calculate area with current left and right pointers
        width = right - left
        current_height = min(height[left], height[right])
        current_area = width * current_height
        
        max_area = max(max_area, current_area)
        
        # Move the pointer pointing to the shorter line
        # This is the key insight: moving the taller line won't help
        # because the area is limited by the shorter line
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    
    return max_area


# Test cases
if __name__ == "__main__":
    # Test 1
    assert maxArea([1, 8, 6, 2, 5, 4, 8, 3, 7]) == 49
    
    # Test 2
    assert maxArea([1, 1]) == 1
    
    # Test 3
    assert maxArea([2, 3, 4, 5, 6, 7, 8, 9, 10]) == 36
    
    # Test 4
    assert maxArea([4, 3, 2, 1, 4]) == 16
    
    # Test 5
    assert maxArea([0, 0]) == 0
    
    print("All tests passed!")
