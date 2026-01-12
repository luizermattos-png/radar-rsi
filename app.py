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
# FUNÇÃO DE ANÁLISE (NATIVA YFINANCE)
# ==========================================
@st.cache_data(ttl=900) # Cache do próprio Streamlit (15 min)
def analisar_carteira(lista_tickers):
    resultados = []
    erros = []
    
    progresso = st.progress(0)
    status = st.empty()
    
    total = len(lista_tickers)
    
    for i, ticker in enumerate(lista_tickers):
        status.text(f"Analisando {ticker} ({i+1}/{total})...")
        progresso.progress((i + 1) / total)
        
        try:
            # Instancia normal (sem sessão customizada, pois o YF novo não aceita)
            stock = yf.Ticker(ticker)
            
            # 1. PEGAR PREÇO (Tenta fast_info, se falhar vai pro histórico)
            try:
                preco = stock.fast_info['last_price']
            except:
                hist = stock.history(period="1d")
                if not hist.empty:
                    preco = hist['Close'].iloc[-1]
                else:
                    erros.append(f"{ticker}: Sem preço")
                    continue # Pula este ticker
            
            # 2. CALCULAR RSI
            hist_long = stock.history(period="3mo")
            if len(hist_long) > 30:
                delta = hist_long['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                mm50 = hist_long['Close'].rolling(window=50).mean().iloc[-1]
                tendencia = "⬆️ Alta" if preco > mm50 else "⬇️ Baixa"
            else:
                rsi = 50
                tendencia = "-"

            # 3. PEGAR FUNDAMENTOS (Info)
            # O try/except aqui evita que um erro de conexão pare tudo
            info = {}
            try:
                info = stock.info
            except Exception:
                pass # Segue com info vazia se der erro

            # Extração de dados (com proteção contra Nulos)
            def get_i(key): return info.get(key)
            
            lpa = get_i('trailingEps') or get_i('forwardEps')
            vpa = get_i('bookValue')
            roe = get_i('returnOnEquity')
            pl = get_i('trailingPE')
            pvp = get_i('priceToBook')
            dy = get_i('dividendYield')

            # Cálculos Valuation
            graham = None
            if lpa and vpa and lpa > 0 and vpa > 0:
                try: graham = math.sqrt(22.5 * lpa * vpa)
                except: pass

            bazin = None
            if dy and dy > 0:
                bazin = (dy * preco) / 0.06

            # Monta o objeto de dados
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
                'motivos': []
            }
            
            # Filtros de Oportunidade
            if rsi <= 35: dados['motivos'].append("RSI Baixo")
            if graham and preco < graham: dados['motivos'].append("Desc. Graham")
            if bazin and preco < bazin: dados['motivos'].append("Teto Bazin")
            
            resultados.append(dados)

        except Exception as e:
            erros.append(f"{ticker}: {str(e)}")
        
        # PAUSA OBRIGATÓRIA (Para o Yahoo não bloquear)
        time.sleep(1.0) 

    progresso.empty()
    status.empty()
    return resultados, erros

# ==========================================
# INTERFACE GRÁFICA
# ==========================================
c1, c2 = st.columns([3, 1])
c1.title("💎 Monitor Valuation Pro")
c1.caption("Versão Compatível: yfinance v0.2.50+")

if c2.button("🔄 Atualizar Agora"):
    st.cache_data.clear()
    st.rerun()

st.divider()

# Chama a função principal
dados, erros_log = analisar_carteira(MEUS_TICKERS)

# Separação
oportunidades = [d for d in dados if d['motivos']]
neutros = [d for d in dados if not d['motivos']]

# Helpers de Formatação
def fmt_m(val, suffix=""): 
    if val is None: return "-"
    return f"{val*100:.1f}%{suffix}"

def fmt_v(val):
    if val is None: return "-"
    return f"R$ {val:.2f}"

def cor(val, limite, invert=False):
    if val is None: return "black"
    if invert: return "green" if val < limite else "black"
    return "green" if val > limite else "black"

# Função de Desenho da Tabela
cols_cfg = [0.8, 0.8, 0.6, 0.8, 0.9, 0.9, 2, 0.8, 0.8, 0.8, 0.8]
headers = ["Ativo", "Preço", "RSI", "Tend.", "Graham", "Bazin", "Sinais", "ROE", "P/L", "P/VP", "DY"]

def desenhar_tabela(lista, titulo):
    if not lista: return
    st.subheader(f"{titulo} ({len(lista)})")
    
    h_cols = st.columns(cols_cfg)
    for i, t in enumerate(headers): h_cols[i].markdown(f"**{t}**")
    st.divider()
    
    for item in lista:
        c = st.columns(cols_cfg)
        c[0].markdown(f"**{item['ticker']}**")
        c[1].write(f"R$ {item['preco']:.2f}")
        
        # RSI
        rsi_c = "green" if item['rsi'] <= 35 else ("red" if item['rsi'] >= 70 else "black")
        c[2].markdown(f":{rsi_c}[{item['rsi']:.0f}]")
        
        # Tendencia
        c[3].markdown(f":{'green' if 'Alta' in item['tendencia'] else 'red'}[{item['tendencia']}]")
        
        # Valuation
        g_c = "green" if item['graham'] and item['preco'] < item['graham'] else "black"
        c[4].markdown(f":{g_c}[{fmt_v(item['graham'])}]")
        
        b_c = "green" if item['bazin'] and item['preco'] < item['bazin'] else "black"
        c[5].markdown(f":{b_c}[{fmt_v(item['bazin'])}]")
        
        # Motivos
        if item['motivos']: c[6].success(", ".join(item['motivos']))
        else: c[6].caption("-")
        
        # Fundamentos
        c[7].markdown(f":{cor(item['roe'], 0.15)}[{fmt_m(item['roe'])}]")
        c[8].markdown(f":{cor(item['pl'], 10, True)}[{item['pl'] if item['pl'] else '-':.1f}]")
        c[9].markdown(f":{cor(item['pvp'], 1.5, True)}[{item['pvp'] if item['pvp'] else '-':.2f}]")
        c[10].markdown(f":{cor(item['dy'], 0.06)}[{fmt_m(item['dy'])}]")
        
        st.markdown("---")

# Renderiza
if not dados and erros_log:
    st.error("Não foi possível carregar dados. O Yahoo pode estar instável.")
else:
    desenhar_tabela(oportunidades, "🚀 Oportunidades")
    desenhar_tabela(neutros, "📋 Lista Geral")

# Log de erros discreto no final
if erros_log:
    with st.expander("Ver logs de erro (Técnico)"):
        for e in erros_log: st.write(e)
