import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA SUA CARTEIRA ---
MEUS_TICKERS = [
    "ALLD3.SA", "ALOS3.SA", "BBAS3.SA", "BHIA3.SA", "CMIG4.SA",
    "EMBJ3.SA", "FLRY3.SA", "GMAT3.SA", "GUAR3.SA", "HAPV3.SA",
    "ISAE4.SA", "ITSA4.SA", "ITUB4.SA", "IVVB11.SA", "KLBN4.SA",
    "MBRF3.SA", "MTRE3.SA", "OCCI", "PETR4.SA", "RAIL3.SA",
    "RDOR3.SA", "SANB4.SA", "UGPA3.SA", "VALE3.SA", "VULC3.SA",
    "WEGE3.SA"
]

st.set_page_config(page_title="Monitor Pro", layout="centered")

# --- CABEÇALHO ---
st.title("📊 Monitor Pro Inteligente")
data_atual = datetime.now().strftime("%d/%m/%Y")
st.caption(f"📅 {data_atual} | Estratégia: RSI + Tendência (MM50)")
st.divider()

# Função de Análise
def analisar_ativo(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if len(df) < 50: return None

        # 1. RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 2. Tendência (MM50)
        df['MM50'] = df['Close'].rolling(window=50).mean()
        
        # Valores atuais
        rsi_val = rsi.iloc[-1]
        if isinstance(rsi_val, pd.Series): rsi_val = rsi_val.item()
        
        preco_val = df['Close'].iloc[-1]
        if isinstance(preco_val, pd.Series): preco_val = preco_val.item()
        
        mm50_val = df['MM50'].iloc[-1]
        if isinstance(mm50_val, pd.Series): mm50_val = mm50_val.item()
        
        # Lógica da Tendência
        tendencia_str = "⬆️ Alta" if preco_val > mm50_val else "⬇️ Baixa"
        
        return {
            'ticker': ticker.replace('.SA', ''), 
            'rsi': rsi_val, 
            'preco': preco_val,
            'tendencia': tendencia_str
        }
    except:
        return None

# Listas
oportunidades = []
alertas = []
neutros = []

barra = st.progress(0)

# --- PROCESSAMENTO INTELIGENTE ---
for i, ticker in enumerate(MEUS_TICKERS):
    dados = analisar_ativo(ticker)
    if dados:
        rsi = dados['rsi']
        tendencia = dados['tendencia']
        
        # Lógica de Oportunidade Refinada
        eh_oportunidade = False
        motivo = ""

        # Critério 1: Muito Barato (RSI < 30) - Clássico
        if rsi <= 30:
            eh_oportunidade = True
            motivo = "💎 Barato"
        
        # Critério 2: Pullback de Alta (RSI < 50 E Tendência Alta)
        elif rsi <= 50 and "Alta" in tendencia:
            eh_oportunidade = True
            motivo = "🚀 Pullback"
            
        if eh_oportunidade:
            dados['motivo'] = motivo
            oportunidades.append(dados)
            
        elif rsi >= 70:
            alertas.append(dados)
        else:
            neutros.append(dados)
            
    barra.progress((i + 1) / len(MEUS_TICKERS))

barra.empty()

# Ordenar Oportunidades: Primeiro as de Tendência de Alta, depois pelo menor RSI
if oportunidades:
    oportunidades.sort(key=lambda x: (0 if "Alta" in x['tendencia'] else 1, x['rsi']))

# --- FUNÇÃO DE DESENHO ---
def desenhar_tabela(lista_ativos, cor_destaque, icone_titulo, titulo, mostrar_motivo=False):
    if len(lista_ativos) > 0:
        st.markdown(f"### {icone_titulo} {titulo}")
        
        # Colunas dinâmicas (com ou sem motivo)
        cols = st.columns([1.5, 1.2, 1.5, 1.5, 1.5]) if mostrar_motivo else st.columns([1.5, 1.2, 1.5, 1.5])
        
        cols[0].markdown("**Ativo**")
        cols[1].markdown("**RSI**")
        cols[2].markdown("**Tend.**")
        cols[3].markdown("**Preço**")
        if mostrar_motivo: cols[4].markdown("**Sinal**")
        
        for item in lista_ativos:
            with st.container():
                c_row = st.columns([1.5, 1.2, 1.5, 1.5, 1.5]) if mostrar_motivo else st.columns([1.5, 1.2, 1.5, 1.5])
                
                c_row[0].write(f"**{item['ticker']}**")
                c_row[1].markdown(f":{cor_destaque}[**{item['rsi']:.0f}**]")
                
                cor_tend = "green" if "Alta" in item['tendencia'] else "red"
                c_row[2].markdown(f":{cor_tend}[{item['tendencia']}]")
                
                c_row[3].write(f"{item['preco']:.2f}")
                
                if mostrar_motivo:
                    # Badge visual para o motivo
                    bg = "#d4edda" if "Pullback" in item['motivo'] else "#cce5ff"
                    cor_txt = "#155724" if "Pullback" in item['motivo'] else "#004085"
                    c_row[4].markdown(f"<span style='background-color:{bg}; color:{cor_txt}; padding: 2px 6px; border-radius:4px; font-size:12px;'>{item['motivo']}</span>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)

# --- EXIBIÇÃO ---

# 1. Oportunidades (Agora considera RSI e Tendência)
if oportunidades:
    st.success(f"{len(oportunidades)} Ativos na Zona de Compra (Desconto ou Tendência)")
    desenhar_tabela(oportunidades, "green", "🟢", "OPORTUNIDADES", mostrar_motivo=True)
else:
    # Caso EXTREMO onde nada se encaixa (raro agora)
    st.warning("Mercado difícil: Nenhum ativo barato e nenhuma tendência de alta clara.")

st.divider()

# 2. Alertas
if alertas:
    desenhar_tabela(alertas, "red", "🔴", "ZONA DE VENDA (RSI Alto)")
    st.divider()

# 3. Neutros
with st.expander(f"Ver Neutros ({len(neutros)})", expanded=True):
    desenhar_tabela(neutros, "gray", "⚪", "Observar (Sem direção clara)")

st.write("")
st.write("")

# --- GUIA ---
with st.expander("📚 Entenda os Sinais Novos"):
    st.markdown("""
    ### 🟢 Tipos de Oportunidade
    Agora o sistema encontra dois tipos de compra:
    
    1. **💎 Barato (Reversão):**
       * **O que é:** O RSI caiu abaixo de 30.
       * **Risco:** Médio/Alto (pode continuar caindo).
       * **Estratégia:** Tentar pegar o fundo do poço.
       
    2. **🚀 Pullback (Tendência):**
       * **O que é:** O RSI está abaixo de 50, mas a Tendência é de ALTA (Seta para cima).
       * **Risco:** Baixo (está a favor da maré).
       * **Estratégia:** O ativo subiu, descansou um pouco e deve voltar a subir. É o melhor cenário.
    """)

if st.button('Atualizar'):
    st.rerun()
