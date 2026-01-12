import streamlit as st
import pandas as pd
import math
from datetime import datetime
from yahooquery import Ticker

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
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

# --- CABEÇALHO ---
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.title("💎 Monitor Valuation & Momentum")
    st.caption("Motor: YahooQuery (Alta Velocidade)")
with c_head2:
    if st.button("🔄 Forçar Atualização"):
        st.cache_data.clear()
        st.rerun()
    st.write(f"📅 **{datetime.now().strftime('%d/%m/%Y')}**")

st.divider()

# ==========================================
# FUNÇÃO DE COLETA EM MASSA (O SEGREDO DA VELOCIDADE)
# ==========================================
@st.cache_data(ttl=1800)
def coletar_dados_em_massa(lista_tickers):
    try:
        # Instancia o Ticker com a lista completa
        t = Ticker(lista_tickers)
        
        # 1. Coleta Fundamentos (1 requisição para todos)
        # summary_detail: P/L, Yield, Preço
        # key_stats: P/VP, Book Value, EPS (LPA)
        # financial_data: ROE
        all_summary = t.summary_detail
        all_stats = t.key_stats
        all_financial = t.financial_data
        all_price = t.price
        
        # 2. Coleta Histórico para RSI (1 requisição para todos)
        historico = t.history(period='3mo', interval='1d')
        
        return all_summary, all_stats, all_financial, all_price, historico
    except Exception as e:
        st.error(f"Erro na conexão com Yahoo Finance: {e}")
        return None, None, None, None, None

# ==========================================
# PROCESSAMENTO DOS DADOS
# ==========================================
def processar_ativos():
    oportunidades = []
    neutros = []
    
    with st.spinner('🚀 Baixando dados de todos os ativos de uma vez...'):
        summary, stats, financial, price_data, history = coletar_dados_em_massa(MEUS_TICKERS)
    
    if summary is None:
        return [], []

    progresso = st.progress(0)
    
    for i, ticker in enumerate(MEUS_TICKERS):
        progresso.progress((i + 1) / len(MEUS_TICKERS))
        
        try:
            # --- EXTRAÇÃO DE DADOS (COM PROTEÇÃO CONTRA ERROS) ---
            # Verifica se o ticker retornou dados (alguns podem falhar individualmente)
            if isinstance(summary, dict) and isinstance(summary.get(ticker), str):
                continue # Ticker inválido retornou string de erro

            # Helpers para pegar dados com segurança (retorna 0 ou None se falhar)
            def get_val(source, t, key):
                try:
                    val = source[t][key]
                    return val if isinstance(val, (int, float)) else None
                except:
                    return None

            preco = get_val(price_data, ticker, 'regularMarketPrice')
            if preco is None: continue # Sem preço, pula

            # Fundamentos
            lpa = get_val(stats, ticker, 'trailingEps') or get_val(stats, ticker, 'forwardEps')
            vpa = get_val(stats, ticker, 'bookValue')
            pe = get_val(summary, ticker, 'trailingPE')
            p_vp = get_val(stats, ticker, 'priceToBook')
            roe = get_val(financial, ticker, 'returnOnEquity')
            dy = get_val(summary, ticker, 'dividendYield')

            # --- CÁLCULOS TÉCNICOS (RSI) ---
            # Filtra o dataframe multi-index para o ticker específico
            try:
                df_ticker = history.loc[ticker].copy()
                delta = df_ticker['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                rsi_val = rsi.iloc[-1]
                
                # Tendência Simples (MM50)
                mm50 = df_ticker['close'].rolling(window=50).mean().iloc[-1]
                tendencia = "⬆️ Alta" if preco > mm50 else "⬇️ Baixa"
            except:
                rsi_val = 50 # Neutro se falhar
                tendencia = "-"

            # --- CÁLCULOS VALUATION ---
            # Graham
            graham = None
            margem_graham = None
            if lpa and vpa and lpa > 0 and vpa > 0:
                try:
                    graham = math.sqrt(22.5 * lpa * vpa)
                    margem_graham = ((graham - preco) / preco) * 100
                except: pass

            # Bazin
            bazin = None
            if dy and dy > 0:
                # O Yahoo entrega DY como 0.06 (6%), precisamos converter para valor em R$
                dy_valor = dy * preco
                bazin = dy_valor / 0.06

            # --- ESTRUTURA FINAL ---
            dados = {
                'ticker': ticker.replace('.SA', ''),
                'preco': preco,
                'rsi': rsi_val,
                'tendencia': tendencia,
                'graham': graham,
                'margem_graham': margem_graham,
                'bazin': bazin,
                'roe': roe,
                'pl': pe,
                'pvp': p_vp,
                'dy': dy,
                'motivos': []
            }

            # --- FILTROS DE OPORTUNIDADE ---
            is_op = False
            if rsi_val <= 35:
                dados['motivos'].append("RSI Baixo")
                is_op = True
            
            if margem_graham and margem_graham > 20:
                dados['motivos'].append(f"Graham +{margem_graham:.0f}%")
                is_op = True
                
            if bazin and preco < bazin:
                dados['motivos'].append("Teto Bazin")
                is_op = True

            dados['motivos_str'] = ", ".join(dados['motivos'])

            if is_op:
                oportunidades.append(dados)
            else:
                neutros.append(dados)

        except Exception as e:
            # st.error(f"Erro processando {ticker}: {e}")
            continue

    progresso.empty()
    return oportunidades, neutros

# Executa a lógica
oportunidades, neutros = processar_ativos()

# ==========================================
# INTERFACE GRÁFICA (TABELAS)
# ==========================================
cols_ratio = [0.8, 0.9, 0.6, 0.8, 1, 1, 2, 0.8, 0.8, 0.8, 0.8]

def desenhar_cabecalho():
    cols = st.columns(cols_ratio)
    titulos = ["Ativo", "Preço", "RSI", "Tend.", "Graham", "Bazin", "Sinais", "ROE", "P/L", "P/VP", "DY"]
    for i, t in enumerate(titulos):
        cols[i].markdown(f"**{t}**")
    st.divider()

def fmt_val(valor, prefix="R$ ", suffix="", casas=2, multiplier=1):
    if valor is None: return "-"
    return f"{prefix}{valor*multiplier:.{casas}f}{suffix}"

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
        
        if destaque: cols[6].success(item['motivos_str'])
        else: cols[6].caption("-")
            
        # Indicadores (ROE e DY vem em decimal do YahooQuery, ex: 0.15 para 15%)
        cols[7].markdown(fmt_cor(fmt_val(item['roe'], prefix="", suffix="%", multiplier=100, casas=1), cor_roe))
        cols[8].markdown(fmt_cor(fmt_val(item['pl'], prefix="", casas=1), cor_pl))
        cols[9].markdown(fmt_cor(fmt_val(item['pvp'], prefix="", casas=2), cor_pvp))
        cols[10].markdown(fmt_cor(fmt_val(item['dy'], prefix="", suffix="%", multiplier=100, casas=1), cor_dy))

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
