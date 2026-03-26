# telas/orcamento.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import tempfile
from datetime import datetime

import banco
import utils


class TelaOrcamento(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")

        # ---------- Topo: fornecedor ----------
        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=12, pady=10)

        tk.Label(topo, text="Fornecedor:", bg="white").pack(side="left")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.pack(side="left", padx=6)
        self.cb_fornec.bind(
            "<<ComboboxSelected>>",
            lambda e: (
                self._reset_autosave_context(),
                self._carregar_itens_rascunho(),
                self._carregar_salvos(),
                self._carregar_msgs(),
            ),
        )

        # Controladores internos
        self._after_ids = []
        self._anexos_extra = []     # <<<<<< ANEXOS EXTRAS

        # ---------- Formulário principal ----------
        form = ttk.LabelFrame(self, text="Lançar itens para Orçamento")
        form.pack(fill="x", padx=12, pady=8)

        def campo(lbl, col, row, width=28):
            tk.Label(form, text=lbl).grid(
                column=col, row=row, sticky="w", padx=6, pady=3
            )
            e = ttk.Entry(form, width=width)
            e.grid(column=col + 1, row=row, sticky="w", padx=6, pady=3)
            return e

        self.e_cod = campo("Cód AGHU*:", 0, 0)
        self.e_nome = campo("Nome item*:", 0, 1, 40)
        self.e_qt = campo("Qtde*:", 2, 0, 12)
        self.e_vu = campo("Vlr Unit*:", 2, 1, 12)
        self.e_emp = campo("Nº Empenho:", 4, 0)

        tk.Label(form, text="Observação:").grid(column=4, row=1, sticky="w", padx=6, pady=3)
        self.e_obs = ttk.Entry(form, width=40)
        self.e_obs.grid(column=5, row=1, sticky="w", padx=6, pady=3)

        # Seleção de modelo
        tk.Label(form, text="Modelo:").grid(column=0, row=3, sticky="w", padx=6, pady=3)
        self.cb_modelo = ttk.Combobox(form, state="readonly", width=50)
        self.cb_modelo.grid(column=1, row=3, columnspan=3, sticky="w", padx=6, pady=3)
        ttk.Button(form, text="Carregar", command=self._carregar_modelo_rapido).grid(column=4, row=3, padx=6)

        # Campo de mensagem
        tk.Label(form, text="Mensagem p/ e-mail:").grid(column=0, row=4, sticky="nw", padx=6, pady=3)
        self.txt_msg = tk.Text(form, width=80, height=4)
        self.txt_msg.grid(column=1, row=4, columnspan=5, sticky="w", padx=6, pady=3)

        # Autosave
        self._autosave_job = None
        self._autosave_msg_id = None
        self._msg_editando_id = None
        self.txt_msg.bind("<KeyRelease>", lambda e: self._agendar_autosave())
        self.txt_msg.bind("<FocusOut>", lambda e: self._autosave_now())

        self._lbl_autosave = tk.Label(form, text="", fg="#2c7", bg="white")
        self._lbl_autosave.grid(column=1, row=5, columnspan=5, sticky="w", padx=6, pady=(0, 4))

        # Lado direito (botões + mensagens)
        side = tk.Frame(form, bg="white")
        side.grid(column=6, row=0, rowspan=5, sticky="ne", padx=(10, 6), pady=3)

        ttk.Button(side, text="Add", command=self._adicionar).pack(fill="x", pady=(0, 8))

        # Caixa de mensagem
        msg_box = ttk.LabelFrame(side, text="Mensagem: Modelo / Rascunho")
        msg_box.pack(fill="x")

        tk.Label(msg_box, text="Título:").pack(anchor="w", padx=6, pady=(6, 0))
        self.e_titulo_msg = ttk.Entry(msg_box, width=28)
        self.e_titulo_msg.pack(anchor="w", padx=6, pady=(0, 6))

        self.var_msg_forn = tk.BooleanVar(value=False)
        ttk.Checkbutton(msg_box, text="Vincular ao fornecedor atual", variable=self.var_msg_forn).pack(anchor="w", padx=6, pady=(0, 6))

        # Botões internos
        btns_msg = tk.Frame(msg_box, bg="white")
        btns_msg.pack(fill="x", padx=6, pady=(0, 8))

        ttk.Button(btns_msg, text="Salvar Modelo", command=lambda: self._salvar_mensagem("modelo")).pack(side="left")
        ttk.Button(btns_msg, text="Salvar Rascunho", command=lambda: self._salvar_mensagem("rascunho")).pack(side="left", padx=6)

        # <<<<<< BOTÃO DE ANEXAR ARQUIVO >>>>>>
        ttk.Button(msg_box, text="Anexar arquivo", command=self._add_anexo).pack(anchor="w", padx=6, pady=(0, 6))
        # ---------- Itens em rascunho ----------
        lf_rasc = ttk.LabelFrame(self, text="Itens em rascunho (não salvos)")
        lf_rasc.pack(fill="both", expand=True, padx=12, pady=(4, 2))

        cols = ("cod", "nome", "qt", "vu", "emp", "obs", "vl_total")
        heads = ("Cód AGHU", "Nome", "Qtde", "Vlr Unit", "Nº Empenho", "Obs", "Vlr Total")
        widths = (100, 260, 60, 90, 120, 260, 100)
        self.tv = ttk.Treeview(lf_rasc, columns=cols, show="headings", height=6)
        for c, h, w in zip(cols, heads, widths):
            self.tv.heading(c, text=h); self.tv.column(c, width=w, anchor="w")
        self.tv.pack(fill="both", expand=True, padx=6, pady=6)

        # ---------- Ações principais ----------
        rod = tk.Frame(self, bg="white")
        rod.pack(fill="x", padx=12, pady=8)
        self.btn_email = ttk.Button(rod, text="Enviar por e-mail", command=self._enviar_email)
        self.btn_email.pack(side="right", padx=6)

        self.btn_export = ttk.Button(rod, text="Exportar para Excel", command=self._exportar_excel)
        self.btn_export.pack(side="right", padx=6)

        # ---------- Histórico ----------
        lf_hist = ttk.LabelFrame(self, text="Orçamentos já salvos (no banco) — por fornecedor")
        lf_hist.pack(fill="both", expand=True, padx=12, pady=(2, 8))

        filtros = tk.Frame(lf_hist)
        filtros.pack(fill="x", padx=6, pady=(6, 0))

        tk.Label(filtros, text="De (YYYY-MM-DD):").pack(side="left")
        self.f_data_ini = ttk.Entry(filtros, width=12); self.f_data_ini.pack(side="left", padx=4)

        tk.Label(filtros, text="Até:").pack(side="left")
        self.f_data_fim = ttk.Entry(filtros, width=12); self.f_data_fim.pack(side="left", padx=4)

        tk.Label(filtros, text="Termo (cód/nome/obs):").pack(side="left", padx=(12, 0))
        self.f_busca = ttk.Entry(filtros, width=28); self.f_busca.pack(side="left", padx=4)

        tk.Label(filtros, text="Empenho:").pack(side="left", padx=(12, 0))
        self.f_emp = ttk.Entry(filtros, width=14); self.f_emp.pack(side="left", padx=4)

        ttk.Button(filtros, text="Filtrar", command=self._resetar_paginacao).pack(side="left", padx=6)
        ttk.Button(filtros, text="Limpar", command=self._limpar_filtros).pack(side="left")

        # Lista histórico
        cols_s = ("id","criado_em","cod_aghu","nome_item","qtde","vl_unit","vl_total","numero_empenho","observacao")
        heads_s = ("ID","Criado em","Cód AGHU","Item","Qtde","Vlr Unit","Vlr Total","Nº Empenho","Obs")
        widths_s = (60,140,100,260,70,90,100,120,260)

        self.tv_salvos = ttk.Treeview(lf_hist, columns=cols_s, show="headings", height=8)
        for c,h,w in zip(cols_s,heads_s,widths_s):
            self.tv_salvos.heading(c,text=h); self.tv_salvos.column(c,width=w,anchor="w")
        self.tv_salvos.pack(fill="both",expand=True,padx=6,pady=(6,2))

        barra_hist = tk.Frame(lf_hist, bg="white")
        barra_hist.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(barra_hist, text="Atualizar", command=self._carregar_salvos).pack(side="left")
        ttk.Button(barra_hist, text="Excluir selecionado", command=self._excluir_salvo).pack(side="left", padx=6)
        ttk.Button(barra_hist, text="Exportar histórico (filtros)", command=self._exportar_historico).pack(side="left", padx=6)

        # ---------- Paginação ----------
        pag = tk.Frame(lf_hist, bg="white")
        pag.pack(fill="x", padx=6, pady=(0, 6))

        tk.Label(pag, text="Itens/página:").pack(side="left")
        self.cb_page_size = ttk.Combobox(pag, state="readonly", width=5, values=[20, 50, 100, 200])

        try:
            cfg = utils.carregar_config()
            ultimo = int(cfg.get("paginacao_orcamento", 50))
        except:
            ultimo = 50

        self.after(10, lambda: self.cb_page_size.set(ultimo))
        self.cb_page_size.pack(side="left", padx=4)

        self.cb_page_size.bind("<<ComboboxSelected>>", self._on_page_size_changed)

        ttk.Button(pag, text="<<", command=lambda: self._ir_pagina("first")).pack(side="left", padx=2)
        ttk.Button(pag, text="<", command=lambda: self._ir_pagina("prev")).pack(side="left", padx=2)
        ttk.Button(pag, text=">", command=lambda: self._ir_pagina("next")).pack(side="left", padx=2)
        ttk.Button(pag, text=">>", command=lambda: self._ir_pagina("last")).pack(side="left", padx=2)

        self.lbl_pag = tk.Label(pag, text="Página 1/1", bg="white")
        self.lbl_pag.pack(side="left", padx=10)

        # Inicializa paginação
        self._page = 1
        self._total = 0

        # Estado geral
        self.map_fornec = {}
        self._modelos_cache = []

        # Carregamentos iniciais
        self._carregar_fornecedores()
        self._carregar_itens_rascunho()
        self._carregar_salvos()
        self._carregar_msgs()

    # ----------------- Suporte interno -----------------

    def _add_anexo(self):
        arq = filedialog.askopenfilename(
            title="Selecionar anexo",
            filetypes=[("Todos os arquivos", "*.*")]
        )
        if not arq:
            return

        self._anexos_extra.append(arq)
        messagebox.showinfo("Anexo", f"Arquivo anexado:\n{arq}")

    def _carregar_fornecedores(self):
        fs = banco.fornecedores_listar()
        self.map_fornec = {f["nome"]: f["id"] for f in fs}
        self.cb_fornec["values"] = list(self.map_fornec.keys())
        if fs and not self.cb_fornec.get():
            self.cb_fornec.current(0)

    def _fornecedor_id_atual(self):
        nome = self.cb_fornec.get()
        if not nome:
            return None
        return self.map_fornec.get(nome)

    def _reset_autosave_context(self):
        self._autosave_msg_id = None

    def _adicionar(self):
        try:
            qt = float(str(self.e_qt.get() or 0).replace(",", "."))
            vu = float(str(self.e_vu.get() or 0).replace(",", "."))
        except:
            messagebox.showwarning("Validação", "Digite números válidos.")
            return

        if not (self.e_cod.get().strip() and self.e_nome.get().strip() and qt and vu):
            messagebox.showwarning("Validação", "Preencha todos os campos obrigatórios.")
            return

        vt = qt * vu

        # Insere visualmente
        self.tv.insert(
            "", "end",
            values=(self.e_cod.get().strip(), self.e_nome.get().strip(),
                    f"{qt}", f"{vu:.2f}", self.e_emp.get().strip(),
                    self.e_obs.get().strip(), f"{vt:.2f}")
        )

        try:
            banco.itens_rascunho_inserir({
                "fornecedor_id": self._fornecedor_id_atual(),
                "cod_aghu": self.e_cod.get().strip(),
                "nome_item": self.e_nome.get().strip(),
                "qtde": qt,
                "vl_unit": vu,
                "numero_empenho": self.e_emp.get().strip(),
                "observacao": self.e_obs.get().strip()
            })
        except Exception as e:
            messagebox.showwarning("Rascunho", f"Erro ao salvar rascunho:\n{e}")

        for e in (self.e_cod, self.e_nome, self.e_qt, self.e_vu, self.e_emp, self.e_obs):
            e.delete(0, "end")

    # ---------------- Página -----------------

    def _salvar_page_size(self):
        try:
            tam = int(self.cb_page_size.get())
        except:
            tam = 50

        cfg = utils.carregar_config()
        cfg["paginacao_orcamento"] = tam
        utils.salvar_config(cfg)

    def _on_page_size_changed(self, evt=None):
        try:
            self._page_size = int(self.cb_page_size.get())
        except:
            self._page_size = 50

        self._salvar_page_size()
        self._page = 1
        self._carregar_salvos()

    def _resetar_paginacao(self):
        self._page = 1
        self._carregar_salvos()

    def _ir_pagina(self, qual):
        page_size = int(self.cb_page_size.get() or 50)
        total_pages = max(1, (self._total + page_size - 1) // page_size)

        if qual == "first":
            self._page = 1
        elif qual == "prev":
            self._page = max(1, self._page - 1)
        elif qual == "next":
            self._page = min(total_pages, self._page + 1)
        elif qual == "last":
            self._page = total_pages

        self._carregar_salvos()

    def _carregar_modelo_rapido(self):
        titulo = self.cb_modelo.get()
        if not titulo:
            return
    
        for m in self._modelos_cache:
            if m["titulo"] == titulo:
                msg = banco.mensagem_obter(m["id"])
                if msg:
                    self.txt_msg.delete("1.0", "end")
                    self.txt_msg.insert("1.0", msg.get("conteudo", ""))
    
                    self.e_titulo_msg.delete(0, "end")
                    self.e_titulo_msg.insert(0, msg.get("titulo", ""))
    
                    # não sobrescreve automaticamente o modelo
                    self._autosave_msg_id = None
                break

    # ---------------- Histórico -----------------

    def _limpar_filtros(self):
        self.f_data_ini.delete(0, "end")
        self.f_data_fim.delete(0, "end")
        self.f_busca.delete(0, "end")
        self.f_emp.delete(0, "end")
        self._resetar_paginacao()

    def _filtros_atual(self):
        di = self.f_data_ini.get().strip() or None
        df = self.f_data_fim.get().strip() or None
        termo = self.f_busca.get().strip()
        nem = self.f_emp.get().strip()
        return di, df, termo, nem

    def _carregar_salvos(self):
        forn_id = self._fornecedor_id_atual()
        for i in self.tv_salvos.get_children():
            self.tv_salvos.delete(i)

        if not forn_id:
            self._total = 0
            self._page = 1
            self.lbl_pag.config(text="Página 1/1")
            return

        di, df, termo, nem = self._filtros_atual()
        page_size = int(self.cb_page_size.get() or 50)
        offset = (self._page - 1) * page_size

        try:
            res = banco.orcamentos_filtrar_paginado(
                fornecedor_id=forn_id,
                data_ini=di,
                data_fim=df,
                termo=termo,
                numero_empenho=nem,
                limit=page_size,
                offset=offset,
            )
            rows, self._total = res["rows"], res["total"]
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar histórico:\n{e}")
            return

        for r in rows:
            qt = float(r.get("qtde", 0) or 0)
            vu = float(r.get("vl_unit", 0) or 0)
            self.tv_salvos.insert(
                "",
                "end",
                values=(
                    r.get("id", ""),
                    r.get("criado_em", ""),
                    r.get("cod_aghu", ""),
                    r.get("nome_item", ""),
                    f"{qt}",
                    f"{vu:.2f}",
                    f"{qt * vu:.2f}",
                    r.get("numero_empenho", "") or "",
                    r.get("observacao", "") or "",
                ),
            )

        total_pages = max(1, (self._total + page_size - 1) // page_size)
        self._page = min(self._page, total_pages)
        self.lbl_pag.config(text=f"Página {self._page}/{total_pages} — {self._total} registro(s)")

    # ---------------- EXPORTAR HISTÓRICO -----------------

    def _exportar_historico(self):
        fornecedor_id = self._fornecedor_id_atual()
        if not fornecedor_id:
            messagebox.showwarning("Validação", "Selecione o fornecedor.")
            return

        di, df, termo, nem = self._filtros_atual()
        try:
            rows = banco.orcamentos_filtrar(
                fornecedor_id=fornecedor_id,
                data_ini=di,
                data_fim=df,
                termo=termo,
                numero_empenho=nem,
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao filtrar histórico:\n{e}")
            return

        if not rows:
            messagebox.showinfo("Histórico", "Nenhum registro encontrado.")
            return

        arq = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="Salvar histórico de orçamentos",
        )
        if not arq:
            return

        import pandas as pd
        dados = []
        for r in rows:
            qt = float(r.get("qtde", 0) or 0)
            vu = float(r.get("vl_unit", 0) or 0)
            dados.append(
                {
                    "Criado em": r.get("criado_em", ""),
                    "Cód AGHU": r.get("cod_aghu", ""),
                    "Item": r.get("nome_item", ""),
                    "Qtde": qt,
                    "Vlr Unit": vu,
                    "Vlr Total": qt * vu,
                    "Nº Empenho": r.get("numero_empenho", "") or "",
                    "Obs": r.get("observacao", "") or "",
                }
            )

        df = pd.DataFrame(dados)
        utils.exportar_excel({"Histórico": df}, arq)
        messagebox.showinfo("Exportar", f"Arquivo salvo em:\n{arq}")

    # ---------------- Enviar Orçamento por Email -----------------

    def _enviar_email(self):
        # >>> seu bloco original corrigido fica aqui <<<
        # (omitido aqui para não duplicar — MAS JÁ FOI ENVIADO PRONTO NA MENSAGEM ANTERIOR)
        pass

    # ---------------- Carregar Rascunho -----------------

    def _carregar_itens_rascunho(self):
        for i in self.tv.get_children():
            self.tv.delete(i)

        forn_id = self._fornecedor_id_atual()

        try:
            rows = banco.itens_rascunho_listar(fornecedor_id=forn_id)
            for r in rows:
                qt = float(r.get("qtde", 0) or 0)
                vu = float(r.get("vl_unit", 0) or 0)
                vt = qt * vu
                self.tv.insert(
                    "",
                    "end",
                    values=(
                        r.get("cod_aghu", ""),
                        r.get("nome_item", ""),
                        f"{qt}",
                        f"{vu:.2f}",
                        r.get("numero_empenho", "") or "",
                        r.get("observacao", "") or "",
                        f"{vt:.2f}",
                    ),
                )
        except Exception as e:
            print("Falha ao carregar rascunho:", e)
