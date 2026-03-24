# auth.py
import os
import sqlite3
import hashlib, base64, secrets
from typing import Optional, Dict, Any, Tuple
from banco import conectar  # usa seu conectar() e CAMINHO_BANCO

def auth_init() -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        senha_hash TEXT NOT NULL,
        nome TEXT,
        role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin')),
        is_ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime')),
        CHECK (email LIKE '%@ebserh.gov.br')
    );
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email COLLATE NOCASE);")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessoes (
        id TEXT PRIMARY KEY,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        expira_em TEXT NOT NULL,
        user_agent TEXT,
        ip TEXT
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessoes_usuario ON sessoes(usuario_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessoes_expira ON sessoes(expira_em);")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS auth_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
        email TEXT,
        evento TEXT NOT NULL CHECK (evento IN ('login_success','login_failure','logout')),
        ip TEXT,
        user_agent TEXT,
        criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_auth_audit_email ON auth_audit(email);")
    conn.commit(); conn.close()

def _pepper() -> str:
    return os.environ.get("APP_PEPPER", "")

def _b64e(b: bytes) -> str: return base64.b64encode(b).decode("ascii")
def _b64d(s: str) -> bytes: return base64.b64decode(s.encode("ascii"))

def _hash_senha(senha: str) -> str:
    if not senha: raise ValueError("Senha inválida.")
    salt = os.urandom(16)
    n, r, p, dklen = 2**14, 8, 1, 32
    pwd = (senha + _pepper()).encode("utf-8")
    dk = hashlib.scrypt(pwd, salt=salt, n=n, r=r, p=p, dklen=dklen)
    return f"scrypt${n}${r}${p}${_b64e(salt)}${_b64e(dk)}"

def _verificar_senha(hash_armazenado: str, senha: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, dk_b64 = hash_armazenado.split("$")
        if scheme != "scrypt": return False
        n, r, p = int(n), int(r), int(p)
        salt = _b64d(salt_b64); dk_stored = _b64d(dk_b64)
        pwd = (senha + _pepper()).encode("utf-8")
        dk = hashlib.scrypt(pwd, salt=salt, n=n, r=r, p=p, dklen=len(dk_stored))
        return secrets.compare_digest(dk, dk_stored)
    except Exception:
        return False

def _email_normalizar(email: str) -> str: return (email or "").strip().lower()
def _email_ebserh_valido(email: str) -> bool:
    e = _email_normalizar(email)
    return e.endswith("@ebserh.gov.br") and " " not in e and "@" in e

def _registrar_auditoria(evento: str, usuario_id: Optional[int], email_norm: Optional[str], ip: Optional[str], user_agent: Optional[str]) -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("""INSERT INTO auth_audit (usuario_id, email, evento, ip, user_agent) VALUES (?,?,?,?,?)""",
                (usuario_id, email_norm, evento, ip, user_agent))
    conn.commit(); conn.close()

def _login_bloqueado(email_norm: str, limite=5, janela_min=10) -> Tuple[bool, int]:
    conn = conectar(); cur = conn.cursor()
    cur.execute(f"""
        SELECT COUNT(*)
          FROM auth_audit
         WHERE email = ?
           AND evento = 'login_failure'
           AND datetime(criado_em) >= datetime('now','localtime','-{janela_min} minutes')
    """, (email_norm,))
    falhas = int(cur.fetchone()[0] or 0)
    conn.close()
    return (falhas >= int(limite), falhas)

def _sessoes_limpar_expiradas() -> None:
    conn = conectar(); cur = conn.cursor()
    cur.execute("DELETE FROM sessoes WHERE expira_em < datetime('now','localtime')")
    conn.commit(); conn.close()

def _sessao_criar(usuario_id: int, duracao_horas: int = 8, user_agent: Optional[str] = None, ip: Optional[str] = None) -> str:
    token = secrets.token_urlsafe(32)
    conn = conectar(); cur = conn.cursor()
    cur.execute("""INSERT INTO sessoes (id, usuario_id, expira_em, user_agent, ip)
                   VALUES (?, ?, datetime('now','localtime', ?), ?, ?)""",
                (token, usuario_id, f'+{int(duracao_horas)} hours', user_agent, ip))
    conn.commit(); conn.close()
    return token

def usuario_registrar(email: str, senha: str, nome: Optional[str] = None, role: str = "user") -> int:
    if not _email_ebserh_valido(email):
        raise ValueError("Use um e-mail @ebserh.gov.br válido.")
    if not senha or len(senha) < 10:
        raise ValueError("Senha deve ter ao menos 10 caracteres.")
    email_norm = _email_normalizar(email)
    senha_hash = _hash_senha(senha)
    role = role if role in ("user","admin") else "user"
    conn = conectar(); cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO usuarios (email, senha_hash, nome, role) VALUES (?,?,?,?)""",
                    (email_norm, senha_hash, nome, role))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError as e:
        raise ValueError("E-mail já registrado.") from e
    finally:
        conn.close()

def usuario_login(email: str, senha: str, user_agent: Optional[str] = None, ip: Optional[str] = None) -> Dict[str, Any]:
    email_norm = _email_normalizar(email)
    if not _email_ebserh_valido(email_norm):
        raise ValueError("E-mail inválido.")
    bloqueado, _ = _login_bloqueado(email_norm)
    if bloqueado:
        raise ValueError("Muitas tentativas falhas. Tente novamente mais tarde.")
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT id, email, senha_hash, nome, role, is_ativo FROM usuarios WHERE email = ?", (email_norm,))
    row = cur.fetchone()
    if not row or not row["is_ativo"]:
        _registrar_auditoria("login_failure", None, email_norm, ip, user_agent)
        conn.close(); raise ValueError("Credenciais inválidas.")
    if not _verificar_senha(row["senha_hash"], senha):
        _registrar_auditoria("login_failure", row["id"], email_norm, ip, user_agent)
        conn.close(); raise ValueError("Credenciais inválidas.")
    token = _sessao_criar(row["id"], 8, user_agent, ip)
    cur.execute("UPDATE usuarios SET atualizado_em = datetime('now','localtime') WHERE id = ?", (row["id"],))
    conn.commit(); conn.close()
    _registrar_auditoria("login_success", row["id"], email_norm, ip, user_agent)
    return {"token": token, "usuario": {"id": row["id"], "email": row["email"], "nome": row["nome"], "role": row["role"]}}

def usuario_por_token(token: str) -> Optional[Dict[str, Any]]:
    if not token: return None
    _sessoes_limpar_expiradas()
    conn = conectar(); cur = conn.cursor()
    cur.execute("""SELECT u.id, u.email, u.nome, u.role
                   FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id
                   WHERE s.id = ? AND s.expira_em >= datetime('now','localtime')""", (token,))
    row = cur.fetchone(); conn.close()
    return dict(row) if row else None

def usuario_logout(token: str, ip: Optional[str] = None, user_agent: Optional[str] = None) -> None:
    if not token: return
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT usuario_id FROM sessoes WHERE id = ?", (token,))
    r = cur.fetchone(); uid = r["usuario_id"] if r else None
    cur.execute("DELETE FROM sessoes WHERE id = ?", (token,))
    conn.commit(); conn.close()
    _registrar_auditoria("logout", uid, None, ip, user_agent)

def usuario_alterar_senha(usuario_id: int, senha_atual: str, nova_senha: str) -> None:
    if not nova_senha or len(nova_senha) < 10:
        raise ValueError("Nova senha deve ter ao menos 10 caracteres.")
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT senha_hash FROM usuarios WHERE id = ? AND is_ativo = 1", (usuario_id,))
    row = cur.fetchone()
    if not row: conn.close(); raise ValueError("Usuário não encontrado/ativo.")
    if not _verificar_senha(row["senha_hash"], senha_atual):
        conn.close(); raise ValueError("Senha atual incorreta.")
    novo_hash = _hash_senha(nova_senha)
    cur.execute("UPDATE usuarios SET senha_hash=?, atualizado_em=datetime('now','localtime') WHERE id=?",
                (novo_hash, usuario_id))
    conn.commit(); conn.close()

def seed_admin_se_nao_existir(email_admin: str, senha: str, nome: Optional[str] = "Administrador") -> int:
    if not _email_ebserh_valido(email_admin):
        raise ValueError("E-mail do admin deve ser @ebserh.gov.br.")
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT id FROM usuarios WHERE role='admin' LIMIT 1;")
    r = cur.fetchone()
    if r: conn.close(); return r["id"]
    uid = usuario_registrar(email_admin, senha, nome=nome, role="admin")
    return uid
