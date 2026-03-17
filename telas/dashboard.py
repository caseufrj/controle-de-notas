# telas/dashboard.py
import tkinter as tk
from tkinter import ttk, messagebox
import banco


class Dashboard(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")
        banco.criar_tabelas()

        # Topo: seleção de fornecedor
        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=16, pady=12)

        tk.Label(topo, text="Fornecedor:", bg="white").pack(side="left")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.pack(side="left", padx=8)
        self.cb_fornec.bind("<<ComboboxSelected>>", lambda e: self.atualizar_listas())

        btn_refresh = ttk.Button(topo, text="Atualizar", command=self.atualizar_listas)
        btn_refresh.pack(side="left", padx=8)

        # Split: Saldos Ata / Saldos Empenho
        split = tk.Frame(self, bg="white")
        split.pack(fill="both", expand=True, padx=16, pady=8)

        # ---- Saldos Ata ----
        lf_ata = ttk.LabelFrame(split, text="Saldo de ATA (quantidade)")
        lf_ata.pack(side="left", fill="both", expand=True, padx=(0,8))

        cols_ata = ("pregao","cod_aghu","nome_item","qtde_total","qtde_usada","qtde_saldo")
        self.tv_ata = ttk.Treeview(lf_ata, columns=cols_ata, show="headings", height=12)
        for c in cols_ata:
            self.tv_ata.heading(c, text=c)
            self.tv_ata.column(c, width=120, anchor="w")
        self.tv_ata.pack(fill="both", expand=True)

        # ---- Saldos Empenho ----
        lf_emp = ttk.LabelFrame(split, text="Saldo de Empenhos (valor)")
        lf_emp.pack(side="left", fill="both", expand=True, padx=(8,0))

        cols_emp = ("cod_aghu","nome_item","vl_total","valor_consumido","valor_saldo")
        self.tv_emp = ttk.Treeview(lf_emp, columns=cols_emp, show="headings", height=12)
        for c in cols_emp:
            self.tv_emp.heading(c, text=c)
            self.tv_emp.column(c, width=140, anchor="w")
        self.tv_emp.pack(fill="both", expand=True)

        self._carregar_fornecedores()

    def _carregar_fornecedores(self):
        fornecedores = banco.fornecedores_listar()
        self.map_forn = {f["nome"]: f["id"] for f in fornecedores}
        self.cb_fornec["values"] = list(self.map_forn.keys())
        if fornecedores:
            self.cb_fornec.current(0)
            self.atualizar_listas()

    def atualizar_listas(self):
        nome = self.cb_fornec.get()
        if not nome:
            return
        forn_id = self.map_forn[nome]

        # ATA
        for i in self.tv_ata.get_children():
            self.tv_ata.delete(i)
        for r in banco.saldo_ata_por_fornecedor(forn_id):
            self.tv_ata.insert("", "end", values=(
                r.get("pregao",""),
                r.get("cod_aghu",""),
                r.get("nome_item",""),
                r.get("qtde_total",0),
                r.get("qtde_usada",0),
                r.get("qtde_saldo",0),
            ))

        # Empenho
        for i in self.tv_emp.get_children():
            self.tv_emp.delete(i)
        for r in banco.saldo_empenho_por_fornecedor(forn_id):
            self.tv_emp.insert("", "end", values=(
                r.get("cod_aghu",""),
                r.get("nome_item",""),
                f'{r.get("vl_total",0):.2f}',
                f'{r.get("valor_consumido",0):.2f}',
                f'{r.get("valor_saldo",0):.2f}',
            ))
