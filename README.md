# Project Autonomax
This repository contains the implementation of an MILP problem developed as part of the course TIØ4150 Industrial Optimization and Decision Support. The problem was formulated and solved by utilizing the [Gurobi Solver](https://www.gurobi.com).

## Requirements
- [Jupyter](https://jupyter.org)
- [Gurobi Solver](https://www.gurobi.com) with license file. Academic license available for [free](https://www.gurobi.com/academia/academic-program-and-licenses/)

## How to run
If Jupyter and Gurobi is available, running should be as simple as opening `project-autonomax.ipynb` and executing all cells

## Important files
### `project-autonomax.ipynb`
The main script. This relies on functionality implemented in other modules to provide a succinct way of running the optimization model and inspecting the result. It makes it easy to change input parameters such as `Z` and `NC`.

### `problem.py`
This contains the main problem parameters provided for the assignment. It defines:
- The names of the 41 cities
- The distance between each pair of cities
- The demand at each city in each of the three scenarios

### `model.py`
This defined the mixed-integer linear program. It provides the class `Autonomax`, which constructs the model corresponding to the provided input configuration. The class provides access to the underlying Gurobi model, and all of the constraints and variables. In addition, it provides convenvient methods to show current model solution and to visualize the model's constraint matrix.

### `visualization.py`
Provides visualizaiton of problem solutions
