import streamlit as st
import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime

# CSS to customize the Streamlit style
st.markdown("""
    <style>
    .reportview-container {
        background: #f0f2f6;
        padding: 1.5rem;
    }
    .stMarkdown {
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 2rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .stDataFrame {
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .stPlotlyChart {
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)

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

# CSS to customize the Streamlit style
st.markdown("""
    <style>
    .reportview-container {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .logo-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        margin-bottom: 20px; /* Espaço entre o logotipo e o conteúdo abaixo */
    }
    .logo-container img {
        max-width: 150px; /* Largura máxima do logotipo */
    }
    </style>
""", unsafe_allow_html=True)

# Row for logos
col1, col2 = st.columns([1, 3])  # Ajusta a proporção das colunas
with col1:
    st.image("Captura de ecrã 2024-07-09 115045.png", use_column_width=True)

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

if len(zones) > 3:
    st.error("Please select only up to 3 countries.")

intensities = {}
for zone in zones:
    intensities[zone] = fetch_carbon_intensities(zone, date)

# Display the table of carbon intensities with units
df_intensities = pd.DataFrame(intensities).T
df_intensities.index.name = 'Zone'
df_intensities.columns.name = 'Hour'
df_intensities = df_intensities.rename(columns={h: f'{h}: gCO2/kWh' for h in df_intensities.columns})
st.dataframe(df_intensities)

# Display bar charts below the table
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

# Agora, você pode calcular as emissões para cada país selecionado
emissions = []
hourly_emissions = []
for i, zone in enumerate(zones):
    if zone in intensities:
        charging_values = [charging_company_1, charging_company_2, charging_company_3][i]
        emissions_company, hourly_emissions_company = calculate_daily_emissions(
            charging_values, intensities[zone])
        emissions.append(emissions_company)
        hourly_emissions.append(hourly_emissions_company)
    else:
        st.error(f"Nenhum dado disponível para a zona {zone}.")

# Cálculo dos cenários para cada empresa
best_cases = []
worst_cases = []
for i, zone in enumerate(zones):
    if zone in intensities:
        total_charging = np.sum([charging_company_1, charging_company_2, charging_company_3][i])
        best_case, worst_case = calculate_scenarios(total_charging, intensities[zone])
        best_cases.append(best_case)
        worst_cases.append(worst_case)

# Cálculo dos scores
scores = []
for i in range(len(emissions)):
    score = calculate_score(emissions[i], best_cases[i], worst_cases[i])
    scores.append(score)

# Criação da tabela de ranking
companies = ['Company 1', 'Company 2', 'Company 3']
df_ranking = pd.DataFrame({
    "Company": companies,
    "Score": scores,
    "% away from Best Scenario": [(calculate_percentages(emissions[i], best_cases[i], worst_cases[i])[0]) for i in range(len(emissions))],
    "% away from Worst Scenario": [(calculate_percentages(emissions[i], best_cases[i], worst_cases[i])[1]) for i in range(len(emissions))]
})

# Exibição da tabela de ranking
st.subheader("Overall Company Ranking")

# Style scores with arrows
df_ranking['Score'] = df_ranking['Score'].apply(style_score)
st.dataframe(df_ranking)
