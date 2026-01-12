import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

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

# --- CABEÇALHO COM DATA ---
st.title("📊 Monitor de Mercado")
data_atual = datetime.now().strftime("%d/%m/%Y")
st.subheader(f"📅 Data do Relatório: {data_atual}")
st.divider()

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
        
        return {'ticker': ticker.replace('.SA', ''), 'rsi': rsi_val, 'preco': preco_val}
    except:
        return None

# Listas para separar as categorias
oportunidades = []
alertas = []
neutros = []

# Barra de progresso visual enquanto carrega
texto_carregando = st.empty()
texto_carregando.text("A analisar o mercado... Por favor aguarde.")
barra = st.progress(0)

# Processamento dos dados
for i, ticker in enumerate(MEUS_TICKERS):
    dados = analisar_ativo(ticker)
    if dados:
        if dados['rsi'] <= 30:
            oportunidades.append(dados)
        elif dados['rsi'] >= 70:
            alertas.append(dados)
        else:
            neutros.append(dados)
    # Atualiza barra de progresso
    barra.progress((i + 1) / len(MEUS_TICKERS))

texto_carregando.empty() # Limpa o texto de carregamento
barra.empty() # Limpa a barra

# --- FUNÇÃO PARA DESENHAR AS TABELAS ---
def desenhar_tabela(lista_ativos, cor_titulo, icone_titulo, titulo_secao):
    if len(lista_ativos) > 0:
        st.markdown(f"### {icone_titulo} {titulo_secao}")
        
        # Cabeçalho das Colunas
        c1, c2, c3 = st.columns([1.5, 1.5, 1.5])
        c1.markdown("**Ativo**")
        c2.markdown("**Preço**")
        c3.markdown("**RSI**")
        
        for item in lista_ativos:
            with st.container():
                col1, col2, col3 = st.columns([1.5, 1.5, 1.5])
                col1.write(f"**{item['ticker']}**")
                col2.write(f"R$ {item['preco']:.2f}")
                col3.markdown(f":{cor_titulo}[**{item['rsi']:.0f}**]")
                st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)
        st.write("") # Espaço extra

# --- EXIBIÇÃO POR CATEGORIAS ---

# 1. Oportunidades (Verde) - Destaque
if len(oportunidades) > 0:
    st.success(f"Encontradas {len(oportunidades)} Oportunidades de Compra!")
    desenhar_tabela(oportunidades, "green", "🟢", "ZONA DE COMPRA (RSI < 30)")
else:
    st.info("Nenhuma oportunidade de compra clara hoje.")

st.divider()

# 2. Alertas (Vermelho)
if len(alertas) > 0:
    desenhar_tabela(alertas, "red", "🔴", "ALERTA DE VENDA (RSI > 70)")
    st.divider()

# 3. Neutros (Cinza)
with st.expander(f"Ver Ativos Neutros ({len(neutros)})", expanded=True):
    desenhar_tabela(neutros, "gray", "⚪", "Tendência Neutra")

# Botão de atualização
if st.button('Atualizar Dados Agora'):
    st.rerun()
