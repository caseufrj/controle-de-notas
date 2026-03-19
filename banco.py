# banco.py
import os
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from contextlib import closing

# =========================
#  Caminho do banco (UNC)
# =========================
CAMINHO_BANCO = r"\\hc-arquivos.hc.ufpr.br\HC-GERAL\GERAD\DILIH\SESUP\Todos-SESUP\OPME\BD_Notas\notas.db"

# -------------------------
#  Conexão única (FK ON)
# -------------------------
def conectar() -> sqlite3.Connection:
    """Abre conexão com row_factory por nome e foreign_keys habilitado."""
    try:
        base_dir = os.path.dirname(CAMINHO_BANCO)
        if base_dir and not os.path.exists(base_dir) and not base_dir.startswith("\\\\"):
            os.makedirs(base_dir, exist_ok=True)
    except Exception:
        pass  # em UNC, diretório já existe

    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# -------------------------
#  Helpers de schema
# -------------------------
def _tabela_info(cur: sqlite3.Cursor, nome_tabela: str) -> List[sqlite3.Row]:
    cur.execute(f"PRAGMA table_info({nome_tabela})")
    return cur.fetchall()

def _coluna_existe(cur: sqlite3.Cursor, nome_tabela: str, coluna: str) -> bool:
    info = _tabela_info(cur, nome_tabela)
    return any(r["name"] == coluna for r in info)

def _view_existe(cur: sqlite3.Cursor, nome_view: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='view' AND name=?", (nome_view,))
    return cur.fetchone() is not None

# -------------------------
#  Criação/Migração schema
# -------------------------
def criar_tabelas() -> None:
    conn = conectar()
    cur = conn.cursor()

    # -------- Fornecedores --------
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

    # -------- Itens de Pregão (Ata) --------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS atas_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
        pregao TEXT NOT NULL,
        cod_aghu TEXT NOT NULL,
        nome_item TEXT NOT NULL,
        qtde_total REAL NOT NULL DEFAULT 0,
        vl_unit REAL NOT NULL DEFAULT 0,
        vl_total REAL NOT NULL DEFAULT 0,
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(fornecedor_id, pregao, cod_aghu)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ata_fornecedor ON atas_itens(fornecedor_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ata_pregao ON atas_itens(pregao);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ata_cod ON atas_itens(cod_aghu);")

    # ------------ Cabeçalho de ATAS -------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS atas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
        numero TEXT NOT NULL,
        vigencia_ini TEXT,          -- YYYY-MM-DD
        vigencia_fim TEXT,          -- YYYY-MM-DD
        status TEXT NOT NULL DEFAULT 'Em vigência'
               CHECK (status IN ('Em vigência','Encerrada','Renovada')),
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(fornecedor_id, numero)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_atas_fornec ON atas(fornecedor_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_atas_num ON atas(numero);")
    
    # Itens de ata passam a aceitar 'ata_id' (FK)
    if not _coluna_existe(cur, "atas_itens", "ata_id"):
        cur.execute("ALTER TABLE atas_itens ADD COLUMN ata_id INTEGER REFERENCES atas(id) ON DELETE CASCADE;")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_atas_itens_ata ON atas_itens(ata_id);")
    
    # Saldo agregado por ATA (valor total dos itens - consumo em notas)
    # Consumo: soma de ni.vl_total em notas_itens onde ni.ata_item_id = ai.id
    if _view_existe(cur, "vw_saldo_ata_total"):
        cur.execute("DROP VIEW vw_saldo_ata_total;")
    cur.execute("""
    CREATE VIEW vw_saldo_ata_total AS
    SELECT
        a.id            AS ata_id,
        a.fornecedor_id,
        a.numero,
        a.vigencia_ini,
        a.vigencia_fim,
        a.status,
        IFNULL(SUM(ai.vl_total),0) AS valor_total_ata,
        IFNULL((
            SELECT SUM(ni.vl_total)
              FROM notas_itens ni
              WHERE ni.ata_item_id IN (SELECT id FROM atas_itens WHERE ata_id = a.id)
        ), 0) AS valor_consumido,
        -- saldo financeiro
        (IFNULL(SUM(ai.vl_total),0) - IFNULL((
            SELECT SUM(ni.vl_total)
              FROM notas_itens ni
              WHERE ni.ata_item_id IN (SELECT id FROM atas_itens WHERE ata_id = a.id)
        ), 0)) AS valor_saldo,
        -- quantidade de itens cadastrados na ata
        (SELECT COUNT(1) FROM atas_itens x WHERE x.ata_id = a.id) AS itens_qtd
    FROM atas a
    LEFT JOIN atas_itens ai ON ai.ata_id = a.id
    GROUP BY a.id;
    """)

    # -------- Empenhos --------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS empenhos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
        cod_aghu TEXT NOT NULL,
        nome_item TEXT NOT NULL,
        vl_unit REAL NOT NULL DEFAULT 0,
        vl_total REAL NOT NULL DEFAULT 0,
        numero_empenho TEXT,
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_emp_fornecedor ON empenhos(fornecedor_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_emp_cod ON empenhos(cod_aghu);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_emp_numero ON empenhos(numero_empenho);")

    # -------- Notas (cabeçalho) --------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
        numero TEXT NOT NULL,               -- numero+série (ex: 1234-1)
        data_expedicao TEXT NOT NULL,       -- 'YYYY-MM-DD' (ou dd/mm/aaaa se preferir)
        vl_total REAL NOT NULL DEFAULT 0,   -- total da nota
        codigo_sei TEXT,
        data_envio_processo TEXT,
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(fornecedor_id, numero)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_fornec ON notas(fornecedor_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_numero ON notas(numero);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_data ON notas(data_expedicao);")

    # -------- Notas Itens (detalhe) --------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notas_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nota_id INTEGER NOT NULL REFERENCES notas(id) ON DELETE CASCADE,
        cod_aghu TEXT NOT NULL,
        data_uso TEXT,
        vl_unit REAL NOT NULL DEFAULT 0,
        qtde REAL NOT NULL DEFAULT 0,
        vl_total REAL NOT NULL DEFAULT 0,
        qtde_consumida REAL NOT NULL DEFAULT 0,
        ata_item_id INTEGER REFERENCES atas_itens(id) ON DELETE SET NULL,
        empenho_id INTEGER REFERENCES empenhos(id) ON DELETE SET NULL
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_itens_codh ON notas_itens(cod_aghu);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_itens_nota ON notas_itens(nota_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_itens_ata ON notas_itens(ata_item_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_itens_emp ON notas_itens(empenho_id);")

    # -------- Orçamentos --------
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orc_fornec ON orcamentos(fornecedor_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orc_cod ON orcamentos(cod_aghu);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orc_criado_em ON orcamentos(criado_em);")

    # -------- Mensagens (modelos/rascunhos) --------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS mensagens_padrao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER REFERENCES fornecedores(id) ON DELETE SET NULL,
        titulo TEXT NOT NULL,
        conteudo TEXT NOT NULL,
        tipo TEXT NOT NULL DEFAULT 'modelo', -- 'modelo' | 'rascunho'
        criado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_msgs_tipo ON mensagens_padrao(tipo);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_msgs_forn ON mensagens_padrao(fornecedor_id);")

    # -------- Itens em rascunho (persistência da grade de orçamento antes do envio) --------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS itens_rascunho (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER NULL,
        cod_aghu TEXT NOT NULL,
        nome_item TEXT NOT NULL,
        qtde REAL NOT NULL,
        vl_unit REAL NOT NULL,
        numero_empenho TEXT,
        observacao TEXT,
        criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_it_rasc_forn ON itens_rascunho (fornecedor_id, criado_em DESC);")

    # -------- Views de saldos --------
    if _view_existe(cur, "vw_saldo_ata"):
        cur.execute("DROP VIEW vw_saldo_ata;")
    cur.execute("""
    CREATE VIEW vw_saldo_ata AS
    SELECT
        a.id           AS ata_id,
        a.fornecedor_id,
        a.pregao,
        a.cod_aghu,
        a.nome_item,
        a.qtde_total,
        IFNULL((SELECT SUM(ni.qtde) FROM notas_itens ni WHERE ni.ata_item_id = a.id), 0) AS qtde_usada,
        (a.qtde_total - IFNULL((SELECT SUM(ni.qtde) FROM notas_itens ni WHERE ni.ata_item_id = a.id), 0)) AS qtde_saldo
    FROM atas_itens a;
    """)

    if _view_existe(cur, "vw_saldo_empenho"):
        cur.execute("DROP VIEW vw_saldo_empenho;")
    cur.execute("""
    CREATE VIEW vw_saldo_empenho AS
    SELECT
        e.id           AS empenho_id,
        e.fornecedor_id,
        e.cod_aghu,
        e.nome_item,
        e.vl_total,
        IFNULL((SELECT SUM(ni.vl_total) FROM notas_itens ni WHERE ni.empenho_id = e.id), 0) AS valor_consumido,
        (e.vl_total - IFNULL((SELECT SUM(ni.vl_total) FROM notas_itens ni WHERE ni.empenho_id = e.id), 0)) AS valor_saldo
    FROM empenhos e;
    """)

    conn.commit()
    conn.close()

# =========================
#   CRUDs / Consultas
# =========================
# ------ Fornecedores ------
def fornecedores_listar(busca: str = "") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    if busca:
        cur.execute("""
            SELECT * FROM fornecedores
            WHERE nome LIKE ?
            ORDER BY nome
        """, (f"%{busca}%",))
    else:
        cur.execute("SELECT * FROM fornecedores ORDER BY nome;")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def fornecedor_obter(id_: int) -> Optional[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT * FROM fornecedores WHERE id=?", (id_,))
    row = cur.fetchone(); conn.close()
    return dict(row) if row else None

def fornecedor_inserir(d: Dict[str, Any]) -> int:
    campos = ("nome","cnpj","contato_vendedor","telefone","email","rua","numero",
              "complemento","bairro","municipio","estado","cep","observacao")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar(); cur = conn.cursor()
    cur.execute(f"INSERT INTO fornecedores ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})", vals)
    conn.commit(); novo_id = cur.lastrowid; conn.close()
    return novo_id

def fornecedor_atualizar(id_: int, d: Dict[str, Any]) -> None:
    campos = ("nome","cnpj","contato_vendedor","telefone","email","rua","numero",
              "complemento","bairro","municipio","estado","cep","observacao")
    sets = ", ".join([f"{k}=?" for k in campos])
    vals = tuple(d.get(k) for k in campos) + (id_,)
    conn = conectar(); cur = conn.cursor()
    cur.execute(f"UPDATE fornecedores SET {sets}, atualizado_em=datetime('now','localtime') WHERE id=?", vals)
    conn.commit(); conn.close()

def fornecedor_excluir(id_: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM fornecedores WHERE id=?", (id_,))
    conn.commit(); conn.close()

# ------ Atas (itens) ------
def ata_item_inserir(d: Dict[str, Any]) -> int:
    campos = ("fornecedor_id","pregao","cod_aghu","nome_item","qtde_total","vl_unit","vl_total","observacao")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar(); cur = conn.cursor()
    cur.execute(f"INSERT INTO atas_itens ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})", vals)
    conn.commit(); novo_id = cur.lastrowid; conn.close()
    return novo_id

def ata_itens_listar(fornecedor_id: Optional[int] = None, busca_cod: str = "", busca_pregao: str = "") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM atas_itens WHERE 1=1"; params: Tuple[Any, ...] = tuple()
    if fornecedor_id:
        sql += " AND fornecedor_id=?"; params += (fornecedor_id,)
    if busca_cod:
        sql += " AND cod_aghu LIKE ?"; params += (f"%{busca_cod}%",)
    if busca_pregao:
        sql += " AND pregao LIKE ?"; params += (f"%{busca_pregao}%",)
    sql += " ORDER BY pregao, cod_aghu;"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

# ------ ATAS (cabeçalho) ------
def ata_hdr_inserir(d: Dict[str,Any]) -> int:
    """
    d = {'fornecedor_id','numero','vigencia_ini','vigencia_fim','status','observacao'}
    datas em 'YYYY-MM-DD' ou None
    """
    campos = ("fornecedor_id","numero","vigencia_ini","vigencia_fim","status","observacao")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar(); cur = conn.cursor()
    cur.execute(f"INSERT INTO atas ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})", vals)
    conn.commit(); nid = cur.lastrowid; conn.close()
    return nid

def ata_hdr_atualizar(ata_id: int, d: Dict[str,Any]) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        UPDATE atas SET
            numero=?, vigencia_ini=?, vigencia_fim=?, status=?, observacao=?,
            atualizado_em = datetime('now','localtime')
        WHERE id=?
    """, (d.get("numero"), d.get("vigencia_ini"), d.get("vigencia_fim"), d.get("status"), d.get("observacao"), ata_id))
    conn.commit(); conn.close()

def ata_hdr_excluir(ata_id: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM atas WHERE id=?", (ata_id,))
    conn.commit(); conn.close()

def atas_hdr_listar(fornecedor_id: Optional[int]=None, busca_numero: str="") -> List[Dict[str,Any]]:
    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM vw_saldo_ata_total WHERE 1=1"
    params: List[Any] = []
    if fornecedor_id:
        sql += " AND fornecedor_id=?"; params.append(fornecedor_id)
    if busca_numero:
        sql += " AND numero LIKE ?"; params.append(f"%{busca_numero}%")
    sql += " ORDER BY numero DESC, ata_id DESC"
    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows


def ata_hdr_obter(ata_id: int) -> Optional[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT * FROM atas WHERE id = ?", (ata_id,))
    row = cur.fetchone(); conn.close()
    return dict(row) if row else None

# ------ ATAS (itens) ------
def ata_item_inserir_v2(d: Dict[str,Any]) -> int:
    """
    d = {'ata_id','cod_aghu','nome_item','qtde_total','vl_unit','vl_total','observacao'}
    """
    campos = ("ata_id","cod_aghu","nome_item","qtde_total","vl_unit","vl_total","observacao")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar(); cur = conn.cursor()
    cur.execute(f"INSERT INTO atas_itens ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})", vals)
    conn.commit(); iid = cur.lastrowid; conn.close()
    return iid

def ata_itens_listar_por_ata(ata_id: int) -> List[Dict[str,Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT id, cod_aghu, nome_item, qtde_total, vl_unit, vl_total, observacao
          FROM atas_itens
         WHERE ata_id=?
         ORDER BY id ASC
    """, (ata_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

def ata_item_atualizar(item_id: int, d: Dict[str,Any]) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        UPDATE atas_itens SET
            cod_aghu=?, nome_item=?, qtde_total=?, vl_unit=?, vl_total=?, observacao=?,
            atualizado_em = datetime('now','localtime')
        WHERE id=?
    """, (d.get("cod_aghu"), d.get("nome_item"), float(d.get("qtde_total") or 0),
          float(d.get("vl_unit") or 0), float(d.get("vl_total") or 0), d.get("observacao"), item_id))
    conn.commit(); conn.close()

def ata_item_excluir(item_id: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM atas_itens WHERE id=?", (item_id,))
    conn.commit(); conn.close()

# ------ Empenhos ------
def empenho_inserir(d: Dict[str, Any]) -> int:
    campos = ("fornecedor_id","cod_aghu","nome_item","vl_unit","vl_total","numero_empenho","observacao")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar(); cur = conn.cursor()
    cur.execute(f"INSERT INTO empenhos ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})", vals)
    conn.commit(); novo_id = cur.lastrowid; conn.close()
    return novo_id

def empenhos_listar(fornecedor_id: Optional[int] = None, busca_cod: str = "", numero_empenho: str = "") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM empenhos WHERE 1=1"; params: Tuple[Any, ...] = tuple()
    if fornecedor_id:
        sql += " AND fornecedor_id=?"; params += (fornecedor_id,)
    if busca_cod:
        sql += " AND cod_aghu LIKE ?"; params += (f"%{busca_cod}%",)
    if numero_empenho:
        sql += " AND numero_empenho LIKE ?"; params += (f"%{numero_empenho}%",)
    sql += " ORDER BY criado_em DESC;"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

# ------ Empenhos (cabeçalho "virtual" agrupado) ------
def empenho_cabecalhos_listar(fornecedor_id: Optional[int]=None, busca_numero: str="") -> List[Dict[str,Any]]:
    """
    Retorna cabeçalhos agrupados por numero_empenho:
    {'numero_empenho','fornecedor_id','itens_qtd','valor_total'}
    """
    conn = conectar(); cur = conn.cursor()
    sql = """
        SELECT
            IFNULL(numero_empenho,'-') AS numero_empenho,
            fornecedor_id,
            COUNT(*) AS itens_qtd,
            IFNULL(SUM(vl_total),0) AS valor_total
          FROM empenhos
         WHERE 1=1
    """
    params: List[Any] = []
    if fornecedor_id:
        sql += " AND fornecedor_id=?"; params.append(fornecedor_id)
    if busca_numero:
        sql += " AND IFNULL(numero_empenho,'') LIKE ?"; params.append(f"%{busca_numero}%")
    sql += " GROUP BY fornecedor_id, IFNULL(numero_empenho,'-') ORDER BY numero_empenho DESC"
    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

def empenho_itens_listar(numero_empenho: str, fornecedor_id: int) -> List[Dict[str,Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT id, cod_aghu, nome_item, vl_unit, vl_total, observacao
          FROM empenhos
         WHERE fornecedor_id=? AND IFNULL(numero_empenho,'-')=IFNULL(?, '-')
         ORDER BY id ASC
    """, (fornecedor_id, numero_empenho))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

def empenho_item_atualizar(item_id: int, d: Dict[str,Any]) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        UPDATE empenhos SET
            cod_aghu=?, nome_item=?, vl_unit=?, vl_total=?, observacao=?,
            atualizado_em = datetime('now','localtime')
        WHERE id=?
    """, (d.get("cod_aghu"), d.get("nome_item"), float(d.get("vl_unit") or 0),
          float(d.get("vl_total") or 0), d.get("observacao"), item_id))
    conn.commit(); conn.close()

def empenho_item_excluir(item_id: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM empenhos WHERE id=?", (item_id,))
    conn.commit(); conn.close()

# ------ Notas (cabeçalho + itens) ------
def nota_inserir(d: Dict[str, Any]) -> int:
    """
    d = {'fornecedor_id','numero','data_expedicao','vl_total','codigo_sei','data_envio_processo','observacao'}
    datas preferencialmente em 'YYYY-MM-DD'
    """
    campos = ("fornecedor_id","numero","data_expedicao","vl_total","codigo_sei","data_envio_processo","observacao")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar(); cur = conn.cursor()
    cur.execute(f"INSERT INTO notas ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})", vals)
    conn.commit(); novo_id = cur.lastrowid; conn.close()
    return novo_id

def nota_atualizar(nota_id: int, d: Dict[str, Any]) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        UPDATE notas
           SET numero=?,
               data_expedicao=?,
               vl_total=?,
               codigo_sei=?,
               data_envio_processo=?,
               observacao=?,
               atualizado_em = datetime('now','localtime')
         WHERE id = ?
    """, (
        d.get("numero"),
        d.get("data_expedicao"),
        float(d.get("vl_total") or 0),
        d.get("codigo_sei"),
        d.get("data_envio_processo"),
        d.get("observacao"),
        nota_id
    ))
    conn.commit(); conn.close()

def nota_excluir(nota_id: int) -> None:
    """Exclui a nota e TODOS os itens (CASCADE)."""
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM notas WHERE id = ?", (nota_id,))
    conn.commit(); conn.close()

def nota_obter(nota_id: int) -> Optional[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT * FROM notas WHERE id = ?", (nota_id,))
    row = cur.fetchone(); conn.close()
    return dict(row) if row else None

def nota_itens_inserir(nota_id: int, itens: List[Dict[str, Any]]) -> None:
    """
    itens = [{'cod_aghu','data_uso','vl_unit','qtde','vl_total','qtde_consumida','ata_item_id','empenho_id'}]
    """
    conn = conectar(); cur = conn.cursor()
    for it in itens:
        cur.execute("""
            INSERT INTO notas_itens
                (nota_id, cod_aghu, data_uso, vl_unit, qtde, vl_total, qtde_consumida, ata_item_id, empenho_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nota_id,
            it.get("cod_aghu"),
            it.get("data_uso"),
            float(it.get("vl_unit") or 0),
            float(it.get("qtde") or 0),
            float(it.get("vl_total") or 0),
            float(it.get("qtde_consumida") or 0),
            it.get("ata_item_id"),
            it.get("empenho_id"),
        ))
    conn.commit(); conn.close()

def nota_itens_listar(nota_id: int) -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT ni.*, a.pregao, a.nome_item AS ata_nome_item, e.numero_empenho
          FROM notas_itens ni
          LEFT JOIN atas_itens a ON a.id = ni.ata_item_id
          LEFT JOIN empenhos e   ON e.id = ni.empenho_id
         WHERE ni.nota_id = ?
         ORDER BY ni.id
    """, (nota_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

def nota_itens_excluir_por_nota(nota_id: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM notas_itens WHERE nota_id = ?", (nota_id,))
    conn.commit(); conn.close()

def nota_total_recalcular(nota_id: int) -> float:
    """Recalcula o total da nota a partir dos itens e atualiza notas.vl_total."""
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT IFNULL(SUM(vl_total),0) FROM notas_itens WHERE nota_id = ?", (nota_id,))
    total = float(cur.fetchone()[0] or 0.0)
    cur.execute("UPDATE notas SET vl_total = ?, atualizado_em = datetime('now','localtime') WHERE id = ?", (total, nota_id))
    conn.commit(); conn.close()
    return total

def nota_listar(fornecedor_id: Optional[int] = None, numero: str = "") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM notas WHERE 1=1"; params: Tuple[Any, ...] = tuple()
    if fornecedor_id:
        sql += " AND fornecedor_id=?"; params += (fornecedor_id,)
    if numero:
        sql += " AND numero LIKE ?"; params += (f"%{numero}%",)
    sql += " ORDER BY data_expedicao DESC, id DESC;"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

# ------ Saldos ------
def saldo_ata_por_fornecedor(fornecedor_id: int) -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT * FROM vw_saldo_ata
        WHERE fornecedor_id=?
        ORDER BY pregao, cod_aghu
    """, (fornecedor_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

def saldo_empenho_por_fornecedor(fornecedor_id: int) -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT * FROM vw_saldo_empenho
         WHERE fornecedor_id=?
         ORDER BY valor_saldo ASC, empenho_id DESC
    """, (fornecedor_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

# ------ Orçamentos ------
def orcamento_inserir(d: Dict[str, Any]) -> int:
    campos = ("fornecedor_id","cod_aghu","nome_item","qtde","vl_unit","numero_empenho","observacao","mensagem_email")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar(); cur = conn.cursor()
    cur.execute(f"INSERT INTO orcamentos ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})", vals)
    conn.commit(); novo_id = cur.lastrowid; conn.close()
    return novo_id

def orcamentos_listar(fornecedor_id: Optional[int] = None, cod_aghu: str = "", numero_empenho: str = "") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM orcamentos WHERE 1=1"; params: List[Any] = []
    if fornecedor_id:
        sql += " AND fornecedor_id=?"; params.append(fornecedor_id)
    if cod_aghu:
        sql += " AND cod_aghu LIKE ?"; params.append(f"%{cod_aghu}%")
    if numero_empenho:
        sql += " AND numero_empenho LIKE ?"; params.append(f"%{numero_empenho}%")
    sql += " ORDER BY id DESC"
    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

def _sql_orc_base() -> str:
    return """
        FROM orcamentos o
        LEFT JOIN fornecedores f ON f.id = o.fornecedor_id
        WHERE 1=1
    """

def _aplicar_filtros_orc(sql_parts: List[str], params: List[Any],
                         fornecedor_id: Optional[int] = None,
                         data_ini: Optional[str] = None,
                         data_fim: Optional[str] = None,
                         termo: str = "",
                         numero_empenho: str = "") -> Tuple[List[str], List[Any]]:
    if fornecedor_id:
        sql_parts.append(" AND o.fornecedor_id=?"); params.append(fornecedor_id)
    if data_ini:
        sql_parts.append(" AND date(o.criado_em) >= date(?)"); params.append(data_ini)
    if data_fim:
        sql_parts.append(" AND date(o.criado_em) <= date(?)"); params.append(data_fim)
    if termo:
        like = f"%{termo}%"
        sql_parts.append(" AND (o.cod_aghu LIKE ? OR o.nome_item LIKE ? OR o.observacao LIKE ?)")
        params.extend([like, like, like])
    if numero_empenho:
        sql_parts.append(" AND IFNULL(o.numero_empenho,'') LIKE ?"); params.append(f"%{numero_empenho}%")
    return sql_parts, params

def orcamentos_filtrar(fornecedor_id: Optional[int] = None,
                       data_ini: Optional[str] = None,
                       data_fim: Optional[str] = None,
                       termo: str = "",
                       numero_empenho: str = "") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    parts: List[str] = [_sql_orc_base()]; params: List[Any] = []
    parts, params = _aplicar_filtros_orc(parts, params, fornecedor_id, data_ini, data_fim, termo, numero_empenho)
    sql_rows = f"""
        SELECT o.id, o.fornecedor_id, f.nome AS fornecedor_nome,
               o.cod_aghu, o.nome_item, o.qtde, o.vl_unit,
               o.numero_empenho, o.observacao, o.criado_em
        {''.join(parts)}
        ORDER BY o.id DESC
    """
    cur.execute(sql_rows, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

def orcamentos_filtrar_paginado(fornecedor_id: Optional[int] = None,
                                data_ini: Optional[str] = None,
                                data_fim: Optional[str] = None,
                                termo: str = "",
                                numero_empenho: str = "",
                                limit: int = 50,
                                offset: int = 0) -> Dict[str, Any]:
    conn = conectar(); cur = conn.cursor()
    parts: List[str] = [_sql_orc_base()]; params: List[Any] = []
    parts, params = _aplicar_filtros_orc(parts, params, fornecedor_id, data_ini, data_fim, termo, numero_empenho)

    sql_count = f"SELECT COUNT(*) {''.join(parts)}"
    cur.execute(sql_count, tuple(params))
    total = int(cur.fetchone()[0] or 0)

    sql_rows = f"""
        SELECT o.id, o.fornecedor_id, f.nome AS fornecedor_nome,
               o.cod_aghu, o.nome_item, o.qtde, o.vl_unit,
               o.numero_empenho, o.observacao, o.criado_em
        {''.join(parts)}
        ORDER BY o.id DESC
        LIMIT ? OFFSET ?
    """
    cur.execute(sql_rows, tuple(params) + (int(limit), int(offset)))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return {"rows": rows, "total": total}

def orcamento_excluir(id_: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM orcamentos WHERE id=?", (id_,))
    conn.commit(); conn.close()

# ------ Mensagens (modelos/rascunhos) ------
def mensagem_inserir(d: Dict[str, Any]) -> int:
    campos = ("fornecedor_id","titulo","conteudo","tipo")
    vals = (d.get("fornecedor_id"), d["titulo"], d["conteudo"], d.get("tipo","modelo"))
    conn = conectar(); cur = conn.cursor()
    cur.execute(f"INSERT INTO mensagens_padrao ({','.join(campos)}) VALUES (?,?,?,?)", vals)
    conn.commit(); novo_id = cur.lastrowid; conn.close()
    return novo_id

def mensagens_listar(tipo: Optional[str] = None, fornecedor_id: Optional[int] = None, busca: str = "") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM mensagens_padrao WHERE 1=1"; params: List[Any] = []
    if tipo:
        sql += " AND tipo=?"; params.append(tipo)
    # inclui globais (NULL) E do fornecedor (quando fornecedor_id for dado)
    if fornecedor_id is not None:
        sql += " AND (fornecedor_id IS NULL OR fornecedor_id=?)"; params.append(fornecedor_id)
    if busca:
        like = f"%{busca}%"
        sql += " AND (titulo LIKE ? OR conteudo LIKE ?)"; params.extend([like, like])
    sql += " ORDER BY id DESC"
    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

def mensagens_obter(id_: int) -> Optional[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT * FROM mensagens_padrao WHERE id=?", (id_,))
    row = cur.fetchone(); conn.close()
    return dict(row) if row else None

# alias compatível com a tela
def mensagem_obter(id_: int) -> Optional[Dict[str, Any]]:
    return mensagens_obter(id_)

def mensagem_excluir(id_: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM mensagens_padrao WHERE id=?", (id_,))
    conn.commit(); conn.close()

def mensagem_atualizar(id_: int, novo_titulo: str, novo_conteudo: str) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        UPDATE mensagens_padrao
           SET titulo=?, conteudo=?
         WHERE id=?
    """, (novo_titulo, novo_conteudo, id_))
    conn.commit(); conn.close()

# ------ Itens em Rascunho (grade de orçamento) ------
def itens_rascunho_inserir(d: Dict[str, Any]) -> int:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO itens_rascunho
            (fornecedor_id, cod_aghu, nome_item, qtde, vl_unit, numero_empenho, observacao)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (d.get("fornecedor_id"), d["cod_aghu"], d["nome_item"], d["qtde"], d["vl_unit"],
          d.get("numero_empenho"), d.get("observacao")))
    conn.commit(); new_id = cur.lastrowid; conn.close()
    return new_id

def itens_rascunho_listar(fornecedor_id: Optional[int]) -> List[Dict[str, Any]]:
    where = "fornecedor_id IS NULL" if fornecedor_id is None else "fornecedor_id = ?"
    params: Tuple[Any, ...] = tuple() if fornecedor_id is None else (fornecedor_id,)
    sql = f"""
        SELECT id, fornecedor_id, cod_aghu, nome_item, qtde, vl_unit,
               numero_empenho, observacao, criado_em
          FROM itens_rascunho
         WHERE {where}
         ORDER BY criado_em ASC, id ASC
    """
    conn = conectar(); cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

def itens_rascunho_excluir(item_id: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM itens_rascunho WHERE id = ?", (item_id,))
    conn.commit(); conn.close()

def itens_rascunho_limpar_por_fornecedor(fornecedor_id: Optional[int]) -> None:
    conn = conectar(); cur = conn.cursor()
    if fornecedor_id is None:
        cur.execute("DELETE FROM itens_rascunho WHERE fornecedor_id IS NULL")
    else:
        cur.execute("DELETE FROM itens_rascunho WHERE fornecedor_id = ?", (fornecedor_id,))
    conn.commit(); conn.close()
