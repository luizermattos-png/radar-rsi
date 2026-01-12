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

st.set_page_config(page_title="Relatório Financeiro", layout="centered")
st.title("📊 Relatório de Mercado")
st.caption("Análise baseada no RSI (14 períodos)")

# Função para buscar dados e calcular RSI
def analisar_ativo(ticker):
    try:
        # Baixa 3 meses de dados para garantir cálculo preciso
        df = yf.download(ticker, period="3mo", progress=False)
        if len(df) < 15: return None # Dados insuficientes

        # Cálculo do RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Pega valores atuais
        # Tratamento seguro para garantir que pegamos um número, não uma Series
        rsi_atual = rsi.iloc[-1]
        if isinstance(rsi_atual, pd.Series): rsi_atual = rsi_atual.item()
        
        preco_atual = df['Close'].iloc[-1]
        if isinstance(preco_atual, pd.Series): preco_atual = preco_atual.item()
        
        return rsi_atual, preco_atual
    except:
        return None

# --- GERAÇÃO DO RELATÓRIO (UM ABAIXO DO OUTRO) ---
for ticker in MEUS_TICKERS:
    dados = analisar_ativo(ticker)
    
    if dados:
        rsi, preco = dados
        nome_ativo = ticker.replace('.SA', '')
        
        # Lógica de Recomendação
        if rsi <= 30:
            recomendacao = "🟢 OPORTUNIDADE DE COMPRA"
            cor_card = "background-color: #d4edda; padding: 10px; border-radius: 10px; border-left: 5px solid #28a745;"
            cor_texto = "green"
        elif rsi >= 70:
            recomendacao = "🔴 ALERTA DE VENDA (Caro)"
            cor_card = "background-color: #f8d7da; padding: 10px; border-radius: 10px; border-left: 5px solid #dc3545;"
            cor_texto = "red"
        else:
            recomendacao = "⚪ NEUTRO (Aguardar)"
            cor_card = "background-color: #e2e3e5; padding: 10px; border-radius: 10px; border-left: 5px solid #6c757d;"
            cor_texto = "gray"

        # Exibição Visual (Card)
        with st.container():
            st.markdown(f"""
            <div style="{cor_card} margin-bottom: 15px;">
                <h3 style="margin:0; color: black;">{nome_ativo}</h3>
                <h4 style="margin:0; color: black;">R$ {preco:.2f}</h4>
                <p style="margin:5px 0 0 0; font-weight:bold; color: {cor_texto};">
                    RSI: {rsi:.1f} | {recomendacao}
                </p>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Opcional: Mostra erro discreto se algum ativo falhar
        # st.error(f"Erro ao ler {ticker}")
        pass

# Botão de atualização
if st.button('Atualizar Cotações'):
    st.rerun()
