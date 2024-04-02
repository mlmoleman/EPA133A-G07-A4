import pandas as pd
from shapely import distance
from pyproj import Transformer
from shapely.geometry import LineString
import shapely.ops as sp_ops
import warnings
from shapely import buffer
import os
from matplotlib import pyplot as plt
import contextily as cx
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd

warnings.filterwarnings("ignore")

# Gets the path to main folder
main_folder_path = os.path.normpath(os.getcwd() + os.sep + os.pardir)
# Reads in the road data and turns it into a geodataframe
df = pd.read_csv(main_folder_path + "/data/roads.csv")
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")

# Creates a list of all the unique road names
road_names = gdf["road"].unique()
# Select the rows that start with N to get all the N roads
road_names_N = [road for road in road_names if road.startswith("N")]

# Transformer that can be used to convert from a lat,lon based crs to a meters one
transformer = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True)
# Will contain the buffered lines made for every road
line_dict_buffer = {}
# Will contain the lines made for every road
line_dict = {}
# Loops over all the road names
for road_name in road_names_N:
    # Selects the rows corresponding to the road name
    bridges_road = gdf[gdf["road"] == road_name]
    # Check if the road has more then two rows, can not make a line from one point
    if len(bridges_road["geometry"]) >= 2:
        # Creates line
        line = LineString(bridges_road["geometry"])
        # Converts to meter based crs and then get the length in meters
        line_transformed = sp_ops.transform(transformer.transform, line).length
        # If line is longer then 25km then add to dict
        if line_transformed > 25000:
            line_dict_buffer[road_name] = buffer(LineString(bridges_road["geometry"]), 0.01)
            line_dict[road_name] = line

# Creates GeoPandasSeries of the line and buffered line dictionaries
gseries = gpd.GeoSeries(line_dict_buffer.values(), index=line_dict_buffer.keys(), crs=4326)
gseries_test = gpd.GeoSeries(line_dict.values(), index=line_dict.keys(), crs=4326)

# Will contain the indexes of the roads that intersect with the N1
cross_index_N1 = []
# Loops over the roads in the gseries
for index in gseries.index:
    # Checks if the road intersects yes or no
    if gseries["N1"].intersects(gseries[index]):
        # If yes then add the index to the cross_index_N1 list
        cross_index_N1.append(index)

# Same as above, but then for the N2
cross_index_N2 = []
for index in gseries.index:
    if gseries["N2"].intersects(gseries[index]):
        cross_index_N2.append(index)

# Selects the lines that intersect with the N1 and N2
intersecting_N1 = gseries[gseries.index.isin(cross_index_N1)]
intersecting_N2 = gseries[gseries.index.isin(cross_index_N2)]

# Calculates the intersection points. N1 and N2 get dropped, because they intersect
# with themselves and there is no need to examine an intersection with itself
intersections_N1 = gseries["N1"].intersection(intersecting_N1).drop("N1")
intersections_N2 = gseries["N2"].intersection(intersecting_N2).drop("N2")

# Create subset of the rows for the N1 and N2
gdf_N1 = gdf[gdf["road"] == "N1"]
gdf_N2 = gdf[gdf["road"] == "N2"]
# Saves the intersection points for the bonus assignment
# pd.concat([intersections_N1, intersections_N2]).to_csv(main_folder_path + "/data/intersections_bonus.csv")


#
def process_intersection_data(gdf_data, intersect_data):
    """
    Used to get the closest LRP on the N1 or N2 to the intersection point
    """
    # Is used outside the function
    global closest_point
    # Creates an empty dataframe that will be filled with points close to the intersection point
    empty_dataframe = gpd.GeoDataFrame(columns=list(gdf.columns) + ["intersec_to"], crs="EPSG:4326")
    # Loops over the intersection point indexes
    for intersect_index_N1 in intersect_data.index:
        # Gets the point corresponding to the index
        intersect_point_n1 = intersect_data[intersect_index_N1]
        # Defines the distance between the intersection point and the closest point
        smallest_distance = 10000
        # Loops over the N road point indexes
        for N_index in gdf_data.index:
            # Gets the point corresponding to the index
            n1_point = gdf_data.loc[N_index, "geometry"]
            # Calculates the distance between the two points
            dist = distance(n1_point, intersect_point_n1)
            # Checks if distance is smaller than the smallest value already found, if True updates the smallest
            # distance and current closest point
            if dist < smallest_distance:
                smallest_distance = dist
                closest_point = N_index
        # Gets LRP data corresponding to index
        series = gdf_data.loc[closest_point]
        # Add a colum to the LRP data to where the LRP intersects to
        series["intersec_to"] = intersect_index_N1
        # Add to the dataframe
        empty_dataframe.loc[closest_point] = series
    # Change the type for all the points to intersection
    empty_dataframe["type"] = "intersection"

    return empty_dataframe


# Find the LRPs the N1 and N2
df_intersections_main_N1 = process_intersection_data(gdf_N1, intersections_N1)
df_intersections_main_N2 = process_intersection_data(gdf_N2, intersections_N2)
# Merge the result into one dataframe
df_intersections_main = pd.concat([df_intersections_main_N1, df_intersections_main_N2], axis=0, ignore_index=True)
# Store dataframe
# df_intersections_main.to_csv(main_folder_path + "/data/intersections_main.csv")

# Creates empty dataframe that will contain the LRPs on the side roads that intersect to the N1
Side_to_N1 = gpd.GeoDataFrame(columns=list(gdf.columns) + ["intersec_to"], crs="EPSG:4326")
# Loops over the intersection point indexes
for road_name in intersections_N1.index:
    # Subsets the data corresponding to the index of the road
    road_gdf = gdf[gdf["road"] == road_name]
    # Gets the point of the intersection
    intersect_point_N1 = intersections_N1[road_name]
    # Defines the distance between the intersection point and the closest point
    min_dist = 10000
    # Loops over the N road point indexes
    for road_point_index in road_gdf.index:
        # Gets the point corresponding to the index
        road_point = road_gdf.loc[road_point_index, "geometry"]
        # Calculates the distance between the two points
        dist = distance(intersect_point_N1, road_point)
        # Checks if distance is smaller than the smallest value already found, if True updates the smallest
        # distance and current closest point
        if dist < min_dist:
            min_dist = dist
            closest_point = road_point_index
    # Gets LRP data corresponding to index
    series = road_gdf.loc[closest_point]
    # Add a colum to the LRP data to where the LRP intersects to, which, in
    # this case is always the N1
    series["intersec_to"] = "N1"
    # Add the LRP data to the empty dataframe
    Side_to_N1.loc[closest_point] = series

# Same as code above, but then for the N2
Side_to_N2 = gpd.GeoDataFrame(columns=list(gdf.columns) + ["intersec_to"], crs="EPSG:4326")
for road_name in intersections_N2.index:
    road_gdf = gdf[gdf["road"] == road_name]
    intersect_point_N2 = intersections_N2[road_name]
    min_dist = 10000
    for road_point_index in road_gdf.index:
        road_point = road_gdf.loc[road_point_index, "geometry"]
        dist = distance(intersect_point_N2, road_point)
        if dist < min_dist:
            min_dist = dist
            closest_point = road_point_index
    series = road_gdf.loc[closest_point]
    series["intersec_to"] = "N2"
    Side_to_N2.loc[closest_point] = series

# Joins the dataframes for the N1 and N2 into one
df_intersections_side = pd.concat([Side_to_N1, Side_to_N2], axis=0, ignore_index=True)
# Changes the type to intersection
df_intersections_side["type"] = "intersection"

# The N208 and N207 are the only side roads with an intersection

# Creates subsets for the N207 and N208
gdf_N208 = gdf[gdf["road"] == "N208"]
gdf_N207 = gdf[gdf["road"] == "N207"]

# Select the LRP closest point, value is manually picked
gdf_N208_closest_point = gdf_N208.loc[3512]
gdf_N208_closest_point["intersec_to"] = "N207"

# The value on the N207 can not be manually picked

# Will be used to determine which distance is the smallest
min_dist = 10000
for N_index in gdf_N207.index:
    # Selects the corresponding point to the index
    N1_point = gdf_N207.loc[N_index, "geometry"]
    # Calculates the distance
    dist = distance(N1_point, gdf_N208_closest_point.loc["geometry"])
    # Check if distance is smaller then the already smallest distance
    if dist < min_dist:
        # If yes, updates the smallest distance
        min_dist = dist
        # Assign new index of closest point
        closest_point = N_index
# Get LRP data corresponding to index
gdf_N207_closest_point = gdf_N207.loc[closest_point]
# Adds value to indicate to which road the intersection is
gdf_N207_closest_point["intersec_to"] = "N208"

# Creates a dataframe of all the intersection data
df_intersections_all = pd.concat([df_intersections_main,
                                  df_intersections_side,
                                  gpd.GeoDataFrame(gdf_N207_closest_point).T,
                                  gpd.GeoDataFrame(gdf_N208_closest_point).T], axis=0, ignore_index=True)

# Saves the intersection data to a csv
main_folder_path = os.path.normpath(os.getcwd() + os.sep + os.pardir)
df_intersections_all.to_csv(main_folder_path + "/data/intersections.csv")

# Creates a plot of the result
fig, ax = plt.subplots(1,1,figsize=(10,10))
# Plots the N1
gpd.GeoSeries(gseries["N1"],crs=4326).plot(ax=ax,color="blue")
df_intersections_main.plot(ax=ax,column="intersec_to")
# Plots the N2
gpd.GeoSeries(gseries["N2"],crs=4326).plot(ax=ax,color="white")
# Plots the map
cx.add_basemap(ax=ax,crs=4326)
# Adds title
ax.title.set_text("Roads intersecting with N1 and N2")
# Merges the roads that intersect with N1 and N2 and plot those
pd.concat([intersecting_N1,intersecting_N2]).reset_index().plot(ax=ax,column="index",legend=True)
# Saves the image
plt.savefig(main_folder_path + "/img/intersect_img.png")
# plt.show()
