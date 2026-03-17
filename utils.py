# utils.py
import json
import os
import smtplib
from email.message import EmailMessage
import pandas as pd

CONFIG_ARQUIVO = "config.json"

def carregar_config():
    if not os.path.exists(CONFIG_ARQUIVO):
        return {"smtp_servidor": "", "smtp_porta": "", "email": "", "senha": "", "email_alerta": ""}
    with open(CONFIG_ARQUIVO, "r", encoding="utf-8") as f:
        return json.load(f)

def enviar_email(destinatarios, assunto, corpo_html, anexos=None):
    cfg = carregar_config()
    if not cfg.get("smtp_servidor") or not cfg.get("email"):
        raise RuntimeError("Configure SMTP e remetente em config.json")

    msg = EmailMessage()
    msg["From"] = cfg["email"]
    msg["To"] = ", ".join(destinatarios if isinstance(destinatarios, list) else [destinatarios])
    msg["Subject"] = assunto
    msg.set_content("Seu cliente de e-mail não suporta HTML.")
    msg.add_alternative(corpo_html, subtype="html")

    if anexos:
        for caminho in anexos:
            with open(caminho, "rb") as f:
                dados = f.read()
            nome = os.path.basename(caminho)
            msg.add_attachment(dados, maintype="application", subtype="octet-stream", filename=nome)

    with smtplib.SMTP(cfg["smtp_servidor"], int(cfg["smtp_porta"])) as s:
        s.starttls()
        s.login(cfg["email"], cfg["senha"])
        s.send_message(msg)

def exportar_excel(dataframes_dict, caminho_saida):
    """
    dataframes_dict: dict { 'Aba1': pd.DataFrame, 'Aba2': df2 }
    """
    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        for aba, df in dataframes_dict.items():
            df.to_excel(writer, sheet_name=aba, index=False)
``
