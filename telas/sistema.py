# telas/sistema.py
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
import traceback

from auth import usuario_logout  # <<--- IMPORTANTE

from telas.dashboard import Dashboard
from telas.fornecedores import TelaFornecedores
from telas.atas_empenhos import TelaAtasEmpenhos
from telas.notas import TelaNotas
from telas.orcamento import TelaOrcamento
from telas.configuracoes import TelaConfiguracoes

class SistemaWindow(tk.Toplevel):
    def __init__(self, root: tk.Tk, auth: dict, build_tag: str = "build 2026-03-18 11:04"):
        super().__init__(root)

        self.root = root          # Tk da Tela Inicial (vamos reexibir no logout)
        self.auth = auth          # {'token', 'usuario': {...}}

        usuario_label = auth['usuario'].get('nome') or auth['usuario']['email']
        self.title(f"Controle de Notas e Empenhos - {build_tag} — {usuario_label}")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        self._estilos()
        self._menu_lateral()
        self._area_trabalho()

        # Tela inicial
        self.abrir_dashboard()

        # Fechamento da janela principal → comporta como "Sair"
        self.protocol("WM_DELETE_WINDOW", self.sair)

    def _estilos(self):
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=10)
        self.option_add("*Font", default_font)

        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

    def _menu_lateral(self):
        self.menu = tk.Frame(self, width=200, bg="#2c3e50")
        self.menu.pack(side="left", fill="y")

        def btn(text, cmd, bg="#34495e"):
            b = tk.Button(
                self.menu, text=text, command=cmd,
                bg=bg, fg="white", bd=0, padx=12, pady=12,
                activebackground="#3d566e", activeforeground="white",
                anchor="w",
            )
            b.pack(fill="x")
            return b

        self.btn_dash = btn("Dashboard", self.abrir_dashboard)
        self.btn_forn = btn("Fornecedores", self.abrir_fornecedores)
        self.btn_atas = btn("Ata / Empenho", self.abrir_atas_empenhos)
        self.btn_notas = btn("Notas Fiscais", self.abrir_notas)
        self.btn_orc  = btn("Orçamento", self.abrir_orcamento)
        self.btn_conf = btn("Configurações", self.abrir_configuracoes)

        # --- Separador visual
        tk.Frame(self.menu, height=1, bg="#22313f").pack(fill="x", pady=6)

        # --- Botão SAIR (vermelho sutil)
        self.btn_sair = btn("Sair", self.sair, bg="#8e2b2b")

    def _area_trabalho(self):
        self.container = tk.Frame(self, bg="#ecf0f1")
        self.container.pack(side="right", expand=True, fill="both")

    def limpar(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # --------- Navegação ----------
    def _abrir_tela(self, classe_tela, nome_log="tela"):
        self.limpar()
        try:
            tela = classe_tela(self.container)
            tela.pack(fill="both", expand=True)
        except Exception as e:
            log_path = os.path.join(os.path.expanduser("~"), "controle_notas_erro.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n" + "="*80 + "\n")
                f.write(f"Erro ao abrir {nome_log}:\n")
                f.write(traceback.format_exc())

            messagebox.showerror(
                "Erro",
                f"Ocorreu um erro ao abrir a tela '{nome_log}'.\n\n"
                f"{e}\n\n"
                f"Um log foi salvo em:\n{log_path}"
            )

    def abrir_dashboard(self):        self._abrir_tela(Dashboard, "Dashboard")
    def abrir_fornecedores(self):     self._abrir_tela(TelaFornecedores, "Fornecedores")
    def abrir_atas_empenhos(self):    self._abrir_tela(TelaAtasEmpenhos, "Ata/Empenho")
    def abrir_notas(self):            self._abrir_tela(TelaNotas, "Notas")
    def abrir_orcamento(self):        self._abrir_tela(TelaOrcamento, "Orçamento")
    def abrir_configuracoes(self):
        self.limpar()
        tela = TelaConfiguracoes(self.container)
        tela.pack(fill="both", expand=True)

    # --------- SAIR / LOGOUT ----------
    def sair(self):
        """Confirma logout, invalida sessão e volta para a Tela Inicial."""
        if not messagebox.askyesno("Sair", "Deseja realmente sair e encerrar a sessão?"):
            return

        # Tenta invalidadar a sessão no backend
        try:
            token = self.auth.get("token")
            if token:
                usuario_logout(token)
        except Exception:
            # não bloqueia a saída se falhar
            pass

        # Fecha a janela principal
        try:
            self.destroy()
        finally:
            # Reexibe a tela inicial (se estiver oculta)
            if hasattr(self.root, "deiconify"):
                self.root.deiconify()
