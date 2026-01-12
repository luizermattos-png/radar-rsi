import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# CONFIGURAÇÃO INICIAL DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Análise Técnica - Códice",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# FUNÇÕES AUXILIARES (CÁLCULOS E DADOS)
# ==========================================

def carregar_dados(ticker):
    """Baixa dados do Yahoo Finance"""
    # Adiciona .SA se não tiver (padrão B3)
    if not ticker.endswith('.SA') and not ticker.endswith('.sa'):
        ticker = f"{ticker}.SA"
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365) # 1 ano de dados
    
    df = yf.download(ticker, start=start_date, end=end_date)
    
    if len(df) == 0:
        return None
    
    # Ajuste para garantir colunas planas (caso venha MultiIndex)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    return df

def calcular_indicadores(df):
    """Calcula RSI e Médias Móveis"""
    # RSI (Índice de Força Relativa) - 14 períodos
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Médias Móveis
    df['MMA9'] = df['Close'].rolling(window=9).mean()
    df['MMA21'] = df['Close'].rolling(window=21).mean()
    
    return df

# ==========================================
# GERENCIAMENTO DE ESTADO (NAVEGAÇÃO)
# ==========================================
if 'tela' not in st.session_state:
    st.session_state['tela'] = 'lista'
if 'ativo_atual' not in st.session_state:
    st.session_state['ativo_atual'] = ''

def ir_para_analise(ticker):
    st.session_state['ativo_atual'] = ticker
    st.session_state['tela'] = 'analise'

def voltar_para_lista():
    st.session_state['tela'] = 'lista'

# ==========================================
# TELA 1: LISTA DE ATIVOS (HOME)
# ==========================================
if st.session_state['tela'] == 'lista':
    st.title("📈 Monitor de Ações")
    st.write("Digite o código da ação para análise técnica.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker_input = st.text_input("Ticker (ex: ALLD3, PETR4)", value="ALLD3").upper()
    with col2:
        st.write("") # Espaçamento
        st.write("") 
        if st.button("Analisar Ação", use_container_width=True):
            ir_para_analise(ticker_input)

    st.info("Dica: O gráfico na próxima tela já inclui a correção do erro de fonte do Plotly.")

# ==========================================
# TELA 2: ANÁLISE PROFUNDA (GRÁFICO)
# ==========================================
elif st.session_state['tela'] == 'analise':
    
    # Botão de Voltar (Como na sua imagem)
    if st.button("⬅ Voltar para a Lista"):
        voltar_para_lista()
        st.rerun()

    ticker = st.session_state['ativo_atual']
    st.title(f"📊 Análise Profunda: {ticker}")

    with st.spinner('Carregando dados...'):
        df = carregar_dados(ticker)

    if df is None:
        st.error(f"Não foi possível encontrar dados para {ticker}. Verifique o código.")
    else:
        # Calcular indicadores
        df = calcular_indicadores(df)
        
        # Último preço
        ultimo_preco = df['Close'].iloc[-1]
        ultimo_rsi = df['RSI'].iloc[-1]
        
        # Métricas no topo
        m1, m2, m3 = st.columns(3)
        m1.metric("Preço Atual", f"R$ {ultimo_preco:.2f}")
        m2.metric("RSI (14)", f"{ultimo_rsi:.1f}", delta_color="off")
        m3.metric("Tendência (M9)", "Alta" if df['Close'].iloc[-1] > df['MMA9'].iloc[-1] else "Baixa")

        # --- CRIAÇÃO DO GRÁFICO (CORRIGIDO) ---
        fig = go.Figure()

        # Candles
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name='Preço'
        ))

        # Médias Móveis
        fig.add_trace(go.Scatter(x=df.index, y=df['MMA9'], line=dict(color='cyan', width=1), name='Média 9'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MMA21'], line=dict(color='orange', width=1), name='Média 21'))

        # Layout com a CORREÇÃO do 'titlefont'
        fig.update_layout(
            title=f"Gráfico Diário - {ticker}",
            height=600,
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            yaxis=dict(
                # --- AQUI ESTÁ A CORREÇÃO ---
                # Antes (Errado): titlefont=dict(...)
                # Agora (Certo): title=dict(text="...", font=dict(...))
                title=dict(
                    text="Preço (R$)",
                    font=dict(size=14, color="white")
                ),
                showgrid=True,
                gridcolor='rgba(128,128,128,0.2)'
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        st.plotly_chart(fig, use_container_width=True)

        # Dados em tabela
        with st.expander("Ver dados históricos"):
            st.dataframe(df.tail(10).style.format("{:.2f}"))
