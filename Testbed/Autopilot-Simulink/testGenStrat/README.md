## Prerequisite

- MATLAB R2021b **[For Simulink Model]**

## Instructions to Run the Proposed Algorithms

### Simulink Model: Autopilot/AP

Open MATLAB and go to the `testGenStrat` main folder.

Add the `testGenStrat` folder and all of its subfolders to your MATLAB path:

```text
Right click on the folder > Add to Path > Selected Folders and Subfolders
```

Open the Autopilot/AP execution file:

```text
executeAPnewHCR.m
```

Inside `executeAPnewHCR.m`, set the appropriate values for `models` and `req` depending on the algorithm and Autopilot requirement you want to run.

For example, `models` can be set for the surrogate technique, ML-guided technique, or random search, and `req` is used to select the Autopilot requirement to be tested.

Run the following command in the MATLAB terminal:

```matlab
executeAPnewHCR
```
