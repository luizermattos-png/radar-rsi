import streamlit as st
import yfinance as yf
import pandas as pd
import math
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

# CONFIGURAÇÃO DE TELA LARGA (DESKTOP)
st.set_page_config(page_title="Monitor Valuation Pro", layout="wide")

# --- CABEÇALHO ---
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.title("💎 Monitor Valuation & Momentum")
    st.caption("Estratégia Combinada: Benjamin Graham + Décio Bazin + RSI (Técnico)")
with c_head2:
    st.write("")
    st.write(f"📅 **{datetime.now().strftime('%d/%m/%Y')}**")

st.divider()

# Função de Análise
def analisar_ativo(ticker):
    try:
        obj_ticker = yf.Ticker(ticker)
        
        # 1. Dados Técnicos (Rápido)
        df = obj_ticker.history(period="6mo")
        if len(df) < 50: return None
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Tendência
        df['MM50'] = df['Close'].rolling(window=50).mean()
        
        preco_atual = df['Close'].iloc[-1]
        rsi_atual = rsi.iloc[-1]
        mm50_atual = df['MM50'].iloc[-1]
        tendencia = "⬆️ Alta" if preco_atual > mm50_atual else "⬇️ Baixa"

        # 2. Dados Fundamentais (Lento)
        info = obj_ticker.info
        
        # Graham
        lpa = info.get('trailingEps', 0)
        vpa = info.get('bookValue', 0)
        preco_graham = 0
        margem_graham = 0
        if lpa is not None and vpa is not None and lpa > 0 and vpa > 0:
            preco_graham = math.sqrt(22.5 * lpa * vpa)
            if preco_graham > 0:
                margem_graham = ((preco_graham - preco_atual) / preco_atual) * 100

        # Bazin
        div_yield_val = info.get('trailingAnnualDividendRate', 0)
        if div_yield_val is None or div_yield_val == 0:
             dy_percent = info.get('dividendYield', 0)
             if dy_percent: div_yield_val = dy_percent * preco_atual
        
        preco_bazin = 0
        if div_yield_val:
            preco_bazin = div_yield_val / 0.06

        return {
            'ticker': ticker.replace('.SA', ''), 
            'preco': preco_atual,
            'rsi': rsi_atual, 
            'tendencia': tendencia,
            'graham': preco_graham,
            'margem_graham': margem_graham,
            'bazin': preco_bazin
        }
    except Exception:
        return None

# Listas
oportunidades = []
neutros = []

# Barra de Progresso
texto_status = st.empty()
texto_status.info("🚀 Iniciando varredura fundamentalista... Isso leva cerca de 40-60 segundos.")
barra = st.progress(0)

# Loop de Análise
for i, ticker in enumerate(MEUS_TICKERS):
    dados = analisar_ativo(ticker)
    if dados:
        # Lógica de Classificação
        is_op = False
        motivos = []

        # 1. Técnico Bom
        if dados['rsi'] <= 35: 
            motivos.append("RSI Baixo")
            is_op = True
        
        # 2. Fundamentalista Bom (Margem Graham > 20%)
        if dados['margem_graham'] > 20: 
            motivos.append(f"Graham +{dados['margem_graham']:.0f}%")
            is_op = True
            
        # 3. Dividendos (Preço abaixo do teto Bazin)
        if dados['bazin'] > 0 and dados['preco'] < dados['bazin']:
            motivos.append("Bazin Teto")
            is_op = True

        dados['motivos'] = ", ".join(motivos)
        
        if is_op:
            oportunidades.append(dados)
        else:
            neutros.append(dados)
            
    barra.progress((i + 1) / len(MEUS_TICKERS))

texto_status.empty()
barra.empty()

# --- LAYOUT DE TABELA DESKTOP ---
def desenhar_cabecalho():
    c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 1, 1, 1.2, 1.2, 1.2, 2])
    c1.markdown("**Ativo**")
    c2.markdown("**Preço**")
    c3.markdown("**RSI**")
    c4.markdown("**Tendência**")
    c5.markdown("**Graham (Justo)**")
    c6.markdown("**Bazin (Teto)**")
    c7.markdown("**Sinais / Motivos**")
    st.divider()

def desenhar_linha(item, destaque=False):
    # Definindo cores dinâmicas
    cor_rsi = "green" if item['rsi'] <= 35 else ("red" if item['rsi'] >= 70 else "black")
    
    # Graham: Verde se tiver margem positiva
    cor_graham = "green" if item['preco'] < item['graham'] else "black"
    texto_graham = f"R$ {item['graham']:.2f}" if item['graham'] > 0 else "-"
    
    # Bazin: Verde se estiver barato
    cor_bazin = "green" if (item['bazin'] > 0 and item['preco'] < item['bazin']) else "black"
    texto_bazin = f"R$ {item['bazin']:.2f}" if item['bazin'] > 0 else "-"

    # Tendência cor
    cor_tend = "green" if "Alta" in item['tendencia'] else "red"

    # Background suave para oportunidades
    bg_style = "background-color: #f0f8ff; border-radius: 5px; padding: 5px 0;" if destaque else ""

    with st.container():
        if destaque: st.markdown(f"<div style='{bg_style}'>", unsafe_allow_html=True)
        
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 1, 1, 1.2, 1.2, 1.2, 2])
        
        c1.markdown(f"**{item['ticker']}**")
        c2.markdown(f"R$ {item['preco']:.2f}")
        c3.markdown(f":{cor_rsi}[**{item['rsi']:.0f}**]")
        c4.markdown(f":{cor_tend}[{item['tendencia']}]")
        c5.markdown(f":{cor_graham}[**{texto_graham}**]")
        c6.markdown(f":{cor_bazin}[**{texto_bazin}**]")
        
        if destaque:
            c7.success(item['motivos'])
        else:
            c7.caption("Neutro")
            
        if destaque: st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)

# --- EXIBIÇÃO ---

if oportunidades:
    st.subheader(f"🚀 Oportunidades Identificadas ({len(oportunidades)})")
    desenhar_cabecalho()
    for item in oportunidades:
        desenhar_linha(item, destaque=True)
else:
    st.info("Nenhuma oportunidade óbvia encontrada hoje.")

st.write("")
st.subheader(f"📋 Lista de Observação ({len(neutros)})")
desenhar_cabecalho()
for item in neutros:
    desenhar_linha(item, destaque=False)

# --- RODAPÉ EXPLICATIVO ---
st.write("")
with st.expander("📚 Entenda os Cálculos"):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🧠 Valuation")
        st.markdown("""
        * **Graham:** $\sqrt{22.5 \\times LPA \\times VPA}$. Busca empresas descontadas frente ao lucro e patrimônio.
        * **Bazin:** $\\frac{Dividendos}{0.06}$. Preço máximo para garantir 6% de retorno em proventos.
        """)
    with c2:
        st.markdown("### 📈 Momentum (Técnico)")
        st.markdown("""
        * **RSI < 35:** Sobrevendido (Pode repicar/subir).
        * **Tendência:** Média Móvel de 50 dias. Se o preço está acima, a tendência é de alta.
        """)

if st.button('🔄 Atualizar Varredura'):
    st.rerun()
