from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from config import Config
import json

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# ========== MODELOS ==========

class Cliente(db.Model):
    __tablename__ = 'clientes'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    telefone = db.Column(db.String(20))
    cpf_cnpj = db.Column(db.String(20), unique=True)
    endereco = db.Column(db.String(200))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(10))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Ativo')
    
    vendas = db.relationship('Venda', backref='cliente', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'telefone': self.telefone,
            'cpf_cnpj': self.cpf_cnpj,
            'endereco': self.endereco,
            'cidade': self.cidade,
            'estado': self.estado,
            'cep': self.cep,
            'data_cadastro': self.data_cadastro.strftime('%d/%m/%Y'),
            'status': self.status
        }

class Produto(db.Model):
    __tablename__ = 'produtos'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    categoria = db.Column(db.String(50))
    preco_compra = db.Column(db.Float, default=0.0)
    preco_venda = db.Column(db.Float, default=0.0)
    quantidade = db.Column(db.Integer, default=0)
    estoque_minimo = db.Column(db.Integer, default=5)
    unidade = db.Column(db.String(10), default='un')
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'codigo': self.codigo,
            'nome': self.nome,
            'descricao': self.descricao,
            'categoria': self.categoria,
            'preco_compra': self.preco_compra,
            'preco_venda': self.preco_venda,
            'quantidade': self.quantidade,
            'estoque_minimo': self.estoque_minimo,
            'unidade': self.unidade,
            'status_estoque': 'Baixo' if self.quantidade <= self.estoque_minimo else 'Normal'
        }

class Venda(db.Model):
    __tablename__ = 'vendas'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    data_venda = db.Column(db.DateTime, default=datetime.utcnow)
    valor_total = db.Column(db.Float, default=0.0)
    desconto = db.Column(db.Float, default=0.0)
    forma_pagamento = db.Column(db.String(30))
    status = db.Column(db.String(20), default='Concluída')
    observacao = db.Column(db.Text)
    
    itens = db.relationship('ItemVenda', backref='venda', lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'cliente_nome': self.cliente.nome,
            'data_venda': self.data_venda.strftime('%d/%m/%Y %H:%M'),
            'valor_total': self.valor_total,
            'desconto': self.desconto,
            'forma_pagamento': self.forma_pagamento,
            'status': self.status,
            'observacao': self.observacao,
            'itens': [item.to_dict() for item in self.itens]
        }

class ItemVenda(db.Model):
    __tablename__ = 'itens_venda'
    
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    
    produto = db.relationship('Produto')
    
    def to_dict(self):
        return {
            'id': self.id,
            'produto_id': self.produto_id,
            'produto_nome': self.produto.nome,
            'quantidade': self.quantidade,
            'preco_unitario': self.preco_unitario,
            'subtotal': self.subtotal
        }

class Conta(db.Model):
    __tablename__ = 'contas'
    
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'Receber' ou 'Pagar'
    categoria = db.Column(db.String(50))
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date)
    status = db.Column(db.String(20), default='Pendente')
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'))
    observacao = db.Column(db.Text)
    
    venda = db.relationship('Venda', backref='contas')
    
    def to_dict(self):
        return {
            'id': self.id,
            'descricao': self.descricao,
            'tipo': self.tipo,
            'categoria': self.categoria,
            'valor': self.valor,
            'data_vencimento': self.data_vencimento.strftime('%d/%m/%Y'),
            'data_pagamento': self.data_pagamento.strftime('%d/%m/%Y') if self.data_pagamento else None,
            'status': self.status,
            'observacao': self.observacao
        }

# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    # Dashboard com resumo
    total_clientes = Cliente.query.count()
    total_produtos = Produto.query.count()
    
    vendas_hoje = Venda.query.filter(
        db.func.date(Venda.data_venda) == datetime.utcnow().date()
    ).count()
    
    valor_vendas = db.session.query(db.func.sum(Venda.valor_total)).filter(
        db.func.date(Venda.data_venda) == datetime.utcnow().date()
    ).scalar() or 0
    
    produtos_baixo = Produto.query.filter(
        Produto.quantidade <= Produto.estoque_minimo
    ).count()
    
    contas_pendentes = Conta.query.filter_by(status='Pendente').count()
    
    return render_template('index.html',
                         total_clientes=total_clientes,
                         total_produtos=total_produtos,
                         vendas_hoje=vendas_hoje,
                         valor_vendas=valor_vendas,
                         produtos_baixo=produtos_baixo,
                         contas_pendentes=contas_pendentes)

@app.route('/clientes')
def clientes():
    return render_template('clientes.html')

@app.route('/vendas')
def vendas():
    return render_template('vendas.html')

@app.route('/estoque')
def estoque():
    return render_template('estoque.html')

@app.route('/financeiro')
def financeiro():
    return render_template('financeiro.html')

# ========== API REST ==========

# ----- CLIENTES -----
@app.route('/api/clientes', methods=['GET', 'POST'])
def api_clientes():
    if request.method == 'GET':
        clientes = Cliente.query.all()
        return jsonify([cliente.to_dict() for cliente in clientes])
    
    elif request.method == 'POST':
        data = request.json
        cliente = Cliente(
            nome=data['nome'],
            email=data.get('email'),
            telefone=data.get('telefone'),
            cpf_cnpj=data.get('cpf_cnpj'),
            endereco=data.get('endereco'),
            cidade=data.get('cidade'),
            estado=data.get('estado'),
            cep=data.get('cep')
        )
        db.session.add(cliente)
        db.session.commit()
        return jsonify(cliente.to_dict()), 201

@app.route('/api/clientes/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    
    if request.method == 'GET':
        return jsonify(cliente.to_dict())
    
    elif request.method == 'PUT':
        data = request.json
        cliente.nome = data.get('nome', cliente.nome)
        cliente.email = data.get('email', cliente.email)
        cliente.telefone = data.get('telefone', cliente.telefone)
        cliente.cpf_cnpj = data.get('cpf_cnpj', cliente.cpf_cnpj)
        cliente.endereco = data.get('endereco', cliente.endereco)
        cliente.cidade = data.get('cidade', cliente.cidade)
        cliente.estado = data.get('estado', cliente.estado)
        cliente.cep = data.get('cep', cliente.cep)
        cliente.status = data.get('status', cliente.status)
        db.session.commit()
        return jsonify(cliente.to_dict())
    
    elif request.method == 'DELETE':
        db.session.delete(cliente)
        db.session.commit()
        return '', 204

# ----- PRODUTOS -----
@app.route('/api/produtos', methods=['GET', 'POST'])
def api_produtos():
    if request.method == 'GET':
        produtos = Produto.query.all()
        return jsonify([produto.to_dict() for produto in produtos])
    
    elif request.method == 'POST':
        data = request.json
        produto = Produto(
            codigo=data['codigo'],
            nome=data['nome'],
            descricao=data.get('descricao'),
            categoria=data.get('categoria'),
            preco_compra=data.get('preco_compra', 0),
            preco_venda=data.get('preco_venda', 0),
            quantidade=data.get('quantidade', 0),
            estoque_minimo=data.get('estoque_minimo', 5),
            unidade=data.get('unidade', 'un')
        )
        db.session.add(produto)
        db.session.commit()
        return jsonify(produto.to_dict()), 201

@app.route('/api/produtos/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_produto(id):
    produto = Produto.query.get_or_404(id)
    
    if request.method == 'GET':
        return jsonify(produto.to_dict())
    
    elif request.method == 'PUT':
        data = request.json
        produto.codigo = data.get('codigo', produto.codigo)
        produto.nome = data.get('nome', produto.nome)
        produto.descricao = data.get('descricao', produto.descricao)
        produto.categoria = data.get('categoria', produto.categoria)
        produto.preco_compra = data.get('preco_compra', produto.preco_compra)
        produto.preco_venda = data.get('preco_venda', produto.preco_venda)
        produto.quantidade = data.get('quantidade', produto.quantidade)
        produto.estoque_minimo = data.get('estoque_minimo', produto.estoque_minimo)
        produto.unidade = data.get('unidade', produto.unidade)
        db.session.commit()
        return jsonify(produto.to_dict())
    
    elif request.method == 'DELETE':
        db.session.delete(produto)
        db.session.commit()
        return '', 204

# ----- VENDAS -----
@app.route('/api/vendas', methods=['GET', 'POST'])
def api_vendas():
    if request.method == 'GET':
        vendas = Venda.query.order_by(Venda.data_venda.desc()).all()
        return jsonify([venda.to_dict() for venda in vendas])
    
    elif request.method == 'POST':
        data = request.json
        
        # Criar venda
        venda = Venda(
            cliente_id=data['cliente_id'],
            valor_total=data['valor_total'],
            desconto=data.get('desconto', 0),
            forma_pagamento=data.get('forma_pagamento'),
            observacao=data.get('observacao')
        )
        db.session.add(venda)
        db.session.flush()
        
        # Adicionar itens
        for item in data['itens']:
            item_venda = ItemVenda(
                venda_id=venda.id,
                produto_id=item['produto_id'],
                quantidade=item['quantidade'],
                preco_unitario=item['preco_unitario'],
                subtotal=item['quantidade'] * item['preco_unitario']
            )
            db.session.add(item_venda)
            
            # Atualizar estoque
            produto = Produto.query.get(item['produto_id'])
            produto.quantidade -= item['quantidade']
        
        # Criar conta a receber se for a prazo
        if data.get('forma_pagamento') == 'A Prazo':
            conta = Conta(
                descricao=f'Venda #{venda.id}',
                tipo='Receber',
                valor=venda.valor_total,
                data_vencimento=datetime.utcnow().date(),
                venda_id=venda.id
            )
            db.session.add(conta)
        
        db.session.commit()
        return jsonify(venda.to_dict()), 201

# ----- CONTAS -----
@app.route('/api/contas', methods=['GET', 'POST'])
def api_contas():
    if request.method == 'GET':
        contas = Conta.query.all()
        return jsonify([conta.to_dict() for conta in contas])
    
    elif request.method == 'POST':
        data = request.json
        conta = Conta(
            descricao=data['descricao'],
            tipo=data['tipo'],
            categoria=data.get('categoria'),
            valor=data['valor'],
            data_vencimento=datetime.strptime(data['data_vencimento'], '%Y-%m-%d').date(),
            observacao=data.get('observacao')
        )
        db.session.add(conta)
        db.session.commit()
        return jsonify(conta.to_dict()), 201

@app.route('/api/contas/<int:id>/pagar', methods=['PUT'])
def api_pagar_conta(id):
    conta = Conta.query.get_or_404(id)
    conta.status = 'Pago'
    conta.data_pagamento = datetime.utcnow().date()
    db.session.commit()
    return jsonify(conta.to_dict())

# ========== INICIALIZAÇÃO ==========

def init_db():
    with app.app_context():
        db.create_all()
        
        # Inserir dados de exemplo se o banco estiver vazio
        if Cliente.query.count() == 0:
            # Clientes de exemplo
            clientes_exemplo = [
                Cliente(nome='João Silva', email='joao@email.com', telefone='(11) 99999-9999'),
                Cliente(nome='Maria Santos', email='maria@email.com', telefone='(21) 88888-8888'),
                Cliente(nome='Pedro Oliveira', email='pedro@email.com', telefone='(31) 77777-7777')
            ]
            db.session.add_all(clientes_exemplo)
            
            # Produtos de exemplo
            produtos_exemplo = [
                Produto(codigo='PROD001', nome='Notebook', preco_venda=3500.00, quantidade=10),
                Produto(codigo='PROD002', nome='Mouse', preco_venda=50.00, quantidade=50),
                Produto(codigo='PROD003', nome='Teclado', preco_venda=100.00, quantidade=30)
            ]
            db.session.add_all(produtos_exemplo)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)