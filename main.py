import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from dotenv import load_dotenv
import os
import mysql.connector

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

st.set_page_config(
    page_title="Barbearia Carriel",
    page_icon="💈",
    layout="wide",
)

logo = Image.open("assets/images/logo.jpg")

DATABASE_URL = DATABASE_URL
engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

# Modelo ORM com SQLAlchemy
Base = declarative_base()

class Produto(Base):
    __tablename__ = 'produtos'
    id = Column(Integer, primary_key=True)
    nome = Column(String(50), nullable=False)
    preco_compra = Column(Float, nullable=False)
    preco_venda = Column(Float, nullable=False)
    quantidade = Column(Integer, nullable=False)

class Venda(Base):
    __tablename__ = 'vendas'
    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=False)
    quantidade_vendida = Column(Integer, nullable=False)
    desconto = Column(Float, default=0.0)
    forma_pagamento = Column(String(50), nullable=False)
    data_venda = Column(Date, default=datetime.today)
    produto = relationship("Produto")

class Saida(Base):
    __tablename__ = 'saidas'
    id = Column(Integer, primary_key=True)
    descricao = Column(String(100), nullable=False)
    valor = Column(Float, nullable=False)
    data_saida = Column(Date, default=datetime.today)

# Cria as tabelas no banco de dados
Base.metadata.create_all(engine)

# Funções CRUD
def adicionar_produto(nome, preco_compra, preco_venda, quantidade):
    produto = Produto(nome=nome, preco_compra=preco_compra, preco_venda=preco_venda, quantidade=quantidade)
    session.add(produto)
    session.commit()

def listar_produtos(nome_filter=None):
    if nome_filter:
        return session.query(Produto).filter(Produto.nome.ilike(f"%{nome_filter}%")).all()
    return session.query(Produto).all()

def alterar_produto(produto_id, nome, preco_compra, preco_venda, quantidade):
    produto = session.query(Produto).get(produto_id)
    if produto:
        produto.nome = nome
        produto.preco_compra = preco_compra
        produto.preco_venda = preco_venda
        produto.quantidade = quantidade
        session.commit()
        st.success("Produto alterado com sucesso!")

def deletar_produto(produto_id):
    # Consultar o produto a ser excluído
    produto = session.query(Produto).get(produto_id)
    
    if produto:
        # Verificar se o produto tem vendas associadas
        vendas_associadas = session.query(Venda).filter_by(produto_id=produto_id).all()
        
        if vendas_associadas:
            st.warning("Não é possível deletar o produto pois ele possui vendas associadas.")
        else:
            try:               
                session.delete(produto)
                session.commit()  
                st.success("Produto deletado com sucesso!")  
            except Exception as e:
                session.rollback()
                st.error(f"Erro ao tentar deletar o produto: {e}")
    else:
        st.error("Produto não encontrado.")

def adicionar_venda(produto_id, quantidade_vendida, desconto, forma_pagamento):
    produto = session.query(Produto).get(produto_id)
    if produto and produto.quantidade >= quantidade_vendida:
        venda = Venda(produto_id=produto_id, quantidade_vendida=quantidade_vendida, desconto=desconto, forma_pagamento=forma_pagamento)
        produto.quantidade -= quantidade_vendida
        session.add(venda)
        session.commit()

def adicionar_saida(descricao, valor):
    saida = Saida(descricao=descricao, valor=valor)
    session.add(saida)
    session.commit()

def restaurar_backup(session, uploaded_file):
    try:
        # Parse DATABASE_URL
        from urllib.parse import urlparse
        import subprocess
        
        url = urlparse(os.getenv("DATABASE_URL"))
        
        # Save uploaded file temporarily
        with open('restore_backup.sql', 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        # Construct mysql command for restoration
        mysql_command = [
            'mysql',
            f'--host={url.hostname}',
            f'--user={url.username}',
            f'--password={url.password}',
            f'--port={url.port or 3306}',
            url.path.lstrip('/'),
            f'--execute=source restore_backup.sql'
        ]
        
        # Execute restoration
        result = subprocess.run(mysql_command, capture_output=True, text=True)
        
        if result.returncode == 0:
            st.success("Backup restaurado com sucesso!")
        else:
            st.error(f"Erro na restauração: {result.stderr}")
    
    except Exception as e:
        st.error(f"Erro ao restaurar backup: {e}")


def fazer_backup_mysql(session):
    try:
        # Parse DATABASE_URL for connection details
        from urllib.parse import urlparse
        
        # Parse the database URL
        url = urlparse(os.getenv("DATABASE_URL"))
        
        # Connection configuration
        db_config = {
            'host': url.hostname,
            'user': url.username,
            'password': url.password,
            'database': url.path.lstrip('/'),
            'port': url.port or 3306
        }
        
        # Timestamp for backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.sql"
        
        # Use mysqldump for more reliable backup
        import subprocess
        
        # Construct mysqldump command
        mysqldump_command = [
            'mysqldump',
            f'-h{db_config["host"]}',
            f'-u{db_config["user"]}',
            f'-p{db_config["password"]}',
            f'-P{db_config["port"]}',
            db_config['database']
        ]
        
        # Execute mysqldump
        with open(backup_filename, 'w') as backup_file:
            subprocess.run(mysqldump_command, stdout=backup_file, check=True)
        
        st.success(f"Backup realizado com sucesso: {backup_filename}")
        return backup_filename
    
    except Exception as e:
        st.error(f"Erro ao realizar backup: {e}")
        return None


# Interface do Usuário com Streamlit
st.title("✂️ Sistema de Vendas - Barbearia Carriel 💈")
st.write("----------------------------------------------------------")
# Aba de Cadastro de Produtos
st.sidebar.header("Opções")
abas = ["Vendas 💰", "Produtos 🛍️", "Saídas 💸", "Relatórios 📊", "Backup 💾"]
aba_selecionada = st.sidebar.radio("Selecionar aba", abas)

if aba_selecionada == "Produtos 🛍️":
    st.sidebar.image(logo, use_column_width=True)
    st.header("Cadastro de Produtos")

    # Adicionar um novo produto
    st.subheader("Adicionar Novo Produto ✍️")
    nome = st.text_input("Nome do Novo Produto")    
    preco_compra = st.number_input("Preço de Compra do Novo Produto", min_value=0.0, format="%.2f")
    preco_venda = st.number_input("Preço de Venda do Novo Produto", min_value=0.0, format="%.2f")
    quantidade = st.number_input("Quantidade do Novo Produto", min_value=0)
    if st.button(" ➕ "):
        adicionar_produto(nome, preco_compra, preco_venda, quantidade)
        st.success("✅ Produto adicionado com sucesso!")
        st.rerun()
        #sleep(1)
        #press('f5')
    st.write("----------------------------------------------------------------------")
    st.subheader("Pesquisa 🔎")
    pesquisa_nome = st.text_input("Pesquisar Produtos pelo Nome")
    # Mostrar/ocultar tabela de produtos cadastrados
    if 'mostrar_produtos' not in st.session_state:
        st.session_state['mostrar_produtos'] = False

    if st.button("Mostrar Produtos" if not st.session_state['mostrar_produtos'] else "Ocultar Produtos"):
        st.session_state['mostrar_produtos'] = not st.session_state['mostrar_produtos']

    # Caixa de pesquisa para filtrar produtos por nome

    if st.session_state['mostrar_produtos']:
        st.subheader("Produtos Cadastrados")
        produtos = listar_produtos(nome_filter=pesquisa_nome)
        if produtos:
            for produto in produtos:
                with st.expander(f"ID: {produto.id} | Nome: {produto.nome}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_nome = st.text_input("Nome do Produto", value=produto.nome, key=f"nome_{produto.id}")
                        new_preco_compra = st.number_input("Preço de Compra", min_value=0.0, value=produto.preco_compra, key=f"compra_{produto.id}")
                    
                    with col2:
                        new_preco_venda = st.number_input("Preço de Venda", min_value=0.0, value=produto.preco_venda, key=f"venda_{produto.id}")
                        new_quantidade = st.number_input("Quantidade", min_value=0, value=produto.quantidade, key=f"quantidade_{produto.id}")
                    
                    col_save, col_delete = st.columns(2)
                    with col_save:
                        if st.button(f"Salvar Alterações", key=f"salvar_{produto.id}"):
                            alterar_produto(produto.id, new_nome, new_preco_compra, new_preco_venda, new_quantidade)
                    
                    with col_delete:
                        if st.button(f"Excluir Produto", key=f"excluir_{produto.id}"):
                            deletar_produto(produto.id)

# Aba de Vendas
elif aba_selecionada == "Vendas 💰":
    st.sidebar.image(logo, use_column_width=True)
    st.header("Lançar Vendas 💰")
    
    # Carregar os produtos como uma lista de IDs e nomes para exibição
    produtos = listar_produtos()
    produtos_opcoes = [(p.id, p.nome) for p in produtos]
    
    # Selecionar um produto por ID
    produto_id = st.selectbox("Selecione o Produto", produtos_opcoes, format_func=lambda x: x[1])
    
    # Reconsultar o produto pelo ID selecionado para garantir que esteja anexado à sessão
    produto_selecionado = session.query(Produto).get(produto_id[0])
    
    # Definir os campos para a venda
    quantidade_vendida = st.number_input("Quantidade Vendida", min_value=1, max_value=produto_selecionado.quantidade)
    desconto = st.number_input("Desconto (R$)", min_value=0.0, format="%.2f")
    forma_pagamento = st.radio("Forma de Pagamento", ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "Pix"])

    # Botão para registrar a venda
    if st.button("Lançar"):
        adicionar_venda(produto_selecionado.id, quantidade_vendida, desconto, forma_pagamento)
        st.success("Venda registrada com sucesso!")
        st.rerun()
        #sleep(0.9)
        #press('f5')

# Aba de Relatórios
elif aba_selecionada == "Relatórios 📊":
    st.sidebar.image(logo, use_column_width=True)
    st.header("Relatório de Vendas por Tipo de Pagamento")
    data_relatorio = st.date_input("Selecione a data do relatório", value=datetime.today().date())
    # Consulta as vendas e agrupa por forma de pagamento
    vendas = session.query(Venda).filter(Venda.data_venda == data_relatorio).all()

    produtos_vendidos = {}
    for venda in vendas:
        produto_nome = venda.produto.nome
        quantidade_vendida = venda.quantidade_vendida
        produtos_vendidos[produto_nome] = produtos_vendidos.get(produto_nome, 0) + quantidade_vendida

    st.subheader("Itens Vendidos")
    for produto, quantidade in produtos_vendidos.items():
        st.write(f"{produto}: {quantidade} unidades")

    if vendas:
        # Dicionário para armazenar o total de vendas por tipo de pagamento
        vendas_por_pagamento = {}
        for venda in vendas:
            forma_pagamento = venda.forma_pagamento
            total_venda = venda.produto.preco_venda * venda.quantidade_vendida - venda.desconto
            vendas_por_pagamento[forma_pagamento] = vendas_por_pagamento.get(forma_pagamento, 0) + total_venda

        # Dados para o gráfico de pizza
        labels = list(vendas_por_pagamento.keys())
        valores = list(vendas_por_pagamento.values())

        # Gráfico de Pizza
        st.subheader("Distribuição de Vendas por Tipo de Pagamento")
        plt.figure(figsize=(8, 8))
        plt.pie(valores, labels=labels, autopct='%1.1f%%', startangle=140)
        plt.title("Percentual de Vendas por Tipo de Pagamento")
        st.pyplot(plt)
        
        # Exibir soma total em cada forma de pagamento
        st.subheader("Total de Vendas por Forma de Pagamento")
        for forma_pagamento, valor_total in vendas_por_pagamento.items():
            st.write(f"{forma_pagamento}: R$ {valor_total:.2f}")
    else:
        st.warning("Nenhuma venda registrada.")

    # Consultar saídas do dia
    saidas = session.query(Saida).filter(Saida.data_saida == datetime.today().date()).all()
    total_saidas = sum(saida.valor for saida in saidas)

    # Exibir total de saídas com descrição e valor
    st.subheader("Total de Saídas no Dia")
    if saidas:
        for saida in saidas:
            st.write(f"{saida.descricao}: R$ {saida.valor:.2f}")
    st.write(f"Total de Saídas: R$ {total_saidas:.2f}")

    # Calcular o saldo final no caixa para cada forma de pagamento
    st.subheader("FECHAMENTO DE CAIXA (TOTAIS)")
    saldo_por_pagamento = vendas_por_pagamento.copy()
    
    # Subtrair o total de saídas do saldo em "Dinheiro"
    saldo_por_pagamento["Dinheiro"] = saldo_por_pagamento.get("Dinheiro", 0) - total_saidas

    # Exibir saldo final em cada forma de pagamento
    for forma_pagamento, saldo in saldo_por_pagamento.items():
        st.write(f"{forma_pagamento} : R$ {saldo:.2f}")

    st.write("----------------------------------------------------------------------------------------")
    st.subheader("Gerar Relatório mensal de vendas.")

    mes_selecionado = st.selectbox("Selecione o mês", range(1, 13), index=datetime.today().month - 1)
    ano_selecionado = st.number_input("Selecione o ano", min_value=2000, max_value=3000, value=datetime.today().year, step=1)
    
    # Botão para gerar relatório mensal
    if st.button("Gerar Relatório Mensal"):
        # Calcular a data de início e fim do mês selecionado
        start_date = datetime(ano_selecionado, mes_selecionado, 1)
        end_date = start_date + timedelta(days=32)
        end_date = end_date.replace(day=1) - timedelta(days=1)
        
        # Consultar as vendas do mês selecionado
        vendas_mes = session.query(Venda).filter(Venda.data_venda.between(start_date, end_date)).all()
        
        # Consultar todos os produtos
        produtos = session.query(Produto).all()
        
        # Cálculo das métricas por produto
        dados_produtos = []
        total_vendas = 0
        total_saidas = 0
        total_custo_produtos = 0
        for produto in produtos:
            vendas_produto = [venda for venda in vendas_mes if venda.produto_id == produto.id]
            quantidade_vendida = sum(venda.quantidade_vendida for venda in vendas_produto)
            valor_total_liquido = sum((venda.produto.preco_venda * venda.quantidade_vendida) - venda.desconto for venda in vendas_produto)
            valor_total_bruto = sum((venda.produto.preco_venda * venda.quantidade_vendida) - (venda.produto.preco_compra * venda.quantidade_vendida) for venda in vendas_produto)
            dados_produtos.append({
                "Produto": produto.nome,
                "Quantidade Vendida": quantidade_vendida,
                "Total Líquido": valor_total_liquido,
                "Total Bruto": valor_total_bruto
            })
            total_vendas += valor_total_liquido
            total_custo_produtos += valor_total_bruto
        
        # Consultar saídas do mês selecionado
        saidas_mes = session.query(Saida).filter(Saida.data_saida.between(start_date, end_date)).all()
        total_saidas = sum(saida.valor for saida in saidas_mes)
        
        # Criar o arquivo XLSX
        df_produtos = pd.DataFrame(dados_produtos)
        df_totais = pd.DataFrame({
            "Total de Vendas": [total_vendas],
            "Total de Saídas": [total_saidas],
            "Total Geral de Caixa (vendas - saidas)": [total_vendas - total_saidas],
            "Lucro": [total_vendas - total_custo_produtos - total_saidas]
        })
        
        with pd.ExcelWriter(f"relatorio_mensal_{mes_selecionado:02d}_{ano_selecionado}.xlsx") as writer:
            df_produtos.to_excel(writer, sheet_name="Produtos Vendidos", index=False)
            df_totais.to_excel(writer, sheet_name="Totais", index=False)
        
        st.success("Relatório mensal gerado com sucesso!")
        st.download_button(
            label="Baixar Relatório",
            data=open(f"relatorio_mensal_{mes_selecionado:02d}_{ano_selecionado}.xlsx", "rb").read(),
            file_name=f"relatorio_mensal_{mes_selecionado:02d}_{ano_selecionado}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Aba de Saídas
elif aba_selecionada == "Saídas 💸":
    st.sidebar.image(logo, use_column_width=True)
    st.header("Registrar Saídas")
    descricao = st.text_input("Descrição")
    valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
    if st.button("Registrar Saída"):
        adicionar_saida(descricao, valor)
        st.success("Saída registrada com sucesso!")

elif aba_selecionada == "Backup 💾":
    st.sidebar.image(logo, use_column_width=True)
    st.header("Backup e Restauração")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Realizar Backup")
        if st.button("Gerar Backup do Sistema"):
            backup_file = fazer_backup_mysql(session)
            if backup_file:
                st.download_button(
                    label="Baixar Backup",
                    data=open(backup_file, 'rb').read(),
                    file_name=backup_file,
                    mime='application/sql'
                )
    
    with col2:
        st.subheader("Restaurar Backup")
        arquivo_backup = st.file_uploader("Selecione arquivo de backup SQL", type=['sql'])
        
        if arquivo_backup is not None:
            if st.button("Restaurar Backup"):
                restaurar_backup(session, arquivo_backup)


