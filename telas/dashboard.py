# telas/dashboard.py
import os
import math
import tempfile
import traceback
import tkinter as tk
from tkinter import ttk, messagebox

import banco


class Dashboard(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")
        banco.criar_tabelas()

        # ------- Topo: seleção de fornecedor + ações -------
        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=16, pady=(12, 6))

        tk.Label(topo, text="Fornecedor:", bg="white").pack(side="left")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.pack(side="left", padx=8)
        self.cb_fornec.bind("<<ComboboxSelected>>", lambda e: self.atualizar_listas())

        ttk.Button(topo, text="Atualizar", command=self.atualizar_listas).pack(side="left", padx=6)

        # --- NOVO: Autoatualizar ---
        self._auto = tk.BooleanVar(value=False)
        ttk.Checkbutton(topo, text="Autoatualizar (10s)", variable=self._auto,
                        command=self._tick_auto).pack(side="left", padx=(12, 0))

        # --- NOVO: Botão de Análises/Gráficos ---
        ttk.Button(topo, text="Análises / Gráficos", command=self._abrir_analises).pack(side="right")

        # ------- Split principal -------
        split = tk.Frame(self, bg="white")
        split.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # ---- Saldos ATA (quantidade) ----
        lf_ata = ttk.LabelFrame(split, text="Saldo de ATA (quantidade)")
        lf_ata.pack(side="left", fill="both", expand=True, padx=(0, 8))

        cols_ata = ("pregao", "cod_aghu", "nome_item", "qtde_total", "qtde_usada", "qtde_saldo")
        self.tv_ata = ttk.Treeview(lf_ata, columns=cols_ata, show="headings", height=14)
        cab = {
            "pregao": "ATA",
            "cod_aghu": "Cód. AGHU",
            "nome_item": "Item",
            "qtde_total": "Qtde total",
            "qtde_usada": "Qtde usada",
            "qtde_saldo": "Qtde saldo",
        }
        widths = {"pregao": 120, "cod_aghu": 100, "nome_item": 240, "qtde_total": 100, "qtde_usada": 100, "qtde_saldo": 100}
        for c in cols_ata:
            self.tv_ata.heading(c, text=cab.get(c, c))
            anchor = "w" if c in ("pregao", "cod_aghu", "nome_item") else "e"
            self.tv_ata.column(c, width=widths.get(c, 120), anchor=anchor, stretch=(c == "nome_item"))
        self.tv_ata.pack(fill="both", expand=True)

        # --- NOVO: duplo clique abre análise da ATA selecionada ---
        self.tv_ata.bind("<Double-1>", self._abrir_analise_ata_por_duplo_clique)

        # ---- Saldos Empenho (valor) ----
        lf_emp = ttk.LabelFrame(split, text="Saldo de Empenhos (valor)")
        lf_emp.pack(side="left", fill="both", expand=True, padx=(8, 0))

        # --- NOVO: inclui coluna oculta 'empenho_id' para identificar com precisão ---
        cols_emp = ("empenho_id", "cod_aghu", "nome_item", "vl_total", "valor_consumido", "valor_saldo")
        self.tv_emp = ttk.Treeview(lf_emp, columns=cols_emp, show="headings", height=14)
        cab_emp = {
            "empenho_id": "ID",
            "cod_aghu": "Cód. AGHU",
            "nome_item": "Item",
            "vl_total": "Valor total",
            "valor_consumido": "Consumido",
            "valor_saldo": "Saldo",
        }
        widths_emp = {"empenho_id": 1, "cod_aghu": 100, "nome_item": 240, "vl_total": 110, "valor_consumido": 110, "valor_saldo": 110}
        for c in cols_emp:
            self.tv_emp.heading(c, text=cab_emp.get(c, c))
            anchor = "w" if c in ("cod_aghu", "nome_item") else "e"
            self.tv_emp.column(c, width=widths_emp.get(c, 100), anchor=anchor, stretch=(c == "nome_item"))
        # oculta a coluna id visualmente
        self.tv_emp.column("empenho_id", width=1, stretch=False, anchor="center")
        self.tv_emp.pack(fill="both", expand=True)

        # --- NOVO: duplo clique abre análise do Empenho selecionado ---
        self.tv_emp.bind("<Double-1>", self._abrir_analise_empenho_por_duplo_clique)

        # Dados iniciais
        self._carregar_fornecedores()

    # ----------------- Autoatualizar -----------------
    def _tick_auto(self):
        if self._auto.get():
            self.after(1000, self._loop_auto)  # inicia loop

    def _loop_auto(self):
        if not self._auto.get():
            return
        try:
            self.atualizar_listas()
        except Exception:
            self._log_erro("Autoatualizar falhou", traceback.format_exc())
        finally:
            # agenda próxima rodada
            self.after(10_000, self._loop_auto)

    # ----------------- Carregamento base -----------------
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
                r.get("pregao", ""),
                r.get("cod_aghu", ""),
                r.get("nome_item", ""),
                r.get("qtde_total", 0),
                r.get("qtde_usada", 0),
                r.get("qtde_saldo", 0),
            ))

        # Empenho
        for i in self.tv_emp.get_children():
            self.tv_emp.delete(i)
        for r in banco.saldo_empenho_por_fornecedor(forn_id):
            # a view retorna 'empenho_id'? Sim, conforme banco.py (e.id AS empenho_id)
            emp_id = r.get("empenho_id") if "empenho_id" in r else r.get("id")  # fallback
            self.tv_emp.insert("", "end", values=(
                emp_id or "",
                r.get("cod_aghu", ""),
                r.get("nome_item", ""),
                f'{float(r.get("vl_total", 0.0)):.2f}',
                f'{float(r.get("valor_consumido", 0.0)):.2f}',
                f'{float(r.get("valor_saldo", 0.0)):.2f}',
            ))

    # ----------------- Aberturas rápidas por duplo clique -----------------
    def _abrir_analise_ata_por_duplo_clique(self, _evt):
        sel = self.tv_ata.selection()
        if not sel:
            return
        vals = self.tv_ata.item(sel[0], "values")
        pregao = vals[0]  # coluna 'pregao' (número da ata)
        nome = self.cb_fornec.get()
        forn_id = self.map_forn.get(nome)
        if not pregao or not forn_id:
            return
        AnalisesWindow(self, fornecedor_id=forn_id, pregao=pregao)

    def _abrir_analise_empenho_por_duplo_clique(self, _evt):
        sel = self.tv_emp.selection()
        if not sel:
            return
        vals = self.tv_emp.item(sel[0], "values")
        emp_id = vals[0]  # coluna oculta 'empenho_id'
        if not emp_id:
            return
        try:
            emp_id = int(emp_id)
        except Exception:
            return
        AnalisesWindow(self, empenho_id=emp_id)

    # ----------------- Botão "Análises / Gráficos" -----------------
    def _abrir_analises(self):
        nome = self.cb_fornec.get()
        forn_id = self.map_forn.get(nome)
        if not forn_id:
            messagebox.showwarning("Atenção", "Selecione um fornecedor.")
            return

        # Tenta usar seleção atual (ATA ou Empenho)
        sel_ata = self.tv_ata.selection()
        sel_emp = self.tv_emp.selection()
        if sel_ata:
            pregao = self.tv_ata.item(sel_ata[0], "values")[0]
            AnalisesWindow(self, fornecedor_id=forn_id, pregao=pregao)
        elif sel_emp:
            emp_id_txt = self.tv_emp.item(sel_emp[0], "values")[0]
            try:
                emp_id = int(emp_id_txt)
            except Exception:
                emp_id = None
            if emp_id:
                AnalisesWindow(self, empenho_id=emp_id)
            else:
                messagebox.showinfo("Análises", "Selecione um empenho válido.")
        else:
            # Abre janela “escolha o que analisar”
            AnalisesWindow(self, fornecedor_id=forn_id)

    # ----------------- Log -----------------
    def _log_erro(self, msg: str, trace: str):
        try:
            caminho = os.path.join(tempfile.gettempdir(), "control_notas_erro.log")
            with open(caminho, "a", encoding="utf-8") as f:
                f.write("\n--- DASHBOARD ---\n" + msg + "\n" + trace + "\n")
        except Exception:
            pass


# ================================================================
#  Janela de Análises / Gráficos (Canvas puro)
# ================================================================
class AnalisesWindow(tk.Toplevel):
    """
    - Se chamado com (fornecedor_id, pregao): mostra análise da ATA
    - Se chamado com (empenho_id): mostra análise do empenho
    - Se chamado apenas com (fornecedor_id): mostra seletor para escolher ATA
    """

    def __init__(self, master, fornecedor_id=None, pregao=None, empenho_id=None):
        super().__init__(master)
        self.title("Análises / Gráficos")
        self.geometry("900x600")
        self.configure(bg="white")
        self.resizable(True, True)

        self.fornecedor_id = fornecedor_id
        self.pregao = pregao
        self.empenho_id = empenho_id

        # Topo
        top = tk.Frame(self, bg="white")
        top.pack(fill="x", padx=12, pady=8)

        self.lbl_titulo = tk.Label(top, text="", font=("Segoe UI", 12, "bold"), bg="white")
        self.lbl_titulo.pack(side="left")

        ttk.Button(top, text="Fechar", command=self.destroy).pack(side="right")

        # Conteúdo
        body = tk.Frame(self, bg="white")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Coluna esquerda: KPIs
        self.kpi = tk.Frame(body, bg="white")
        self.kpi.pack(side="left", fill="y", padx=(0, 10))

        # Direita: gráficos
        right = tk.Frame(body, bg="white")
        right.pack(side="left", fill="both", expand=True)

        self.lf1 = ttk.LabelFrame(right, text="Gráfico principal", padding=6)
        self.lf1.pack(fill="both", expand=True)

        self.canvas1 = tk.Canvas(self.lf1, bg="white", height=260, highlightthickness=0)
        self.canvas1.pack(fill="both", expand=True)

        self.lf2 = ttk.LabelFrame(right, text="Detalhe", padding=6)
        self.lf2.pack(fill="both", expand=True, pady=(8, 0))

        self.canvas2 = tk.Canvas(self.lf2, bg="white", height=220, highlightthickness=0)
        self.canvas2.pack(fill="both", expand=True)

        # Rodapé informativo
        self.lbl_info = tk.Label(self, text="", bg="white", fg="#666", font=("Segoe UI", 9))
        self.lbl_info.pack(fill="x", padx=12, pady=(0, 10))

        # Roteia
        if self.empenho_id:
            self._carregar_empenho()
        elif self.pregao and self.fornecedor_id:
            self._carregar_ata()
        else:
            self._carregar_seletor_ata()

    # ----------------- Análise de ATA -----------------
    def _carregar_ata(self):
        try:
            # Obtem ID do cabeçalho pelo número (pregao == numero na tabela 'atas')
            conn = banco.conectar(); cur = conn.cursor()
            cur.execute("SELECT id FROM atas WHERE fornecedor_id=? AND numero=?", (self.fornecedor_id, self.pregao))
            row = cur.fetchone()
            ata_id = int(row[0]) if row else None
            conn.close()

            if not ata_id:
                messagebox.showwarning("Análise de ATA", "ATA não encontrada para este fornecedor.")
                self.destroy(); return

            itens = banco.ata_itens_listar_por_ata(ata_id)  # id, cod_aghu, nome_item, qtde_total, vl_unit, vl_total, observacao
            itens_saldo = banco.ata_itens_listar_por_ata_com_saldo(ata_id)  # inclui qtde_empenhada, qtde_saldo

            # Agrega quantidades
            qt_total = sum(float(x.get("qtde_total") or 0) for x in itens)
            qt_empenhada = sum(float(x.get("qtde_empenhada") or 0) for x in itens_saldo)
            qt_saldo = sum(float(x.get("qtde_saldo") or 0) for x in itens_saldo)

            self._titulo(f"ATA {self.pregao} — Fornecedor {self.fornecedor_id}")
            self._kpis([
                ("Itens", len(itens)),
                ("Qtde total", qt_total),
                ("Qtde empenhada", qt_empenhada),
                ("Qtde saldo", qt_saldo),
            ])

            # Gráfico 1: Pizza (empenhada x saldo)
            self._pizza(self.canvas1, [("Empenhada", qt_empenhada, "#107C10"), ("Saldo", qt_saldo, "#0078D4")])

            # Gráfico 2: Top-10 itens por saldo (barras)
            top = sorted(
                [(i.get("nome_item",""), float(i.get("qtde_saldo") or 0)) for i in itens_saldo],
                key=lambda t: t[1], reverse=True
            )[:10]
            self._barras_horiz(self.canvas2, top, titulo="Top-10 itens por saldo (quantidade)")

            self._info(f"Itens: {len(itens)} • Total: {qt_total:.0f} • Empenhada: {qt_empenhada:.0f} • Saldo: {qt_saldo:.0f}")
        except Exception:
            self._log_erro("Falha ao carregar análise de ATA", traceback.format_exc())
            messagebox.showerror("Erro", "Não foi possível carregar a análise da ATA.")
            self.destroy()

    # ----------------- Análise de Empenho -----------------
    def _carregar_empenho(self):
        try:
            # Recupera dados do empenho pelo ID
            conn = banco.conectar(); cur = conn.cursor()
            cur.execute("""
                SELECT id, fornecedor_id, cod_aghu, nome_item, vl_total
                  FROM empenhos
                 WHERE id=?
            """, (self.empenho_id,))
            emp = cur.fetchone()
            if not emp:
                conn.close()
                messagebox.showwarning("Análise de Empenho", "Empenho não encontrado.")
                self.destroy(); return

            # Consumo (notas_itens) deste empenho
            cur.execute("SELECT IFNULL(SUM(vl_total),0) FROM notas_itens WHERE empenho_id = ?", (self.empenho_id,))
            consumido = float(cur.fetchone()[0] or 0)
            conn.close()

            total = float(emp["vl_total"] or 0)
            saldo = total - consumido

            self._titulo(f"Empenho #{self.empenho_id} — {emp['nome_item']}")
            self._kpis([
                ("Valor total", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X",".")),
                ("Consumido", f"R$ {consumido:,.2f}".replace(",", "X").replace(".", ",").replace("X",".")),
                ("Saldo", f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X",".")),
            ])

            # Pizza (consumido x saldo)
            self._pizza(self.canvas1, [("Consumido", consumido, "#D83B01"), ("Saldo", saldo, "#0078D4")])

            # Tabela simples dos itens deste empenho (se houver granularidade)
            self._tabela_empenho_itens(self.canvas2, self.empenho_id)

            self._info(f"Total: R$ {total:,.2f} • Consumido: R$ {consumido:,.2f} • Saldo: R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
        except Exception:
            self._log_erro("Falha ao carregar análise do empenho", traceback.format_exc())
            messagebox.showerror("Erro", "Não foi possível carregar a análise do empenho.")
            self.destroy()

    # ----------------- Seletor de ATA (quando só fornecedor foi passado) -----------------
    def _carregar_seletor_ata(self):
        self._titulo("Selecione uma ATA para analisar")
        cont = tk.Frame(self, bg="white")
        cont.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(cont, text="ATA (número):").pack(anchor="w")
        cb = ttk.Combobox(cont, state="readonly", width=40)
        cb.pack(anchor="w", pady=(4, 12))

        # carrega atas do fornecedor
        try:
            conn = banco.conectar(); cur = conn.cursor()
            cur.execute("SELECT numero FROM atas WHERE fornecedor_id=? ORDER BY numero DESC", (self.fornecedor_id,))
            atas = [r[0] for r in cur.fetchall()]
            conn.close()
            cb["values"] = atas
        except Exception:
            self._log_erro("Falha ao carregar atas no seletor", traceback.format_exc())
            cb["values"] = []

        def abrir():
            num = cb.get()
            if not num:
                return
            self.pregao = num
            for w in (cont,):
                w.destroy()
            self._carregar_ata()

        ttk.Button(cont, text="Abrir", command=abrir).pack(anchor="w")

    # ----------------- Widgets auxiliares (KPIs, gráficos, tabela) -----------------
    def _titulo(self, txt: str):
        self.lbl_titulo.config(text=txt)

    def _info(self, txt: str):
        self.lbl_info.config(text=txt)

    def _kpis(self, pares):
        # Limpa
        for w in self.kpi.winfo_children():
            w.destroy()

        cores = ["#0063B1", "#107C10", "#D83B01", "#5C2D91", "#0078D4", "#FF8C00"]
        for i, (titulo, valor) in enumerate(pares):
            cor = cores[i % len(cores)]
            card = tk.Frame(self.kpi, bg="white")
            card.pack(fill="x", pady=6)
            tk.Frame(card, bg=cor, height=3).pack(fill="x", side="top")
            corpo = tk.Frame(card, bg="white")
            corpo.pack(fill="x", padx=8, pady=6)
            tk.Label(corpo, text=titulo, bg="white", fg="#555", font=("Segoe UI", 9)).pack(anchor="w")
            tk.Label(corpo, text=str(valor), bg="white", fg="#222", font=("Segoe UI", 14, "bold")).pack(anchor="w")

    def _pizza(self, cv: tk.Canvas, partes):
        # partes = [(rotulo, valor, cor)]
        cv.delete("all")
        w = cv.winfo_width() or cv.winfo_reqwidth()
        h = cv.winfo_height() or cv.winfo_reqheight()
        cx, cy = w // 2, h // 2
        r = min(w, h) * 0.35
        total = sum(max(0.0, float(v)) for (_, v, _c) in partes) or 1.0

        ang = 0.0
        bbox = (cx - r, cy - r, cx + r, cy + r)
        legend_y = 10
        for (rot, val, cor) in partes:
            frac = max(0.0, float(val)) / total
            ang2 = ang + frac * 360.0
            cv.create_arc(bbox, start=ang, extent=(ang2 - ang), fill=cor, outline="white")
            # legenda
            txt = f"{rot}: {frac*100:0.1f}%"
            cv.create_rectangle(10, legend_y, 22, legend_y + 12, fill=cor, outline=cor)
            cv.create_text(30, legend_y + 6, text=txt, anchor="w", font=("Segoe UI", 9), fill="#333")
            legend_y += 18
            ang = ang2

    def _barras_horiz(self, cv: tk.Canvas, dados, titulo=""):
        # dados = [(label, valor)]
        cv.delete("all")
        w = cv.winfo_width() or cv.winfo_reqwidth()
        h = cv.winfo_height() or cv.winfo_reqheight()
        margem = 8
        x0 = 140
        y0 = 24
        x1 = w - 12
        y1 = h - 16

        if titulo:
            cv.create_text(w//2, 12, text=titulo, font=("Segoe UI", 10, "bold"), fill="#333")

        if not dados:
            cv.create_text(w//2, h//2, text="Sem dados", font=("Segoe UI", 10), fill="#666")
            return

        valores = [v for (_l, v) in dados]
        vmax = max(valores) or 1.0

        n = len(dados)
        barra_h = max(14, int((y1 - y0) / max(1, n)) - 4)
        y = y0

        for (lab, val) in dados:
            largura = (val / vmax) * (x1 - x0)
            cv.create_text(margem, y + barra_h / 2, text=str(lab)[:30], anchor="w", font=("Segoe UI", 9), fill="#333")
            cv.create_rectangle(x0, y, x0 + largura, y + barra_h, fill="#0078D4", outline="")
            cv.create_text(x0 + largura + 4, y + barra_h / 2, text=f"{val:.0f}", anchor="w", font=("Segoe UI", 9), fill="#444")
            y += barra_h + 6

    def _tabela_empenho_itens(self, cv: tk.Canvas, empenho_id: int):
        """Desenha uma mini-tabela dos itens do empenho (cód, nome, qtde, valores)."""
        cv.delete("all")
        w = cv.winfo_width() or cv.winfo_reqwidth()

        try:
            conn = banco.conectar(); cur = conn.cursor()
            cur.execute("""
                SELECT cod_aghu, nome_item, qtde, vl_unit, vl_total
                  FROM empenhos
                 WHERE id=?
            """, (empenho_id,))
            r = cur.fetchone()
            conn.close()
            if not r:
                cv.create_text(w//2, 40, text="Empenho sem itens detalhados.", font=("Segoe UI", 10), fill="#666")
                return
            linhas = [("Cód. AGHU", r["cod_aghu"]), ("Item", r["nome_item"]),
                      ("Qtde", f'{float(r["qtde"] or 0):.0f}'),
                      ("Vlr unit.", f'R$ {float(r["vl_unit"] or 0):,.2f}'.replace(",", "X").replace(".", ",").replace("X",".")),
                      ("Vlr total", f'R$ {float(r["vl_total"] or 0):,.2f}'.replace(",", "X").replace(".", ",").replace("X","."))]
        except Exception:
            linhas = []

        if not linhas:
            cv.create_text(w//2, 40, text="Sem dados para exibir.", font=("Segoe UI", 10), fill="#666")
            return

        x_label, x_val = 12, 220
        y = 16
        for (k, v) in linhas:
            cv.create_text(x_label, y, text=k + ":", anchor="w", font=("Segoe UI", 9, "bold"), fill="#333")
            cv.create_text(x_val, y, text=str(v), anchor="w", font=("Segoe UI", 9), fill="#333")
            y += 22

    # ----------------- Log -----------------
    def _log_erro(self, msg: str, trace: str):
        try:
            caminho = os.path.join(tempfile.gettempdir(), "control_notas_erro.log")
            with open(caminho, "a", encoding="utf-8") as f:
                f.write("\n--- ANALISES ---\n" + msg + "\n" + trace + "\n")
        except Exception:
            pass
