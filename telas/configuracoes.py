# telas/configuracoes.py
import tkinter as tk
from tkinter import ttk, messagebox
import utils

class TelaConfiguracoes(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")

        tk.Label(self, text="Configurações de E-mail (SMTP)",
                 font=("Segoe UI", 12, "bold"), bg="white").pack(anchor="w", padx=12, pady=(12, 6))

        corpo = tk.Frame(self, bg="white")
        corpo.pack(fill="x", padx=12)

        def linha(lbl, width=36):
            f = tk.Frame(corpo, bg="white")
            f.pack(fill="x", pady=4)
            tk.Label(f, text=lbl, width=20, anchor="w", bg="white").pack(side="left")
            e = ttk.Entry(f, width=width)
            e.pack(side="left")
            return e

        self.e_servidor = linha("Servidor SMTP:")
        self.e_porta    = linha("Porta (465/587):", width=10)
        self.e_email    = linha("E-mail remetente:")
        self.e_senha    = linha("Senha / App Password:")
        self.e_senha.config(show="•")
        self.e_alerta   = linha("E-mail p/ cópia (opcional):", width=40)

        f_ssl = tk.Frame(corpo, bg="white")
        f_ssl.pack(fill="x", pady=4)
        self.var_ssl = tk.BooleanVar(value=False)
        tk.Label(f_ssl, text="Usar SSL (porta 465):", width=20, anchor="w", bg="white").pack(side="left")
        ttk.Checkbutton(f_ssl, variable=self.var_ssl).pack(side="left")

        # Caminho efetivo do config
        self.lbl_path = tk.Label(self, text=f"Arquivo: {utils.CONFIG_ARQUIVO}", bg="white", fg="#7f8c8d")
        self.lbl_path.pack(anchor="w", padx=12, pady=(2,8))

        botoes = tk.Frame(self, bg="white")
        botoes.pack(fill="x", padx=12, pady=(6,12))
        ttk.Button(botoes, text="Salvar", command=self._salvar).pack(side="left")
        ttk.Button(botoes, text="Testar envio", command=self._testar_envio).pack(side="left", padx=6)

        self._carregar()

    def _carregar(self):
        cfg = utils.carregar_config()
        self.e_servidor.delete(0, "end"); self.e_servidor.insert(0, cfg.get("smtp_servidor",""))
        self.e_porta.delete(0, "end");    self.e_porta.insert(0, str(cfg.get("smtp_porta", 587)))
        self.e_email.delete(0, "end");    self.e_email.insert(0, cfg.get("email",""))
        self.e_senha.delete(0, "end");    self.e_senha.insert(0, cfg.get("senha",""))
        self.e_alerta.delete(0, "end");   self.e_alerta.insert(0, cfg.get("email_alerta",""))
        self.var_ssl.set(bool(cfg.get("usar_ssl", False)))

    def _salvar(self):
        try:
            porta = int(self.e_porta.get() or 0)
        except ValueError:
            messagebox.showwarning("Validação", "Porta inválida.")
            return

        cfg = {
            "smtp_servidor": self.e_servidor.get().strip(),
            "smtp_porta": porta,
            "email": self.e_email.get().strip(),
            "senha": self.e_senha.get(),
            "email_alerta": self.e_alerta.get().strip(),
            "usar_ssl": self.var_ssl.get(),
        }

        if not cfg["smtp_servidor"] or not cfg["email"]:
            messagebox.showwarning("Validação", "Informe servidor SMTP e e-mail remetente.")
            return
        utils.salvar_config(cfg)
        messagebox.showinfo("Configurações", "Configurações salvas com sucesso.")

    def _testar_envio(self):
        # Salva antes de testar
        self._salvar()
        cfg = utils.carregar_config()
        destino = cfg.get("email_alerta") or cfg.get("email")
        if not destino:
            messagebox.showwarning("Teste de envio", "Defina 'e-mail p/ cópia' ou deixe vazio para enviar para o remetente.")
            destino = cfg.get("email")

        html = "<h3>Teste de envio</h3><p>Se você recebeu esta mensagem, seu SMTP está configurado.</p>"
        try:
            utils.enviar_email(destinatarios=destino, assunto="Teste - Configurações SMTP", corpo_html=html)
            messagebox.showinfo("Teste de envio", f"E-mail enviado para: {destino}")
        except Exception as e:
            messagebox.showerror("Teste de envio", f"Falha ao enviar e-mail: {e}")
