import pandas as pd
from pandas import Series, DataFrame

def postcodes():
    postcodes = pd.read_excel('post_codes/wales_pc.xlsx')
    #postcode=[]
    postcode = postcodes['Postcode'].values
    return postcode
