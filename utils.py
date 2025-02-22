import math

def get_delta_color(change):
    """
    Determines the color for the delta indicator.
    Always returns "off" to keep metrics in black.
    """
    return "off"  # No color for all changes

def format_percentage(value):
    """
    Formats the percentage change with appropriate sign and decimal places.
    """
    if math.isclose(value, 0, abs_tol=1e-4):
        return "0.00%"
    return f"{value:+.2f}%"  # `+` ensures explicit sign for positives

# Example usage
if __name__ == "__main__":
    test_values = [0.0023, -0.0045, 0.0, -0.00005, 0.01]

    for val in test_values:
        color = get_delta_color(val)
        formatted = format_percentage(val * 100)  # Assuming values are in decimal (e.g., 0.01 = 1%)
        print(f"Change: {val:.5f}, Color: {color}, Formatted: {formatted}")