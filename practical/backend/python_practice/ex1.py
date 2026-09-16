""" 
Radioactivity Sensor Peak Detection

Your company builds radioactivity sensors and you are responsible for validating their behavior. 

A failing sensor often produces large fluctuations over short periods of time.

You receive a list named values, where each element represents the radioactivity measured by the sensor every second.

Your task is to count the number of peaks in the data.

A value is considered a peak if:

* It is a top peak:
    * The value is at least 5 units greater than both neighboring values.
* It is a bottom peak:
    * The value is at least 5 units smaller than both neighboring values.

Return the total number of top peaks and bottom peaks.

Important rules

* The first and last elements can never be peaks because they do not have two neighbors.
* A difference of exactly 5 is valid.
* values is always defined.
* values contains between 0 and 20 elements.
* Values range between 0 and 100.

Fx: def count_peaks(values: List[float]) -> int:

 """
from typing import List

def count_peaks(values: List[float]) -> int:

    peaks = 0

    for i in range(1, len(values) - 1):
        current = values[i]
        left = values[i - 1]
        right = values[i + 1]
        # Top peak
        if current >= left + 5 and current >= right + 5:
            peaks += 1
        # Bottom peak
        elif current <= left - 5 and current <= right - 5:
            peaks += 1

    return peaks



# Test Cases
if __name__ == "__main__":
    # Test 1: Empty list
    assert count_peaks([]) == 0, "Empty list should return 0 peaks"
    
    # Test 2: Single element
    assert count_peaks([50]) == 0, "Single element should return 0 peaks"
    
    # Test 3: Two elements
    assert count_peaks([10, 50]) == 0, "Two elements should return 0 peaks"
    
    # Test 4: No peaks
    assert count_peaks([1, 2, 3, 4, 5]) == 0, "Monotonic increase should have no peaks"
    
    # Test 5: Single top peak
    assert count_peaks([1, 10, 1]) == 1, "Single top peak: 10 is 9 units above both neighbors"
    
    # Test 6: Single bottom peak
    assert count_peaks([50, 40, 50]) == 1, "Single bottom peak: 40 is 10 units below both neighbors"
    
    # Test 7: Top peak with exactly 5 unit difference (boundary case)
    assert count_peaks([10, 15, 10]) == 1, "Exactly 5 units difference should count as peak"
    
    # Test 8: Bottom peak with exactly 5 unit difference (boundary case)
    assert count_peaks([50, 45, 50]) == 1, "Exactly 5 units difference should count as valley"
    
    # Test 9: Multiple top peaks
    assert count_peaks([1, 10, 1, 10, 1]) == 2, "Two top peaks separated"
    
    # Test 10: Multiple bottom peaks
    assert count_peaks([50, 40, 50, 40, 50]) == 2, "Two bottom peaks separated"
    
    # Test 11: Mixed top and bottom peaks
    assert count_peaks([0, 10, 0, 50, 40, 50]) == 3, "One top peak and two bottom peaks"
    
    # Test 12: Almost a peak (difference < 5)
    assert count_peaks([10, 14, 10]) == 0, "Less than 5 units difference should not be a peak"
    
    # Test 13: Peak at different positions
    assert count_peaks([5, 5, 15, 5, 5]) == 1, "Peak in middle of plateau"
    
    # Test 14: Complex real-world sensor data
    assert count_peaks([20, 30, 20, 15, 25, 15, 20]) == 2, "Multiple peaks in realistic data"
    
    # Test 15: Longer list with single peak
    assert count_peaks([10, 10, 10, 25, 10, 10, 10]) == 1, "Single peak in long sequence"
    
    print("All test cases passed!")
