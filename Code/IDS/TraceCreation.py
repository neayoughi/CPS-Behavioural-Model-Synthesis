import pandas as pd

def simplify_attack_type(attack_type, label):
    # """ Simplifies the attack type and label into a shorter format. """
    # if not isinstance(attack_type, str) or not isinstance(label, str):
    #     return "Invalid"  # Return a placeholder or handle as needed
    attack_short = attack_type[1]  # First letter of attack type
    # attack_short = attack_type
    label_short = label[0]         # First letter of label
    # label_short = label
    return f"{attack_short}{label_short}"

def simplify_state(state):
    """ Simplifies the state into a shorter format. """
    # if not isinstance(state, str):
    #     return "Unknown"  # Return a placeholder for non-string values

    if state == "Safe":
        return "Safe"
    elif state == "WARNING!":
        return "Warning"
    elif state == "ALERT!":
        return "Alert"
    elif state == "Tending Warning":
        return "TW"
    elif state == "Tending Alert":
        return "TA"
    else:
        return state

# Load your dataset
df = pd.read_csv('Abstraction_DDoS.csv')

df['attack_type'] = df['attack_type'].astype(str)
df['State'] = df['State'].astype(str)
df['Label'] = df['Label'].astype(str)

# Simplify attack type and label, and state
df['Simplified_Attack'] = df.apply(lambda row: simplify_attack_type(row['attack_type'], row['Label']), axis=1)
df['Simplified_State'] = df['State'].apply(simplify_state)

# Efficiently creating the continuous trace
continuous_trace = []
for i in range(1, len(df) + 1):
    input_sequence = tuple(df['Simplified_Attack'].iloc[:i])
    output_alphabet = df['Simplified_State'].iloc[i - 1]
    continuous_trace.append((input_sequence, output_alphabet))

# Writing the trace to a text file
output_file_path = 'Trace_DDoS.csv.txt'
with open(output_file_path, 'w') as file:
    file.write("[\n")  # Add "[" at the beginning
    for i, item in enumerate(continuous_trace):
        file.write(f"{item}")
        if i < len(continuous_trace) - 1:
            file.write(",\n")
    file.write("\n]")  # Add "]" at the end

