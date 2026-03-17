# banco.py
import sqlite3
import os

CAMINHO_BANCO = r"\\hc-arquivos.hc.ufpr.br\HC-GERAL\GERAD\DILIH\SESUP\Todos-SESUP\OPME\BD_Notas\notas.db"

def conectar():
    # Ativa FK e retorna conexão
    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def criar_tabelas():
    conn = conectar()
    cur = conn.cursor()

    # ---------------- Fornecedores ----------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fornecedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cnpj TEXT,
        contato_vendedor TEXT,
        telefone TEXT,
        email TEXT,
        rua TEXT,
        numero TEXT,
        complemento TEXT,
        bairro TEXT,
        municipio TEXT,
        estado TEXT,
        cep TEXT,
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fornec_nome ON fornecedores(nome);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_fornec_cnpj ON fornecedores(cnpj);")

    # ---------------- Itens de Pregão (Ata) ----------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS atas_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
        pregao TEXT NOT NULL,                  -- número/identificador do pregão (Ata)
        cod_aghu TEXT NOT NULL,               -- código do item
        nome_item TEXT NOT NULL,
        qtde_total REAL NOT NULL DEFAULT 0,   -- quantidade prevista na ata
        vl_unit REAL NOT NULL DEFAULT 0,
        vl_total REAL NOT NULL DEFAULT 0,     -- redundante para facilitar conferência
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(fornecedor_id, pregao, cod_aghu)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ata_fornecedor ON atas_itens(fornecedor_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ata_pregao ON atas_itens(pregao);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ata_cod ON atas_itens(cod_aghu);")

    # ---------------- Empenhos ----------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS empenhos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
        cod_aghu TEXT NOT NULL,               -- relaciona ao item do pregão
        nome_item TEXT NOT NULL,
        vl_unit REAL NOT NULL DEFAULT 0,
        vl_total REAL NOT NULL DEFAULT 0,
        numero_empenho TEXT,                  -- opcional: número textual do empenho
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_emp_fornecedor ON empenhos(fornecedor_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_emp_cod ON empenhos(cod_aghu);")

    # ---------------- Notas e Itens ----------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
        numero TEXT NOT NULL,          -- numero + série (ex: 1234-1)
        data_expedicao TEXT NOT NULL,
        vl_total REAL NOT NULL DEFAULT 0,
        codigo_sei TEXT,               -- processo
        data_envio_processo TEXT,
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(fornecedor_id, numero)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_fornec ON notas(fornecedor_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_numero ON notas(numero);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notas_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nota_id INTEGER NOT NULL REFERENCES notas(id) ON DELETE CASCADE,
        cod_aghu TEXT NOT NULL,
        data_uso TEXT,
        vl_unit REAL NOT NULL DEFAULT 0,
        qtde REAL NOT NULL DEFAULT 0,
        vl_total REAL NOT NULL DEFAULT 0,
        qtde_consumida REAL NOT NULL DEFAULT 0
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_itens_codh ON notas_itens(cod_aghu);")

    # ---------------- Orçamentos ----------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orcamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
        cod_aghu TEXT NOT NULL,
        nome_item TEXT NOT NULL,
        qtde REAL NOT NULL DEFAULT 0,
        vl_unit REAL NOT NULL DEFAULT 0,
        numero_empenho TEXT,
        observacao TEXT,
        mensagem_email TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    """)

    # --------- Views de Saldos ---------
    # Saldo de ATA (quantidade): qtde_total - Σ(qtde dos itens de notas para mesmo fornecedor+cod)
    cur.execute("""
    CREATE VIEW IF NOT EXISTS vw_saldo_ata AS
    SELECT
        a.id AS ata_id,
        a.fornecedor_id,
        a.pregao,
        a.cod_aghu,
        a.nome_item,
        a.qtde_total,
        IFNULL((
            SELECT SUM(ni.qtde)
            FROM notas_itens ni
            JOIN notas n ON n.id = ni.nota_id
            WHERE n.fornecedor_id = a.fornecedor_id
              AND ni.cod_aghu = a.cod_aghu
        ), 0) AS qtde_usada,
        (a.qtde_total - IFNULL((
            SELECT SUM(ni.qtde)
            FROM notas_itens ni
            JOIN notas n ON n.id = ni.nota_id
            WHERE n.fornecedor_id = a.fornecedor_id
              AND ni.cod_aghu = a.cod_aghu
        ), 0)) AS qtde_saldo
    FROM atas_itens a;
    """)

    # Saldo de Empenho (valor): vl_total - Σ(vl_total itens da nota vinculados ao empenho)
    # (usaremos o campo numero_empenho em notas_itens? Você pediu no orçamento; para empenho,
    # manteremos a vinculação por cod_aghu + fornecedor. Se quiser, adiciono referência direta de nota_itens->empenho.)
    cur.execute("""
    CREATE VIEW IF NOT EXISTS vw_saldo_empenho AS
    SELECT
        e.id AS empenho_id,
        e.fornecedor_id,
        e.cod_aghu,
        e.nome_item,
        e.vl_total,
        IFNULL((
            SELECT SUM(ni.vl_total)
            FROM notas_itens ni
            JOIN notas n ON n.id = ni.nota_id
            WHERE n.fornecedor_id = e.fornecedor_id
              AND ni.cod_aghu = e.cod_aghu
        ), 0) AS valor_consumido,
        (e.vl_total - IFNULL((
            SELECT SUM(ni.vl_total)
            FROM notas_itens ni
            JOIN notas n ON n.id = ni.nota_id
            WHERE n.fornecedor_id = e.fornecedor_id
              AND ni.cod_aghu = e.cod_aghu
        ), 0)) AS valor_saldo
    FROM empenhos e;
    """)

    conn.commit()
    conn.close()
