from __future__ import annotations
import os, re, hashlib
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date

import pandas as pd  # engine=openpyxl
import sqlite3

import banco

# ======================================================================
#  MAPEAMENTO FLEXÍVEL (AGORA 100% COMPATÍVEL COM SUA PLANILHA REAL)
# ======================================================================
MAPEAMENTO_COLUNAS = {
    # Fornecedor
    "fornecedor_nome": ["fornecedor"],
    "fornecedor_cnpj": ["cnpj"],

    # Número da ATA
    "ata_numero": ["ata", "numero_ata", "pregao", "pregão", "n_ata", "nº_ata"],

    # Vigência – SUA PLANILHA USA APENAS DATA FINAL
    "vigencia_fim": ["vigência", "vigencia", "vigencia_fim", "fim"],

    # Status
    "status": ["status", "status vigencia", "status vigência", "situacao"],

    # >>> CORREÇÃO CONFIRMADA POR VOCÊ <<<
    # cod_aghu = Item
    "cod_aghu": ["item"],

    # nome_item → usa Item OU Nome Genérico
    "nome_item": ["item", "nome genérico", "descricao", "descricao_item"],

    # Quantidade
    "qtde_total": ["quant.", "quantidade", "qtde", "qtd"],

    # Valor unitário
    "vl_unit": ["valor unitário", "valor_unit", "vl_unitario"],

    # Observacao
    "observacao": ["obs envio", "obs", "observacoes", "observação"],
}

# Colunas que podem conter data para modo incremental HOJE
COLUNAS_DATA_LINHA = [
    "data_atualizacao","dt_atualizacao","atualizado_em",
    "data_cadastro","dt_cadastro","criado_em","data"
]

STATUS_DEFAULT = "Em vigência"


# ======================================================================
#  UTILITÁRIOS
# ======================================================================
def _sha1_arquivo(path: str, chunk=1024*1024) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _cnpj_digits(s: Any) -> str:
    return re.sub(r"\D", "", str(s or "").strip())


def _norm(s: Any) -> str:
    return str(s or "").strip()


def _parse_data(s: Any) -> Optional[str]:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    txt = str(s).strip()
    if not txt:
        return None
    # tenta formatos comuns brasileiros
    for fmt in ("%d/%m/%Y","%Y-%m-%d","%d-%m-%Y","%d/%m/%y"):
        try:
            return datetime.strptime(txt, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    # tenta converter data excel/ISO
    d = pd.to_datetime(s, errors="coerce")
    if pd.isna(d):
        return None
    return d.strftime("%Y-%m-%d")


def _parse_float_br(x: Any) -> float:
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        try:
            return float(x)
        except Exception:
            return 0.0
    t = str(x).strip().replace(".", "").replace(",", ".")
    try:
        return float(Decimal(t))
    except Exception:
        return 0.0


# ======================================================================
#  RESOLVER DE COLUNAS (AGORA LIMPINHO E SEM ESTRANHOS)
# ======================================================================
def _resolver_mapeamento(df: pd.DataFrame) -> Dict[str, str]:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    out: Dict[str, str] = {}

    # mapeia cada coluna canônica
    for canon, cand_list in MAPEAMENTO_COLUNAS.items():
        if canon in cols_lower:
            out[canon] = cols_lower[canon]
            continue

        found = None
        for c in [canon] + cand_list:
            key = c.lower().strip()
            if key in cols_lower:
                found = cols_lower[key]
                break
        if found:
            out[canon] = found

    # Colunas obrigatórias (vigência_ini NÃO é obrigatória)
    obrig = ["fornecedor_nome", "ata_numero", "cod_aghu", "nome_item", "qtde_total", "vl_unit"]
    falt = [c for c in obrig if c not in out]

    if falt:
        raise ValueError(
            f"Colunas obrigatórias ausentes: {falt}\n"
            f"Encontradas: {list(df.columns)}"
        )

    return out


def _descobrir_coluna_data(df: pd.DataFrame) -> Optional[str]:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    for k in COLUNAS_DATA_LINHA:
        if k in cols_lower:
            return cols_lower[k]
    return None


# ======================================================================
#  UPSERTS – Fornecedor, ATA e Itens
# ======================================================================
def _fornecedor_upsert(cur: sqlite3.Cursor, nome: str, cnpj: str) -> int:
    nome = _norm(nome)
    cnpj = _cnpj_digits(cnpj)

    # tenta por CNPJ
    if cnpj:
        cur.execute("SELECT id FROM fornecedores WHERE cnpj=? LIMIT 1", (cnpj,))
        r = cur.fetchone()
        if r:
            cur.execute(
                "UPDATE fornecedores SET nome=COALESCE(NULLIF(?,''),nome) WHERE id=?",
                (nome, r["id"])
            )
            return int(r["id"])

    # tenta por nome
    cur.execute("SELECT id FROM fornecedores WHERE nome=? LIMIT 1", (nome,))
    r = cur.fetchone()
    if r:
        if cnpj:
            cur.execute(
                "UPDATE fornecedores SET cnpj=COALESCE(NULLIF(?,''),cnpj) WHERE id=?",
                (cnpj, r["id"])
            )
        return int(r["id"])

    # cria
    cur.execute(
        "INSERT INTO fornecedores (nome, cnpj) VALUES (?,?)",
        (nome, cnpj or None)
    )
    return int(cur.lastrowid)


def _ata_upsert(
    cur: sqlite3.Cursor,
    fornecedor_id: int,
    numero: str,
    vig_ini: Optional[str],
    vig_fim: Optional[str],
    status: Optional[str],
    obs: Optional[str],
) -> int:

    numero = _norm(numero)
    st = _norm(status) or STATUS_DEFAULT

    cur.execute(
        "SELECT id FROM atas WHERE fornecedor_id=? AND numero=? LIMIT 1",
        (fornecedor_id, numero)
    )
    r = cur.fetchone()

    if r:
        cur.execute(
            """
            UPDATE atas SET
                vigencia_ini = COALESCE(?, vigencia_ini),
                vigencia_fim = COALESCE(?, vigencia_fim),
                status       = COALESCE(NULLIF(?,''), status),
                observacao   = COALESCE(NULLIF(?,''), observacao),
                atualizado_em = datetime('now','localtime')
            WHERE id=?
            """,
            (vig_ini, vig_fim, st, _norm(obs), r["id"])
        )
        return int(r["id"])

    # cria
    cur.execute(
        """
        INSERT INTO atas (fornecedor_id, numero, vigencia_ini, vigencia_fim, status, observacao)
        VALUES (?,?,?,?,?,?)
        """,
        (fornecedor_id, numero, vig_ini, vig_fim, st, _norm(obs) or None)
    )
    return int(cur.lastrowid)


def _item_upsert(
    cur: sqlite3.Cursor,
    ata_id: int,
    cod: str,
    nome: str,
    qt: float,
    vu: float,
    vt: float,
    obs: Optional[str],
    atualizar_se_existir: bool,
) -> Tuple[int, bool]:

    cod = _norm(cod)
    cur.execute(
        "SELECT id FROM atas_itens WHERE ata_id=? AND cod_aghu=? LIMIT 1",
        (ata_id, cod)
    )
    r = cur.fetchone()

    if r:
        if atualizar_se_existir:
            cur.execute(
                """
                UPDATE atas_itens SET
                    nome_item = COALESCE(NULLIF(?,''), nome_item),
                    qtde_total=?, vl_unit=?, vl_total=?, observacao=COALESCE(NULLIF(?,''), observacao),
                    atualizado_em = datetime('now','localtime')
                WHERE id=?
                """,
                (_norm(nome), float(qt), float(vu), float(vt), _norm(obs), r["id"])
            )
        return int(r["id"]), False

    # cria
    cur.execute("SELECT fornecedor_id, numero FROM atas WHERE id=?", (ata_id,))
    hdr = cur.fetchone()
    forn_id = hdr["fornecedor_id"]
    pregao = _norm(hdr["numero"])

    cur.execute(
        """
        INSERT INTO atas_itens
            (fornecedor_id, pregao, cod_aghu, nome_item, qtde_total, vl_unit, vl_total, observacao, ata_id)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (forn_id, pregao, cod, _norm(nome), float(qt), float(vu), float(vt),
         _norm(obs) or None, ata_id)
    )
    return int(cur.lastrowid), True


# ======================================================================
#  IMPORTADOR INCREMENTAL
# ======================================================================
def importar_atas_xlsx_incremental(
    caminho_xlsx: str,
    somente_hoje: bool = True,
    atualizar_itens_existentes: bool = False
) -> Dict[str, Any]:

    if not os.path.exists(caminho_xlsx):
        return {"ok": False, "msg": f"Arquivo não encontrado: {caminho_xlsx}"}

    # hash
    hash_atual = _sha1_arquivo(caminho_xlsx)
    estado = banco.etl_estado_obter()

    if not somente_hoje and estado.get("ultimo_hash") == hash_atual:
        return {"ok": True, "msg": "Planilha sem mudanças desde último import.", "stats": {}, "erros": []}

    # lê planilha
    df = pd.read_excel(caminho_xlsx, engine="openpyxl")
    if df.empty:
        return {"ok": True, "msg": "Planilha vazia.", "stats": {}, "erros": []}

    cols = _resolver_mapeamento(df)
    col_data = _descobrir_coluna_data(df)

    # filtra HOJE
    if somente_hoje and col_data:
        serie = pd.to_datetime(df[col_data], errors="coerce")
        hoje = pd.Timestamp(date.today())
        df = df[serie.dt.date == hoje.date()].copy()

    if df.empty and somente_hoje:
        banco.etl_estado_atualizar(hash_atual)
        return {"ok": True, "msg": "Nada 'de hoje' para importar.", "stats": {}, "erros": []}

    conn = banco.conectar()
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    cache_forn = {}
    cache_ataid = {}

    def _forn_id(nome: str, cnpj: str) -> int:
        k = f"{_cnpj_digits(cnpj)}|{_norm(nome)}"
        if k in cache_forn:
            return cache_forn[k]
        fid = _fornecedor_upsert(cur, nome, cnpj)
        cache_forn[k] = fid
        return fid

    def _ata_id(fid: int, numero: str, vi: Optional[str], vf: Optional[str], st: str, obs: str) -> int:
        k = (fid, _norm(numero))
        if k in cache_ataid:
            return cache_ataid[k]
        aid = _ata_upsert(cur, fid, numero, vi, vf, st, obs)
        cache_ataid[k] = aid
        return aid

    stats = {
        "fornecedores_criados": 0,
        "fornecedores_atualizados": 0,
        "atas_criadas": 0,
        "atas_atualizadas": 0,
        "itens_criados": 0,
        "itens_atualizados": 0,
    }
    erros = []

    # ----------------------------
    #  LOOP DAS LINHAS
    # ----------------------------
    try:
        for idx, row in df.iterrows():
            try:
                forn_nome = _norm(row[cols["fornecedor_nome"]])
                forn_cnpj = _cnpj_digits(row.get(cols.get("fornecedor_cnpj",""), ""))
                ata_num   = _norm(row[cols["ata_numero"]])

                # >>> VIGÊNCIA FINAL SOMENTE <<<
                vi = None
                vf = _parse_data(row.get(cols.get("vigencia_fim",""), None))

                st = _norm(row.get(cols.get("status",""), "")) or STATUS_DEFAULT

                cod = _norm(row[cols["cod_aghu"]])
                nom = _norm(row[cols["nome_item"]])
                qt  = _parse_float_br(row[cols["qtde_total"]])
                vu  = _parse_float_br(row[cols["vl_unit"]])
                vt  = qt * vu
                obs = _norm(row.get(cols.get("observacao",""), ""))

                if not (forn_nome and ata_num and cod and nom):
                    raise ValueError("Campos obrigatórios vazios.")

                fid = _forn_id(forn_nome, forn_cnpj)
                aid = _ata_id(fid, ata_num, vi, vf, st, obs)

                atualizar = bool(col_data) and atualizar_itens_existentes
                _, created = _item_upsert(cur, aid, cod, nom, qt, vu, vt, obs, atualizar)
                if created:
                    stats["itens_criados"] += 1
                else:
                    if atualizar:
                        stats["itens_atualizados"] += 1

            except Exception as e:
                erros.append(f"Linha {idx+2}: {e}")

        conn.commit()
        banco.etl_estado_atualizar(hash_atual)

        return {"ok": True, "msg": "Importação incremental concluída.", "stats": stats, "erros": erros}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "msg": f"Falha ao importar: {e}", "stats": stats, "erros": erros}

    finally:
        conn.close()


# ======================================================================
#  MODO AUTOMÁTICO (1ª VEZ = FULL, depois HOJE)
# ======================================================================
def importar_atas_xlsx_auto(
    caminho_xlsx: str,
    atualizar_itens_existentes_no_full: bool = True,
    atualizar_itens_existentes_no_hoje: bool = False,
) -> Dict[str, Any]:

    conn = banco.conectar()
    cur = conn.cursor()
    cur.execute("SELECT EXISTS(SELECT 1 FROM atas LIMIT 1)")
    tem_ata = int(cur.fetchone()[0]) == 1
    conn.close()

    if not tem_ata:
        # primeira importação -> FULL
        return importar_atas_xlsx_incremental(
            caminho_xlsx,
            somente_hoje=False,
            atualizar_itens_existentes=atualizar_itens_existentes_no_full
        )
    else:
        # demais -> HOJE
        return importar_atas_xlsx_incremental(
            caminho_xlsx,
            somente_hoje=True,
            atualizar_itens_existentes=atualizar_itens_existentes_no_hoje
        )
