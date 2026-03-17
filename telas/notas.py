# notas.py
import tkinter as tk
from tkinter import ttk, messagebox
from banco import conectar

BODY_BG = "#efefef"

def _combo_fornecedores(parent):
    with conectar() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM fornecedores ORDER BY nome;")
        rows = cur.fetchall()
    mapa = {f"{r[1]} (id {r[0]})": r[0] for r in rows}
    var = tk.StringVar()
    cb = ttk.Combobox(parent, state="readonly", values=list(mapa.keys()), width=42, textvariable=var)
    return cb, var, mapa

class TelaNotas(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BODY_BG)
        tk.Label(self, text="Cadastro de Notas", font=("Segoe UI Semibold", 16), bg=BODY_BG)\
            .pack(anchor="w", padx=20, pady=(20, 10))

        self.nota_sel_id = None

        frm = tk.LabelFrame(self, text="Dados da Nota", bg=BODY_BG)
        frm.pack(fill="x", padx=20)

        cb, self.for_var, self.map_for = _combo_fornecedores(frm)
        tk.Label(frm, text="Fornecedor", bg=BODY_BG).grid(row=0, column=0, sticky="e", padx=(10,6), pady=4)
        cb.grid(row=0, column=1, sticky="w", padx=(0,12), pady=4)

        self.vars = {k: tk.StringVar() for k in [
            "numero","data_expedicao","vl_total","codigo_sei","data_envio_processo","observacao"
        ]}

        def row(r, rot, chave, w=30):
            tk.Label(frm, text=rot, bg=BODY_BG).grid(row=r, column=2, sticky="e", padx=(10,6), pady=4)
            tk.Entry(frm, textvariable=self.vars[chave], width=w).grid(row=r, column=3, sticky="w", padx=(0,10), pady=4)

        row(0,"Número + Série", "numero", 20)
        row(1,"Data de expedição (AAAA-MM-DD)", "data_expedicao", 22)
        row(2,"Valor total da nota", "vl_total", 16)
        row(3,"Código SEI", "codigo_sei", 22)
        row(4,"Data de envio do processo", "data_envio_processo", 22)
        tk.Label(frm, text="Observação", bg=BODY_BG).grid(row=5, column=2, sticky="e", padx=(10,6), pady=4)
        tk.Entry(frm, textvariable=self.vars["observacao"], width=60).grid(row=5, column=3, sticky="w", padx=(0,10), pady=4)

        act = tk.Frame(self, bg=BODY_BG); act.pack(fill="x", padx=20, pady=8)
        tk.Button(act, text="Nova", command=self.nova).pack(side="left")
        tk.Button(act, text="Salvar", command=self.salvar).pack(side="left", padx=(8,0))
        tk.Button(act, text="Atualizar", command=self.atualizar).pack(side="left", padx=(8,0))
        tk.Button(act, text="Excluir", command=self.excluir).pack(side="left", padx=(8,0))

        # Lista de notas
        cols = ("id","fornecedor","numero","data_expedicao","vl_total")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=7)
        for c in cols:
            self.tree.heading(c, text=c.upper()); self.tree.column(c, width=160, anchor="w")
        self.tree.column("id", width=60)
        self.tree.pack(fill="x", padx=20, pady=(0,8))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # ------- Itens da Nota -------
        itens = tk.LabelFrame(self, text="Itens da Nota", bg=BODY_BG)
        itens.pack(fill="both", expand=True, padx=20, pady=(0,20))

        self.item = {k: tk.StringVar() for k in ["cod_aghu","data_uso","vl_unit","qtde","vl_total","qtde_consumida"]}
        def irow(r, rot, chave, w=20):
            tk.Label(itens, text=rot, bg=BODY_BG).grid(row=r, column=0, sticky="e", padx=(10,6), pady=4)
            tk.Entry(itens, textvariable=self.item[chave], width=w).grid(row=r, column=1, sticky="w", padx=(0,12), pady=4)

        irow(0,"Código AGHU", "cod_aghu", 18)
        irow(0,"Data de uso (AAAA-MM-DD)", "data_uso", 18)
        irow(1,"Valor unitário", "vl_unit", 12)
        irow(1,"Qtde do item", "qtde", 12)
        irow(1,"Valor total do item", "vl_total", 12)
        irow(2,"Qtde consumida", "qtde_consumida", 12)

        act2 = tk.Frame(itens, bg=BODY_BG); act2.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=6)
        tk.Button(act2, text="Adicionar item", command=self.item_add).pack(side="left")
        tk.Button(act2, text="Remover selecionado", command=self.item_remove).pack(side="left", padx=(8,0))
        # tabela de itens
        self.items_cols = ("id","cod_aghu","data_uso","vl_unit","qtde","vl_total","qtde_consumida")
        self.items_tree = ttk.Treeview(itens, columns=self.items_cols, show="headings", height=8)
        for c in self.items_cols:
            self.items_tree.heading(c, text=c.upper()); self.items_tree.column(c, width=130, anchor="w")
        self.items_tree.column("id", width=60)
        self.items_tree.grid(row=4, column=0, columnspan=4, sticky="nsew", padx=10, pady=6)
        itens.grid_columnconfigure(3, weight=1)
        itens.grid_rowconfigure(4, weight=1)

        self.carregar_notas()

    # -------- Notas --------
    def nova(self):
        self.nota_sel_id = None
        for v in self.vars.values(): v.set("")
        self.for_var.set("")
        for i in self.items_tree.get_children(): self.items_tree.delete(i)
        self.tree.selection_remove(*self.tree.selection())

    def _nota_parse(self):
        try:
            return {
                "fornecedor_id": self.map_for[self.for_var.get()],
                "numero": self.vars["numero"].get().strip(),
                "data_expedicao": self.vars["data_expedicao"].get().strip(),
                "vl_total": float(self.vars["vl_total"].get() or 0),
                "codigo_sei": self.vars["codigo_sei"].get().strip(),
                "data_envio_processo": self.vars["data_envio_processo"].get().strip(),
                "observacao": self.vars["observacao"].get().strip()
            }
        except Exception:
            messagebox.showwarning("Validação", "Verifique os campos numéricos.")
            return None

    def salvar(self):
        d = self._nota_parse()
        if not d: return
        if not d["numero"] or not d["data_expedicao"]:
            messagebox.showwarning("Validação", "Informe Número+Série e Data de expedição.")
            return
        with conectar() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO notas (fornecedor_id, numero, data_expedicao, vl_total, codigo_sei, data_envio_processo, observacao)
                VALUES (:fornecedor_id, :numero, :data_expedicao, :vl_total, :codigo_sei, :data_envio_processo, :observacao)
            """, d)
            self.nota_sel_id = cur.lastrowid
            conn.commit()
        messagebox.showinfo("OK", "Nota salva. Agora adicione os itens se necessário.")
        self.carregar_notas()

    def atualizar(self):
        if not self.nota_sel_id:
            messagebox.showinfo("Info", "Selecione uma nota.")
            return
        d = self._nota_parse()
        if not d: return
        d["id"] = self.nota_sel_id
        with conectar() as conn:
            conn.execute("""
                UPDATE notas SET
                    fornecedor_id=:fornecedor_id, numero=:numero, data_expedicao=:data_expedicao,
                    vl_total=:vl_total, codigo_sei=:codigo_sei, data_envio_processo=:data_envio_processo,
                    observacao=:observacao, atualizado_em=datetime('now','localtime')
                WHERE id=:id
            """, d)
            conn.commit()
        messagebox.showinfo("OK", "Nota atualizada.")
        self.carregar_notas()

    def excluir(self):
        if not self.nota_sel_id:
            messagebox.showinfo("Info", "Selecione uma nota.")
            return
        if not messagebox.askyesno("Confirmar", "Excluir nota e itens?"): return
        with conectar() as conn:
            conn.execute("DELETE FROM notas WHERE id=?", (self.nota_sel_id,))
            conn.commit()
        self.nova()
        self.carregar_notas()

    def carregar_notas(self):
        with conectar() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT n.id, f.nome AS fornecedor, n.numero, n.data_expedicao, n.vl_total
                FROM notas n
                JOIN fornecedores f ON f.id = n.fornecedor_id
                ORDER BY n.data_expedicao DESC, n.id DESC
            """)
            rows = cur.fetchall()
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", "end", values=r)

        # Carrega itens da nota atual
        self.carregar_itens()

    def on_select(self, _e):
        sel = self.tree.selection()
        if not sel: return
        self.nota_sel_id = self.tree.item(sel[0])["values"][0]
        with conectar() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM notas WHERE id=?", (self.nota_sel_id,))
            r = cur.fetchone()
            cols = [d[0] for d in cur.description]
            d = dict(zip(cols, r))
        # seta form
        for rot, idv in self.map_for.items():
            if idv == d["fornecedor_id"]:
                self.for_var.set(rot); break
        self.vars["numero"].set(d["numero"])
        self.vars["data_expedicao"].set(d["data_expedicao"])
        self.vars["vl_total"].set(d["vl_total"])
        self.vars["codigo_sei"].set(d["codigo_sei"] or "")
        self.vars["data_envio_processo"].set(d["data_envio_processo"] or "")
        self.vars["observacao"].set(d["observacao"] or "")

        self.carregar_itens()

    # -------- Itens --------
    def item_add(self):
        if not self.nota_sel_id:
            messagebox.showinfo("Info", "Salve a nota antes de incluir itens.")
            return
        try:
            d = {
                "nota_id": self.nota_sel_id,
                "cod_aghu": self.item["cod_aghu"].get().strip(),
                "data_uso": self.item["data_uso"].get().strip(),
                "vl_unit": float(self.item["vl_unit"].get() or 0),
                "qtde": float(self.item["qtde"].get() or 0),
                "vl_total": float(self.item["vl_total"].get() or 0),
                "qtde_consumida": float(self.item["qtde_consumida"].get() or 0)
            }
        except Exception:
            messagebox.showwarning("Validação", "Verifique valores numéricos do item.")
            return
        if not d["cod_aghu"]:
            messagebox.showwarning("Validação", "Informe o Código AGHU do item.")
            return
        with conectar() as conn:
            conn.execute("""
                INSERT INTO notas_itens (nota_id, cod_aghu, data_uso, vl_unit, qtde, vl_total, qtde_consumida)
                VALUES (:nota_id, :cod_aghu, :data_uso, :vl_unit, :qtde, :vl_total, :qtde_consumida)
            """, d)
            conn.commit()
        self.carregar_itens()
        for v in self.item.values(): v.set("")

    def item_remove(self):
        sel = self.items_tree.selection()
        if not sel: return
        iid = self.items_tree.item(sel[0])["values"][0]
        with conectar() as conn:
            conn.execute("DELETE FROM notas_itens WHERE id=?", (iid,))
            conn.commit()
        self.carregar_itens()

    def carregar_itens(self):
        for i in self.items_tree.get_children():
            self.items_tree.delete(i)
        if not self.nota_sel_id:
            return
        with conectar() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, cod_aghu, data_uso, vl_unit, qtde, vl_total, qtde_consumida
                FROM notas_itens WHERE nota_id=? ORDER BY id
            """, (self.nota_sel_id,))
            for r in cur.fetchall():
                self.items_tree.insert("", "end", values=r)
