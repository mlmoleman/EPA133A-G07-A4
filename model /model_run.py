from model import BangladeshModel

"""
    Run simulation
    Print output at terminal
"""

# ---------------------------------------------------------------

# run time 5 x 24 hours; 1 tick 1 minute
run_length = 5 * 24 * 60

seed = 1234567

sim_model = BangladeshModel(seed=seed)

# Check if the seed is set
print("SEED " + str(sim_model._seed))

# One run with given steps
for i in range(run_length):
    sim_model.step()

# retrieve model data
# model_data = sim_model.datacollector.get_model_vars_dataframe()
# and put in CSV
# model_data.to_csv("../data/model_data.csv")