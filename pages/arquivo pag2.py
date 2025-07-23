import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(
    page_title="Cotação de Preços",
    page_icon="📊",
    layout="wide"
)

st.title("📊 2. Cotação de Preços")

# Garante que o dataframe original esteja disponível
if 'df_orcamento_original' not in st.session_state or st.session_state.df_orcamento_original is None:
    st.warning("Por favor, carregue primeiro a planilha de orçamento na página '1. Pedidos de Compra'.")
    st.stop()

# Usa o dataframe carregado na primeira página
df_orcamento = st.session_state.df_orcamento_original

# --- ETAPA 1: GERAR PLANILHA PARA COTAÇÃO ---
st.header("Etapa 1: Gerar Planilha para Cotação")
st.markdown("Use o botão abaixo para gerar uma planilha com todos os itens do seu orçamento. Envie esta planilha para seus fornecedores preencherem a coluna de valor.")

# Prepara o dataframe para cotação
df_para_cotacao = df_orcamento[['Cod', 'Descricao', 'Qtde']].copy()
df_para_cotacao['Valor Unitário (R$)'] = '' # Adiciona coluna vazia

# Função para converter o dataframe para Excel in-memory
@st.cache_data
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Cotacao')
    processed_data = output.getvalue()
    return processed_data

df_excel = to_excel(df_para_cotacao)

st.download_button(
    label="📥 Baixar Planilha de Cotação para Fornecedores",
    data=df_excel,
    file_name="planilha_cotacao.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.divider()


# --- ETAPA 2: IMPORTAR COTAÇÕES E COMPARAR ---
st.header("Etapa 2: Importar e Comparar Cotações")
st.markdown("Após receber as planilhas preenchidas, carregue todas elas aqui para ver o comparativo de preços.")

arquivos_cotados = st.file_uploader(
    "Carregue as planilhas respondidas pelos fornecedores (.xlsx)",
    type="xlsx",
    accept_multiple_files=True
)

if arquivos_cotados:
    df_comparativo = df_orcamento[['Cod', 'Descricao']].copy().set_index('Cod')

    for arquivo in arquivos_cotados:
        try:
            # Pega o nome do fornecedor a partir do nome do arquivo
            nome_fornecedor = arquivo.name.split('.')[0]
            
            df_cotado = pd.read_excel(arquivo)
            df_cotado = df_cotado[['Cod', 'Valor Unitário (R$)']]
            df_cotado.rename(columns={'Valor Unitário (R$)': f'Valor {nome_fornecedor} (R$)'}, inplace=True)
            df_cotado['Cod'] = df_cotado['Cod'].astype(str)
            
            df_comparativo = df_comparativo.join(df_cotado.set_index('Cod'))
        except Exception as e:
            st.error(f"Erro ao processar o arquivo '{arquivo.name}': {e}")
    
    df_comparativo.reset_index(inplace=True)
    colunas_valores = [col for col in df_comparativo.columns if 'Valor' in col]

    # Função para destacar o menor valor em cada linha
    def highlight_min(s):
        is_min = s == s.min()
        return ['background-color: #A6ECA9' if v else '' for v in is_min]

    st.subheader("Comparativo de Preços")
    st.dataframe(df_comparativo.style.apply(highlight_min, subset=colunas_valores, axis=1), use_container_width=True)


    # --- ETAPA 3: SELECIONAR VENCEDORES ---
    st.subheader("Etapa 3: Selecionar Fornecedor Vencedor por Item")
    st.markdown("Para cada item, selecione de qual fornecedor você irá comprar. A seleção será usada na página de Pedidos.")

    if 'cotacoes_vencedoras' not in st.session_state:
        st.session_state.cotacoes_vencedoras = {}

    opcoes_fornecedores = [col.replace('Valor ', '').replace(' (R$)', '') for col in colunas_valores]

    for index, row in df_comparativo.iterrows():
        st.write(f"**Item:** {row['Descricao']}")
        
        # Cria uma lista de opções válidas (onde o fornecedor deu um preço)
        opcoes_validas = []
        for i, col in enumerate(colunas_valores):
            if pd.notna(row[col]):
                opcoes_validas.append(opcoes_fornecedores[i])

        if opcoes_validas:
            fornecedor_selecionado = st.radio(
                "Escolha o fornecedor:",
                options=opcoes_validas,
                key=f"radio_{row['Cod']}",
                horizontal=True
            )
            # Salva a escolha no estado da sessão
            valor_selecionado = row[f"Valor {fornecedor_selecionado} (R$)"]
            st.session_state.cotacoes_vencedoras[row['Cod']] = {
                'fornecedor': fornecedor_selecionado,
                'valor': valor_selecionado
            }
        else:
            st.write("Nenhum preço cotado para este item.")
        st.divider()

    if st.button("Confirmar Seleções e Atualizar Pedidos"):
        st.success("Seleções de cotação salvas! Agora você pode voltar para a página '1. Pedidos de Compra' para gerar os pedidos com os valores e fornecedores atualizados.")