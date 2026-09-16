"""
Top K Frequent Elements

Given an integer array nums and an integer k, return the k most frequent elements. 
You may return the answer in any order.

Constraints:
* 1 <= nums.length <= 10^5
* -10^4 <= nums[i] <= 10^4
* k is in the range [1, the number of unique elements in the array]
* It is guaranteed that the answer is unique.

Follow up: Your algorithm's time complexity must be better than O(n log n), where n is the array's length.

Example 1:
Input: nums = [1, 1, 1, 2, 2, 3], k = 2
Output: [1, 2]
Explanation: The element 1 appears 3 times, 2 appears 2 times, 3 appears 1 time. 
Return the 2 most frequent elements.

Example 2:
Input: nums = [4, 1, 1, 1, 2, 2, 3], k = 2
Output: [1, 2]

Hint: Use a hash map to count frequencies, then use a min heap of size k to find top k.
Alternative: Use bucket sort for O(n) solution.
"""

from typing import List
from collections import Counter
import heapq

def topKFrequent(nums: List[int], k: int) -> List[int]:
    """
    Return the k most frequent elements using bucket sort.
    
    Time Complexity: O(n)  [Better than O(n log n)]
    Space Complexity: O(n)
    
    Args:
        nums: List of integers
        k: Number of top frequent elements to return
        
    Returns:
        List of k most frequent elements in any order
    """
    # Step 1: Count frequencies - O(n)
    count = Counter(nums)
    
    # Step 2: Create buckets where index represents frequency
    # Frequencies range from 1 to len(nums)
    buckets = [[] for _ in range(len(nums) + 1)]
    
    for num, freq in count.items():
        buckets[freq].append(num)
    
    # Step 3: Collect k most frequent elements from highest frequency buckets
    result = []
    for i in range(len(buckets) - 1, 0, -1):
        result.extend(buckets[i])
        if len(result) >= k:
            return result[:k]
    
    return result


# Test cases
if __name__ == "__main__":
    # Test 1
    result = topKFrequent([1, 1, 1, 2, 2, 3], 2)
    assert sorted(result) == [1, 2]
    
    # Test 2
    result = topKFrequent([4, 1, 1, 1, 2, 2, 3], 2)
    assert sorted(result) == [1, 2]
    
    # Test 3
    result = topKFrequent([1], 1)
    assert result == [1]
    
    # Test 4
    result = topKFrequent([1, 2, 3, 4, 5, 5, 5, 6, 6, 6, 6], 2)
    assert sorted(result) == [5, 6]
    
    print("All tests passed!")
