# importadores/atas_xlsx.py
from __future__ import annotations
import os, re, hashlib
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date

import pandas as pd  # engine=openpyxl
import sqlite3

import banco

# Mapeamento flexível de cabeçalhos (case-insensitive)
MAPEAMENTO_COLUNAS = {
    "fornecedor_nome": ["fornecedor","forn","razao_social","nome_fornecedor"],
    "fornecedor_cnpj": ["cnpj","doc","cpf_cnpj"],
    "ata_numero":      ["numero_ata","pregao","n_ata","nº_ata","n ata"],
    "vigencia_ini":    ["vigencia_inicio","inicio_vigencia","ini_vigencia","ini"],
    "vigencia_fim":    ["vigencia_fim","fim_vigencia","fim"],
    "status":          ["situacao","sit","status_ata"],
    "cod_aghu":        ["codigo_aghu","cod","codigo"],
    "nome_item":       ["descricao","descricao_item","item"],
    "qtde_total":      ["quantidade","qtde","qtd","qt_total"],
    "vl_unit":         ["valor_unit","vl_unitario","preco_unit","valor unit"],
    "observacao":      ["obs","observacoes","observação"],
}
# Colunas candidatas de "data da linha" para filtrar HOJE
COLUNAS_DATA_LINHA = [
    "data_atualizacao","dt_atualizacao","atualizado_em",
    "data_cadastro","dt_cadastro","criado_em","data"
]
STATUS_DEFAULT = "Em vigência"

# ---------- util ----------
def _sha1_arquivo(path: str, chunk=1024*1024) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()

def _cnpj_digits(s: Any) -> str:
    return re.sub(r"\D", "", str(s or "").strip())

def _norm(s: Any) -> str:
    return str(s or "").strip()

def _parse_data(s: Any) -> Optional[str]:
    if s is None or (isinstance(s, float) and pd.isna(s)): return None
    txt = str(s).strip()
    if not txt: return None
    for fmt in ("%d/%m/%Y","%Y-%m-%d","%d-%m-%Y","%d/%m/%y"):
        try: return datetime.strptime(txt, fmt).strftime("%Y-%m-%d")
        except Exception: pass
    d = pd.to_datetime(s, errors="coerce")
    if pd.isna(d): return None
    return d.strftime("%Y-%m-%d")

def _parse_float_br(x: Any) -> float:
    if x is None: return 0.0
    if isinstance(x, (int,float)):
        try: return float(x)
        except Exception: return 0.0
    t = str(x).strip().replace(".","").replace(",",".")
    try: return float(Decimal(t))
    except Exception: return 0.0

def _resolver_mapeamento(df: pd.DataFrame) -> Dict[str,str]:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    out: Dict[str,str] = {}
    for canon, cand in MAPEAMENTO_COLUNAS.items():
        if canon in cols_lower:
            out[canon] = cols_lower[canon]; continue
        achou = None
        for k in [canon] + cand:
            kk = k.lower().strip()
            if kk in cols_lower: achou = cols_lower[kk]; break
        if achou: out[canon] = achou
    obrig = ["fornecedor_nome","ata_numero","cod_aghu","nome_item","qtde_total","vl_unit"]
    falt = [c for c in obrig if c not in out]
    if falt:
        raise ValueError(f"Colunas obrigatórias ausentes: {falt}\nEncontradas: {list(df.columns)}")
    return out

def _descobrir_coluna_data(df: pd.DataFrame) -> Optional[str]:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    for k in COLUNAS_DATA_LINHA:
        if k in cols_lower:
            return cols_lower[k]
    return None

# ---------- upserts SQL (leves) ----------
def _fornecedor_upsert(cur: sqlite3.Cursor, nome: str, cnpj: str) -> int:
    nome = _norm(nome); cnpj = _cnpj_digits(cnpj)
    if cnpj:
        cur.execute("SELECT id FROM fornecedores WHERE cnpj=? LIMIT 1", (cnpj,))
        r = cur.fetchone()
        if r:
            cur.execute("UPDATE fornecedores SET nome=COALESCE(NULLIF(?,''),nome) WHERE id=?", (nome, r["id"]))
            return int(r["id"])
    cur.execute("SELECT id FROM fornecedores WHERE nome=? LIMIT 1", (nome,))
    r = cur.fetchone()
    if r:
        if cnpj:
            cur.execute("UPDATE fornecedores SET cnpj=COALESCE(NULLIF(?,''),cnpj) WHERE id=?", (cnpj, r["id"]))
        return int(r["id"])
    cur.execute("INSERT INTO fornecedores (nome, cnpj) VALUES (?,?)", (nome, cnpj or None))
    return int(cur.lastrowid)

def _ata_upsert(cur: sqlite3.Cursor, fornecedor_id: int, numero: str,
                vig_ini: Optional[str], vig_fim: Optional[str],
                status: Optional[str], obs: Optional[str]) -> int:
    numero = _norm(numero); st = _norm(status) or STATUS_DEFAULT
    cur.execute("SELECT id FROM atas WHERE fornecedor_id=? AND numero=? LIMIT 1", (fornecedor_id, numero))
    r = cur.fetchone()
    if r:
        # ATUALIZAÇÕES LEVES (não pesam)
        cur.execute("""
            UPDATE atas SET
              vigencia_ini = COALESCE(?, vigencia_ini),
              vigencia_fim = COALESCE(?, vigencia_fim),
              status       = COALESCE(NULLIF(?,''), status),
              observacao   = COALESCE(NULLIF(?,''), observacao),
              atualizado_em = datetime('now','localtime')
            WHERE id=?
        """, (vig_ini, vig_fim, st, _norm(obs), r["id"]))
        return int(r["id"])
    cur.execute("""
        INSERT INTO atas (fornecedor_id, numero, vigencia_ini, vigencia_fim, status, observacao)
        VALUES (?,?,?,?,?,?)
    """, (fornecedor_id, numero, vig_ini, vig_fim, st, _norm(obs) or None))
    return int(cur.lastrowid)

def _item_upsert(cur: sqlite3.Cursor, ata_id: int,
                 cod: str, nome: str, qt: float, vu: float, vt: float, obs: Optional[str],
                 atualizar_se_existir: bool) -> Tuple[int, bool]:
    cod = _norm(cod)
    cur.execute("SELECT id FROM atas_itens WHERE ata_id=? AND cod_aghu=? LIMIT 1", (ata_id, cod))
    r = cur.fetchone()
    if r:
        if atualizar_se_existir:
            cur.execute("""
                UPDATE atas_itens SET
                  nome_item = COALESCE(NULLIF(?,''), nome_item),
                  qtde_total=?, vl_unit=?, vl_total=?, observacao=COALESCE(NULLIF(?,''), observacao),
                  atualizado_em = datetime('now','localtime')
                WHERE id=?
            """, (_norm(nome), float(qt), float(vu), float(vt), _norm(obs), r["id"]))
        return int(r["id"]), False
    # completar colunas de compatibilidade
    cur.execute("SELECT fornecedor_id, numero FROM atas WHERE id=?", (ata_id,))
    h = cur.fetchone()
    cur.execute("""
        INSERT INTO atas_itens (fornecedor_id, pregao, cod_aghu, nome_item, qtde_total, vl_unit, vl_total, observacao, ata_id)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (int(h["fornecedor_id"]), _norm(h["numero"]), cod, _norm(nome), float(qt),
          float(vu), float(vt), _norm(obs) or None, ata_id))
    return int(cur.lastrowid), True

# ---------- importador ----------
def importar_atas_xlsx_incremental(
    caminho_xlsx: str,
    somente_hoje: bool = True,
    atualizar_itens_existentes: bool = False
) -> Dict[str, Any]:
    """
    Importa ATAs/itens de uma planilha .xlsx de forma leve:
      - se houver coluna de data -> filtra HOJE;
      - se não houver -> só insere itens/atas novos (não atualiza os antigos), evitando peso.
    Usa hash do arquivo para short-circuit quando útil.
    """
    if not os.path.exists(caminho_xlsx):
        return {"ok": False, "msg": f"Arquivo não encontrado: {caminho_xlsx}"}

    # Short-circuit por hash (se não for 'somente hoje', podemos pular quando hash igual)
    hash_atual = _sha1_arquivo(caminho_xlsx)
    estado = banco.etl_estado_obter()
    if not somente_hoje and estado.get("ultimo_hash") == hash_atual:
        return {"ok": True, "msg": "Planilha sem mudanças desde o último import.", "stats": {}, "erros": []}

    # Carrega planilha
    df = pd.read_excel(caminho_xlsx, engine="openpyxl")
    if df.empty:
        return {"ok": True, "msg": "Planilha vazia.", "stats": {}, "erros": []}

    cols = _resolver_mapeamento(df)
    col_data = _descobrir_coluna_data(df)

    # Filtra HOJE se possível e solicitado
    if somente_hoje and col_data:
        serie = pd.to_datetime(df[col_data], errors="coerce")
        hoje = pd.Timestamp(date.today())
        df = df[serie.dt.date == hoje.date()].copy()

    # Se virou vazio após o filtro: nada a fazer
    if df.empty and somente_hoje:
        banco.etl_estado_atualizar(hash_atual)  # marca execução
        return {"ok": True, "msg": "Nenhuma linha 'de hoje' para importar.", "stats": {}, "erros": []}

    # Para acelerar, se NÃO temos coluna de data, pré-carregamos chaves existentes em memória
    chaves_atas_exist: set[tuple[int, str]] = set()
    chaves_itens_exist: set[tuple[int, str]] = set()
    cache_forn: Dict[str, int] = {}
    cache_ataid_por_forn_num: Dict[tuple[int, str], int] = {}

    conn = banco.conectar()
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    # --- AUTO: 1ª execução = FULL; demais = HOJE ---
    def importar_atas_xlsx_auto(
        caminho_xlsx: str,
        atualizar_itens_existentes_no_full: bool = True,
        atualizar_itens_existentes_no_hoje: bool = False
    ) -> Dict[str, Any]:
        """
        Executa FULL se for a primeira importação (sem ATAs no banco),
        depois executa apenas as linhas do dia (incremental).
        """
        # Detecta "primeira importação" verificando se há dados em 'atas'
        try:
            conn = banco.conectar(); cur = conn.cursor()
            cur.execute("SELECT EXISTS(SELECT 1 FROM atas LIMIT 1)")
            tem_ata = int(cur.fetchone()[0]) == 1
        finally:
            try: conn.close()
            except Exception: pass
    
        if not tem_ata:
            # PRIMEIRA VEZ → FULL
            return importar_atas_xlsx_incremental(
                caminho_xlsx=caminho_xlsx,
                somente_hoje=False,                         # FULL
                atualizar_itens_existentes=atualizar_itens_existentes_no_full
            )
        else:
            # DEMAIS VEZES → HOJE
            return importar_atas_xlsx_incremental(
                caminho_xlsx=caminho_xlsx,
                somente_hoje=True,                          # apenas as linhas de hoje (se houver coluna de data)
                atualizar_itens_existentes=atualizar_itens_existentes_no_hoje
            )

    def _forn_id(nome: str, cnpj: str) -> int:
        key = f"{_cnpj_digits(cnpj)}|{_norm(nome)}"
        if key in cache_forn: return cache_forn[key]
        fid = _fornecedor_upsert(cur, nome, cnpj)
        cache_forn[key] = fid
        return fid

    def _ata_id(fid: int, numero: str, vi: Optional[str], vf: Optional[str], st: str, obs: str) -> int:
        tup = (fid, _norm(numero))
        if tup in cache_ataid_por_forn_num:
            return cache_ataid_por_forn_num[tup]
        aid = _ata_upsert(cur, fid, numero, vi, vf, st, obs)
        cache_ataid_por_forn_num[tup] = aid
        return aid

    stats = {"fornecedores_criados": 0, "atas_criadas": 0, "itens_criados": 0,
             "fornecedores_atualizados": 0, "atas_atualizadas": 0, "itens_atualizados": 0}
    erros: List[str] = []

    try:
        for idx, row in df.iterrows():
            try:
                forn_nome = _norm(row[cols["fornecedor_nome"]])
                forn_cnpj = _cnpj_digits(row.get(cols.get("fornecedor_cnpj",""), ""))
                ata_num   = _norm(row[cols["ata_numero"]])

                vi = _parse_data(row.get(cols.get("vigencia_ini",""), None))
                vf = _parse_data(row.get(cols.get("vigencia_fim",""), None))
                st = _norm(row.get(cols.get("status",""), "")) or STATUS_DEFAULT

                cod = _norm(row[cols["cod_aghu"]])
                nom = _norm(row[cols["nome_item"]])
                qt  = _parse_float_br(row[cols["qtde_total"]])
                vu  = _parse_float_br(row[cols["vl_unit"]])
                vt  = qt * vu
                obs = _norm(row.get(cols.get("observacao",""), ""))

                if not (forn_nome and ata_num and cod and nom):
                    raise ValueError("Campos obrigatórios vazios (fornecedor/ata/código/nome_item).")

                fid = _forn_id(forn_nome, forn_cnpj)
                aid = _ata_id(fid, ata_num, vi, vf, st, obs)

                # Incremental “leve”:
                # - Se não temos coluna de data, não atualizamos itens existentes (evita custo).
                # - Se temos coluna de data (linhas de hoje), podemos atualizar se a flag permitir.
                atualizar = bool(col_data) and atualizar_itens_existentes
                _, created = _item_upsert(cur, aid, cod, nom, qt, vu, vt, obs, atualizar)
                if created: stats["itens_criados"] += 1
                else:
                    if atualizar: stats["itens_atualizados"] += 1

            except Exception as e:
                # Excel conta header na linha 1
                erros.append(f"Linha {idx+2}: {e}")

        conn.commit()
        # Atualiza estado do ETL
        banco.etl_estado_atualizar(hash_atual)
        return {"ok": True, "msg": "Importação incremental concluída.", "stats": stats, "erros": erros}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "msg": f"Falha ao importar: {e}", "stats": stats, "erros": erros}
    finally:
        conn.close()
