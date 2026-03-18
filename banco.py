# banco.py
import sqlite3
import os
from typing import List, Dict, Any, Optional, Tuple

# Caminho do banco (UNC). Mantenha como está se o compartilhamento estiver acessível.
CAMINHO_BANCO = r"\\hc-arquivos.hc.ufpr.br\HC-GERAL\GERAD\DILIH\SESUP\Todos-SESUP\OPME\BD_Notas\notas.db"

# ---------- Conexão ----------
def conectar():
    """
    Abre conexão SQLite com FK habilitada e row_factory por nome de coluna.
    """
    # Garante diretório quando for caminho local; para UNC normalmente já existe.
    try:
        base_dir = os.path.dirname(CAMINHO_BANCO)
        if base_dir and not os.path.exists(base_dir) and not base_dir.startswith("\\\\"):
            os.makedirs(base_dir, exist_ok=True)
    except Exception:
        # Em UNC, ignoramos criação de pasta
        pass

    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    # Mantém journal_mode em WAL quando local; em rede pode não ser suportado. Não forçamos aqui.
    return conn

# ---------- Helpers de migração ----------
def _tabela_info(cur: sqlite3.Cursor, nome_tabela: str) -> List[sqlite3.Row]:
    cur.execute(f"PRAGMA table_info({nome_tabela})")
    return cur.fetchall()

def _coluna_existe(cur: sqlite3.Cursor, nome_tabela: str, coluna: str) -> bool:
    info = _tabela_info(cur, nome_tabela)
    return any(r["name"] == coluna for r in info)

def _indice_existe(cur: sqlite3.Cursor, nome_indice: str) -> bool:
    cur.execute("PRAGMA database_list")
    cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (nome_indice,))
    return cur.fetchone() is not None

def _view_existe(cur: sqlite3.Cursor, nome_view: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='view' AND name=?", (nome_view,))
    return cur.fetchone() is not None

# ---------- Criação/Migração de Schema ----------
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
    # CNPJ pode ser nulo; UNIQUE aceita múltiplos NULLs no SQLite, então é seguro.
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_fornec_cnpj ON fornecedores(cnpj);")

    # ---------------- Itens de Pregão (Ata) ----------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS atas_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
        pregao TEXT NOT NULL,                  -- número/identificador do pregão (Ata)
        cod_aghu TEXT NOT NULL,                -- código do item
        nome_item TEXT NOT NULL,
        qtde_total REAL NOT NULL DEFAULT 0,    -- quantidade prevista na ata
        vl_unit REAL NOT NULL DEFAULT 0,
        vl_total REAL NOT NULL DEFAULT 0,      -- redundante para facilitar conferência
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
        cod_aghu TEXT NOT NULL,                -- relaciona ao item do pregão
        nome_item TEXT NOT NULL,
        vl_unit REAL NOT NULL DEFAULT 0,
        vl_total REAL NOT NULL DEFAULT 0,
        numero_empenho TEXT,                   -- número textual do empenho (se houver)
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_emp_fornecedor ON empenhos(fornecedor_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_emp_cod ON empenhos(cod_aghu);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_emp_numero ON empenhos(numero_empenho);")

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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_data ON notas(data_expedicao);")

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
        -- colunas de vínculo serão adicionadas abaixo, caso não existam
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_itens_codh ON notas_itens(cod_aghu);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_itens_nota ON notas_itens(nota_id);")

    # --- Migração: acrescenta vínculos diretos (idempotente) ---
    if not _coluna_existe(cur, "notas_itens", "ata_item_id"):
        cur.execute("ALTER TABLE notas_itens ADD COLUMN ata_item_id INTEGER REFERENCES atas_itens(id) ON DELETE SET NULL;")
    if not _coluna_existe(cur, "notas_itens", "empenho_id"):
        cur.execute("ALTER TABLE notas_itens ADD COLUMN empenho_id INTEGER REFERENCES empenhos(id) ON DELETE SET NULL;")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_itens_ata ON notas_itens(ata_item_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notas_itens_emp ON notas_itens(empenho_id);")

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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orc_fornec ON orcamentos(fornecedor_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orc_cod ON orcamentos(cod_aghu);")

    # ---------------- Índice auxiliar para histórico de orçamentos ----------------
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orc_criado_em ON orcamentos(criado_em);")

    # ---------------- Mensagens (Modelos & Rascunhos) ----------------
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

    # --------- Views de Saldos (recriadas) ---------
    # SLD ATA: por item de ata (id), considera SOMENTE itens de nota vinculados àquela ata_item_id
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
        IFNULL((
            SELECT SUM(ni.qtde)
            FROM notas_itens ni
            WHERE ni.ata_item_id = a.id
        ), 0) AS qtde_usada,
        (a.qtde_total - IFNULL((
            SELECT SUM(ni.qtde)
            FROM notas_itens ni
            WHERE ni.ata_item_id = a.id
        ), 0)) AS qtde_saldo
    FROM atas_itens a;
    """)

    # SLD EMPENHO: por empenho (id), soma valor total dos itens vinculados àquele empenho
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
        IFNULL((
            SELECT SUM(ni.vl_total)
            FROM notas_itens ni
            WHERE ni.empenho_id = e.id
        ), 0) AS valor_consumido,
        (e.vl_total - IFNULL((
            SELECT SUM(ni.vl_total)
            FROM notas_itens ni
            WHERE ni.empenho_id = e.id
        ), 0)) AS valor_saldo
    FROM empenhos e;
    """)

    conn.commit()
    conn.close()

# ---------- Funções de Dados (CRUDs simples) ----------
# ------ Fornecedores ------
def fornecedores_listar(busca: str = "") -> List[Dict[str, Any]]:
    conn = conectar()
    cur = conn.cursor()
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
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT * FROM fornecedores WHERE id=?", (id_,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def fornecedor_inserir(d: Dict[str, Any]) -> int:
    """
    d = {
      'nome','cnpj','contato_vendedor','telefone','email','rua','numero',
      'complemento','bairro','municipio','estado','cep','observacao'
    }
    """
    campos = ("nome","cnpj","contato_vendedor","telefone","email","rua","numero",
              "complemento","bairro","municipio","estado","cep","observacao")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO fornecedores ({",".join(campos)})
        VALUES ({",".join(["?"]*len(campos))})
    """, vals)
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id

def fornecedor_atualizar(id_: int, d: Dict[str, Any]) -> None:
    campos = ("nome","cnpj","contato_vendedor","telefone","email","rua","numero",
              "complemento","bairro","municipio","estado","cep","observacao")
    sets = ", ".join([f"{k}=?" for k in campos])
    vals = tuple(d.get(k) for k in campos) + (id_,)
    conn = conectar()
    cur = conn.cursor()
    cur.execute(f"UPDATE fornecedores SET {sets}, atualizado_em=datetime('now','localtime') WHERE id=?", vals)
    conn.commit()
    conn.close()

def fornecedor_excluir(id_: int) -> None:
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM fornecedores WHERE id=?", (id_,))
    conn.commit()
    conn.close()

# ------ Itens de Ata (Pregão) ------
def ata_item_inserir(d: Dict[str, Any]) -> int:
    """
    d = {'fornecedor_id','pregao','cod_aghu','nome_item','qtde_total','vl_unit','vl_total','observacao'}
    """
    campos = ("fornecedor_id","pregao","cod_aghu","nome_item","qtde_total","vl_unit","vl_total","observacao")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO atas_itens ({",".join(campos)})
        VALUES ({",".join(["?"]*len(campos))})
    """, vals)
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id

def ata_itens_listar(fornecedor_id: Optional[int] = None, busca_cod: str = "", busca_pregao: str = "") -> List[Dict[str, Any]]:
    conn = conectar()
    cur = conn.cursor()
    sql = "SELECT * FROM atas_itens WHERE 1=1"
    params: Tuple[Any, ...] = tuple()
    if fornecedor_id:
        sql += " AND fornecedor_id=?"
        params += (fornecedor_id,)
    if busca_cod:
        sql += " AND cod_aghu LIKE ?"
        params += (f"%{busca_cod}%",)
    if busca_pregao:
        sql += " AND pregao LIKE ?"
        params += (f"%{busca_pregao}%",)
    sql += " ORDER BY pregao, cod_aghu;"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# ------ Empenhos ------
def empenho_inserir(d: Dict[str, Any]) -> int:
    """
    d = {'fornecedor_id','cod_aghu','nome_item','vl_unit','vl_total','numero_empenho','observacao'}
    """
    campos = ("fornecedor_id","cod_aghu","nome_item","vl_unit","vl_total","numero_empenho","observacao")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO empenhos ({",".join(campos)})
        VALUES ({",".join(["?"]*len(campos))})
    """, vals)
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id

def empenhos_listar(fornecedor_id: Optional[int] = None, busca_cod: str = "", numero_empenho: str = "") -> List[Dict[str, Any]]:
    conn = conectar()
    cur = conn.cursor()
    sql = "SELECT * FROM empenhos WHERE 1=1"
    params: Tuple[Any, ...] = tuple()
    if fornecedor_id:
        sql += " AND fornecedor_id=?"
        params += (fornecedor_id,)
    if busca_cod:
        sql += " AND cod_aghu LIKE ?"
        params += (f"%{busca_cod}%",)
    if numero_empenho:
        sql += " AND numero_empenho LIKE ?"
        params += (f"%{numero_empenho}%",)
    sql += " ORDER BY criado_em DESC;"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# ------ Notas ------
def nota_inserir(d: Dict[str, Any]) -> int:
    """
    d = {'fornecedor_id','numero','data_expedicao','vl_total','codigo_sei','data_envio_processo','observacao'}
    datas em 'YYYY-MM-DD'
    """
    campos = ("fornecedor_id","numero","data_expedicao","vl_total","codigo_sei","data_envio_processo","observacao")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO notas ({",".join(campos)})
        VALUES ({",".join(["?"]*len(campos))})
    """, vals)
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id

def nota_itens_inserir(nota_id: int, itens: List[Dict[str, Any]]) -> None:
    """
    itens = lista de {
        'cod_aghu','data_uso','vl_unit','qtde','vl_total','qtde_consumida',
        'ata_item_id'(opcional), 'empenho_id'(opcional)
    }
    """
    conn = conectar()
    cur = conn.cursor()
    for it in itens:
        cur.execute("""
            INSERT INTO notas_itens (nota_id, cod_aghu, data_uso, vl_unit, qtde, vl_total, qtde_consumida, ata_item_id, empenho_id)
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
    conn.commit()
    conn.close()

def nota_listar(fornecedor_id: Optional[int] = None, numero: str = "") -> List[Dict[str, Any]]:
    conn = conectar()
    cur = conn.cursor()
    sql = "SELECT * FROM notas WHERE 1=1"
    params: Tuple[Any, ...] = tuple()
    if fornecedor_id:
        sql += " AND fornecedor_id=?"
        params += (fornecedor_id,)
    if numero:
        sql += " AND numero LIKE ?"
        params += (f"%{numero}%",)
    sql += " ORDER BY data_expedicao DESC, id DESC;"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def nota_itens_listar(nota_id: int) -> List[Dict[str, Any]]:
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT ni.*, a.pregao, a.nome_item AS ata_nome_item, e.numero_empenho
        FROM notas_itens ni
        LEFT JOIN atas_itens a ON a.id = ni.ata_item_id
        LEFT JOIN empenhos e   ON e.id = ni.empenho_id
        WHERE ni.nota_id = ?
        ORDER BY ni.id
    """, (nota_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# ------ Saldos ------
def saldo_ata_por_fornecedor(fornecedor_id: int) -> List[Dict[str, Any]]:
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM vw_saldo_ata
        WHERE fornecedor_id=?
        ORDER BY pregao, cod_aghu
    """, (fornecedor_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def saldo_empenho_por_fornecedor(fornecedor_id: int) -> List[Dict[str, Any]]:
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM vw_saldo_empenho
        WHERE fornecedor_id=?
        ORDER BY valor_saldo ASC, empenho_id DESC   -- <<< coluna correta
    """, (fornecedor_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# ------ Orçamentos ------
def orcamento_inserir(d):
    """
    d = {
      'fornecedor_id','cod_aghu','nome_item','qtde','vl_unit','numero_empenho',
      'observacao','mensagem_email'
    }
    """
    campos = ("fornecedor_id","cod_aghu","nome_item","qtde","vl_unit",
              "numero_empenho","observacao","mensagem_email")
    vals = tuple(d.get(k) for k in campos)
    conn = conectar()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO orcamentos ({",".join(campos)})
        VALUES ({",".join(["?"]*len(campos))})
    """, vals)
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id

def orcamentos_listar(fornecedor_id=None, cod_aghu="", numero_empenho=""):
    conn = conectar()
    cur = conn.cursor()
    sql = "SELECT * FROM orcamentos WHERE 1=1"
    params = []
    if fornecedor_id:
        sql += " AND fornecedor_id=?"; params.append(fornecedor_id)
    if cod_aghu:
        sql += " AND cod_aghu LIKE ?"; params.append(f"%{cod_aghu}%")
    if numero_empenho:
        sql += " AND numero_empenho LIKE ?"; params.append(f"%{numero_empenho}%")
    sql += " ORDER BY id DESC"
    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def orcamento_excluir(id_):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM orcamentos WHERE id=?", (id_,))
    conn.commit()
    conn.close()

# ------ Orçamentos (filtros p/ histórico) ------
def orcamentos_filtrar(
    fornecedor_id: int | None = None,
    data_ini: str | None = None,  # 'YYYY-MM-DD'
    data_fim: str | None = None,  # 'YYYY-MM-DD'
    termo: str = "",
    numero_empenho: str = ""
):
    conn = conectar()
    cur = conn.cursor()
    sql = """
        SELECT o.id, o.fornecedor_id, f.nome AS fornecedor_nome,
               o.cod_aghu, o.nome_item, o.qtde, o.vl_unit,
               o.numero_empenho, o.observacao, o.criado_em
        FROM orcamentos o
        LEFT JOIN fornecedores f ON f.id = o.fornecedor_id
        WHERE 1=1
    """
    params: list = []
    if fornecedor_id:
        sql += " AND o.fornecedor_id=?"
        params.append(fornecedor_id)
    if data_ini:
        sql += " AND date(o.criado_em) >= date(?)"
        params.append(data_ini)
    if data_fim:
        sql += " AND date(o.criado_em) <= date(?)"
        params.append(data_fim)
    if termo:
        sql += """ AND (
            o.cod_aghu LIKE ? OR
            o.nome_item LIKE ? OR
            o.observacao LIKE ?
        )"""
        like = f"%{termo}%"
        params.extend([like, like, like])
    if numero_empenho:
        sql += " AND IFNULL(o.numero_empenho,'') LIKE ?"
        params.append(f"%{numero_empenho}%")

    sql += " ORDER BY o.id DESC"
    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# ------ Mensagens padrão / rascunhos ------
def mensagem_inserir(d):
    """
    d = {'fornecedor_id': Optional[int], 'titulo': str, 'conteudo': str, 'tipo': 'modelo'|'rascunho'}
    """
    campos = ("fornecedor_id","titulo","conteudo","tipo")
    vals = (d.get("fornecedor_id"), d["titulo"], d["conteudo"], d.get("tipo","modelo"))
    conn = conectar()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO mensagens_padrao ({",".join(campos)})
        VALUES (?,?,?,?)
    """, vals)
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id

def mensagens_listar(tipo: str | None = None, fornecedor_id: int | None = None, busca: str = ""):
    conn = conectar()
    cur = conn.cursor()
    sql = "SELECT * FROM mensagens_padrao WHERE 1=1"
    params: list = []
    if tipo:
        sql += " AND tipo=?"; params.append(tipo)
    if fornecedor_id is not None:
        sql += " AND (fornecedor_id IS NULL OR fornecedor_id=?)"; params.append(fornecedor_id)
    if busca:
        sql += " AND (titulo LIKE ? OR conteudo LIKE ?)"
        like = f"%{busca}%"
        params.extend([like, like])
    sql += " ORDER BY id DESC"
    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def mensagem_excluir(id_: int):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM mensagens_padrao WHERE id=?", (id_,))
    conn.commit()
    conn.close()

def mensagem_atualizar(id_: int, novo_titulo: str, novo_conteudo: str):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        UPDATE mensagens_padrao
           SET titulo=?, conteudo=?
         WHERE id=?
    """, (novo_titulo, novo_conteudo, id_))
    conn.commit()
    conn.close()
