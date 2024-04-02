from mesa import Model
from mesa.time import BaseScheduler
from mesa.space import ContinuousSpace
from components import Source, Sink, SourceSink, Bridge, Link, Intersection, Vehicle
import pandas as pd
from collections import defaultdict
from statistics import mean
from mesa.datacollection import DataCollector
import networkx as nx
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
# ---------------------------------------------------------------


def get_steps(model):
    return model.schedule.steps


def get_avg_delay(model):
    """
    Returns the average delay time per bridge
    """
    delays = [a.delay_time for a in model.schedule.agents if isinstance(a, Bridge)]
    if len(delays) > 0:
        return mean(delays)
    else:
        return 0


def get_avg_driving(model):
    """
    Returns the average driving time of vehicles on roads
    """
    if len(model.driving_time_of_trucks) > 0:
        return sum(model.driving_time_of_trucks) / len(model.driving_time_of_trucks)
    else:
        return 0


def get_avg_speed(model):
    """
    Returns the average speed of vehicles on roads
    """
    if len(model.speed_of_trucks) > 0:
        return sum(model.speed_of_trucks) / len(model.speed_of_trucks)
    else:
        return 0


def get_tot_collapsed(model):
    """
    Returns the total number of collapsed bridges per time step
    """
    collapsed = [a.collapsed for a in model.schedule.agents if isinstance(a, Bridge)]
    return collapsed.count(True)


def get_A_collapsed(model):
    """
    Returns the number of collapsed bridges per time step with condition A
    """
    condition = 'A'
    return model.collapsed_conditions_dict[condition]


def get_B_collapsed(model):
    """
    Returns the number of collapsed bridges per time step with condition B
    """
    condition = 'B'
    return model.collapsed_conditions_dict[condition]


def get_C_collapsed(model):
    """
    Returns the number of collapsed bridges per time step with condition C
    """
    condition = 'C'
    return model.collapsed_conditions_dict[condition]


def get_D_collapsed(model):
    """
    Returns the number of collapsed bridges per time step with condition D
    """
    condition = 'D'
    return model.collapsed_conditions_dict[condition]


def set_lat_lon_bound(lat_min, lat_max, lon_min, lon_max, edge_ratio=0.02):
    """
    Set the HTML continuous space canvas bounding box (for visualization)
    give the min and max latitudes and Longitudes in Decimal Degrees (DD)

    Add white borders at edges (default 2%) of the bounding box
    """

    lat_edge = (lat_max - lat_min) * edge_ratio
    lon_edge = (lon_max - lon_min) * edge_ratio

    x_max = lon_max + lon_edge
    y_max = lat_min - lat_edge
    x_min = lon_min - lon_edge
    y_min = lat_max + lat_edge
    return y_min, y_max, x_min, x_max


# ---------------------------------------------------------------
class BangladeshModel(Model):
    """
    The main (top-level) simulation model

    One tick represents one minute; this can be changed
    but the distance calculation need to be adapted accordingly

    Class Attributes:
    -----------------
    step_time: int
        step_time = 1 # 1 step is 1 min

    path_ids_dict: defaultdict
        Key: (origin, destination)
        Value: the shortest path (Infra component IDs) from an origin to a destination

        Only straight paths in the Demo are added into the dict;
        when there is a more complex network layout, the paths need to be managed differently

    sources: list
        all sources in the network

    sinks: list
        all sinks in the network

    """

    step_time = 1

    file_name = '../data/bridges_intersected_linked.csv'

    def __init__(self, seed=None, x_max=500, y_max=500, x_min=0, y_min=0,
                 collapse_dict: defaultdict = {'A': 0.0, 'B': 0.0, 'C': 0.0, 'D': 0.8}, routing_type: str = "shortest"):

        self.routing_type = routing_type
        self.collapse_dict = collapse_dict
        self.schedule = BaseScheduler(self)
        self.running = True
        self.path_ids_dict = defaultdict(lambda: pd.Series())
        self.shortest_path_dict = defaultdict(lambda: pd.Series())
        self.space = None
        self.sources = []
        self.sinks = []

        self.long_length_threshold = 200
        self.medium_length_threshold = 50
        self.short_length_threshold = 10

        self.G = self.generate_network()  # generate network using networkx library
        self.generate_model()

        self.driving_time_of_trucks = []  # initialise list for driving time of trucks
        self.speed_of_trucks = []  # initialise list for speed for trucks
        self.collapsed_conditions_dict = {'A': 0, 'B': 0, 'C': 0, 'D': 0}

    def generate_network(self):
        """
        generate the network used within the simulation model
        returns a multi directed graph which includes bridges and intersections between roads
        """
        # import data
        df = pd.read_csv('../data/bridges_intersected_linked.csv')
        # drop old id
        df = df.drop("id", axis='columns')
        # sort roads dataframe based on road name and chainage
        df = df.sort_values(by=['road', 'km'])
        # reset index
        df = df.reset_index(drop=False)
        # set new index as ID
        df.rename(columns={'index': 'id'}, inplace=True)
        # retrieve all roads in dataset
        roads = df['road'].unique().tolist()
        # initialise the graph
        self.G = nx.DiGraph()
        # for each road in list roads
        for road in roads:
            road_subset = df[df['road'] == road]
            for index, row in df.iterrows():
                self.G.add_node(row['id'], pos=(row['lat'], row['lon']), len=row['length'],
                                typ=row['model_type'], road=row['road'], intersec=row['intersec_to'],
                                km=row['km'])
            # retrieve all edges between bridges for one road
            edges = [(index, index + 1) for index, row in road_subset.iterrows()]
            # remove last one, which is out of bound
            edges.pop()
            # reverse subset
            road_subset_reversed = road_subset.iloc[::-1]
            # get all reversed indexes and add to list of edges
            edges += [(index, index - 1) for index, row in road_subset_reversed.iterrows()]
            # remove last one, which is out of bound
            edges.pop()
            # add all edges
            self.G.add_edges_from(edges)

        # get model type of all nodes
        typ = nx.get_node_attributes(self.G, 'typ')
        # get road which is intersected with N1 or N2
        intersec_to = nx.get_node_attributes(self.G, 'intersec')
        # get current roads
        road = nx.get_node_attributes(self.G, 'road')
        # get all key, value pairs in dictionaries
        for key_typ, value_typ in typ.items():
            # if value equals intersection as model type
            if value_typ == 'intersection':
                # current road
                current_road = road[key_typ]
                # get road name which intersects N1 or N2
                intersected_road = intersec_to[key_typ]
                # get subset of intersected road
                subset_intersected_road = df[df['road'] == intersected_road]
                # get all rows which are intersections
                intersections = subset_intersected_road[subset_intersected_road['model_type'] == 'intersection']
                # select the row for which intersection to equals current road
                row = intersections[intersections['intersec_to'] == current_road]
                # retrieve ID
                row_index = row.index[0]
                # assign intersected edge to variable
                if (key_typ, row_index) not in self.G.edges:
                    # add intersected edge
                    self.G.add_edge(key_typ, row_index, distance=0)

        # retrieve the chainage of every node
        chainage = nx.get_node_attributes(self.G, 'km')
        # for each edge pair
        for u, v in self.G.edges:
            # if difference between node values equals one i.e. not an intersected edge
            if abs(v - u) == 1:
                # compute the distance based on difference in chainage, take absolute value
                distance = abs(chainage[v] - chainage[u])
                # multiply to retrieve kilometers rather than meters
                distance *= 1000
                # add to edge as distance attribute
                self.G[u][v]['distance'] = distance

        # return network
        return self.G

    def generate_model(self):
        """
        generate the simulation model according to the csv file component information

        Warning: the labels are the same as the csv column labels

        """
        # import data
        df = pd.read_csv(self.file_name)

        # a list of names of roads to be generated
        roads = df['road'].unique().tolist()

        df_objects_all = []
        for road in roads:
            # Select all the objects on a particular road in the original order as in the cvs
            df_objects_on_road = df[df['road'] == road]

            if not df_objects_on_road.empty:
                df_objects_all.append(df_objects_on_road)

                """
                Set the path 
                1. get the serie of object IDs on a given road in the cvs in the original order
                2. add the (straight) path to the path_ids_dict
                3. put the path in reversed order and reindex
                4. add the path to the path_ids_dict so that the vehicles can drive backwards too
                """
                path_ids = df_objects_on_road['id']
                path_ids.reset_index(inplace=True, drop=True)
                self.path_ids_dict[path_ids[0], path_ids.iloc[-1]] = path_ids
                self.path_ids_dict[path_ids[0], None] = path_ids
                path_ids = path_ids[::-1]
                path_ids.reset_index(inplace=True, drop=True)
                self.path_ids_dict[path_ids[0], path_ids.iloc[-1]] = path_ids
                self.path_ids_dict[path_ids[0], None] = path_ids

        # put back to df with selected roads so that min and max and be easily calculated
        df = pd.concat(df_objects_all)
        y_min, y_max, x_min, x_max = set_lat_lon_bound(
            df['lat'].min(),
            df['lat'].max(),
            df['lon'].min(),
            df['lon'].max(),
            0.05
        )

        # ContinuousSpace from the Mesa package;
        # not to be confused with the SimpleContinuousModule visualization
        self.space = ContinuousSpace(x_max, y_max, True, x_min, y_min)

        for df in df_objects_all:
            for _, row in df.iterrows():  # index, row in ...

                # create agents according to model_type
                model_type = row['model_type'].strip()
                agent = None

                name = row['name']
                if pd.isna(name):
                    name = ""
                else:
                    name = name.strip()

                if model_type == 'source':
                    agent = Source(row['id'], self, row['length'], name, row['road'])
                    self.sources.append(agent.unique_id)
                elif model_type == 'sink':
                    agent = Sink(row['id'], self, row['length'], name, row['road'])
                    self.sinks.append(agent.unique_id)
                elif model_type == 'sourcesink':
                    agent = SourceSink(row['id'], self, row['length'], name, row['road'])
                    self.sources.append(agent.unique_id)
                    self.sinks.append(agent.unique_id)
                elif model_type == 'bridge':
                    agent = Bridge(row['id'], self, row['length'], name, row['road'], row['condition'])
                elif model_type == 'link':
                    agent = Link(row['id'], self, row['length'], name, row['road'])
                elif model_type == 'intersection':
                    if not row['id'] in self.schedule._agents:
                        agent = Intersection(row['id'], self, row['length'], name, row['road'])

                if agent:
                    self.schedule.add(agent)
                    y = row['lat']
                    x = row['lon']
                    self.space.place_agent(agent, (x, y))
                    agent.pos = (x, y)

        # define the model metrics we want to extract for each model run
        model_metrics = {
                        "step": get_steps,
                        "avg_delay": get_avg_delay,
                        "avg_driving_time": get_avg_driving,
                        "avg_speed": get_avg_speed,
                        "avg_collapsed": get_tot_collapsed,
                        "A_collapsed": get_A_collapsed,
                        "B_collapsed": get_B_collapsed,
                        "C_collapsed": get_C_collapsed,
                        "D_collapsed": get_D_collapsed
                        }

        # set up the data collector
        self.datacollector = DataCollector(model_reporters=model_metrics)

    def get_random_route(self, source):
        """
        pick up a random route given an origin
        """
        while True:
            # different source and sink
            sink = self.random.choice(self.sinks)
            if sink is not source:
                break
        return self.path_ids_dict[source, sink]

    def get_shortest_path_route(self, source):
        """
        gives the shortest path between an origin and destination,
        based on bridge network defined using NetworkX library,
        and adds this path to path_ids_dict
        """
        # call network
        network = self.G
        # determine the sink to calculate the shortest path to
        while True:
            # different source and sink
            sink = self.random.choice(self.sinks)
            if sink is not source:
                break
        # the dictionary key is the origin, destination combination:
        key = source, sink
        # first, check if there already is a shortest path:
        if key in self.shortest_path_dict.keys():
            return self.shortest_path_dict[key]
        else:
            # compute shortest path between origin and destination based on distance (which is weight)
            shortest_path = nx.shortest_path(network, source, sink, weight='distance')
            # retrieve the length
            shortest_path_length = nx.shortest_path_length(network, source, sink, weight='distance')
            # assign value to shortest path dictionary, which is a tuple of the path and length of the path
            self.shortest_path_dict[key] = shortest_path, shortest_path_length
            # print("path", shortest_path, "length:",shortest_path_length)

            return self.shortest_path_dict[key]

    def get_straight_route(self, source):
        """
        pick up a straight route given an origin
        """
        return self.path_ids_dict[source, None]

    def get_route(self, source):
        if self.routing_type == "random":
            return self.get_random_route(source)
        elif self.routing_type == "straight":
            return self.get_straight_route(source)
        elif self.routing_type == "shortest":
            return self.get_shortest_path_route(source)
        else:
            return self.get_straight_route(source)

    def step(self):
        """
        Advance the simulation by one step.
        """
        self.datacollector.collect(self)
        self.schedule.step()

# EOF -----------------------------------------------------------
