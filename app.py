import streamlit as st
import yfinance as yf
import pandas as pd
import math
import time
from datetime import datetime, timedelta

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
            
            # 2. TÉCNICA (RSI CALIBRADO - WILDER'S SMOOTHING)
            # Pegamos 6 meses para que a média exponencial tenha tempo de estabilizar
            hist_long = stock.history(period="6mo") 
            
            if len(hist_long) > 30:
                delta = hist_long['Close'].diff()
                
                # --- CORREÇÃO MATEMÁTICA AQUI ---
                # Antes (Errado): rolling(window=14).mean() -> Média Simples
                # Agora (Certo/Investing): ewm(alpha=1/14).mean() -> Média Exponencial de Wilder
                
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
                
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                mm50 = hist_long['Close'].rolling(window=50).mean().iloc[-1]
                tendencia = "Alta" if preco > mm50 else "Baixa"
            else:
                rsi = 50
                tendencia = "-"

            # 3. DY REAL
            try:
                divs = stock.dividends
                if not divs.empty:
                    cutoff = pd.Timestamp.now().replace(tzinfo=None) - pd.Timedelta(days=365)
                    divs.index = divs.index.tz_localize(None) 
                    soma_12m = divs[divs.index >= cutoff].sum()
                    dy = soma_12m / preco
                else:
                    dy = 0.0
            except:
                dy = 0.0

            # 4. FUNDAMENTOS
            info = {}
            try: info = stock.info
            except: pass 

            def get_i(key): return info.get(key)
            lpa = get_i('trailingEps') or get_i('forwardEps')
            vpa = get_i('bookValue')
            roe = get_i('returnOnEquity')
            pl = get_i('trailingPE')
            pvp = get_i('priceToBook')

            # Valuation (Visual)
            graham = None
            if lpa and vpa and lpa > 0 and vpa > 0:
                try: graham = math.sqrt(22.5 * lpa * vpa)
                except: pass

            bazin = None
            val_pago_ano = dy * preco
            if val_pago_ano > 0:
                bazin = val_pago_ano / 0.06

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
                'motivos': [],
                'score_ouro': False
            }
            
            # --- LÓGICA DE DECISÃO ---
            
            # Critérios de Fundamentos
            f_ok_pl = (pl is not None and 0 < pl < 15)
            f_ok_roe = (roe is not None and roe > 0.10)
            fundamentos_bons = f_ok_pl and f_ok_roe

            # 1. 🏆 OPORTUNIDADE DE OURO
            if tendencia == "Alta" and fundamentos_bons and rsi < 65:
                dados['motivos'].append("💎 TENDÊNCIA + FUNDAMENTOS")
                dados['sinal'] = 'COMPRA OURO'
                dados['score_ouro'] = True
            
            # 2. Compra Tática
            elif rsi <= 35:
                dados['motivos'].append("RSI Baixo (Repique)")
                dados['sinal'] = 'COMPRA'
            
            # 3. Compra por Qualidade
            elif tendencia == "Alta" and fundamentos_bons:
                dados['motivos'].append("Qualidade Técnica")
                dados['sinal'] = 'COMPRA'

            # 4. Venda
            if rsi >= 70:
                dados['motivos'] = ["RSI Estourado"] 
                dados['sinal'] = 'VENDA'
                dados['score_ouro'] = False
            
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

ouros = [d for d in dados if d['score_ouro']]
compras_normais = [d for d in dados if d['sinal'] == 'COMPRA' and not d['score_ouro']]
vendas = [d for d in dados if d['sinal'] == 'VENDA']
neutros = [d for d in dados if d['sinal'] == 'NEUTRO']

# 1. SESSÃO DE OURO
if ouros:
    st.markdown("### 🏆 Oportunidades de Ouro (Técnica + Fundamentos)")
    cols = st.columns(len(ouros)) if len(ouros) < 4 else st.columns(4)
    for i, item in enumerate(ouros):
        col_idx = i % 4
        with cols[col_idx]:
            st.warning(f"""
            **{item['ticker']}** (R$ {item['preco']:.2f})  
            ✅ Tendência de Alta  
            ✅ P/L: {item['pl']:.1f} | ROE: {item['roe']*100:.0f}%  
            ✅ RSI: {item['rsi']:.0f} (Wilder)
            """)
    st.markdown("---")

# 2. RADAR GERAL
st.subheader("📢 Radar Geral")
c_compra, c_venda = st.columns(2)

with c_compra:
    st.info(f"🟢 **Outras Compras ({len(compras_normais)})**")
    if compras_normais:
        for c in compras_normais:
            motivo = c['motivos'][0]
            st.markdown(f"**{c['ticker']}** (R$ {c['preco']:.2f}) 👉 *{motivo}*")
    else:
        st.caption("Apenas oportunidades de Ouro ou Neutras.")

with c_venda:
    st.error(f"🔴 **Vender / Risco ({len(vendas)})**")
    if vendas:
        for v in vendas:
            st.markdown(f"**{v['ticker']}** (R$ {v['preco']:.2f}) 👉 RSI Alto ({v['rsi']:.0f})")
    else:
        st.caption("Nenhum ativo em zona de risco.")

st.markdown("---")

# 3. TABELA DETALHADA
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
        texto = f"{valor*100:.2f}%" 
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
        
        if item['score_ouro']:
            c[0].markdown(f"⭐ **{item['ticker']}**")
        else:
            c[0].markdown(f"**{item['ticker']}**")
            
        c[1].write(f"R$ {item['preco']:.2f}")
        exibir_metrica(c[2], item['rsi'], tipo="rsi")
        
        tend = item['tendencia']
        cor_t = "green" if "Alta" in tend else ("red" if "Baixa" in tend else None)
        if cor_t: c[3].markdown(f":{cor_t}[{tend}]")
        else: c[3].write(tend)

        exibir_metrica(c[4], item['graham'], tipo="dinheiro", meta=item['preco'], inverter=False)
        exibir_metrica(c[5], item['bazin'], tipo="dinheiro", meta=item['preco'], inverter=False)
        
        if item['motivos']: 
            if item['sinal'] == 'VENDA': c[6].error(item['motivos'][0])
            elif item['score_ouro']: c[6].warning("💎 GOLD")
            else: c[6].success(item['motivos'][0])
        else: c[6].caption("-")
        
        exibir_metrica(c[7], item['roe'], tipo="percentual", meta=0.10)
        exibir_metrica(c[8], item['pl'], tipo="decimal", meta=15, inverter=True)
        exibir_metrica(c[9], item['pvp'], tipo="decimal", meta=1.5, inverter=True)
        exibir_metrica(c[10], item['dy'], tipo="percentual", meta=0.06)
        
        st.markdown("---")

if not dados and erros_log:
    st.error("Falha ao obter dados. Tente atualizar novamente.")
else:
    desenhar_tabela(ouros, "🏆 Seleção de Ouro")
    desenhar_tabela(compras_normais, "🚀 Oportunidades Táticas")
    desenhar_tabela(vendas, "⚠️ Atenção (Venda)")
    desenhar_tabela(neutros, "📋 Lista de Observação")

# 4. CRITÉRIOS
st.write("")
with st.expander("ℹ️ Ajustes Técnicos Realizados", expanded=True):
    st.markdown("""
    **RSI Calibrado (Wilder's Smoothing):** Agora o cálculo usa Média Exponencial (alpha=1/14) em vez de Simples, para alinhar os valores com o **Investing.com**.
    
    *Nota: Pequenas diferenças (decimais) ainda podem ocorrer se o Investing.com estiver usando dados intra-day (minuto a minuto) e nós usarmos o fechamento diário.*
    """)

if erros_log:
    with st.expander("Logs técnicos"):
        for e in erros_log: st.write(e)
