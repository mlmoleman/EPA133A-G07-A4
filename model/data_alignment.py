# import libraries
import pandas as pd
import numpy as np
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)


def data_network():
    """
    This function returns a dataframe used to align bridge data with intersections
    """
    # import bridge data
    df_bridges = pd.read_csv('../data/bridges_cleaned_maps_sourcesinked.csv')
    # add intersection to column
    df_bridges['intersec_to'] = None
    # reposition columns
    df_bridges = df_bridges[['road', 'km', 'type', 'model_type', 'name', 'length', 'condition', 'lat', 'lon',
                             'intersec_to', 'FLOODCAT', 'CycloonCat', 'Total Cargo', 'Total People', 'Total Transport',
                             'Total Transport Weight', 'SourceSink Cargo Weight', 'SourceSink People Weight']]

    # import intersections data
    df_intersections = pd.read_csv('../data/intersections.csv')
    # change chainage into km
    df_intersections.rename({'chainage': 'km'}, axis=1, inplace=True)
    # create model_type
    df_intersections['model_type'] = 'intersection'
    # create length
    df_intersections['length'] = 0
    # create condition
    df_intersections['condition'] = None
    # create flow columns
    new_intersection_columns = ['FLOODCAT', 'CycloonCat', 'Total Cargo', 'Total People', 'Total Transport',
                                'Total Transport Weight', 'SourceSink Cargo Weight', 'SourceSink People Weight']
    for column in new_intersection_columns:
        df_intersections[column] = np.nan
        # format columns
    df_intersections = df_intersections[['road', 'km', 'type', 'model_type', 'name', 'length', 'condition', 'lat',
                                         'lon', 'intersec_to', 'FLOODCAT', 'CycloonCat', 'Total Cargo', 'Total People',
                                         'Total Transport', 'Total Transport Weight', 'SourceSink Cargo Weight',
                                         'SourceSink People Weight']]

    # get all intersected roads
    intersections = df_intersections['intersec_to'].unique().tolist()
    # remove nan if present
    intersections = [x for x in intersections if str(x) != 'nan']

    # keep all bridges in roads that intersect
    df_bridges = df_bridges[df_bridges['road'].isin(intersections)]
    # keep all roads which are still in intersections list, so longer than 25 km
    df_intersections = df_intersections[df_intersections['intersec_to'].isin(intersections)]
    # get the dataframes which needs to be merged
    frames = [df_bridges, df_intersections]
    # merge dataframes into df
    df = pd.concat(frames)

    df = df.sort_values(by=['road', 'km'])

    # reset index
    df = df.reset_index(drop=True)
    # convert to csv
    df.to_csv('../data/bridges_intersected.csv')


# call function
data_network()