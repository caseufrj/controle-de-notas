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
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

import pandas as pd
import sqlite3

import banco

# ======================================================================
#  MAPEAMENTO DEFINITIVO
# ======================================================================
MAPEAMENTO_COLUNAS = {
    "fornecedor_nome": ["fornecedor"],
    "fornecedor_cnpj": ["cnpj"],
    "ata_numero": ["ata", "número da ata", "numero da ata"],     # <-- CORREÇÃO CRÍTICA
    "vigencia_fim": ["vigência", "vigencia"],
    "status": ["status", "status vigencia", "status vigência"],
    "cod_aghu": ["item", "cod aghu", "codigo aghu"],
    "nome_item": ["nome genérico", "item", "descricao"],
    "qtde_total": ["quant.", "qtde", "quantidade"],
    "vl_unit": ["valor unitário", "valor unit", "vl unit"],
    "observacao": ["obs", "observações", "obs envio"],
}

STATUS_DEFAULT = "Em vigência"

# ======================================================================
#  UTILITÁRIOS
# ======================================================================
# ============================================================
# CARREGA MAPA DE E-MAILS A PARTIR DA ABA "Planilha1 (2)"
# ============================================================
def carregar_emails_planilha(caminho_arquivo: str) -> dict:
    try:
        df_em = pd.read_excel(
            caminho_arquivo,
            sheet_name="Planilha1 (2)",
            engine="openpyxl"
        )
    except Exception:
        return {}

    # Normalizar cabeçalhos
    df_em.columns = df_em.columns.str.strip().str.upper()

    map_email = {}

    for _, row in df_em.iterrows():
        cnpj = re.sub(r"\D", "", str(row.get("CNPJ", "")))
        if not cnpj:
            continue

        emails = []
        for col in ["EMAIL", "EMAIL CORRETO", "OBS ENVIO"]:
            if col in df_em.columns:
                v = str(row.get(col, "")).strip()
                if v and v.lower() != "nan":
                    emails.append(v)

        map_email[cnpj] = ";".join(emails)

    return map_email

def _norm(s: Any) -> str:
    return str(s or "").strip()

def _cnpj_digits(s: Any) -> str:
    return re.sub(r"\D", "", str(s or ""))

def _parse_data(x: Any) -> Optional[str]:
    if pd.isna(x):
        return None
    try:
        dt = pd.to_datetime(x, dayfirst=True)
        return dt.strftime("%Y-%m-%d")
    except:
        return None

def _parse_float(x: Any) -> float:
    if x is None or x == "":
        return 0.0
    return float(str(x).replace(".", "").replace(",", ".") or 0)

# ======================================================================
#  RESOLVE CABEÇALHOS DA PLANILHA
# ======================================================================
def _resolver_mapeamento(df: pd.DataFrame) -> Dict[str, str]:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    out = {}

    for canon, candidatos in MAPEAMENTO_COLUNAS.items():
        found = None
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
        raise ValueError(f"Colunas obrigatórias ausentes: {falt}")

    return out

# ======================================================================
#  UPSERTS
# ======================================================================
def _fornecedor_upsert(cur: sqlite3.Cursor, nome: str, cnpj: str) -> int:
    nome = _norm(nome)
    cnpj = _cnpj_digits(cnpj)

    # Tenta achar por CNPJ
    if cnpj:
        cur.execute("SELECT id FROM fornecedores WHERE cnpj=? LIMIT 1", (cnpj,))
        r = cur.fetchone()
        if r:
            cur.execute("UPDATE fornecedores SET nome=? WHERE id=?", (nome, r["id"]))
            return r["id"]

    # Tenta achar por nome
    cur.execute("SELECT id FROM fornecedores WHERE nome=? LIMIT 1", (nome,))
    r = cur.fetchone()
    if r:
        if cnpj:
            cur.execute("UPDATE fornecedores SET cnpj=? WHERE id=?", (cnpj, r["id"]))
        return r["id"]

    # Criar novo
    cur.execute("INSERT INTO fornecedores (nome, cnpj) VALUES (?,?)", (nome, cnpj or None))
    return cur.lastrowid

def _ata_upsert(cur, fornecedor_id, numero, vig_fim, status, obs):
    numero = _norm(numero)
    status = _norm(status) or STATUS_DEFAULT

    cur.execute("SELECT id FROM atas WHERE fornecedor_id=? AND numero=? LIMIT 1",
                (fornecedor_id, numero))
    r = cur.fetchone()

    if r:
        cur.execute("""
            UPDATE atas SET
                vigencia_fim=COALESCE(?, vigencia_fim),
                status=?,
                observacao=COALESCE(NULLIF(?,''), observacao),
                atualizado_em=datetime('now','localtime')
            WHERE id=?
        """, (vig_fim, status, obs, r["id"]))
        return r["id"]

    cur.execute("""
        INSERT INTO atas (fornecedor_id, numero, vigencia_fim, status, observacao)
        VALUES (?,?,?,?,?)
    """, (fornecedor_id, numero, vig_fim, status, obs or None))

    return cur.lastrowid

def _item_upsert(cur, ata_id, cod, nome, qt, vu, vt, obs):
    cod = _norm(cod)
    cur.execute("SELECT id FROM atas_itens WHERE ata_id=? AND cod_aghu=? LIMIT 1",
                (ata_id, cod))
    r = cur.fetchone()

    if r:
        cur.execute("""
            UPDATE atas_itens SET
                nome_item=?, qtde_total=?, vl_unit=?, vl_total=?,
                observacao=COALESCE(NULLIF(?,''), observacao),
                atualizado_em=datetime('now','localtime')
            WHERE id=?
        """, (nome, qt, vu, vt, obs, r["id"]))
        return False

    cur.execute("SELECT fornecedor_id, numero FROM atas WHERE id=?", (ata_id,))
    hdr = cur.fetchone()

    cur.execute("""
        INSERT INTO atas_itens
        (fornecedor_id, pregao, cod_aghu, nome_item,
         qtde_total, vl_unit, vl_total, observacao, ata_id)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        hdr["fornecedor_id"], hdr["numero"], cod, nome,
        qt, vu, vt, obs or None, ata_id
    ))
    return True

# ======================================================================
#  IMPORTAÇÃO COMPLETA E INCREMENTAL REAL
# ======================================================================
def importar_atas_xlsx(caminho: str) -> Dict[str, Any]:

    if not os.path.exists(caminho):
        return {"ok": False, "msg": "Arquivo não encontrado"}

    df = pd.read_excel(caminho, engine="openpyxl")
    # ------ carregar mapa de e-mails ------
    map_emails = carregar_emails_planilha(caminho)

    if df.empty:
        return {"ok": False, "msg": "Planilha vazia"}

    cols = _resolver_mapeamento(df)

    conn = banco.conectar()
    cur = conn.cursor()

    stats = dict(fornecedores=0, atas=0, itens_criados=0, itens_atualizados=0)
    erros = []

    cache_f = {}
    cache_a = {}

    try:
        for idx, row in df.iterrows():
            try:
                nome_f = _norm(row[cols["fornecedor_nome"]])
                cnpj_f = _cnpj_digits(row.get(cols.get("fornecedor_cnpj",""), ""))

                ata_num = _norm(row[cols["ata_numero"]])
                vig_fim = _parse_data(row.get(cols.get("vigencia_fim","")))
                # -------------------------------------------
                # NORMALIZAÇÃO DO STATUS (CORREÇÃO DO ERRO)
                # -------------------------------------------
                _status_raw = _norm(row.get(cols.get("status",""))).lower()
                _status_raw = _status_raw.replace("\n", "").replace("\r", "").replace("\t", "").strip()
                
                if _status_raw in ("vigente", "em vigencia", "em vigência"):
                    status = "Em vigência"
                elif _status_raw in ("encerrada", "encerrado", "não", "nao", ""):
                    status = "Encerrada"
                elif _status_raw.startswith("renov"):
                    status = "Renovada"
                else:
                    status = "Em vigência"
                    
                obs = _norm(row.get(cols.get("observacao","")))

                cod = _norm(row[cols["cod_aghu"]])
                nome = _norm(row[cols["nome_item"]])
                qt = _parse_float(row[cols["qtde_total"]])
                vu = _parse_float(row[cols["vl_unit"]])
                vt = qt * vu

                # Fornecedor
                key_f = (nome_f, cnpj_f)
                if key_f in cache_f:
                    fid = cache_f[key_f]
                else:
                    # ========================
                    # FORNECEDOR COM E-MAIL
                    # ========================
                    email_planilha = map_emails.get(cnpj_f, "").strip()
                    
                    # tentar upsert normal
                    fid = _fornecedor_upsert(cur, nome_f, cnpj_f)
                    
                    # atualizar e-mail se ainda não existir no banco
                    cur.execute("SELECT email FROM fornecedores WHERE id=?", (fid,))
                    rmail = cur.fetchone()
                    
                    email_atual = (rmail["email"] or "").strip() if rmail else ""
                    
                    # se o banco não tinha e-mail e a planilha tem, atualizar
                    if not email_atual and email_planilha:
                        cur.execute(
                            "UPDATE fornecedores SET email=? WHERE id=?",
                            (email_planilha, fid)
                        )
                    
                    cache_f[key_f] = fid

                # ATA
                key_a = (fid, ata_num)
                if key_a in cache_a:
                    aid = cache_a[key_a]
                else:
                    aid = _ata_upsert(cur, fid, ata_num, vig_fim, status, obs)
                    cache_a[key_a] = aid

                # ITEM
                criou = _item_upsert(cur, aid, cod, nome, qt, vu, vt, obs)
                if criou:
                    stats["itens_criados"] += 1
                else:
                    stats["itens_atualizados"] += 1

            except Exception as e:
                erros.append(f"Linha {idx+2}: {e}")

        conn.commit()
        return {"ok": True, "msg": "Importação concluída", "stats": stats, "erros": erros}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "msg": str(e), "stats": stats, "erros": erros}

    finally:
        conn.close()
