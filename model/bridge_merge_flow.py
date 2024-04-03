import numpy as np
import pandas as pd


def data_merge():
    """
    This function is used to merge data from two csv files,
    namely bridges_cleaned_maps.csv and sourcesinks.csv
    """

    # read dataframe
    df_bridges = pd.read_csv('../data/bridges_cleaned_maps.csv')
    # import intersections data
    df_intersections = pd.read_csv('../data/intersections.csv')
    # get all intersected roads
    intersections = df_intersections['intersec_to'].unique().tolist()
    # remove nan if present
    intersections = [x for x in intersections if str(x) != 'nan']
    # keep all bridges in roads that intersect
    df_bridges = df_bridges[df_bridges['road'].isin(intersections)]
    # initialize columns needed to align with sourcesinks
    new_bridges_columns = ['Total Cargo', 'Total People', 'Total Transport', 'Total Transport Weight',
                           'SourceSink Cargo Weight', 'SourceSink People Weight']
    # for each column
    for column in new_bridges_columns:
        # add column to bridges dataframe and assign NaN value to each entry
        df_bridges[column] = np.nan
    # drop unnecessary columns
    df_bridges = df_bridges.drop(["Unnamed: 0", "Unnamed: 0.1", "Unnamed: 0.2", "index", "geometry"], axis='columns')

    # read sourcesinks dataframe
    df_sourcesinks = pd.read_csv('../data/sourcesinks.csv')
    # drop unnecessary columns
    df_sourcesinks = df_sourcesinks.drop(["Unnamed: 0", 'Start_LRP', 'End_LRP'], axis='columns')
    # rename columns
    df_sourcesinks.rename({"Road": "road", "Name": "name", "Average Chainage": "km"}, axis=1, inplace=True)
    # add new columns to align with bridges
    df_sourcesinks['type'] = 'sourcesink'
    df_sourcesinks['length'] = 0
    df_sourcesinks['condition'] = np.nan
    df_sourcesinks['model_type'] = 'sourcesink'
    df_sourcesinks['lat'] = np.nan
    df_sourcesinks['lon'] = np.nan
    df_sourcesinks['FLOODCAT'] = np.nan
    df_sourcesinks['CycloonCat'] = np.nan

    # get the dataframes which needs to be merged
    frames = [df_bridges, df_sourcesinks]
    # merge dataframes into df
    df = pd.concat(frames)
    # sort values based on road and chainage
    df = df.sort_values(by=['road', 'km'])
    # reset index
    df = df.reset_index(drop=True)
    # retrieve all duplicates based on a subset of road and chainage
    duplicates = df[df.duplicated(subset=['road', 'km'])]
    # only keep duplicates which are sourcesinks
    duplicates = duplicates[duplicates['type'] == 'sourcesink']
    # initialize list for indexes to remove
    id_to_remove = []
    # for each index and row in duplicates dataframe
    for index, row in duplicates.iterrows():
        # retrieve road name of each row
        road = df.loc[index, 'road']
        # retrieve chainage of each row
        chainage = df.loc[index, 'km']
        # new latitude is based on latitude of previous one, which is duplicate
        df.at[index, 'lat'] = df.at[index - 1, 'lat']
        # new longitude is based on longitude of previous one, which is duplicate
        df.at[index, 'lon'] = df.at[index - 1, 'lon']
        # add old index (index - 1) to list
        id_to_remove.append(index - 1)
    # drop rows in dataframe with index in id_to_remove list
    df.drop(df.index[id_to_remove], inplace=True)
    # reset index of dataframe
    df = df.reset_index(drop=True)

    # now the missing coordinates of some sourcesinks are filled using the roads dataframe
    df_roads = pd.read_csv('../data/roads.csv')
    # retrieving missing values based on latitude
    missing = df[df.lat.isnull()]
    for index in missing.index:
        # get chainage of missing value
        get_chainage = df.loc[index, 'km']
        # get road name of missing value
        road_name = df.loc[index, 'road']
        # get road subset
        road_subset = df_roads[df_roads['road'] == road_name]
        # if one of the main roads
        if road_name == 'N1' or road_name == 'N2' or road_name == 'N8':
            # get similar chainage in road dataset
            similar_chainage = road_subset[road_subset['chainage'].between(get_chainage - 0.5, get_chainage + 0.5)]
        else:
            # if not a main road, make range of possible chainages larger
            similar_chainage = road_subset[road_subset['chainage'].between(get_chainage - 5, get_chainage + 5)]
        # get latitude and longitude of last row in subset of similar chainage
        lat = similar_chainage.at[similar_chainage.index[-1], 'lat']
        lon = similar_chainage.at[similar_chainage.index[-1], 'lon']
        # assign latitude and longitude to missing row
        df.loc[index, 'lat'] = lat
        df.loc[index, 'lon'] = lon

    id_to_remove = []
    for index, row in df.iterrows():
        if row['type'] == 'sourcesink' and pd.isnull(df.at[index, 'Total Cargo']) == True:
            id_to_remove.append(index)
    # drop rows in dataframe with index in id_to_remove list
    df.drop(df.index[id_to_remove], inplace=True)
    # reset index of dataframe
    df = df.reset_index(drop=True)
    # write to csv file
    df.to_csv('../data/bridges_cleaned_maps_sourcesinked.csv')


data_merge()