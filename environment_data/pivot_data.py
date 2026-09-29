""" 
Climate and Pollution Data Analysis  - Transform Data to Wide Format

Do not run this script until the data has been downloaded and cleaned. This script will read in the cleaned data and pivot it to have the
pollutants and climate readings as columns, with the grid code, year, and month as the index.

The goal of this is to transform the data from the long format to the wide format that we can use to analyse the data. These
are large datasets so we will save the pivoted data to CSV files so that we can load them in later without having to pivot them again.
"""
import pandas as pd

# Read in the pollution data and pivot it to have pollutants as columns
print("Reading in the pollution data and pivoting it to have pollutants as columns...")
df_pollution = pd.read_csv('scotland_annual_pollution.csv')
df_poll_pivot = pd.pivot_table(df_pollution, index=['ukgridcode','year'], columns='pollutant', values='amount', aggfunc='mean').reset_index()

print("Reading in the climate data and pivoting it to have climate readings as columns...")
# Read in the climate data - this is big and takes some time!
df_climate = pd.read_csv('scotland_monthly_climate.csv')
# Pivot it to have the different climate readings as columns, with the grid code, year, and month as the index
df_climate_pivot = pd.pivot_table(df_climate, index=['x_grid','y_grid', 'year', 'month'], columns='type_of_reading', values='value', aggfunc='mean').reset_index()

print("Pivoting complete. Saving the pivoted dataframes to CSV files...")
# Save the pivoted dataframes to CSV files
df_climate_pivot.to_csv('scotland_monthly_climate_pivot.csv', index=False)
df_poll_pivot.to_csv('scotland_annual_pollution_pivot.csv', index=False)