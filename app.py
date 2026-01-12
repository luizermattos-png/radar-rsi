import streamlit as st
import yfinance as yf
import pandas as pd
import math
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Monitor Valuation Pro", layout="wide")

# --- SUA CARTEIRA ---
MEUS_TICKERS = [
    "ALLD3.SA", "ALOS3.SA", "BBAS3.SA", "BHIA3.SA", "CMIG4.SA",
    "EMBJ3.SA", "FLRY3.SA", "GMAT3.SA", "GUAR3.SA", "HAPV3.SA",
    "ISAE4.SA", "ITSA4.SA", "ITUB4.SA", "IVVB11.SA", "KLBN4.SA",
    "MBRF3.SA", "MTRE3.SA", "PETR4.SA", "RAIL3.SA",
    "RDOR3.SA", "SANB4.SA", "UGPA3.SA", "VALE3.SA", "VULC3.SA",
    "WEGE3.SA"
]
# Removi "OCCI" que parecia ser um ticker americano perdido na lista BR

# --- CABEÇALHO ---
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.title("💎 Monitor Valuation & Momentum")
    st.caption("Graham + Bazin + RSI + Indicadores Fundamentalistas")
with c_head2:
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()
    st.write(f"📅 **{datetime.now().strftime('%d/%m/%Y')}**")

st.divider()

# ==========================================
# FUNÇÃO DE ANÁLISE
# ==========================================
@st.cache_data(ttl=3600)
def analisar_ativo(ticker):
    try:
        obj_ticker = yf.Ticker(ticker)
        
        # 1. DADOS TÉCNICOS (Preço e RSI) - Geralmente funcionam bem
        # Usamos 'auto_adjust=False' para evitar problemas com splits recentes
        df = obj_ticker.history(period="6mo", auto_adjust=False)
        
        if len(df) < 50: 
            return None
        
        # Ajuste manual se o dataframe vier vazio ou com colunas estranhas
        if 'Close' not in df.columns:
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

        # 2. DADOS FUNDAMENTAIS (Graham/Bazin) - A parte problemática
        # Inicializa com None para diferenciar "Zero" de "Sem Dados"
        lpa = None
        vpa = None
        roe = None
        pl = None
        pvp = None
        dy_percent = None
        
        try:
            info = obj_ticker.info
            # Tenta pegar chaves alternativas caso o Yahoo mude o nome
            lpa = info.get('trailingEps') or info.get('forwardEps')
            vpa = info.get('bookValue')
            roe = info.get('returnOnEquity')
            pl = info.get('trailingPE')
            pvp = info.get('priceToBook')
            dy_percent = info.get('dividendYield')
        except:
            pass # Falha silenciosa na coleta de info para não travar o app

        # Cálculos de Valuation
        preco_graham = None
        margem_graham = None
        
        if lpa and vpa and lpa > 0 and vpa > 0:
            try:
                val_graham = math.sqrt(22.5 * lpa * vpa)
                preco_graham = val_graham
                margem_graham = ((val_graham - preco_atual) / preco_atual) * 100
            except:
                pass

        preco_bazin = None
        # Tenta calcular DY em valor financeiro se não vier pronto
        dy_valor = 0
        if dy_percent and dy_percent > 0:
            dy_valor = dy_percent * preco_atual
            preco_bazin = dy_valor / 0.06

        return {
            'ticker': ticker.replace('.SA', ''), 
            'preco': preco_atual,
            'rsi': rsi_atual, 
            'tendencia': tendencia,
            'graham': preco_graham,       # Pode ser None
            'margem_graham': margem_graham, # Pode ser None
            'bazin': preco_bazin,         # Pode ser None
            'roe': roe,                   # Pode ser None
            'pl': pl,                     # Pode ser None
            'pvp': pvp,                   # Pode ser None
            'dy': dy_percent              # Pode ser None
        }
    except Exception as e:
        return None

# ==========================================
# LOOP DE EXECUÇÃO
# ==========================================

oportunidades = []
neutros = []

texto_status = st.empty()
bar = st.progress(0)

# Processamento
total = len(MEUS_TICKERS)
for i, ticker in enumerate(MEUS_TICKERS):
    texto_status.text(f"Analisando {ticker} ({i+1}/{total})...")
    dados = analisar_ativo(ticker)
    bar.progress((i + 1) / total)
    
    if dados:
        is_op = False
        motivos = []

        # RSI Baixo (<30 é mais conservador, <35 mais agressivo)
        if dados['rsi'] <= 35: 
            motivos.append("RSI Baixo")
            is_op = True
        
        # Graham com margem (só se tiver dados)
        if dados['margem_graham'] and dados['margem_graham'] > 20: 
            motivos.append(f"Graham +{dados['margem_graham']:.0f}%")
            is_op = True
            
        # Bazin (só se tiver dados)
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
# FUNÇÕES DE DESENHO (INTERFACE)
# ==========================================
# Ajustei as proporções das colunas para caber melhor
cols_ratio = [0.8, 0.9, 0.6, 0.8, 1, 1, 2, 0.8, 0.8, 0.8, 0.8]

def desenhar_cabecalho():
    cols = st.columns(cols_ratio)
    titulos = ["Ativo", "Preço", "RSI", "Tend.", "Graham", "Bazin", "Sinais", "ROE", "P/L", "P/VP", "DY"]
    for i, t in enumerate(titulos):
        cols[i].markdown(f"**{t}**")
    st.divider()

def fmt_val(valor, prefix="R$ ", suffix="", casas=2):
    """Formata valores lidando com None"""
    if valor is None:
        return "-"
    return f"{prefix}{valor:.{casas}f}{suffix}"

def fmt_cor(texto, cor):
    if cor == "black": return texto
    return f":{cor}[{texto}]"

def desenhar_linha(item, destaque=False):
    # Cores
    cor_rsi = "green" if item['rsi'] <= 35 else ("red" if item['rsi'] >= 70 else "black")
    cor_tend = "green" if "Alta" in item['tendencia'] else "red"
    
    # Só pinta de verde se o dado existir (is not None)
    cor_graham = "green" if (item['graham'] and item['preco'] < item['graham']) else "black"
    cor_bazin = "green" if (item['bazin'] and item['preco'] < item['bazin']) else "black"
    
    cor_roe = "green" if (item['roe'] and item['roe'] > 0.15) else "black"
    cor_pl = "green" if (item['pl'] and 0 < item['pl'] < 10) else "black"
    cor_pvp = "green" if (item['pvp'] and 0 < item['pvp'] < 1.5) else "black"
    cor_dy = "green" if (item['dy'] and item['dy'] > 0.06) else "black"

    with st.container():
        if destaque: st.markdown("---")
        
        cols = st.columns(cols_ratio)
        
        # 1. Ativo e Preço
        cols[0].markdown(f"**{item['ticker']}**")
        cols[1].markdown(f"R$ {item['preco']:.2f}")
        
        # 2. Técnicos
        cols[2].markdown(fmt_cor(f"**{item['rsi']:.0f}**", cor_rsi))
        cols[3].markdown(fmt_cor(item['tendencia'], cor_tend))
        
        # 3. Valuation
        cols[4].markdown(fmt_cor(fmt_val(item['graham']), cor_graham))
        cols[5].markdown(fmt_cor(fmt_val(item['bazin']), cor_bazin))
        
        # 4. Motivos
        if destaque: cols[6].success(item['motivos'])
        else: cols[6].caption("-")
            
        # 5. Fundamentos
        # Multiplicamos por 100 para % onde necessário, mas verificamos se não é None antes
        val_roe = item['roe'] * 100 if item['roe'] is not None else None
        cols[7].markdown(fmt_cor(fmt_val(val_roe, prefix="", suffix="%", casas=1), cor_roe))
        
        cols[8].markdown(fmt_cor(fmt_val(item['pl'], prefix="", casas=1), cor_pl))
        
        cols[9].markdown(fmt_cor(fmt_val(item['pvp'], prefix="", casas=2), cor_pvp))
        
        val_dy = item['dy'] * 100 if item['dy'] is not None else None
        cols[10].markdown(fmt_cor(fmt_val(val_dy, prefix="", suffix="%", casas=1), cor_dy))

# ==========================================
# RENDERIZAÇÃO
# ==========================================
if oportunidades:
    st.subheader(f"🚀 Oportunidades ({len(oportunidades)})")
    desenhar_cabecalho()
    for item in oportunidades:
        desenhar_linha(item, destaque=True)
else:
    st.info("Nenhuma oportunidade clara hoje.")

st.write("")
st.subheader(f"📋 Lista de Observação ({len(neutros)})")
desenhar_cabecalho()
for item in neutros:
    desenhar_linha(item, destaque=False)

# Rodapé
st.write("")
st.caption("Nota: Se os campos de valuation (Graham/Bazin/Fundamentos) aparecerem como '-', significa que o Yahoo Finance não forneceu os dados fundamentais para este ativo neste momento. Tente atualizar a página em alguns minutos.")
