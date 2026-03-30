# ============================================================
#  banco.py LIMPO — COMPLETO (PARTE 1 / 4)
#  Livre de criar_tabelas() e migrações. Apenas CRUD.
# ============================================================

import os
import sqlite3
from typing import List, Dict, Any, Optional, Tuple

# =========================
#  Caminho do banco
# =========================
CAMINHO_BANCO = r"\\hc-arquivos.hc.ufpr.br\HC-GERAL\GERAD\DILIH\SESUP\Todos-SESUP\OPME\BD_Notas\notas_novo.db"

# -------------------------------------------------------
#  Conexão SQLite (sempre com FK ON)
# -------------------------------------------------------
def conectar() -> sqlite3.Connection:
    try:
        base_dir = os.path.dirname(CAMINHO_BANCO)
        if base_dir and not base_dir.startswith("\\\\") and not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
    except Exception:
        pass

    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys = ON;")
    except Exception:
        pass

    return conn


# -------------------------------------------------------
#  criar_tabelas() — DESATIVADO
# -------------------------------------------------------
def criar_tabelas() -> None:
    """
    DESATIVADO — O banco é mantido externamente (DBeaver).
    Não remover esta função; várias telas importam ela.
    """
    return


# ===========================================================
#  CRUD / CONSULTAS — APENAS OPERAÇÃO DE DADOS
# ===========================================================

# ===========================================================
#  FORNECEDORES
# ===========================================================
def fornecedores_listar(busca: str = "") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    if busca:
        cur.execute("SELECT * FROM fornecedores WHERE nome LIKE ? ORDER BY nome",
                    (f"%{busca}%",))
    else:
        cur.execute("SELECT * FROM fornecedores ORDER BY nome")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def fornecedor_obter(id_: int) -> Optional[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT * FROM fornecedores WHERE id=?", (id_,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def fornecedor_inserir(d: Dict[str, Any]) -> int:
    campos = (
        "nome", "cnpj", "contato_vendedor", "telefone", "email",
        "rua", "numero", "complemento", "bairro", "municipio",
        "estado", "cep", "observacao"
    )
    vals = tuple(d.get(k) for k in campos)

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"INSERT INTO fornecedores ({','.join(campos)}) "
        f"VALUES ({','.join(['?']*len(campos))})",
        vals
    )
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id


def fornecedor_atualizar(id_: int, d: Dict[str, Any]) -> None:
    campos = (
        "nome","cnpj","contato_vendedor","telefone","email",
        "rua","numero","complemento","bairro","municipio",
        "estado","cep","observacao"
    )
    sets = ", ".join([f"{k}=?" for k in campos])
    vals = tuple(d.get(k) for k in campos) + (id_,)

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"UPDATE fornecedores SET {sets}, atualizado_em=datetime('now','localtime') "
        f"WHERE id=?",
        vals
    )
    conn.commit()
    conn.close()


def fornecedor_excluir(id_: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM fornecedores WHERE id=?", (id_,))
    conn.commit()
    conn.close()


# ===========================================================
#  ATAS — CABEÇALHO
# ===========================================================
def ata_hdr_inserir(d: Dict[str,Any]) -> int:
    campos = ("fornecedor_id","numero","vigencia_ini",
              "vigencia_fim","status","observacao")
    vals = tuple(d.get(k) for k in campos)

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"INSERT INTO atas ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})",
        vals
    )
    conn.commit()
    nid = cur.lastrowid
    conn.close()
    return nid


def ata_hdr_atualizar(ata_id: int, d: Dict[str,Any]) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        UPDATE atas SET
            numero=?, vigencia_ini=?, vigencia_fim=?, status=?, observacao=?,
            atualizado_em=datetime('now','localtime')
        WHERE id=?
    """, (
        d.get("numero"),
        d.get("vigencia_ini"),
        d.get("vigencia_fim"),
        d.get("status"),
        d.get("observacao"),
        ata_id
    ))
    conn.commit()
    conn.close()


def ata_hdr_excluir(ata_id: int) -> None:
    conn = conectar(); cur = conn.cursor()

    cur.execute("""
        DELETE FROM empenhos
         WHERE ata_item_id IN (SELECT id FROM atas_itens WHERE ata_id=?)
    """, (ata_id,))

    cur.execute("DELETE FROM atas_itens WHERE ata_id=?", (ata_id,))
    cur.execute("DELETE FROM atas WHERE id=?", (ata_id,))

    conn.commit()
    conn.close()


def ata_hdr_obter(ata_id: int) -> Optional[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT * FROM atas WHERE id=?", (ata_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def atas_hdr_listar(fornecedor_id: Optional[int] = None,
                    busca_numero: str = "") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()

    sql = """
        SELECT 
            a.id AS ata_id,
            a.fornecedor_id,
            a.numero,
            a.vigencia_ini,
            a.vigencia_fim,
            a.status,
            
            -- Quantidade total de itens
            (SELECT COUNT(*) 
               FROM atas_itens ai 
              WHERE ai.ata_id = a.id) AS itens_qtd,
            
            -- Valor total da ATA
            IFNULL((SELECT SUM(vl_total)
                      FROM atas_itens ai
                     WHERE ai.ata_id = a.id), 0) AS valor_total_ata,

            -- Valor empenhado
            IFNULL((SELECT SUM(e.vl_total)
                      FROM empenhos e
                     WHERE e.ata_item_id IN 
                         (SELECT id FROM atas_itens WHERE ata_id = a.id)), 0)
                 AS valor_empenhado,

            -- Valor consumido
            IFNULL((SELECT SUM(ni.vl_total)
                      FROM notas_itens ni
                     WHERE ni.ata_item_id IN 
                         (SELECT id FROM atas_itens WHERE ata_id = a.id)), 0)
                 AS valor_consumido,

            -- Saldo
            (
                IFNULL((SELECT SUM(vl_total)
                          FROM atas_itens ai
                         WHERE ai.ata_id = a.id),0)
                -
                IFNULL((SELECT SUM(e.vl_total)
                          FROM empenhos e
                         WHERE e.ata_item_id IN 
                             (SELECT id FROM atas_itens WHERE ata_id = a.id)),0)
            ) AS valor_saldo
        FROM atas a
        WHERE 1=1
    """

    params: List[Any] = []

    if fornecedor_id:
        sql += " AND a.fornecedor_id = ?"
        params.append(fornecedor_id)

    if busca_numero:
        sql += " AND a.numero LIKE ?"
        params.append(f"%{busca_numero}%")

    sql += " ORDER BY a.numero DESC, a.id DESC"

    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# ===========================================================
#  ATAS — ITENS
# ===========================================================

def ata_itens_listar(fornecedor_id: Optional[int] = None,
                     busca_cod: str = "",
                     busca_pregao: str = "") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM atas_itens WHERE 1=1"
    params: List[Any] = []

    if fornecedor_id:
        sql += " AND fornecedor_id=?"
        params.append(fornecedor_id)

    if busca_cod:
        sql += " AND cod_aghu LIKE ?"
        params.append(f"%{busca_cod}%")

    if busca_pregao:
        sql += " AND pregao LIKE ?"
        params.append(f"%{busca_pregao}%")

    sql += " ORDER BY pregao, cod_aghu"
    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def ata_itens_listar_por_ata(ata_id: int) -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT id, cod_aghu, nome_item, qtde_total, vl_unit, vl_total, observacao
          FROM atas_itens
         WHERE ata_id=?
         ORDER BY id ASC
    """, (ata_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def ata_itens_listar_por_ata_com_saldo(ata_id: int) -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT
            ai.id,
            ai.cod_aghu,
            ai.nome_item,
            ai.qtde_total,
            ai.vl_unit,
            ai.vl_total,
            ai.observacao,
            IFNULL((SELECT SUM(e.qtde) FROM empenhos e WHERE e.ata_item_id=ai.id), 0) AS qtde_empenhada,
            (ai.qtde_total -
             IFNULL((SELECT SUM(e.qtde) FROM empenhos e WHERE e.ata_item_id=ai.id), 0)) AS qtde_saldo
        FROM atas_itens ai
        WHERE ai.ata_id=?
        ORDER BY ai.nome_item ASC
    """, (ata_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def ata_item_inserir(d: Dict[str, Any]) -> int:
    campos = (
        "fornecedor_id","pregao","cod_aghu","nome_item",
        "qtde_total","vl_unit","vl_total","observacao"
    )
    vals = tuple(d.get(k) for k in campos)

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"INSERT INTO atas_itens ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})",
        vals
    )
    conn.commit()
    iid = cur.lastrowid
    conn.close()
    return iid


def ata_item_inserir_v2(d: Dict[str, Any]) -> int:
    ata_id = d.get("ata_id")
    if not ata_id:
        raise ValueError("ata_id é obrigatório.")

    hdr = ata_hdr_obter(int(ata_id))
    if not hdr:
        raise ValueError(f"Ata cabeçalho id={ata_id} não encontrado.")

    fornecedor_id = hdr["fornecedor_id"]
    pregao = hdr["numero"]

    campos = (
        "fornecedor_id","pregao","cod_aghu","nome_item",
        "qtde_total","vl_unit","vl_total","observacao","ata_id"
    )
    vals = (
        fornecedor_id, pregao, d.get("cod_aghu"), d.get("nome_item"),
        float(d.get("qtde_total") or 0),
        float(d.get("vl_unit") or 0),
        float(d.get("vl_total") or 0),
        d.get("observacao"), ata_id
    )

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"INSERT INTO atas_itens ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})",
        vals
    )
    conn.commit()
    iid = cur.lastrowid
    conn.close()
    return iid


def ata_item_atualizar(item_id: int, d: Dict[str,Any]) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        UPDATE atas_itens SET
            cod_aghu=?, nome_item=?, qtde_total=?, vl_unit=?, vl_total=?, observacao=?,
            atualizado_em = datetime('now','localtime')
        WHERE id=?
    """, (
        d.get("cod_aghu"), d.get("nome_item"),
        float(d.get("qtde_total") or 0),
        float(d.get("vl_unit") or 0),
        float(d.get("vl_total") or 0),
        d.get("observacao"),
        item_id
    ))
    conn.commit()
    conn.close()


def ata_item_excluir(item_id: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM atas_itens WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


# ===========================================================
#  EMPENHOS
# ===========================================================

def validar_saldo_antes_empenho(ata_item_id: int, qtde_solicitada: float) -> Tuple[bool, str, float]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT 
            qtde_total,
            IFNULL((SELECT SUM(qtde) FROM empenhos WHERE ata_item_id=?), 0) AS empenhado
        FROM atas_itens
        WHERE id=?
    """, (ata_item_id, ata_item_id))

    row = cur.fetchone()
    conn.close()

    if not row:
        return False, "Item não encontrado.", 0

    total = row["qtde_total"]
    empenhado = row["empenhado"]
    saldo = total - empenhado

    if qtde_solicitada > saldo:
        return False, f"Saldo insuficiente! Disponível: {saldo}, Solicitado: {qtde_solicitada}", saldo

    return True, "Saldo OK", saldo


def empenho_inserir(d: Dict[str, Any]) -> int:
    campos = (
        "fornecedor_id","cod_aghu","nome_item","qtde",
        "vl_unit","vl_total","numero_empenho","observacao",
        "ata_item_id"
    )
    vals = (
        d.get("fornecedor_id"), d.get("cod_aghu"), d.get("nome_item"),
        float(d.get("qtde") or 0),
        float(d.get("vl_unit") or 0),
        float(d.get("vl_total") or 0),
        d.get("numero_empenho"),
        d.get("observacao"),
        d.get("ata_item_id")
    )

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"INSERT INTO empenhos ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})",
        vals
    )
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id


def empenhos_listar(fornecedor_id: Optional[int] = None,
                    busca_cod: str = "",
                    numero_empenho: str = "") -> List[Dict[str,Any]]:

    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM empenhos WHERE 1=1"
    params: List[Any] = []

    if fornecedor_id:
        sql += " AND fornecedor_id=?"
        params.append(fornecedor_id)

    if busca_cod:
        sql += " AND cod_aghu LIKE ?"
        params.append(f"%{busca_cod}%")

    if numero_empenho:
        sql += " AND numero_empenho LIKE ?"
        params.append(f"%{numero_empenho}%")

    sql += " ORDER BY criado_em DESC"
    cur.execute(sql, params)

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def empenho_itens_listar(numero_empenho: str, fornecedor_id: int) -> List[Dict[str,Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT id, cod_aghu, nome_item, qtde, vl_unit, vl_total, observacao, ata_item_id
          FROM empenhos
         WHERE fornecedor_id=? 
           AND IFNULL(numero_empenho,'-') = IFNULL(?, '-')
         ORDER BY id ASC
    """, (fornecedor_id, numero_empenho))

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def empenho_item_atualizar(item_id: int, d: Dict[str,Any]) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        UPDATE empenhos SET
            cod_aghu=?, nome_item=?, qtde=?, vl_unit=?, vl_total=?, observacao=?, ata_item_id=?,
            atualizado_em = datetime('now','localtime')
        WHERE id=?
    """, (
        d.get("cod_aghu"), d.get("nome_item"),
        float(d.get("qtde") or 0),
        float(d.get("vl_unit") or 0),
        float(d.get("vl_total") or 0),
        d.get("observacao"),
        d.get("ata_item_id"),
        item_id
    ))
    conn.commit()
    conn.close()


def empenho_excluir_por_numero(fornecedor_id: int, numero_empenho: str) -> int:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        DELETE FROM empenhos
         WHERE fornecedor_id=?
           AND IFNULL(numero_empenho,'-')=IFNULL(?, '-')
    """, (fornecedor_id, numero_empenho))

    afetados = cur.rowcount
    conn.commit()
    conn.close()
    return int(afetados or 0)


def empenho_item_excluir(item_id: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM empenhos WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def empenho_cabecalhos_listar(fornecedor_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Lista os cabeçalhos de empenho, agrupando itens pelo número do empenho.
    Retorna: numero_empenho, itens_qtd, valor_total (somado).
    """
    conn = conectar(); cur = conn.cursor()

    sql = """
        SELECT 
            e.numero_empenho,
            COUNT(e.id) AS itens_qtd,
            IFNULL(SUM(e.vl_total), 0) AS valor_total
        FROM empenhos e
        WHERE 1=1
    """
    params: List[Any] = []

    if fornecedor_id:
        sql += " AND e.fornecedor_id = ?"
        params.append(fornecedor_id)

    sql += """
        GROUP BY e.numero_empenho
        ORDER BY e.numero_empenho DESC
    """

    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# ===========================================================
#  NOTAS — CABEÇALHO + ITENS
# ===========================================================

def nota_inserir(d: Dict[str, Any]) -> int:
    campos = (
        "fornecedor_id","numero","data_expedicao",
        "vl_total","codigo_sei","data_envio_processo","observacao"
    )
    vals = tuple(d.get(k) for k in campos)

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"INSERT INTO notas ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})",
        vals
    )
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id


def nota_atualizar(nota_id: int, d: Dict[str, Any]) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        UPDATE notas SET
            numero=?, data_expedicao=?, vl_total=?, codigo_sei=?, data_envio_processo=?, observacao=?,
            atualizado_em = datetime('now','localtime')
        WHERE id=?
    """,
    (
        d.get("numero"),
        d.get("data_expedicao"),
        float(d.get("vl_total") or 0),
        d.get("codigo_sei"),
        d.get("data_envio_processo"),
        d.get("observacao"),
        nota_id
    ))
    conn.commit()
    conn.close()


def nota_excluir(nota_id: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM notas WHERE id=?", (nota_id,))
    conn.commit()
    conn.close()


def nota_obter(nota_id: int) -> Optional[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT * FROM notas WHERE id=?", (nota_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def nota_itens_inserir(nota_id: int, itens: List[Dict[str, Any]]) -> None:
    """
    itens = [
       {'cod_aghu','data_uso','vl_unit','qtde','vl_total',
        'qtde_consumida','ata_item_id','empenho_id'}
    ]
    """
    conn = conectar(); cur = conn.cursor()

    for it in itens:
        cur.execute("""
            INSERT INTO notas_itens
                (nota_id, cod_aghu, data_uso, vl_unit, qtde, vl_total, 
                 qtde_consumida, ata_item_id, empenho_id)
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


def nota_itens_listar(nota_id: int) -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT ni.*,
               a.pregao,
               a.nome_item AS ata_nome_item,
               e.numero_empenho
          FROM notas_itens ni
          LEFT JOIN atas_itens a ON a.id = ni.ata_item_id
          LEFT JOIN empenhos e   ON e.id = ni.empenho_id
         WHERE ni.nota_id = ?
         ORDER BY ni.id
    """, (nota_id,))

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def nota_itens_excluir_por_nota(nota_id: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM notas_itens WHERE nota_id=?", (nota_id,))
    conn.commit()
    conn.close()


def nota_total_recalcular(nota_id: int) -> float:
    conn = conectar(); cur = conn.cursor()

    cur.execute("SELECT IFNULL(SUM(vl_total),0) FROM notas_itens WHERE nota_id=?", (nota_id,))
    total = float(cur.fetchone()[0] or 0.0)

    cur.execute("""
        UPDATE notas
           SET vl_total=?, atualizado_em=datetime('now','localtime')
         WHERE id=?
    """, (total, nota_id))

    conn.commit()
    conn.close()
    return total


def nota_listar(fornecedor_id: Optional[int] = None,
                numero: str = "") -> List[Dict[str, Any]]:

    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM notas WHERE 1=1"
    params: List[Any] = []

    if fornecedor_id:
        sql += " AND fornecedor_id=?"
        params.append(fornecedor_id)

    if numero:
        sql += " AND numero LIKE ?"
        params.append(f"%{numero}%")

    sql += " ORDER BY data_expedicao DESC, id DESC"
    cur.execute(sql, params)

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ===========================================================
#  SALDOS (vw_saldo_ata / vw_saldo_empenho)
# ===========================================================

def saldo_ata_por_fornecedor(fornecedor_id: int) -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()

    cur.execute("""
        SELECT * 
          FROM vw_saldo_ata
         WHERE fornecedor_id=?
         ORDER BY pregao, cod_aghu
    """, (fornecedor_id,))

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def saldo_empenho_por_fornecedor(fornecedor_id: int) -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()

    cur.execute("""
        SELECT *
          FROM vw_saldo_empenho
         WHERE fornecedor_id=?
         ORDER BY valor_saldo ASC, empenho_id DESC
    """, (fornecedor_id,))

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ===========================================================
#  ORÇAMENTOS
# ===========================================================

def orcamento_inserir(d: Dict[str, Any]) -> int:
    campos = (
        "fornecedor_id","cod_aghu","nome_item","qtde",
        "vl_unit","numero_empenho","observacao","mensagem_email"
    )
    vals = tuple(d.get(k) for k in campos)

    conn = conectar(); cur = conn.cursor()

    cur.execute(
        f"INSERT INTO orcamentos ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})",
        vals
    )
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id


def orcamentos_listar(fornecedor_id: Optional[int] = None,
                      cod_aghu: str = "",
                      numero_empenho: str = "") -> List[Dict[str, Any]]:

    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM orcamentos WHERE 1=1"
    params: List[Any] = []

    if fornecedor_id:
        sql += " AND fornecedor_id=?"
        params.append(fornecedor_id)

    if cod_aghu:
        sql += " AND cod_aghu LIKE ?"
        params.append(f"%{cod_aghu}%")

    if numero_empenho:
        sql += " AND numero_empenho LIKE ?"
        params.append(f"%{numero_empenho}%")

    sql += " ORDER BY id DESC"

    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def orcamentos_filtrar(fornecedor_id: Optional[int] = None,
                       data_ini: Optional[str] = None,
                       data_fim: Optional[str] = None,
                       termo: str = "",
                       numero_empenho: str = "") -> List[Dict[str, Any]]:

    conn = conectar(); cur = conn.cursor()

    sql = """
        SELECT o.id, o.fornecedor_id, f.nome AS fornecedor_nome,
               o.cod_aghu, o.nome_item, o.qtde, o.vl_unit,
               o.numero_empenho, o.observacao, o.criado_em
          FROM orcamentos o
     LEFT JOIN fornecedores f ON f.id = o.fornecedor_id
         WHERE 1=1
    """

    params: List[Any] = []

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
        like = f"%{termo}%"
        sql += " AND (o.cod_aghu LIKE ? OR o.nome_item LIKE ? OR o.observacao LIKE ?)"
        params.extend([like, like, like])

    if numero_empenho:
        sql += " AND IFNULL(o.numero_empenho,'') LIKE ?"
        params.append(f"%{numero_empenho}%")

    sql += " ORDER BY o.id DESC"

    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def orcamentos_filtrar_paginado(
        fornecedor_id: Optional[int] = None,
        data_ini: Optional[str] = None,
        data_fim: Optional[str] = None,
        termo: str = "",
        numero_empenho: str = "",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:

    conn = conectar(); cur = conn.cursor()

    sql = """
        SELECT 
            o.id, 
            o.fornecedor_id, 
            f.nome AS fornecedor_nome,
            o.cod_aghu, 
            o.nome_item, 
            o.qtde, 
            o.vl_unit,
            o.numero_empenho, 
            o.observacao, 
            o.criado_em
        FROM orcamentos o
        LEFT JOIN fornecedores f ON f.id = o.fornecedor_id
        WHERE 1 = 1
    """

    params = []

    if fornecedor_id:
        sql += " AND o.fornecedor_id = ?"
        params.append(fornecedor_id)

    if data_ini:
        sql += " AND date(o.criado_em) >= date(?)"
        params.append(data_ini)

    if data_fim:
        sql += " AND date(o.criado_em) <= date(?)"
        params.append(data_fim)

    if termo:
        like = f"%{termo}%"
        sql += " AND (o.cod_aghu LIKE ? OR o.nome_item LIKE ? OR o.observacao LIKE ?)"
        params.extend([like, like, like])

    if numero_empenho:
        sql += " AND IFNULL(o.numero_empenho,'') LIKE ?"
        params.append(f"%{numero_empenho}%")

    sql += " ORDER BY o.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    # consulta paginada
    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]

    # total para paginação
    total = orcamentos_total(
        fornecedor_id=fornecedor_id,
        data_ini=data_ini,
        data_fim=data_fim,
        termo=termo,
        numero_empenho=numero_empenho
    )

    conn.close()
    return {
        "rows": rows,
        "total": total
    }

def orcamentos_total(
        fornecedor_id: Optional[int] = None,
        data_ini: Optional[str] = None,
        data_fim: Optional[str] = None,
        termo: str = "",
        numero_empenho: str = ""
    ) -> int:

    conn = conectar(); cur = conn.cursor()

    sql = """
        SELECT COUNT(*)
        FROM orcamentos o
        WHERE 1 = 1
    """
    params = []

    if fornecedor_id:
        sql += " AND o.fornecedor_id = ?"
        params.append(fornecedor_id)

    if data_ini:
        sql += " AND date(o.criado_em) >= date(?)"
        params.append(data_ini)

    if data_fim:
        sql += " AND date(o.criado_em) <= date(?)"
        params.append(data_fim)

    if termo:
        like = f"%{termo}%"
        sql += " AND (o.cod_aghu LIKE ? OR o.nome_item LIKE ? OR o.observacao LIKE ?)"
        params.extend([like, like, like])

    if numero_empenho:
        sql += " AND IFNULL(o.numero_empenho,'') LIKE ?"
        params.append(f"%{numero_empenho}%")

    cur.execute(sql, tuple(params))
    total = int(cur.fetchone()[0])
    conn.close()
    return total

# ===========================================================
#  MENSAGENS / RASCUNHOS — FUNCIONANDO DE VERDADE
# ===========================================================

# ========== INSERIR ==========
def mensagem_inserir(d: Dict[str, Any]) -> int:
    """
    Insere uma nova mensagem padrão (modelo ou rascunho).
    Tabela real: mensagens_padrao
    """
    campos = ("fornecedor_id", "titulo", "conteudo", "tipo")
    vals = (d.get("fornecedor_id"), d["titulo"], d["conteudo"], d.get("tipo", "modelo"))

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"INSERT INTO mensagens_padrao ({','.join(campos)}) VALUES (?,?,?,?)",
        vals
    )
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id


# ========== OBTER ==========
def mensagem_obter(id_msg: int) -> Optional[Dict[str, Any]]:
    """
    Retorna uma mensagem padrão (modelo/rascunho) pelo ID.
    Funciona com _editar_msg(), _usar_msg(), _carregar_modelo_rapido().
    """
    conn = conectar(); cur = conn.cursor()

    cur.execute("""
        SELECT id, fornecedor_id, titulo, conteudo, tipo, criado_em
        FROM mensagens_padrao
        WHERE id = ?
    """, (id_msg,))

    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ========== LISTAR ==========
def mensagens_listar(tipo: Optional[str] = None,
                     fornecedor_id: Optional[int] = None,
                     busca: str = "") -> List[Dict[str, Any]]:
    """
    Lista modelos e rascunhos.
    Usa a tabela correta: mensagens_padrao.
    """
    conn = conectar(); cur = conn.cursor()

    sql = "SELECT * FROM mensagens_padrao WHERE 1=1"
    params: List[Any] = []

    if tipo:
        sql += " AND tipo=?"
        params.append(tipo)

    if fornecedor_id is not None:
        sql += " AND (fornecedor_id IS NULL OR fornecedor_id=?)"
        params.append(fornecedor_id)

    if busca:
        like = f"%{busca}%"
        sql += " AND (titulo LIKE ? OR conteudo LIKE ?)"
        params.extend([like, like])

    sql += " ORDER BY id DESC"

    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ========== ATUALIZAR ==========
def mensagem_atualizar(id_: int, novo_titulo: str, novo_conteudo: str) -> None:
    """
    Atualiza título e conteúdo de um modelo/rascunho.
    """
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        UPDATE mensagens_padrao
           SET titulo=?, conteudo=?
         WHERE id=?
    """, (novo_titulo, novo_conteudo, id_))
    conn.commit()
    conn.close()


# ========== EXCLUIR ==========
def mensagem_excluir(id_: int) -> None:
    """
    Exclui um modelo/rascunho pelo ID.
    """
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM mensagens_padrao WHERE id=?", (id_,))
    conn.commit()
    conn.close()


# ===========================================================
#  RASCUNHOS (GRADE EM ORÇAMENTOS)
# ===========================================================

def itens_rascunho_inserir(d: Dict[str, Any]) -> int:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO itens_rascunho
            (fornecedor_id, cod_aghu, nome_item, qtde, vl_unit,
             numero_empenho, observacao)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        d.get("fornecedor_id"), d["cod_aghu"], d["nome_item"],
        d["qtde"], d["vl_unit"], d.get("numero_empenho"),
        d.get("observacao")
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def itens_rascunho_listar(fornecedor_id: Optional[int]) -> List[Dict[str, Any]]:
    where = "fornecedor_id IS NULL" if fornecedor_id is None else "fornecedor_id = ?"
    params = tuple() if fornecedor_id is None else (fornecedor_id,)

    sql = f"""
        SELECT id, fornecedor_id, cod_aghu, nome_item, qtde,
               vl_unit, numero_empenho, observacao, criado_em
          FROM itens_rascunho
         WHERE {where}
         ORDER BY criado_em ASC, id ASC
    """

    conn = conectar(); cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def itens_rascunho_excluir(item_id: int) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM itens_rascunho WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


def itens_rascunho_limpar_por_fornecedor(fornecedor_id: Optional[int]) -> None:
    conn = conectar(); cur = conn.cursor()

    if fornecedor_id is None:
        cur.execute("DELETE FROM itens_rascunho WHERE fornecedor_id IS NULL")
    else:
        cur.execute("DELETE FROM itens_rascunho WHERE fornecedor_id=?", (fornecedor_id,))

    conn.commit()
    conn.close()


# ===========================================================
#  ETL (Importações de ATAS)
# ===========================================================

def etl_estado_obter() -> Dict[str, Any]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT id, fonte, ultimo_hash, ultimo_import_ok
          FROM etl_estado
         WHERE id=1
    """)
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


def etl_estado_atualizar(ultimo_hash: Optional[str],
                         quando_local: Optional[str] = None) -> None:

    from datetime import datetime

    if not quando_local:
        quando_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = conectar(); cur = conn.cursor()

    cur.execute("""
        UPDATE etl_estado
           SET ultimo_hash=?, ultimo_import_ok=?
         WHERE id=1
    """, (ultimo_hash, quando_local))

    conn.commit()
    conn.close()

# ===========================================================
#  MENSAGENS ENVIADAS (HISTÓRICO DE E-MAILS)
# ===========================================================

def mensagem_enviada_registrar(d: Dict[str, Any]) -> int:
    """Registra uma mensagem enviada no histórico."""
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO mensagens_enviadas (fornecedor_id, destinatario, assunto, conteudo, enviado_em)
        VALUES (?, ?, ?, ?, datetime('now','localtime'))
    """, (d.get("fornecedor_id"), d.get("destinatario"), d.get("assunto"), d.get("conteudo")))
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id


def mensagens_enviadas_filtrar_paginado(
        fornecedor_id: Optional[int] = None,
        data_ini: Optional[str] = None,
        data_fim: Optional[str] = None,
        destinatario: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
    """Lista mensagens enviadas com filtros e paginação."""
    conn = conectar(); cur = conn.cursor()

    sql = """
        SELECT me.*, f.nome AS fornecedor_nome
        FROM mensagens_enviadas me
        LEFT JOIN fornecedores f ON f.id = me.fornecedor_id
        WHERE 1 = 1
    """
    params = []

    if fornecedor_id:
        sql += " AND me.fornecedor_id = ?"
        params.append(fornecedor_id)

    if data_ini:
        sql += " AND date(me.enviado_em) >= date(?)"
        params.append(data_ini)

    if data_fim:
        sql += " AND date(me.enviado_em) <= date(?)"
        params.append(data_fim)

    if destinatario:
        sql += " AND me.destinatario LIKE ?"
        params.append(f"%{destinatario}%")

    sql += " ORDER BY me.enviado_em DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]

    # Total para paginação
    total_sql = """
        SELECT COUNT(*) FROM mensagens_enviadas me WHERE 1 = 1
    """
    total_params = []
    if fornecedor_id:
        total_sql += " AND me.fornecedor_id = ?"
        total_params.append(fornecedor_id)
    if data_ini:
        total_sql += " AND date(me.enviado_em) >= date(?)"
        total_params.append(data_ini)
    if data_fim:
        total_sql += " AND date(me.enviado_em) <= date(?)"
        total_params.append(data_fim)
    if destinatario:
        total_sql += " AND me.destinatario LIKE ?"
        total_params.append(f"%{destinatario}%")

    cur.execute(total_sql, tuple(total_params))
    total = int(cur.fetchone()[0])

    conn.close()
    return {"rows": rows, "total": total}


def mensagens_enviadas_listar(
        fornecedor_id: Optional[int] = None,
        data_ini: Optional[str] = None,
        data_fim: Optional[str] = None,
        destinatario: Optional[str] = None
    ) -> List[Dict[str, Any]]:
    """Lista todas as mensagens enviadas (sem paginação, para exportação)."""
    conn = conectar(); cur = conn.cursor()

    sql = """
        SELECT me.*, f.nome AS fornecedor_nome
        FROM mensagens_enviadas me
        LEFT JOIN fornecedores f ON f.id = me.fornecedor_id
        WHERE 1 = 1
    """
    params = []

    if fornecedor_id:
        sql += " AND me.fornecedor_id = ?"
        params.append(fornecedor_id)
    if data_ini:
        sql += " AND date(me.enviado_em) >= date(?)"
        params.append(data_ini)
    if data_fim:
        sql += " AND date(me.enviado_em) <= date(?)"
        params.append(data_fim)
    if destinatario:
        sql += " AND me.destinatario LIKE ?"
        params.append(f"%{destinatario}%")

    sql += " ORDER BY me.enviado_em DESC"

    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def orcamento_excluir(id_: int) -> None:
    """Exclui um orçamento salvo."""
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM orcamentos WHERE id=?", (id_,))
    conn.commit()
    conn.close()
