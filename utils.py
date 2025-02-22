def get_delta_color(change):
    """
    Determines the color for the delta indicator based on the change value.
    Returns:
    - "normal" for positive changes (green)
    - "inverse" for negative changes (red)
    - "off" for no change (gray)
    """
    if abs(change) < 0.0001:  # Handle floating point comparison
        return "off"  # Gray
    elif change > 0:
        return "normal"  # Green
    else:
        return "inverse"  # Red

def format_percentage(value):
    """
    Formats the percentage change with appropriate sign and decimal places.
    """
    if abs(value) < 0.0001:  # Handle floating point comparison
        return "0.00%"
    if value < 0:
        return f"{value:.2f}%"
    return f"+{value:.2f}%"