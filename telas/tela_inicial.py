# telas/tela_inicial.py
import os, socket, logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional, Callable

from auth import auth_init, usuario_login, usuario_registrar
from banco import criar_tabelas

# Imports das telas do sistema
from telas.dashboard import Dashboard
from telas.fornecedores import TelaFornecedores
from telas.atas_empenhos import TelaAtasEmpenhos
from telas.notas import TelaNotas
from telas.orcamento import TelaOrcamento
from telas.configuracoes import TelaConfiguracoes

APP_NAME = "SICONAE"
TITULO = "Sistema de Controle de Atas e Empenhos"
CAMINHO_LOGO = None

# Cores
PRIMARY = "#0d3758"
PRIMARY_HOVER = "#12476f"
PRIMARY_TEXT = "#ffffff"
OUTLINE_TEXT = "#0d3758"
BG_TOP = "#cfe9ff"
BG_MID = "#e8f4ff"
BG_BOTTOM = "#f6fbff"

# Logging
logging.basicConfig(filename='siconae.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def estilizar(root: tk.Tk):
    st = ttk.Style(root)
    try: st.theme_use("clam")
    except: pass
    st.configure("Primary.TButton", font=("Segoe UI Semibold", 20),
                 background=PRIMARY, foreground=PRIMARY_TEXT,
                 padding=(32,12), borderwidth=0, relief="flat")
    st.map("Primary.TButton", background=[("active", PRIMARY_HOVER)])
    st.configure("Outline.TButton", font=("Segoe UI Semibold", 12),
                 background="white", foreground=OUTLINE_TEXT,
                 padding=(22,8), borderwidth=2, relief="solid")

def desenhar_gradiente(canvas, w, h, top, mid, bottom):
    def hex_to_rgb(hx): return tuple(int(hx[i:i+2], 16) for i in (1,3,5))
    t, m, b = hex_to_rgb(top), hex_to_rgb(mid), hex_to_rgb(bottom)
    for y in range(h):
        ratio = y/(h-1) if h>1 else 0
        if ratio <= 0.5:
            r2 = ratio/0.5
            rgb = tuple(int(t[i] + (m[i]-t[i])*r2) for i in range(3))
        else:
            r2 = (ratio-0.5)/0.5
            rgb = tuple(int(m[i] + (b[i]-m[i])*r2) for i in range(3))
        canvas.create_line(0, y, w, y, fill="#%02x%02x%02x" % rgb)

class AppPrincipal:
    """Classe que gerencia o sistema principal DENTRO da mesma janela root."""
    
    def __init__(self, root: tk.Tk, auth: dict, build_tag: str = "build 2026-03-18"):
        self.root = root
        self.auth = auth
        self.build_tag = build_tag
        self.usuario = auth.get('usuario', {})
        
        self._configurar_janela()
        self._criar_menu_lateral()
        self._criar_area_trabalho()
        self._abrir_dashboard()
        
        logging.info(f"Sistema iniciado para usuário: {self.usuario.get('email')}")

    def _configurar_janela(self):
        self.root.title(f"{APP_NAME} - {self.usuario.get('nome', 'Usuário')}")
        self.root.geometry("1100x650")
        self.root.minsize(1000, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.sair)
        
        # Fonte global
        import tkinter.font as tkfont
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=10)
        self.root.option_add("*Font", default_font)

    def _criar_menu_lateral(self):
        menu = tk.Frame(self.root, width=200, bg="#2c3e50")
        menu.pack(side="left", fill="y")
        menu.pack_propagate(False)  # Mantém largura fixa

        def btn(text, cmd, bg="#34495e"):
            b = tk.Button(menu, text=text, command=cmd, bg=bg, fg="white",
                         bd=0, padx=12, pady=10, anchor="w",
                         activebackground="#3d566e", activeforeground="white",
                         font=("Segoe UI", 10))
            b.pack(fill="x", padx=2, pady=1)
            return b

        btn("📊 Dashboard", lambda: self._trocar_tela(Dashboard, "Dashboard"))
        btn("🏢 Fornecedores", lambda: self._trocar_tela(TelaFornecedores, "Fornecedores"))
        btn("📋 Ata / Empenho", lambda: self._trocar_tela(TelaAtasEmpenhos, "Ata/Empenho"))
        btn("🧾 Notas Fiscais", lambda: self._trocar_tela(TelaNotas, "Notas"))
        btn("💰 Orçamento", lambda: self._trocar_tela(TelaOrcamento, "Orçamento"))
        btn("⚙️ Configurações", lambda: self._trocar_tela(TelaConfiguracoes, "Configurações"))
        
        tk.Frame(menu, height=2, bg="#22313f").pack(fill="x", pady=8)
        btn("🚪 Sair", self.sair, bg="#8e2b2b")

    def _criar_area_trabalho(self):
        self.container = tk.Frame(self.root, bg="#ecf0f1")
        self.container.pack(side="right", expand=True, fill="both")

    def _trocar_tela(self, classe_tela, nome: str):
        """Limpa o container e carrega nova tela."""
        for widget in self.container.winfo_children():
            widget.destroy()
        try:
            tela = classe_tela(self.container)
            tela.pack(fill="both", expand=True)
            logging.debug(f"Tela carregada: {nome}")
        except Exception as e:
            logging.exception(f"Erro ao carregar {nome}")
            messagebox.showerror("Erro", f"Falha ao abrir {nome}:\n{e}")

    def _abrir_dashboard(self):
        self._trocar_tela(Dashboard, "Dashboard")

    def sair(self):
        """Logout e volta para tela inicial."""
        if not messagebox.askyesno("Sair", "Encerrar sessão e voltar ao login?"):
            return
        
        try:
            from auth import usuario_logout
            token = self.auth.get("token")
            if token:
                usuario_logout(token)
        except Exception as e:
            logging.warning(f"Erro no logout: {e}")
        
        logging.info("Sessão encerrada. Voltando ao login.")
        self._limpar_janela()
        TelaInicial(self.root).render()

    def _limpar_janela(self):
        """Remove todos os widgets da janela para retornar ao estado inicial."""
        for widget in self.root.winfo_children():
            widget.destroy()


class TelaInicial:
    """Tela de login/registro - renderizada no root."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.canvas = None

    def render(self):
        """Desenha a tela inicial."""
        self.root.title(APP_NAME)
        self.root.geometry("920x540")
        estilizar(self.root)
        
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.root.bind("<Configure>", self._redesenhar)
        self.root.after(30, lambda: self._redesenhar(None))
        
        logging.info("Tela inicial renderizada")

    def _redesenhar(self, _evt):
        if not self.canvas: return
        self.canvas.delete("all")
        w, h = self.root.winfo_width(), self.root.winfo_height()
        cx = w // 2
        
        desenhar_gradiente(self.canvas, w, h, BG_TOP, BG_MID, BG_BOTTOM)
        
        # Título
        self.canvas.create_text(cx, 70, text=TITULO, font=("Segoe UI Semibold", 20), fill="#113a5e")
        self.canvas.create_text(cx, 108, text=APP_NAME, font=("Segoe UI", 12), fill="#1f4c77")
        
        # Logo placeholder
        y_logo = 150
        self.canvas.create_oval(cx-34, y_logo-34, cx+34, y_logo+34, outline="#0d3758", width=3)
        
        # Botões
        btn_login = ttk.Button(self.root, text="LOGIN", style="Primary.TButton",
                              command=self._abrir_modal_login)
        self.canvas.create_window(cx, y_logo+96, window=btn_login, anchor="center")
        
        btn_reg = ttk.Button(self.root, text="REGISTRO / CADASTRO", style="Outline.TButton",
                            command=self._abrir_modal_registro)
        self.canvas.create_window(cx, y_logo+150, window=btn_reg, anchor="center")
        
        # Rodapé
        self.canvas.create_rectangle(0, h-40, w, h, fill="#0b2f4a", width=0)

    def _abrir_modal_login(self):
        modal = tk.Toplevel(self.root)
        modal.title("Login")
        modal.transient(self.root)
        modal.grab_set()
        modal.resizable(False, False)
        modal.geometry("400x300")
        
        frm = ttk.Frame(modal, padding=20)
        frm.pack(fill="both", expand=True)
        
        ttk.Label(frm, text="E-mail EBSERH").pack(anchor="w")
        ent_email = ttk.Entry(frm, width=40)
        ent_email.pack(pady=(0,8), fill="x")
        
        ttk.Label(frm, text="Senha").pack(anchor="w")
        ent_senha = ttk.Entry(frm, width=40, show="•")
        ent_senha.pack(pady=(0,12), fill="x")
        
        def do_login():
            email, senha = ent_email.get().strip(), ent_senha.get()
            if not email or not senha:
                messagebox.showwarning("Atenção", "Preencha todos os campos.")
                return
            try:
                auth = usuario_login(email, senha)  # 👈 Ajuste conforme sua API
                modal.grab_release()
                modal.destroy()
                self._entrar_no_sistema(auth)
            except Exception as e:
                messagebox.showerror("Erro", str(e))
                ent_senha.delete(0, tk.END)
        
        ttk.Button(frm, text="Entrar", style="Primary.TButton", command=do_login).pack(fill="x")
        modal.protocol("WM_DELETE_WINDOW", lambda: [modal.grab_release(), modal.destroy()])
        modal.after(100, lambda: ent_email.focus_set())

    def _abrir_modal_registro(self):
        modal = tk.Toplevel(self.root)
        modal.title("Registro")
        modal.transient(self.root)
        modal.grab_set()
        modal.resizable(False, False)
        modal.geometry("400x380")
        
        frm = ttk.Frame(modal, padding=20)
        frm.pack(fill="both", expand=True)
        
        campos = [
            ("Nome", "ent_nome"), ("E-mail EBSERH", "ent_email"),
            ("Senha (mín. 10)", "ent_senha"), ("Confirmar Senha", "ent_conf")
        ]
        entries = {}
        for label, name in campos:
            ttk.Label(frm, text=label).pack(anchor="w")
            show = "•" if "senha" in name.lower() else ""
            ent = ttk.Entry(frm, width=40, show=show)
            ent.pack(pady=(0,8), fill="x")
            entries[name] = ent
        
        def do_registro():
            nome = entries["ent_nome"].get().strip()
            email = entries["ent_email"].get().strip()
            s1, s2 = entries["ent_senha"].get(), entries["ent_conf"].get()
            
            if s1 != s2:
                messagebox.showerror("Erro", "Senhas não coincidem.")
                return
            if len(s1) < 10:
                messagebox.showwarning("Senha fraca", "Use pelo menos 10 caracteres.")
                return
                
            try:
                from auth import usuario_registrar
                usuario_registrar(email, s1, nome or None)
                messagebox.showinfo("Sucesso", "Cadastro realizado! Faça login.")
                modal.grab_release()
                modal.destroy()
            except Exception as e:
                messagebox.showerror("Erro", str(e))
        
        ttk.Button(frm, text="Registrar", style="Primary.TButton", command=do_registro).pack(fill="x", pady=(10,0))
        modal.protocol("WM_DELETE_WINDOW", lambda: [modal.grab_release(), modal.destroy()])
        modal.after(100, lambda: entries["ent_nome"].focus_set())

    def _entrar_no_sistema(self, auth: Dict[str, Any]):
        """Limpa a tela inicial e carrega o sistema principal NO MESMO root."""
        logging.info("Login bem-sucedido. Carregando sistema principal...")
        
        # Remove tudo da janela root
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Instancia o sistema principal diretamente no root
        AppPrincipal(self.root, auth)


def tela_inicial():
    """Ponto de entrada da aplicação."""
    try:
        criar_tabelas()
    except Exception as e:
        logging.warning(f"Aviso ao criar tabelas: {e}")
    
    auth_init()
    
    if not os.environ.get("APP_PEPPER"):
        print("⚠️ AVISO: defina APP_PEPPER para fortalecer hash de senhas.")
    
    root = tk.Tk()
    TelaInicial(root).render()
    root.mainloop()


if __name__ == "__main__":
    tela_inicial()
