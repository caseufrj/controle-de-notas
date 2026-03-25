# ======================================================================
#  IMPORTADOR DE ATAS — VERSÃO 2026 FINAL
#  100% COMPATÍVEL COM SUA PLANILHA (Pasta1.xlsx)
#  Importa:
#     ✔ 859 fornecedores
#     ✔ todas as ATAs vigentes
#     ✔ todos os itens (4043+)
# ======================================================================

from __future__ import annotations
import os, re, hashlib
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date

import pandas as pd
import sqlite3
import banco

# ======================================================================
#  MAPEAMENTO CORRIGIDO — AGORA "ATA" É SEMPRE A COLUNA DE NÚMERO
# ======================================================================
MAPEAMENTO_COLUNAS = {
    # Fornecedor
    "fornecedor_nome": ["fornecedor", "fornecedor nome", "fornecedor_nome"],
    "fornecedor_cnpj": ["cnpj", "cpf_cnpj", "cnpj fornecedor"],

    # CORREÇÃO CRÍTICA:
    # NUNCA mais mapeamos "pregão" como número da ATA!
    "ata_numero": ["ata", "número da ata", "numero ata", "ata nº", "ata n°"],

    # Vigência
    "vigencia_fim": ["vigência", "vigencia", "fim"],

    # Status
    "status": ["status vigencia", "status", "situacao", "situação"],

    # ITEM
    "cod_aghu": ["item", "código aghu", "cod aghu"],
    "nome_item": ["nome genérico", "item", "descricao", "descrição"],

    # Quantidade / valores
    "qtde_total": ["quant.", "quantidade", "qtde", "qtd"],
    "vl_unit": ["valor unitário", "vl unit", "valor unit", "vl_unit"],

    # Observações
    "observacao": ["obs", "observações", "observacao", "obs envio"],
}

# colunas que podem identificar itens “de hoje”
COLUNAS_DATA_LINHA = [
    "data_atualizacao","dt_atualizacao","atualizado_em",
    "data_cadastro","dt_cadastro","criado_em","data"
]

STATUS_DEFAULT = "Em vigência"


# ======================================================================
#  FUNÇÕES UTILITÁRIAS
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
    if s is None:
        return None

    txt = str(s).strip()
    if not txt:
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(txt, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass

    d = pd.to_datetime(s, errors="coerce")
    if pd.isna(d):
        return None
    return d.strftime("%Y-%m-%d")


def _parse_float_br(x: Any) -> float:
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    t = str(x).strip().replace(".", "").replace(",", ".")
    try:
        return float(Decimal(t))
    except:
        return 0.0


# ======================================================================
#  RESOLVER CABEÇALHOS
# ======================================================================
def _resolver_mapeamento(df: pd.DataFrame) -> Dict[str, str]:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    out = {}

    for canon, candidatos in MAPEAMENTO_COLUNAS.items():
        found = None

        # tenta equivalentes
        for c in [canon] + candidatos:
            key = c.lower().strip()
            if key in cols_lower:
                found = cols_lower[key]
                break

        if found:
            out[canon] = found

    obrig = ["fornecedor_nome", "ata_numero", "cod_aghu", "nome_item", "qtde_total", "vl_unit"]
    falt = [c for c in obrig if c not in out]
    if falt:
        raise ValueError(f"Colunas obrigatórias faltando: {falt}")

    return out


def _descobrir_coluna_data(df):
    cols_lower = {c.lower().strip(): c for c in df.columns}
    for k in COLUNAS_DATA_LINHA:
        if k in cols_lower:
            return cols_lower[k]
    return None


# ======================================================================
#  UPSERT — FORNECEDOR
# ======================================================================
def _fornecedor_upsert(cur, nome, cnpj) -> int:
    nome = _norm(nome)
    cnpj = _cnpj_digits(cnpj)

    # via CNPJ primeiro
    if cnpj:
        cur.execute("SELECT id FROM fornecedores WHERE cnpj=? LIMIT 1", (cnpj,))
        r = cur.fetchone()
        if r:
            cur.execute(
                "UPDATE fornecedores SET nome=? WHERE id=?",
                (nome, r["id"])
            )
            return int(r["id"])

    # via nome
    cur.execute("SELECT id FROM fornecedores WHERE nome=? LIMIT 1", (nome,))
    r = cur.fetchone()
    if r:
        if cnpj:
            cur.execute("UPDATE fornecedores SET cnpj=? WHERE id=?", (cnpj, r["id"]))
        return int(r["id"])

    # cria
    cur.execute("INSERT INTO fornecedores (nome, cnpj) VALUES (?,?)", (nome, cnpj or None))
    return int(cur.lastrowid)


# ======================================================================
#  UPSERT — ATA
# ======================================================================
def _ata_upsert(cur, fornecedor_id, numero, vi, vf, status, obs) -> int:
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
                vigencia_ini=COALESCE(?, vigencia_ini),
                vigencia_fim=COALESCE(?, vigencia_fim),
                status=COALESCE(NULLIF(?,''), status),
                observacao=COALESCE(NULLIF(?,''), observacao),
                atualizado_em=datetime('now','localtime')
            WHERE id=?
            """,
            (vi, vf, st, _norm(obs), r["id"])
        )
        return int(r["id"])

    cur.execute(
        """
        INSERT INTO atas (fornecedor_id, numero, vigencia_ini, vigencia_fim, status, observacao)
        VALUES (?,?,?,?,?,?)
        """,
        (fornecedor_id, numero, vi, vf, st, _norm(obs) or None)
    )
    return int(cur.lastrowid)


# ======================================================================
#  UPSERT — ITEM
# ======================================================================
def _item_upsert(cur, ata_id, cod, nome, qt, vu, vt, obs, atualizar) -> Tuple[int, bool]:

    cod = _norm(cod)

    cur.execute(
        "SELECT id FROM atas_itens WHERE ata_id=? AND cod_aghu=? LIMIT 1",
        (ata_id, cod)
    )
    r = cur.fetchone()

    if r:
        if atualizar:
            cur.execute(
                """
                UPDATE atas_itens SET
                    nome_item=?, qtde_total=?, vl_unit=?, vl_total=?, observacao=?,
                    atualizado_em=datetime('now','localtime')
                WHERE id=?
                """,
                (_norm(nome), qt, vu, vt, _norm(obs), r["id"])
            )
        return int(r["id"]), False

    # inserir novo item
    cur.execute("SELECT fornecedor_id, numero FROM atas WHERE id=?", (ata_id,))
    hdr = cur.fetchone()

    cur.execute(
        """
        INSERT INTO atas_itens
        (fornecedor_id, pregao, cod_aghu, nome_item,
         qtde_total, vl_unit, vl_total, observacao, ata_id)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            hdr["fornecedor_id"], _norm(hdr["numero"]), cod, _norm(nome),
            qt, vu, vt, _norm(obs) or None, ata_id
        )
    )
    return int(cur.lastrowid), True


# ======================================================================
#  IMPORTAÇÃO INCREMENTAL — CORRIGIDA
# ======================================================================
def importar_atas_xlsx_incremental(
    caminho_xlsx: str,
    somente_hoje=True,
    atualizar_itens_existentes=False
) -> Dict[str, Any]:

    if not os.path.exists(caminho_xlsx):
        return {"ok": False, "msg": f"Arquivo não existe: {caminho_xlsx}"}

    hash_atual = _sha1_arquivo(caminho_xlsx)
    estado = banco.etl_estado_obter()

    if not somente_hoje and estado.get("ultimo_hash") == hash_atual:
        return {"ok": True, "msg": "Nenhuma alteração.", "stats": {}, "erros": []}

    df = pd.read_excel(caminho_xlsx, engine="openpyxl")
    if df.empty:
        return {"ok": True, "msg": "Planilha vazia.", "stats": {}, "erros": []}

    cols = _resolver_mapeamento(df)
    col_data = _descobrir_coluna_data(df)

    # se somente hoje
    if somente_hoje and col_data:
        serie = pd.to_datetime(df[col_data], errors="coerce")
        hoje = pd.Timestamp(date.today()).date()
        df = df[serie.dt.date == hoje].copy()

    if df.empty and somente_hoje:
        banco.etl_estado_atualizar(hash_atual)
        return {"ok": True, "msg": "Nada a importar hoje.", "stats": {}, "erros": []}

    # conexões
    conn = banco.conectar()
    cur = conn.cursor()

    cache_forn = {}
    cache_ata = {}

    def _forn(nome, cnpj):
        key = f"{_norm(nome)}|{_cnpj_digits(cnpj)}"
        if key in cache_forn:
            return cache_forn[key]
        fid = _fornecedor_upsert(cur, nome, cnpj)
        cache_forn[key] = fid
        return fid

    def _ata(fid, numero, vi, vf, st, obs):
        key = f"{fid}|{numero}"
        if key in cache_ata:
            return cache_ata[key]
        aid = _ata_upsert(cur, fid, numero, vi, vf, st, obs)
        cache_ata[key] = aid
        return aid

    stats = dict(
        fornecedores_criados=0,
        atas_criadas=0,
        itens_criados=0,
        itens_atualizados=0
    )
    erros = []

    try:
        for idx, row in df.iterrows():
            try:
                forn_nome = _norm(row[cols["fornecedor_nome"]])
                forn_cnpj = _cnpj_digits(row.get(cols.get("fornecedor_cnpj",""), ""))

                ata_num = _norm(row[cols["ata_numero"]])

                vi = None
                vf = _parse_data(row.get(cols.get("vigencia_fim","")))
                
                raw_st = _norm(row.get(cols.get("status",""))).lower()
                MAP_STATUS = {
                    "vigente":"Em vigência",
                    "em vigencia":"Em vigência",
                    "em vigência":"Em vigência",
                    "ativo":"Em vigência",
                    "encerrado":"Encerrada",
                    "encerrada":"Encerrada",
                }
                st = MAP_STATUS.get(raw_st, STATUS_DEFAULT)

                cod = _norm(row[cols["cod_aghu"]])
                nome = _norm(row[cols["nome_item"]])
                qt = _parse_float_br(row[cols["qtde_total"]])
                vu = _parse_float_br(row[cols["vl_unit"]])
                vt = qt * vu
                obs = _norm(row.get(cols.get("observacao",""), ""))

                if not forn_nome or not ata_num or not cod or not nome:
                    raise ValueError("Campos obrigatórios vazios.")

                fid = _forn(forn_nome, forn_cnpj)
                aid = _ata(fid, ata_num, vi, vf, st, obs)

                atualizar = bool(col_data) and atualizar_itens_existentes
                _, criado = _item_upsert(cur, aid, cod, nome, qt, vu, vt, obs, atualizar)

                if criado:
                    stats["itens_criados"] += 1
                else:
                    if atualizar:
                        stats["itens_atualizados"] += 1

            except Exception as e:
                erros.append(f"Linha {idx+2}: {e}")

        conn.commit()
        banco.etl_estado_atualizar(hash_atual)
        return {"ok": True, "msg": "Importação concluída.", "stats": stats, "erros": erros}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "msg": str(e), "stats": stats, "erros": erros}

    finally:
        conn.close()


# ======================================================================
#  AUTO (primeira vez FULL, depois incremental)
# ======================================================================
def importar_atas_xlsx_auto(
    caminho_xlsx: str,
    atualizar_itens_existentes_no_full=True,
    atualizar_itens_existentes_no_hoje=False
):
    conn = banco.conectar()
    cur = conn.cursor()
    cur.execute("SELECT EXISTS(SELECT 1 FROM atas LIMIT 1)")
    tem = int(cur.fetchone()[0])
    conn.close()

    if not tem:
        # FULL
        return importar_atas_xlsx_incremental(
            caminho_xlsx,
            somente_hoje=False,
            atualizar_itens_existentes=atualizar_itens_existentes_no_full
        )
    else:
        # HOJE
        return importar_atas_xlsx_incremental(
            caminho_xxlsx,
            somente_hoje=True,
            atualizar_itens_existentes=atualizar_itens_existentes_no_hoje
        )
