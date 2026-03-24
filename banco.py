import os
import sqlite3
from typing import List, Dict, Any, Optional, Tuple


# =========================
#  Caminho do banco (UNC)
# =========================
CAMINHO_BANCO = r"\\hc-arquivos.hc.ufpr.br\HC-GERAL\GERAD\DILIH\SESUP\Todos-SESUP\OPME\BD_Notas\notas_novo.db"


# -------------------------
#  Conexão única (FK ON)
# -------------------------
def conectar() -> sqlite3.Connection:
    """Abre conexão SQLite com FK ON e ajustes mínimos apropriados."""
    # Garante que diretório existe (exceto UNC)
    try:
        base_dir = os.path.dirname(CAMINHO_BANCO)
        if base_dir and not os.path.exists(base_dir) and not base_dir.startswith("\\\\"):
            os.makedirs(base_dir, exist_ok=True)
    except Exception:
        pass

    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        cur.execute("PRAGMA foreign_keys = ON;")
    except Exception:
        pass

    return conn


# -------------------------
#  Criar tabelas — DESATIVADO
# -------------------------
def criar_tabelas() -> None:
    """
    DESATIVADO — o schema agora é mantido externamente (DBeaver).
    Esta função não faz nada.
    """
    return


# ===========================================================
#   CRUDs / Consultas — APENAS OPERAÇÃO DE DADOS
# ===========================================================

# ------ Fornecedores ------
def fornecedores_listar(busca: str = "") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    if busca:
        cur.execute("SELECT * FROM fornecedores WHERE nome LIKE ? ORDER BY nome", (f"%{busca}%",))
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
    campos = ("nome","cnpj","contato_vendedor","telefone","email","rua","numero",
              "complemento","bairro","municipio","estado","cep","observacao")
    vals = tuple(d.get(k) for k in campos)

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"INSERT INTO fornecedores ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})",
        vals
    )
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id


def fornecedor_atualizar(id_: int, d: Dict[str, Any]) -> None:
    campos = ("nome","cnpj","contato_vendedor","telefone","email","rua","numero",
              "complemento","bairro","municipio","estado","cep","observacao")
    sets = ", ".join([f"{k}=?" for k in campos])
    vals = tuple(d.get(k) for k in campos) + (id_,)

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"UPDATE fornecedores SET {sets}, atualizado_em=datetime('now','localtime') WHERE id=?",
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
#  ATAS — Cabeçalho
# ===========================================================
def ata_hdr_inserir(d: Dict[str,Any]) -> int:
    campos = ("fornecedor_id","numero","vigencia_ini","vigencia_fim","status","observacao")
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
            atualizado_em = datetime('now','localtime')
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

    # Exclui empenhos ligados a itens
    cur.execute("""
        DELETE FROM empenhos
         WHERE ata_item_id IN (SELECT id FROM atas_itens WHERE ata_id=?)
    """, (ata_id,))

    # Exclui itens
    cur.execute("DELETE FROM atas_itens WHERE ata_id=?", (ata_id,))

    # Exclui a ATA
    cur.execute("DELETE FROM atas WHERE id=?", (ata_id,))
    conn.commit()
    conn.close()


def atas_hdr_listar(fornecedor_id: Optional[int]=None, busca_numero: str="") -> List[Dict[str,Any]]:
    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM vw_saldo_ata_total WHERE 1=1"
    params: List[Any] = []

    if fornecedor_id:
        sql += " AND fornecedor_id=?"
        params.append(fornecedor_id)

    if busca_numero:
        sql += " AND numero LIKE ?"
        params.append(f"%{busca_numero}%")

    sql += " ORDER BY numero DESC, ata_id DESC"
    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def ata_hdr_obter(ata_id: int) -> Optional[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT * FROM atas WHERE id=?", (ata_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ===========================================================
#  ATAS — Itens
# ===========================================================
def ata_item_inserir(d: Dict[str, Any]) -> int:
    campos = ("fornecedor_id","pregao","cod_aghu","nome_item","qtde_total","vl_unit","vl_total","observacao")
    vals = tuple(d.get(k) for k in campos)

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"INSERT INTO atas_itens ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})",
        vals
    )
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id


def ata_item_inserir_v2(d: Dict[str,Any]) -> int:
    ata_id = d.get("ata_id")
    if not ata_id:
        raise ValueError("ata_id é obrigatório.")

    hdr = ata_hdr_obter(int(ata_id))
    if not hdr:
        raise ValueError(f"Ata {ata_id} não encontrada.")

    fornecedor_id = hdr["fornecedor_id"]
    pregao = hdr["numero"]

    campos = (
        "fornecedor_id","pregao","cod_aghu","nome_item","qtde_total","vl_unit",
        "vl_total","observacao","ata_id"
    )
    vals = (
        fornecedor_id, pregao,
        d.get("cod_aghu"), d.get("nome_item"),
        float(d.get("qtde_total") or 0),
        float(d.get("vl_unit") or 0),
        float(d.get("vl_total") or 0),
        d.get("observacao"),
        ata_id
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


def ata_itens_listar(fornecedor_id: Optional[int]=None, busca_cod: str="", busca_pregao: str="") -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    sql = "SELECT * FROM atas_itens WHERE 1=1"
    params = []

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
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def ata_itens_listar_por_ata(ata_id: int) -> List[Dict[str,Any]]:
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
            IFNULL((SELECT SUM(e.qtde) FROM empenhos e WHERE e.ata_item_id = ai.id), 0) AS qtde_empenhada,
            (ai.qtde_total - IFNULL((SELECT SUM(e.qtde) FROM empenhos e WHERE e.ata_item_id = ai.id), 0)) AS qtde_saldo
        FROM atas_itens ai
        WHERE ai.ata_id = ?
        ORDER BY ai.nome_item ASC
    """, (ata_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


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
#   Empenhos
# ===========================================================
def validar_saldo_antes_empenho(ata_item_id: int, qtde_solicitada: float) -> Tuple[bool,str,float]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT 
            qtde_total,
            IFNULL((SELECT SUM(qtde) FROM empenhos WHERE ata_item_id = ?), 0) AS empenhado
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
    campos = ("fornecedor_id","cod_aghu","nome_item","qtde","vl_unit","vl_total","numero_empenho","observacao","ata_item_id")
    vals = (d.get("fornecedor_id"), d.get("cod_aghu"), d.get("nome_item"),
            float(d.get("qtde") or 0), float(d.get("vl_unit") or 0), float(d.get("vl_total") or 0),
            d.get("numero_empenho"), d.get("observacao"), d.get("ata_item_id"))

    conn = conectar(); cur = conn.cursor()
    cur.execute(
        f"INSERT INTO empenhos ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})",
        vals
    )
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id


def empenhos_listar(fornecedor_id: Optional[int]=None, busca_cod: str="", numero_empenho: str="") -> List[Dict[str,Any]]:
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
         WHERE fornecedor_id=? AND IFNULL(numero_empenho,'-') = IFNULL(?, '-')
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
        float(d.get("qtde") or 0), float(d.get("vl_unit") or 0),
        float(d.get("vl_total") or 0), d.get("observacao"),
        d.get("ata_item_id"), item_id
    ))
    conn.commit()
    conn.close()


def empenho_excluir_por_numero(fornecedor_id: int, numero_empenho: str) -> int:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        DELETE FROM empenhos
         WHERE fornecedor_id=? AND IFNULL(numero_empenho,'-')=IFNULL(?, '-')
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


# ===========================================================
#  Notas (cabeçalho + itens)
# ===========================================================
def nota_inserir(d: Dict[str, Any]) -> int:
    campos = ("fornecedor_id","numero","data_expedicao","vl_total","codigo_sei","data_envio_processo","observacao")
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
    """, (
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
    conn.commit()
    conn.close()


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

    cur.execute("UPDATE notas SET vl_total=?, atualizado_em=datetime('now','localtime') WHERE id=?",
                (total, nota_id))
    conn.commit()
    conn.close()
    return total


def nota_listar(fornecedor_id: Optional[int]=None, numero: str="") -> List[Dict[str, Any]]:
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
#  Saldos
# ===========================================================
def saldo_ata_por_fornecedor(fornecedor_id: int) -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT * FROM vw_saldo_ata
        WHERE fornecedor_id=?
        ORDER BY pregao, cod_aghu
    """, (fornecedor_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def saldo_empenho_por_fornecedor(fornecedor_id: int) -> List[Dict[str, Any]]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        SELECT * FROM vw_saldo_empenho
        WHERE fornecedor_id=?
        ORDER BY valor_saldo ASC, empenho_id DESC
    """, (fornecedor_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ===========================================================
#  Orçamentos
# ===========================================================
def orcamento_inserir(d: Dict[str, Any]) -> int:
    campos = ("fornecedor_id","cod_aghu","nome_item","qtde","vl_unit","numero_empenho","observacao","mensagem_email")
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


def orcamentos_listar(fornecedor_id: Optional[int]=None, cod_aghu: str="", numero_empenho: str="") -> List[Dict[str, Any]]:
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


def orcamentos_filtrar(fornecedor_id: Optional[int]=None,
                       data_ini: Optional[str]=None,
                       data_fim: Optional[str]=None,
                       termo: str="",
                       numero_empenho: str="") -> List[Dict[str, Any]]:
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


# ===========================================================
#  Funções auxiliares do ETL
# ===========================================================
def etl_estado_obter() -> Dict[str, Any]:
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT id, fonte, ultimo_hash, ultimo_import_ok FROM etl_estado WHERE id=1")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


def etl_estado_atualizar(ultimo_hash: Optional[str], quando_local: Optional[str]=None) -> None:
    from datetime import datetime
    if not quando_local:
        quando_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = conectar(); cur = conn.cursor()
    cur.execute("""
        UPDATE etl_estado SET ultimo_hash=?, ultimo_import_ok=? WHERE id=1
    """, (ultimo_hash, quando_local))
    conn.commit()
    conn.close()
