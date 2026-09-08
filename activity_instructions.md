# Especificaciones del Proyecto / Prompt para Kiro (M4)

## Purpose (Propósito)
The purpose of this activity is to integrate the previous stages of the project and develop, implement, and evaluate an **intelligent Multi-Agent System solution** for the logistics environment.

### Project Progression
1. **M2: Environment**
   $$\text{Environment} \rightarrow \text{Logistics Zones} \rightarrow \text{Racks} \rightarrow \text{Pallets} \rightarrow \text{Stations} \rightarrow \text{Traversable Areas}$$
   *In M2, each team developed and customized the logistics environment.*

2. **M3: Multi-Agent Interaction**
   $$\text{Agents} \rightarrow \text{Missions} \rightarrow \text{Communication} \rightarrow \text{Negotiation} \rightarrow \text{Collaboration} \rightarrow \text{Action}$$
   *In M3, autonomous AGV agents were introduced into the environment, including basic mechanisms for interaction.*

3. **M4: Intelligent Solution**
   $$\text{M2: Environment} \rightarrow \text{M3: Multi-Agent Interaction} \rightarrow \text{M4: Intelligent Solution}$$
   *In M4, teams must integrate these components and propose an actual solution to improve the operation of the AGV fleet using one or more intelligent techniques studied in class.*

---

## Core Objective
The objective is no longer simply to demonstrate that the agents can interact. Teams must now investigate:
> **Can the decisions made by the AGVs be improved, and can this improvement be demonstrated through simulation results?**

---

## 1. Integration of M2 and M3
M4 must build directly upon the previous work. Teams should **not** start a completely independent simulation.

The submitted notebook must contain the relevant components developed in M2 and M3 so that the complete system can be executed and evaluated from the same notebook.

### Environment from M2 (At minimum)
* warehouse dimensions;
* racks;
* pallet storage positions;
* inbound/production areas;
* outbound/truck dock areas;
* charging stations;
* traversable areas;
* obstacles or restricted areas.

### Multi-Agent System from M3 (At minimum)
* multiple AGV agents;
* individual AGV states;
* multiple pallets;
* transportation missions;
* Mission Manager;
* communication;
* collaboration;
* negotiation;
* battery behavior;
* agent movement;
* dynamic simulation;
* visualization/animation.

### Resulting Architecture Formula
$$\text{Environment} + \text{Agents} + \text{Missions} + \text{Interaction} + \text{Decision Strategy} = \text{Complete MAS}$$

---

## 2. Problem Identification
Before implementing an intelligent technique, each team must clearly identify **what problem they are attempting to improve**.

Do **not** begin with:
> *"We are going to use Q-Learning."*

Instead, begin with a problem. For example:
* *"Our AGVs frequently select missions that require unnecessary travel."*
* *"AGVs experience congestion when several agents attempt to use the same corridor."*
* *"The current negotiation mechanism does not adequately consider battery level and workload."*

Then select an appropriate technique.

### Expected Workflow
$$\text{Problem} \rightarrow \text{Technique} \rightarrow \text{Implementation} \rightarrow \text{Evaluation}$$

and **not** simply:

$$\text{Technique} \rightarrow \text{Implementation}$$

---

## 3. Intelligent Solution
Each team must implement **at least one technique studied in class** to improve the behavior of the Multi-Agent System.

Teams may use a learning-based, heuristic, probabilistic, or combined approach.

### Heuristic Approach
Teams may develop a heuristic decision rule based on variables such as:

$$H_{i,m} = w_d D_{i,m} + w_b B_i + w_q Q_i + w_p P_m$$

where, depending on the team's definition:
* $D_{i,m}$: distance between AGV $i$ and mission $m$;
* $B_i$: battery condition;
* $Q_i$: workload or queue-related factor;
* $P_m$: mission priority;
* $w_d, w_b, w_q, w_p$: weights selected by the team.

The complete formula must be defined and explained in the notebook.

A heuristic could be used for:
* mission selection;
* AGV bidding;
* route selection;
* charging priority;
* congestion avoidance;
* mission prioritization.

Teams are free to propose their own heuristic, provided its variables and reasoning are clearly explained.

---

## 4. Distinguish Routing from Decision Making
Teams must clearly explain the purpose of each algorithm used.

For example:
$$\text{A}^*/\text{Dijkstra} \rightarrow \text{How should the AGV reach the destination?}$$

while:
$$\text{Heuristic / MDP / Q-Learning} \rightarrow \text{What should the AGV decide?}$$

Students should avoid presenting a routing algorithm alone as the complete intelligent Multi-Agent solution.

---

## 5. Baseline Strategy
Each team must maintain or implement a **baseline strategy**.

The baseline represents the system before the proposed intelligent improvement.

The baseline must operate **without** the proposed intelligent coordination/decision improvement and should provide a reasonable reference for comparison.

For example, a baseline may use:
* first available AGV;
* nearest available AGV;
* first available mission;
* fixed routing rules;
* simple predefined charging behavior;
* no mission reassignment;
* no advanced negotiation strategy.

The baseline should remain simple and clearly documented.

---

## 6. Proposed Intelligent Strategy
The proposed solution should replace or improve a clearly identified component of the baseline.

For example:
$$\text{Baseline: } \text{AGV}^* = \arg\min_i D_{i,m}$$

may select the closest AGV.

An improved heuristic could consider:
$$U_{i,m} = -w_d D_{i,m} + w_b B_i - w_L L_i - w_C C_i$$

where:
* $D_{i,m}$: distance to the mission;
* $B_i$: battery level;
* $L_i$: current workload;
* $C_i$: estimated congestion or route cost.

The preferred AGV becomes:
$$\text{AGV}^* = \arg\max_i U_{i,m}$$

The exact method is open to each team.

What matters is that the notebook clearly identifies:
$$\text{Baseline } \text{ vs. } \text{ Proposed Solution}$$

---

## 7. Fair Experimental Comparison
The baseline and proposed strategy must be evaluated under **equivalent simulation conditions**.

Both strategies should use, as much as possible:
* the same warehouse layout;
* the same number of AGVs;
* the same initial AGV positions;
* the same initial battery levels;
* the same missions;
* the same pallet positions;
* the same simulation duration;
* the same dynamic events;
* the same pedestrian/obstacle conditions.

Conceptually:
$$\text{Conditions}_{\text{baseline}} = \text{Conditions}_{\text{proposed}}$$

The principal difference should be the decision strategy being evaluated.

If random behavior is used, teams should control the random seed whenever possible.

For example:
```python
random.seed(42)
np.random.seed(42)
```

This helps make the comparison reproducible.

---

## 8. Dynamic Events
The final simulation should demonstrate that the proposed strategy operates in a dynamic environment.

At least one relevant dynamic condition should be included, such as:
* pedestrians crossing AGV routes;
* temporary route obstruction;
* another AGV occupying a required path;
* temporary station unavailability;
* changing mission availability.

Low battery does not need to be artificially generated as an external event because it should emerge naturally from AGV movement and energy consumption.

The objective is to demonstrate that the solution operates under changing conditions rather than only in a completely static warehouse.

---

## 9. Communication, Collaboration, and Negotiation
The intelligent strategy must remain part of a **Multi-Agent System**.

Therefore, teams must preserve and demonstrate the fundamental MAS elements developed in M3.

The notebook should make it possible to identify:

### Communication
What information do agents exchange?

Examples:
$$\text{Message} = (\text{MissionID}, \text{Origin}, \text{Destination}, \text{Priority})$$

or information concerning:
* battery;
* availability;
* route occupancy;
* mission status;
* charging requirements.

### Collaboration
How does one AGV's behavior contribute to the operation of the fleet?

### Negotiation
How do agents resolve situations in which multiple AGVs are interested in the same mission or shared resource?

The final solution should not transform the Mission Manager into a centralized controller that makes all decisions for the AGVs.

---

## 10. Mission Manager Constraint
The Mission Manager may:
* generate or receive missions;
* store pending missions;
* publish available missions;
* record mission acceptance;
* update mission states;
* record completed missions.

However:
$$\text{Mission Manager} \neq \text{Centralized Decision Maker}$$

The Mission Manager should **not determine which AGV must execute a mission**.

That decision should arise from the behavior and interaction of the AGV agents.

---

## 11. Performance Metrics
Teams must quantitatively evaluate their solution.

At minimum, report:

### 1. Missions completed per unit of time
$$\text{Throughput} = \frac{N_{\text{completed}}}{T_{\text{simulation}}}$$

where $N_{\text{completed}}$ is the number of completed missions and $T_{\text{simulation}}$ is the simulation duration.

### 2. Average mission execution time
$$\overline{T}_{\text{mission}} = \frac{1}{N} \sum_{k=1}^{N} \left(T_k^{\text{complete}} - T_k^{\text{start}}\right)$$

This measures how long missions require on average.

### 3. AGV utilization
A simple utilization measure can be:

$$\text{Utilization}_i = \frac{T_i^{\text{active}}}{T_{\text{simulation}}} \times 100\%$$

where $T_i^{\text{active}}$ represents the time AGV $i$ spends performing productive activities.

Teams may additionally report:
* distance traveled;
* energy/battery consumption;
* waiting time;
* number of charging events;
* route conflicts;
* congestion;
* missions rejected;
* missions pending;
* number of replanning events;
* idle time.

Additional metrics are encouraged when they directly support the team's proposed solution.

---

## 12. Visualization and Animation
The final notebook must contain dynamic visual evidence of the system operating.

The animation should clearly show, when applicable:
* warehouse boundaries;
* racks;
* pallet storage positions;
* pallets;
* inbound/production areas;
* outbound/truck dock areas;
* charging stations;
* AGVs;
* AGV identifiers;
* AGV status;
* battery level;
* obstacles;
* pedestrians;
* mission execution.

AGVs should respect the physical restrictions of the environment.

For example:
$$\text{Rack Cells} \rightarrow \text{Non-Traversable}$$

and dynamic obstacles should influence AGV behavior when appropriate.

The visualization should make the operation of the proposed solution understandable without requiring the evaluator to inspect every line of code.

---

## 13. Explain the Intelligent Behavior
Each team must identify exactly **where intelligence enters the system**.

A useful architecture is:

$$\text{Perception} \rightarrow \text{State} \rightarrow \text{Decision} \rightarrow \text{Communication} \rightarrow \text{Action} \rightarrow \text{Environment}$$

Teams should explain:
1. What does the AGV perceive?
2. What information constitutes its state?
3. What decisions can it make?
4. What information does it communicate?
5. How does it interact with other AGVs?
6. Which algorithm influences its decision?
7. What action is produced?
8. How does the environment change as a consequence?

---

## 14. Required Analysis
At the end of the notebook, include a Markdown section answering the following questions:

1. What specific problem did your team identify in the M3 implementation?
2. What intelligent technique did you select?
3. Why is this technique appropriate for the identified problem?
4. What is the state/information available to each AGV?
5. What decisions/actions can each AGV make?
6. If applicable, what reward, utility, heuristic, or probability model did you define?
7. Provide and explain the complete formula(s) used by your solution.
8. How do AGVs communicate?
9. How do AGVs negotiate or collaborate?
10. How does your proposed strategy differ from the baseline?
11. How did you ensure that the baseline and proposed strategy were tested under equivalent conditions?
12. What metrics did you use?
13. Did the proposed strategy improve the system? Support your answer with numerical results.
14. Under which conditions did your strategy perform well?
15. Under which conditions did it perform poorly?
16. What limitations remain in the current implementation?
17. What would you improve if additional development time were available?

---

## 15. Scope of M4
M4 should integrate the complete progression of the project:

$$\underbrace{\text{Environment}}_{\text{M2}} + \underbrace{\text{Agents} + \text{Interaction}}_{\text{M3}} + \underbrace{\text{Intelligent Strategy}}_{\text{M4}}$$

The expected development process is:

$$\text{Environment} \rightarrow \text{Agents} \rightarrow \text{Missions} \rightarrow \text{Communication} \rightarrow \text{Negotiation} \rightarrow \text{Baseline} \rightarrow \text{Intelligent Strategy} \rightarrow \text{Simulation} \rightarrow \text{Evaluation}$$

The objective is **not** to use every technique studied in class.

A well-designed implementation using one appropriate technique, supported by a fair experimental comparison, is preferable to several algorithms without a clear purpose.

---

## 16. Deliverables
This is a group assignment. Each team must submit in Canvas:

1. **Google Colab link** and/or `.ipynb` notebook containing the complete integrated simulation.
2. The relevant **M2 environment** components.
3. The relevant **M3 Multi-Agent** components, including AGVs, missions, communication, collaboration, and negotiation.
4. The **baseline strategy**.
5. The implemented **intelligent solution** using at least one learning, heuristic, and/or probabilistic technique studied in class.
6. **Complete explanation** of the selected technique and formulas.
7. **Dynamic simulation** with animation/visualization.
8. **Evidence** of at least one relevant dynamic condition or event.
9. **Performance metrics** for both the baseline and proposed strategy.
10. **Tables and/or plots** comparing the results.
11. The required **Markdown analysis** and conclusions.
12. A **short section** identifying the remaining limitations and the elements that will be presented in the final report and presentation.

*The notebook must execute from beginning to end and should be clearly organized into sections.*
