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

st.set_page_config(page_title="Monitor Valuation", layout="centered")

# --- CABEÇALHO ---
st.title("💎 Monitor Valuation Pro")
data_atual = datetime.now().strftime("%d/%m/%Y")
st.caption(f"📅 {data_atual} | RSI + Tendência + Graham + Bazin")
st.divider()

# Função de Análise Completa
def analisar_ativo(ticker):
    try:
        # 1. Obter Dados Fundamentais (Lento, mas necessário para Graham/Bazin)
        obj_ticker = yf.Ticker(ticker)
        info = obj_ticker.info
        
        # Histórico para RSI e Tendência
        df = obj_ticker.history(period="6mo")
        if len(df) < 50: return None

        # --- CÁLCULOS TÉCNICOS (RSI + TENDÊNCIA) ---
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        df['MM50'] = df['Close'].rolling(window=50).mean()
        
        preco_atual = df['Close'].iloc[-1]
        rsi_atual = rsi.iloc[-1]
        mm50_atual = df['MM50'].iloc[-1]
        tendencia = "⬆️" if preco_atual > mm50_atual else "⬇️"

        # --- CÁLCULOS FUNDAMENTALISTAS (GRAHAM + BAZIN) ---
        
        # Graham: Raiz(22.5 * LPA * VPA)
        lpa = info.get('trailingEps', 0)
        vpa = info.get('bookValue', 0)
        preco_graham = 0
        if lpa > 0 and vpa > 0:
            preco_graham = math.sqrt(22.5 * lpa * vpa)
        
        # Bazin: Dividendos 12m / 6%
        div_yield_val = info.get('trailingAnnualDividendRate', 0) # Valor em $ pago nos ultimos 12m
        # Fallback: Se não tiver o Rate, tenta pegar pelo Yield * Preço
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
            'bazin': preco_bazin
        }
    except Exception as e:
        # st.error(f"Erro em {ticker}: {e}") # Descomente para debug
        return None

# Listas
oportunidades = []
neutros = []

texto_loading = st.empty()
texto_loading.text("⏳ Consultando balanços e preços... Isso pode levar 1 minuto.")
barra = st.progress(0)

# --- PROCESSAMENTO ---
for i, ticker in enumerate(MEUS_TICKERS):
    dados = analisar_ativo(ticker)
    if dados:
        # Lógica de Classificação Simples
        # Se RSI for bom OU se estiver muito descontado em Graham, vai para o topo
        rsi = dados['rsi']
        
        motivo = ""
        is_op = False
        
        # Critérios para "Oportunidade"
        if rsi <= 35:
            is_op = True
            motivo = "RSI Baixo"
        elif dados['graham'] > 0 and dados['preco'] < (dados['graham'] * 0.7): # 30% margem Graham
            is_op = True
            motivo = "Desconto Graham"
        elif dados['bazin'] > 0 and dados['preco'] < dados['bazin']:
            is_op = True
            motivo = "Teto Bazin"

        dados['motivo'] = motivo
        
        if is_op:
            oportunidades.append(dados)
        else:
            neutros.append(dados)
            
    barra.progress((i + 1) / len(MEUS_TICKERS))

texto_loading.empty()
barra.empty()

# --- FUNÇÃO DE DESENHO (LAYOUT OTIMIZADO MOBILE) ---
def desenhar_card(item, cor_borda):
    with st.container():
        # CSS para dar um visual de cartão
        st.markdown(f"""
        <div style="border-left: 5px solid {cor_borda}; padding: 10px; background-color: #f0f2f6; border-radius: 5px; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 1.2em; font-weight: bold;">{item['ticker']}</span>
                <span style="font-size: 1.1em;">R$ {item['preco']:.2f}</span>
                <span style="background-color: #fff; padding: 2px 5px; border-radius: 4px;">RSI: {item['rsi']:.0f} {item['tendencia']}</span>
            </div>
            <hr style="margin: 5px 0; opacity: 0.2;">
            <div style="display: flex; justify-content: space-between; font-size: 0.9em;">
                <span>⚖️ Graham: {formatar_valor(item['preco'], item['graham'])}</span>
                <span>💰 Bazin: {formatar_valor(item['preco'], item['bazin'])}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

def formatar_valor(preco_atual, preco_alvo):
    if preco_alvo <= 0:
        return "<span style='color: gray;'>N/A</span>"
    
    cor = "green" if preco_atual < preco_alvo else "black"
    # Negrito se tiver margem de segurança
    style = "font-weight:bold;" if preco_atual < preco_alvo else ""
    return f"<span style='color:{cor}; {style}'>R$ {preco_alvo:.2f}</span>"

# --- EXIBIÇÃO ---

if oportunidades:
    st.success(f"💎 {len(oportunidades)} Ativos com Indicadores Interessantes")
    for item in oportunidades:
        desenhar_card(item, "#28a745") # Borda Verde

st.divider()

with st.expander(f"Ver Lista Completa / Neutros ({len(neutros)})", expanded=True):
    for item in neutros:
        desenhar_card(item, "#6c757d") # Borda Cinza

st.write("")
# --- LEGENDA ---
with st.expander("📚 Como ler Valuation?"):
    st.markdown("""
    * **Graham:** Preço Justo baseado no lucro e patrimônio. Se o valor estiver **VERDE**, a ação está sendo negociada abaixo do justo.
    * **Bazin:** Preço Teto para receber 6% de dividendos. Se estiver **VERDE**, o dividendo esperado é superior a 6%.
    * **N/A:** Significa que a empresa deu prejuízo (sem P/L) ou não pagou dividendos.
    """)

if st.button('🔄 Atualizar Dados'):
    st.rerun()
