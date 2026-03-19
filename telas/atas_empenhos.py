# telas/atas_empenhos.py
import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

import banco
# Reaproveita os widgets de Notas
from telas.notas import MoedaEntry, DataEntry, formatar_moeda_br

class TelaAtasEmpenhos(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")
        banco.criar_tabelas()

        # Fornecedor comum
        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=12, pady=8)
        tk.Label(topo, text="Fornecedor:", bg="white").pack(side="left")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.pack(side="left", padx=6)
        self.cb_fornec.bind("<<ComboboxSelected>>", lambda e: self._recarregar_tudo())

        # Notebook principal
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=10)

        # --------- Aba ATAS ---------
        self._montar_aba_atas()

        # --------- Aba EMPENHOS ---------
        self._montar_aba_empenhos()

        # Estado
        self.map_fornec = {}
        self._carregar_fornecedores()
        self._recarregar_tudo()

    # ======================
    #       ATAS
    # ======================
    def _montar_aba_atas(self):
        aba = tk.Frame(self.nb, bg="white")
        self.nb.add(aba, text="Atas")

        # Cabeçalho ATA
        hdr = ttk.LabelFrame(aba, text="Cabeçalho da ATA")
        hdr.pack(fill="x", padx=6, pady=6)

        tk.Label(hdr, text="Nº da ATA*:").grid(row=0, column=0, sticky="w", padx=6, pady=3)
        self.e_ata_num = ttk.Entry(hdr, width=20); self.e_ata_num.grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(hdr, text="Vigência (início):").grid(row=0, column=2, sticky="w", padx=6)
        self.e_ata_ini = DataEntry(hdr, width=12); self.e_ata_ini.grid(row=0, column=3, sticky="w", padx=6)

        tk.Label(hdr, text="Vigência (fim):").grid(row=0, column=4, sticky="w", padx=6)
        self.e_ata_fim = DataEntry(hdr, width=12); self.e_ata_fim.grid(row=0, column=5, sticky="w", padx=6)

        tk.Label(hdr, text="Status:").grid(row=0, column=6, sticky="w", padx=6)
        self.cb_ata_status = ttk.Combobox(hdr, state="readonly", width=14,
            values=["Em vigência","Encerrada","Renovada"])
        self.cb_ata_status.set("Em vigência")
        self.cb_ata_status.grid(row=0, column=7, sticky="w", padx=6)

        tk.Label(hdr, text="Observação:").grid(row=1, column=0, sticky="w", padx=6)
        self.e_ata_obs = ttk.Entry(hdr, width=60); self.e_ata_obs.grid(row=1, column=1, columnspan=7, sticky="w", padx=6)

        btns_hdr = tk.Frame(hdr, bg="white"); btns_hdr.grid(row=0, column=8, rowspan=2, sticky="ne", padx=(10,0))
        ttk.Button(btns_hdr, text="Nova ATA", command=self._nova_ata).pack(fill="x", pady=2)
        ttk.Button(btns_hdr, text="Salvar ATA", command=self._salvar_ata).pack(fill="x", pady=2)
        ttk.Button(btns_hdr, text="Excluir ATA", command=self._excluir_ata).pack(fill="x", pady=2)

        # Itens da ATA
        it = ttk.LabelFrame(aba, text="Item da ATA")
        it.pack(fill="x", padx=6, pady=4)

        tk.Label(it, text="Cód AGHU*:").grid(row=0, column=0, sticky="w", padx=6)
        self.e_ai_cod = ttk.Entry(it, width=18); self.e_ai_cod.grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(it, text="Descrição*:").grid(row=0, column=2, sticky="w", padx=6)
        self.e_ai_nome = ttk.Entry(it, width=40); self.e_ai_nome.grid(row=0, column=3, sticky="w", padx=6)

        tk.Label(it, text="Qtde total*:").grid(row=1, column=0, sticky="w", padx=6)
        self.e_ai_qt = ttk.Entry(it, width=10); self.e_ai_qt.grid(row=1, column=1, sticky="w", padx=6)

        tk.Label(it, text="Vlr Unit*:").grid(row=1, column=2, sticky="w", padx=6)
        self.e_ai_vu = MoedaEntry(it, width=18); self.e_ai_vu.grid(row=1, column=3, sticky="w", padx=6)

        tk.Label(it, text="Vlr Total:").grid(row=1, column=4, sticky="w", padx=6)
        self.e_ai_vt = ttk.Entry(it, width=18, state="readonly"); self.e_ai_vt.grid(row=1, column=5, sticky="w", padx=6)

        tk.Label(it, text="Observação:").grid(row=2, column=0, sticky="w", padx=6)
        self.e_ai_obs = ttk.Entry(it, width=60); self.e_ai_obs.grid(row=2, column=1, columnspan=5, sticky="w", padx=6, pady=(0,6))

        # recalcula total
        self.e_ai_qt.bind("<KeyRelease>", lambda e: self._calc_total(self.e_ai_qt, self.e_ai_vu, self.e_ai_vt))
        self.e_ai_vu.bind("<KeyRelease>", lambda e: self._calc_total(self.e_ai_qt, self.e_ai_vu, self.e_ai_vt))

        btns_it = tk.Frame(it, bg="white"); btns_it.grid(row=0, column=6, rowspan=3, sticky="ne", padx=(10,0))
        ttk.Button(btns_it, text="Adicionar item", command=self._ata_add_item).pack(fill="x", pady=2)
        ttk.Button(btns_it, text="Editar item selec.", command=self._ata_editar_item_selec).pack(fill="x", pady=2)
        ttk.Button(btns_it, text="Excluir item selec.", command=self._ata_excluir_item_selec).pack(fill="x", pady=2)

        # Catálogo (hierárquico)
        box = ttk.LabelFrame(aba, text="Atas cadastradas (clique no cabeçalho para expandir itens)")
        box.pack(fill="both", expand=True, padx=6, pady=6)

        cols = ("fornecedor","numero","vig_ini","vig_fim","status","itens","saldo")
        self.tv_atas = ttk.Treeview(box, columns=cols, show="tree headings", height=10)
        for c, h, w in zip(cols,
                           ("Fornecedor","Nº ATA","Vigência (ini)","Vigência (fim)","Status","Itens","Saldo"),
                           (240,120,110,110,120,60,120)):
            self.tv_atas.heading(c, text=h)
            self.tv_atas.column(c, width=w, anchor="w")
        self.tv_atas.pack(fill="both", expand=True, padx=6, pady=6)

        self.tv_atas.bind("<<TreeviewOpen>>", self._atas_on_open)
        self.tv_atas.bind("<Double-1>", self._atas_on_double_click)

        bar = tk.Frame(box, bg="white"); bar.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(bar, text="Recarregar", command=self._carregar_atas).pack(side="left")

        # estado interno
        self._ata_id_editando = None
        self._ata_item_editando = None

    # ======================
    #     EMPENHOS
    # ======================
    def _montar_aba_empenhos(self):
        aba = tk.Frame(self.nb, bg="white")
        self.nb.add(aba, text="Empenhos")

        # Item de Empenho (agrupado por nº)
        frm = ttk.LabelFrame(aba, text="Item do Empenho")
        frm.pack(fill="x", padx=6, pady=6)

        tk.Label(frm, text="Nº Empenho*:").grid(row=0, column=0, sticky="w", padx=6)
        self.e_emp_num = ttk.Entry(frm, width=20); self.e_emp_num.grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(frm, text="Cód AGHU*:").grid(row=0, column=2, sticky="w", padx=6)
        self.e_emp_cod = ttk.Entry(frm, width=18); self.e_emp_cod.grid(row=0, column=3, sticky="w", padx=6)

        tk.Label(frm, text="Descrição*:").grid(row=0, column=4, sticky="w", padx=6)
        self.e_emp_nome = ttk.Entry(frm, width=40); self.e_emp_nome.grid(row=0, column=5, sticky="w", padx=6)

        tk.Label(frm, text="Vlr Unit*:").grid(row=1, column=0, sticky="w", padx=6)
        self.e_emp_vu = MoedaEntry(frm, width=18); self.e_emp_vu.grid(row=1, column=1, sticky="w", padx=6)

        tk.Label(frm, text="Qtde*:").grid(row=1, column=2, sticky="w", padx=6)
        self.e_emp_qt = ttk.Entry(frm, width=10); self.e_emp_qt.grid(row=1, column=3, sticky="w", padx=6)

        tk.Label(frm, text="Vlr Total:").grid(row=1, column=4, sticky="w", padx=6)
        self.e_emp_vt = ttk.Entry(frm, width=18, state="readonly"); self.e_emp_vt.grid(row=1, column=5, sticky="w", padx=6)

        tk.Label(frm, text="Observação:").grid(row=2, column=0, sticky="w", padx=6)
        self.e_emp_obs = ttk.Entry(frm, width=60); self.e_emp_obs.grid(row=2, column=1, columnspan=5, sticky="w", padx=6, pady=(0,6))

        self.e_emp_qt.bind("<KeyRelease>", lambda e: self._calc_total(self.e_emp_qt, self.e_emp_vu, self.e_emp_vt))
        self.e_emp_vu.bind("<KeyRelease>", lambda e: self._calc_total(self.e_emp_qt, self.e_emp_vu, self.e_emp_vt))

        btns = tk.Frame(frm, bg="white"); btns.grid(row=0, column=6, rowspan=3, sticky="ne", padx=(10,0))
        ttk.Button(btns, text="Adicionar item", command=self._emp_add_item).pack(fill="x", pady=2)
        ttk.Button(btns, text="Editar item selec.", command=self._emp_editar_item_selec).pack(fill="x", pady=2)
        ttk.Button(btns, text="Excluir item selec.", command=self._emp_excluir_item_selec).pack(fill="x", pady=2)

        # Catálogo por Nº do Empenho (hierárquico)
        box = ttk.LabelFrame(aba, text="Empenhos — agrupados por número (clique para ver itens)")
        box.pack(fill="both", expand=True, padx=6, pady=6)

        cols = ("fornecedor","numero","itens","valor_total")
        self.tv_emp = ttk.Treeview(box, columns=cols, show="tree headings", height=10)
        for c, h, w in zip(cols, ("Fornecedor","Nº Empenho","Itens","Valor total"), (240,160,80,140)):
            self.tv_emp.heading(c, text=h)
            self.tv_emp.column(c, width=w, anchor="w")
        self.tv_emp.pack(fill="both", expand=True, padx=6, pady=6)

        self.tv_emp.bind("<<TreeviewOpen>>", self._emp_on_open)
        self.tv_emp.bind("<Double-1>", self._emp_on_double_click)

        bar = tk.Frame(box, bg="white"); bar.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(bar, text="Recarregar", command=self._carregar_empenhos).pack(side="left")

        # estado interno
        self._emp_item_editando = None

    # ======================
    #     Utilidades
    # ======================
    def _calc_total(self, e_qt: ttk.Entry, e_vu: MoedaEntry, e_vt: ttk.Entry):
        try:
            qt = Decimal(str((e_qt.get() or "0").replace(",", ".")))
        except Exception:
            qt = Decimal("0")
        vu = e_vu.value()
        total = (qt * vu).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        e_vt.configure(state="normal"); e_vt.delete(0,"end")
        e_vt.insert(0, formatar_moeda_br(total)); e_vt.configure(state="readonly")

    def _carregar_fornecedores(self):
        fs = banco.fornecedores_listar()
        self.map_fornec = {f["nome"]: f["id"] for f in fs}
        self.cb_fornec["values"] = list(self.map_fornec.keys())
        if fs and not self.cb_fornec.get():
            self.cb_fornec.current(0)

    def _fid(self):
        nome = self.cb_fornec.get()
        return self.map_fornec.get(nome) if nome else None

    def _recarregar_tudo(self):
        self._carregar_atas()
        self._carregar_empenhos()

    # ======================
    #     ATAS - ações
    # ======================
    def _nova_ata(self):
        self._ata_id_editando = None
        self.e_ata_num.delete(0,"end")
        self.e_ata_ini.set_value("")
        self.e_ata_fim.set_value("")
        self.cb_ata_status.set("Em vigência")
        self.e_ata_obs.delete(0,"end")

    def _salvar_ata(self):
        fid = self._fid()
        if not fid:
            messagebox.showwarning("ATA","Selecione o fornecedor."); return
        numero = (self.e_ata_num.get() or "").strip()
        if not numero:
            messagebox.showwarning("ATA","Informe o Nº da ATA."); return

        def gui_to_iso(s):
            if not s: return None
            try: return datetime.strptime(s, "%d/%m/%Y").strftime("%Y-%m-%d")
            except Exception: return None

        d = {
            "fornecedor_id": fid,
            "numero": numero,
            "vigencia_ini": gui_to_iso(self.e_ata_ini.value()),
            "vigencia_fim": gui_to_iso(self.e_ata_fim.value()),
            "status": self.cb_ata_status.get(),
            "observacao": (self.e_ata_obs.get() or "").strip()
        }
        try:
            if self._ata_id_editando:
                banco.ata_hdr_atualizar(self._ata_id_editando, d)
                messagebox.showinfo("ATA","Cabeçalho atualizado.")
            else:
                self._ata_id_editando = banco.ata_hdr_inserir(d)
                messagebox.showinfo("ATA","ATA criada. Agora adicione os itens.")
        except Exception as e:
            messagebox.showerror("ATA", f"Falha ao salvar: {e}")
        self._carregar_atas()

    def _excluir_ata(self):
        if not self._ata_id_editando:
            messagebox.showwarning("ATA","Nenhuma ATA carregada no cabeçalho.")
            return
        if not messagebox.askyesno("Confirmar","Excluir a ATA e todos os itens?"):
            return
        try:
            banco.ata_hdr_excluir(self._ata_id_editando)
            self._nova_ata()
            self._carregar_atas()
        except Exception as e:
            messagebox.showerror("ATA", f"Falha ao excluir: {e}")

    def _ata_add_item(self):
        if not self._ata_id_editando:
            messagebox.showwarning("ATA","Salve o cabeçalho da ATA antes de incluir itens."); return
        try:
            qt = float((self.e_ai_qt.get() or "0").replace(",", "."))
        except Exception:
            qt = 0.0
        vu = float(str(self.e_ai_vu.value()))
        vt = qt * vu
        d = {
            "ata_id": self._ata_id_editando,
            "cod_aghu": (self.e_ai_cod.get() or "").strip(),
            "nome_item": (self.e_ai_nome.get() or "").strip(),
            "qtde_total": qt,
            "vl_unit": vu,
            "vl_total": vt,
            "observacao": (self.e_ai_obs.get() or "").strip()
        }
        if not (d["cod_aghu"] and d["nome_item"] and d["qtde_total"] and d["vl_unit"]):
            messagebox.showwarning("ATA","Preencha cód, descrição, qtde e Vlr Unit."); return
        try:
            banco.ata_item_inserir_v2(d)
            self._carregar_atas(refresh_items_of=self._ata_id_editando)
            # limpa campos do item
            self.e_ai_cod.delete(0,"end"); self.e_ai_nome.delete(0,"end")
            self.e_ai_qt.delete(0,"end"); self.e_ai_vu.set_value(0)
            self.e_ai_vt.configure(state="normal"); self.e_ai_vt.delete(0,"end"); self.e_ai_vt.configure(state="readonly")
            self.e_ai_obs.delete(0,"end")
        except Exception as e:
            messagebox.showerror("ATA", f"Falha ao incluir item: {e}")

    def _ata_editar_item_selec(self):
        sel = self.tv_atas.selection()
        if not sel: return
        iid = sel[0]
        # só permite editar itens (não cabeçalho); itens terão tag 'item'
        if "item" not in self.tv_atas.item(iid,"tags"):
            messagebox.showinfo("ATA","Selecione um item (filho)."); return
        vals = self.tv_atas.item(iid,"values")
        # values para item: ("", "", "", "", "", "", "") – mas guardo via 'values' custom? Melhor usar 'text'
        data = self.tv_atas.item(iid,"text")  # embuto um dict string
        try:
            d = eval(data)  # {'id':..., 'cod':'...', ...}
        except Exception:
            messagebox.showwarning("ATA","Não foi possível carregar o item."); return
        self._ata_item_editando = d.get("id")
        # joga nos campos
        self.e_ai_cod.delete(0,"end"); self.e_ai_cod.insert(0, d.get("cod") or "")
        self.e_ai_nome.delete(0,"end"); self.e_ai_nome.insert(0, d.get("nome") or "")
        self.e_ai_qt.delete(0,"end"); self.e_ai_qt.insert(0, str(d.get("qt") or "0"))
        self.e_ai_vu.set_value(Decimal(str(d.get("vu") or 0)))
        # força recálculo
        self._calc_total(self.e_ai_qt, self.e_ai_vu, self.e_ai_vt)
        self.e_ai_obs.delete(0,"end"); self.e_ai_obs.insert(0, d.get("obs") or "")

        # troca botão "Adicionar" por "Salvar edição"
        for w in self.e_ai_cod.master.grid_slaves(row=0, column=6)[0].winfo_children():
            # limpa painel e recria (evita state bleed)
            pass
        # simples: reusa o botão "Adicionar" chamando salvar edição se _ata_item_editando estiver setado
        self.e_ai_cod.master.after(10, lambda: None)

    def _ata_excluir_item_selec(self):
        sel = self.tv_atas.selection()
        if not sel: return
        iid = sel[0]
        if "item" not in self.tv_atas.item(iid,"tags"):
            messagebox.showinfo("ATA","Selecione um item (filho)."); return
        data = self.tv_atas.item(iid,"text")
        try:
            d = eval(data)
        except Exception:
            return
        if not messagebox.askyesno("Confirmar","Excluir o item selecionado?"):
            return
        try:
            banco.ata_item_excluir(d.get("id"))
            self._carregar_atas(refresh_items_of=d.get("ata_id"))
        except Exception as e:
            messagebox.showerror("ATA", f"Falha ao excluir item: {e}")

    def _carregar_atas(self, refresh_items_of: int|None=None):
        fid = self._fid()
        for i in self.tv_atas.get_children():
            self.tv_atas.delete(i)
        if not fid: return

        rows = banco.atas_hdr_listar(fornecedor_id=fid)
        # monta cabeçalhos
        for r in rows:
            vig_i = self._fmt(r.get("vigencia_ini"))
            vig_f = self._fmt(r.get("vigencia_fim"))
            saldo = formatar_moeda_br(r.get("valor_saldo", 0))
            nome_f = self.cb_fornec.get()

            iid = self.tv_atas.insert("", "end", text="", values=(
                nome_f, r.get("numero",""), vig_i, vig_f, r.get("status",""),
                str(r.get("itens_qtd",0)), saldo
            ))
            # guardo ata_id para expandir
            self.tv_atas.set(iid, column="numero", value=r.get("numero",""))
            self.tv_atas.item(iid, tags=("cab", f"ata_{r['ata_id']}"))

            # se vier pedido para atualizar os filhos de uma ata específica
            if refresh_items_of and int(r["ata_id"]) == int(refresh_items_of):
                self._popular_itens_ata(iid, r["ata_id"])

    def _fmt(self, iso):
        if not iso: return ""
        try: return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception: return iso

    def _atas_on_open(self, event):
        iid = self.tv_atas.focus()
        tags = self.tv_atas.item(iid,"tags")
        ata_id = None
        for t in tags:
            if t.startswith("ata_"):
                ata_id = int(t.split("_",1)[1]); break
        if ata_id:
            # limpa filhos e repopula
            for ch in self.tv_atas.get_children(iid):
                self.tv_atas.delete(ch)
            self._popular_itens_ata(iid, ata_id)

    def _popular_itens_ata(self, parent_iid, ata_id: int):
        itens = banco.ata_itens_listar_por_ata(ata_id)
        idx = 1
        for it in itens:
            payload = {
                "id": it["id"], "ata_id": ata_id,
                "cod": it.get("cod_aghu",""), "nome": it.get("nome_item",""),
                "qt": it.get("qtde_total",0), "vu": it.get("vl_unit",0),
                "vt": it.get("vl_total",0), "obs": it.get("observacao","") or ""
            }
            txt = str(payload)  # guardo no text
            self.tv_atas.insert(parent_iid, "end", text=txt, values=(
                f"Item {idx}",  # aparece na col 'fornecedor' como rótulo
                payload["cod"],
                "", "", "", "", formatar_moeda_br(payload["vt"])
            ), tags=("item",))
            idx += 1

    def _atas_on_double_click(self, event):
        # duplo clique num cabeçalho -> carrega no formulário de edição
        iid = self.tv_atas.focus()
        tags = self.tv_atas.item(iid,"tags")
        if "cab" in tags:
            # extrai ata_id a partir da tag
            ata_id = None
            for t in tags:
                if t.startswith("ata_"):
                    ata_id = int(t.split("_",1)[1]); break
            if not ata_id: return
            # carrega cabeçalho no form
            rows = banco.atas_hdr_listar(fornecedor_id=self._fid())
            row = next((r for r in rows if int(r["ata_id"])==ata_id), None)
            if not row: return
            self._ata_id_editando = ata_id
            self.e_ata_num.delete(0,"end"); self.e_ata_num.insert(0, row.get("numero",""))
            self.e_ata_ini.set_value(self._fmt(row.get("vigencia_ini")))
            self.e_ata_fim.set_value(self._fmt(row.get("vigencia_fim")))
            self.cb_ata_status.set(row.get("status","Em vigência"))
            self.e_ata_obs.delete(0,"end")  # sem obs na view; deixo em branco
            # abre lista de itens
            self._popular_itens_ata(iid, ata_id)

    # ======================
    #     EMPENHOS - ações
    # ======================
    def _emp_add_item(self):
        fid = self._fid()
        if not fid:
            messagebox.showwarning("Empenho","Selecione o fornecedor."); return
        num = (self.e_emp_num.get() or "").strip()
        if not num:
            messagebox.showwarning("Empenho","Informe o Nº do empenho."); return
        cod = (self.e_emp_cod.get() or "").strip()
        nome = (self.e_emp_nome.get() or "").strip()
        try: qt = float((self.e_emp_qt.get() or "0").replace(",", "."))
        except Exception: qt = 0.0
        vu = float(str(self.e_emp_vu.value()))
        vt = qt * vu
        if not (cod and nome and qt and vu):
            messagebox.showwarning("Empenho","Preencha cód, descrição, qtde e Vlr Unit."); return
        try:
            banco.empenho_inserir({
                "fornecedor_id": fid,
                "cod_aghu": cod,
                "nome_item": nome,
                "vl_unit": vu,
                "vl_total": vt,
                "numero_empenho": num,
                "observacao": (self.e_emp_obs.get() or "").strip()
            })
            self._carregar_empenhos(refresh_num=num)
            # limpar
            self.e_emp_cod.delete(0,"end"); self.e_emp_nome.delete(0,"end")
            self.e_emp_qt.delete(0,"end"); self.e_emp_vu.set_value(0)
            self.e_emp_vt.configure(state="normal"); self.e_emp_vt.delete(0,"end"); self.e_emp_vt.configure(state="readonly")
            self.e_emp_obs.delete(0,"end")
        except Exception as e:
            messagebox.showerror("Empenho", f"Falha ao incluir item: {e}")

    def _emp_editar_item_selec(self):
        sel = self.tv_emp.selection()
        if not sel: return
        iid = sel[0]
        if "item" not in self.tv_emp.item(iid,"tags"):
            messagebox.showinfo("Empenho","Selecione um item (filho)."); return
        payload = self.tv_emp.item(iid,"text")
        try:
            d = eval(payload)
        except Exception:
            return
        self._emp_item_editando = d.get("id")
        # joga para edição
        self.e_emp_num.delete(0,"end"); self.e_emp_num.insert(0, d.get("num") or "")
        self.e_emp_cod.delete(0,"end"); self.e_emp_cod.insert(0, d.get("cod") or "")
        self.e_emp_nome.delete(0,"end"); self.e_emp_nome.insert(0, d.get("nome") or "")
        self.e_emp_qt.delete(0,"end"); self.e_emp_qt.insert(0, str(d.get("qt") or 0))
        self.e_emp_vu.set_value(Decimal(str(d.get("vu") or 0)))
        self._calc_total(self.e_emp_qt, self.e_emp_vu, self.e_emp_vt)
        self.e_emp_obs.delete(0,"end"); self.e_emp_obs.insert(0, d.get("obs") or "")

    def _emp_excluir_item_selec(self):
        sel = self.tv_emp.selection()
        if not sel: return
        iid = sel[0]
        if "item" not in self.tv_emp.item(iid,"tags"):
            messagebox.showinfo("Empenho","Selecione um item (filho)."); return
        payload = self.tv_emp.item(iid,"text")
        try:
            d = eval(payload)
        except Exception:
            return
        if not messagebox.askyesno("Confirmar","Excluir o item do empenho?"):
            return
        try:
            banco.empenho_item_excluir(d.get("id"))
            self._carregar_empenhos(refresh_num=d.get("num"))
        except Exception as e:
            messagebox.showerror("Empenho", f"Falha ao excluir: {e}")

    def _carregar_empenhos(self, refresh_num: str|None=None):
        fid = self._fid()
        for i in self.tv_emp.get_children():
            self.tv_emp.delete(i)
        if not fid: return

        hdrs = banco.empenho_cabecalhos_listar(fornecedor_id=fid)
        nome_f = self.cb_fornec.get()
        for h in hdrs:
            num = h.get("numero_empenho") or "-"
            iid = self.tv_emp.insert("", "end", text="", values=(
                nome_f, num, str(h.get("itens_qtd",0)), formatar_moeda_br(h.get("valor_total",0))
            ), tags=("cab", f"emp_{num}"))
            if refresh_num and num == refresh_num:
                self._popular_itens_empenho(iid, num, fid)

    def _emp_on_open(self, event):
        iid = self.tv_emp.focus()
        tags = self.tv_emp.item(iid,"tags")
        num = None
        for t in tags:
            if t.startswith("emp_"): num = t.split("_",1)[1]; break
        if num:
            for ch in self.tv_emp.get_children(iid):
                self.tv_emp.delete(ch)
            self._popular_itens_empenho(iid, num, self._fid())

    def _popular_itens_empenho(self, parent_iid, num: str, fornecedor_id: int):
        itens = banco.empenho_itens_listar(num, fornecedor_id)
        idx = 1
        for it in itens:
            vt = Decimal(str(it.get("vl_total",0))).quantize(Decimal("0.01"))
            vu = Decimal(str(it.get("vl_unit",0))).quantize(Decimal("0.01"))
            payload = {
                "id": it["id"], "num": num,
                "cod": it.get("cod_aghu",""), "nome": it.get("nome_item",""),
                "qt": "", "vu": float(vu), "vt": float(vt), "obs": it.get("observacao","") or ""
            }
            self.tv_emp.insert(parent_iid, "end", text=str(payload), values=(
                f"Item {idx}", payload["cod"], "", formatar_moeda_br(vt)
            ), tags=("item",))
            idx += 1

    def _emp_on_double_click(self, event):
        # duplo clique no cabeçalho só expande; edição é pelo item
        pass
