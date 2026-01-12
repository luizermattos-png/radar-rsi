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

st.set_page_config(page_title="Monitor Pro", layout="centered")

# --- CABEÇALHO ---
st.title("📊 Monitor Pro")
data_atual = datetime.now().strftime("%d/%m/%Y")
st.caption(f"📅 {data_atual} | RSI (14) + Tendência (MM50)")
st.divider()

# Função de Análise
def analisar_ativo(ticker):
    try:
        # Baixamos 6 meses para garantir dados para a Média de 50
        df = yf.download(ticker, period="6mo", progress=False)
        if len(df) < 50: return None

        # 1. RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 2. Tendência (MM50)
        df['MM50'] = df['Close'].rolling(window=50).mean()
        
        # Valores atuais
        rsi_val = rsi.iloc[-1]
        if isinstance(rsi_val, pd.Series): rsi_val = rsi_val.item()
        
        preco_val = df['Close'].iloc[-1]
        if isinstance(preco_val, pd.Series): preco_val = preco_val.item()
        
        mm50_val = df['MM50'].iloc[-1]
        if isinstance(mm50_val, pd.Series): mm50_val = mm50_val.item()
        
        # Lógica da Tendência
        tendencia = "⬆️ Alta" if preco_val > mm50_val else "⬇️ Baixa"
        
        return {
            'ticker': ticker.replace('.SA', ''), 
            'rsi': rsi_val, 
            'preco': preco_val,
            'tendencia': tendencia
        }
    except:
        return None

# Listas
oportunidades = []
alertas = []
neutros = []

barra = st.progress(0)

for i, ticker in enumerate(MEUS_TICKERS):
    dados = analisar_ativo(ticker)
    if dados:
        if dados['rsi'] <= 30:
            oportunidades.append(dados)
        elif dados['rsi'] >= 70:
            alertas.append(dados)
        else:
            neutros.append(dados)
    barra.progress((i + 1) / len(MEUS_TICKERS))

barra.empty()

# --- FUNÇÃO DE DESENHO ---
def desenhar_tabela(lista_ativos, cor_destaque, icone_titulo, titulo):
    if len(lista_ativos) > 0:
        st.markdown(f"### {icone_titulo} {titulo}")
        c1, c2, c3, c4 = st.columns([1.5, 1.2, 1.5, 1.5])
        c1.markdown("**Ativo**")
        c2.markdown("**RSI**")
        c3.markdown("**Tend.**")
        c4.markdown("**Preço**")
        
        for item in lista_ativos:
            with st.container():
                col1, col2, col3, col4 = st.columns([1.5, 1.2, 1.5, 1.5])
                col1.write(f"**{item['ticker']}**")
                col2.markdown(f":{cor_destaque}[**{item['rsi']:.0f}**]")
                cor_tend = "green" if "Alta" in item['tendencia'] else "red"
                col3.markdown(f":{cor_tend}[{item['tendencia']}]")
                col4.write(f"{item['preco']:.2f}")
                st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)

# --- EXIBIÇÃO ---
if oportunidades:
    st.success(f"{len(oportunidades)} Oportunidades Detectadas")
    desenhar_tabela(oportunidades, "green", "🟢", "COMPRA (RSI Baixo)")
else:
    st.info("Sem oportunidades claras de RSI agora.")

st.divider()

if alertas:
    desenhar_tabela(alertas, "red", "🔴", "VENDA (RSI Alto)")
    st.divider()

with st.expander(f"Ver Neutros ({len(neutros)})", expanded=True):
    desenhar_tabela(neutros, "gray", "⚪", "Observar")

st.write("")
st.write("")

# --- GUIA DE LEITURA (NOVO) ---
with st.expander("📚 Guia Rápido: Como analisar este Monitor?"):
    st.markdown("""
    ### 1. O que é o RSI?
    * **Abaixo de 30 (Verde):** O preço caiu muito rápido. O mercado pode estar exagerando no pessimismo. **Possível Compra.**
    * **Acima de 70 (Vermelho):** O preço subiu muito rápido. O mercado pode estar eufórico. **Possível Venda.**

    ### 2. O Segredo da Tendência (Seta)
    A seta mostra a Média Móvel de 50 dias:
    * ⬆️ **Alta:** O preço está ACIMA da média. A "maré" está a subir.
    * ⬇️ **Baixa:** O preço está ABAIXO da média. A "maré" está a descer.

    ### 3. As Combinações (Estratégia)
    * 💎 **Ouro (RSI Baixo + Tendência Alta):** O ativo está numa tendência de alta, mas caiu temporariamente ("pullback"). É a melhor chance de comprar barato.
    * ⚠️ **Faca Caindo (RSI Baixo + Tendência Baixa):** O ativo está barato, mas a tendência é de queda forte. Cuidado, pode cair mais.
    * 🚀 **Foguete (RSI Alto + Tendência Alta):** O ativo está forte, mas pode estar caro agora. Esperar recuar um pouco.
    """)

if st.button('Atualizar'):
    st.rerun()
