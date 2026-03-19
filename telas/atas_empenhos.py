# telas/atas_empenhos.py
import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import ast

import banco
# Reaproveita widgets e util de moeda/data da tela de Notas
from telas.notas import MoedaEntry, DataEntry, formatar_moeda_br
from tkinter.scrolledtext import ScrolledText


class TelaAtasEmpenhos(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")
        try:
            master.winfo_toplevel().title("Controle de Notas e Empenhos - Atas & Empenhos")
        except Exception:
            pass

        banco.criar_tabelas()

        # ---------- Fornecedor (comum às abas) ----------
        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=12, pady=8)
        tk.Label(topo, text="Fornecedor:", bg="white").pack(side="left")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.pack(side="left", padx=6)
        self.cb_fornec.bind("<<ComboboxSelected>>", lambda e: self._recarregar_tudo())

        # ---------- Notebook principal ----------
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=10)

        self._montar_aba_atas()
        self._montar_aba_empenhos()
        self._emp_ata_item_id_sel = None

        self._map_emp_ata = {}

        # Estado
        self.map_fornec = {}
        self._carregar_fornecedores()
        self._recarregar_tudo()

    # =========================================================
    #                       ABA ATAS
    # =========================================================
    def _montar_aba_atas(self):
        aba = tk.Frame(self.nb, bg="white")
        self.nb.add(aba, text="Atas")

        # ----- Cabeçalho da ATA -----
        hdr = ttk.LabelFrame(aba, text="Cabeçalho da ATA")
        hdr.pack(fill="x", padx=6, pady=6)

        tk.Label(hdr, text="Nº ATA*:").grid(row=0, column=0, sticky="w", padx=6, pady=3)
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

        # ----- Item da ATA -----
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

        # recálculo
        self.e_ai_qt.bind("<KeyRelease>", lambda e: self._calc_total(self.e_ai_qt, self.e_ai_vu, self.e_ai_vt))
        self.e_ai_vu.bind("<KeyRelease>", lambda e: self._calc_total(self.e_ai_qt, self.e_ai_vu, self.e_ai_vt))

        btns_it = tk.Frame(it, bg="white"); btns_it.grid(row=0, column=6, rowspan=3, sticky="ne", padx=(10,0))
        self.btn_ata_add = ttk.Button(btns_it, text="Adicionar item", command=self._ata_add_or_save_item)
        self.btn_ata_add.pack(fill="x", pady=2)
        ttk.Button(btns_it, text="Editar item selec.", command=self._ata_editar_item_selec).pack(fill="x", pady=2)
        ttk.Button(btns_it, text="Excluir item selec.", command=self._ata_excluir_item_selec).pack(fill="x", pady=2)

        # ----- Catálogo (hierárquico) -----
        box = ttk.LabelFrame(aba, text="Atas cadastradas (clique no cabeçalho para ver os itens)")
        box.pack(fill="both", expand=True, padx=6, pady=6)

        self.tv_atas = ttk.Treeview(
            box,
            columns=("forn","numero","vig_i","vig_f","status","qtd","saldo","_ata_id","_item_id","_payload"),
            show="tree headings", height=10
        )
        heads = ("Fornecedor","Nº ATA","Vigência (ini)","Vigência (fim)","Status","Itens","Saldo")
        widths = (240,120,110,110,120,70,120)
        for c,h,w in zip(("forn","numero","vig_i","vig_f","status","qtd","saldo"), heads, widths):
            self.tv_atas.heading(c, text=h)
            self.tv_atas.column(c, width=w, anchor="w")
        # colunas ocultas
        self.tv_atas.column("_ata_id", width=0, stretch=False)
        self.tv_atas.column("_item_id", width=0, stretch=False)
        self.tv_atas.column("_payload", width=0, stretch=False)

        self.tv_atas.pack(fill="both", expand=True, padx=6, pady=6)
        self.tv_atas.bind("<<TreeviewOpen>>", self._atas_on_open)
        self.tv_atas.bind("<Double-1>", self._atas_on_double_click)
        self.tv_atas.bind("<<TreeviewClose>>", self._atas_on_close)

        bar = tk.Frame(box, bg="white"); bar.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(bar, text="Recarregar", command=self._carregar_atas).pack(side="left")
        ttk.Button(bar, text="Expandir tudo", command=self._atas_expandir_tudo).pack(side="left", padx=6)
        ttk.Button(bar, text="Debug", command=self._debug_ata).pack(side="left", padx=6)

        # estado de edição e expansão
        self._ata_id_editando = None
        self._ata_item_editando = None
        self._atas_expandidas = set()

    # ========================================================
    #                     DEBUG TEMPORÁRIO
    # ========================================================
    def _debug_ata(self):
        """Abre um relatório com o estado atual da ATA no banco (itens, empenhos, view de saldo e triggers)."""
        # 1) Qual ATA?
        ata_id = None
        if getattr(self, "_ata_id_editando", None):
            ata_id = self._ata_id_editando
        else:
            try:
                iid = self.tv_atas.focus()
                if iid:
                    tags = self.tv_atas.item(iid, "tags")
                    if "cab" in tags:
                        ata_id = int(self.tv_atas.set(iid, "_ata_id") or 0)
            except Exception:
                ata_id = None

        if not ata_id:
            messagebox.showinfo("Debug", "Selecione o cabeçalho da ATA (ou carregue-a no formulário) e tente novamente.")
            return

        # 2) Consultas
        try:
            conn = banco.conectar(); cur = conn.cursor()

            cur.execute("SELECT * FROM vw_saldo_ata_total WHERE ata_id=?", (ata_id,))
            row_hdr = cur.fetchone()
            hdr_lines = []
            if row_hdr:
                r = dict(row_hdr)
                hdr_lines.append(f"ATA id={r.get('ata_id')}  numero={r.get('numero')}  fornecedor_id={r.get('fornecedor_id')}")
                hdr_lines.append(f"vigencia_ini={r.get('vigencia_ini')}  vigencia_fim={r.get('vigencia_fim')}  status={r.get('status')}")
                hdr_lines.append(f"valor_total_ata={r.get('valor_total_ata')}  valor_empenhado={r.get('valor_empenhado') if 'valor_empenhado' in r else 'N/A'}  valor_consumido={r.get('valor_consumido')}  valor_saldo={r.get('valor_saldo')}")
            else:
                hdr_lines.append("(sem linha na view vw_saldo_ata_total)")

            cur.execute("""
                SELECT id, cod_aghu, nome_item, qtde_total, vl_unit, vl_total, observacao
                  FROM atas_itens
                 WHERE ata_id=?
                 ORDER BY id
            """, (ata_id,))
            itens = [dict(x) for x in cur.fetchall()]

            cur.execute("""
                SELECT e.id, e.numero_empenho, e.cod_aghu, e.qtde, e.vl_unit, e.vl_total, e.ata_item_id
                  FROM empenhos e
                 WHERE e.ata_item_id IN (SELECT id FROM atas_itens WHERE ata_id = ?)
                 ORDER BY e.id
            """, (ata_id,))
            emps = [dict(x) for x in cur.fetchall()]

            cur.execute("""
                SELECT name, tbl_name, sql
                  FROM sqlite_master
                 WHERE type='trigger'
                 ORDER BY name
            """)
            triggers = [dict(name=r[0], tbl_name=r[1], sql=r[2]) for r in cur.fetchall()]

            conn.close()
        except Exception as ex:
            messagebox.showerror("Debug", f"Falha ao consultar o banco: {ex}")
            return

        # 3) Monta relatório
        def fmt_money(v):
            try:
                return formatar_moeda_br(Decimal(str(v)).quantize(Decimal("0.01")))
            except Exception:
                return str(v)

        lines = []
        lines.append("===== DEBUG ATA =====")
        lines.append(f"ata_id: {ata_id}")
        lines.append("\n-- Cabeçalho (vw_saldo_ata_total) --")
        lines.extend(hdr_lines)

        lines.append("\n-- Itens da ATA (atas_itens) --")
        lines.append(f"total_itens={len(itens)}")
        for it in itens:
            lines.append(
                f"[item_id={it['id']}] cod={it.get('cod_aghu','')}  nome={it.get('nome_item','')}"
                f"  qtde_total={it.get('qtde_total',0)}  vl_unit={fmt_money(it.get('vl_unit',0))}  vl_total={fmt_money(it.get('vl_total',0))}"
            )

        lines.append("\n-- Empenhos vinculados a itens desta ATA (empenhos) --")
        lines.append(f"total_empenhos={len(emps)}")
        for e in emps:
            lines.append(
                f"[emp_id={e['id']}] num={e.get('numero_empenho','')}  cod={e.get('cod_aghu','')}  qtde={e.get('qtde',0)}"
                f"  vl_unit={fmt_money(e.get('vl_unit',0))}  vl_total={fmt_money(e.get('vl_total',0))}  ata_item_id={e.get('ata_item_id')}"
            )

        lines.append("\n-- Triggers existentes --")
        if not triggers:
            lines.append("(nenhum trigger)")
        else:
            for t in triggers:
                lines.append(f"name={t['name']}  tbl={t['tbl_name']}")

        texto = "\n".join(lines)

        # 4) Mostra janela
        top = tk.Toplevel(self)
        top.title(f"Debug ATA {ata_id}")
        top.geometry("900x600+120+80")

        frm = tk.Frame(top, bg="white"); frm.pack(fill="both", expand=True)
        st = ScrolledText(frm, wrap="word")
        st.pack(fill="both", expand=True, padx=8, pady=8)
        st.insert("1.0", texto)
        st.configure(state="disabled")

        bar = tk.Frame(frm, bg="white"); bar.pack(fill="x", padx=8, pady=(0,8))
        def _copy():
            try:
                top.clipboard_clear()
                top.clipboard_append(texto)
                messagebox.showinfo("Debug","Conteúdo copiado para a área de transferência.")
            except Exception:
                pass
        ttk.Button(bar, text="Copiar tudo", command=_copy).pack(side="left")
        ttk.Button(bar, text="Fechar", command=top.destroy).pack(side="right")

    # =========================================================
    #                     ABA EMPENHOS
    # =========================================================
    def _montar_aba_empenhos(self):
        aba = tk.Frame(self.nb, bg="white")
        self.nb.add(aba, text="Empenhos")

        frm = ttk.LabelFrame(aba, text="Item do Empenho (agrupado por nº)")
        frm.pack(fill="x", padx=6, pady=6)

        # Vincular à ATA (linha 0)
        tk.Label(frm, text="Vincular à ATA:").grid(row=0, column=0, sticky="w", padx=6, pady=(0,4))
        self.cb_emp_ata = ttk.Combobox(frm, state="readonly", width=40)
        self.cb_emp_ata.grid(row=0, column=1, columnspan=3, sticky="w", padx=6, pady=(0,4))
        self.cb_emp_ata.bind("<<ComboboxSelected>>", lambda e: self._emp_carregar_itens_da_ata())

        # Lista de itens da ATA (linha 1)
        cols_ata = ("cod","desc","vu","_id")
        self.tv_emp_ata = ttk.Treeview(frm, columns=cols_ata, show="headings", height=5)
        for c,h,w in zip(cols_ata, ("Cód AGHU","Descrição","Vlr Unit","_id"), (100,280,120,0)):
            self.tv_emp_ata.heading(c, text=h)
            self.tv_emp_ata.column(c, width=w if c!="_id" else 0, anchor="w", stretch=False)
        self.tv_emp_ata.grid(row=1, column=0, columnspan=7, sticky="we", padx=6, pady=(0,6))
        self.tv_emp_ata.bind("<Double-1>", lambda e: self._emp_puxar_item_ata())

        # Linha 2: Nº Empenho, Cód, Descrição
        tk.Label(frm, text="Nº Empenho*:").grid(row=2, column=0, sticky="w", padx=6)
        self.e_emp_num = ttk.Entry(frm, width=20); self.e_emp_num.grid(row=2, column=1, sticky="w", padx=6)

        tk.Label(frm, text="Cód AGHU*:").grid(row=2, column=2, sticky="w", padx=6)
        self.e_emp_cod = ttk.Entry(frm, width=18); self.e_emp_cod.grid(row=2, column=3, sticky="w", padx=6)
        self.e_emp_cod.configure(state="readonly")

        tk.Label(frm, text="Descrição*:").grid(row=2, column=4, sticky="w", padx=6)
        self.e_emp_nome = ttk.Entry(frm, width=40); self.e_emp_nome.grid(row=2, column=5, sticky="w", padx=6)
        self.e_emp_nome.configure(state="readonly")

        # Linha 3: Qtde, Vlr Unit, Vlr Total
        tk.Label(frm, text="Qtde*:").grid(row=3, column=0, sticky="w", padx=6)
        self.e_emp_qt = ttk.Entry(frm, width=10); self.e_emp_qt.grid(row=3, column=1, sticky="w", padx=6)

        tk.Label(frm, text="Vlr Unit*:").grid(row=3, column=2, sticky="w", padx=6)
        self.e_emp_vu = MoedaEntry(frm, width=18); self.e_emp_vu.grid(row=3, column=3, sticky="w", padx=6)

        # Trava/Libera edição do VU (padrão: travado)
        self._lock_vu = tk.BooleanVar(value=True)
        frm_chk = tk.Frame(frm, bg="white")
        frm_chk.grid(row=3, column=6, sticky="nw", padx=(10,0))
        ttk.Checkbutton(frm_chk, text="Liberar edição de Vlr Unit", variable=self._lock_vu,
                        command=self._toggle_lock_vu).pack(anchor="w")

        tk.Label(frm, text="Vlr Total:").grid(row=3, column=4, sticky="w", padx=6)
        self.e_emp_vt = ttk.Entry(frm, width=18, state="readonly"); self.e_emp_vt.grid(row=3, column=5, sticky="w", padx=6)

        self.e_emp_qt.bind("<KeyRelease>", lambda e: self._calc_total(self.e_emp_qt, self.e_emp_vu, self.e_emp_vt))
        self.e_emp_vu.bind("<KeyRelease>", lambda e: self._calc_total(self.e_emp_qt, self.e_emp_vu, self.e_emp_vt))

        # Linha 4: Observação
        tk.Label(frm, text="Observação:").grid(row=4, column=0, sticky="w", padx=6)
        self.e_emp_obs = ttk.Entry(frm, width=60); self.e_emp_obs.grid(row=4, column=1, columnspan=5, sticky="w", padx=6, pady=(0,6))

        # Botões (ao lado das linhas 2–4)
        btns = tk.Frame(frm, bg="white"); btns.grid(row=2, column=6, rowspan=3, sticky="ne", padx=(10,0))
        self.btn_emp_add = ttk.Button(btns, text="Adicionar item", command=self._emp_add_or_save_item)
        self.btn_emp_add.pack(fill="x", pady=2)
        ttk.Button(btns, text="Editar item selec.", command=self._emp_editar_item_selec).pack(fill="x", pady=2)
        ttk.Button(btns, text="Excluir item selec.", command=self._emp_excluir_item_selec).pack(fill="x", pady=2)

        box = ttk.LabelFrame(aba, text="Empenhos — agrupados por número (clique para ver itens)")
        box.pack(fill="both", expand=True, padx=6, pady=6)

        self.tv_emp = ttk.Treeview(
            box,
            columns=("forn","num","qtd","total","_num","_item_id","_payload"),
            show="tree headings", height=10
        )
        for c,h,w in zip(("forn","num","qtd","total"), ("Fornecedor","Nº Empenho","Itens","Total"), (240,160,80,140)):
            self.tv_emp.heading(c, text=h)
            self.tv_emp.column(c, width=w, anchor="w")
        self.tv_emp.column("_num", width=0, stretch=False)
        self.tv_emp.column("_item_id", width=0, stretch=False)
        self.tv_emp.column("_payload", width=0, stretch=False)

        self.tv_emp.pack(fill="both", expand=True, padx=6, pady=6)
        self.tv_emp.bind("<<TreeviewOpen>>", self._emp_on_open)
        self.tv_emp.bind("<Double-1>", self._emp_on_double_click)

        bar = tk.Frame(box, bg="white"); bar.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(bar, text="Recarregar", command=self._carregar_empenhos).pack(side="left")
        ttk.Button(bar, text="Excluir Nº empenho selec.", command=self._emp_excluir_cabecalho).pack(side="left", padx=6)

        self._ata_item_editando = None
        self._emp_item_editando = None

    def _emp_listar_atas_do_fornecedor(self):
        """
        Preenche a combo 'Vincular à ATA' com as ATAs do fornecedor selecionado,
        populando self._map_emp_ata = {texto_da_combo: ata_id}.
        Depois de popular, se houver uma ATA selecionável, carrega seus itens na grade de baixo.
        """
        fid = self._fid()
        # Limpa combo e mapa caso não haja fornecedor
        if not fid:
            self._map_emp_ata = {}
            self.cb_emp_ata["values"] = []
            return
    
        # Busca ATAs do fornecedor (view agrega saldo/itens)
        rows = banco.atas_hdr_listar(fornecedor_id=fid)
    
        # Monta tuplas (texto visível -> ata_id)
        vals = []
        for r in rows:
            num = r.get("numero", "")
            Ini = self._fmt_data(r.get("vigencia_ini"))
            Fim = self._fmt_data(r.get("vigencia_fim"))
            texto = f"{num} ({Ini} → {Fim})"
            vals.append((texto, r["ata_id"]))
    
        # Atualiza mapa e combo
        self._map_emp_ata = dict(vals)
        self.cb_emp_ata["values"] = [k for k, _ in vals]
    
        # Se a combo está vazia e temos opções, seleciona a primeira e carrega os itens
        if vals and not self.cb_emp_ata.get():
            self.cb_emp_ata.current(0)
            self._emp_carregar_itens_da_ata()

    def _toggle_lock_vu(self):
        try:
            self.e_emp_vu.configure(state="readonly" if self._lock_vu.get() else "normal")
        except Exception:
            pass

    def _emp_carregar_itens_da_ata(self):
        """Carrega na grade (tv_emp_ata) os itens da ATA escolhida na combo 'Vincular à ATA'."""
        # Zera seleção atual de item
        self._emp_ata_item_id_sel = None
    
        # Limpa a grid
        for i in self.tv_emp_ata.get_children():
            self.tv_emp_ata.delete(i)
    
        # Mapa pode não existir no primeiro disparo em alguns temas do Tk
        map_atas = getattr(self, "_map_emp_ata", {})
        if not isinstance(map_atas, dict):
            map_atas = {}
    
        texto = self.cb_emp_ata.get() or ""
        ata_id = map_atas.get(texto)
        if not ata_id:
            return  # nada a carregar
    
        # Busca itens da ATA e preenche a grid abaixo (cód, desc, vl unit, id)
        itens = banco.ata_itens_listar_por_ata(ata_id)
        for it in itens:
            self.tv_emp_ata.insert(
                "", "end",
                values=(
                    it.get("cod_aghu", ""),
                    it.get("nome_item", ""),
                    formatar_moeda_br(Decimal(str(it.get('vl_unit', 0))).quantize(Decimal("0.01"))),
                    it.get("id")
                )
            )

    def _emp_puxar_item_ata(self):
        """
        Handler de duplo clique na grade de itens da ATA (aba Empenhos).
        Preenche o formulário do empenho com Cód/Descrição/Vlr Unit (travados por padrão).
        """
        sel = self.tv_emp_ata.selection()
        if not sel:
            return
    
        # Lê a linha selecionada: (cod, desc, vu_formatado, ata_item_id)
        v = self.tv_emp_ata.item(sel[0], "values")
        if not v or len(v) < 4:
            return
        cod, desc, vu_fmt, ata_item_id = v[0], v[1], v[2], v[3]
    
        # guarda o vínculo ao item da ATA
        try:
            self._emp_ata_item_id_sel = int(ata_item_id)
        except Exception:
            self._emp_ata_item_id_sel = None
    
        # 1) Cód (readonly)
        self.e_emp_cod.configure(state="normal")
        self.e_emp_cod.delete(0, "end")
        self.e_emp_cod.insert(0, cod)
        self.e_emp_cod.configure(state="readonly")
    
        # 2) Descrição (readonly)
        self.e_emp_nome.configure(state="normal")
        self.e_emp_nome.delete(0, "end")
        self.e_emp_nome.insert(0, desc)
        self.e_emp_nome.configure(state="readonly")
    
        # 3) Vlr Unit (vem da ATA) — readonly por padrão; checkbox pode liberar
        try:
            vu = Decimal(str(vu_fmt).replace("R$", "").strip().replace(".", "").replace(",", "."))
        except Exception:
            vu = Decimal("0")
        self.e_emp_vu.set_value(vu)
        # respeita travamento atual
        self.e_emp_vu.configure(state="readonly" if getattr(self, "_lock_vu", tk.BooleanVar(value=True)).get() else "normal")
    
        # 4) Limpa Qtde e Vlr Total para o usuário informar e recalcular
        self.e_emp_qt.delete(0, "end")
        self.e_emp_vt.configure(state="normal"); self.e_emp_vt.delete(0, "end"); self.e_emp_vt.configure(state="readonly")
        self._calc_total(self.e_emp_qt, self.e_emp_vu, self.e_emp_vt)
    
        # foco amigável (opcional): põe o cursor no Nº do empenho
        try:
            self.e_emp_num.focus_set()
        except Exception:
            pass
    ``


    # =========================================================
    #                     Utilidades Comuns
    # =========================================================
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
        self._emp_listar_atas_do_fornecedor()

    def _calc_total(self, e_qt: ttk.Entry, e_vu: MoedaEntry, e_vt: ttk.Entry):
        try:
            qt = Decimal(str((e_qt.get() or "0").replace(",", ".")))
        except Exception:
            qt = Decimal("0")
        vu = e_vu.value()
        total = (qt * vu).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        e_vt.configure(state="normal"); e_vt.delete(0, "end")
        e_vt.insert(0, formatar_moeda_br(total)); e_vt.configure(state="readonly")

    # =========================================================
    #                           ATAS: Ações
    # =========================================================
    def _nova_ata(self):
        self._ata_id_editando = None
        self._ata_item_editando = None
        self.e_ata_num.delete(0, "end")
        self.e_ata_ini.set_value("")
        self.e_ata_fim.set_value("")
        self.cb_ata_status.set("Em vigência")
        self.e_ata_obs.delete(0, "end")
        self.btn_ata_add.config(text="Adicionar item")

    def _salvar_ata(self):
        fid = self._fid()
        if not fid:
            messagebox.showwarning("ATA", "Selecione o fornecedor."); return

        numero = (self.e_ata_num.get() or "").strip()
        if not numero:
            messagebox.showwarning("ATA", "Informe o Nº da ATA."); return

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
                messagebox.showinfo("ATA", "Cabeçalho atualizado.")
            else:
                self._ata_id_editando = banco.ata_hdr_inserir(d)
                messagebox.showinfo("ATA", "ATA criada. Agora adicione os itens.")
        except Exception as e:
            messagebox.showerror("ATA", f"Falha ao salvar: {e}")

        self._carregar_atas()
        self._emp_listar_atas_do_fornecedor()  # manter combo atualizada

    def _excluir_ata(self):
        if not self._ata_id_editando:
            messagebox.showwarning("ATA", "Nenhuma ATA carregada no cabeçalho.")
            return

        if not messagebox.askyesno("Confirmar", "Excluir a ATA e todos os itens? Os empenhos vinculados serão removidos."):
            return
        try:
            banco.ata_hdr_excluir(self._ata_id_editando)
            self._nova_ata()
            # Recarrega listas
            self._carregar_atas()
            self._carregar_empenhos()
            self._emp_listar_atas_do_fornecedor()
            messagebox.showinfo("ATA", "ATA e empenhos vinculados excluídos.")
        except Exception as e:
            messagebox.showerror("ATA", f"Falha ao excluir: {e}")

    def _ata_add_or_save_item(self):
        if not self._ata_id_editando:
            messagebox.showwarning("ATA", "Salve o cabeçalho da ATA antes de incluir itens."); return

        # leitura
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
            "qtde_total": qt, "vl_unit": vu, "vl_total": vt,
            "observacao": (self.e_ai_obs.get() or "").strip()
        }
        if not (d["cod_aghu"] and d["nome_item"] and d["qtde_total"] and d["vl_unit"]):
            messagebox.showwarning("ATA", "Preencha cód, descrição, qtde e Vlr Unit."); return

        try:
            if self._ata_item_editando:
                banco.ata_item_atualizar(self._ata_item_editando, d)
                self._ata_item_editando = None
                self.btn_ata_add.config(text="Adicionar item")
            else:
                banco.ata_item_inserir_v2(d)
            self._carregar_atas(refresh_items_of=self._ata_id_editando)
            # limpa campos do item
            self.e_ai_cod.delete(0, "end"); self.e_ai_nome.delete(0, "end")
            self.e_ai_qt.delete(0, "end"); self.e_ai_vu.set_value(0)
            self.e_ai_vt.configure(state="normal"); self.e_ai_vt.delete(0, "end"); self.e_ai_vt.configure(state="readonly")
            self.e_ai_obs.delete(0, "end")
        except Exception as e:
            messagebox.showerror("ATA", f"Falha ao salvar item: {e}")

    def _ata_editar_item_selec(self):
        sel = self.tv_atas.selection()
        if not sel: return
        iid = sel[0]
        if "item" not in self.tv_atas.item(iid, "tags"):
            messagebox.showinfo("ATA", "Selecione um item (filho)."); return
        payload = self.tv_atas.set(iid, "_payload")
        try:
            d = ast.literal_eval(payload)
        except Exception:
            messagebox.showwarning("ATA", "Não foi possível carregar o item."); return
        self._ata_item_editando = d.get("id")
        # joga nos campos
        self.e_ai_cod.delete(0, "end"); self.e_ai_cod.insert(0, d.get("cod") or "")
        self.e_ai_nome.delete(0, "end"); self.e_ai_nome.insert(0, d.get("nome") or "")
        self.e_ai_qt.delete(0, "end"); self.e_ai_qt.insert(0, str(d.get("qt") or "0"))
        self.e_ai_vu.set_value(Decimal(str(d.get("vu") or 0)))
        self._calc_total(self.e_ai_qt, self.e_ai_vu, self.e_ai_vt)
        self.e_ai_obs.delete(0, "end"); self.e_ai_obs.insert(0, d.get("obs") or "")
        self.btn_ata_add.config(text="Salvar edição")

    def _ata_excluir_item_selec(self):
        sel = self.tv_atas.selection()
        if not sel: return
        iid = sel[0]
        if "item" not in self.tv_atas.item(iid, "tags"):
            messagebox.showinfo("ATA", "Selecione um item (filho)."); return
        payload = self.tv_atas.set(iid, "_payload")
        try:
            d = ast.literal_eval(payload)
        except Exception:
            return
        if not messagebox.askyesno("Confirmar", "Excluir o item selecionado?"):
            return
        try:
            banco.ata_item_excluir(d.get("id"))
            self._carregar_atas(refresh_items_of=d.get("ata_id"))
        except Exception as e:
            messagebox.showerror("ATA", f"Falha ao excluir item: {e}")

    def _carregar_atas(self, refresh_items_of: int | None = None):
        fid = self._fid()
        for i in self.tv_atas.get_children():
            self.tv_atas.delete(i)
        if not fid: return

        rows = banco.atas_hdr_listar(fornecedor_id=fid)
        forn_nome = self.cb_fornec.get()

        # Reabrir o que estava expandido
        reabrir = set()
        if refresh_items_of:
            reabrir.add(int(refresh_items_of))
        reabrir.update(getattr(self, "_atas_expandidas", set()))

        for r in rows:
            vig_i = self._fmt_data(r.get("vigencia_ini"))
            vig_f = self._fmt_data(r.get("vigencia_fim"))
            saldo = formatar_moeda_br(r.get("valor_saldo", 0))
            ata_id = int(r["ata_id"])
            iid = self.tv_atas.insert(
                "", "end", text="",
                values=(forn_nome, r.get("numero",""), vig_i, vig_f,
                        r.get("status",""), str(r.get("itens_qtd",0)), saldo,
                        ata_id, "", ""),
                tags=("cab", f"ata_{ata_id}")
            )
            if ata_id in reabrir:
                # limpa filhos e repopula
                for ch in self.tv_atas.get_children(iid):
                    self.tv_atas.delete(ch)
                self._popular_itens_ata(iid, ata_id)

    def _atas_on_open(self, _evt):
        iid = self.tv_atas.focus()
        tags = self.tv_atas.item(iid, "tags")
        ata_id = None
        for t in tags:
            if t.startswith("ata_"):
                ata_id = int(t.split("_", 1)[1]); break
        if ata_id:
            # marca como expandida
            self._atas_expandidas.add(ata_id)
            # limpa filhos e repopula
            for ch in self.tv_atas.get_children(iid):
                self.tv_atas.delete(ch)
            self._popular_itens_ata(iid, ata_id)

    def _atas_on_close(self, _evt):
        iid = self.tv_atas.focus()
        tags = self.tv_atas.item(iid, "tags")
        for t in tags:
            if t.startswith("ata_"):
                ata_id = int(t.split("_", 1)[1])
                if ata_id in self._atas_expandidas:
                    self._atas_expandidas.remove(ata_id)
                break

    def _popular_itens_ata(self, parent_iid, ata_id: int):
        # Itens da ATA sempre aparecem; exibimos Qtde Empenhada e Saldo (por quantidade)
        itens = banco.ata_itens_listar_por_ata_com_saldo(ata_id)

        # Subcabeçalho mapeado às 7 colunas do treeview
        self.tv_atas.insert(
            parent_iid, "end", text="",
            values=("Itens", "Cód AGHU", "Qtde ATA", "Empenhado", "Saldo", "Vlr Unit", "Vlr Total", "", "", ""),
            tags=("subheader",)
        )

        for idx, it in enumerate(itens, start=1):
            qt_total = it.get("qtde_total", 0)
            qt_emp   = it.get("qtde_empenhada", 0)
            qt_saldo = it.get("qtde_saldo", 0)
            vu = Decimal(str(it.get("vl_unit",0))).quantize(Decimal("0.01"))
            vt = Decimal(str(it.get("vl_total",0))).quantize(Decimal("0.01"))
            payload = {
                "id": it["id"], "ata_id": ata_id,
                "cod": it.get("cod_aghu",""), "nome": it.get("nome_item",""),
                "qt": qt_total, "qt_empenhada": qt_emp, "qt_saldo": qt_saldo,
                "vu": float(vu), "vt": float(vt), "obs": it.get("observacao","") or ""
            }
            self.tv_atas.insert(
                parent_iid, "end", text="",
                values=(f"Item {idx}", payload["cod"], str(qt_total), str(qt_emp), str(qt_saldo),
                        formatar_moeda_br(vu), formatar_moeda_br(vt),
                        "", str(payload["id"]), str(payload)),
                tags=("item",)
            )

    def _atas_expandir_tudo(self):
        # Registra todas como expandidas e popula
        self._atas_expandidas = set()
        for iid in self.tv_atas.get_children(""):
            try:
                ata_id = int(self.tv_atas.set(iid, "_ata_id") or 0)
            except Exception:
                ata_id = 0
            if ata_id:
                self._atas_expandidas.add(ata_id)
                # limpa filhos e repopula
                for ch in self.tv_atas.get_children(iid):
                    self.tv_atas.delete(ch)
                self._popular_itens_ata(iid, ata_id)

    def _atas_on_double_click(self, _evt):
        # Duplo clique no cabeçalho → carrega a ATA no formulário
        iid = self.tv_atas.focus()
        tags = self.tv_atas.item(iid, "tags")
        if "cab" not in tags: return
        ata_id = int(self.tv_atas.set(iid, "_ata_id") or 0)
        if not ata_id: return
        rows = banco.atas_hdr_listar(fornecedor_id=self._fid())
        row = next((r for r in rows if int(r["ata_id"]) == ata_id), None)
        if not row: return
        self._ata_id_editando = ata_id
        self.e_ata_num.delete(0, "end"); self.e_ata_num.insert(0, row.get("numero",""))
        self.e_ata_ini.set_value(self._fmt_data(row.get("vigencia_ini")))
        self.e_ata_fim.set_value(self._fmt_data(row.get("vigencia_fim")))
        self.cb_ata_status.set(row.get("status","Em vigência"))
        self.e_ata_obs.delete(0, "end")  # view não traz obs; fica em branco
        self.btn_ata_add.config(text="Adicionar item")

    # =========================================================
    #                      EMPENHOS: Ações
    # =========================================================
    def _emp_add_or_save_item(self):
        fid = self._fid()
        if not fid:
            messagebox.showwarning("Empenho", "Selecione o fornecedor."); return
        num = (self.e_emp_num.get() or "").strip()
        if not num:
            messagebox.showwarning("Empenho", "Informe o Nº do empenho."); return
        cod = (self.e_emp_cod.get() or "").strip()
        nome = (self.e_emp_nome.get() or "").strip()
        try:
            qt = float((self.e_emp_qt.get() or "0").replace(",", "."))
        except Exception:
            qt = 0.0
        vu = float(str(self.e_emp_vu.value()))
        vt = qt * vu
        if not (cod and nome and qt and vu):
            messagebox.showwarning("Empenho", "Preencha cód, descrição, qtde e Vlr Unit."); return

        d = {
            "fornecedor_id": fid, "cod_aghu": cod, "nome_item": nome,
            "qtde": qt, "vl_unit": vu, "vl_total": vt,
            "numero_empenho": num, "observacao": (self.e_emp_obs.get() or "").strip(),
            "ata_item_id": self._emp_ata_item_id_sel  # vincula ao item da ATA (se selecionado)
        }
        try:
            if self._emp_item_editando:
                banco.empenho_item_atualizar(self._emp_item_editando, d)
                self._emp_item_editando = None
                self.btn_emp_add.config(text="Adicionar item")
            else:
                banco.empenho_inserir(d)
            self._carregar_empenhos(refresh_num=num)

            # Atualiza ATA em edição (ver Empenhado/Saldo imediatamente)
            if getattr(self, "_ata_id_editando", None):
                self._carregar_atas(refresh_items_of=self._ata_id_editando)

            # limpa
            self.e_emp_cod.configure(state="normal"); self.e_emp_cod.delete(0, "end"); self.e_emp_cod.configure(state="readonly")
            self.e_emp_nome.configure(state="normal"); self.e_emp_nome.delete(0, "end"); self.e_emp_nome.configure(state="readonly")
            self.e_emp_qt.delete(0, "end"); self.e_emp_vu.set_value(0)
            self.e_emp_vt.configure(state="normal"); self.e_emp_vt.delete(0, "end"); self.e_emp_vt.configure(state="readonly")
            self.e_emp_obs.delete(0, "end")
        except Exception as e:
            messagebox.showerror("Empenho", f"Falha ao salvar item: {e}")

    def _emp_editar_item_selec(self):
        sel = self.tv_emp.selection()
        if not sel: return
        iid = sel[0]
        if "item" not in self.tv_emp.item(iid, "tags"):
            messagebox.showinfo("Empenho","Selecione um item (linha abaixo do cabeçalho do número)."); return

        payload = self.tv_emp.set(iid, "_payload")
        if not payload:
            messagebox.showerror("Empenho","Não foi possível obter os dados do item (payload vazio)."); return
        try:
            d = ast.literal_eval(payload)
        except Exception as ex:
            messagebox.showerror("Empenho", f"Não foi possível ler os dados do item.\nDetalhe: {ex}")
            return

        self._emp_item_editando = d.get("id")
        # joga nos campos
        self.e_emp_num.delete(0,"end"); self.e_emp_num.insert(0, d.get("num") or "")
        self.e_emp_cod.configure(state="normal"); self.e_emp_cod.delete(0,"end"); self.e_emp_cod.insert(0, d.get("cod") or ""); self.e_emp_cod.configure(state="readonly")
        self.e_emp_nome.configure(state="normal"); self.e_emp_nome.delete(0,"end"); self.e_emp_nome.insert(0, d.get("nome") or ""); self.e_emp_nome.configure(state="readonly")
        self.e_emp_qt.delete(0,"end"); self.e_emp_qt.insert(0, str(d.get("qt") or 0))
        self.e_emp_vu.set_value(Decimal(str(d.get("vu") or 0)))
        self._calc_total(self.e_emp_qt, self.e_emp_vu, self.e_emp_vt)
        self.e_emp_obs.delete(0,"end"); self.e_emp_obs.insert(0, d.get("obs") or "")
        self.btn_emp_add.config(text="Salvar edição")

    def _emp_excluir_item_selec(self):
        sel = self.tv_emp.selection()
        if not sel: return
        iid = sel[0]
        if "item" not in self.tv_emp.item(iid,"tags"):
            messagebox.showinfo("Empenho","Selecione um item (linha abaixo do cabeçalho do número)."); return

        payload = self.tv_emp.set(iid, "_payload")
        if not payload:
            messagebox.showerror("Empenho","Não foi possível obter os dados do item (payload vazio)."); return
        try:
            d = ast.literal_eval(payload)
        except Exception as ex:
            messagebox.showerror("Empenho", f"Não foi possível ler os dados do item.\nDetalhe: {ex}")
            return

        if not messagebox.askyesno("Confirmar","Excluir o item do empenho?"):
            return
        try:
            banco.empenho_item_excluir(d.get("id"))
            self._carregar_empenhos(refresh_num=d.get("num"))
        except Exception as e:
            messagebox.showerror("Empenho", f"Falha ao excluir item: {e}")

    def _emp_excluir_cabecalho(self):
        sel = self.tv_emp.selection()
        if not sel:
            messagebox.showinfo("Empenho","Selecione um Nº de empenho (linha de cabeçalho).")
            return
        iid = sel[0]
        if "cab" not in self.tv_emp.item(iid, "tags"):
            messagebox.showinfo("Empenho","Selecione a linha do Nº de empenho (cabeçalho).")
            return
        num = self.tv_emp.set(iid, "_num") or self.tv_emp.item(iid, "values")[1]
        if not num:
            messagebox.showwarning("Empenho","Nº do empenho não identificado.")
            return
        if not messagebox.askyesno("Confirmar", f"Excluir TODOS os itens do Nº de empenho '{num}'?"):
            return
        try:
            afetados = banco.empenho_excluir_por_numero(self._fid(), num)
            self._carregar_empenhos()
            messagebox.showinfo("Empenho", f"Itens excluídos: {afetados}.")
        except Exception as e:
            messagebox.showerror("Empenho", f"Falha ao excluir Nº de empenho: {e}")

    def _carregar_empenhos(self, refresh_num: str | None = None):
        fid = self._fid()
        for i in self.tv_emp.get_children():
            self.tv_emp.delete(i)
        if not fid: return

        hdrs = banco.empenho_cabecalhos_listar(fornecedor_id=fid)
        nome_f = self.cb_fornec.get()
        for h in hdrs:
            num = h.get("numero_empenho") or "-"
            iid = self.tv_emp.insert(
                "", "end", text="",
                values=(nome_f, num, str(h.get("itens_qtd", 0)), formatar_moeda_br(h.get("valor_total", 0)),
                        num, "", ""),
                tags=("cab",)
            )
            if refresh_num and num == refresh_num:
                self._popular_itens_empenho(iid, num, fid)

    def _emp_on_open(self, _evt):
        iid = self.tv_emp.focus()
        num = self.tv_emp.set(iid, "_num")
        if num:
            for ch in self.tv_emp.get_children(iid):
                self.tv_emp.delete(ch)
            self._popular_itens_empenho(iid, num, self._fid())

    def _popular_itens_empenho(self, parent_iid, num: str, fornecedor_id: int):
        itens = banco.empenho_itens_listar(num, fornecedor_id)
        for idx, it in enumerate(itens, start=1):
            vu = Decimal(str(it.get("vl_unit", 0))).quantize(Decimal("0.01"))
            vt = Decimal(str(it.get("vl_total", 0))).quantize(Decimal("0.01"))
            payload = {
                "id": it["id"], "num": num,
                "cod": it.get("cod_aghu", ""), "nome": it.get("nome_item", ""),
                "qt": it.get("qtde", 0), "vu": float(vu), "vt": float(vt),
                "obs": it.get("observacao", "") or "", "ata_item_id": it.get("ata_item_id")
            }
            self.tv_emp.insert(
                parent_iid, "end", text="",
                values=(f"Item {idx}", payload["cod"], str(payload["qt"]), formatar_moeda_br(payload["vt"]),
                        "", str(payload["id"]), str(payload)),
                tags=("item",)
            )

    def _emp_on_double_click(self, _evt):
        # Duplo clique no cabeçalho apenas expande
        pass

    # =========================================================
    #                         Helpers
    # =========================================================
    def _fmt_data(self, iso: str | None):
        if not iso: return ""
        try:
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return iso
