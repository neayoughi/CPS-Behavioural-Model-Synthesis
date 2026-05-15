import pandas as pd

def categorize_packet_size(packet_size):
    """
    Categorizes the packet size into different classes based on the decision tree.

    Args:
    packet_size (float): The size of the packet.

    Returns:
    str: The category of the packet.
    """
    # if packet_size <= 10.50:
    #     return 'Low'
    # elif 10.50 < packet_size <= 406.50:
    #     return 'Medium'
    # elif 406.50 < packet_size <= 452.50:
    #     return 'Medium-High'
    # elif packet_size >= 452.50:
    #     return 'High'

def categorize_unreplied(unreplied):
    """
    Categorizes the 'Unreplied' feature based on the decision tree intervals.

    Args:
    unreplied (float): The value of the 'Unreplied' feature.

    Returns:
    str: The category of the 'Unreplied' feature.
    """
    if unreplied <= 400.50:
        return "Low"
    elif 400.50 < unreplied <= 4259.50:
        return "Med"
    elif unreplied > 4259.50:
        return "High"

def categorize_flow(flow):
    """
    Categorizes the 'Flow Total' feature based on the decision tree intervals.

    Args:
    flow_total (float): The value of the 'Flow Total' feature.

    Returns:
    str: The category of the 'Flow Total' feature.
    """
    if flow <= 341:
        return "Low"
    elif 341 < flow <= 3999:
        return "Med"
    elif flow > 3999:
        return "High"


# Load the dataset
file_path = 'TimeSeriesData_DDoS.csv'
df = pd.read_csv(file_path)

# Apply the function to the  column and create a new 'Label' column
df['Label'] = df['Flow'].apply(categorize_flow)
df['Label'] = df['Unreplied'].apply(categorize_unreplied)

# Save the updated dataframe to a new CSV file
updated_file_path = 'Abstraction_DDoS.csv'
df.to_csv(updated_file_path, index=False)

