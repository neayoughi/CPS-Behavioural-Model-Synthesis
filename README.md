# MELA: Machine Learning-Enhanced Passive Automata Learning

MELA is a passive automata-learning approach for cyber-physical systems (CPS) with numeric time-series inputs and outputs. It combines statistical machine learning and automata learning to derive interpretable Moore state machines from execution traces.

The repository contains the implementation, data, evaluation scripts, learned models, and verification artifacts for two case studies:

1. A network intrusion detection system (IDS) for DoS and DDoS traffic scenarios.
2. An autopilot system for ascent and descent flight scenarios.

MELA converts raw numeric traces into symbolic traces by selecting relevant variables and abstracting numeric values into discrete ranges. The resulting traces are then used to learn Moore machines. The learned models support conformance assessment, requirement verification, and behaviour exploration.

## Repository Structure

```text
MELA/
├── Code/
│   ├── IDS/
│   └── Autopilot/
├── Data/
│   ├── IDS/
│   └── Autopilot/
├── Evalution/
│   ├── IDS/
│   └── Autopilot/
├── Figures/
│   ├── IDS/
│   └── Autopilot/
├── Results/
│   ├── IDS/
│   └── Autopilot/
└── Testbed/
    ├── IDS/
    └── Autopilot-Simulink/
```



## MELA Workflow

MELA follows six main steps:

1. **Data generation**: Generates time-series inputs and executes the system under learning.
2. **Trace creation**: Samples time-series inputs and outputs into finite traces.
3. **Trace abstraction**: Selects relevant variables and maps numeric values to symbolic ranges.
4. **Automata learning**: Learns Moore state machines from abstract traces with passive automata learning.
5. **Conformance checking**: Evaluates learned models against test traces.
6. **Verification**: Checks temporal properties over the learned models with NuSMV.

## Case Study 1: IDS

### Overview

The IDS case study models the behaviour of an IDS-enabled router developed by RabbitRun Technologies. The IDS monitors network traffic and updates its state based on flow-level features. The testbed simulates local users, external users, normal traffic, DoS attacks, and DDoS attacks.

The IDS states are:

- `Safe`
- `Warning`
- `Tending Warning`
- `Tending Alert`
- `Alert`

The main goal is to learn state machines that show how normal and attack traffic move the IDS among these states.

### IDS Testbed

The IDS testbed consists of three virtual machines, each deployed on a separate laptop:

- `VM-left`: simulates local users.
- `VM-centre`: hosts the IDS-enabled RabbitRun router.
- `VM-right`: simulates external users and generates normal, DoS, and DDoS traffic.

The testbed scripts are available in:

```text
Testbed/IDS/
├── container.sh
├── hping.sh
└── hping_traffic.sh
```

The actual router implementation is proprietary and is not included in the repository.

### IDS Inputs and States

The IDS receives network-flow features such as:

- `num_flows`: total number of flows through the router.
- `num_unreplied`: number of flows with no reply from local users.
- `External User type`: normal user, DoS attacker, or DDoS attacker.

For the reported experiments, the following IDS configurations are used:

- `num_flows`
- `num_unreplied`
- `flow_unreplied`, which combines `num_flows` and `num_unreplied`

In all IDS configurations, `External User type` is retained because it distinguishes normal traffic from attack traffic.

### IDS Learning Sets

The IDS experiments use three learning sets:

- `DoS3`: DoS traces with three-state coverage.
- `DoS5`: DoS traces with five-state coverage.
- `DDoS`: DDoS traces with three-state coverage.

The learning sets are stored in:

```text
Data/IDS/Learning set/
├── DoS3.csv
├── DoS5.csv
└── DDoS.csv
```

### IDS Data and Results

IDS artifacts are organized as follows:

```text
Data/IDS/
├── Input/
├── Output/
├── Learning set/
├── Abstraction/
└── Trace/

Results/IDS/
├── LearnedModel/
├── RQ1/
└── RQ2/

Evalution/IDS/
├── RQ1/
└── RQ2/
```

- `Data/IDS/Input`: input data used for trace construction.
- `Data/IDS/Output`: IDS output data.
- `Data/IDS/Learning set`: learning sets used for automata learning.
- `Data/IDS/Abstraction`: abstracted data produced by MELA and BASELINE.
- `Data/IDS/Trace`: symbolic traces used for learning.
- `Results/IDS/LearnedModel`: learned Moore machines.
- `Results/IDS/RQ1`: complexity and conformance results.
- `Results/IDS/RQ2`: model-checking and behaviour-exploration results.

### IDS Code

IDS scripts are available in:

```text
Code/IDS/
├── TimeSeriesData.py
├── TraceCreation.py
├── TraceCreation_Passive.py
├── VariableSelection.py
├── DecisionTree.py
├── MELA_Abstraction.py
├── BASELINE_Abstraction.py
├── AutomataLearning.py
└── PTA_moore.py
```

Script purposes:

- `TimeSeriesData.py`: supports time-series data processing for IDS traces.
- `TraceCreation.py` and `TraceCreation_Passive.py`: create abstract traces from IDS data.
- `VariableSelection.py`: ranks variables with information gain.
- `DecisionTree.py`: learns decision-tree thresholds for numeric abstraction.
- `MELA_Abstraction.py`: produces MELA abstractions.
- `BASELINE_Abstraction.py`: produces expertise-based BASELINE abstractions.
- `AutomataLearning.py`: learns Moore machines from abstract traces.
- `PTA_moore.py`: builds PTA-based models for verification support.

## Case Study 2: Autopilot

### Overview

The autopilot case study uses a Simulink model of a De Havilland Beaver aircraft. The autopilot receives flight commands and adjusts the aircraft toward a target altitude. The experiments study two flight scenarios:

- `ascend`
- `descend`

The autopilot states are:

- `Nominal`
- `Caution`
- `Critical`

The goal is to learn state machines that capture how the autopilot moves the aircraft from higher-criticality states toward lower-criticality states under different commands.

### Autopilot Inputs and States

The main input variables used in the experiments are:

- `PitchWheel`
- `Throttle`
- `PWheel_Throttle`, which combines `PitchWheel` and `Throttle`

The requirement-referenced input is `Target Altitude`, which is fixed by the learning-set setting:

- `ascend`: traces where the aircraft climbs toward the target altitude.
- `descend`: traces where the aircraft descends toward the target altitude.

### Autopilot Data and Results

Autopilot artifacts are organized as follows:

```text
Data/Autopilot/
├── Input/
│   ├── raw/
│   └── processed/
├── Learning set/
├── Abstraction/
└── Trace/

Results/Autopilot/
├── LearnedModel/
├── RQ1/
└── RQ2/

Evalution/Autopilot/
├── RQ1/
└── RQ2/
```

The autopilot data folders contain separate subfolders for `ascend` and `descend`, and for the MELA and BASELINE methods.

### Autopilot Code

Autopilot scripts are available in:

```text
Code/Autopilot/
├── TraceCreation.py
├── MELA_Abstraction.py
├── Baseline_Abstraction.py
├── DecisionTree.py
├── AutomataLearning.py
└── Boxplots.py
```

Script purposes:

- `TraceCreation.py`: builds final trace CSV and TXT files for MELA and BASELINE.
- `MELA_Abstraction.py`: writes MELA level columns for each direction and configuration.
- `Baseline_Abstraction.py`: writes BASELINE level columns for each direction and configuration.
- `DecisionTree.py`: learns decision-tree rules for `PitchWheel`, `Throttle`, and `PWheel_Throttle`.
- `AutomataLearning.py`: learns Moore models from final traces and exports DOT models.
- `Boxplots.py`: creates the final accuracy boxplot.

Autopilot RQ2 scripts are available in:

```text
Evalution/Autopilot/RQ2/model_checking/
├── ModelChecking.py
├── build_gsm_smv_models.py
├── build_moore_pta_with_aalpy.py
├── build_pta_models_from_training_traces.py
├── build_pta_smv_models.py
├── run_gsm_nusmv_checks.py
├── smv_model_checking_core.py
└── ag_not_target_properties/
    └── evaluate_ag_not_target_properties.py
```

These scripts build NuSMV models from learned Moore machines and PTAs, run CTL checks, and summarize verification results.


## Requirements

The repository uses the following tools and libraries:

- Python 3.8 or later
- AALpy
- scikit-learn
- pandas
- matplotlib
- pydot
- NuSMV
- VirtualBox, Ubuntu, Kali Linux, hping3, and Metasploitable for the IDS testbed
- MATLAB/Simulink for the autopilot testbed

A typical Python setup is:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas scikit-learn matplotlib pydot aalpy
```

NuSMV must be installed separately and available from the command line for RQ2 model checking.

## Reproducing the Main Workflow

Run scripts from the repository root when possible. Some scripts contain fixed path assumptions, so paths may need to be adjusted if the repository is moved or renamed.

### IDS Workflow

1. Prepare or place IDS input and output data under `Data/IDS/`.
2. Create traces:

```bash
python Code/IDS/TraceCreation.py
```

3. Run variable selection and decision-tree abstraction:

```bash
python Code/IDS/VariableSelection.py
python Code/IDS/DecisionTree.py
python Code/IDS/MELA_Abstraction.py
python Code/IDS/BASELINE_Abstraction.py
```

4. Learn automata:

```bash
python Code/IDS/AutomataLearning.py
```

5. Run RQ1 evaluation:

```bash
python Evalution/IDS/RQ1/RQ1.py
```

6. Inspect RQ2 outputs under:

```text
Results/IDS/RQ2/
```

### Autopilot Workflow

1. Prepare autopilot data under `Data/Autopilot/`.
2. Create traces:

```bash
python Code/Autopilot/TraceCreation.py
```

3. Run abstraction:

```bash
python Code/Autopilot/DecisionTree.py
python Code/Autopilot/MELA_Abstraction.py
python Code/Autopilot/Baseline_Abstraction.py
```

4. Learn automata:

```bash
python Code/Autopilot/AutomataLearning.py
```

5. Run RQ1 evaluation:

```bash
python Evalution/Autopilot/RQ1/Evaluation.py
```

6. Run RQ2 model checking:

```bash
python Evalution/Autopilot/RQ2/model_checking/ModelChecking.py
```

## Evaluation Summary

The evaluation addresses two research questions.

### RQ1: Complexity and Conformance

RQ1 compares MELA with BASELINE, where BASELINE uses manually defined numeric abstractions. The comparison uses the same learning sets and test sets for both methods.

The reported metrics are:

- Number of states
- Number of transitions
- Alphabet size
- Accuracy on test traces

In the reported experiments, MELA produced smaller and more accurate automata than BASELINE on average. The paper reports an average 49% reduction in the number of states and transitions and an average 41.71% improvement in accuracy compared with expertise-based abstractions.

### RQ2: Verification and Behaviour Exploration

RQ2 uses the MELA-generated automata that meet the accuracy threshold. The learned Moore machines are translated to NuSMV and checked against CTL properties.

For the IDS, the CTL properties are derived from the expected staged response to attack and normal traffic. The IDS results report pass, fail, and vacuity outcomes for DoS and DDoS learning sets and for the `num_flows`, `num_unreplied`, and `flow_unreplied` configurations.

For the autopilot, the CTL properties are derived from the requirement that the aircraft moves toward the target altitude in a staged manner from `Critical` to `Caution` and then to `Nominal`.

RQ2 also studies IDS behaviours in the `Tending Warning` and `Tending Alert` states. These results show how the IDS behaves under low-, medium-, and high-flow traffic conditions.

## Figures

Selected figures are available in:

```text
Figures/IDS/
Figures/Autopilot/
```

Examples include:

- IDS testbed diagrams.
- IDS learned state-machine figures.
- Autopilot learned model figures.
- Accuracy boxplots for IDS and Autopilot.

## Data Availability and Proprietary Material

The repository provides scripts, trace creation and abstraction routines, evaluation code, learned models, and experimental artifacts that can be shared. The RabbitRun router implementation and any proprietary internal data are not included.

## Naming Conventions

The repository uses the following naming conventions:

- `MELA`: ML-based abstraction with passive automata learning.
- `BASELINE`: expertise-based abstraction with passive automata learning.
- `num_flows`: IDS flow-count configuration.
- `num_unreplied`: IDS unreplied-flow configuration.
- `flow_unreplied`: IDS joint flow and unreplied-flow configuration.
- `pitchwheel`: Autopilot pitch-wheel configuration.
- `throttle`: Autopilot throttle configuration.
- `pitchwheel_throttle`: Autopilot joint pitch-wheel and throttle configuration.
- `ascend`: Autopilot ascent setting.
- `descend`: Autopilot descent setting.


