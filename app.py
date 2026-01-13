import streamlit as st
import yfinance as yf
import pandas as pd
import math
import time
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="Monitor Valuation Pro", layout="wide")

MEUS_TICKERS = [
    "ALLD3.SA", "ALOS3.SA", "BBAS3.SA", "BHIA3.SA", "CMIG4.SA",
    "EMBJ3.SA", "FLRY3.SA", "GMAT3.SA", "GUAR3.SA", "HAPV3.SA",
    "ISAE4.SA", "ITSA4.SA", "ITUB4.SA", "IVVB11.SA", "KLBN4.SA",
    "MBRF3.SA", "MTRE3.SA", "PETR4.SA", "RAIL3.SA",
    "RDOR3.SA", "SANB4.SA", "UGPA3.SA", "VALE3.SA", "VULC3.SA",
    "WEGE3.SA"
]

# ==========================================
# MOTOR DE ANÁLISE
# ==========================================
@st.cache_data(ttl=900)
def analisar_carteira(lista_tickers):
    resultados = []
    erros = []
    
    progresso = st.progress(0)
    status = st.empty()
    total = len(lista_tickers)
    
    for i, ticker in enumerate(lista_tickers):
        status.caption(f"Analisando {ticker} ({i+1}/{total})...")
        progresso.progress((i + 1) / total)
        
        try:
            stock = yf.Ticker(ticker)
            
            # 1. PREÇO
            try:
                preco = stock.fast_info['last_price']
            except:
                hist = stock.history(period="1d")
                if not hist.empty:
                    preco = hist['Close'].iloc[-1]
                else:
                    erros.append(f"{ticker}: Sem cotação")
                    continue 
            
            # 2. TÉCNICA (RSI + TENDÊNCIA)
            hist_long = stock.history(period="3mo")
            if len(hist_long) > 30:
                delta = hist_long['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                mm50 = hist_long['Close'].rolling(window=50).mean().iloc[-1]
                tendencia = "Alta" if preco > mm50 else "Baixa"
            else:
                rsi = 50
                tendencia = "-"

            # 3. FUNDAMENTOS
            info = {}
            try: info = stock.info
            except: pass 

            def get_i(key): return info.get(key)
            lpa = get_i('trailingEps') or get_i('forwardEps')
            vpa = get_i('bookValue')
            roe = get_i('returnOnEquity')
            pl = get_i('trailingPE')
            pvp = get_i('priceToBook')
            dy = get_i('dividendYield')

            # Graham e Bazin (Apenas cálculo, sem decisão)
            graham = None
            if lpa and vpa and lpa > 0 and vpa > 0:
                try: graham = math.sqrt(22.5 * lpa * vpa)
                except: pass

            bazin = None
            if dy and dy > 0:
                dy_calc = dy if dy < 1 else dy / 100
                bazin = (dy_calc * preco) / 0.06

            dados = {
                'ticker': ticker.replace('.SA', ''),
                'preco': preco,
                'rsi': rsi,
                'tendencia': tendencia,
                'graham': graham,
                'bazin': bazin,
                'roe': roe,
                'pl': pl,
                'pvp': pvp,
                'dy': dy,
                'sinal': 'NEUTRO',
                'motivos': []
            }
            
            # --- LÓGICA DE DECISÃO INTELIGENTE ---
            # Ignora Graham e Bazin. Usa RSI, Tendência e Fundamentos básicos.
            
            # CENÁRIO 1: Oportunidade Tática (Sobrevenda Exagerada)
            if rsi <= 35:
                dados['motivos'].append("RSI Baixo")
                dados['sinal'] = 'COMPRA'
            
            # CENÁRIO 2: Qualidade em Tendência (Oportunidade Fundamentalista)
            # Regra: Tendência de Alta + Lucrativa (P/L positivo e < 15) + Eficiente (ROE > 10%)
            elif tendencia == "Alta":
                condicao_pl = (pl is not None and 0 < pl < 15)
                condicao_roe = (roe is not None and roe > 0.10)
                
                if condicao_pl and condicao_roe:
                    dados['motivos'].append("Tendência + Fundamentos")
                    dados['sinal'] = 'COMPRA'

            # CENÁRIO 3: Venda (Risco Alto)
            if rsi >= 70:
                dados['motivos'].append("RSI Estourado")
                dados['sinal'] = 'VENDA'
            
            resultados.append(dados)

        except Exception as e:
            erros.append(f"{ticker}: {str(e)}")
        
        time.sleep(0.5)

    progresso.empty()
    status.empty()
    return resultados, erros

# ==========================================
# INTERFACE GRÁFICA
# ==========================================
st.title("💎 Monitor Valuation Pro")
st.markdown("---")

col_top1, col_top2 = st.columns([6, 1])
with col_top2:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()

dados, erros_log = analisar_carteira(MEUS_TICKERS)

compras = [d for d in dados if d['sinal'] == 'COMPRA']
vendas = [d for d in dados if d['sinal'] == 'VENDA']
neutros = [d for d in dados if d['sinal'] == 'NEUTRO']

# ==========================================
# 1. RADAR DE OPORTUNIDADES
# ==========================================
st.subheader("📢 Radar de Oportunidades")
c_compra, c_venda = st.columns(2)

with c_compra:
    st.info(f"🟢 **Comprar ({len(compras)})**")
    if compras:
        for c in compras:
            # Mostra o motivo específico (RSI ou Fundamentos)
            motivo = c['motivos'][0] if c['motivos'] else "Análise Técnica"
            st.markdown(f"**{c['ticker']}** (R$ {c['preco']:.2f}) 👉 *{motivo}*")
    else:
        st.caption("Nenhuma oportunidade nos critérios atuais.")

with c_venda:
    st.error(f"🔴 **Vender / Risco ({len(vendas)})**")
    if vendas:
        for v in vendas:
            st.markdown(f"**{v['ticker']}** (R$ {v['preco']:.2f}) 👉 RSI Alto ({v['rsi']:.0f})")
    else:
        st.caption("Nenhum ativo sobrecomprado.")

st.markdown("---")

# ==========================================
# 2. TABELA
# ==========================================
def exibir_metrica(coluna, valor, tipo="padrao", meta=None, inverter=False):
    if valor is None:
        coluna.caption("-")
        return
    texto = ""
    cor = None

    if tipo == "dinheiro":
        texto = f"R$ {valor:.2f}"
        if meta and not inverter and valor > meta: cor = "green"
        if meta and inverter and valor < meta: cor = "green"

    elif tipo == "percentual":
        val_ajustado = valor * 100 if valor < 5 else valor
        texto = f"{val_ajustado:.1f}%"
        if meta and valor > meta: cor = "green"

    elif tipo == "decimal":
        texto = f"{valor:.2f}"
        if meta and not inverter and valor > meta: cor = "green"
        if meta and inverter and valor < meta: cor = "green"

    elif tipo == "rsi":
        texto = f"{valor:.0f}"
        if valor <= 35: cor = "green"
        elif valor >= 70: cor = "red"
    
    if cor: coluna.markdown(f":{cor}[{texto}]")
    else: coluna.markdown(texto)

cols_cfg = [0.8, 0.8, 0.6, 0.8, 0.9, 0.9, 2, 0.8, 0.8, 0.8, 0.8]
headers = ["Ativo", "Preço", "RSI", "Tend.", "Graham", "Bazin", "Sinais", "ROE", "P/L", "P/VP", "DY"]

def desenhar_tabela(lista, titulo):
    if not lista: return
    st.subheader(f"{titulo} ({len(lista)})")
    h = st.columns(cols_cfg)
    for i, t in enumerate(headers): h[i].markdown(f"**{t}**")
    st.divider()
    
    for item in lista:
        c = st.columns(cols_cfg)
        
        c[0].markdown(f"**{item['ticker']}**")
        c[1].write(f"R$ {item['preco']:.2f}")
        exibir_metrica(c[2], item['rsi'], tipo="rsi")
        
        # Tendência com cor
        tend = item['tendencia']
        cor_t = "green" if "Alta" in tend else ("red" if "Baixa" in tend else None)
        if cor_t: c[3].markdown(f":{cor_t}[{tend}]")
        else: c[3].write(tend)

        # Graham/Bazin (Só visual)
        exibir_metrica(c[4], item['graham'], tipo="dinheiro", meta=item['preco'], inverter=False)
        exibir_metrica(c[5], item['bazin'], tipo="dinheiro", meta=item['preco'], inverter=False)
        
        if item['motivos']: 
            if item['sinal'] == 'VENDA': c[6].error(item['motivos'][0])
            else: c[6].success(item['motivos'][0])
        else: c[6].caption("-")
        
        exibir_metrica(c[7], item['roe'], tipo="percentual", meta=0.15)       # ROE > 15%
        exibir_metrica(c[8], item['pl'], tipo="decimal", meta=15, inverter=True) # P/L < 15
        exibir_metrica(c[9], item['pvp'], tipo="decimal", meta=1.5, inverter=True) # P/VP < 1.5
        exibir_metrica(c[10], item['dy'], tipo="percentual", meta=0.06)       # DY > 6%
        
        st.markdown("---")

if not dados and erros_log:
    st.error("Falha ao obter dados. Tente atualizar novamente.")
else:
    desenhar_tabela(compras, "🚀 Oportunidades (Compra)")
    desenhar_tabela(vendas, "⚠️ Atenção (Venda)")
    desenhar_tabela(neutros, "📋 Lista de Observação")

# ==========================================
# 3. CRITÉRIOS UTILIZADOS
# ==========================================
st.write("")
with st.expander("ℹ️ Critérios do Algoritmo de Decisão", expanded=True):
    st.markdown("""
    **O Sistema indica COMPRA se acontecer UM destes cenários:**
    1.  **RSI Baixo:** O RSI está abaixo de 35 (Ativo caiu demais, repique provável).
    2.  **Qualidade em Tendência:** O ativo está em **Tendência de Alta** E possui bons fundamentos (**P/L entre 0 e 15** E **ROE acima de 10%**).
    
    **O Sistema indica VENDA se:**
    * **RSI Alto:** O RSI está acima de 70 (Ativo "esticado").
    
    *Nota: Os indicadores de Graham e Bazin são exibidos na tabela apenas para consulta manual.*
    """)

if erros_log:
    with st.expander("Logs técnicos"):
        for e in erros_log: st.write(e)
