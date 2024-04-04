import pandas as pd

# Retrieve the Bridge dataframe
df = pd.read_csv('../data/bridges_intersected.csv')

# Create a list of the indexes
index = df.index


def create_links(df, indexes):
    # Create an empty dictionary
    inserting_links = {}
    # Loop over all the objects, skipping the first one as that is a sourcesink
    for i in index[1:]:
        # Determine the latitude of the object
        lat = df.iloc[i, df.columns.get_indexer(['lat'])].values
        # Determine the longitude of the object
        lon = df.iloc[i, df.columns.get_indexer(['lon'])].values
        # Determine the latitude of the previous object
        lat_prev = df.iloc[i-1, df.columns.get_indexer(['lat'])].values
        # Determine the longitude of the previous object
        lon_prev = df.iloc[i-1, df.columns.get_indexer(['lon'])].values
        # Determine the type of the object
        type_obj = df.iloc[i, df.columns.get_indexer(['type'])].values
        # Determine the type of the previous object
        type_prev_obj = df.iloc[i-1, df.columns.get_indexer(['type'])].values
        # Determine on which road the object is located
        road_obj = df.iloc[i, df.columns.get_indexer(['road'])].values
        # Determine on which road the previous object is located
        road_prev_obj = df.iloc[i-1, df.columns.get_indexer(['road'])].values
        # Check if the lat and lon of this object and the previous object are not the same
        # AND if the roads are both the same
        if not (lat == lat_prev and lon == lon_prev) and road_obj == road_prev_obj:
        # # AND if the type of this object and the previous object are not both equal to 'sourcesink'
        # if (not (lat == lat_prev and lon == lon_prev) and not type_obj == type_prev_obj == 'sourcesink'
        #         and not (type_prev_obj == 'sourcesink' and type_obj == 'intersection')):
            # if that is the case insert link
            # determine the length of the link by calculating the difference in km of the objects
            # and substracting half of the length of the objects.
            length = abs((1000*df.iloc[i, df.columns.get_indexer(['km'])].values -
                          1000*df.iloc[i-1, df.columns.get_indexer(['km'])].values -
                          0.5*df.iloc[i, df.columns.get_indexer(['length'])].values -
                          0.5*df.iloc[i-1, df.columns.get_indexer(['length'])].values))
            # Determine the road to which the link belongs
            road = df.iloc[i, df.columns.get_indexer(['road'])].values[0]
            # Calculate the km of the link by taking the average
            km = (df.iloc[i, df.columns.get_indexer(['km'])].values[0] +
                  df.iloc[i-1, df.columns.get_indexer(['km'])].values[0])/2
            # Calculate the latitude of the link by interpolating
            lat = (df.iloc[i, df.columns.get_indexer(['lat'])].values[0] +
                   df.iloc[i-1, df.columns.get_indexer(['lat'])].values[0])/2
            # Calculate the longitude of the link by interpolating
            lon = (df.iloc[i, df.columns.get_indexer(['lon'])].values[0] +
                   df.iloc[i-1, df.columns.get_indexer(['lon'])].values[0])/2
            # Add the link to the dictionary with the necessary attributes
            inserting_links[i] = {'road': [road], 'km': [km], 'type': ['link'], 'name': ['link'],
                                  'length': [round(length[0])], 'condition': None, 'lat': [lat], 'lon': [lon],
                                  'model_type': ['link']}
    return inserting_links


dict_links = create_links(df, index)


#%%
# Create a function to insert the links into the main dataframe
def insert_links(df, dict_links):
    # Make a copy of the dataframe
    main_df = df.copy()
    # create a list of the indexes of the links to insert
    index_links = list(dict_links.keys())
    # Loop over the links in the dictionary
    for link in dict_links:
        # update the index by adding the index of the link in the list
        # so that the links that are already added to the dataframe are taken into account
        index = link + index_links.index(link)
        # create a dataframe based on the link we want to insert
        df_insert = pd.DataFrame(dict_links[link])
        # Add the link to the main dataframe by concatting the dataframe until the index,
        # the link dataframe and the dataframe from the index
        main_df = pd.concat([main_df.iloc[:index, ], df_insert, main_df.iloc[index:, ]])
    # Reset the index of the main dataframe
    main_df = main_df.reset_index(drop=True)
    # Return the dataframe
    return main_df


# Call the function to check the outcome
main_df = insert_links(df, dict_links)
# Adding an id to every object
main_df['id'] = main_df.index
# Adding a column with the cumulative weight of Cargo transport
main_df['Cargo Weight cumsum'] = main_df['SourceSink Cargo Weight'].cumsum()
# Adding a column with the cumulative weight of Personal transport
main_df['People Weight cumsum'] = main_df['SourceSink People Weight'].cumsum()
# Drop the Unnamed column
main_df.drop(columns=['Unnamed: 0'], inplace=True)
# Set index to road column
main_df.set_index('road', inplace=True)

# Convert dataframe into csv
main_df.to_csv('../data/bridges_intersected_linked.csv')
