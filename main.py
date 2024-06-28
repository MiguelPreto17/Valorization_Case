import streamlit as st
import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt

# CSS para personalizar o estilo do Streamlit
st.markdown("""
    <style>
    .reportview-container {
        background: #f0f2f6
;
        padding: 1.5rem;
    }
    .stMarkdown {
        background-color: #f0f2f6
;
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

# Função para buscar intensidades de carbono para uma zona específica no dia anterior
def fetch_carbon_intensities(zone):
    url = "https://api.electricitymap.org/v3/carbon-intensity/history"
    params = {"zone": zone}
    headers = {"auth-token": "YOUR_API_TOKEN"}
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return [entry["carbonIntensity"] for entry in data["history"]][-24:]
    else:
        st.error("Failed to fetch carbon intensities.")
        return []

# Função para calcular emissões totais diárias
def calculate_daily_emissions(charging, emissions):
    hourly_emissions = charging * emissions
    daily_emissions = np.sum(hourly_emissions)
    return daily_emissions, hourly_emissions

# Função para calcular os cenários de emissões
def calculate_scenarios(total_charging, emissions):
    emissions_sorted_asc = np.sort(emissions)
    emissions_sorted_desc = np.sort(emissions)[::-1]

    hourly_capacity = 10  # Definir capacidade por hora como 10
    hours_needed = int(np.ceil(total_charging / hourly_capacity))

    best_case = hourly_capacity * emissions_sorted_asc[:hours_needed]
    worst_case = hourly_capacity * emissions_sorted_desc[:hours_needed]

    best_case_total = np.sum(best_case)
    worst_case_total = np.sum(worst_case)

    return best_case_total, worst_case_total

# Calcular o score usando a nova abordagem
def calculate_score(actual_emissions, best_case, worst_case):
    return (actual_emissions - best_case) / (worst_case - best_case)

# Calcular as porcentagens detalhadas
def calculate_percentages(actual_emissions, best_case, worst_case):
    away_best = ((actual_emissions - best_case) / best_case) * 100
    away_worst = ((worst_case - actual_emissions) / worst_case) * 100
    return away_best, away_worst

# Streamlit UI
st.title("Electric Vehicle Charging Impact Analysis")


st.subheader("Carbon Intensities for Each Zone")

zones = ["DE", "IT", "PT"]
intensities = {}
for zone in zones:
    intensities[zone] = fetch_carbon_intensities(zone)

# Utilizar colunas para exibir a tabela e o gráfico lado a lado
col1, col2 = st.columns(2)

with col1:
    # Tabela de intensidades de carbono
    df_intensities = pd.DataFrame(intensities)
    st.dataframe(df_intensities)

with col2:
    # Plot das intensidades de carbono
    plt.figure(figsize=(10, 5))
    for zone in zones:
        plt.plot(intensities[zone], label=zone)
    plt.legend()
    plt.title("Carbon Intensities for Each Zone")
    plt.xlabel("Hour")
    plt.ylabel("Carbon Intensity (gCO2/kWh)")
    st.pyplot(plt)

# Entrada de usuário para os valores de carregamento
st.subheader("Charging Values for Each Company")

charging_company_1 = []
charging_company_2 = []
charging_company_3 = []

st.write("Enter 24 hourly values for each company:")

for i in range(24):
    col1, col2, col3 = st.columns(3)
    with col1:
        charging_company_1.append(st.number_input(f'Company 1 - Hour {i}', min_value=0, max_value=100, value=5))
    with col2:
        charging_company_2.append(st.number_input(f'Company 2 - Hour {i}', min_value=0, max_value=100, value=5))
    with col3:
        charging_company_3.append(st.number_input(f'Company 3 - Hour {i}', min_value=0, max_value=100, value=5))

charging_company_1 = np.array(charging_company_1)
charging_company_2 = np.array(charging_company_2)
charging_company_3 = np.array(charging_company_3)

total_charging_company_1 = np.sum(charging_company_1)
total_charging_company_2 = np.sum(charging_company_2)
total_charging_company_3 = np.sum(charging_company_3)

emissions_company_1, hourly_emissions_company_1 = calculate_daily_emissions(charging_company_1, intensities["DE"])
emissions_company_2, hourly_emissions_company_2 = calculate_daily_emissions(charging_company_2, intensities["IT"])
emissions_company_3, hourly_emissions_company_3 = calculate_daily_emissions(charging_company_3, intensities["PT"])

best_case_1, worst_case_1 = calculate_scenarios(total_charging_company_1, intensities["DE"])
best_case_2, worst_case_2 = calculate_scenarios(total_charging_company_2, intensities["IT"])
best_case_3, worst_case_3 = calculate_scenarios(total_charging_company_3, intensities["PT"])

score_1 = calculate_score(emissions_company_1, best_case_1, worst_case_1)
score_2 = calculate_score(emissions_company_2, best_case_2, worst_case_2)
score_3 = calculate_score(emissions_company_3, best_case_3, worst_case_3)

percent_away_best_1, percent_away_worst_1 = calculate_percentages(emissions_company_1, best_case_1, worst_case_1)
percent_away_best_2, percent_away_worst_2 = calculate_percentages(emissions_company_2, best_case_2, worst_case_2)
percent_away_best_3, percent_away_worst_3 = calculate_percentages(emissions_company_3, best_case_3, worst_case_3)

companies = ['Company 1', 'Company 2', 'Company 3']
scores = [score_1, score_2, score_3]
percent_away_best = [percent_away_best_1, percent_away_best_2, percent_away_best_3]
percent_away_worst = [percent_away_worst_1, percent_away_worst_2, percent_away_worst_3]
ranking = sorted(zip(companies, scores, percent_away_best, percent_away_worst), key=lambda x: x[1])

# Criar DataFrame com dados de ranking e estilizar com setas coloridas
df_ranking = pd.DataFrame(ranking, columns=["Company", "Score", "% away from Best Scenario", "% away from Worst Scenario"])

# Função para aplicar estilos condicionais com setas
def style_percentages(value, scenario):
    if scenario == "best":
        return f"+{value:.2f}%"
    elif scenario == "worst":
        return f"-{value:.2f}%"

df_ranking["% away from Best Scenario"] = df_ranking.apply(lambda row: style_percentages(row["% away from Best Scenario"], "best"), axis=1)
df_ranking["% away from Worst Scenario"] = df_ranking.apply(lambda row: style_percentages(row["% away from Worst Scenario"], "worst"), axis=1)

# Ajuste de estilo na tabela
st.subheader("Overall Company Ranking")
st.dataframe(df_ranking.style.applymap(lambda x: 'color: green' if isinstance(x, str) and x.startswith('+') else ('color: red' if isinstance(x, str) and x.startswith('-') else '')).set_table_styles([{
    'selector': 'td',
    'props': [
        ('max-width', '200px'), ('font-size', '12px')]
}]))

# Ajuste de estilo na tabela
st.markdown(
    """
    <style>
    .stDataFrame tbody tr:nth-child(even) {
        background-color: #f0f2f6;
    }
    .stDataFrame tbody tr:nth-child(odd) {
        background-color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True
)












