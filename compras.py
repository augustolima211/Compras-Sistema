import streamlit as st
import pandas as pd

# --- Configuração da Página ---
st.set_page_config(
    page_title="Pedidos de Compra",
    page_icon="🛒",
    layout="wide"
)

# --- Inicialização do Estado da Sessão (Session State) ---
# Garante que os dados persistam entre as páginas
if 'pedido_final' not in st.session_state:
    st.session_state.pedido_final = pd.DataFrame(columns=[
        'Código', 'Descrição', 'Quantidade', 'Fornecedor', 
        'Previsão de Entrega', 'Valor Unitário (R$)', 'Valor Total (R$)'
    ])
if 'cotacoes_vencedoras' not in st.session_state:
    st.session_state.cotacoes_vencedoras = {}
if 'df_orcamento_original' not in st.session_state:
    st.session_state.df_orcamento_original = None

# --- Funções Auxiliares ---
def adicionar_item_pedido(codigo, descricao, quantidade, fornecedor, previsao, valor_unitario):
    st.session_state.pedido_final = st.session_state.pedido_final[
        st.session_state.pedido_final['Código'] != codigo
    ]
    valor_total = quantidade * valor_unitario
    novo_item = pd.DataFrame({
        'Código': [codigo], 'Descrição': [descricao], 'Quantidade': [quantidade],
        'Fornecedor': [fornecedor], 'Previsão de Entrega': [previsao],
        'Valor Unitário (R$)': [f'{valor_unitario:,.2f}'], 'Valor Total (R$)': [f'{valor_total:,.2f}']
    })
    st.session_state.pedido_final = pd.concat([st.session_state.pedido_final, novo_item], ignore_index=True)

# --- Título e Descrição da Aplicação ---
st.title("🛒 1. Pedidos de Compra")
st.markdown("Gere seus pedidos de compra a partir dos itens em falta ou das cotações selecionadas.")

# --- Upload da Planilha ---
st.header("Carregue sua Planilha de Orçamento")
uploaded_file = st.file_uploader("Escolha um arquivo Excel (.xlsx)", type="xlsx", key="uploader_pedidos")

if uploaded_file:
    try:
        df_orcamento = pd.read_excel(uploaded_file, skiprows=1, header=None)
        df_orcamento.columns = ['ID_Linha', 'Cod', 'Qtde', 'Estoque', 'Descricao', 'Marca', 'Unitario', 'Total']
        df_orcamento.dropna(how='all', subset=['Cod', 'Descricao'], inplace=True)
        st.session_state.df_orcamento_original = df_orcamento # Salva para uso na outra página
        
        st.success("Planilha carregada e processada com sucesso!")

        st.header("Selecione os Itens para o Pedido")
        
        df_orcamento['Cod'] = df_orcamento['Cod'].astype(str)
        itens_em_falta_df = df_orcamento[df_orcamento['Estoque'].isnull()].copy()

        if itens_em_falta_df.empty:
            st.warning("✅ Nenhum item com a coluna 'Estoque' vazia foi encontrado.")
        else:
            st.info("Os itens abaixo foram identificados como 'em falta'.")
            itens_em_falta_df['display'] = itens_em_falta_df['Cod'] + " - " + itens_em_falta_df['Descricao']
            opcoes_selecao = itens_em_falta_df['display'].tolist()
            
            item_selecionado_display = st.selectbox("Escolha um item para adicionar ao pedido:", options=opcoes_selecao)

            if item_selecionado_display:
                codigo_selecionado = item_selecionado_display.split(" - ")[0]
                dados_item = itens_em_falta_df[itens_em_falta_df['Cod'] == codigo_selecionado].iloc[0]

                st.subheader(f"📝 Adicionar Informações para: **{dados_item['Descricao']}**")

                # --- LÓGICA DE INTEGRAÇÃO COM COTAÇÃO ---
                fornecedor_padrao = ""
                unitario_str = str(dados_item['Unitario']).replace(',', '.')
                valor_padrao = float(unitario_str)

                if codigo_selecionado in st.session_state.cotacoes_vencedoras:
                    dados_vencedor = st.session_state.cotacoes_vencedoras[codigo_selecionado]
                    fornecedor_padrao = dados_vencedor['fornecedor']
                    valor_padrao = dados_vencedor['valor']
                    st.success(f"🏆 Cotação vencedora encontrada: **{fornecedor_padrao}** por **R$ {valor_padrao:,.2f}**")
                
                fornecedor = st.text_input("Fornecedor", value=fornecedor_padrao, key=f"forn_{codigo_selecionado}")
                previsao_entrega = st.date_input("Previsão de Entrega", key=f"data_{codigo_selecionado}")
                
                col1, col2 = st.columns(2)
                with col1:
                    qtde_str = str(dados_item['Qtde']).replace(',', '.')
                    valor_qtde = int(float(qtde_str))
                    quantidade = st.number_input("Quantidade", min_value=1, value=valor_qtde, step=1, key=f"qtd_{codigo_selecionado}")
                with col2:
                    valor_unitario = st.number_input("Valor Unitário (R$)", min_value=0.0, value=valor_padrao, format="%.2f", key=f"val_{codigo_selecionado}")

                if st.button(f"Adicionar '{dados_item['Descricao']}' ao Pedido"):
                    if not fornecedor:
                        st.error("O campo 'Fornecedor' é obrigatório.")
                    else:
                        adicionar_item_pedido(codigo=codigo_selecionado, descricao=dados_item['Descricao'], quantidade=quantidade, fornecedor=fornecedor, previsao=previsao_entrega, valor_unitario=valor_unitario)
                        st.success(f"**{dados_item['Descricao']}** foi adicionado/atualizado no pedido!")
    
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

# --- Exibição do Pedido Final ---
if not st.session_state.pedido_final.empty:
    st.header("📦 Pedido de Compra Final")
    df_final_display = st.session_state.pedido_final.sort_values(by='Código').reset_index(drop=True)
    st.dataframe(df_final_display, use_container_width=True)
    
    @st.cache_data
    def convert_df_to_csv(df):
        return df.to_csv(index=False, sep=';').encode('latin1')
    csv = convert_df_to_csv(df_final_display)
    st.download_button(label="✅ Baixar Pedido como CSV (para Excel)", data=csv, file_name='pedido_de_compra.csv', mime='text/csv')