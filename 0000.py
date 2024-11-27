import pandas as pd
import streamlit as st
import plotly.express as px

# Configuração da aplicação
st.set_page_config(page_title="Gestão de Resíduos Sólidos Urbanos", layout="wide")
st.title("📊 Gestão de Resíduos Sólidos Urbanos")
st.sidebar.header("Configurações de Entrada")

# Função para carregar os dados das tabelas
@st.cache_data
def carregar_tabelas(tabela1_path, tabela2_path):
    """Carrega e retorna os dados das duas tabelas fornecidas."""
    gravimetria_data = pd.read_excel(tabela1_path)
    resumo_fluxo_data = pd.read_excel(tabela2_path)
    gravimetria_data.columns = gravimetria_data.columns.str.strip()  # Remove espaços das colunas
    resumo_fluxo_data.columns = resumo_fluxo_data.columns.str.strip()  # Remove espaços das colunas
    return gravimetria_data, resumo_fluxo_data

# Percentuais fixos para materiais de entulho
percentuais_entulho = {
    "Concreto": 0.0677, "Argamassa": 0.1065, "Tijolo": 0.078, "Madeira": 0.0067,
    "Papel": 0.0023, "Plástico": 0.0034, "Metal": 0.0029, "Material agregado": 0.0484,
    "Terra bruta": 0.0931, "Pedra": 0.00192, "Caliça Retida": 0.3492,
    "Caliça Peneirada": 0.2, "Cerâmica": 0.0161, "Material orgânico e galhos": 0.0087,
    "Outros": 0
}

def calcular_fluxo_ajustado(gravimetria_data, resumo_fluxo_data):
    """Calcula o fluxo ajustado com base nos dados de gravimetria e resumo."""
    fluxo_ajustado = []
    for _, row in resumo_fluxo_data.iterrows():
        uf = row["UF"]
        unidade = row["Tipo de unidade, segundo o município informante"]
        ajuste_residuos = {"UF": uf, "Unidade": unidade}

        for residuo in ["Dom+Pub", "Entulho", "Podas", "Saúde", "Outros"]:
            if residuo in resumo_fluxo_data.columns:
                gravimetricos = gravimetria_data[
                    gravimetria_data["Tipo de unidade, segundo o município informante"] == unidade
                ]
                if not gravimetricos.empty:
                    gravimetricos = gravimetricos.iloc[0]
                    if residuo == "Dom+Pub":
                        ajuste_residuos.update({
                            "Papel/Papelão": row[residuo] * gravimetricos.get("Papel/Papelão", 0),
                            "Plásticos": row[residuo] * gravimetricos.get("Plásticos", 0),
                            "Vidros": row[residuo] * gravimetricos.get("Vidros", 0),
                            "Metais": row[residuo] * gravimetricos.get("Metais", 0),
                            "Orgânicos": row[residuo] * gravimetricos.get("Orgânicos", 0),
                        })
                    elif residuo == "Entulho":
                        for material, percentual in percentuais_entulho.items():
                            ajuste_residuos[material] = row[residuo] * percentual
                    elif residuo == "Saúde":
                        ajuste_residuos["Valor energético (MJ/ton)"] = row[residuo] * gravimetricos.get(
                            "Valor energético p/Incineração", 0
                        )
                    elif residuo == "Podas":
                        ajuste_residuos["Redução Peso Seco"] = row[residuo] * gravimetricos.get(
                            "Redução de peso seco com Podas", 0
                        )
                        ajuste_residuos["Redução Peso Líquido"] = row[residuo] * gravimetricos.get(
                            "Redução de peso Líquido com Podas", 0
                        )
                    elif residuo == "Outros":
                        ajuste_residuos["Outros Processados"] = row[residuo] * gravimetricos.get("Outros", 0)
        fluxo_ajustado.append(ajuste_residuos)
    return pd.DataFrame(fluxo_ajustado)

# Upload de arquivos
tabela1_path = st.sidebar.file_uploader("Carregue a Tabela 1 (Gravimetria por Tipo de Unidade)", type=["xlsx"])
tabela2_path = st.sidebar.file_uploader("Carregue a Tabela 2 (Resumo por Unidade e UF)", type=["xlsx"])

if tabela1_path and tabela2_path:
    gravimetria_data, resumo_fluxo_data = carregar_tabelas(tabela1_path, tabela2_path)
    st.success("✅ Tabelas carregadas com sucesso!")
    fluxo_ajustado = calcular_fluxo_ajustado(gravimetria_data, resumo_fluxo_data)

    # Exibição de totais por UF e por tipo de unidade
    st.header("📋 Resumo Geral por UF e Tipo de Unidade")
    resumo_por_uf = fluxo_ajustado.groupby("UF").sum(numeric_only=True).reset_index()
    resumo_por_tipo_unidade = fluxo_ajustado.groupby("Unidade").sum(numeric_only=True).reset_index()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📍 Totais por UF")
        st.dataframe(resumo_por_uf)
    with col2:
        st.subheader("📍 Totais por Tipo de Unidade")
        st.dataframe(resumo_por_tipo_unidade)

    # Indicadores principais
    st.header("📊 Indicadores Totais e Comparativos")
    total_residuos = fluxo_ajustado.filter(regex="Papel|Plásticos|Vidros|Metais|Orgânicos|Concreto|Argamassa").sum().sum()
    total_entulho = fluxo_ajustado.filter(regex="Concreto|Argamassa|Tijolo").sum().sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Resíduos Processados (ton)", f"{total_residuos:,.2f}")
    col2.metric("Total de Entulho Processado (ton)", f"{total_entulho:,.2f}")
    col3.metric("Número de UFs", f"{resumo_por_uf['UF'].nunique()}")

    # Gráficos comparativos
    st.header("📈 Comparativos por Categorias de Resíduos")
    categorias = {
        "Urbanos": ["Plásticos", "Vidros", "Metais", "Orgânicos"],
        "Entulho": ["Concreto", "Argamassa", "Tijolo", "Madeira"],
    }

    for categoria, cols in categorias.items():
        cols = [col for col in cols if col in fluxo_ajustado.columns]
        if cols:
            st.subheader(f"📍 {categoria}")
            dados_categoria = fluxo_ajustado[["UF"] + cols].groupby("UF").sum().reset_index()
            fig_categoria = px.bar(dados_categoria, x="UF", y=cols, barmode="stack", title=f"{categoria} por UF")
            st.plotly_chart(fig_categoria, use_container_width=True)

    # Gráfico de proporções
    st.header("📊 Proporção de Resíduos por UF")
    proporcao_residuos = resumo_por_uf.set_index("UF").apply(lambda x: (x / x.sum()) * 100, axis=1)
    fig_proporcao = px.bar(proporcao_residuos.reset_index(), x="UF", y=proporcao_residuos.columns,
                           barmode="relative", title="Proporção de Resíduos por UF")
    st.plotly_chart(fig_proporcao, use_container_width=True)
