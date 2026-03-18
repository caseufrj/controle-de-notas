# telas/notas.py
import tkinter as tk
from tkinter import ttk, messagebox
import banco
from datetime import date

# --- Utilidades de formatação BR ---
from decimal import Decimal, ROUND_HALF_UP
import re

def _to_decimal_safe(val) -> Decimal:
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, float)):
        return Decimal(str(val))
    s = str(val or "").strip()
    # aceita formatos "R$ 1.234,56" / "1.234,56" / "1234,56" / "1234.56"
    s = s.replace("R$", "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except Exception:
        return Decimal("0")

def formatar_moeda_br(valor, com_prefixo=True) -> str:
    d = _to_decimal_safe(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # separadores BR
    inteira, frac = f"{d:.2f}".split(".")
    inteira = f"{int(inteira):,}".replace(",", ".")  # milhar com ponto
    s = f"{inteira},{frac}"
    return f"R$ {s}" if com_prefixo else s

def parse_moeda_br(texto) -> Decimal:
    return _to_decimal_safe(texto)

def mascarar_data_ddmmaa(s: str) -> str:
    # mantém apenas dígitos e injeta "/"
    d = re.sub(r"\D", "", s)[:8]  # até 8 dígitos
    if len(d) > 4:
        return f"{d[:2]}/{d[2:4]}/{d[4:]}"
    elif len(d) > 2:
        return f"{d[:2]}/{d[2:]}"
    return d

def validar_data_ddmmaa(s: str) -> bool:
    s = mascarar_data_ddmmaa(s)
    if len(s) != 10:
        return False
    try:
        datetime.strptime(s, "%d/%m/%Y")
        return True
    except ValueError:
        return False

# --- Widgets com máscara: MoedaEntry e DataEntry ---
class MoedaEntry(ttk.Entry):
    """Entry que formata como moeda BR enquanto digita. value() retorna Decimal."""
    def __init__(self, master=None, prefixo=True, **kw):
        super().__init__(master, **kw)
        self._prefixo = prefixo
        self._sv = tk.StringVar()
        self.configure(textvariable=self._sv)
        self._sv.trace_add("write", self._on_write)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self._formatando = False

    def _on_write(self, *_):
        if self._formatando:
            return
        self._formatando = True
        texto = self._sv.get()
        # permite apagar completamente
        if not texto.strip():
            self._formatando = False
            return
        # mantém apenas dígitos e vírgulas/pontos usados pelo usuário; converte ao final
        dec = parse_moeda_br(texto)
        self._sv.set(formatar_moeda_br(dec, com_prefixo=self._prefixo))
        self.icursor("end")
        self._formatando = False

    def _on_focus_in(self, *_):
        # ao focar, remove prefixo para facilitar edição
        txt = self._sv.get().replace("R$", "").strip()
        self._sv.set(txt)

    def _on_focus_out(self, *_):
        # ao sair, formata bonitinho com prefixo
        if not self._sv.get().strip():
            return
        dec = parse_moeda_br(self._sv.get())
        self._sv.set(formatar_moeda_br(dec, com_prefixo=self._prefixo))

    def value(self) -> Decimal:
        return parse_moeda_br(self._sv.get())

    def set_value(self, val):
        self._sv.set(formatar_moeda_br(val, com_prefixo=self._prefixo))


class DataEntry(ttk.Entry):
    """Entry que mascara data DD/MM/AAAA; value() retorna 'DD/MM/AAAA' válido ou ''."""
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._sv = tk.StringVar()
        self.configure(textvariable=self._sv)
        self._sv.trace_add("write", self._on_write)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<F4>", self._hoje)  # atalho: F4 = hoje

    def _on_write(self, *_):
        cur = self.index("insert")
        antes = self._sv.get()
        mas = mascarar_data_ddmmaa(antes)
        self._sv.set(mas)
        try:
            # reposiciona cursor de maneira amigável
            if cur in (2, 5): cur += 1
            self.icursor(min(cur, len(mas)))
        except Exception:
            pass

    def _on_focus_out(self, *_):
        s = self._sv.get()
        if s and not validar_data_ddmmaa(s):
            messagebox.showwarning("Data", "Data inválida. Use DD/MM/AAAA.")
            self.focus_set()

    def _hoje(self, *_):
        self._sv.set(datetime.now().strftime("%d/%m/%Y"))

    def value(self) -> str:
        return self._sv.get()

    def set_value(self, s: str):
        self._sv.set(mascarar_data_ddmmaa(s))


class TelaNotas(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")
        banco.criar_tabelas()

        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=12, pady=10)

        # Fornecedor
        tk.Label(topo, text="Fornecedor:", bg="white").grid(row=0, column=0, sticky="w")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.grid(row=0, column=1, padx=6, pady=2, sticky="w")
        self.cb_fornec.bind("<<ComboboxSelected>>", lambda e: self._recarregar_vinculos())

        # Dados da nota
        tk.Label(topo, text="Número+Série*:", bg="white").grid(row=1, column=0, sticky="w")
        self.e_numero = ttk.Entry(topo, width=30)
        self.e_numero.grid(row=1, column=1, sticky="w", padx=6, pady=2)

        tk.Label(topo, text="Data expedição* (YYYY-MM-DD):", bg="white").grid(row=1, column=2, sticky="w")
        self.e_data = ttk.Entry(topo, width=18)
        self.e_data.grid(row=1, column=3, sticky="w", padx=6, pady=2)
        self.e_data.insert(0, date.today().isoformat())

        tk.Label(topo, text="Valor total*:", bg="white").grid(row=2, column=0, sticky="w")
        self.e_total = ttk.Entry(topo, width=18)
        self.e_total.grid(row=2, column=1, sticky="w", padx=6, pady=2)

        tk.Label(topo, text="Código SEI:", bg="white").grid(row=2, column=2, sticky="w")
        self.e_sei = ttk.Entry(topo, width=24)
        self.e_sei.grid(row=2, column=3, sticky="w", padx=6, pady=2)

        tk.Label(topo, text="Envio processo (YYYY-MM-DD):", bg="white").grid(row=3, column=0, sticky="w")
        self.e_envio = ttk.Entry(topo, width=18)
        self.e_envio.grid(row=3, column=1, sticky="w", padx=6, pady=2)

        tk.Label(topo, text="Observação:", bg="white").grid(row=3, column=2, sticky="w")
        self.e_obs = ttk.Entry(topo, width=40)
        self.e_obs.grid(row=3, column=3, sticky="w", padx=6, pady=2)

        self.btn_salvar_nota = ttk.Button(topo, text="Salvar Nota", command=self._salvar_nota)
        self.btn_salvar_nota.grid(row=0, column=3, sticky="e")

        # Área itens
        area = ttk.LabelFrame(self, text="Itens da Nota")
        area.pack(fill="both", expand=True, padx=12, pady=10)

        grid = tk.Frame(area)
        grid.pack(fill="x", padx=8, pady=6)

        # >>> Primeiro crie as Combobox de vínculo
        tk.Label(grid, text="Vínculo ATA:").grid(row=0, column=0, sticky="w")
        self.cb_ata = ttk.Combobox(grid, state="readonly", width=40)
        self.cb_ata.grid(row=0, column=1, padx=6, pady=2, sticky="w")

        tk.Label(grid, text="Vínculo Empenho:").grid(row=0, column=2, sticky="w")
        self.cb_emp = ttk.Combobox(grid, state="readonly", width=40)
        self.cb_emp.grid(row=0, column=3, padx=6, pady=2, sticky="w")

        # Campos do item
        labels = ["Cód AGHU*", "Data uso (YYYY-MM-DD)", "Vlr Unit*", "Qtde*", "Vlr Total*", "Qtde consumida"]
        self.ent_item = []
        for i, lb in enumerate(labels, start=1):
            tk.Label(grid, text=lb).grid(row=i, column=0, sticky="w")
            e = ttk.Entry(grid, width=20)
            e.grid(row=i, column=1, sticky="w", padx=6, pady=2)
            self.ent_item.append(e)

        tk.Label(grid, text="Nome item (opcional)").grid(row=1, column=2, sticky="w")
        self.e_nome_item = ttk.Entry(grid, width=40)
        self.e_nome_item.grid(row=1, column=3, sticky="w", padx=6, pady=2)

        self.btn_add_item = ttk.Button(grid, text="Adicionar item", command=self._adicionar_item_na_tabela, state="disabled")
        self.btn_add_item.grid(row=6, column=3, sticky="e", pady=4)

        # Tabela de itens (pendentes)
        cols = ("cod_aghu","data_uso","vl_unit","qtde","vl_total","qtde_consumida","ata_item_id","empenho_id","ata_leg","emp_leg")
        self.tv = ttk.Treeview(area, columns=cols, show="headings", height=10)
        heads = ("Cód AGHU","Data uso","Vlr Unit","Qtde","Vlr Total","Qtde cons.","ID ATA","ID Emp","ATA","Empenho")
        widths = (100,100,90,70,100,100,60,60,160,160)
        for c, h, w in zip(cols, heads, widths):
            self.tv.heading(c, text=h)
            self.tv.column(c, width=w, anchor="w")
        self.tv.pack(fill="both", expand=True, padx=8, pady=6)

        # Rodapé
        rod = tk.Frame(self, bg="white")
        rod.pack(fill="x", padx=12, pady=(0,10))
        self.btn_salvar_itens = ttk.Button(rod, text="Salvar Itens na Nota", command=self._salvar_itens, state="disabled")
        self.btn_salvar_itens.pack(side="right")

        # Estado
        self.nota_id = None
        self.map_fornec = {}
        self.map_ata = {}
        self.map_emp = {}

        # >>> Só agora carregue fornecedores (pois cb_ata/cb_emp já existem)
        self._carregar_fornecedores()

    # ---------- Carregamentos ----------
    def _carregar_fornecedores(self):
        fs = banco.fornecedores_listar()
        self.map_fornec = {f["nome"]: f["id"] for f in fs}
        self.cb_fornec["values"] = list(self.map_fornec.keys())
        if fs:
            self.cb_fornec.current(0)
            self._recarregar_vinculos()
        else:
            # sem fornecedores, desabilita botões
            self.btn_add_item.config(state="disabled")
            self.btn_salvar_itens.config(state="disabled")

    def _recarregar_vinculos(self):
        # Garante que os widgets existem
        if not hasattr(self, "cb_ata") or not hasattr(self, "cb_emp"):
            return
        nome = self.cb_fornec.get()
        if not nome:
            self.cb_ata["values"] = []
            self.cb_emp["values"] = []
            return
        fid = self.map_fornec.get(nome)
        if not fid:
            return
        # ATA
        atas = banco.ata_itens_listar(fornecedor_id=fid)
        self.map_ata = {f'{a["pregao"]} | {a["cod_aghu"]} | {a["nome_item"]}': a["id"] for a in atas}
        self.cb_ata["values"] = list(self.map_ata.keys())
        # Empenho
        emps = banco.empenhos_listar(fornecedor_id=fid)
        self.map_emp = {f'{(e["numero_empenho"] or "-")} | {e["cod_aghu"]} | {e["nome_item"]}': e["id"] for e in emps}
        self.cb_emp["values"] = list(self.map_emp.keys())

    # ---------- Nota ----------
    def _salvar_nota(self):
        nome = self.cb_fornec.get()
        if not nome:
            messagebox.showwarning("Validação","Selecione o fornecedor.")
            return
        try:
            vl_total = float(self.e_total.get() or 0)
        except ValueError:
            messagebox.showwarning("Validação","Valor total inválido.")
            return

        d = {
            "fornecedor_id": self.map_fornec[nome],
            "numero": self.e_numero.get().strip(),
            "data_expedicao": self.e_data.get().strip(),
            "vl_total": vl_total,
            "codigo_sei": self.e_sei.get().strip(),
            "data_envio_processo": self.e_envio.get().strip(),
            "observacao": self.e_obs.get().strip()
        }
        if not (d["numero"] and d["data_expedicao"] and d["vl_total"]):
            messagebox.showwarning("Validação","Preencha número, data e valor total.")
            return
        try:
            self.nota_id = banco.nota_inserir(d)
            messagebox.showinfo("OK", f"Nota salva (ID {self.nota_id}). Agora adicione os itens.")
            self.btn_add_item.config(state="normal")
            self.btn_salvar_itens.config(state="normal")
            # Congela cabeçalho
            self.cb_fornec.config(state="disabled")
            self.e_numero.config(state="disabled")
            self.e_data.config(state="disabled")
            self.e_total.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar nota: {e}")

    # ---------- Itens ----------
    def _adicionar_item_na_tabela(self):
        if not self.nota_id:
            messagebox.showwarning("Atenção","Salve a nota antes de incluir itens.")
            return

        def _to_float(x):
            try:
                return float((x or "").replace(",", "."))
            except Exception:
                return 0.0

        cod = self.ent_item[0].get().strip()
        data_uso = self.ent_item[1].get().strip()
        vl_unit = _to_float(self.ent_item[2].get())
        qtde = _to_float(self.ent_item[3].get())
        vl_total = _to_float(self.ent_item[4].get())
        qtde_cons = _to_float(self.ent_item[5].get())

        if not (cod and vl_unit and qtde and vl_total):
            messagebox.showwarning("Validação","Preencha código, valor unitário, quantidade e valor total.")
            return

        ata_leg = self.cb_ata.get() or ""
        emp_leg = self.cb_emp.get() or ""
        ata_id = self.map_ata.get(ata_leg)
        emp_id = self.map_emp.get(emp_leg)

        self.tv.insert("", "end", values=(
            cod, data_uso, f"{vl_unit:.2f}", f"{qtde}", f"{vl_total:.2f}", f"{qtde_cons}",
            ata_id or "", emp_id or "", ata_leg, emp_leg
        ))

        # limpa campos do item (mantém vínculos)
        for e in self.ent_item:
            e.delete(0, "end")
        self.e_nome_item.delete(0, "end")

    def _salvar_itens(self):
        if not self.nota_id:
            return
        itens = []
        for iid in self.tv.get_children():
            v = self.tv.item(iid, "values")
            itens.append({
                "cod_aghu": v[0],
                "data_uso": v[1] or None,
                "vl_unit": float(str(v[2]).replace(",", ".")),
                "qtde": float(str(v[3]).replace(",", ".")),
                "vl_total": float(str(v[4]).replace(",", ".")),
                "qtde_consumida": float(str(v[5]).replace(",", ".")) if v[5] else 0.0,
                "ata_item_id": int(v[6]) if str(v[6]).isdigit() else None,
                "empenho_id": int(v[7]) if str(v[7]).isdigit() else None
            })
        try:
            banco.nota_itens_inserir(self.nota_id, itens)
            messagebox.showinfo("OK","Itens salvos na nota. Saldos já atualizados.")
            # Limpa tabela de pendências
            for i in self.tv.get_children():
                self.tv.delete(i)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar itens: {e}")
