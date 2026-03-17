# atas_empenhos.py
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

class TelaAtasEmpenhos(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BODY_BG)
        tk.Label(self, text="Atas (Pregão) & Empenhos", font=("Segoe UI Semibold", 16), bg=BODY_BG)\
            .pack(anchor="w", padx=20, pady=(20, 10))

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.tab_ata = tk.Frame(nb, bg=BODY_BG)
        nb.add(self.tab_ata, text="Itens de Pregão (Ata)")
        self._montar_tab_ata()

        self.tab_emp = tk.Frame(nb, bg=BODY_BG)
        nb.add(self.tab_emp, text="Empenhos")
        self._montar_tab_empenho()

    # ---------------- ATA ----------------
    def _montar_tab_ata(self):
        f = self.tab_ata
        form = tk.LabelFrame(f, text="Cadastro de Itens do Pregão (Ata)", bg=BODY_BG)
        form.pack(fill="x", pady=8)

        self.ata = {k: tk.StringVar() for k in ["pregao","cod_aghu","nome_item","qtde_total","vl_unit","vl_total","observacao"]}
        cb, self.ata_for_var, self.ata_map = _combo_fornecedores(form)
        tk.Label(form, text="Fornecedor", bg=BODY_BG).grid(row=0, column=0, sticky="e", padx=(10,6), pady=4)
        cb.grid(row=0, column=1, sticky="w", padx=(0,10), pady=4)

        def row(r, rot, chave, w=40):
            tk.Label(form, text=rot, bg=BODY_BG).grid(row=r, column=2, sticky="e", padx=(10,6), pady=4)
            tk.Entry(form, textvariable=self.ata[chave], width=w).grid(row=r, column=3, sticky="w", padx=(0,10), pady=4)

        row(0,"Pregão", "pregao", 20)
        row(1,"Código AGHU", "cod_aghu", 18)
        row(2,"Nome do item", "nome_item", 40)
        row(3,"Qtde no pregão", "qtde_total", 12)
        row(4,"Valor unitário", "vl_unit", 12)
        row(5,"Valor total no pregão", "vl_total", 14)

        tk.Label(form, text="Observação", bg=BODY_BG).grid(row=6, column=2, sticky="e", padx=(10,6), pady=4)
        tk.Entry(form, textvariable=self.ata["observacao"], width=60).grid(row=6, column=3, sticky="w", padx=(0,10), pady=4)

        act = tk.Frame(f, bg=BODY_BG)
        act.pack(fill="x", pady=4)
        tk.Button(act, text="Salvar", command=self.ata_salvar).pack(side="left")
        tk.Button(act, text="Atualizar", command=self.ata_atualizar).pack(side="left", padx=(8,0))
        tk.Button(act, text="Excluir", command=self.ata_excluir).pack(side="left", padx=(8,0))
        tk.Button(act, text="Limpar", command=self.ata_limpar).pack(side="left", padx=(8,0))

        self.ata_sel_id = None
        cols = ("id","fornecedor","pregao","cod_aghu","nome_item","qtde_total","vl_unit","vl_total","saldo_qtde")
        self.ata_tree = ttk.Treeview(f, columns=cols, show="headings", height=12)
        for c in cols:
            self.ata_tree.heading(c, text=c.upper())
            self.ata_tree.column(c, width=120, anchor="w")
        self.ata_tree.column("id", width=60)
        self.ata_tree.pack(fill="both", expand=True, pady=(6, 10))
        self.ata_tree.bind("<<TreeviewSelect>>", self.ata_on_select)

        self.ata_carregar()

    def _ata_parse(self):
        try:
            return {
                "fornecedor_id": self.ata_map[self.ata_for_var.get()],
                "pregao": self.ata["pregao"].get().strip(),
                "cod_aghu": self.ata["cod_aghu"].get().strip(),
                "nome_item": self.ata["nome_item"].get().strip(),
                "qtde_total": float(self.ata["qtde_total"].get() or 0),
                "vl_unit": float(self.ata["vl_unit"].get() or 0),
                "vl_total": float(self.ata["vl_total"].get() or 0),
                "observacao": self.ata["observacao"].get().strip()
            }
        except Exception:
            messagebox.showwarning("Validação", "Verifique os campos numéricos (quantidade e valores).")
            return None

    def ata_salvar(self):
        dados = self._ata_parse()
        if not dados: return
        if not dados["pregao"] or not dados["cod_aghu"] or not dados["nome_item"]:
            messagebox.showwarning("Validação", "Informe Pregão, Código AGHU e Nome do item.")
            return
        try:
            with conectar() as conn:
                conn.execute("""
                    INSERT INTO atas_itens
                    (fornecedor_id, pregao, cod_aghu, nome_item, qtde_total, vl_unit, vl_total, observacao)
                    VALUES (:fornecedor_id, :pregao, :cod_aghu, :nome_item, :qtde_total, :vl_unit, :vl_total, :observacao)
                """, dados)
                conn.commit()
            messagebox.showinfo("OK", "Item do pregão salvo.")
            self.ata_carregar()
            self.ata_limpar()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar: {e}")

    def ata_atualizar(self):
        if not self.ata_sel_id:
            messagebox.showinfo("Info", "Selecione um item.")
            return
        dados = self._ata_parse()
        if not dados: return
        dados["id"] = self.ata_sel_id
        try:
            with conectar() as conn:
                conn.execute("""
                    UPDATE atas_itens SET
                        fornecedor_id=:fornecedor_id,pregao=:pregao,cod_aghu=:cod_aghu,nome_item=:nome_item,
                        qtde_total=:qtde_total,vl_unit=:vl_unit,vl_total=:vl_total,observacao=:observacao,
                        atualizado_em=datetime('now','localtime')
                    WHERE id=:id
                """, dados)
                conn.commit()
            messagebox.showinfo("OK", "Item atualizado.")
            self.ata_carregar()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao atualizar: {e}")

    def ata_excluir(self):
        if not self.ata_sel_id:
            messagebox.showinfo("Info", "Selecione um item.")
            return
        if not messagebox.askyesno("Confirmar", "Excluir item do pregão?"):
            return
        with conectar() as conn:
            conn.execute("DELETE FROM atas_itens WHERE id=?", (self.ata_sel_id,))
            conn.commit()
        self.ata_carregar()
        self.ata_limpar()

    def ata_limpar(self):
        self.ata_sel_id = None
        for v in self.ata.values():
            v.set("")
        self.ata_for_var.set("")
        self.ata_tree.selection_remove(*self.ata_tree.selection())

    def ata_carregar(self):
        with conectar() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.id, f.nome AS fornecedor, a.pregao, a.cod_aghu, a.nome_item,
                       a.qtde_total, a.vl_unit, a.vl_total,
                       COALESCE(v.qtde_saldo, a.qtde_total) AS saldo_qtde
                FROM atas_itens a
                JOIN fornecedores f ON f.id = a.fornecedor_id
                LEFT JOIN vw_saldo_ata v ON v.ata_id = a.id
                ORDER BY f.nome, a.pregao, a.cod_aghu
            """)
            rows = cur.fetchall()
        for i in self.ata_tree.get_children():
            self.ata_tree.delete(i)
        for r in rows:
            self.ata_tree.insert("", "end", values=r)

    def ata_on_select(self, _e):
        sel = self.ata_tree.selection()
        if not sel: return
        vals = self.ata_tree.item(sel[0])["values"]
        self.ata_sel_id = vals[0]
        # Carrega do banco para preencher todos os campos
        with conectar() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM atas_itens WHERE id=?", (self.ata_sel_id,))
            r = cur.fetchone()
            cols = [d[0] for d in cur.description]
            d = dict(zip(cols, r))
        # set
        # fornecedor combobox (busca label correspondente)
        for rot, idv in self.ata_map.items():
            if idv == d["fornecedor_id"]:
                self.ata_for_var.set(rot)
                break
        self.ata["pregao"].set(d["pregao"])
        self.ata["cod_aghu"].set(d["cod_aghu"])
        self.ata["nome_item"].set(d["nome_item"])
        self.ata["qtde_total"].set(d["qtde_total"])
        self.ata["vl_unit"].set(d["vl_unit"])
        self.ata["vl_total"].set(d["vl_total"])
        self.ata["observacao"].set(d["observacao"] or "")

    # ---------------- EMPENHOS ----------------
    def _montar_tab_empenho(self):
        f = self.tab_emp
        form = tk.LabelFrame(f, text="Cadastro de Empenhos (por item)", bg=BODY_BG)
        form.pack(fill="x", pady=8)

        self.emp = {k: tk.StringVar() for k in ["cod_aghu","nome_item","vl_unit","vl_total","numero_empenho","observacao"]}
        cb, self.emp_for_var, self.emp_map = _combo_fornecedores(form)
        tk.Label(form, text="Fornecedor", bg=BODY_BG).grid(row=0, column=0, sticky="e", padx=(10,6), pady=4)
        cb.grid(row=0, column=1, sticky="w", padx=(0,10), pady=4)

        def row(r, rot, chave, w=30):
            tk.Label(form, text=rot, bg=BODY_BG).grid(row=r, column=2, sticky="e", padx=(10,6), pady=4)
            tk.Entry(form, textvariable=self.emp[chave], width=w).grid(row=r, column=3, sticky="w", padx=(0,10), pady=4)

        row(0,"Código AGHU", "cod_aghu", 18)
        row(1,"Nome do item", "nome_item", 40)
        row(2,"Valor unitário", "vl_unit", 12)
        row(3,"Valor total do empenho", "vl_total", 14)
        row(4,"Número do empenho", "numero_empenho", 20)
        row(5,"Observação", "observacao", 60)

        act = tk.Frame(f, bg=BODY_BG)
        act.pack(fill="x", pady=4)
        tk.Button(act, text="Salvar", command=self.emp_salvar).pack(side="left")
        tk.Button(act, text="Atualizar", command=self.emp_atualizar).pack(side="left", padx=(8,0))
        tk.Button(act, text="Excluir", command=self.emp_excluir).pack(side="left", padx=(8,0))
        tk.Button(act, text="Limpar", command=self.emp_limpar).pack(side="left", padx=(8,0))

        self.emp_sel_id = None
        cols = ("id","fornecedor","cod_aghu","nome_item","vl_unit","vl_total","valor_saldo","numero_empenho")
        self.emp_tree = ttk.Treeview(f, columns=cols, show="headings", height=12)
        for c in cols:
            self.emp_tree.heading(c, text=c.upper())
            self.emp_tree.column(c, width=130, anchor="w")
        self.emp_tree.column("id", width=60)
        self.emp_tree.pack(fill="both", expand=True, pady=(6, 10))
        self.emp_tree.bind("<<TreeviewSelect>>", self.emp_on_select)

        self.emp_carregar()

    def _emp_parse(self):
        try:
            return {
                "fornecedor_id": self.emp_map[self.emp_for_var.get()],
                "cod_aghu": self.emp["cod_aghu"].get().strip(),
                "nome_item": self.emp["nome_item"].get().strip(),
                "vl_unit": float(self.emp["vl_unit"].get() or 0),
                "vl_total": float(self.emp["vl_total"].get() or 0),
                "numero_empenho": self.emp["numero_empenho"].get().strip(),
                "observacao": self.emp["observacao"].get().strip()
            }
        except Exception:
            messagebox.showwarning("Validação", "Verifique os campos numéricos de valores.")
            return None

    def emp_salvar(self):
        dados = self._emp_parse()
        if not dados: return
        if not dados["cod_aghu"] or not dados["nome_item"]:
            messagebox.showwarning("Validação", "Informe Código AGHU e Nome do item.")
            return
        with conectar() as conn:
            conn.execute("""
                INSERT INTO empenhos (fornecedor_id, cod_aghu, nome_item, vl_unit, vl_total, numero_empenho, observacao)
                VALUES (:fornecedor_id, :cod_aghu, :nome_item, :vl_unit, :vl_total, :numero_empenho, :observacao)
            """, dados)
            conn.commit()
        messagebox.showinfo("OK", "Empenho salvo.")
        self.emp_carregar()
        self.emp_limpar()

    def emp_atualizar(self):
        if not self.emp_sel_id:
            messagebox.showinfo("Info", "Selecione um empenho.")
            return
        dados = self._emp_parse()
        if not dados: return
        dados["id"] = self.emp_sel_id
        with conectar() as conn:
            conn.execute("""
                UPDATE empenhos SET
                    fornecedor_id=:fornecedor_id, cod_aghu=:cod_aghu, nome_item=:nome_item,
                    vl_unit=:vl_unit, vl_total=:vl_total, numero_empenho=:numero_empenho,
                    observacao=:observacao, atualizado_em=datetime('now','localtime')
                WHERE id=:id
            """, dados)
            conn.commit()
        messagebox.showinfo("OK", "Empenho atualizado.")
        self.emp_carregar()

    def emp_excluir(self):
        if not self.emp_sel_id:
            messagebox.showinfo("Info", "Selecione um empenho.")
            return
        if not messagebox.askyesno("Confirmar", "Excluir empenho?"):
            return
        with conectar() as conn:
            conn.execute("DELETE FROM empenhos WHERE id=?", (self.emp_sel_id,))
            conn.commit()
        self.emp_carregar()
        self.emp_limpar()

    def emp_limpar(self):
        self.emp_sel_id = None
        for v in self.emp.values():
            v.set("")
        self.emp_for_var.set("")
        self.emp_tree.selection_remove(*self.emp_tree.selection())

    def emp_carregar(self):
        with conectar() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT e.id, f.nome AS fornecedor, e.cod_aghu, e.nome_item, e.vl_unit, e.vl_total,
                       COALESCE(v.valor_saldo, e.vl_total) AS valor_saldo, e.numero_empenho
                FROM empenhos e
                JOIN fornecedores f ON f.id = e.fornecedor_id
                LEFT JOIN vw_saldo_empenho v ON v.empenho_id = e.id
                ORDER BY f.nome, e.cod_aghu
            """)
            rows = cur.fetchall()
        for i in self.emp_tree.get_children():
            self.emp_tree.delete(i)
        for r in rows:
            self.emp_tree.insert("", "end", values=r)

    def emp_on_select(self, _e):
        sel = self.emp_tree.selection()
        if not sel: return
        self.emp_sel_id = self.emp_tree.item(sel[0])["values"][0]
        with conectar() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM empenhos WHERE id=?", (self.emp_sel_id,))
            r = cur.fetchone()
            cols = [d[0] for d in cur.description]
            d = dict(zip(cols, r))
        for rot, idv in self.emp_map.items():
            if idv == d["fornecedor_id"]:
                self.emp_for_var.set(rot); break
        self.emp["cod_aghu"].set(d["cod_aghu"])
        self.emp["nome_item"].set(d["nome_item"])
        self.emp["vl_unit"].set(d["vl_unit"])
        self.emp["vl_total"].set(d["vl_total"])
        self.emp["numero_empenho"].set(d["numero_empenho"] or "")
        self.emp["observacao"].set(d["observacao"] or "")
