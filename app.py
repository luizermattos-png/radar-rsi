import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import math
import time
from io import StringIO

# ==========================================
# CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="Monitor Valuation Pro", layout="wide")

MEUS_TICKERS_BASE = [
    "ALLD3", "ALOS3", "BBAS3", "BHIA3", "CMIG4",
    "EMBJ3", "FLRY3", "GMAT3", "GUAR3", "HAPV3",
    "ISAE4", "ITSA4", "ITUB4", "IVVB11", "KLBN4",
    "MBRF3", "MTRE3", "PETR4", "RAIL3",
    "RDOR3", "SANB4", "UGPA3", "VALE3", "VULC3",
    "WEGE3"
]

# ==========================================
# FUNÇÃO "MACGYVER" (Substitui a biblioteca Fundamentus)
# ==========================================
@st.cache_data(ttl=1800) # Cache de 30 min
def resgatar_fundamentus_na_raca():
    url = 'https://www.fundamentus.com.br/resultado.php'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        r = requests.get(url, headers=headers)
        # Transforma o HTML em Tabela Pandas
        # O replace é para trocar vírgula decimal por ponto
        df = pd.read_html(StringIO(r.text), decimal=',', thousands='.')[0]
        
        # Limpeza de dados (Porcentagens e Textos)
        for col in ['Div.Yield', 'ROE', 'ROIC', 'Mrg Ebit', 'Mrg. Líq.', 'Cresc. Rec.5a']:
            df[col] = df[col].str.replace('.', '', regex=False)
            df[col] = df[col].str.replace(',', '.', regex=False)
            df[col] = df[col].str.rstrip('%').astype('float') / 100

        # Define o ticker como índice
        df.set_index('Papel', inplace=True)
        return df
    
    except Exception as e:
        st.error(f"Erro ao acessar site Fundamentus direto: {e}")
        return pd.DataFrame()

# ==========================================
# MOTOR DE ANÁLISE
# ==========================================
@st.cache_data(ttl=900)
def analisar_carteira(lista_tickers_base):
    resultados = []
    erros = []
    
    # 1. Puxa a tabela gigante do Fundamentus
    df_fund = resgatar_fundamentus_na_raca()
    
    progresso = st.progress(0)
    status = st.empty()
    total = len(lista_tickers_base)
    
    for i, ticker_base in enumerate(lista_tickers_base):
        ticker_yahoo = f"{ticker_base}.SA"
        status.caption(f"Analisando {ticker_yahoo} ({i+1}/{total})...")
        progresso.progress((i + 1) / total)
        
        try:
            # --- TÉCNICA (YAHOO) ---
            stock = yf.Ticker(ticker_yahoo)
            try:
                preco = stock.fast_info['last_price']
            except:
                hist = stock.history(period="1d")
                if not hist.empty:
                    preco = hist['Close'].iloc[-1]
                else:
                    # Se não tem preço no Yahoo, tenta pegar do Fundamentus
                    if ticker_base in df_fund.index:
                        preco = float(df_fund.loc[ticker_base, 'Cotação']) / 100 # Ajuste se necessário, mas geralmente vem certo
                    else:
                        erros.append(f"{ticker_base}: Sem cotação")
                        continue
            
            # RSI (Wilder)
            hist_long = stock.history(period="6mo") 
            if len(hist_long) > 30:
                delta = hist_long['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                mm50 = hist_long['Close'].rolling(window=50).mean().iloc[-1]
                tendencia = "Alta" if preco > mm50 else "Baixa"
            else:
                rsi = 50
                tendencia = "-"

            # --- FUNDAMENTOS (DA NOSSA TABELA MACGYVER) ---
            lpa = 0
            vpa = 0
            roe = 0
            pl = 0
            pvp = 0
            dy = 0
            
            if ticker_base in df_fund.index:
                row = df_fund.loc[ticker_base]
                
                pl = row['P/L']
                pvp = row['P/VP']
                roe = row['ROE']      # Já vem decimal (ex: 0.15)
                dy = row['Div.Yield'] # Já vem decimal (ex: 0.06)
                
                # Para Graham
                if pl != 0: lpa = preco / pl
                if pvp != 0: vpa = preco / pvp
            
            # CÁLCULOS FINAIS
            graham = None
            if lpa > 0 and vpa > 0:
                try: graham = math.sqrt(22.5 * lpa * vpa)
                except: pass

            bazin = None
            if dy > 0:
                # Preço Teto = (Preço * DY) / 0.06
                bazin = (preco * dy) / 0.06

            dados = {
                'ticker': ticker_base,
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
            
            # --- DECISÃO ---
            fundamentos_bons = (0 < pl < 15) and (roe > 0.10)

            # 1. 🏆 OURO
            if tendencia == "Alta" and fundamentos_bons and rsi < 65:
                dados['motivos'].append("💎 TENDÊNCIA + FUNDAMENTOS")
                dados['sinal'] = 'COMPRA OURO'
                dados['score_ouro'] = True
            
            # 2. Compra Tática
            elif rsi <= 35:
                dados['motivos'].append("RSI Baixo (Repique)")
                dados['sinal'] = 'COMPRA'
            
            # 3. Compra Qualidade
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
            erros.append(f"{ticker_base}: {str(e)}")
        
        time.sleep(0.1)

    progresso.empty()
    status.empty()
    return resultados, erros

# ==========================================
# VISUAL
# ==========================================
st.title("💎 Monitor Valuation Pro")
st.caption("Fonte: Yahoo (Preço/RSI) + Fundamentus Direto (Indicadores)")
st.markdown("---")

col_top1, col_top2 = st.columns([6, 1])
with col_top2:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()

dados, erros_log = analisar_carteira(MEUS_TICKERS_BASE)

ouros = [d for d in dados if d['score_ouro']]
compras_normais = [d for d in dados if d['sinal'] == 'COMPRA' and not d['score_ouro']]
vendas = [d for d in dados if d['sinal'] == 'VENDA']
neutros = [d for d in dados if d['sinal'] == 'NEUTRO']

# 1. SESSÃO DE OURO
if ouros:
    st.markdown("### 🏆 Oportunidades de Ouro")
    cols = st.columns(len(ouros)) if len(ouros) < 4 else st.columns(4)
    for i, item in enumerate(ouros):
        col_idx = i % 4
        with cols[col_idx]:
            st.warning(f"""
            **{item['ticker']}** (R$ {item['preco']:.2f})  
            ✅ Tendência de Alta  
            ✅ P/L: {item['pl']:.1f} | ROE: {item['roe']*100:.0f}%  
            ✅ RSI: {item['rsi']:.0f}
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
        st.caption("Nada aqui.")

with c_venda:
    st.error(f"🔴 **Vender / Risco ({len(vendas)})**")
    if vendas:
        for v in vendas:
            st.markdown(f"**{v['ticker']}** (R$ {v['preco']:.2f}) 👉 RSI Alto ({v['rsi']:.0f})")
    else:
        st.caption("Nada aqui.")

st.markdown("---")

# 3. TABELA
cols_cfg = [0.8, 0.8, 0.6, 0.8, 0.9, 0.9, 2, 0.8, 0.8, 0.8, 0.8]
headers = ["Ativo", "Preço", "RSI", "Tend.", "Graham", "Bazin", "Sinais", "ROE", "P/L", "P/VP", "DY"]

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

def desenhar_tabela(lista, titulo):
    if not lista: return
    st.subheader(f"{titulo} ({len(lista)})")
    h = st.columns(cols_cfg)
    for i, t in enumerate(headers): h[i].markdown(f"**{t}**")
    st.divider()
    for item in lista:
        c = st.columns(cols_cfg)
        if item['score_ouro']: c[0].markdown(f"⭐ **{item['ticker']}**")
        else: c[0].markdown(f"**{item['ticker']}**")
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
    st.error("Falha ao obter dados.")
else:
    desenhar_tabela(ouros, "🏆 Seleção de Ouro")
    desenhar_tabela(compras_normais, "🚀 Oportunidades Táticas")
    desenhar_tabela(vendas, "⚠️ Atenção (Venda)")
    desenhar_tabela(neutros, "📋 Lista de Observação")

if erros_log:
    with st.expander("Logs técnicos"):
        for e in erros_log: st.write(e)
