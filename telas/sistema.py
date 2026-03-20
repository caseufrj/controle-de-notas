# telas/sistema.py
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont

from auth import usuario_logout

logger = logging.getLogger(__name__)


class SistemaApp:
    """
    Sistema principal da aplicação.
    Gerencia menu lateral e área de trabalho DENTRO da mesma janela root.
    """
    
    def __init__(self, root: tk.Tk, auth: dict, build_tag: str = "build 2026-03-18"):
        self.root = root
        self.auth = auth
        self.build_tag = build_tag
        self.usuario = auth.get('usuario', {})
        self.container = None  # Será criado em _criar_interface()
        
        self._setup_estilos()
        self._setup_janela()
        self._criar_interface()
        self._carregar_dashboard()
        
        logger.info(f"Sistema iniciado para: {self.usuario.get('email')}")

    def _setup_estilos(self):
        """Configura fontes e temas globais."""
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=10)
        self.root.option_add("*Font", default_font)
        
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

    def _setup_janela(self):
        """Configura propriedades da janela principal."""
        nome_usuario = self.usuario.get('nome') or self.usuario.get('email', 'Usuário')
        self.root.title(f"Controle de Atas e Empenhos — {nome_usuario}")
        self.root.geometry("1100x650")
        self.root.minsize(1000, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.sair)

    def _criar_interface(self):
        """Cria menu lateral e área de trabalho."""
        # === MENU LATERAL ===
        self.menu_frame = tk.Frame(self.root, width=200, bg="#2c3e50")
        self.menu_frame.pack(side="left", fill="y")
        self.menu_frame.pack_propagate(False)
        
        self._criar_botao_menu("📊 Dashboard", self._carregar_dashboard)
        self._criar_botao_menu("🏢 Fornecedores", self._carregar_fornecedores)
        self._criar_botao_menu("📋 Ata / Empenho", self._carregar_atas_empenhos)
        self._criar_botao_menu("🧾 Notas Fiscais", self._carregar_notas)
        self._criar_botao_menu("💰 Orçamento", self._carregar_orcamento)
        self._criar_botao_menu("⚙️ Configurações", self._carregar_configuracoes)
        
        # Separador
        tk.Frame(self.menu_frame, height=2, bg="#22313f").pack(fill="x", pady=8)
        
        # Botão Sair
        self._criar_botao_menu("🚪 Sair", self.sair, bg="#8e2b2b", hover="#a33535")
        
        # === ÁREA DE TRABALHO ===
        self.container = tk.Frame(self.root, bg="#ecf0f1")
        self.container.pack(side="right", expand=True, fill="both")

    def _criar_botao_menu(self, texto: str, comando, bg="#34495e", hover="#3d566e"):
        """Cria botão estilizado para o menu lateral."""
        btn = tk.Button(
            self.menu_frame, text=texto, command=comando,
            bg=bg, fg="white", bd=0, padx=12, pady=10,
            activebackground=hover, activeforeground="white",
            anchor="w", font=("Segoe UI", 10)
        )
        btn.pack(fill="x", padx=2, pady=1)
        return btn

    def _limpar_container(self):
        """Remove todos os widgets da área de trabalho."""
        for widget in self.container.winfo_children():
            widget.destroy()

    def _carregar_tela(self, classe_tela, nome: str):
        """Limpa o container e instancia uma nova tela."""
        self._limpar_container()
        try:
            tela = classe_tela(self.container)
            tela.pack(fill="both", expand=True)
            logger.debug(f"Tela carregada: {nome}")
        except Exception as e:
            logger.exception(f"Erro ao carregar {nome}")
            messagebox.showerror("Erro", f"Falha ao abrir {nome}:\n{e}")

    def _carregar_dashboard(self):
        from telas.dashboard import Dashboard
        self._carregar_tela(Dashboard, "Dashboard")

    def _carregar_fornecedores(self):
        from telas.fornecedores import TelaFornecedores
        self._carregar_tela(TelaFornecedores, "Fornecedores")

    def _carregar_atas_empenhos(self):
        from telas.atas_empenhos import TelaAtasEmpenhos
        self._carregar_tela(TelaAtasEmpenhos, "Ata/Empenho")

    def _carregar_notas(self):
        from telas.notas import TelaNotas
        self._carregar_tela(TelaNotas, "Notas")

    def _carregar_orcamento(self):
        from telas.orcamento import TelaOrcamento
        self._carregar_tela(TelaOrcamento, "Orçamento")

    def _carregar_configuracoes(self):
        from telas.configuracoes import TelaConfiguracoes
        self._carregar_tela(TelaConfiguracoes, "Configurações")

    def sair(self):
        """Logout e volta para tela inicial."""
        if not messagebox.askyesno("Sair", "Encerrar sessão e voltar ao login?"):
            return
        
        try:
            token = self.auth.get("token")
            if token:
                usuario_logout(token)
        except Exception as e:
            logger.warning(f"Erro no logout: {e}")
        
        logger.info("Sessão encerrada. Voltando ao login.")
        
        # Limpa toda a janela e chama a tela inicial
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Importa e renderiza a tela inicial
        from telas.tela_inicial import TelaInicial
        TelaInicial(self.root).render()
