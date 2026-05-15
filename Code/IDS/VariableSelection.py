import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.preprocessing import LabelEncoder
import numpy as np

# Load the dataset
file_path = 'Timestamps_DDoS.csv'
data = pd.read_csv(file_path)


# Selecting relevant features and target
features = data[['packet_size', 'Port', 'Protocol', 'attack_type', 'Flow', 'Unreplied']].copy()
target = LabelEncoder().fit_transform(data['State'])

# Converting categorical data to numerical
features['Protocol'] = features['Protocol'].astype('category').cat.codes
features['attack_type'] = features['attack_type'].astype('category').cat.codes

# Handling NaN and infinite values in features (If you have Error)
features.replace([np.inf, -np.inf], np.nan, inplace=True)  # Replace infinities with NaN
features.fillna(features.mean(), inplace=True)  # Replace NaNs with the mean of each column

# Ensure that all columns in 'features' are numeric
assert all(features.dtypes != 'object'), "All features must be numeric"

# Calculating Information Gain for each feature
info_gain = mutual_info_classif(features, target)

# Creating a DataFrame to display the results
info_gain_df = pd.DataFrame({'Feature': features.columns, 'Information Gain': info_gain})
info_gain_df.sort_values(by='Information Gain', ascending=True)
print(info_gain_df)










