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
            
            # 2. RSI e TENDÊNCIA
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

            # Valuation
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
                'sinal': 'NEUTRO', # Novo campo
                'motivos': []
            }
            
            # --- LÓGICA DE DECISÃO (COMPRA vs VENDA) ---
            
            # Sinais de COMPRA (Verde)
            if rsi <= 35: 
                dados['motivos'].append("RSI Baixo")
                dados['sinal'] = 'COMPRA'
            if graham and preco < graham: 
                dados['motivos'].append("Desc. Graham")
                dados['sinal'] = 'COMPRA'
            if bazin and preco < bazin: 
                dados['motivos'].append("Teto Bazin")
                dados['sinal'] = 'COMPRA'

            # Sinais de VENDA (Vermelho) - Prioritário se RSI estiver explodindo
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

# Botão de atualização no topo direito
col_top1, col_top2 = st.columns([6, 1])
with col_top2:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()

# Executa Análise
dados, erros_log = analisar_carteira(MEUS_TICKERS)

# Separa os grupos
compras = [d for d in dados if d['sinal'] == 'COMPRA']
vendas = [d for d in dados if d['sinal'] == 'VENDA']
neutros = [d for d in dados if d['sinal'] == 'NEUTRO']

# ==========================================
# 1. PAINEL DE DESTAQUES (TOPO)
# ==========================================
st.subheader("📢 Resumo de Sinais")
c_compra, c_venda = st.columns(2)

with c_compra:
    st.info(f"🟢 **Oportunidades de Compra ({len(compras)})**")
    if compras:
        for c in compras:
            motivos = ", ".join(c['motivos'])
            st.markdown(f"**{c['ticker']}** (R$ {c['preco']:.2f}) 👉 *{motivos}*")
    else:
        st.caption("Nenhum sinal claro de compra hoje.")

with c_venda:
    st.error(f"🔴 **Sinais de Venda / Atenção ({len(vendas)})**")
    if vendas:
        for v in vendas:
            st.markdown(f"**{v['ticker']}** (R$ {v['preco']:.2f}) 👉 RSI Alto ({v['rsi']:.0f})")
    else:
        st.caption("Nenhum ativo sobrecomprado (RSI > 70).")

st.markdown("---")

# ==========================================
# 2. TABELA DETALHADA
# ==========================================

# Função de formatação visual segura
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
        
        tend = item['tendencia']
        cor_t = "green" if "Alta" in tend else ("red" if "Baixa" in tend else None)
        if cor_t: c[3].markdown(f":{cor_t}[{tend}]")
        else: c[3].write(tend)

        exibir_metrica(c[4], item['graham'], tipo="dinheiro", meta=item['preco'], inverter=False)
        exibir_metrica(c[5], item['bazin'], tipo="dinheiro", meta=item['preco'], inverter=False)
        
        if item['motivos']: 
            if item['sinal'] == 'VENDA': c[6].error(", ".join(item['motivos']))
            else: c[6].success(", ".join(item['motivos']))
        else: c[6].caption("-")
        
        exibir_metrica(c[7], item['roe'], tipo="percentual", meta=0.15)
        exibir_metrica(c[8], item['pl'], tipo="decimal", meta=10, inverter=True)
        exibir_metrica(c[9], item['pvp'], tipo="decimal", meta=1.5, inverter=True)
        exibir_metrica(c[10], item['dy'], tipo="percentual", meta=0.06)
        
        st.markdown("---")

if not dados and erros_log:
    st.error("Falha ao obter dados. Tente atualizar novamente.")
else:
    # Mostra lista completa (ordenada: Compras -> Vendas -> Neutros)
    desenhar_tabela(compras, "🚀 Oportunidades (Compra)")
    desenhar_tabela(vendas, "⚠️ Atenção (Venda/Sobrecompra)")
    desenhar_tabela(neutros, "📋 Lista de Observação (Neutro)")

# ==========================================
# 3. RODAPÉ EDUCATIVO
# ==========================================
st.write("")
st.write("")
with st.expander("📚 Como analisar os indicadores? (Guia Rápido)", expanded=True):
    col_guia1, col_guia2, col_guia3 = st.columns(3)
    
    with col_guia1:
        st.markdown("### 📊 Valuation (Preço Justo)")
        st.markdown("""
        * **Graham:** Calcula o "Preço Justo" baseado no lucro e patrimônio. Se o Preço Atual for **menor** que o Preço Graham, a ação está descontada.
        * **Bazin:** Foca em dividendos. Calcula o preço teto para receber pelo menos 6% de retorno em dividendos.
        * **P/L (Preço/Lucro):** Em quantos anos você recupera o investimento através do lucro da empresa. Idealmente **abaixo de 10**.
        * **P/VP (Preço/Valor Patrimonial):** Quanto o mercado paga pelo patrimônio líquido. **Abaixo de 1.0** indica que a empresa vale menos que seus ativos (barata).
        """)

    with col_guia2:
        st.markdown("### 📈 Momentum (Timing)")
        st.markdown("""
        * **RSI (IFR):** Mede a força da tendência.
            * **Abaixo de 30:** Sobrevendido (Caiu demais, chance de repique -> Compra).
            * **Acima de 70:** Sobrecomprado (Subiu demais, chance de correção -> Venda).
        * **Tendência:** Baseada na Média Móvel de 50 dias. Se o preço está acima da média, tendência de Alta.
        """)

    with col_guia3:
        st.markdown("### 🏢 Qualidade (Fundamentos)")
        st.markdown("""
        * **ROE (Retorno sobre Patrimônio):** Mede a eficiência da gestão. Quanto dinheiro eles geram com o capital dos sócios. Idealmente **acima de 15%**.
        * **DY (Dividend Yield):** Quanto a empresa pagou de proventos nos últimos 12 meses em relação ao preço atual. Idealmente **acima de 6%**.
        """)

if erros_log:
    with st.expander("Logs técnicos"):
        for e in erros_log: st.write(e)
