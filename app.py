import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import math
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

st.set_page_config(page_title="Monitor Valuation Pro", layout="wide")

# --- GERENCIAMENTO DE ESTADO (NAVEGAÇÃO) ---
if 'ativo_selecionado' not in st.session_state:
    st.session_state['ativo_selecionado'] = None

# --- FUNÇÃO DO GRÁFICO DE DETALHES ---
def mostrar_detalhes_ativo(ticker):
    st.button("⬅️ Voltar para a Lista", on_click=lambda: st.session_state.update(ativo_selecionado=None))
    
    st.title(f"📊 Análise Profunda: {ticker}")
    
    with st.spinner('Baixando histórico de Cotação e Lucros...'):
        try:
            ativo = yf.Ticker(ticker)
            
            # 1. Histórico de Preços (Mensal para suavizar)
            hist = ativo.history(period="5y", interval="1mo")
            hist.index = pd.to_datetime(hist.index).tz_localize(None) # Remove fuso para compatibilidade
            
            # 2. Histórico de Lucros (Anual)
            financials = ativo.financials.T
            # Tenta pegar Lucro Líquido (vários nomes possíveis na API)
            col_lucro = None
            for col in ['Net Income', 'Net Income Common Stockholders', 'Net Income Continuous Operations']:
                if col in financials.columns:
                    col_lucro = col
                    break
            
            if col_lucro and not hist.empty:
                # Tratamento de datas dos balanços
                financials.index = pd.to_datetime(financials.index).tz_localize(None)
                financials = financials.sort_index()
                
                # --- CRIAÇÃO DO GRÁFICO COM PLOTLY (Eixo Duplo) ---
                fig = go.Figure()

                # Linha 1: Cotação (Eixo Esquerdo)
                fig.add_trace(go.Scatter(
                    x=hist.index, 
                    y=hist['Close'],
                    name="Cotação (Preço)",
                    line=dict(color='#ffc107', width=3), # Amarelo/Dourado igual a imagem
                    yaxis='y1'
                ))

                # Linha 2: Lucro Líquido (Eixo Direito)
                # Usamos Scatter com markers+lines para destacar os anos
                fig.add_trace(go.Scatter(
                    x=financials.index, 
                    y=financials[col_lucro],
                    name="Lucro Líquido (Anual)",
                    line=dict(color='#28a745', width=3, shape='spline'), # Verde
                    mode='lines+markers',
                    yaxis='y2'
                ))

                # Layout para Eixo Duplo
                fig.update_layout(
                    title=f"Cotação vs Lucro Líquido (5 Anos)",
                    xaxis=dict(title="Tempo"),
                    yaxis=dict(
                        title="Preço da Ação (R$)",
                        titlefont=dict(color="#ffc107"),
                        tickfont=dict(color="#ffc107")
                    ),
                    yaxis2=dict(
                        title="Lucro Líquido (Bilhões)",
                        titlefont=dict(color="#28a745"),
                        tickfont=dict(color="#28a745"),
                        overlaying='y',
                        side='right'
                    ),
                    legend=dict(x=0.01, y=0.99),
                    hovermode="x unified",
                    height=600
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.info("💡 **Interpretação:** O ideal é ver a linha Amarela (Cotação) acompanhando a linha Verde (Lucro). Se o Lucro sobe e a Cotação cai, pode ser uma oportunidade (Boca de Jacaré).")

            else:
                st.warning("Não foi possível extrair o histórico de Lucros deste ativo automaticamente via Yahoo Finance.")
                st.line_chart(hist['Close'])

        except Exception as e:
            st.error(f"Erro ao gerar gráfico: {e}")

# --- FUNÇÃO DE ANÁLISE DA TABELA (CÓDIGO ANTERIOR) ---
def analisar_ativo(ticker):
    try:
        obj_ticker = yf.Ticker(ticker)
        df = obj_ticker.history(period="6mo")
        if len(df) < 50: return None
        
        # RSI e Tendência
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        df['MM50'] = df['Close'].rolling(window=50).mean()
        
        preco_atual = df['Close'].iloc[-1]
        rsi_atual = rsi.iloc[-1]
        mm50_atual = df['MM50'].iloc[-1]
        tendencia = "⬆️ Alta" if preco_atual > mm50_atual else "⬇️ Baixa"

        # Fundamentos
        info = obj_ticker.info
        lpa = info.get('trailingEps', 0)
        vpa = info.get('bookValue', 0)
        
        # Graham
        preco_graham = 0
        margem_graham = 0
        if lpa and vpa and lpa > 0 and vpa > 0:
            preco_graham = math.sqrt(22.5 * lpa * vpa)
            if preco_graham > 0:
                margem_graham = ((preco_graham - preco_atual) / preco_atual) * 100

        # Bazin
        div_yield_val = info.get('trailingAnnualDividendRate', 0)
        dy_percent = info.get('dividendYield', 0)
        if (div_yield_val is None or div_yield_val == 0) and dy_percent:
             div_yield_val = dy_percent * preco_atual
        preco_bazin = 0 if not div_yield_val else div_yield_val / 0.06

        # Indicadores
        roe = info.get('returnOnEquity', 0)
        pl = info.get('trailingPE', 0)
        if (pl is None or pl == 0) and lpa and lpa > 0: pl = preco_atual / lpa
        pvp = info.get('priceToBook', 0)
        if (pvp is None or pvp == 0) and vpa and vpa > 0: pvp = preco_atual / vpa

        return {
            'ticker': ticker.replace('.SA', ''), 
            'preco': preco_atual, 'rsi': rsi_atual, 'tendencia': tendencia,
            'graham': preco_graham, 'margem_graham': margem_graham,
            'bazin': preco_bazin, 'roe': roe if roe else 0,
            'pl': pl if pl else 0, 'pvp': pvp if pvp else 0,
            'dy': dy_percent if dy_percent else 0
        }
    except:
        return None

# --- RENDERIZAÇÃO PRINCIPAL ---

# SE TIVER ATIVO SELECIONADO, MOSTRA O GRÁFICO
if st.session_state['ativo_selecionado']:
    mostrar_detalhes_ativo(st.session_state['ativo_selecionado'])

# SE NÃO, MOSTRA A TABELA
else:
    # Cabeçalho
    c_head1, c_head2 = st.columns([3, 1])
    with c_head1:
        st.title("💎 Monitor Valuation & Momentum")
    with c_head2:
        st.write(f"📅 **{datetime.now().strftime('%d/%m/%Y')}**")
    st.divider()

    # Processamento
    oportunidades = []
    neutros = []
    
    msg = st.empty()
    msg.info("🚀 Varrendo mercado... Clique no Ticker para ver o gráfico de Lucros!")
    barra = st.progress(0)

    for i, ticker in enumerate(MEUS_TICKERS):
        dados = analisar_ativo(ticker)
        if dados:
            is_op = False
            motivos = []
            if dados['rsi'] <= 35: motivos.append("RSI Baixo"); is_op = True
            if dados['margem_graham'] > 20: motivos.append(f"Graham +{dados['margem_graham']:.0f}%"); is_op = True
            if dados['bazin'] > 0 and dados['preco'] < dados['bazin']: motivos.append("Teto Bazin"); is_op = True
            dados['motivos'] = ", ".join(motivos)
            
            if is_op: oportunidades.append(dados)
            else: neutros.append(dados)
        barra.progress((i + 1) / len(MEUS_TICKERS))
    
    msg.empty(); barra.empty()

    # Função de Desenho da Linha com Botão
    cols_ratio = [0.8, 0.8, 0.6, 0.8, 1, 1, 2, 0.7, 0.7, 0.7, 0.7]

    def desenhar_cabecalho():
        cols = st.columns(cols_ratio)
        cols[0].markdown("**Ativo (Clique)**") # Indicando que é clicável
        cols[1].markdown("**Preço**")
        cols[2].markdown("**RSI**")
        cols[3].markdown("**Tend.**")
        cols[4].markdown("**Graham**")
        cols[5].markdown("**Bazin**")
        cols[6].markdown("**Sinais**")
        cols[7].markdown("**ROE**")
        cols[8].markdown("**P/L**")
        cols[9].markdown("**P/VP**")
        cols[10].markdown("**DY**")
        st.divider()

    def fmt_cor(valor, cor_solicitada, texto_exibicao=None):
        texto = texto_exibicao if texto_exibicao else str(valor)
        if cor_solicitada == "black": return texto
        return f":{cor_solicitada}[{texto}]"

    def desenhar_linha(item, destaque=False):
        # Lógica de cores (igual antes)
        cor_rsi = "green" if item['rsi'] <= 35 else ("red" if item['rsi'] >= 70 else "black")
        cor_graham = "green" if (item['graham'] > 0 and item['preco'] < item['graham']) else "black"
        cor_bazin = "green" if (item['bazin'] > 0 and item['preco'] < item['bazin']) else "black"
        cor_tend = "green" if "Alta" in item['tendencia'] else "red"
        cor_roe = "green" if item['roe'] > 0.15 else "black"
        cor_pl = "green" if 0 < item['pl'] < 10 else "black"
        cor_pvp = "green" if 0 < item['pvp'] < 1.5 else "black"
        cor_dy = "green" if item['dy'] > 0.06 else "black"
        
        bg_style = "background-color: #f0f8ff; border-radius: 5px; padding: 5px 0;" if destaque else ""

        with st.container():
            if destaque: st.markdown(f"<div style='{bg_style}'>", unsafe_allow_html=True)
            cols = st.columns(cols_ratio)
            
            # --- A MÁGICA DO CLIQUE ESTÁ AQUI ---
            # O Ticker vira um botão. Ao clicar, atualiza o estado e recarrega a página.
            ticker_completo = item['ticker'] + ".SA" if "OCCI" not in item['ticker'] else item['ticker']
            
            if cols[0].button(f"🔎 {item['ticker']}", key=f"btn_{item['ticker']}"):
                st.session_state['ativo_selecionado'] = ticker_completo
                st.rerun()
            
            cols[1].markdown(f"R$ {item['preco']:.2f}")
            cols[2].markdown(fmt_cor(None, cor_rsi, f"**{item['rsi']:.0f}**"))
            cols[3].markdown(f":{cor_tend}[{item['tendencia']}]")
            cols[4].markdown(fmt_cor(None, cor_graham, f"**R${item['graham']:.2f}**" if item['graham'] > 0 else "-"))
            cols[5].markdown(fmt_cor(None, cor_bazin, f"**R${item['bazin']:.2f}**" if item['bazin'] > 0 else "-"))
            
            if destaque: cols[6].success(item['motivos'])
            else: cols[6].caption("-")
                
            cols[7].markdown(fmt_cor(None, cor_roe, f"{item['roe']*100:.1f}%"))
            cols[8].markdown(fmt_cor(None, cor_pl, f"{item['pl']:.1f}"))
            cols[9].markdown(fmt_cor(None, cor_pvp, f"{item['pvp']:.2f}"))
            cols[10].markdown(fmt_cor(None, cor_dy, f"{item['dy']*100:.1f}%"))

            if destaque: st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)

    # Exibição das Tabelas
    if oportunidades:
        st.subheader(f"🚀 Oportunidades ({len(oportunidades)})")
        desenhar_cabecalho()
        for item in oportunidades: desenhar_linha(item, destaque=True)

    st.subheader(f"📋 Lista Completa ({len(neutros)})")
    desenhar_cabecalho()
    for item in neutros: desenhar_linha(item, destaque=False)
    
    if st.button('🔄 Atualizar Varredura'): st.rerun()
