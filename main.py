import tkinter as tk
from tkinter import ttk
import sys
import os

# Módulos de telas
from telas.dashboard import Dashboard
from telas.fornecedores import TelaFornecedores
from telas.atas_empenhos import TelaAtasEmpenhos
from telas.notas import TelaNotas
from telas.orcamento import TelaOrcamento

# Corrige caminho quando vira EXE
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

sys.path.append(base_path)


class Sistema(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Controle de Notas e Empenhos")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        self._estilos()
        self._menu_lateral()
        self._area_trabalho()

        # Tela inicial
        self.abrir_dashboard()

    def _estilos(self):
        try:
            self.option_add("*Font", "Segoe UI 10")
        except Exception:
            pass
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

    def _menu_lateral(self):
        self.menu = tk.Frame(self, width=200, bg="#2c3e50")
        self.menu.pack(side="left", fill="y")

        def btn(text, cmd):
            b = tk.Button(self.menu, text=text, command=cmd,
                          bg="#34495e", fg="white", bd=0, padx=12, pady=12,
                          activebackground="#3d566e", activeforeground="white",
                          anchor="w")
            b.pack(fill="x")
            return b

        self.btn_dash = btn("Dashboard", self.abrir_dashboard)
        self.btn_forn = btn("Fornecedores", self.abrir_fornecedores)
        self.btn_atas = btn("Ata / Empenho", self.abrir_atas_empenhos)
        self.btn_notas = btn("Notas Fiscais", self.abrir_notas)
        self.btn_orc = btn("Orçamento", self.abrir_orcamento)

    def _area_trabalho(self):
        self.container = tk.Frame(self, bg="#ecf0f1")
        self.container.pack(side="right", expand=True, fill="both")

    def limpar(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # --------- Navegação ----------
    def abrir_dashboard(self):
        self.limpar()
        tela = Dashboard(self.container)
        tela.pack(fill="both", expand=True)

    def abrir_fornecedores(self):
        self.limpar()
        tela = TelaFornecedores(self.container)
        tela.pack(fill="both", expand=True)

    def abrir_atas_empenhos(self):
        self.limpar()
        tela = TelaAtasEmpenhos(self.container)
        tela.pack(fill="both", expand=True)

    def abrir_notas(self):
        self.limpar()
        tela = TelaNotas(self.container)
        tela.pack(fill="both", expand=True)

    def abrir_orcamento(self):
        self.limpar()
        tela = TelaOrcamento(self.container)
        tela.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = Sistema()
    app.mainloop()
