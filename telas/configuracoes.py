# telas/configuracoes.py
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import utils
# Importadores de ATAs
# Importador novo (FULL + incremental real)
from importadores.atas_xlsx import importar_atas_xlsx
import banco
import tkinter.messagebox as mb

mb.showinfo("DEBUG", f"Banco usado:\n{banco.CAMINHO_BANCO}")

class TelaConfiguracoes(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")

        # -------------------------------
        # Seção: E-mail (SMTP)
        # -------------------------------
        tk.Label(
            self,
            text="Configurações de E-mail (SMTP)",
            font=("Segoe UI", 12, "bold"),
            bg="white",
        ).pack(anchor="w", padx=12, pady=(12, 6))

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
        self.e_porta = linha("Porta (465/587):", width=10)
        self.e_email = linha("E-mail remetente:")
        self.e_senha = linha("Senha / App Password:")
        self.e_senha.config(show="•")
        self.e_alerta = linha("E-mail p/ cópia (opcional):", width=40)

        f_ssl = tk.Frame(corpo, bg="white")
        f_ssl.pack(fill="x", pady=4)
        self.var_ssl = tk.BooleanVar(value=False)
        tk.Label(
            f_ssl, text="Usar SSL (porta 465):", width=20, anchor="w", bg="white"
        ).pack(side="left")
        ttk.Checkbutton(f_ssl, variable=self.var_ssl).pack(side="left")

        # Caminho efetivo do arquivo de config
        self.lbl_path = tk.Label(
            self, text=f"Arquivo: {utils.CONFIG_ARQUIVO}", bg="white", fg="#7f8c8d"
        )
        self.lbl_path.pack(anchor="w", padx=12, pady=(2, 8))

        botoes = tk.Frame(self, bg="white")
        botoes.pack(fill="x", padx=12, pady=(6, 12))
        ttk.Button(botoes, text="Salvar", command=self._salvar).pack(side="left")
        ttk.Button(botoes, text="Testar envio", command=self._testar_envio).pack(
            side="left", padx=6
        )

        # -------------------------------
        # Seção: Importadores / ATAs
        # -------------------------------
        tk.Frame(self, height=1, bg="#e0e0e0").pack(fill="x", padx=12, pady=(4, 8))
        tk.Label(
            self,
            text="Importadores",
            font=("Segoe UI", 12, "bold"),
            bg="white",
        ).pack(anchor="w", padx=12, pady=(0, 6))

        box_imp = tk.Frame(self, bg="white")
        box_imp.pack(fill="x", padx=12, pady=(0, 12))

        ttk.Button(
            box_imp,
            text="Importar ATAs (Automático: 1ª FULL, depois HOJE)",
            command=self._imp_atas_auto,
        ).pack(anchor="w", pady=(0, 4))

        # (opcionais) mantenha se quiser ter os modos manuais
        ttk.Button(
            box_imp,
            text="Importar ATAs (incremental - apenas HOJE)",
            command=self._imp_atas_hoje,
        ).pack(anchor="w", pady=2)

        ttk.Button(
            box_imp,
            text="Importar ATAs (forçar FULL)",
            command=self._imp_atas_full,
        ).pack(anchor="w", pady=2)

        # Carrega os valores do SMTP ao abrir
        self._carregar()

    # -------------------- SMTP --------------------
    def _carregar(self):
        cfg = utils.carregar_config()
        self.e_servidor.delete(0, "end")
        self.e_servidor.insert(0, cfg.get("smtp_servidor", ""))
        self.e_porta.delete(0, "end")
        self.e_porta.insert(0, str(cfg.get("smtp_porta", 587)))
        self.e_email.delete(0, "end")
        self.e_email.insert(0, cfg.get("email", ""))
        self.e_senha.delete(0, "end")
        self.e_senha.insert(0, cfg.get("senha", ""))
        self.e_alerta.delete(0, "end")
        self.e_alerta.insert(0, cfg.get("email_alerta", ""))
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
            messagebox.showwarning(
                "Validação", "Informe servidor SMTP e e-mail remetente."
            )
            return

        utils.salvar_config(cfg)
        messagebox.showinfo("Configurações", "Configurações salvas com sucesso.")

    def _testar_envio(self):
        # Salva antes de testar
        self._salvar()
        cfg = utils.carregar_config()
        destino = cfg.get("email_alerta") or cfg.get("email")
        if not destino:
            messagebox.showwarning(
                "Teste de envio",
                "Defina 'e-mail p/ cópia' ou deixe vazio para enviar para o remetente.",
            )
            return

        # HTML real (sem entidades)
        html = (
            "<h3>Teste de envio</h3>"
            "<p>Se você recebeu esta mensagem, seu SMTP está configurado.</p>"
        )
        try:
            # garantir lista de destinatários
            dest_list = [destino] if isinstance(destino, str) else destino
            utils.enviar_email(
                destinatarios=dest_list,
                assunto="Teste - Configurações SMTP",
                corpo_html=html,
            )
            messagebox.showinfo("Teste de envio", f"E-mail enviado para: {destino}")
        except Exception as e:
            messagebox.showerror("Teste de envio", f"Falha ao enviar e-mail: {e}")

    # ----------------- Importadores / ATAs -----------------
    def _imp_atas_auto(self):
        import tkinter.messagebox as mb
        from tkinter.filedialog import askopenfilename
    
        caminho = askopenfilename(
            title="Selecione a planilha de ATAs",
            filetypes=[("Excel", "*.xlsx")],
        )
    
        if not caminho:
            return
    
        try:
            # nova função, sempre FULL (e incremental real internamente)
            from importadores.atas_xlsx import importar_atas_xlsx
            r = importar_atas_xlsx(caminho)
    
            msg = (
                f"Importação concluída.\n\n"
                f"Fornecedores: {r['stats'].get('fornecedores', '?')}\n"
                f"ATAs: {r['stats'].get('atas', '?')}\n"
                f"Itens criados: {r['stats'].get('itens_criados', '?')}\n"
                f"Itens atualizados: {r['stats'].get('itens_atualizados', '?')}\n"
            )
    
            if r.get("erros"):
                msg += f"\nForam encontrados {len(r['erros'])} erros.\n"
            
            mb.showinfo("Importar ATAs", msg)
    
        except Exception as e:
            mb.showerror("Erro ao importar ATAs", str(e))

    def _imp_atas_hoje(self):
        import tkinter.messagebox as mb
        from tkinter import filedialog
    
        arq = filedialog.askopenfilename(
            title="Selecione a planilha de ATAs (.xlsx)",
            filetypes=[("Excel", "*.xlsx")],
        )
    
        if not arq:
            return
    
        try:
            from importadores.atas_xlsx import importar_atas_xlsx
            res = importar_atas_xlsx(arq)
            self._mostrar_resultado_import(res)
    
        except Exception as e:
            mb.showerror("Erro", f"Falha ao importar ATAs:\n{e}")

    def _imp_atas_full(self):
        import tkinter.messagebox as mb
        from tkinter import filedialog
    
        arq = filedialog.askopenfilename(
            title="Selecione a planilha de ATAs (.xlsx)",
            filetypes=[("Excel", "*.xlsx")],
        )
    
        if not arq:
            return
    
        try:
            from importadores.atas_xlsx import importar_atas_xlsx
            res = importar_atas_xlsx(arq)
            self._mostrar_resultado_import(res)
    
        except Exception as e:
            mb.showerror("Erro", f"Falha ao importar ATAs:\n{e}")

    def _mostrar_resultado_import(self, res: dict):
        if not res.get("ok"):
            messagebox.showerror(
                "Importar ATAs", res.get("msg") or "Falha ao importar."
            )
            return

        st = res.get("stats", {})
        msg = (
            f"{res.get('msg','Importação concluída')}\n\n"
            f"Fornecedores:  +{st.get('fornecedores_criados',0)} / "
            f"{st.get('fornecedores_atualizados',0)} atualizados\n"
            f"ATAs:          +{st.get('atas_criadas',0)} / "
            f"{st.get('atas_atualizadas',0)} atualizadas\n"
            f"Itens:         +{st.get('itens_criados',0)} / "
            f"{st.get('itens_atualizados',0)} atualizados\n"
        )

        if res.get("erros"):
            msg += f"\nOcorreram {len(res['erros'])} linha(s) com problema(s)."
            try:
                log_path = os.path.join(
                    os.path.expanduser("~"), "import_atas_erros.log"
                )
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(res["erros"]))
                msg += f"\nLog: {log_path}"
            except Exception:
                pass

        messagebox.showinfo("Importar ATAs", msg)
