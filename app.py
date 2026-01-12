import streamlit as st
import yfinance as yf
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Radar RSI", layout="centered")

st.title("🎯 Radar de Oportunidades")

# 1. Seleção da Ação
ticker = st.selectbox(
    "Escolha o Ativo:",
    ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBAS3.SA", "BTC-USD"]
)

# 2. Baixar Dados e Calcular
@st.cache_data
def get_data(ticker):
    try:
        df = yf.download(ticker, period="60d", progress=False)
        if df.empty:
            return pd.DataFrame()
            
        # Calcular RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        return df
    except Exception as e:
        st.error(f"Erro ao obter dados: {e}")
        return pd.DataFrame()

df = get_data(ticker)

if not df.empty and 'RSI' in df.columns:
    rsi_atual = df['RSI'].iloc[-1]
    preco_atual = df['Close'].iloc[-1]

    # 3. Mostrador Gigante
    col1, col2 = st.columns(2)
    
    # Tratamento para float ou Series
    p_atual = float(preco_atual) if not isinstance(preco_atual, float) else preco_atual
    r_atual = float(rsi_atual) if not isinstance(rsi_atual, float) else rsi_atual

    col1.metric("Preço Atual", f"R$ {p_atual:.2f}")
    
    if r_atual <= 30:
        st.success(f"🟢 RSI: {r_atual:.1f} - SOBREVENDIDO (Oportunidade?)")
    elif r_atual >= 70:
        st.error(f"🔴 RSI: {r_atual:.1f} - SOBRECOMPRADO (Cuidado?)")
    else:
        st.info(f"⚪ RSI: {r_atual:.1f} - Neutro")

    # 4. Gráfico
    st.line_chart(df['RSI'])
    st.caption("A linha mostra a tendência do RSI nos últimos 60 dias.")
else:
    st.warning("A aguardar dados...")