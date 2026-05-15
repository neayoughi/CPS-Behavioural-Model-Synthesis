import pandas as pd

# Load the dataset
df = pd.read_csv('TimeSeriesData_DDoS.csv')

def categorize_value(value, thresholds):
    """Categorize value into 'Low', 'Med', or 'High' based on thresholds."""
    if value <= thresholds[0]:
        return 'Low'
    elif value <= thresholds[1]:
        return 'Med'
    else:
        return 'High'

columns_to_categorize = ['packet_size', 'Flow', 'Unreplied']
for col in columns_to_categorize:
    col_min, col_max = df[col].min(), df[col].max()
    col_range = col_max - col_min
    thresholds = [col_min + col_range/3, col_min + 2*col_range/3]
    print(thresholds)

    # Categorize and add to a new column
    df[f'{col}_Category'] = df[col].apply(lambda x: categorize_value(x, thresholds))

# Save the updated dataset
df.to_csv('Baseline_Abstraction_DDoS.csv', index=False)