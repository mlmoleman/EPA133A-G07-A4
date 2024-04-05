import pandas as pd
from model import BangladeshModel
from mesa import batch_run

"""
    Run simulation
    Perform batchrunner
"""

# ---------------------------------------------------------------

# use bridge's breaking down probabilities as input
# this allows to adjust probabilities
scenario_lst = pd.read_csv('../data/scenarios.csv')
# print(scenario_lst)

# Change scenario number to run different experiments, possible scenario: 0, 1, 2
for scenario_number in [0, 1, 2]:
    scenario: int = scenario_number

    # get the probabilities for each condition
    prob = scenario_lst.iloc[scenario].to_dict()
    if scenario == 0:
        flood_par = [False]
    else:
        flood_par = [True,False]
    params = {"collapse_dict": [prob], "routing_type": "shortest","flood_lever":flood_par}
    # print(params)

    # Settings of batch runner
    results = batch_run(
        BangladeshModel,
        parameters=params,
        iterations=5,
        max_steps=7200,
        number_processes=1,
        data_collection_period=5,
        display_progress=True)

    # Convert results to dataframe
    df_results = pd.DataFrame(results)
    # Convert dataframe to CSV-file
    df_results.to_csv("../experiment/Scenario" + str(scenario) + ".csv")

# # Loop over the scenarios
# for dictionary in collapse_dict:
#     # Define the parameters that need to be assessed by the batch runner
#     params = {"collapse_dict": [dictionary], "routing_type": "shortest"}
#
#     # Settings of batch runner
#     results = batch_run(
#         BangladeshModel,
#         parameters=params,
#         iterations=10,
#         max_steps=7200,
#         number_processes=1,
#         data_collection_period=-1,
#         display_progress=True)
#
#     # Convert results to dataframe
#     df_results = pd.DataFrame(results)
#     # Convert dataframe to CSV-file
#     df_results.to_csv("../experiment/scenario"+str(scenario)+".csv")
#
#     # Add one to scenario counter
#     scenario += 1
