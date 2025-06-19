import pandas as pd

import pandas as pd

def import_excel(file):
    try:
        data = pd.read_excel(file)
        return data
    except Exception as e:
        raise ValueError(f"An error occurred while importing the Excel file: {e}")