import streamlit as st
import yfinance as yf
import pandas as pd
import math
import requests_cache
from datetime import datetime, timedelta

# ==========================================
# CONFIGURAÇÃO E CACHE (O SEGREDO)
# ==========================================
st.set_page_config(page_title="Monitor Valuation Pro", layout="wide")

# Cria uma sessão que salva os dados num arquivo local 'yahoo_cache.sqlite'.
# Isso evita pedir a mesma coisa pro Yahoo repetidamente e evita o bloqueio.
session = requests_cache.CachedSession('yahoo_cache', expire_after=timedelta(hours=1))

# Adiciona cabeçalhos para fingir ser um navegador Google Chrome
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

MEUS_TICKERS = [
    "ALLD3.SA", "ALOS3.SA", "BBAS3.SA", "BHIA3.SA", "CMIG4.SA",
    "EMBJ3.SA", "FLRY3.SA", "GMAT3.SA", "GUAR3.SA", "HAPV3.SA",
    "ISAE4.SA", "ITSA4.SA", "ITUB4.SA", "IVVB11.SA", "KLBN4.SA",
    "MBRF3.SA", "MTRE3.SA", "PETR4.SA", "RAIL3.SA",
    "RDOR3.SA", "SANB4.SA", "UGPA3.SA", "VALE3.SA", "VULC3.SA",
    "WEGE3.SA"
]

# ==========================================
# INTERFACE
# ==========================================
c1, c2 = st.columns([3, 1])
c1.title("💎 Monitor Valuation & Momentum")
c1.caption("Motor: yfinance + Requests Cache (Modo Anti-Bloqueio)")

if c2.button("🗑️ Limpar Cache e Atualizar"):
    session.cache.clear()
    st.cache_data.clear()
    st.rerun()

st.divider()

# ==========================================
# FUNÇÃO DE ANÁLISE INDIVIDUAL
# ==========================================
def analisar_ativo(ticker):
    log_erros = []
    try:
        # Usa a sessão com cache
        stock = yf.Ticker(ticker, session=session)
        
        # 1. TENTA PEGAR O PREÇO E INFO
        # fast_info é mais rápido e falha menos que .info
        try:
            preco = stock.fast_info['last_price']
        except:
            # Fallback para histórico se fast_info falhar
            hist_hoje = stock.history(period='1d')
            if not hist_hoje.empty:
                preco = hist_hoje['Close'].iloc[-1]
            else:
                return None, ["Sem preço disponível"]

        # 2. RSI (Histórico)
        hist = stock.history(period="3mo")
        if len(hist) < 30:
            rsi = 50 # Neutro
            tendencia = "-"
        else:
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            mm50 = hist['Close'].rolling(window=50).mean().iloc[-1]
            tendencia = "⬆️ Alta" if preco > mm50 else "⬇️ Baixa"

        # 3. FUNDAMENTOS (A parte crítica)
        info = stock.info
        if not info or len(info) < 5:
            # Se info vier vazio, é sinal de bloqueio parcial ou falta de dados
            log_erros.append("Yahoo não retornou Info Fundamentalista")
            # Continuamos apenas com dados técnicos
            return {
                'ticker': ticker.replace('.SA', ''),
                'preco': preco,
                'rsi': rsi,
                'tendencia': tendencia,
                'graham': None,
                'bazin': None,
                'roe': None,
                'pl': None,
                'pvp': None,
                'dy': None,
                'erro_info': True
            }, log_erros

        # Extração segura
        lpa = info.get('trailingEps') or info.get('forwardEps')
        vpa = info.get('bookValue')
        roe = info.get('returnOnEquity')
        pl = info.get('trailingPE')
        pvp = info.get('priceToBook')
        dy = info.get('dividendYield')

        # Cálculos Valuation
        graham = None
        if lpa and vpa and lpa > 0 and vpa > 0:
            try: graham = math.sqrt(22.5 * lpa * vpa)
            except: pass

        bazin = None
        if dy and dy > 0:
            bazin = (dy * preco) / 0.06

        return {
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
            'erro_info': False
        }, log_erros

    except Exception as e:
        return None, [str(e)]

# ==========================================
# LOOP DE EXECUÇÃO
# ==========================================
dados_finais = []
erros_globais = {}

bar = st.progress(0)
status = st.empty()

for i, ticker in enumerate(MEUS_TICKERS):
    status.text(f"Analisando {ticker}...")
    res, logs = analisar_ativo(ticker)
    
    if logs:
        erros_globais[ticker] = logs
        
    if res:
        # Prepara a string de motivos
        motivos = []
        if res['rsi'] <= 35: motivos.append("RSI Baixo")
        if res['graham'] and res['preco'] < res['graham']: motivos.append("Desc. Graham")
        if res['bazin'] and res['preco'] < res['bazin']: motivos.append("Teto Bazin")
        
        res['motivos'] = ", ".join(motivos)
        dados_finais.append(res)
        
    bar.progress((i+1)/len(MEUS_TICKERS))

status.empty()
bar.empty()

# ==========================================
# EXIBIÇÃO
# ==========================================

# Formatação auxiliar
def cor_val(val, ideal, invert=False):
    if val is None: return "black"
    if invert: return "green" if val < ideal else "black"
    return "green" if val > ideal else "black"

def fmt(val, prefix="", suffix="", mult=1, d=2):
    if val is None: return "-"
    return f"{prefix}{val*mult:.{d}f}{suffix}"

# Cabeçalho da Tabela
cols_ratio = [0.8, 0.8, 0.6, 0.8, 0.9, 0.9, 2, 0.8, 0.8, 0.8, 0.8]
header = ["Ativo", "Preço", "RSI", "Tend.", "Graham", "Bazin", "Sinais", "ROE", "P/L", "P/VP", "DY"]

if not dados_finais:
    st.error("Nenhum dado foi carregado. Verifique a seção de Diagnóstico abaixo.")
else:
    # Separa oportunidades
    ops = [d for d in dados_finais if d['motivos']]
    neutros = [d for d in dados_finais if not d['motivos']]

    # Função de desenhar tabela
    def draw_table(lista_dados, titulo):
        if not lista_dados: return
        st.subheader(f"{titulo} ({len(lista_dados)})")
        
        c = st.columns(cols_ratio)
        for i, h in enumerate(header): c[i].markdown(f"**{h}**")
        st.divider()
        
        for item in lista_dados:
            c = st.columns(cols_ratio)
            c[0].write(f"**{item['ticker']}**")
            c[1].write(f"R$ {item['preco']:.2f}")
            
            # RSI
            cor_rsi = "green" if item['rsi'] <= 35 else ("red" if item['rsi'] >= 70 else "black")
            c[2].markdown(f":{cor_rsi}[{item['rsi']:.0f}]")
            
            # Tendencia
            c[3].markdown(f":{'green' if 'Alta' in item['tendencia'] else 'red'}[{item['tendencia']}]")
            
            # Valuation
            cor_g = "green" if item['graham'] and item['preco'] < item['graham'] else "black"
            c[4].markdown(f":{cor_g}[{fmt(item['graham'], 'R$ ')}]")
            
            cor_b = "green" if item['bazin'] and item['preco'] < item['bazin'] else "black"
            c[5].markdown(f":{cor_b}[{fmt(item['bazin'], 'R$ ')}]")
            
            # Sinais
            if item['motivos']: c[6].success(item['motivos'])
            else: c[6].caption("-")
            
            # Fundamentos
            if item['erro_info']:
                c[7].caption("N/A")
                c[8].caption("N/A")
                c[9].caption("N/A")
                c[10].caption("N/A")
            else:
                c[7].markdown(f":{cor_val(item['roe'], 0.15)}[{fmt(item['roe'], mult=100, suffix='%', d=1)}]")
                c[8].markdown(f":{cor_val(item['pl'], 10, invert=True)}[{fmt(item['pl'], d=1)}]")
                c[9].markdown(f":{cor_val(item['pvp'], 1.5, invert=True)}[{fmt(item['pvp'], d=2)}]")
                c[10].markdown(f":{cor_val(item['dy'], 0.06)}[{fmt(item['dy'], mult=100, suffix='%', d=1)}]")
            
            st.markdown("---")

    draw_table(ops, "🚀 Oportunidades")
    draw_table(neutros, "📋 Lista de Observação")

# ==========================================
# DIAGNÓSTICO DE ERROS (PARA SABERMOS O QUE OCORREU)
# ==========================================
with st.expander("🛠️ Diagnóstico de Erros (Se a tabela estiver vazia, veja aqui)"):
    st.write(f"Total analisado: {len(dados_finais)} de {len(MEUS_TICKERS)}")
    if erros_globais:
        st.warning("Alguns ativos retornaram erros:")
        for t, e in erros_globais.items():
            st.write(f"**{t}**: {e}")
    else:
        st.success("Nenhum erro crítico detectado nos logs.")
