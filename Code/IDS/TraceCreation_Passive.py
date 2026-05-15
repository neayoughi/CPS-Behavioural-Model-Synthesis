import pandas as pd

# Load the dataset
file_path = 'TimeSeriesData_DDoS.csv'  # Replace with your file path
df = pd.read_csv(file_path)

# Adjusting the code to maintain the desired format
traces = []
previous_inputs = []

for index, row in df.iterrows():
    current_input = f"'{row['attack_type']},{row['Port']},{row['Protocol']},{row['packet_size']},{row['Flow']},{row['Unreplied']}'"
    input_data = ' , '.join(previous_inputs + [current_input])
    traces.append(f"({input_data}, '{row['State']}')")
    previous_inputs.append(current_input)

# Save the final traces to a text file
formatted_output_file = 'Trace_DDoS_Passive.txt'  # Replace with your desired output path
with open(formatted_output_file, 'w') as file:
    file.write('[')
    file.write(',\n'.join(traces))
    file.write(']')

# The path to the output file
print(formatted_output_file)

