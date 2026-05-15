import random

# Read the content of the file
file_path = 'Test set/5sDOS/set3/Trace_5s_dos_Un_Algorithm.txt'
with open(file_path, 'r') as file:
    content = file.read()

# Extracting the elements from the given sequence in the file content
# Assuming the sequence format is consistent throughout the file
sequence_str = content.split('((')[1].split('))')[0]
elements = sequence_str.replace("'", "").replace(" ", "").split(',')

# Generating 50 sequences with random sizes
random_sequences = []
index = int(0.5 * len(elements))
print(f"len(elements): {len(elements)}")

for _ in range(50):
    # Randomly choosing a size for the sequence #len(elements)
    size = random.randint(5, index)
    # Selecting a subsequence of the chosen size
    subsequence = elements[:size]
    # Formatting the subsequence as a string and adding it to the list
    random_sequences.append(str(subsequence))

# Joining the sequences with a newline character to prepare for writing to a file
sequences_text = "\n".join(random_sequences)

# Preparing the path for the new file
output_file_path = 'Test set/5sDOS/set3/2nd/Sequences_5s_dos_Un_Algorithm_len50_2.txt'

# Writing the sequences to a new file
with open(output_file_path, 'w') as file:
    file.write(sequences_text)
