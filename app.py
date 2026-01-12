import streamlit as st
import yfinance as yf
import pandas as pd

# --- CONFIGURAÇÃO DA SUA CARTEIRA ---
MEUS_TICKERS = [
    "ALLD3.SA", "ALOS3.SA", "BBAS3.SA", "BHIA3.SA", "CMIG4.SA",
    "EMBJ3.SA", "FLRY3.SA", "GMAT3.SA", "GUAR3.SA", "HAPV3.SA",
    "ISAE4.SA", "ITSA4.SA", "ITUB4.SA", "IVVB11.SA", "KLBN4.SA",
    "MBRF3.SA", "MTRE3.SA", "OCCI", "PETR4.SA", "RAIL3.SA",
    "RDOR3.SA", "SANB4.SA", "UGPA3.SA", "VALE3.SA", "VULC3.SA",
    "WEGE3.SA"
]

st.set_page_config(page_title="Monitor RSI", layout="centered")
st.title("📊 Monitor de Mercado")

# Cabeçalho da Tabela (Colunas)
# Ajuste dos números abaixo muda a largura de cada coluna
col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.2, 2.5])
col1.markdown("**Ativo**")
col2.markdown("**Preço**")
col3.markdown("**RSI**")
col4.markdown("**Status**")
st.divider() # Linha separadora

# Função de Análise
def analisar_ativo(ticker):
    try:
        df = yf.download(ticker, period="3mo", progress=False)
        if len(df) < 15: return None

        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        rsi_val = rsi.iloc[-1]
        if isinstance(rsi_val, pd.Series): rsi_val = rsi_val.item()
        
        preco_val = df['Close'].iloc[-1]
        if isinstance(preco_val, pd.Series): preco_val = preco_val.item()
        
        return rsi_val, preco_val
    except:
        return None

# Loop para criar as linhas
for ticker in MEUS_TICKERS:
    dados = analisar_ativo(ticker)
    
    if dados:
        rsi, preco = dados
        nome_ativo = ticker.replace('.SA', '')
        
        # Lógica de Cores e Ícones
        if rsi <= 30:
            status = "🟢 COMPRA"
            cor_rsi = "green"
            icone = "🟢"
        elif rsi >= 70:
            status = "🔴 VENDA"
            cor_rsi = "red"
            icone = "🔴"
        else:
            status = "Neutro"
            cor_rsi = "gray"
            icone = "⚪"

        # Criação das Colunas da Linha
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.2, 2.5])
        
        with c1:
            st.write(f"**{nome_ativo}**")
        with c2:
            st.write(f"R$ {preco:.2f}")
        with c3:
            # Pinta o número do RSI com a cor correspondente
            st.markdown(f":{cor_rsi}[{rsi:.0f}]")
        with c4:
            st.markdown(f":{cor_rsi}[**{status}**]")
        
        # Linha fina entre cada ativo para organizar
        st.markdown("<hr style='margin: 0px; opacity: 0.2;'>", unsafe_allow_html=True)
