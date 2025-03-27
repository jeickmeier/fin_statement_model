import pandas as pd

try:
    file_name = "101-01-90-Minute-Case-Study-Otis-Complete.xlsx"
    f = pd.read_excel(file_name)
    print(f.head())
except FileNotFoundError:
    print(f"No such file or directory: '{file_name}'")
