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
        banco.criar_tabelas()

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
                self._carregar_itens_rascunho(),   # <<< aqui
                self._carregar_salvos(),
                self._carregar_msgs(),
            ),
        )

        # ---------- Formulário de lançamento ----------
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
        tk.Label(form, text="Observação:").grid(
            column=4, row=1, sticky="w", padx=6, pady=3
        )
        self.e_obs = ttk.Entry(form, width=40)
        self.e_obs.grid(column=5, row=1, sticky="w", padx=6, pady=3)

        # ----- Seleção rápida de modelo
        tk.Label(form, text="Modelo:").grid(
            column=0, row=3, sticky="w", padx=6, pady=3
        )
        self.cb_modelo = ttk.Combobox(form, state="readonly", width=50)
        self.cb_modelo.grid(column=1, row=3, columnspan=3, sticky="w", padx=6, pady=3)
        ttk.Button(form, text="Carregar", command=self._carregar_modelo_rapido).grid(
            column=4, row=3, padx=6
        )

        # Mensagem (corpo do e-mail)
        tk.Label(form, text="Mensagem p/ e-mail:").grid(
            column=0, row=4, sticky="nw", padx=6, pady=3
        )
        self.txt_msg = tk.Text(form, width=80, height=4)
        self.txt_msg.grid(column=1, row=4, columnspan=5, sticky="w", padx=6, pady=3)

        # Autosave: timer + eventos (digitar, sair do campo, fechar janela)
        self._autosave_job = None
        self._autosave_msg_id = None  # ID do rascunho que está sendo atualizado
        self._msg_editando_id = None  # ID de qualquer mensagem que esteja no editor
        self.txt_msg.bind("<KeyRelease>", lambda e: self._agendar_autosave())
        self.txt_msg.bind("<FocusOut>", lambda e: self._autosave_now())
        try:
            self.winfo_toplevel().protocol("WM_DELETE_WINDOW", self._on_close)
        except Exception:
            pass

        # Indicador visual do autosave
        self._lbl_autosave = tk.Label(form, text="", fg="#2c7", bg="white")
        self._lbl_autosave.grid(
            column=1, row=5, columnspan=5, sticky="w", padx=6, pady=(0, 4)
        )

        # ----- Lado direito: Add + Título + Vincular + Salvar
        side = tk.Frame(form, bg="white")
        side.grid(column=6, row=0, rowspan=5, sticky="ne", padx=(10, 6), pady=3)

        ttk.Button(side, text="Add", command=self._adicionar).pack(fill="x", pady=(0, 8))

        msg_box = ttk.LabelFrame(side, text="Mensagem: Modelo / Rascunho")
        msg_box.pack(fill="x")

        tk.Label(msg_box, text="Título:").pack(anchor="w", padx=6, pady=(6, 0))
        self.e_titulo_msg = ttk.Entry(msg_box, width=28)
        self.e_titulo_msg.pack(anchor="w", padx=6, pady=(0, 6))

        self.var_msg_forn = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            msg_box,
            text="Vincular ao fornecedor atual",
            variable=self.var_msg_forn,
        ).pack(anchor="w", padx=6, pady=(0, 6))

        btns_msg = tk.Frame(msg_box, bg="white")
        btns_msg.pack(fill="x", padx=6, pady=(0, 8))
        ttk.Button(
            btns_msg, text="Salvar Modelo", command=lambda: self._salvar_mensagem("modelo")
        ).pack(side="left")
        ttk.Button(
            btns_msg,
            text="Salvar Rascunho",
            command=lambda: self._salvar_mensagem("rascunho"),
        ).pack(side="left", padx=6)

        # ---------- Rascunho (itens não salvos) ----------
        lf_rasc = ttk.LabelFrame(self, text="Itens em rascunho (não salvos)")
        lf_rasc.pack(fill="both", expand=True, padx=12, pady=(4, 2))

        cols = ("cod", "nome", "qt", "vu", "emp", "obs", "vl_total")
        heads = ("Cód AGHU", "Nome", "Qtde", "Vlr Unit", "Nº Empenho", "Obs", "Vlr Total")
        widths = (100, 260, 60, 90, 120, 260, 100)
        self.tv = ttk.Treeview(lf_rasc, columns=cols, show="headings", height=6)
        for c, h, w in zip(cols, heads, widths):
            self.tv.heading(c, text=h)
            self.tv.column(c, width=w, anchor="w")
        self.tv.pack(fill="both", expand=True, padx=6, pady=6)

        # ---------- Ações principais ----------
        rod = tk.Frame(self, bg="white")
        rod.pack(fill="x", padx=12, pady=8)
        self.btn_email = ttk.Button(rod, text="Enviar por e-mail", command=self._enviar_email)
        self.btn_email.pack(side="right", padx=6)
        self.btn_export = ttk.Button(rod, text="Exportar para Excel", command=self._exportar_excel)
        self.btn_export.pack(side="right", padx=6)

        # ---------- Histórico (com filtros) ----------
        lf_hist = ttk.LabelFrame(self, text="Orçamentos já salvos (no banco) — por fornecedor")
        lf_hist.pack(fill="both", expand=True, padx=12, pady=(2, 8))

        filtros = tk.Frame(lf_hist)
        filtros.pack(fill="x", padx=6, pady=(6, 0))

        tk.Label(filtros, text="De (YYYY-MM-DD):").pack(side="left")
        self.f_data_ini = ttk.Entry(filtros, width=12)
        self.f_data_ini.pack(side="left", padx=4)

        tk.Label(filtros, text="Até:").pack(side="left")
        self.f_data_fim = ttk.Entry(filtros, width=12)
        self.f_data_fim.pack(side="left", padx=4)

        tk.Label(filtros, text="Termo (cód/nome/obs):").pack(side="left", padx=(12, 0))
        self.f_busca = ttk.Entry(filtros, width=28)
        self.f_busca.pack(side="left", padx=4)

        tk.Label(filtros, text="Empenho:").pack(side="left", padx=(12, 0))
        self.f_emp = ttk.Entry(filtros, width=14)
        self.f_emp.pack(side="left", padx=4)

        ttk.Button(filtros, text="Filtrar", command=self._resetar_paginacao).pack(side="left", padx=6)
        ttk.Button(filtros, text="Limpar", command=self._limpar_filtros).pack(side="left")

        cols_s = (
            "id",
            "criado_em",
            "cod_aghu",
            "nome_item",
            "qtde",
            "vl_unit",
            "vl_total",
            "numero_empenho",
            "observacao",
        )
        heads_s = (
            "ID",
            "Criado em",
            "Cód AGHU",
            "Item",
            "Qtde",
            "Vlr Unit",
            "Vlr Total",
            "Nº Empenho",
            "Obs",
        )
        widths_s = (60, 140, 100, 260, 70, 90, 100, 120, 260)
        self.tv_salvos = ttk.Treeview(lf_hist, columns=cols_s, show="headings", height=8)
        for c, h, w in zip(cols_s, heads_s, widths_s):
            self.tv_salvos.heading(c, text=h)
            self.tv_salvos.column(c, width=w, anchor="w")
        self.tv_salvos.pack(fill="both", expand=True, padx=6, pady=(6, 2))

        barra_hist = tk.Frame(lf_hist, bg="white")
        barra_hist.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(barra_hist, text="Atualizar", command=self._carregar_salvos).pack(side="left")
        ttk.Button(barra_hist, text="Excluir selecionado", command=self._excluir_salvo).pack(
            side="left", padx=6
        )
        ttk.Button(
            barra_hist, text="Exportar histórico (filtros)", command=self._exportar_historico
        ).pack(side="left", padx=6)

        # paginação
        pag = tk.Frame(lf_hist, bg="white")
        pag.pack(fill="x", padx=6, pady=(0, 6))
        tk.Label(pag, text="Itens/página:").pack(side="left")
        self.cb_page_size = ttk.Combobox(pag, state="readonly", width=5, values=[20, 50, 100, 200])
        self.cb_page_size.set(50)
        self.cb_page_size.pack(side="left", padx=4)
        self.cb_page_size.bind("<<ComboboxSelected>>", lambda e: self._resetar_paginacao())

        ttk.Button(pag, text="<<", command=lambda: self._ir_pagina("first")).pack(side="left", padx=2)
        ttk.Button(pag, text="<", command=lambda: self._ir_pagina("prev")).pack(side="left", padx=2)
        ttk.Button(pag, text=">", command=lambda: self._ir_pagina("next")).pack(side="left", padx=2)
        ttk.Button(pag, text=">>", command=lambda: self._ir_pagina("last")).pack(side="left", padx=2)

        self.lbl_pag = tk.Label(pag, text="Página 1/1", bg="white")
        self.lbl_pag.pack(side="left", padx=10)

        # estado da paginação
        self._page = 1
        self._total = 0

        # ---------- Mensagens (Modelos e Rascunhos) ----------
        lf_msg = ttk.LabelFrame(self, text="Mensagens (Modelos e Rascunhos)")
        lf_msg.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Busca de mensagens (para as listas)
        busca_bar = tk.Frame(lf_msg)
        busca_bar.pack(fill="x", padx=6, pady=(6, 6))
        tk.Label(busca_bar, text="Buscar (título/conteúdo):").pack(side="left")
        self.e_msg_busca = ttk.Entry(busca_bar, width=40)
        self.e_msg_busca.pack(side="left", padx=6)
        ttk.Button(busca_bar, text="Filtrar listas", command=self._carregar_msgs).pack(side="left")

        # Botões gerais de edição nas listas
        msg_edit = tk.Frame(lf_msg)
        msg_edit.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(msg_edit, text="Editar selecionada", command=self._editar_msg).pack(side="left")
        ttk.Button(msg_edit, text="Salvar alterações", command=self._salvar_alteracoes_msg).pack(
            side="left", padx=6
        )

        # Notebook com as listas
        nb = ttk.Notebook(lf_msg)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        # Aba Modelos
        aba_modelos = tk.Frame(nb)
        nb.add(aba_modelos, text="Modelos")
        cols_m = ("id", "titulo", "fornecedor_id", "criado_em")
        self.tv_modelos = ttk.Treeview(aba_modelos, columns=cols_m, show="headings", height=6)
        for c, h, w in zip(cols_m, ("ID", "Título", "Fornecedor", "Criado em"), (60, 280, 100, 140)):
            self.tv_modelos.heading(c, text=h)
            self.tv_modelos.column(c, width=w, anchor="w")
        self.tv_modelos.pack(fill="both", expand=True, padx=4, pady=4)
        self.tv_modelos.bind("<Double-1>", lambda e: self._usar_msg("modelo"))

        bar_m = tk.Frame(aba_modelos)
        bar_m.pack(fill="x", padx=4, pady=(0, 6))
        ttk.Button(bar_m, text="Usar na mensagem", command=lambda: self._usar_msg("modelo")).pack(
            side="left"
        )
        ttk.Button(bar_m, text="Excluir", command=lambda: self._excluir_msg("modelo")).pack(
            side="left", padx=6
        )
        ttk.Button(bar_m, text="Atualizar", command=self._carregar_msgs).pack(side="left", padx=6)

        # Aba Rascunhos
        aba_rasc = tk.Frame(nb)
        nb.add(aba_rasc, text="Rascunhos")
        self.tv_rasc = ttk.Treeview(aba_rasc, columns=cols_m, show="headings", height=6)
        for c, h, w in zip(cols_m, ("ID", "Título", "Fornecedor", "Criado em"), (60, 280, 100, 140)):
            self.tv_rasc.heading(c, text=h)
            self.tv_rasc.column(c, width=w, anchor="w")
        self.tv_rasc.pack(fill="both", expand=True, padx=4, pady=4)
        self.tv_rasc.bind("<Double-1>", lambda e: self._usar_msg("rascunho"))

        bar_r = tk.Frame(aba_rasc)
        bar_r.pack(fill="x", padx=4, pady=(0, 6))
        ttk.Button(bar_r, text="Usar na mensagem", command=lambda: self._usar_msg("rascunho")).pack(
            side="left"
        )
        ttk.Button(bar_r, text="Excluir", command=lambda: self._excluir_msg("rascunho")).pack(
            side="left", padx=6
        )
        ttk.Button(bar_r, text="Atualizar", command=self._carregar_msgs).pack(side="left", padx=6)

        # Estado
        self.map_fornec = {}
        self._modelos_cache = []

        # Inicializações
        self._carregar_fornecedores()
        self._carregar_itens_rascunho()   # <<< NOVO: carrega itens persistidos
        self._carregar_salvos()
        self._carregar_msgs()

    # ----------------- Utilidades -----------------
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
        """Quando troca o fornecedor, este rascunho deixa de ser editado automaticamente."""
        self._autosave_msg_id = None

    def _adicionar(self):
        try:
            qt = float(str(self.e_qt.get() or 0).replace(",", "."))
            vu = float(str(self.e_vu.get() or 0).replace(",", "."))
        except ValueError:
            messagebox.showwarning("Validação", "Digite números válidos em Qtde/Valor.")
            return
    
        if not (self.e_cod.get().strip() and self.e_nome.get().strip() and qt and vu):
            messagebox.showwarning("Validação", "Preencha código, nome, qtde e valor unitário.")
            return
    
        # 1) Insere na Treeview (visual)
        vt = qt * vu
        self.tv.insert("", "end", values=(
            self.e_cod.get().strip(),
            self.e_nome.get().strip(),
            f"{qt}",
            f"{vu:.2f}",
            self.e_emp.get().strip(),
            self.e_obs.get().strip(),
            f"{vt:.2f}"
        ))
    
        # 2) Persiste no banco como item em rascunho
        try:
            forn_id = self._fornecedor_id_atual()  # None = Global
            banco.itens_rascunho_inserir({
                "fornecedor_id": forn_id,
                "cod_aghu": self.e_cod.get().strip(),
                "nome_item": self.e_nome.get().strip(),
                "qtde": qt,
                "vl_unit": vu,
                "numero_empenho": self.e_emp.get().strip(),
                "observacao": self.e_obs.get().strip()
            })
        except Exception as e:
            messagebox.showwarning("Rascunho de itens", f"Não foi possível salvar o item em rascunho:\n{e}")
    
        # 3) Limpa campos
        for e in (self.e_cod, self.e_nome, self.e_qt, self.e_vu, self.e_emp, self.e_obs):
            e.delete(0, "end")

    # ---------- Persistência de itens ----------
    def _salvar_orcamento_linhas(self, values_rows) -> int:
        forn_id = self._fornecedor_id_atual()
        if not forn_id:
            raise RuntimeError("Selecione o fornecedor.")

        mensagem = self.txt_msg.get("1.0", "end").strip()
        salvos = 0
        for v in values_rows:
            try:
                banco.orcamento_inserir(
                    {
                        "fornecedor_id": forn_id,
                        "cod_aghu": v[0],
                        "nome_item": v[1],
                        "qtde": float(str(v[2]).replace(",", ".")),
                        "vl_unit": float(str(v[3]).replace(",", ".")),
                        "numero_empenho": v[4],
                        "observacao": v[5],
                        "mensagem_email": mensagem,
                    }
                )
                salvos += 1
            except Exception:
                continue
        return salvos

    # ---------- Histórico (filtros + paginação) ----------
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

    def _resetar_paginacao(self):
        self._page = 1
        self._carregar_salvos()

    def _ir_pagina(self, qual: str):
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

    def _carregar_salvos(self):
        forn_id = self._fornecedor_id_atual()
        for i in self.tv_salvos.get_children():
            self.tv_salvos.delete(i)
        if not forn_id:
            self._total, self._page = 0, 1
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
            for r in rows:
                qt = float(r.get("qtde", 0) or 0)
                vu = float(r.get("vl_unit", 0) or 0)
                self.tv_salvos.insert(
                    "", "end",
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
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar orçamentos salvos:\n{e}")

    def _exportar_historico(self):
        forn_id = self._fornecedor_id_atual()
        if not forn_id:
            messagebox.showwarning("Validação", "Selecione o fornecedor.")
            return
        di, df, termo, nem = self._filtros_atual()
        try:
            rows = banco.orcamentos_filtrar(
                fornecedor_id=forn_id, data_ini=di, data_fim=df, termo=termo, numero_empenho=nem
            )
            if not rows:
                messagebox.showinfo("Exportar histórico", "Nenhum registro para exportar com os filtros atuais.")
                return
            arq = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx")],
                title="Salvar histórico de orçamentos",
            )
            if not arq:
                return
            import pandas as pd  # import local para evitar custo no startup
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
            messagebox.showinfo("Exportar histórico", f"Planilha salva em:\n{arq}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar histórico:\n{e}")

    def _excluir_salvo(self):
        sel = self.tv_salvos.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma linha salva para excluir.")
            return
        vals = self.tv_salvos.item(sel[0], "values")
        try:
            id_ = int(vals[0])
        except Exception:
            return
        if not messagebox.askyesno("Confirmar", "Excluir o orçamento selecionado?"):
            return
        try:
            banco.orcamento_excluir(id_)
            self._carregar_salvos()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir: {e}")

    # ---------- Mensagens: modelos & rascunhos ----------
    def _carregar_msgs(self):
        """Carrega Modelos e Rascunhos combinando globais (fornecedor_id NULL) e do fornecedor atual."""
        forn_id = self._fornecedor_id_atual()
        busca = self.e_msg_busca.get().strip() if hasattr(self, "e_msg_busca") else ""
    
        # Limpa UI
        if hasattr(self, "tv_modelos"):
            for i in self.tv_modelos.get_children():
                self.tv_modelos.delete(i)
        if hasattr(self, "tv_rasc"):
            for i in self.tv_rasc.get_children():
                self.tv_rasc.delete(i)
        if hasattr(self, "cb_modelo"):
            self.cb_modelo.set("")
            self.cb_modelo["values"] = []
    
        def _safe_listar(tipo: str, fornecedor_id):
            """Busca do fornecedor; se houver fornecedor, também junta globais."""
            lst = []
            try:
                lst = banco.mensagens_listar(tipo=tipo, fornecedor_id=fornecedor_id, busca=busca) or []
            except Exception as e:
                print(f"Falha ao listar {tipo} (forn={fornecedor_id}):", e)
    
            # Se temos fornecedor, tenta também globais e junta
            if fornecedor_id is not None:
                try:
                    glb = banco.mensagens_listar(tipo=tipo, fornecedor_id=None, busca=busca) or []
                except Exception as e:
                    print(f"Falha ao listar {tipo} globais:", e)
                    glb = []
    
                # Merge evitando duplicados (por id)
                seen = set(m.get("id") for m in lst)
                for g in glb:
                    if g.get("id") not in seen:
                        lst.append(g)
    
            # Ordena (se seus campos forem string ISO-like, isso já funciona bem)
            # Se seu banco tiver 'atualizado_em', pode ordenar por ele em vez de criado_em
            try:
                lst.sort(key=lambda m: (m.get("criado_em") or "", m.get("id") or 0), reverse=True)
            except Exception:
                pass
    
            return lst
    
        # ---- Modelos (combo + lista)
        modelos = _safe_listar("modelo", forn_id)
        self._modelos_cache = modelos[:]  # guarda para o "Carregar" rápido
        if hasattr(self, "cb_modelo"):
            self.cb_modelo["values"] = [m.get("titulo", "") for m in modelos]
    
        if hasattr(self, "tv_modelos"):
            for m in modelos:
                escopo = "Global" if m.get("fornecedor_id") in (None, "") else f"Forn {m['fornecedor_id']}"
                self.tv_modelos.insert(
                    "", "end",
                    values=(m.get("id", ""), m.get("titulo", ""), escopo, m.get("criado_em", ""))
                )
    
        # ---- Rascunhos (lista)
        rascs = _safe_listar("rascunho", forn_id)
        if hasattr(self, "tv_rasc"):
            for m in rascs:
                escopo = "Global" if m.get("fornecedor_id") in (None, "") else f"Forn {m['fornecedor_id']}"
                self.tv_rasc.insert(
                    "", "end",
                    values=(m.get("id", ""), m.get("titulo", ""), escopo, m.get("criado_em", ""))
                )

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
                    # reseta autosave (não sobrescrever modelo)
                    self._autosave_msg_id = None
                break

    def _salvar_mensagem(self, tipo: str):
        titulo = (self.e_titulo_msg.get() or "").strip()
        if not titulo:
            messagebox.showwarning("Validação", "Informe um título para a mensagem.")
            return
        conteudo = self.txt_msg.get("1.0", "end").strip()
        if not conteudo:
            messagebox.showwarning("Validação", "Escreva o conteúdo da mensagem.")
            return

        forn_id = self._fornecedor_id_atual() if self.var_msg_forn.get() else None
        if self.var_msg_forn.get() and not forn_id:
            messagebox.showwarning("Validação", "Selecione um fornecedor para vincular a mensagem.")
            return

        try:
            mid = banco.mensagem_inserir(
                {
                    "fornecedor_id": forn_id,
                    "titulo": titulo,
                    "conteudo": conteudo,
                    "tipo": tipo,
                }
            )
            self._msg_editando_id = mid
            self._autosave_msg_id = mid if tipo == "rascunho" else None
            self._carregar_msgs()
            messagebox.showinfo(
                "OK",
                f"Mensagem salva como {tipo.upper()}.\nEla aparece na lista da aba correspondente.",
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar mensagem: {e}")

    def _usar_msg(self, tipo: str):
        tv = self.tv_modelos if tipo == "modelo" else self.tv_rasc
        sel = tv.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma mensagem.")
            return
        vals = tv.item(sel[0], "values")
        try:
            mid = int(vals[0])
        except Exception:
            return
        msg = banco.mensagem_obter(mid)
        if not msg:
            messagebox.showwarning("Aviso", "Mensagem não encontrada.")
            return

        self._msg_editando_id = mid
        # se for rascunho, autosave atualiza este; se for modelo, autosave criará novo rascunho
        self._autosave_msg_id = mid if msg.get("tipo") == "rascunho" else None

        self.e_titulo_msg.delete(0, "end")
        self.e_titulo_msg.insert(0, msg.get("titulo", ""))
        self.txt_msg.delete("1.0", "end")
        self.txt_msg.insert("1.0", msg.get("conteudo", ""))

    def _editar_msg(self):
        sel = self.tv_modelos.selection() or self.tv_rasc.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma mensagem nas abas.")
            return
        tv = self.tv_modelos if self.tv_modelos.selection() else self.tv_rasc
        vals = tv.item(sel[0], "values")
        try:
            mid = int(vals[0])
        except Exception:
            return
        msg = banco.mensagem_obter(mid)
        if not msg:
            messagebox.showwarning("Aviso", "Mensagem não encontrada.")
            return

        self._msg_editando_id = mid
        self._autosave_msg_id = mid if msg.get("tipo") == "rascunho" else None

        self.e_titulo_msg.delete(0, "end")
        self.e_titulo_msg.insert(0, msg.get("titulo", ""))
        self.txt_msg.delete("1.0", "end")
        self.txt_msg.insert("1.0", msg.get("conteudo", ""))

    def _salvar_alteracoes_msg(self):
        if not self._msg_editando_id:
            messagebox.showwarning("Edição", "Nenhuma mensagem selecionada para editar.")
            return
        titulo = (self.e_titulo_msg.get() or "").strip()
        conteudo = self.txt_msg.get("1.0", "end").strip()
        if not titulo or not conteudo:
            messagebox.showwarning("Validação", "Título e conteúdo são obrigatórios.")
            return
        try:
            banco.mensagem_atualizar(self._msg_editando_id, titulo, conteudo)
            self._carregar_msgs()
            messagebox.showinfo("OK", "Mensagem atualizada.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao atualizar: {e}")

    def _excluir_msg(self, tipo: str):
        tv = self.tv_modelos if tipo == "modelo" else self.tv_rasc
        sel = tv.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma mensagem.")
            return
        vals = tv.item(sel[0], "values")
        try:
            mid = int(vals[0])
        except Exception:
            return
        if not messagebox.askyesno("Confirmar", "Excluir a mensagem selecionada?"):
            return
        try:
            banco.mensagem_excluir(mid)
            self._msg_editando_id = None
            if self._autosave_msg_id == mid:
                self._autosave_msg_id = None
            self._carregar_msgs()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir: {e}")

    # ---------- Autosave de rascunho ----------
    def _agendar_autosave(self):
        if self._autosave_job:
            self.after_cancel(self._autosave_job)
        # 2s depois que parar de digitar
        self._autosave_job = self.after(2000, self._autosave_rascunho)

    def _autosave_now(self):
        """Força salvar imediatamente (sair do campo/fechar)."""
        try:
            if self._autosave_job:
                self.after_cancel(self._autosave_job)
                self._autosave_job = None
        except Exception:
            pass
        self._autosave_rascunho()

    def _on_close(self):
        """Intercepta fechar janela para gravar rascunho antes de sair."""
        try:
            self._autosave_now()
        except Exception:
            pass
        self.winfo_toplevel().destroy()

    def _autosave_rascunho(self):
        conteudo = self.txt_msg.get("1.0", "end").strip()
        if not conteudo:
            return

        # Escopo do rascunho no momento da criação: global (None) ou vinculado
        forn_id = self._fornecedor_id_atual() if self.var_msg_forn.get() else None
        titulo = (self.e_titulo_msg.get() or f"Rascunho automático - {self.cb_fornec.get() or 'Global'}").strip()

        try:
            if self._autosave_msg_id:
                banco.mensagem_atualizar(self._autosave_msg_id, titulo, conteudo)
            else:
                # cria UM rascunho dedicado e guarda o ID para sempre atualizar este
                self._autosave_msg_id = banco.mensagem_inserir(
                    {
                        "fornecedor_id": forn_id,
                        "titulo": titulo,
                        "conteudo": conteudo,
                        "tipo": "rascunho",
                    }
                )

            # feedback + recarregar listas
            try:
                self._lbl_autosave.config(text=f"Rascunho salvo às {datetime.now():%H:%M:%S}")
            except Exception:
                pass
            self._carregar_msgs()
        except Exception as e:
            print("Erro autosave:", e, file=sys.stderr)

    # ---------- Exportar / Enviar (salva antes) ----------
    def _exportar_excel(self):
        values_rows = [self.tv.item(iid, "values") for iid in self.tv.get_children()]
        if not values_rows:
            messagebox.showinfo("Exportação", "Não há itens no rascunho para exportar.")
            return
    
        # 1) SALVA no banco de orçamentos (histórico)
        try:
            self._salvar_orcamento_linhas(values_rows)
        except Exception as e:
            messagebox.showwarning(
                "Salvar orçamento",
                f"Não foi possível salvar no banco antes de exportar:\n{e}"
            )
            # Continua a exportação mesmo assim? Se não quiser, dê 'return' aqui.
            # return
    
        # 2) Monta a estrutura para o Excel
        linhas = []
        for v in values_rows:
            linhas.append({
                "Cód AGHU": v[0],
                "Nome": v[1],
                "Qtde": float(str(v[2]).replace(",", ".")),
                "Valor Unitário": float(str(v[3]).replace(",", ".")),
                "Nº Empenho": v[4],
                "Observação": v[5],
                "Valor Total": float(str(v[6]).replace(",", "."))
            })
    
        arq = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="Salvar orçamento"
        )
        if not arq:
            return
    
        # 3) Exporta e, só em caso de sucesso, decide o que fazer com os rascunhos
        try:
            df = utils.tabela_para_dataframe(
                linhas,
                ["Cód AGHU", "Nome", "Qtde", "Valor Unitário", "Valor Total", "Nº Empenho", "Observação"]
            )
            utils.exportar_excel({"Orcamento": df}, arq)
            messagebox.showinfo("Exportação", f"Planilha salva em:\n{arq}")
    
            # Pergunta se deseja manter os itens em rascunho
            manter = messagebox.askyesno(
                "Itens em rascunho",
                "Deseja manter os itens em rascunho para continuar depois?\n\n"
                "Sim = mantém os itens.\nNão = limpa os itens desta grade e do rascunho."
            )
    
            if not manter:
                # 3.1) Limpa o rascunho no banco (escopo do fornecedor atual) ANTES de limpar a UI
                try:
                    fornecedor_id = self._fornecedor_id_atual()
                    banco.itens_rascunho_limpar_por_fornecedor(fornecedor_id)
                except Exception as e:
                    print("Falha ao limpar itens rascunho após exportar:", e)
    
                # 3.2) Limpa grade e recarrega histórico
                for iid in self.tv.get_children():
                    self.tv.delete(iid)
    
            # Atualiza histórico e (se desejar) recarrega rascunhos da fonte
            self._carregar_salvos()
            if not manter:
                # Se removeu do banco, garante UI sincronizada
                self._carregar_itens_rascunho()
    
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar para Excel: {e}")
            # Em erro, NÃO mexe nos rascunhos (nem na UI nem no banco).

    def _enviar_email(self):
        forn_id = self._fornecedor_id_atual()
        if not forn_id:
            messagebox.showwarning("Validação", "Selecione o fornecedor.")
            return
    
        # Busca fornecedor
        fornecedor = None
        for f in banco.fornecedores_listar():
            if f["id"] == forn_id:
                fornecedor = f
                break
        if not fornecedor:
            messagebox.showwarning("Validação", "Fornecedor não encontrado no cadastro.")
            return
    
        destinatario = (fornecedor.get("email") or "").strip()
        if not destinatario:
            messagebox.showwarning("Validação", "O fornecedor selecionado não possui e-mail cadastrado.")
            return
    
        # Coleta itens da grade
        values_rows = [self.tv.item(iid, "values") for iid in self.tv.get_children()]
        if not values_rows:
            messagebox.showinfo("E-mail", "Não há itens no rascunho para enviar.")
            return
    
        # 1) Salva no histórico antes de enviar (não interrompe o fluxo se falhar)
        try:
            self._salvar_orcamento_linhas(values_rows)
        except Exception as e:
            messagebox.showwarning(
                "Salvar orçamento",
                f"Não foi possível salvar no banco antes de enviar:\n{e}"
            )
    
        # 2) Monta HTML + anexo
        linhas = []
        total_geral = 0.0
        for v in values_rows:
            l = {
                "cod": v[0],
                "nome": v[1],
                "qt": float(str(v[2]).replace(",", ".")),
                "vu": float(str(v[3]).replace(",", ".")),
                "emp": v[4],
                "obs": v[5],
                "vt": float(str(v[6]).replace(",", "."))
            }
            linhas.append(l)
            total_geral += l["vt"]
    
        msg_user = self.txt_msg.get("1.0", "end").strip()
    
        # <<< HTML CORRIGIDO (sem entidades) >>>
        html_rows = ""
        for l in linhas:
            html_rows += f"""
                <tr>
                  <td>{l['cod']}</td>
                  <td>{l['nome']}</td>
                  <td style="text-align:right">{l['qt']}</td>
                  <td style="text-align:right">{l['vu']:.2f}</td>
                  <td style="text-align:right">{l['vt']:.2f}</td>
                  <td>{l['emp']}</td>
                  <td>{l['obs']}</td>
                </tr>
            """
    
        corpo_html = f"""
        <html>
          <body>
            <p>Prezados,</p>
            <p>{msg_user or 'Segue orçamento conforme itens abaixo.'}</p>
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-family:Segoe UI,Arial,sans-serif;font-size:12px;">
              <thead style="background:#eee;">
                <tr>
                  <th>Cód AGHU</th>
                  <th>Nome</th>
                  <th>Qtde</th>
                  <th>Valor Unitário</th>
                  <th>Valor Total</th>
                  <th>Nº Empenho</th>
                  <th>Observação</th>
                </tr>
              </thead>
              <tbody>
                {html_rows}
              </tbody>
              <tfoot>
                <tr>
                  <td colspan="4" style="text-align:right"><b>Total geral</b></td>
                  <td style="text-align:right"><b>{total_geral:.2f}</b></td>
                  <td colspan="2"></td>
                </tr>
              </tfoot>
            </table>
            <p>Atenciosamente,</p>
          </body>
        </html>
        """
    
        # Anexo Excel
        anexos = []
        try:
            tmp = tempfile.NamedTemporaryFile(prefix="orcamento_", suffix=".xlsx", delete=False)
            tmp.close()
            df = utils.tabela_para_dataframe(
                [
                    {
                        "Cód AGHU": l["cod"],
                        "Nome": l["nome"],
                        "Qtde": l["qt"],
                        "Valor Unitário": l["vu"],
                        "Valor Total": l["vt"],
                        "Nº Empenho": l["emp"],
                        "Observação": l["obs"]
                    } for l in linhas
                ],
                ["Cód AGHU", "Nome", "Qtde", "Valor Unitário", "Valor Total", "Nº Empenho", "Observação"]
            )
            utils.exportar_excel({"Orcamento": df}, tmp.name)
            anexos.append(tmp.name)
        except Exception as e:
            print("Falha ao gerar anexo Excel:", e)
    
        # 3) Envio com CC (email_alerta)
        try:
            cfg = utils.carregar_config()
            destinatarios = [destinatario]
            if cfg.get("email_alerta"):
                destinatarios.append(cfg["email_alerta"])
    
            fornecedor_nome = fornecedor.get("nome") or self.cb_fornec.get() or "Fornecedor"
            assunto = f"Orçamento - {fornecedor_nome} - {datetime.now():%d/%m/%Y}"
    
            utils.enviar_email(
                destinatarios=destinatarios,
                assunto=assunto,
                corpo_html=corpo_html,
                anexos=anexos
            )
            messagebox.showinfo(
                "E-mail",
                f"E-mail enviado com sucesso para: {', '.join(destinatarios)}"
            )
    
            # Pergunta se deseja manter os itens em rascunho
            manter = messagebox.askyesno(
                "Itens em rascunho",
                "Deseja manter os itens em rascunho para continuar depois?\n\n"
                "Sim = mantém os itens.\nNão = limpa os itens desta grade e do rascunho."
            )
    
            if not manter:
                # Limpa rascunho no banco (escopo fornecedor atual) ANTES de limpar UI
                try:
                    banco.itens_rascunho_limpar_por_fornecedor(self._fornecedor_id_atual())
                except Exception as e:
                    print("Falha ao limpar itens rascunho após enviar:", e)
    
                # Limpa grade
                for i in self.tv.get_children():
                    self.tv.delete(i)
    
            # Sincroniza listas pós-envio
            self._carregar_salvos()
            if not manter:
                self._carregar_itens_rascunho()
    
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao enviar e-mail: {e}")

    def _carregar_itens_rascunho(self):
        """Recarrega a grade 'Itens em rascunho' a partir da tabela persistida."""
        # Limpa a treeview
        for i in self.tv.get_children():
            self.tv.delete(i)
    
        # Escopo: se quiser vincular itens por fornecedor, use o fornecedor atual;
        # se quiser um rascunho global (sem fornecedor), defina fornecedor_id=None
        forn_id = self._fornecedor_id_atual()  # pode ser None, que indica Global
    
        try:
            rows = banco.itens_rascunho_listar(fornecedor_id=forn_id)
            for r in rows:
                qt = float(r.get("qtde", 0) or 0)
                vu = float(r.get("vl_unit", 0) or 0)
                vt = qt * vu
                self.tv.insert("", "end", values=(
                    r.get("cod_aghu", ""),
                    r.get("nome_item", ""),
                    f"{qt}",
                    f"{vu:.2f}",
                    r.get("numero_empenho", "") or "",
                    r.get("observacao", "") or "",
                    f"{vt:.2f}"
                ))
        except Exception as e:
            print("Falha ao carregar itens em rascunho:", e)

