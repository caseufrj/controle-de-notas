# utils.py
import json
import os
import sys
import smtplib
import ssl
import mimetypes
from email.message import EmailMessage
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd

# ------------------------------
# Caminho do arquivo de configuração
# ------------------------------

def _dir_config_app() -> str:
    """
    Retorna o diretório apropriado para armazenar config do app.
    - Windows: %APPDATA%\ControleNotas
    - Linux/Mac: ~/.config/controle-notas
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        path = os.path.join(base, "ControleNotas")
    else:
        base = os.path.expanduser("~/.config")
        path = os.path.join(base, "controle-notas")
    os.makedirs(path, exist_ok=True)
    return path

def _path_config() -> str:
    return os.path.join(_dir_config_app(), "config.json")

# Mantém compat com código legado (se houver um config.json no dir atual)
# mas dá preferência ao diretório do usuário.
def _resolver_caminho_config() -> str:
    user_cfg = _path_config()
    local_cfg = os.path.join(os.getcwd(), "config.json")
    if os.path.exists(user_cfg):
        return user_cfg
    if os.path.exists(local_cfg):
        # copia para o diretório do usuário na primeira execução
        try:
            os.makedirs(os.path.dirname(user_cfg), exist_ok=True)
            with open(local_cfg, "rb") as src, open(user_cfg, "wb") as dst:
                dst.write(src.read())
        except Exception:
            return local_cfg
    return user_cfg

CONFIG_ARQUIVO = _resolver_caminho_config()

# ------------------------------
# Configuração
# ------------------------------

def carregar_config() -> Dict[str, Any]:
    """
    Estrutura esperada:
    {
      "smtp_servidor": "",
      "smtp_porta": 587,
      "email": "",
      "senha": "",
      "email_alerta": "",
      "usar_ssl": false  # true para porta 465
    }
    """
    if not os.path.exists(CONFIG_ARQUIVO):
        return {
            "smtp_servidor": "",
            "smtp_porta": 587,
            "email": "",
            "senha": "",
            "email_alerta": "",
            "usar_ssl": False
        }
    try:
        with open(CONFIG_ARQUIVO, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # defaults
        cfg.setdefault("smtp_porta", 587)
        cfg.setdefault("usar_ssl", False)
        cfg.setdefault("email_alerta", "")
        return cfg
    except Exception:
        # Se corrompido, retorna defaults
        return {
            "smtp_servidor": "",
            "smtp_porta": 587,
            "email": "",
            "senha": "",
            "email_alerta": "",
            "usar_ssl": False
        }

def salvar_config(cfg: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CONFIG_ARQUIVO), exist_ok=True)
    with open(CONFIG_ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ------------------------------
# E-mail
# ------------------------------

def _detectar_mime(caminho: str) -> Tuple[str, str]:
    mtype, _enc = mimetypes.guess_type(caminho)
    if mtype is None:
        return ("application", "octet-stream")
    major, minor = mtype.split("/", 1)
    return (major, minor)

def enviar_email(
    destinatarios: List[str] | str,
    assunto: str,
    corpo_html: str,
    anexos: Optional[List[str]] = None
) -> None:
    """
    Envia e-mail usando as credenciais do config.json.
    - Suporta TLS (porta 587) e SSL (porta 465) conforme `usar_ssl`.
    - `destinatarios` pode ser lista ou string única.
    """
    cfg = carregar_config()
    if not cfg.get("smtp_servidor") or not cfg.get("email"):
        raise RuntimeError(
            f"SMTP não configurado. Edite {CONFIG_ARQUIVO} com 'smtp_servidor', 'smtp_porta', 'email' e 'senha'."
        )
    if not cfg.get("senha"):
        raise RuntimeError("Senha do remetente não configurada em config.json.")

    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]
    destinatarios = [d for d in destinatarios if d]  # remove vazios
    if not destinatarios:
        raise ValueError("Nenhum destinatário informado.")

    msg = EmailMessage()
    msg["From"] = cfg["email"]
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = assunto.strip() or "(sem assunto)"
    msg.set_content("Seu cliente de e-mail não suporta HTML.")
    msg.add_alternative(corpo_html or "<p>(sem corpo)</p>", subtype="html")

    # Anexos
    if anexos:
        for caminho in anexos:
            if not caminho or not os.path.exists(caminho):
                continue
            with open(caminho, "rb") as f:
                dados = f.read()
            nome = os.path.basename(caminho)
            major, minor = _detectar_mime(caminho)
            msg.add_attachment(dados, maintype=major, subtype=minor, filename=nome)

    servidor = cfg.get("smtp_servidor")
    porta = int(cfg.get("smtp_porta") or 587)
    usar_ssl = bool(cfg.get("usar_ssl"))

    try:
        if usar_ssl or porta == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(servidor, porta, context=context) as s:
                s.login(cfg["email"], cfg["senha"])
                s.send_message(msg)
        else:
            with smtplib.SMTP(servidor, porta) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.login(cfg["email"], cfg["senha"])
                s.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise RuntimeError(f"Falha de autenticação no SMTP ({servidor}:{porta}) para o remetente {cfg['email']}. Detalhes: {e}") from e
    except smtplib.SMTPConnectError as e:
        raise RuntimeError(f"Falha de conexão ao SMTP ({servidor}:{porta}). Detalhes: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Erro ao enviar e-mail via SMTP ({servidor}:{porta}): {e}") from e

# ------------------------------
# Excel
# ------------------------------

def exportar_excel(dataframes_dict: Dict[str, pd.DataFrame], caminho_saida: str) -> None:
    """
    dataframes_dict: {'Aba1': df1, 'Aba2': df2, ...}
    """
    base_dir = os.path.dirname(caminho_saida)
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)
    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        for aba, df in dataframes_dict.items():
            if not isinstance(df, pd.DataFrame):
                df = pd.DataFrame(list(df))
            df.to_excel(writer, sheet_name=str(aba)[:31], index=False)

def tabela_para_dataframe(linhas: List[Dict[str, Any]], colunas_ordenadas: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Converte uma lista de dicts em DataFrame e reordena colunas se solicitado.
    """
    df = pd.DataFrame(linhas)
    if colunas_ordenadas:
        for c in colunas_ordenadas:
            if c not in df.columns:
                df[c] = ""
        df = df[colunas_ordenadas]
    return df
