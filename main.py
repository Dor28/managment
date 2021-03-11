import numpy as np
import pandas as pd


purchase = pd.read_csv("purchases.csv", delimiter='\t')
visits = pd.read_csv("visits.csv", delimiter='\t')

print(type(purchase["revenue"]))
