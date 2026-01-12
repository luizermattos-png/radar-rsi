import streamlit as st
import yfinance as yf
import pandas as pd
import math
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Monitor Valuation Pro", layout="wide")

# --- CONFIGURAÇÃO DA SUA CARTEIRA ---
MEUS_TICKERS = [
    "ALLD3.SA", "ALOS3.SA", "BBAS3.SA", "BHIA3.SA", "CMIG4.SA",
    "EMBJ3.SA", "FLRY3.SA", "GMAT3.SA", "GUAR3.SA", "HAPV3.SA",
    "ISAE4.SA", "ITSA4.SA", "ITUB4.SA", "IVVB11.SA", "KLBN4.SA",
    "MBRF3.SA", "MTRE3.SA", "OCCI", "PETR4.SA", "RAIL3.SA",
    "RDOR3.SA", "SANB4.SA", "UGPA3.SA", "VALE3.SA", "VULC3.SA",
    "WEGE3.SA"
]

# --- CABEÇALHO ---
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.title("💎 Monitor Valuation & Momentum")
    st.caption("Graham + Bazin + RSI + Indicadores Fundamentalistas")
with c_head2:
    st.write("")
    st.write(f"📅 **{datetime.now().strftime('%d/%m/%Y')}**")

st.divider()

# ==========================================
# FUNÇÃO DE ANÁLISE (COM CACHE)
# ==========================================
@st.cache_data(ttl=3600) # Guarda os dados por 1 hora para não ficar lento
def analisar_ativo(ticker):
    try:
        obj_ticker = yf.Ticker(ticker)
        
        # 1. Dados Técnicos (Histórico)
        df = obj_ticker.history(period="6mo")
        if len(df) < 50: 
            return None
        
        # RSI Calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Tendência (MM50)
        df['MM50'] = df['Close'].rolling(window=50).mean()
        
        preco_atual = df['Close'].iloc[-1]
        rsi_atual = rsi.iloc[-1]
        mm50_atual = df['MM50'].iloc[-1]
        tendencia = "⬆️ Alta" if preco_atual > mm50_atual else "⬇️ Baixa"

        # 2. Dados Fundamentais (Info) - Esta parte é lenta
        try:
            info = obj_ticker.info
        except:
            # Fallback se falhar pegar info
            info = {}
        
        # Graham
        lpa = info.get('trailingEps', 0)
        vpa = info.get('bookValue', 0)
        preco_graham = 0
        margem_graham = 0
        
        if lpa and vpa and lpa > 0 and vpa > 0:
            try:
                preco_graham = math.sqrt(22.5 * lpa * vpa)
                if preco_graham > 0:
                    margem_graham = ((preco_graham - preco_atual) / preco_atual) * 100
            except:
                pass # Erro de domínio matemático

        # Bazin
        div_yield_val = info.get('trailingAnnualDividendRate', 0)
        dy_percent = info.get('dividendYield', 0)
        
        if (div_yield_val is None or div_yield_val == 0) and dy_percent:
             div_yield_val = dy_percent * preco_atual
        
        preco_bazin = 0
        if div_yield_val:
            preco_bazin = div_yield_val / 0.06

        # Outros Indicadores
        roe = info.get('returnOnEquity', 0)
        pl = info.get('trailingPE', 0)
        pvp = info.get('priceToBook', 0)
        
        if (pl is None or pl == 0) and lpa and lpa > 0:
            pl = preco_atual / lpa
            
        if (pvp is None or pvp == 0) and vpa and vpa > 0:
            pvp = preco_atual / vpa

        return {
            'ticker': ticker.replace('.SA', ''), 
            'preco': preco_atual,
            'rsi': rsi_atual, 
            'tendencia': tendencia,
            'graham': preco_graham,
            'margem_graham': margem_graham,
            'bazin': preco_bazin,
            'roe': roe if roe else 0,
            'pl': pl if pl else 0,
            'pvp': pvp if pvp else 0,
            'dy': dy_percent if dy_percent else 0
        }
    except Exception as e:
        # print(f"Erro ao analisar {ticker}: {e}") # Debug apenas no terminal
        return None

# ==========================================
# LOOP DE EXECUÇÃO
# ==========================================

oportunidades = []
neutros = []

texto_status = st.empty()
texto_status.info("🚀 Coletando dados... Isso pode demorar cerca de 30-60 segundos na primeira vez.")
barra = st.progress(0)

# Processamento
total = len(MEUS_TICKERS)
for i, ticker in enumerate(MEUS_TICKERS):
    dados = analisar_ativo(ticker)
    
    # Atualiza barra de progresso
    progresso = (i + 1) / total
    barra.progress(progresso)
    
    if dados:
        is_op = False
        motivos = []

        if dados['rsi'] <= 35: 
            motivos.append("RSI Baixo")
            is_op = True
        
        if dados['margem_graham'] > 20: 
            motivos.append(f"Graham +{dados['margem_graham']:.0f}%")
            is_op = True
            
        if dados['bazin'] > 0 and dados['preco'] < dados['bazin']:
            motivos.append("Teto Bazin")
            is_op = True

        dados['motivos'] = ", ".join(motivos)
        
        if is_op:
            oportunidades.append(dados)
        else:
            neutros.append(dados)

texto_status.empty()
barra.empty()

# ==========================================
# FUNÇÕES DE DESENHO (INTERFACE)
# ==========================================
cols_ratio = [0.8, 0.8, 0.6, 0.8, 1, 1, 2, 0.7, 0.7, 0.7, 0.7]

def desenhar_cabecalho():
    cols = st.columns(cols_ratio)
    titulos = ["Ativo", "Preço", "RSI", "Tend.", "Graham", "Bazin", "Sinais", "ROE", "P/L", "P/VP", "DY"]
    for i, t in enumerate(titulos):
        cols[i].markdown(f"**{t}**")
    st.divider()

def fmt_cor(valor, cor_solicitada, texto_exibicao=None):
    texto = texto_exibicao if texto_exibicao else str(valor)
    if cor_solicitada == "black":
        return texto 
    return f":{cor_solicitada}[{texto}]"

def desenhar_linha(item, destaque=False):
    # Lógica de Cores
    cor_rsi = "green" if item['rsi'] <= 35 else ("red" if item['rsi'] >= 70 else "black")
    
    cor_graham = "green" if (item['graham'] > 0 and item['preco'] < item['graham']) else "black"
    txt_graham = f"R${item['graham']:.2f}" if item['graham'] > 0 else "-"
    
    cor_bazin = "green" if (item['bazin'] > 0 and item['preco'] < item['bazin']) else "black"
    txt_bazin = f"R${item['bazin']:.2f}" if item['bazin'] > 0 else "-"

    cor_tend = "green" if "Alta" in item['tendencia'] else "red"
    
    cor_roe = "green" if item['roe'] > 0.15 else "black"
    cor_pl = "green" if 0 < item['pl'] < 10 else "black"
    cor_pvp = "green" if 0 < item['pvp'] < 1.5 else "black"
    cor_dy = "green" if item['dy'] > 0.06 else "black"

    with st.container():
        # Se for destaque, coloca um fundo leve (hack CSS visual simples ou apenas container)
        if destaque:
            st.markdown("---") 
        
        cols = st.columns(cols_ratio)
        
        cols[0].markdown(f"**{item['ticker']}**")
        cols[1].markdown(f"R$ {item['preco']:.2f}")
        
        cols[2].markdown(fmt_cor(None, cor_rsi, f"**{item['rsi']:.0f}**"))
        cols[3].markdown(f":{cor_tend}[{item['tendencia']}]")
        cols[4].markdown(fmt_cor(None, cor_graham, f"**{txt_graham}**"))
        cols[5].markdown(fmt_cor(None, cor_bazin, f"**{txt_bazin}**"))
        
        if destaque:
            cols[6].success(item['motivos'])
        else:
            cols[6].caption("-")
            
        cols[7].markdown(fmt_cor(None, cor_roe, f"{item['roe']*100:.1f}%"))
        cols[8].markdown(fmt_cor(None, cor_pl, f"{item['pl']:.1f}"))
        cols[9].markdown(fmt_cor(None, cor_pvp, f"{item['pvp']:.2f}"))
        cols[10].markdown(fmt_cor(None, cor_dy, f"{item['dy']*100:.1f}%"))

# ==========================================
# RENDERIZAÇÃO NA TELA
# ==========================================
if oportunidades:
    st.subheader(f"🚀 Oportunidades Identificadas ({len(oportunidades)})")
    desenhar_cabecalho()
    for item in oportunidades:
        desenhar_linha(item, destaque=True)
else:
    st.info("Nenhuma oportunidade óbvia encontrada hoje com os critérios atuais.")

st.write("")
st.subheader(f"📋 Lista de Observação ({len(neutros)})")
desenhar_cabecalho()
for item in neutros:
    desenhar_linha(item, destaque=False)

# Rodapé
st.write("")
with st.expander("📚 Legenda dos Indicadores"):
    st.markdown("""
    * **ROE:** Lucro sobre Patrimônio. Acima de 15% (Verde) = Eficiente.
    * **P/L:** Anos para retorno. Abaixo de 10 (Verde) = Barato.
    * **P/VP:** Preço sobre Patrimônio. Abaixo de 1.5 (Verde) = Desconto.
    * **DY:** Dividend Yield. Acima de 6% (Verde) = Bom pagador.
    * **Nota:** O carregamento pode ser lento devido à coleta de dados fundamentais do Yahoo Finance.
    """)

if st.button('🔄 Forçar Atualização (Limpar Cache)'):
    st.cache_data.clear()
    st.rerun()
