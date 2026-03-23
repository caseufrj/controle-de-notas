# telas/sistema.py
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
import traceback

from auth import usuario_logout


class SistemaApp:
    """
    Monta o sistema (menu lateral + área de trabalho) DENTRO do root (única janela Tk).
    Use SistemaApp(root, auth, on_sair=callback) para montar; chame .desmontar() para remover.
    """
    def __init__(self, root: tk.Tk, auth: dict, on_sair):
        self.root = root
        self.auth = auth
        self.on_sair = on_sair  # callback para voltar à tela inicial

        # ---- Estilos / fonte padrão
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=10)
        self.root.option_add("*Font", default_font)

        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

        usuario_label = auth['usuario'].get('nome') or auth['usuario']['email']
        self.root.title(f"SICONAE — Controle de Notas e Empenhos — {usuario_label}")

        # ---- Estrutura base
        self.frame_root = tk.Frame(self.root, bg="#ecf0f1")
        self.frame_root.pack(fill="both", expand=True)

        self.menu = tk.Frame(self.frame_root, width=200, bg="#2c3e50")
        self.menu.pack(side="left", fill="y")

        self.container = tk.Frame(self.frame_root, bg="#ecf0f1")
        self.container.pack(side="right", expand=True, fill="both")

        # ---- Botões menu
        def btn(text, cmd, bg="#34495e"):
            b = tk.Button(
                self.menu, text=text, command=cmd,
                bg=bg, fg="white", bd=0, padx=12, pady=12,
                activebackground="#3d566e", activeforeground="white",
                anchor="w",
            )
            b.pack(fill="x")
            return b

        self.btn_dash = btn("Dashboard", self.abrir_dashboard)
        self.btn_forn = btn("Fornecedores", self.abrir_fornecedores)
        self.btn_atas = btn("Ata / Empenho", self.abrir_atas_empenhos)
        self.btn_notas = btn("Notas Fiscais", self.abrir_notas)
        self.btn_orc  = btn("Orçamento", self.abrir_orcamento)
        self.btn_conf = btn("Configurações", self.abrir_configuracoes)

        tk.Frame(self.menu, height=1, bg="#22313f").pack(fill="x", pady=6)
        self.btn_sair = btn("Sair", self.sair, bg="#8e2b2b")

        # Primeira tela
        self.abrir_dashboard()

        # Fechar no X = encerrar COMPLETAMENTE o app
        self.root.protocol("WM_DELETE_WINDOW", self._encerrar_app_total)
        # Alt+F4 (Windows) também deve fechar completamente
        self.root.bind_all("<Alt-F4>", lambda e: self._encerrar_app_total())

    # -------- util --------
    def desmontar(self):
        """Remove todos os widgets do sistema da janela."""
        try:
            self.frame_root.destroy()
        except Exception:
            pass

    def limpar_container(self):
        for w in self.container.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

    def _abrir_tela(self, classe_tela, nome_log: str = "tela"):
        """
        Troca a tela atual pela classe informada.
        Antes de limpar, se a tela antiga tiver _on_close(), chamamos para ela
        cancelar timers/binds/Toplevels próprios.
        """
        # Hook de fechamento da tela antiga
        for w in list(self.container.winfo_children()):
            try:
                if hasattr(w, "_on_close"):
                    w._on_close()
            except Exception:
                # não deixe a troca de tela quebrar por erro no hook
                pass

        # Limpa e cria a nova
        self.limpar_container()
        try:
            tela = classe_tela(self.container)
            tela.pack(fill="both", expand=True)
        except Exception as e:
            # Log amigável + MessageBox
            log_path = os.path.join(os.path.expanduser("~"), "controle_notas_erro.log")
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write("\n" + "=" * 80 + "\n")
                    f.write(f"Erro ao abrir {nome_log}:\n")
                    f.write(traceback.format_exc())
            except Exception:
                pass
            messagebox.showerror(
                "Erro",
                f"Ocorreu um erro ao abrir a tela '{nome_log}'.\n\n"
                f"{e}\n\n"
                f"Um log foi salvo em:\n{log_path}"
            )

    # -------- telas --------
    def abrir_dashboard(self):
        from telas.dashboard import Dashboard
        self._abrir_tela(Dashboard, "Dashboard")

    def abrir_fornecedores(self):
        from telas.fornecedores import TelaFornecedores
        self._abrir_tela(TelaFornecedores, "Fornecedores")

    def abrir_atas_empenhos(self):
        from telas.atas_empenhos import TelaAtasEmpenhos
        self._abrir_tela(TelaAtasEmpenhos, "Ata/Empenho")

    def abrir_notas(self):
        from telas.notas import TelaNotas
        self._abrir_tela(TelaNotas, "Notas")

    def abrir_orcamento(self):
        from telas.orcamento import TelaOrcamento
        self._abrir_tela(TelaOrcamento, "Orçamento")

    def abrir_configuracoes(self):
        from telas.configuracoes import TelaConfiguracoes
        self._abrir_tela(TelaConfiguracoes, "Configurações")

    # -------- sair / logout --------
    def sair(self):
        if not messagebox.askyesno("Sair", "Deseja realmente sair e encerrar a sessão?"):
            return
        try:
            token = (self.auth or {}).get("token")
            if token:
                usuario_logout(token)
        except Exception:
            pass

        # desmonta o sistema e chama callback da tela inicial
        self.desmontar()
        try:
            if hasattr(self.root, "_sistema"):
                self.root._sistema = None
        except Exception:
            pass

        if callable(self.on_sair):
            self.on_sair(self.root)

    def _encerrar_app_total(self):
        """Fecha todo o aplicativo ao clicar no X."""
        try:
            # tente encerrar sessão se existir token (não bloqueia se falhar)
            try:
                token = (self.auth or {}).get("token")
                if token:
                    usuario_logout(token)
            except Exception:
                pass
        finally:
            # sequência robusta de shutdown
            try:
                self.root.quit()  # encerra mainloop (se ativo)
            except Exception:
                pass
            try:
                self.root.update_idletasks()
            except Exception:
                pass
            try:
                self.root.destroy()  # destrói a janela raiz
            except Exception:
                pass
            # fallback: garante fim do processo
            try:
                sys.exit(0)
            except Exception:
                try:
                    os._exit(0)
                except Exception:
                    pass
