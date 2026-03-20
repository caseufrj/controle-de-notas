# telas/dashboard.py
import os
import csv
import math
import tempfile
import traceback
import tkinter as tk
from tkinter import ttk, messagebox

import banco

try:
    from PIL import Image  # opcional para converter EPS->PNG
    PIL_OK = True
except Exception:
    PIL_OK = False


class Dashboard(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")
        banco.criar_tabelas()

        # ------- Topo: seleção de fornecedor + período + ações -------
        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=16, pady=(12, 6))

        tk.Label(topo, text="Fornecedor:", bg="white").pack(side="left")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=46)
        self.cb_fornec.pack(side="left", padx=8)
        self.cb_fornec.bind("<<ComboboxSelected>>", lambda e: self.atualizar_listas())

        ttk.Button(topo, text="Atualizar", command=self.atualizar_listas).pack(side="left", padx=6)

        # Período
        tk.Label(topo, text="Período:", bg="white").pack(side="left", padx=(12, 2))
        self.ent_ini = ttk.Entry(topo, width=12)
        self.ent_ini.pack(side="left")
        tk.Label(topo, text="até", bg="white").pack(side="left", padx=4)
        self.ent_fim = ttk.Entry(topo, width=12)
        self.ent_fim.pack(side="left", padx=(0, 8))

        ttk.Button(topo, text="Indicadores (Período)", command=self._abrir_indicadores).pack(side="right")
        ttk.Button(topo, text="Análises / Gráficos", command=self._abrir_analises).pack(side="right", padx=(0, 6))

        # Autoatualizar
        self._auto = tk.BooleanVar(value=False)
        ttk.Checkbutton(topo, text="Autoatualizar (10s)", variable=self._auto,
                        command=self._tick_auto).pack(side="left", padx=(8, 0))

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
        widths = {"pregao": 120, "cod_aghu": 100, "nome_item": 260, "qtde_total": 100, "qtde_usada": 100, "qtde_saldo": 100}
        for c in cols_ata:
            self.tv_ata.heading(c, text=cab.get(c, c))
            anchor = "w" if c in ("pregao", "cod_aghu", "nome_item") else "e"
            self.tv_ata.column(c, width=widths.get(c, 120), anchor=anchor, stretch=(c == "nome_item"))
        self.tv_ata.pack(fill="both", expand=True)
        self.tv_ata.bind("<Double-1>", self._abrir_analise_ata_por_duplo_clique)

        # ---- Saldos Empenho (valor) ----
        lf_emp = ttk.LabelFrame(split, text="Saldo de Empenhos (valor)")
        lf_emp.pack(side="left", fill="both", expand=True, padx=(8, 0))

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
        widths_emp = {"empenho_id": 1, "cod_aghu": 100, "nome_item": 260, "vl_total": 110, "valor_consumido": 110, "valor_saldo": 110}
        for c in cols_emp:
            self.tv_emp.heading(c, text=cab_emp.get(c, c))
            anchor = "w" if c in ("cod_aghu", "nome_item") else "e"
            self.tv_emp.column(c, width=widths_emp.get(c, 100), anchor=anchor, stretch=(c == "nome_item"))
        self.tv_emp.column("empenho_id", width=1, stretch=False, anchor="center")
        self.tv_emp.pack(fill="both", expand=True)
        self.tv_emp.bind("<Double-1>", self._abrir_analise_empenho_por_duplo_clique)

        # Dados iniciais
        self._carregar_fornecedores()

    # ----------------- Autoatualizar -----------------
    def _tick_auto(self):
        if self._auto.get():
            self.after(1000, self._loop_auto)

    def _loop_auto(self):
        if not self._auto.get():
            return
        try:
            self.atualizar_listas()
        except Exception:
            self._log_erro("Autoatualizar falhou", traceback.format_exc())
        finally:
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
            emp_id = r.get("empenho_id") if "empenho_id" in r else r.get("id")
            self.tv_emp.insert("", "end", values=(
                emp_id or "",
                r.get("cod_aghu", ""),
                r.get("nome_item", ""),
                f'{float(r.get("vl_total", 0.0)):.2f}',
                f'{float(r.get("valor_consumido", 0.0)):.2f}',
                f'{float(r.get("valor_saldo", 0.0)):.2f}',
            ))

    # ----------------- Aberturas rápidas -----------------
    def _abrir_analise_ata_por_duplo_clique(self, _evt):
        sel = self.tv_ata.selection()
        if not sel:
            return
        vals = self.tv_ata.item(sel[0], "values")
        pregao = vals[0]
        nome = self.cb_fornec.get()
        forn_id = self.map_forn.get(nome)
        if pregao and forn_id:
            AnalisesWindow(self, fornecedor_id=forn_id, pregao=pregao,
                           data_ini=self.ent_ini.get().strip() or None,
                           data_fim=self.ent_fim.get().strip() or None)

    def _abrir_analise_empenho_por_duplo_clique(self, _evt):
        sel = self.tv_emp.selection()
        if not sel:
            return
        vals = self.tv_emp.item(sel[0], "values")
        try:
            emp_id = int(vals[0])
        except Exception:
            return
        AnalisesWindow(self, empenho_id=emp_id,
                       data_ini=self.ent_ini.get().strip() or None,
                       data_fim=self.ent_fim.get().strip() or None)

    def _abrir_analises(self):
        nome = self.cb_fornec.get()
        forn_id = self.map_forn.get(nome)
        if not forn_id:
            messagebox.showwarning("Atenção", "Selecione um fornecedor.")
            return
        sel_ata = self.tv_ata.selection()
        sel_emp = self.tv_emp.selection()
        if sel_ata:
            pregao = self.tv_ata.item(sel_ata[0], "values")[0]
            AnalisesWindow(self, fornecedor_id=forn_id, pregao=pregao,
                           data_ini=self.ent_ini.get().strip() or None,
                           data_fim=self.ent_fim.get().strip() or None)
        elif sel_emp:
            emp_id_txt = self.tv_emp.item(sel_emp[0], "values")[0]
            try:
                emp_id = int(emp_id_txt)
            except Exception:
                emp_id = None
            if emp_id:
                AnalisesWindow(self, empenho_id=emp_id,
                               data_ini=self.ent_ini.get().strip() or None,
                               data_fim=self.ent_fim.get().strip() or None)
            else:
                messagebox.showinfo("Análises", "Selecione um empenho válido.")
        else:
            # Sem seleção: abre seletor de ATA
            AnalisesWindow(self, fornecedor_id=forn_id,
                           data_ini=self.ent_ini.get().strip() or None,
                           data_fim=self.ent_fim.get().strip() or None)

    def _abrir_indicadores(self):
        IndicadoresWindow(self,
                          fornecedor_id=self.map_forn.get(self.cb_fornec.get()),
                          data_ini=self.ent_ini.get().strip() or None,
                          data_fim=self.ent_fim.get().strip() or None)

    # ----------------- Log -----------------
    def _log_erro(self, msg: str, trace: str):
        try:
            caminho = os.path.join(tempfile.gettempdir(), "control_notas_erro.log")
            with open(caminho, "a", encoding="utf-8") as f:
                f.write("\n--- DASHBOARD ---\n" + msg + "\n" + trace + "\n")
        except Exception:
            pass


# ================================================================
#  Janela de Análises / Gráficos
# ================================================================
class AnalisesWindow(tk.Toplevel):
    def __init__(self, master, fornecedor_id=None, pregao=None, empenho_id=None,
                 data_ini=None, data_fim=None):
        super().__init__(master)
        self.title("Análises / Gráficos")
        self.geometry("1000x680")
        self.configure(bg="white")
        self.resizable(True, True)

        self.fornecedor_id = fornecedor_id
        self.pregao = pregao
        self.empenho_id = empenho_id
        self.data_ini = data_ini
        self.data_fim = data_fim

        # --- Topo ---
        top = tk.Frame(self, bg="white")
        top.pack(fill="x", padx=12, pady=8)

        self.lbl_titulo = tk.Label(top, text="", font=("Segoe UI", 12, "bold"), bg="white")
        self.lbl_titulo.pack(side="left")

        self.metric = tk.StringVar(value="valor")  # 'valor' | 'quantidade'
        self.metric_buttons = tk.Frame(top, bg="white")
        ttk.Radiobutton(self.metric_buttons, text="Valor (R$)", value="valor",
                        variable=self.metric, command=self._render_metric).pack(side="left")
        ttk.Radiobutton(self.metric_buttons, text="Quantidade", value="quantidade",
                        variable=self.metric, command=self._render_metric).pack(side="left")

        # Exportar / Salvar PNG / Fechar
        ttk.Button(top, text="Salvar PNG", command=self._salvar_png).pack(side="right", padx=(0, 6))
        ttk.Button(top, text="Exportar CSV", command=self._exportar_csv).pack(side="right", padx=(0, 6))
        ttk.Button(top, text="Fechar", command=self.destroy).pack(side="right")

        # --- Corpo ---
        body = tk.Frame(self, bg="white")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # KPIs
        self.kpi = tk.Frame(body, bg="white")
        self.kpi.pack(side="left", fill="y", padx=(0, 10))

        # Gráficos
        right = tk.Frame(body, bg="white")
        right.pack(side="left", fill="both", expand=True)

        self.lf1 = ttk.LabelFrame(right, text="Gráfico principal", padding=6)
        self.lf1.pack(fill="both", expand=True)
        self.canvas1 = tk.Canvas(self.lf1, bg="white", height=280, highlightthickness=0)
        self.canvas1.pack(fill="both", expand=True)

        self.lf2 = ttk.LabelFrame(right, text="Detalhe", padding=6)
        self.lf2.pack(fill="both", expand=True, pady=(8, 0))
        self.canvas2 = tk.Canvas(self.lf2, bg="white", height=260, highlightthickness=0)
        self.canvas2.pack(fill="both", expand=True)

        self.lbl_info = tk.Label(self, text="", bg="white", fg="#666", font=("Segoe UI", 9))
        self.lbl_info.pack(fill="x", padx=12, pady=(0, 10))

        self._context = {}

        # Roteia
        if self.empenho_id:
            self.metric_buttons.pack_forget()
            self._carregar_empenho()
        elif self.pregao and self.fornecedor_id:
            self.metric_buttons.pack(side="left", padx=12)
            self._carregar_ata()
        else:
            self.metric_buttons.pack_forget()
            self._carregar_seletor_ata()

    # ----------------- ATA -----------------
    def _carregar_ata(self):
        try:
            conn = banco.conectar(); cur = conn.cursor()
            cur.execute("SELECT id FROM atas WHERE fornecedor_id=? AND numero=?", (self.fornecedor_id, self.pregao))
            row = cur.fetchone(); ata_id = int(row[0]) if row else None
            conn.close()
            if not ata_id:
                messagebox.showwarning("Análise de ATA", "ATA não encontrada para este fornecedor.")
                self.destroy(); return

            # Quantidades
            itens = banco.ata_itens_listar_por_ata(ata_id)
            itens_saldo = banco.ata_itens_listar_por_ata_com_saldo(ata_id)
            qt_total = sum(float(x.get("qtde_total") or 0) for x in itens)
            qt_empenhada = sum(float(x.get("qtde_empenhada") or 0) for x in itens_saldo)
            qt_saldo = sum(float(x.get("qtde_saldo") or 0) for x in itens_saldo)

            # Valores (respeitando período no consumo)
            conn = banco.conectar(); cur = conn.cursor()
            cur.execute("""
                SELECT 
                    IFNULL((SELECT SUM(e.vl_total) FROM empenhos e 
                             WHERE e.ata_item_id IN (SELECT id FROM atas_itens WHERE ata_id=?)), 0),
                    IFNULL((SELECT SUM(ni.vl_total)  FROM notas_itens ni
                             WHERE ni.ata_item_id IN (SELECT id FROM atas_itens WHERE ata_id=?)
                               AND (? IS NULL OR date(ni.data_uso) >= date(?))
                               AND (? IS NULL OR date(ni.data_uso) <= date(?))
                            ), 0)
            """, (ata_id, ata_id, self.data_ini, self.data_ini, self.data_fim, self.data_fim))
            vl_empenhado, vl_consumido = cur.fetchone()
            vl_empenhado = float(vl_empenhado or 0.0)
            vl_consumido = float(vl_consumido or 0.0)
            vl_saldo = vl_empenhado - vl_consumido
            conn.close()

            # Top-10 saldos (valor e qtd)
            # Valor (usa subselects sem período no empenhado; consumo pode ser com período se desejar)
            conn = banco.conectar(); cur = conn.cursor()
            cur.execute("""
                SELECT 
                    ai.id, ai.nome_item,
                    IFNULL((SELECT SUM(e.vl_total)  FROM empenhos e WHERE e.ata_item_id = ai.id),0) AS emp,
                    IFNULL((SELECT SUM(ni.vl_total) FROM notas_itens ni
                             WHERE ni.ata_item_id = ai.id
                               AND (? IS NULL OR date(ni.data_uso) >= date(?))
                               AND (? IS NULL OR date(ni.data_uso) <= date(?))
                    ),0) AS cons
                FROM atas_itens ai
                WHERE ai.ata_id=?
            """, (self.data_ini, self.data_ini, self.data_fim, self.data_fim, ata_id))
            top_valor = []
            for r in cur.fetchall():
                saldo = float(r["emp"] or 0) - float(r["cons"] or 0)
                top_valor.append((r["nome_item"], max(0.0, saldo)))
            conn.close()
            top_valor.sort(key=lambda t: t[1], reverse=True)
            top_valor = top_valor[:10]

            top_qt = sorted(
                [(i.get("nome_item",""), float(i.get("qtde_saldo") or 0)) for i in itens_saldo],
                key=lambda t: t[1], reverse=True
            )[:10]

            # Consumo mensal (valor e qtd) no período
            conn = banco.conectar(); cur = conn.cursor()
            cur.execute("""
                SELECT strftime('%Y-%m', COALESCE(NULLIF(ni.data_uso, ''), ni.nota_id || '')) AS ano_mes,
                       IFNULL(SUM(ni.vl_total),0) AS total_mes,
                       IFNULL(SUM(ni.qtde),0)     AS qtde_mes
                  FROM notas_itens ni
                 WHERE ni.ata_item_id IN (SELECT id FROM atas_itens WHERE ata_id=?)
                   AND (? IS NULL OR date(ni.data_uso) >= date(?))
                   AND (? IS NULL OR date(ni.data_uso) <= date(?))
                 GROUP BY ano_mes
                 ORDER BY ano_mes
            """, (ata_id, self.data_ini, self.data_ini, self.data_fim, self.data_fim))
            serie_valor = []; serie_qt = []
            for r in cur.fetchall():
                mes = r["ano_mes"] or "-"
                serie_valor.append((mes, float(r["total_mes"] or 0)))
                serie_qt.append((mes, float(r["qtde_mes"] or 0)))
            conn.close()

            self._context = {
                "tipo": "ata",
                "ata_id": ata_id,
                "kpi_qt": (qt_total, qt_empenhada, qt_saldo),
                "kpi_vl": (vl_empenhado, vl_consumido, vl_saldo),
                "top_qt": top_qt,
                "top_vl": top_valor,
                "serie_qt": serie_qt,
                "serie_vl": serie_valor,
                "itens": itens,
                "itens_saldo": itens_saldo
            }

            self._titulo(f"ATA {self.pregao} — Fornecedor {self.fornecedor_id}  "
                         f"{'(período: ' + (self.data_ini or '-') + ' a ' + (self.data_fim or '-') + ')' if (self.data_ini or self.data_fim) else ''}")

            self._render_metric()
        except Exception:
            self._log_erro("Falha ao carregar análise de ATA", traceback.format_exc())
            messagebox.showerror("Erro", "Não foi possível carregar a análise da ATA.")
            self.destroy()

    # ----------------- Empenho -----------------
    def _carregar_empenho(self):
        try:
            conn = banco.conectar(); cur = conn.cursor()
            cur.execute("""
                SELECT id, fornecedor_id, cod_aghu, nome_item, qtde, vl_unit, vl_total
                  FROM empenhos
                 WHERE id=?
            """, (self.empenho_id,))
            emp = cur.fetchone()
            if not emp:
                conn.close()
                messagebox.showwarning("Análise de Empenho", "Empenho não encontrado.")
                self.destroy(); return

            cur.execute("""
                SELECT IFNULL(SUM(vl_total),0), IFNULL(SUM(qtde),0)
                  FROM notas_itens
                 WHERE empenho_id = ?
                   AND (? IS NULL OR date(data_uso) >= date(?))
                   AND (? IS NULL OR date(data_uso) <= date(?))
            """, (self.empenho_id, self.data_ini, self.data_ini, self.data_fim, self.data_fim))
            cons_val, cons_qt = cur.fetchone()
            cons_val = float(cons_val or 0.0); cons_qt = float(cons_qt or 0.0)

            cur.execute("""
                SELECT strftime('%Y-%m', COALESCE(NULLIF(data_uso, ''), nota_id || '')) AS ano_mes,
                       IFNULL(SUM(vl_total),0) AS total_mes
                  FROM notas_itens
                 WHERE empenho_id=?
                   AND (? IS NULL OR date(data_uso) >= date(?))
                   AND (? IS NULL OR date(data_uso) <= date(?))
                 GROUP BY ano_mes
                 ORDER BY ano_mes
            """, (self.empenho_id, self.data_ini, self.data_ini, self.data_fim, self.data_fim))
            serie = [(r[0] or "-", float(r[1] or 0.0)) for r in cur.fetchall()]
            conn.close()

            total = float(emp["vl_total"] or 0.0)
            saldo = total - cons_val

            self._context = {
                "tipo": "empenho",
                "emp": emp,
                "serie": serie,
                "cons_val": cons_val,
                "cons_qt": cons_qt,
                "saldo": saldo
            }

            self._titulo(f"Empenho #{self.empenho_id} — {emp['nome_item']}  "
                         f"{'(período: ' + (self.data_ini or '-') + ' a ' + (self.data_fim or '-') + ')' if (self.data_ini or self.data_fim) else ''}")

            self._kpis([
                ("Valor total", self._fmt_brl(total)),
                ("Consumido", self._fmt_brl(cons_val)),
                ("Saldo", self._fmt_brl(saldo)),
                ("Qtde (se aplicável)", f"{float(emp['qtde'] or 0):.0f}")
            ])
            self._pizza(self.canvas1, [("Consumido", cons_val, "#D83B01"), ("Saldo", saldo, "#0078D4")])
            self._barras_vert(self.canvas2, self._prep_serie(self._context["serie"]), "Consumo mensal (R$)")
            self._info(f"Total: {self._fmt_brl(total)} • Consumido: {self._fmt_brl(cons_val)} • Saldo: {self._fmt_brl(saldo)}")
        except Exception:
            self._log_erro("Falha ao carregar análise do empenho", traceback.format_exc())
            messagebox.showerror("Erro", "Não foi possível carregar a análise do empenho.")
            self.destroy()

    # ----------------- Seletor de ATA -----------------
    def _carregar_seletor_ata(self):
        self._titulo("Selecione uma ATA para analisar")
        cont = tk.Frame(self, bg="white")
        cont.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(cont, text="ATA (número):").pack(anchor="w")
        cb = ttk.Combobox(cont, state="readonly", width=40)
        cb.pack(anchor="w", pady=(4, 12))

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
            self.metric_buttons.pack(side="left", padx=12)
            self._carregar_ata()

        ttk.Button(cont, text="Abrir", command=abrir).pack(anchor="w")

    # ----------------- Alternância de métrica (ATA) -----------------
    def _render_metric(self):
        if self._context.get("tipo") != "ata":
            return
        m = self.metric.get()

        if m == "valor":
            vl_empenhado, vl_consumido, vl_saldo = self._context["kpi_vl"]
            self._kpis([
                ("Empenhado (R$)", self._fmt_brl(vl_empenhado)),
                ("Consumido (R$)", self._fmt_brl(vl_consumido)),
                ("Saldo (R$)", self._fmt_brl(vl_saldo)),
            ])
            self._pizza(self.canvas1, [("Consumido", vl_consumido, "#D83B01"), ("Saldo", vl_saldo, "#0078D4")])
            self._barras_horiz(self.canvas2, self._context["top_vl"], "Top-10 itens por saldo (R$)")
            self._info(f"Empenhado: {self._fmt_brl(vl_empenhado)} • Consumido: {self._fmt_brl(vl_consumido)} • Saldo: {self._fmt_brl(vl_saldo)}")
        else:
            qt_total, qt_empenhada, qt_saldo = self._context["kpi_qt"]
            self._kpis([
                ("Qtde total", f"{qt_total:.0f}"),
                ("Qtde empenhada", f"{qt_empenhada:.0f}"),
                ("Qtde saldo", f"{qt_saldo:.0f}"),
            ])
            self._pizza(self.canvas1, [("Empenhada", qt_empenhada, "#107C10"), ("Saldo", qt_saldo, "#0078D4")])
            self._barras_horiz(self.canvas2, self._context["top_qt"], "Top-10 itens por saldo (quantidade)")
            self._info(f"Itens: {len(self._context['itens'])} • Total: {qt_total:.0f} • Empenhada: {qt_empenhada:.0f} • Saldo: {qt_saldo:.0f}")

    # ----------------- Exportações / Salvar PNG -----------------
    def _exportar_csv(self):
        try:
            pasta_tmp = tempfile.gettempdir()
            if self._context.get("tipo") == "ata":
                caminho = os.path.join(pasta_tmp, f"ata_{self._context['ata_id']}_itens.csv")
                self._exportar_csv_ata(caminho)
            elif self._context.get("tipo") == "empenho":
                caminho = os.path.join(pasta_tmp, f"empenho_{self.empenho_id}_consumo.csv")
                self._exportar_csv_empenho(caminho)
            messagebox.showinfo("Exportação", f"CSV gerado em:\n{caminho}")
        except Exception:
            self._log_erro("Falha ao exportar CSV", traceback.format_exc())
            messagebox.showerror("Exportação", "Não foi possível exportar os dados.")

    def _salvar_png(self):
        try:
            pasta_tmp = tempfile.gettempdir()
            arq1 = os.path.join(pasta_tmp, "grafico1.png")
            arq2 = os.path.join(pasta_tmp, "grafico2.png")
            ok1 = self._canvas_to_png(self.canvas1, arq1)
            ok2 = self._canvas_to_png(self.canvas2, arq2)
            if ok1 or ok2:
                msg = "Salvo:\n"
                if ok1: msg += f"- {arq1}\n"
                if ok2: msg += f"- {arq2}\n"
                if not PIL_OK:
                    msg += "\nObs.: Pillow não encontrado. Salvei também arquivos .EPS (compatíveis com editores vetoriais)."
                messagebox.showinfo("Salvar PNG", msg)
            else:
                messagebox.showwarning("Salvar PNG", "Não foi possível salvar os gráficos.")
        except Exception:
            self._log_erro("Falha ao salvar PNG", traceback.format_exc())
            messagebox.showerror("Salvar PNG", "Erro ao salvar os gráficos.")

    def _canvas_to_png(self, canvas: tk.Canvas, destino_png: str) -> bool:
        # Gera PostScript e tenta converter com Pillow; sem Pillow, salva .eps como fallback
        try:
            ps = canvas.postscript(colormode='color')
            pasta_tmp = tempfile.gettempdir()
            arq_eps = destino_png[:-4] + ".eps"
            with open(arq_eps, "w", encoding="utf-8") as f:
                f.write(ps)
            if PIL_OK:
                img = Image.open(arq_eps)
                img.save(destino_png, "PNG")
                return True
            else:
                return os.path.exists(arq_eps)
        except Exception:
            return False

    def _exportar_csv_ata(self, caminho):
        ata_id = self._context["ata_id"]
        saldo_q = {i["id"]: i for i in self._context["itens_saldo"]}

        conn = banco.conectar(); cur = conn.cursor()
        cur.execute("""
            SELECT 
                ai.id,
                IFNULL((SELECT SUM(e.vl_total)  FROM empenhos e WHERE e.ata_item_id = ai.id),0) AS emp,
                IFNULL((SELECT SUM(ni.vl_total) FROM notas_itens ni
                         WHERE ni.ata_item_id = ai.id
                           AND (? IS NULL OR date(ni.data_uso) >= date(?))
                           AND (? IS NULL OR date(ni.data_uso) <= date(?))
                ),0) AS cons
            FROM atas_itens ai
            WHERE ai.ata_id=?
        """, (self.data_ini, self.data_ini, self.data_fim, self.data_fim, ata_id))
        valores = {r["id"]: (float(r["emp"] or 0.0), float(r["cons"] or 0.0)) for r in cur.fetchall()}
        conn.close()

        with open(caminho, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["cod_aghu", "nome_item", "qtde_total", "qtde_empenhada", "qtde_saldo",
                        "vl_empenhado", "vl_consumido", "vl_saldo"])
            for it in banco.ata_itens_listar_por_ata(ata_id):
                iid = it["id"]
                q = saldo_q.get(iid, {})
                emp, cons = valores.get(iid, (0.0, 0.0))
                w.writerow([
                    q.get("cod_aghu", it.get("cod_aghu","")),
                    q.get("nome_item", it.get("nome_item","")),
                    f'{float(q.get("qtde_total", it.get("qtde_total") or 0)):.0f}',
                    f'{float(q.get("qtde_empenhada", 0.0)):.0f}',
                    f'{float(q.get("qtde_saldo", 0.0)):.0f}',
                    f'{emp:.2f}'.replace(".", ","),
                    f'{cons:.2f}'.replace(".", ","),
                    f'{(emp - cons):.2f}'.replace(".", ",")
                ])

    def _exportar_csv_empenho(self, caminho):
        conn = banco.conectar(); cur = conn.cursor()
        cur.execute("""
            SELECT ni.id, ni.data_uso, ni.cod_aghu, ni.vl_unit, ni.qtde, ni.vl_total, a.pregao, a.nome_item
              FROM notas_itens ni
              LEFT JOIN atas_itens a ON a.id = ni.ata_item_id
             WHERE ni.empenho_id = ?
               AND (? IS NULL OR date(ni.data_uso) >= date(?))
               AND (? IS NULL OR date(ni.data_uso) <= date(?))
             ORDER BY ni.id
        """, (self.empenho_id, self.data_ini, self.data_ini, self.data_fim, self.data_fim))
        rows = cur.fetchall(); conn.close()

        with open(caminho, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["id", "data_uso", "cod_aghu", "vl_unit", "qtde", "vl_total", "ata", "item"])
            for r in rows:
                w.writerow([
                    r["id"], r["data_uso"] or "",
                    r["cod_aghu"] or "",
                    f'{float(r["vl_unit"] or 0):.2f}'.replace(".", ","),
                    f'{float(r["qtde"] or 0):.0f}',
                    f'{float(r["vl_total"] or 0):.2f}'.replace(".", ","),
                    r["pregao"] or "", r["nome_item"] or ""
                ])

    # ----------------- Widgets auxiliares -----------------
    def _titulo(self, txt: str):
        self.lbl_titulo.config(text=txt)

    def _info(self, txt: str):
        self.lbl_info.config(text=txt)

    def _kpis(self, pares):
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
        cv.delete("all")
        w = cv.winfo_width() or cv.winfo_reqwidth()
        h = cv.winfo_height() or cv.winfo_reqheight()
        cx, cy = w // 2, h // 2
        r = min(w, h) * 0.35
        total = sum(max(0.0, float(v)) for (_r, v, _c) in partes) or 1.0

        ang = 0.0
        bbox = (cx - r, cy - r, cx + r, cy + r)
        legend_y = 10
        for (rot, val, cor) in partes:
            frac = max(0.0, float(val)) / total
            ang2 = ang + frac * 360.0
            cv.create_arc(bbox, start=ang, extent=(ang2 - ang), fill=cor, outline="white")
            txt = f"{rot}: {frac*100:0.1f}%"
            cv.create_rectangle(10, legend_y, 22, legend_y + 12, fill=cor, outline=cor)
            cv.create_text(30, legend_y + 6, text=txt, anchor="w", font=("Segoe UI", 9), fill="#333")
            legend_y += 18
            ang = ang2

    def _barras_horiz(self, cv: tk.Canvas, dados, titulo=""):
        cv.delete("all")
        w = cv.winfo_width() or cv.winfo_reqwidth()
        h = cv.winfo_height() or cv.winfo_reqheight()
        margem = 8
        x0 = 160
        y0 = 32
        x1 = w - 12
        y1 = h - 16

        if titulo:
            cv.create_text(w//2, 14, text=titulo, font=("Segoe UI", 10, "bold"), fill="#333")

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
            cv.create_text(margem, y + barra_h / 2, text=str(lab)[:40], anchor="w", font=("Segoe UI", 9), fill="#333")
            cv.create_rectangle(x0, y, x0 + largura, y + barra_h, fill="#0078D4", outline="")
            rot_val = self._fmt_brl(val) if "R$" in (titulo or "") else f"{val:.0f}"
            cv.create_text(x0 + largura + 4, y + barra_h / 2, text=rot_val, anchor="w", font=("Segoe UI", 9), fill="#444")
            y += barra_h + 6

    def _barras_vert(self, cv: tk.Canvas, serie, titulo=""):
        cv.delete("all")
        w = cv.winfo_width() or cv.winfo_reqwidth()
        h = cv.winfo_height() or cv.winfo_reqheight()

        margem_esq = 56
        margem_inf = 36
        margem_dir = 10
        margem_sup = 22

        x0 = margem_esq
        y0 = margem_sup
        x1 = w - margem_dir
        y1 = h - margem_inf

        if titulo:
            cv.create_text(w//2, 12, text=titulo, font=("Segoe UI", 10, "bold"), fill="#333")

        if not serie:
            cv.create_text(w//2, h//2, text="Sem dados", font=("Segoe UI", 10), fill="#666")
            return

        valores = [v for (_m, v) in serie]
        vmax = max(valores) or 1.0
        escala = self._nice_ceil(vmax)
        if escala <= 0:
            escala = 1.0

        # grade
        linhas = 4
        for i in range(linhas + 1):
            y = y1 - (i / linhas) * (y1 - y0)
            cv.create_line(x0, y, x1, y, fill="#EEE")
            val = (escala * i / linhas)
            cv.create_text(x0 - 6, y, text=self._fmt_brl(val), font=("Segoe UI", 8), fill="#666", anchor="e")

        n = len(serie)
        largura_total = (x1 - x0)
        gap = max(4, int(largura_total / max(12, n) * 0.25))
        largura_barra = max(8, int((largura_total - gap * (n + 1)) / n))

        x = x0 + gap
        for (mes, valor) in serie:
            altura = 0 if escala == 0 else (valor / escala) * (y1 - y0)
            y_top = y1 - altura
            cv.create_rectangle(x, y_top, x + largura_barra, y1, fill="#0078D4", outline="#0078D4")
            cv.create_text(x + largura_barra / 2, y1 + 12, text=mes, font=("Segoe UI", 8), fill="#444")
            if altura > 22:
                cv.create_text(x + largura_barra / 2, y_top - 8, text=self._fmt_brl(valor),
                               font=("Segoe UI", 8), fill="#333")
            x += largura_barra + gap

        cv.create_line(x0, y0, x0, y1, fill="#AAA")
        cv.create_line(x0, y1, x1, y1, fill="#AAA")

    # ----------------- Utilitários -----------------
    def _nice_ceil(self, val: float) -> float:
        if val <= 0:
            return 1.0
        p = 10 ** int(math.floor(math.log10(val)))
        for m in (1, 2, 5, 10):
            alvo = m * p
            if val <= alvo:
                return float(alvo)
        return float(10 * p)

    def _fmt_brl(self, v: float) -> str:
        s = f"{v:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"

    def _prep_serie(self, serie):
        out = []
        for (k, v) in serie:
            try:
                ano, mes = (k or "-").split("-")
                rot = f"{mes}/{ano[-2:]}"
            except Exception:
                rot = k or "-"
            out.append((rot, v))
        return out

    def _log_erro(self, msg: str, trace: str):
        try:
            caminho = os.path.join(tempfile.gettempdir(), "control_notas_erro.log")
            with open(caminho, "a", encoding="utf-8") as f:
                f.write("\n--- ANALISES ---\n" + msg + "\n" + trace + "\n")
        except Exception:
            pass


# ================================================================
#  JANELA: Indicadores (Período)
# ================================================================
class IndicadoresWindow(tk.Toplevel):
    def __init__(self, master, fornecedor_id=None, data_ini=None, data_fim=None):
        super().__init__(master)
        self.title("Indicadores (Período)")
        self.geometry("1000x620")
        self.configure(bg="white")

        self.fornecedor_id = fornecedor_id
        self.data_ini = data_ini
        self.data_fim = data_fim

        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=12, pady=8)
        titulo = "Indicadores"
        if data_ini or data_fim:
            titulo += f" — Período: {data_ini or '-'} a {data_fim or '-'}"
        tk.Label(topo, text=titulo, font=("Segoe UI", 12, "bold"), bg="white").pack(side="left")
        ttk.Button(topo, text="Exportar CSVs", command=self._exportar_csvs).pack(side="right")
        ttk.Button(topo, text="Fechar", command=self.destroy).pack(side="right", padx=(0, 6))

        corpo = tk.Frame(self, bg="white")
        corpo.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Esquerda: % consumo por ATA (do fornecedor)
        lf_atas = ttk.LabelFrame(corpo, text="Consumo por ATA (Fornecedor)", padding=6)
        lf_atas.pack(side="left", fill="both", expand=True, padx=(0, 8))

        cols_a = ("pregao", "vl_empenhado", "vl_consumido", "perc_consumo")
        self.tv_atas = ttk.Treeview(lf_atas, columns=cols_a, show="headings", height=18)
        cab_a = {
            "pregao": "ATA",
            "vl_empenhado": "Empenhado (R$)",
            "vl_consumido": "Consumido (R$)",
            "perc_consumo": "% Consumo",
        }
        for c in cols_a:
            self.tv_atas.heading(c, text=cab_a[c])
            anchor = "w" if c == "pregao" else "e"
            self.tv_atas.column(c, width=140, anchor=anchor)
        self.tv_atas.pack(fill="both", expand=True)

        # Direita: Ranking de fornecedores (global)
        lf_rank = ttk.LabelFrame(corpo, text="Ranking de Fornecedores por Consumo (global)", padding=6)
        lf_rank.pack(side="left", fill="both", expand=True, padx=(8, 0))

        cols_r = ("fornecedor_nome", "valor_consumido")
        self.tv_rank = ttk.Treeview(lf_rank, columns=cols_r, show="headings", height=18)
        self.tv_rank.heading("fornecedor_nome", text="Fornecedor")
        self.tv_rank.heading("valor_consumido", text="Valor consumido (R$)")
        self.tv_rank.column("fornecedor_nome", width=260, anchor="w")
        self.tv_rank.column("valor_consumido", width=160, anchor="e")
        self.tv_rank.pack(fill="both", expand=True)

        self._carregar_dados()

    def _carregar_dados(self):
        # Esquerda: consumo por ATA (se tiver fornecedor)
        for i in self.tv_atas.get_children():
            self.tv_atas.delete(i)
        if self.fornecedor_id:
            try:
                dados = banco.consumo_por_ata(self.fornecedor_id, self.data_ini, self.data_fim)
            except Exception:
                dados = []
            for r in dados:
                self.tv_atas.insert("", "end", values=(
                    r["pregao"],
                    self._fmt_brl(r["vl_empenhado"]),
                    self._fmt_brl(r["vl_consumido"]),
                    f'{r["perc_consumo"]:.1f}%'
                ))

        # Direita: ranking global
        for i in self.tv_rank.get_children():
            self.tv_rank.delete(i)
        try:
            ranking = banco.ranking_fornecedores_consumo(self.data_ini, self.data_fim, limit=20)
        except Exception:
            ranking = []
        for r in ranking:
            self.tv_rank.insert("", "end", values=(r["fornecedor_nome"], self._fmt_brl(r["valor_consumido"])))

    def _exportar_csvs(self):
        pasta_tmp = tempfile.gettempdir()
        # CSV 1: consumo por ATA
        if self.fornecedor_id:
            c1 = os.path.join(pasta_tmp, f"indicadores_consumo_atas_{self.fornecedor_id}.csv")
            try:
                rows = banco.consumo_por_ata(self.fornecedor_id, self.data_ini, self.data_fim)
                with open(c1, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f, delimiter=";")
                    w.writerow(["ata", "vl_empenhado", "vl_consumido", "perc_consumo"])
                    for r in rows:
                        w.writerow([r["pregao"],
                                    f'{r["vl_empenhado"]:.2f}'.replace(".", ","),
                                    f'{r["vl_consumido"]:.2f}'.replace(".", ","),
                                    f'{r["perc_consumo"]:.1f}%'])
            except Exception:
                c1 = None

        # CSV 2: ranking global
        c2 = os.path.join(pasta_tmp, "indicadores_ranking_fornecedores.csv")
        try:
            rows = banco.ranking_fornecedores_consumo(self.data_ini, self.data_fim, limit=100)
            with open(c2, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["fornecedor", "valor_consumido"])
                for r in rows:
                    w.writerow([r["fornecedor_nome"], f'{float(r["valor_consumido"] or 0):.2f}'.replace(".", ",")])
        except Exception:
            c2 = None

        msg = "Arquivos gerados em %TEMP%:\n"
        if self.fornecedor_id and c1:
            msg += f" - {c1}\n"
        if c2:
            msg += f" - {c2}\n"
        messagebox.showinfo("Exportação", msg)

    def _fmt_brl(self, v: float) -> str:
        s = f"{float(v or 0):,.2f}"
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
