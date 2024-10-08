import streamlit as st
import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime

# Function to fetch carbon intensities for a specific zone on the selected day
def fetch_carbon_intensities(zone, date):
    url = "https://api.electricitymap.org/v3/carbon-intensity/history"
    params = {"zone": zone, "date": date.strftime('%Y-%m-%d')}
    headers = {"auth-token": "YOUR_API_TOKEN"}  # Replace with your API token
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return [entry["carbonIntensity"] for entry in data["history"]]
    else:
        st.error(f"Failed to fetch carbon intensities for {zone} on {date}.")
        return []

# Function to calculate total daily emissions
def calculate_daily_emissions(charging, emissions):
    hourly_emissions = charging * emissions
    daily_emissions = np.sum(hourly_emissions)
    return daily_emissions, hourly_emissions

# Function to calculate emission scenarios
def calculate_scenarios(total_charging, emissions):
    emissions_sorted_asc = np.sort(emissions)
    emissions_sorted_desc = np.sort(emissions)[::-1]

    hourly_capacity = 10  # Define hourly capacity as 10
    hours_needed = int(np.ceil(total_charging / hourly_capacity))

    best_case_total = np.sum(hourly_capacity * emissions_sorted_asc[:hours_needed])
    worst_case_total = np.sum(hourly_capacity * emissions_sorted_desc[:hours_needed])

    return best_case_total, worst_case_total

# Calculate the score using the new approach
def calculate_score(actual_emissions, best_case, worst_case):
    if worst_case == best_case:
        return 0  # or any other value that makes sense for your application
    return (actual_emissions - best_case) / (worst_case - best_case)

# Calculate detailed percentages
def calculate_percentages(actual_emissions, best_case, worst_case):
    away_best = ((actual_emissions - best_case) / best_case) * 100
    away_worst = ((worst_case - actual_emissions) / worst_case) * 100
    return away_best, away_worst

# Default example of charging values (randomly generated)
default_charging_values = {
    'Hour': list(range(24)),
    'Company 1 (kW)': np.random.randint(0, 13, 24),  # valores entre 0 e 12
    'Company 2 (kW)': np.random.randint(0, 13, 24),  # valores entre 0 e 12
    'Company 3 (kW)': np.random.randint(0, 13, 24)   # valores entre 0 e 12
}

# Function to style score with arrows
def style_score(value):
    if value > 0:
        return f"🔺 {value:.2f}%"
    elif value < 0:
        return f"🔻 {-value:.2f}%"
    else:
        return "0.00%"

# Streamlit UI
st.title("Electric Vehicle Charging Impact Analysis")

# Add an information button
if st.button("ℹ️ Info"):
    st.markdown("""
        <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px;">
            This web application analyzes carbon emissions based on the charging values of different companies. 
            You can input hourly charging values for each company and see the carbon emission rankings based on calculated scores.
        </div>
    """, unsafe_allow_html=True)

st.subheader("Carbon Intensities for Each Zone")

# Selection of date
date = st.date_input("Select the date for analysis", datetime.now())

# Selection of up to three countries
zones = st.multiselect("Select up to 3 countries", ["DE", "IT", "PT", "FR", "ES"], default=["PT"])

# Verificar se há pelo menos uma zona selecionada
if len(zones) == 0:
    st.error("Selecione pelo menos um país para prosseguir.")
elif len(zones) > 3:
    st.error("Por favor, selecione no máximo 3 países.")
else:
    intensities = {}
    for zone in zones:
        intensities[zone] = fetch_carbon_intensities(zone, date)

    # Verificar se houve falha na obtenção das intensidades de carbono para algum país
    if any([len(intensities[zone]) == 0 for zone in zones]):
        st.error("Houve um problema ao buscar as intensidades de carbono para um dos países selecionados.")
    else:
        # Exibir a tabela de intensidades de carbono com as unidades
        df_intensities = pd.DataFrame(intensities).T
        df_intensities.index.name = 'Zone'
        df_intensities.columns.name = 'Hour'
        df_intensities = df_intensities.rename(columns={h: f'{h}: gCO2/kWh' for h in df_intensities.columns})
        st.dataframe(df_intensities)

        # Exibir gráficos de barras abaixo da tabela
        for zone in zones:
            st.subheader(f"Carbon Intensity for {zone}")
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(range(24), intensities[zone], color='blue')
            ax.set_title(f"Carbon Intensity for {zone}")
            ax.set_xlabel("Hour")
            ax.set_ylabel("Carbon Intensity (gCO2/kWh)")
            st.pyplot(fig)

# User input for charging values
st.subheader("Charging Values for Each Company")

# Option to upload a CSV file
uploaded_file = st.file_uploader("Upload a CSV file", type="csv")

# Add an information button about CSV rules
if st.button("📄 CSV Info"):
    st.markdown("""
            <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px;">
                The CSV file must contain the following columns: 'Hour', 'Company 1', 'Company 2', and 'Company 3'. <br>
                Each column must contain 24 values representing the hours of the day, with 'Company X' values in kW (kilowatts).
            </div>
        """, unsafe_allow_html=True)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    if 'Hour' in df.columns and 'Company 1 (kW)' in df.columns and 'Company 2 (kW)' in df.columns and 'Company 3 (kW)' in df.columns:
        charging_company_1 = df['Company 1 (kW)'].values
        charging_company_2 = df['Company 2 (kW)'].values
        charging_company_3 = df['Company 3 (kW)'].values
    else:
        st.error("CSV file must contain 'Hour', 'Company 1', 'Company 2', and 'Company 3' columns.")
else:
    # Use default values if no file is uploaded
    st.write("Using default values for the companies:")
    st.dataframe(pd.DataFrame(default_charging_values))
    charging_company_1 = np.array(default_charging_values['Company 1 (kW)'])
    charging_company_2 = np.array(default_charging_values['Company 2 (kW)'])
    charging_company_3 = np.array(default_charging_values['Company 3 (kW)'])

# Total charging for each company
total_charging_company_1 = np.sum(charging_company_1)
total_charging_company_2 = np.sum(charging_company_2)
total_charging_company_3 = np.sum(charging_company_3)

# Handling dynamic country selection for emissions
if len(zones) >= 1:
    emissions_company_1, hourly_emissions_company_1 = calculate_daily_emissions(charging_company_1,
                                                                                intensities[zones[0]])
if len(zones) >= 2:
    emissions_company_2, hourly_emissions_company_2 = calculate_daily_emissions(charging_company_2,
                                                                                intensities[zones[1]])
if len(zones) == 3:
    emissions_company_3, hourly_emissions_company_3 = calculate_daily_emissions(charging_company_3,
                                                                                intensities[zones[2]])

# Calculate best and worst scenarios based on available zones
best_case_1, worst_case_1 = calculate_scenarios(total_charging_company_1, intensities[zones[0]])
best_case_2, worst_case_2 = calculate_scenarios(total_charging_company_2, intensities[zones[1]])
if len(zones) == 3:
    best_case_3, worst_case_3 = calculate_scenarios(total_charging_company_3, intensities[zones[2]])

# Score calculation
score_1 = calculate_score(emissions_company_1, best_case_1, worst_case_1)
score_2 = calculate_score(emissions_company_2, best_case_2, worst_case_2)
if len(zones) == 3:
    score_3 = calculate_score(emissions_company_3, best_case_3, worst_case_3)

# Calculate detailed percentages for ranking
percent_away_best_1, percent_away_worst_1 = calculate_percentages(emissions_company_1, best_case_1, worst_case_1)
percent_away_best_2, percent_away_worst_2 = calculate_percentages(emissions_company_2, best_case_2, worst_case_2)
if len(zones) == 3:
    percent_away_best_3, percent_away_worst_3 = calculate_percentages(emissions_company_3, best_case_3, worst_case_3)

# Prepare ranking data based on the number of selected countries
companies = ['Company 1', 'Company 2']
scores = [score_1, score_2]
percent_away_best = [percent_away_best_1, percent_away_best_2]
percent_away_worst = [percent_away_worst_1, percent_away_worst_2]

if len(zones) == 3:
    companies.append('Company 3')
    scores.append(score_3)
    percent_away_best.append(percent_away_best_3)
    percent_away_worst.append(percent_away_worst_3)

df_ranking = pd.DataFrame(list(zip(companies, scores, percent_away_best, percent_away_worst)),
                          columns=["Company", "Score", "% away from Best Scenario", "% away from Worst Scenario"])


# Apply conditional styles with arrows
def style_percentages(value, scenario):
    if scenario == "best":
        return f"🔺{value:.2f}%"
    elif scenario == "worst":
        return f"🔻{value:.2f}%"


df_ranking["% away from Best Scenario"] = df_ranking.apply(
    lambda row: style_percentages(row["% away from Best Scenario"], "best"), axis=1)
df_ranking["% away from Worst Scenario"] = df_ranking.apply(
    lambda row: style_percentages(row["% away from Worst Scenario"], "worst"), axis=1)

# Display ranking table
st.subheader("Overall Company Ranking")
st.dataframe(df_ranking.style.applymap(lambda x: 'color: red' if isinstance(x, str) and x.startswith('🔺') else (
    'color: green' if isinstance(x, str) and x.startswith('🔻') else '')).set_table_styles([{
    'selector': 'td',
    'props': [
        ('max-width', '200px'), ('font-size', '12px')]}]))

