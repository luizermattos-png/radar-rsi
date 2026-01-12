import streamlit as st
import yfinance as yf
import pandas as pd
import math
import time
import requests
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Monitor Valuation Pro", layout="wide")

# Lista de Tickers
MEUS_TICKERS = [
    "ALLD3.SA", "ALOS3.SA", "BBAS3.SA", "BHIA3.SA", "CMIG4.SA",
    "EMBJ3.SA", "FLRY3.SA", "GMAT3.SA", "GUAR3.SA", "HAPV3.SA",
    "ISAE4.SA", "ITSA4.SA", "ITUB4.SA", "IVVB11.SA", "KLBN4.SA",
    "MBRF3.SA", "MTRE3.SA", "PETR4.SA", "RAIL3.SA",
    "RDOR3.SA", "SANB4.SA", "UGPA3.SA", "VALE3.SA", "VULC3.SA",
    "WEGE3.SA"
]

# --- CABEÇALHO ---
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.title("💎 Monitor Valuation & Momentum")
    st.caption("Graham + Bazin + RSI + Anti-Bloqueio Yahoo")
with c_head2:
    if st.button("🔄 Forçar Atualização"):
        st.cache_data.clear()
        st.rerun()
    st.write(f"📅 **{datetime.now().strftime('%d/%m/%Y')}**")

st.divider()

# ==========================================
# SESSÃO CAMUFLADA (O SEGREDO PARA NÃO SER BLOQUEADO)
# ==========================================
def criar_sessao():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

# ==========================================
# FUNÇÃO DE ANÁLISE ROBUSTA
# ==========================================
@st.cache_data(ttl=1800) # Cache de 30 min
def analisar_ativo(ticker):
    try:
        # Cria o ticker usando a sessão camuflada
        session = criar_sessao()
        obj_ticker = yf.Ticker(ticker, session=session)
        
        # 1. PREÇO ATUAL (Via fast_info, que é mais rápido e confiável)
        try:
            preco_atual = obj_ticker.fast_info['last_price']
        except:
            # Fallback: tenta pegar do histórico se o fast_info falhar
            hist = obj_ticker.history(period="1d")
            if len(hist) > 0:
                preco_atual = hist['Close'].iloc[-1]
            else:
                return None # Sem preço, ativo inválido

        # 2. RSI (Precisa de histórico)
        df = obj_ticker.history(period="3mo")
        if len(df) < 30: return None
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_atual = 100 - (100 / (1 + rs.iloc[-1]))
        
        # Tendência MM50
        mm50 = df['Close'].rolling(window=50).mean().iloc[-1]
        tendencia = "⬆️ Alta" if preco_atual > mm50 else "⬇️ Baixa"

        # 3. FUNDAMENTOS (A parte que estava falhando)
        # O try/except aqui garante que o código não quebre se o Yahoo negar dados
        info = {}
        try:
            info = obj_ticker.info
        except Exception:
            pass # Segue o baile com dicionário vazio
        
        # Extração Segura de Dados
        lpa = info.get('trailingEps') or info.get('forwardEps')
        vpa = info.get('bookValue')
        roe = info.get('returnOnEquity')
        pl = info.get('trailingPE')
        pvp = info.get('priceToBook')
        dy_percent = info.get('dividendYield')

        # Cálculos Valuation
        preco_graham = None
        margem_graham = None
        
        # Lógica Graham
        if lpa and vpa and lpa > 0 and vpa > 0:
            try:
                val_graham = math.sqrt(22.5 * lpa * vpa)
                preco_graham = val_graham
                margem_graham = ((val_graham - preco_atual) / preco_atual) * 100
            except: pass

        # Lógica Bazin
        preco_bazin = None
        if dy_percent and dy_percent > 0:
            dy_valor = dy_percent * preco_atual
            preco_bazin = dy_valor / 0.06

        # Pequena pausa para evitar bloqueio do Yahoo (IMPORTANTE)
        time.sleep(0.5)

        return {
            'ticker': ticker.replace('.SA', ''), 
            'preco': preco_atual,
            'rsi': rsi_atual, 
            'tendencia': tendencia,
            'graham': preco_graham,
            'margem_graham': margem_graham,
            'bazin': preco_bazin,
            'roe': roe,
            'pl': pl,
            'pvp': pvp,
            'dy': dy_percent
        }

    except Exception as e:
        # print(f"Erro em {ticker}: {e}")
        return None

# ==========================================
# LOOP PRINCIPAL
# ==========================================
oportunidades = []
neutros = []

texto_status = st.empty()
bar = st.progress(0)

total = len(MEUS_TICKERS)

# Loop com barra de progresso
for i, ticker in enumerate(MEUS_TICKERS):
    texto_status.markdown(f"🔍 Analisando **{ticker}** ({i+1}/{total})...")
    
    dados = analisar_ativo(ticker)
    bar.progress((i + 1) / total)
    
    if dados:
        is_op = False
        motivos = []

        # Critérios de Oportunidade
        if dados['rsi'] <= 35: 
            motivos.append("RSI Baixo")
            is_op = True
        
        if dados['margem_graham'] and dados['margem_graham'] > 20: 
            motivos.append(f"Graham +{dados['margem_graham']:.0f}%")
            is_op = True
            
        if dados['bazin'] and dados['preco'] < dados['bazin']:
            motivos.append("Teto Bazin")
            is_op = True

        dados['motivos'] = ", ".join(motivos)
        
        if is_op:
            oportunidades.append(dados)
        else:
            neutros.append(dados)

texto_status.empty()
bar.empty()

# ==========================================
# INTERFACE GRÁFICA
# ==========================================
cols_ratio = [0.8, 0.9, 0.6, 0.8, 1, 1, 2, 0.8, 0.8, 0.8, 0.8]

def desenhar_cabecalho():
    cols = st.columns(cols_ratio)
    titulos = ["Ativo", "Preço", "RSI", "Tend.", "Graham", "Bazin", "Sinais", "ROE", "P/L", "P/VP", "DY"]
    for i, t in enumerate(titulos):
        cols[i].markdown(f"**{t}**")
    st.divider()

def fmt_val(valor, prefix="R$ ", suffix="", casas=2):
    if valor is None: return "-"
    return f"{prefix}{valor:.{casas}f}{suffix}"

def fmt_cor(texto, cor):
    if cor == "black": return texto
    return f":{cor}[{texto}]"

def desenhar_linha(item, destaque=False):
    # Definição de Cores
    cor_rsi = "green" if item['rsi'] <= 35 else ("red" if item['rsi'] >= 70 else "gray")
    cor_tend = "green" if "Alta" in item['tendencia'] else "red"
    
    cor_graham = "green" if (item['graham'] and item['preco'] < item['graham']) else "gray"
    cor_bazin = "green" if (item['bazin'] and item['preco'] < item['bazin']) else "gray"
    
    cor_roe = "green" if (item['roe'] and item['roe'] > 0.15) else "gray"
    cor_pl = "green" if (item['pl'] and 0 < item['pl'] < 10) else "gray"
    cor_pvp = "green" if (item['pvp'] and 0 < item['pvp'] < 1.5) else "gray"
    cor_dy = "green" if (item['dy'] and item['dy'] > 0.06) else "gray"

    with st.container():
        if destaque: st.markdown("---")
        cols = st.columns(cols_ratio)
        
        cols[0].markdown(f"**{item['ticker']}**")
        cols[1].markdown(f"R$ {item['preco']:.2f}")
        cols[2].markdown(fmt_cor(f"**{item['rsi']:.0f}**", cor_rsi))
        cols[3].markdown(fmt_cor(item['tendencia'], cor_tend))
        
        cols[4].markdown(fmt_cor(fmt_val(item['graham']), cor_graham))
        cols[5].markdown(fmt_cor(fmt_val(item['bazin']), cor_bazin))
        
        if destaque: cols[6].success(item['motivos'])
        else: cols[6].caption("-")
            
        # Indicadores fundamentalistas
        val_roe = item['roe'] * 100 if item['roe'] else None
        cols[7].markdown(fmt_cor(fmt_val(val_roe, prefix="", suffix="%", casas=1), cor_roe))
        
        cols[8].markdown(fmt_cor(fmt_val(item['pl'], prefix="", casas=1), cor_pl))
        cols[9].markdown(fmt_cor(fmt_val(item['pvp'], prefix="", casas=2), cor_pvp))
        
        val_dy = item['dy'] * 100 if item['dy'] else None
        cols[10].markdown(fmt_cor(fmt_val(val_dy, prefix="", suffix="%", casas=1), cor_dy))

# Renderização
if oportunidades:
    st.subheader(f"🚀 Oportunidades ({len(oportunidades)})")
    desenhar_cabecalho()
    for item in oportunidades:
        desenhar_linha(item, destaque=True)

st.write("")
st.subheader(f"📋 Lista de Observação ({len(neutros)})")
desenhar_cabecalho()
for item in neutros:
    desenhar_linha(item, destaque=False)
