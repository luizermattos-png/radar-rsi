import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Análise Técnica", layout="wide")

# Título Principal
st.title("📊 Análise Profunda de Ações")

# Sidebar para inserir o código da ação
ticker = st.sidebar.text_input("Digite o Ticker da Ação (ex: ALLD3.SA):", value="ALLD3.SA").upper()
periodo = st.sidebar.selectbox("Período", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2)

if st.button("Analisar Ação") or ticker:
    try:
        # Baixar dados
        dados = yf.download(ticker, period=periodo)
        
        if len(dados) == 0:
            st.error(f"Não foram encontrados dados para o ticker {ticker}. Verifique se está correto.")
        else:
            st.subheader(f"Análise Profunda: {ticker}")
            
            # Criar médias móveis para complementar a análise
            dados['MA9'] = dados['Close'].rolling(window=9).mean()
            dados['MA21'] = dados['Close'].rolling(window=21).mean()

            # --- CRIAÇÃO DO GRÁFICO (AQUI ESTAVA O ERRO, AGORA CORRIGIDO) ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, subplot_titles=('Preço e Médias', 'Volume'),
                                row_width=[0.2, 0.7])

            # Gráfico de Candlestick
            fig.add_trace(go.Candlestick(x=dados.index,
                                         open=dados['Open'], high=dados['High'],
                                         low=dados['Low'], close=dados['Close'], name='Candles'), 
                          row=1, col=1)

            # Médias Móveis
            fig.add_trace(go.Scatter(x=dados.index, y=dados['MA9'], line=dict(color='cyan', width=1), name='Média 9'), row=1, col=1)
            fig.add_trace(go.Scatter(x=dados.index, y=dados['MA21'], line=dict(color='orange', width=1), name='Média 21'), row=1, col=1)

            # Gráfico de Volume
            fig.add_trace(go.Bar(x=dados.index, y=dados['Volume'], name='Volume'), row=2, col=1)

            # --- CORREÇÃO DO LAYOUT ---
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=600,
                showlegend=True,
                margin=dict(l=20, r=20, t=40, b=20),
                # A CORREÇÃO PRINCIPAL ESTÁ AQUI EMBAIXO:
                yaxis=dict(
                    title=dict(
                        text="Preço (R$)",  # O texto fica aqui
                        font=dict(size=14, color="white") # A fonte fica aqui DENTRO de title
                    ),
                    showgrid=True, 
                    gridcolor='rgba(128,128,128,0.2)'
                ),
                yaxis2=dict(
                    title=dict(
                        text="Volume",
                        font=dict(size=12, color="white")
                    ),
                    showgrid=False
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)', # Fundo transparente para combinar com tema dark
                font=dict(color="white") # Fonte geral branca
            )

            # Exibir gráfico no Streamlit
            st.plotly_chart(fig, use_container_width=True)

            # Exibir dados brutos (opcional)
            with st.expander("Ver dados brutos"):
                st.dataframe(dados.tail(10))

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os dados: {e}")
