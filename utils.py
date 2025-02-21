def get_delta_color(change):
    """
    Determines the color for the delta indicator based on the change value.
    """
    if change > 0:
        return "normal"  # Green
    elif change < 0:
        return "inverse"  # Red
    return "off"  # Gray

def format_percentage(value):
    """
    Formats the percentage change with appropriate sign and decimal places.
    """
    if value == 0:
        return None
    return f"{'+' if value > 0 else ''}{value:.2f}%"
