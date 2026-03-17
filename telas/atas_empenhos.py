# telas/atas_empenhos.py
import tkinter as tk
from tkinter import ttk, messagebox
import banco


class TelaAtasEmpenhos(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")
        banco.criar_tabelas()

        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=12, pady=12)
        tk.Label(topo, text="Fornecedor:", bg="white").pack(side="left")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.pack(side="left", padx=8)
        self.cb_fornec.bind("<<ComboboxSelected>>", lambda e: (self._listar_ata(), self._listar_empenho()))

        self._carregar_fornecedores()

        split = tk.Frame(self, bg="white")
        split.pack(fill="both", expand=True, padx=12, pady=4)

        self._bloco_ata(split)
        self._bloco_empenho(split)

    def _carregar_fornecedores(self):
        forn = banco.fornecedores_listar()
        self.map_forn = {f["nome"]: f["id"] for f in forn}
        self.cb_fornec["values"] = list(self.map_forn.keys())
        if forn:
            self.cb_fornec.current(0)

    # ---------- ATA ----------
    def _bloco_ata(self, parent):
        left = ttk.LabelFrame(parent, text="Itens de ATA (Pregão)")
        left.pack(side="left", fill="both", expand=True, padx=(0,6))

        form = tk.Frame(left)
        form.pack(fill="x", padx=8, pady=6)

        def r(lbl):
            f = tk.Frame(form)
            f.pack(fill="x", pady=2)
            tk.Label(f, text=lbl, width=16, anchor="w").pack(side="left")
            e = ttk.Entry(f, width=30)
            e.pack(side="left")
            return e

        self.a_pregao = r("Pregão*:")
        self.a_cod = r("Cód. AGHU*:")
        self.a_nome = r("Nome do item*:")
        self.a_qt = r("Qtde total*:")
        self.a_vu = r("Valor unitário*:")
        self.a_vt = r("Valor total*:")

        fobs = tk.Frame(form)
        fobs.pack(fill="x", pady=2)
        tk.Label(fobs, text="Observação:", width=16, anchor="w").pack(side="left")
        self.a_obs = ttk.Entry(fobs, width=50)
        self.a_obs.pack(side="left")

        tk.Button(form, text="Salvar Item de ATA", command=self._salvar_ata, bg="#2ecc71", fg="white").pack(pady=4, anchor="e")

        self.tv_ata = ttk.Treeview(left, columns=("pregao","cod","nome","qt","vu","vt"), show="headings", height=10)
        for c, t in zip(("pregao","cod","nome","qt","vu","vt"),
                        ("Pregão","Cód AGHU","Item","Qtde","Vlr Unit","Vlr Total")):
            self.tv_ata.heading(c, text=t)
            self.tv_ata.column(c, width=110, anchor="w")
        self.tv_ata.pack(fill="both", expand=True, padx=8, pady=(4,8))

    def _salvar_ata(self):
        forn_nome = self.cb_fornec.get()
        if not forn_nome:
            messagebox.showwarning("Validação","Selecione o fornecedor.")
            return
        d = {
            "fornecedor_id": self.map_forn[forn_nome],
            "pregao": self.a_pregao.get().strip(),
            "cod_aghu": self.a_cod.get().strip(),
            "nome_item": self.a_nome.get().strip(),
            "qtde_total": float(self.a_qt.get() or 0),
            "vl_unit": float(self.a_vu.get() or 0),
            "vl_total": float(self.a_vt.get() or 0),
            "observacao": self.a_obs.get().strip()
        }
        if not (d["pregao"] and d["cod_aghu"] and d["nome_item"]):
            messagebox.showwarning("Validação","Preencha pregão, código e nome do item.")
            return
        try:
            banco.ata_item_inserir(d)
            messagebox.showinfo("OK","Item de ATA salvo.")
            self._listar_ata()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar: {e}")

    def _listar_ata(self):
        forn_nome = self.cb_fornec.get()
        if not forn_nome:
            return
        forn_id = self.map_forn[forn_nome]
        for i in self.tv_ata.get_children():
            self.tv_ata.delete(i)
        for r in banco.ata_itens_listar(fornecedor_id=forn_id):
            self.tv_ata.insert("", "end", values=(
                r.get("pregao",""), r.get("cod_aghu",""), r.get("nome_item",""),
                r.get("qtde_total",0), f'{r.get("vl_unit",0):.2f}', f'{r.get("vl_total",0):.2f}'
            ))

    # ---------- EMPENHO ----------
    def _bloco_empenho(self, parent):
        right = ttk.LabelFrame(parent, text="Empenhos")
        right.pack(side="left", fill="both", expand=True, padx=(6,0))

        form = tk.Frame(right)
        form.pack(fill="x", padx=8, pady=6)

        def r(lbl):
            f = tk.Frame(form)
            f.pack(fill="x", pady=2)
            tk.Label(f, text=lbl, width=18, anchor="w").pack(side="left")
            e = ttk.Entry(f, width=36)
            e.pack(side="left")
            return e

        self.e_num = r("Número do empenho:")
        self.e_cod = r("Cód. AGHU*:")
        self.e_nome = r("Nome do item*:")
        self.e_vu = r("Valor unitário*:")
        self.e_vt = r("Valor total*:")

        fobs = tk.Frame(form)
        fobs.pack(fill="x", pady=2)
        tk.Label(fobs, text="Observação:", width=18, anchor="w").pack(side="left")
        self.e_obs = ttk.Entry(fobs, width=50)
        self.e_obs.pack(side="left")

        tk.Button(form, text="Salvar Empenho", command=self._salvar_empenho, bg="#2ecc71", fg="white").pack(pady=4, anchor="e")

        self.tv_emp = ttk.Treeview(right, columns=("numero","cod","nome","vu","vt"), show="headings", height=10)
        heads = ("Número","Cód AGHU","Item","Vlr Unit","Vlr Total")
        for c, t in zip(("numero","cod","nome","vu","vt"), heads):
            self.tv_emp.heading(c, text=t)
            self.tv_emp.column(c, width=120, anchor="w")
        self.tv_emp.pack(fill="both", expand=True, padx=8, pady=(4,8))

    def _salvar_empenho(self):
        forn_nome = self.cb_fornec.get()
        if not forn_nome:
            messagebox.showwarning("Validação","Selecione o fornecedor.")
            return
        d = {
            "fornecedor_id": self.map_forn[forn_nome],
            "cod_aghu": self.e_cod.get().strip(),
            "nome_item": self.e_nome.get().strip(),
            "vl_unit": float(self.e_vu.get() or 0),
            "vl_total": float(self.e_vt.get() or 0),
            "numero_empenho": self.e_num.get().strip(),
            "observacao": self.e_obs.get().strip()
        }
        if not (d["cod_aghu"] and d["nome_item"]):
            messagebox.showwarning("Validação","Preencha código e nome do item.")
            return
        try:
            banco.empenho_inserir(d)
            messagebox.showinfo("OK","Empenho salvo.")
            self._listar_empenho()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar: {e}")

    def _listar_empenho(self):
        forn_nome = self.cb_fornec.get()
        if not forn_nome:
            return
        forn_id = self.map_forn[forn_nome]
        for i in self.tv_emp.get_children():
            self.tv_emp.delete(i)
        for r in banco.empenhos_listar(fornecedor_id=forn_id):
            self.tv_emp.insert("", "end", values=(
                r.get("numero_empenho",""), r.get("cod_aghu",""),
                r.get("nome_item",""), f'{r.get("vl_unit",0):.2f}',
                f'{r.get("vl_total",0):.2f}'
            ))
