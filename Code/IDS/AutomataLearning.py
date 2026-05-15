import ast
from pathlib import Path
from aalpy.learning_algs import run_RPNI


def load_traces_from_file(file_path: str):
    return ast.literal_eval(Path(file_path).read_text())


trace_file_path = "MELA/DDoS/Trace_Top-2.txt"

traces = load_traces_from_file(trace_file_path)

# GSM-RPNI in your AALpy is selected via algorithm="gsm"
learned_model = run_RPNI(
    traces,
    automaton_type="moore",
    algorithm="gsm",
    input_completeness=None,
    print_info=True,
)

# If you want an input-complete model for later steps (model checking, etc.)
# learned_model.make_input_complete("sink_state")

print("Input complete:", learned_model.is_input_complete())
print("Input alphabet:", learned_model.get_input_alphabet())
print(learned_model)

learned_model.visualize(file_type="dot", path="LearnedModel_DDoS.dot")
learned_model.visualize(file_type="pdf", path="LearnedModel_DDoS.pdf")
learned_model.save()