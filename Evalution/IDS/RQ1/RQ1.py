import ast
from aalpy.learning_algs import run_RPNI


# Load your trace data from a file
def load_traces_from_file(file_path):
    with open(file_path, 'r') as file:
        file_content = file.read()
        traces = ast.literal_eval(file_content)
        return traces


# Load the sequences from the generated file
def load_sequences_from_generated_file(generated_file_path):
    with open(generated_file_path, 'r') as file:
        sequences = file.readlines()
        # Convert each line to a list of elements
        sequences = [ast.literal_eval(line.strip()) for line in sequences]
        return sequences


# Path to your trace file
trace_file_path = 'Trace_DDoS.txt'

# Load the traces
traces = load_traces_from_file(trace_file_path)

# Run RPNI algorithm
learned_model = run_RPNI(traces, automaton_type='moore', input_completeness=None, print_info=True)
learned_model.make_input_complete('sink_state')
print(learned_model)
learned_model.visualize(file_type='dot', path='Test_trace_DDoS.dot')
learned_model.visualize(file_type='pdf', path='Test_Trace_DDoS.pdf')

# Path to your generated sequences file
generated_sequences_file_path = 'Test_Sequences_DDoS.txt'

# Load the sequences
sequences = load_sequences_from_generated_file(generated_sequences_file_path)

# # Execute each sequence and write the results to the output file
# with open(output_file_path, 'w') as output_file:
#     for sequence in sequences:
#         try:
#             execute_sequence = learned_model.execute_sequence(learned_model.initial_state, sequence)
#             # Format the output
#             output = execute_sequence if execute_sequence is not None else 'None'
#         except KeyError:
#             # Handle the case where the sequence contains an unknown input
#             output = 'fail'
#
#         output_file.write(str(output) + '\n')

def calculate_accuracy(output_file_path, sequences, learned_model):
    total_sequences = len(sequences)
    pass_count = 0

    with open(output_file_path, 'w') as output_file:
        for sequence in sequences:
            try:
                execute_sequence = learned_model.execute_sequence(learned_model.initial_state, sequence)
                if 'sink_state' in execute_sequence:
                    output = 'fail due to sink_state'
                else:
                    output = execute_sequence if execute_sequence is not None else 'None'
                    pass_count += 1  # Increment pass count if sequence is complete and has no sink_state
            except KeyError as e:
                problematic_transition = str(e).strip("'")
                output = f'fail due to transition: {problematic_transition}'

            output_file.write(str(output) + '\n')

    # Calculate accuracy
    accuracy = (pass_count / total_sequences) * 100
    print(f"pass_count: {pass_count} \n")
    print(f"total_sequences: {total_sequences}")
    return accuracy


# Example usage
output_file_path = 'Test set/5sDOS/set3/execute_sequence_DDoS.txt'
accuracy = calculate_accuracy(output_file_path, sequences, learned_model)
print(f"Accuracy: {accuracy}%")
print(learned_model.get_input_alphabet())
