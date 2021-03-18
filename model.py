from dataclasses import dataclass
from typing import List
from itertools import product, combinations
import gurobipy as gp
from gurobipy import GRB, quicksum


@dataclass
class Config:
    # The set of cities
    cities: List[str]
    # The distances between two cities. In other words, `distances[i, j]` is the distance between city `i` and city `j`
    distances: List[List[float]]
    # The demand from a certain city.
    demand: List[float]
    # The number of core cities
    core_city_count: int
    # Whether or not the core ought to be a cycle or a path
    core_net_is_cycle: bool


def normalize(i, j):
    assert i != j
    return (i, j) if i < j else (j, i)


def non_zero(items):
    for (key, v) in items.items():
        if abs(v.x) > 1e-9:
            yield key


class Autonomax:
    def __init__(self, config: Config, name='autonomax'):
        # The underlying Gurobi model we're building
        model = gp.Model(name)

        # Commonly used derived sets and parameters
        demand = config.demand
        D = config.distances
        NC = config.core_city_count
        Z = 1 if config.core_net_is_cycle else 0
        C = len(config.cities)
        CITIES = list(range(C))
        EDGES = list(combinations(CITIES, r=2))

        # There is exactly one control center,
        is_control_center = model.addVars(
            CITIES, vtype=GRB.BINARY, name='is-control-center')
        model.addConstr(quicksum(is_control_center[c] for c in CITIES) == 1)

        # Whether or not the edge between city `i` and `j` is part of the core net
        is_core_edge = model.addVars(
            EDGES, vtype=GRB.BINARY, name='is-core-edge')

        # Whether or not a city `i` is part of the core net
        is_core_city = model.addVars(C, vtype=GRB.BINARY, name='is-core-city')

        # The control center is required to be one of the core cities
        model.addConstrs(
            (is_core_city[i] >= is_control_center[i] for i in CITIES),
            name='control-center-directly-connected'
        )

        # Force cc to 0 if a city has no adjacent core edges
        model.addConstrs(
            (is_core_city[i] <= sum(is_core_edge[normalize(i, j)]
             for j in CITIES if j != i) for i in CITIES),
            name='core-city-ub'
        )

        # Force cc to 1 if a city has an adjacent core edge
        # model.addConstrs(
        #    (is_core_city[i] >= is_core_edge[normalize(i, j)]
        #    for i, j in product(CITIES, repeat=2) if i != j),
        #    name='core-city-lb'
        # )

        # A cycle has |V| = |E|. A path has |V| = |E| + 1
        model.addConstr(sum(is_core_city[i] for i in CITIES) == sum(
            is_core_edge[i, j] for i, j in EDGES) + 1 - Z)

        # Ensure that all core nodes have at most degree 2
        model.addConstrs(
            (2 * is_core_city[i] >= sum(is_core_edge[normalize(i, j)]
             for j in CITIES if j != i) for i in CITIES),
            name='disallow-core-tree',
        )

        # Ensure the number of core cities equals NC
        model.addConstr(
            sum(is_core_city[i] for i in CITIES) == NC,
            name='exactly-nc-core-cities'
        )

        # The number of timesteps we have to ensure connectedness is given
        # by the number of core cities for which we have to ensure connectedness
        T = NC

        is_connected_step = model.addVars(
            C, T, vtype=GRB.BINARY, name='is-connected-step')
        is_connectable_step = model.addVars(C, C, range(
            1, T), vtype=GRB.BINARY, name='is-connectable-step')

        # At timestep 0, the control center is the only connected city
        model.addConstrs(
            (is_connected_step[i, 0] == is_control_center[i] for i in CITIES),
            name='control-center-is-connected',
        )

        # A city `i` is connectable to a city `j` at time `t` if (i, j) ∈ core edges and `j`
        # is connected at time `t - 1`
        model.addConstrs(
            (2 * is_connectable_step[i, j, t] <= is_connected_step[i, t - 1] + is_connected_step[j,
             t - 1] + is_core_edge[i, j] for t, (i, j) in product(range(1, T), EDGES)),
            name='is-connectable'
        )

        # At timestep n, a city can be marked as connected if it has a core edge to a city
        # that was set as connected on timestep (n - 1)
        model.addConstrs(
            (is_connected_step[i, t] <= sum(is_connectable_step[(*normalize(i, j), t)]
             for j in CITIES if j != i) for t, i in product(range(1, T), CITIES)),
            name='is-connected-timestep'
        )

        # Ensure that all core cities are connected at some timestep
        model.addConstrs(
            (sum(is_connected_step[i, t] for t in range(
                T)) == is_core_city[i] for i in CITIES),
            name='connected-graph'
        )

        # How much (directed) demand is sent along an edge between two cities
        flow = model.addVars(EDGES, lb=-sum(demand),
                             ub=sum(demand), name='flow')
        abs_flow = model.addVars(EDGES, ub=sum(demand), name='abs-flow')
        model.addConstrs(
            (abs_flow[e] == gp.abs_(flow[e]) for e in EDGES)
        )
        # What direction a flow is sent in. For i < j: 1 = forward (i -> j), 0 = backward (j -> i)
        # direction = model.addVars(
        #    EDGES, vtype=GRB.BINARY, name='flow-direction')

        # We can only run flow in a single direction
        # model.addConstrs(
        #    (flow[i, j] <= sum(demand) * direction[i, j] for (i, j) in EDGES),
        #    name='flow-dir-forward'
        # )

        # We can only run flow in a single direction
        # model.addConstrs(
        #    (flow[j, i] <= sum(demand) * (1 - direction[i, j])
        #     for (i, j) in EDGES),
        #    name='flow-dir-backward'
        # )

        # The required surplus must equal the difference between (ingoing + self demand) - (outgoing)
        # model.addConstrs(
        #    (sum(demand) * is_control_center[i] == demand[i] + sum(flow[j, i]
        #     for j in CITIES if j != i) - sum(flow[i, j] for j in CITIES if j != i) for i in CITIES),
        #    name='conservation-of-flow'
        # )
        model.addConstrs(
            (sum(demand) * is_control_center[i] == demand[i] + sum(
                flow[normalize(i, j)] * (1 if i > j else -1) for j in CITIES if j != i) for i in CITIES)
        )

        # Whether an edge is a sub edge, i.e. part of the sub network.
        is_sub_edge = model.addVars(
            EDGES, vtype=GRB.BINARY, name='is-sub-edge')

        # We can only send flow along an edge if it is either a sub edge or a core edge
        model.addConstrs(
            (sum(demand) * (is_sub_edge[e] + is_core_edge[e])
             >= abs_flow[e] for e in EDGES),
            name='force-is-edge-up-if-flow',

        )

        # Force is_sub_edge to 0 if there is no flow (with M = min(demand))
        model.addConstrs(
            (min(demand) * is_sub_edge[e] <= abs_flow[e] for e in EDGES),
            name='force-is-edge-down-if-no-flow',
        )

        # An edge can not be both a core edge and a sub edge
        model.addConstrs(
            (is_core_edge[e] + is_sub_edge[e] <= 1 for e in EDGES),
            name='disallow-is-both-sub-and-core',
        )

        # The cost of an edge excluding its cost as a core edge
        edge_cost = model.addVars(EDGES, name='edge-cost')

        # The edge cost must be bounded below by 10 + (0.1 D_ij)**1.5 * B if it is a sub edge
        def M(e): return 10 + (0.1 * D[e])**1.5 * sum(demand)
        model.addConstrs(
            (edge_cost[e] + M(e) * is_core_edge[e] >= 10 * is_sub_edge[e] +
             (0.1 * D[e])**1.5 * abs_flow[e] for e in EDGES),
            name='edge-cost-lb'
        )

        # Finally: we can set the objective function
        model.setObjective(
            sum(edge_cost[e] + 10 * D[e] * is_core_edge[e] for e in EDGES), GRB.MINIMIZE)

        # Assign relevant stuff to `self`
        self.config = config
        self.model = model
        self.is_control_center = is_control_center
        self.is_core_edge = is_core_edge
        self.is_core_city = is_core_city
        self.is_connected_step = is_connected_step
        self.is_connectable_step = is_connectable_step
        self.flow = flow
        # self.direction = direction
        self.is_sub_edge = is_sub_edge
        self.edge_cost = edge_cost
        self.CITIES = CITIES
        self.EDGES = EDGES

    def edge_info(self):
        core = list(non_zero(self.is_core_edge))
        utilized = [normalize(*e) for e in non_zero(self.flow)]
        D = self.config.distances

        return [{
            'From': self.config.cities[i],
            'To': self.config.cities[j],
            'Type': 'CORE' if normalize(i, j) in core else 'SUB',
            'Flow': self.flow[i, j].x,
            'Cost': (10 * D[i, j] * self.is_core_edge[normalize(i, j)] + self.edge_cost[normalize(i, j)]).getValue(),
            'Distance': D[i, j],
        } for (i, j) in set(core + utilized)]

    def city_info(self):
        core_cities = list(non_zero(self.is_core_city))
        control_center = list(non_zero(self.is_control_center))

        return [{
            'Index': i,
            'Name': self.config.cities[i],
            'IsCoreCity': i in core_cities,
            'IsControlCenter': i in control_center,
            'Demand': self.config.demand[i],
            # IngoingFlow: if the last point is i and the flow is positive or the first point is i and the flow is negative
            'IngoingFlow': sum(abs(self.flow[a, b].x) * (1 if ((b == i and self.flow[a, b].x > 0) or (a == i and self.flow[a, b].x < 0)) else 0) for (a, b) in self.EDGES),
            # OutgoingFlow: if the first point is i and the flow is positive or the last point is i and the flow is negative
            'OutgoingFlow': sum(abs(self.flow[a, b].x) * (1 if ((a == i and self.flow[a, b].x > 0) or (b == i and self.flow[a, b].x < 0)) else 0) for (a, b) in self.EDGES),
        } for i in self.CITIES]
