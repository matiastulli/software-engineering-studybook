"""
To prevent confusion between multiples of 1000 bytes and multiples of 1024 bytes, the terms “kibibyte”, “mebibyte”, etc. were invented.

* One kibibyte (abbreviated KiB) corresponds to 1024 bytes.
* One mebibyte (MiB) corresponds to (1024 por 1024 = 1048576) bytes.

Given a quantity of bytes:

* If it is lower than one KiB, return it as a string.
* If it is between one KiB (included) and one MiB (excluded), convert it to KiB, round it down, and return it followed by a space and the text “KiB”.
* If it is greater or equal than one MiB, convert it to MiB, round it down and return it followed by a space and the text “MiB”.

You will never have values greater than 10⁹ bytes, so you will never reach the “gibibyte”.
"""



def format_bytes(num_bytes: int) -> str:
    """
    Convert bytes to human-readable format (bytes, KiB, or MiB).
    
    Args:
        num_bytes: Number of bytes to format
        
    Returns:
        Formatted string representation
    """
    Kib = 1024
    Mib = 1024 * 1024

    if num_bytes < Kib:
        return str(num_bytes)
    elif num_bytes >= Kib and num_bytes < Mib:
        return str(int(num_bytes / Kib)) + " KiB"
    else:
        return str(int(num_bytes / Mib)) + " MiB"
     



# TEST CASES
if __name__ == "__main__":
    # Test 1: Less than 1 KiB - return as string
    assert format_bytes(0) == "0"
    assert format_bytes(1) == "1"
    assert format_bytes(512) == "512"
    assert format_bytes(1023) == "1023"
    
    # Test 2: Exactly 1 KiB
    assert format_bytes(1024) == "1 KiB"
    
    # Test 3: Between 1 KiB and 1 MiB - round down
    assert format_bytes(1025) == "1 KiB"
    assert format_bytes(2048) == "2 KiB"
    assert format_bytes(5000) == "4 KiB"  # 5000/1024 = 4.88... rounds down to 4
    assert format_bytes(10240) == "10 KiB"
    assert format_bytes(1048575) == "1023 KiB"  # Just before 1 MiB
    
    # Test 4: Exactly 1 MiB
    assert format_bytes(1048576) == "1 MiB"
    
    # Test 5: Greater than 1 MiB - round down
    assert format_bytes(1048577) == "1 MiB"
    assert format_bytes(2097152) == "2 MiB"  # Exactly 2 MiB
    assert format_bytes(5242880) == "5 MiB"
    assert format_bytes(1073741823) == "1023 MiB"  # Large value
    
    print("All tests passed!")


