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
            
            # 2. TÉCNICA (RSI + TENDÊNCIA)
            hist_long = stock.history(period="6mo") # Pegamos 6 meses para garantir médias e dividendos
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

            # 3. DY REAL (CÁLCULO NA RAÇA: Soma dos dividendos pagos nos últimos 12m)
            try:
                # Pega histórico de dividendos
                divs = stock.dividends
                if not divs.empty:
                    # Filtra últimos 365 dias
                    # Remove fuso horário para comparação segura
                    cutoff = pd.Timestamp.now().replace(tzinfo=None) - pd.Timedelta(days=365)
                    divs.index = divs.index.tz_localize(None) 
                    
                    soma_12m = divs[divs.index >= cutoff].sum()
                    dy = soma_12m / preco # Resultado decimal puro (ex: 0.0524)
                else:
                    dy = 0.0
            except:
                dy = 0.0

            # 4. FUNDAMENTOS (Info)
            info = {}
            try: info = stock.info
            except: pass 

            def get_i(key): return info.get(key)
            lpa = get_i('trailingEps') or get_i('forwardEps')
            vpa = get_i('bookValue')
            roe = get_i('returnOnEquity')
            pl = get_i('trailingPE')
            pvp = get_i('priceToBook')

            # Valuation (Apenas Visual)
            graham = None
            if lpa and vpa and lpa > 0 and vpa > 0:
                try: graham = math.sqrt(22.5 * lpa * vpa)
                except: pass

            bazin = None
            # Preço Teto Bazin: DY em R$ / 0.06
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
                'motivos': []
            }
            
            # --- LÓGICA DE DECISÃO (PEDIDO DO USUÁRIO) ---
            
            # 1. Oportunidade por Sobrevenda (Tática)
            if rsi <= 35:
                dados['motivos'].append("RSI Baixo")
                dados['sinal'] = 'COMPRA'
            
            # 2. Oportunidade por Qualidade (Tendência + Fundamentos)
            # Regra: Tendência Alta + P/L Saudável + ROE Bom
            elif tendencia == "Alta":
                condicao_pl = (pl is not None and 0 < pl < 15)
                condicao_roe = (roe is not None and roe > 0.10)
                
                if condicao_pl and condicao_roe:
                    dados['motivos'].append("Tendência + Qualidade")
                    dados['sinal'] = 'COMPRA'

            # 3. Venda (Risco)
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
# 1. RADAR (TOPO)
# ==========================================
st.subheader("📢 Radar de Oportunidades")
c_compra, c_venda = st.columns(2)

with c_compra:
    st.info(f"🟢 **Comprar ({len(compras)})**")
    if compras:
        for c in compras:
            motivo = c['motivos'][0]
            st.markdown(f"**{c['ticker']}** (R$ {c['preco']:.2f}) 👉 *{motivo}*")
    else:
        st.caption("Nenhuma oportunidade nos critérios atuais.")

with c_venda:
    st.error(f"🔴 **Vender / Risco ({len(vendas)})**")
    if vendas:
        for v in vendas:
            st.markdown(f"**{v['ticker']}** (R$ {v['preco']:.2f}) 👉 RSI Alto ({v['rsi']:.0f})")
    else:
        st.caption("Nenhum ativo em zona de risco.")

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
        # Multiplicamos por 100 pois agora o DY é sempre decimal (0.05)
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
        
        c[0].markdown(f"**{item['ticker']}**")
        c[1].write(f"R$ {item['preco']:.2f}")
        exibir_metrica(c[2], item['rsi'], tipo="rsi")
        
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
        
        exibir_metrica(c[7], item['roe'], tipo="percentual", meta=0.10)
        exibir_metrica(c[8], item['pl'], tipo="decimal", meta=15, inverter=True)
        exibir_metrica(c[9], item['pvp'], tipo="decimal", meta=1.5, inverter=True)
        exibir_metrica(c[10], item['dy'], tipo="percentual", meta=0.06)
        
        st.markdown("---")

if not dados and erros_log:
    st.error("Falha ao obter dados. Tente atualizar novamente.")
else:
    desenhar_tabela(compras, "🚀 Oportunidades (Compra)")
    desenhar_tabela(vendas, "⚠️ Atenção (Venda)")
    desenhar_tabela(neutros, "📋 Lista de Observação")

# ==========================================
# 3. CRITÉRIOS
# ==========================================
st.write("")
with st.expander("ℹ️ Lógica do Robô (Como ele decide?)", expanded=True):
    st.markdown("""
    **Sinal de COMPRA (Verde):**
    1.  **Repique Técnico:** RSI <= 35.
    2.  **Qualidade:** Tendência de Alta + (P/L entre 0 e 15) + (ROE > 10%).
    
    **Sinal de VENDA (Vermelho):**
    * **Risco:** RSI >= 70.
    
    *Nota: Graham e Bazin não influenciam os sinais, use-os como referência manual.*
    """)

if erros_log:
    with st.expander("Logs técnicos"):
        for e in erros_log: st.write(e)
