# telas/tela_inicial.py
import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any

from auth import auth_init, usuario_login, usuario_registrar
from banco import criar_tabelas

logger = logging.getLogger(__name__)

APP_NAME = "SICONAE"
TITULO = "Sistema de Controle de Atas e Empenhos"
CAMINHO_LOGO = None  # Ex.: "assets/logo.png"

# Cores
PRIMARY = "#0d3758"
PRIMARY_HOVER = "#12476f"
PRIMARY_TEXT = "#ffffff"
OUTLINE_TEXT = "#0d3758"
BG_TOP = "#cfe9ff"
BG_MID = "#e8f4ff"
BG_BOTTOM = "#f6fbff"


class TelaInicial:
    """Tela de login/registro - renderizada no root."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.canvas = None
        self._referencias = {}  # Mantém referências de imagens

    def render(self):
        """Desenha a tela inicial."""
        self.root.title(APP_NAME)
        self.root.geometry("920x540")
        self.root.minsize(760, 460)
        self._estilizar()
        
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.root.bind("<Configure>", self._redesenhar)
        self.root.after(30, lambda: self._redesenhar(None))
        
        logger.info("Tela inicial renderizada")

    def _estilizar(self):
        """Configura estilos de botões."""
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except:
            pass
        
        style.configure("Primary.TButton", 
                       font=("Segoe UI Semibold", 20),
                       background=PRIMARY, 
                       foreground=PRIMARY_TEXT,
                       padding=(32, 12), 
                       borderwidth=0, 
                       relief="flat")
        style.map("Primary.TButton", 
                 background=[("active", PRIMARY_HOVER)])
        
        style.configure("Outline.TButton", 
                       font=("Segoe UI Semibold", 12),
                       background="white", 
                       foreground=OUTLINE_TEXT,
                       padding=(22, 8), 
                       borderwidth=2, 
                       relief="solid")
        style.map("Outline.TButton", 
                 background=[("active", "#f2f7ff")])

    def _redesenhar(self, _evt):
        """Redesenha o canvas quando a janela é redimensionada."""
        if not self.canvas:
            return
        
        self.canvas.delete("all")
        w, h = self.root.winfo_width(), self.root.winfo_height()
        cx = w // 2
        
        self._desenhar_gradiente(w, h)
        
        # Título
        self.canvas.create_text(cx, 70, text=TITULO, 
                               font=("Segoe UI Semibold", 20), 
                               fill="#113a5e")
        self.canvas.create_text(cx, 108, text=APP_NAME, 
                               font=("Segoe UI", 12), 
                               fill="#1f4c77")
        
        # Logo placeholder
        y_logo = 150
        self.canvas.create_oval(cx-34, y_logo-34, cx+34, y_logo+34, 
                               outline="#0d3758", width=3)
        
        # Botão LOGIN
        btn_login = ttk.Button(self.root, text="LOGIN", 
                              style="Primary.TButton",
                              command=self._abrir_modal_login)
        self.canvas.create_window(cx, y_logo+96, window=btn_login, anchor="center")
        
        # Botão REGISTRO
        btn_reg = ttk.Button(self.root, text="REGISTRO / CADASTRO", 
                            style="Outline.TButton",
                            command=self._abrir_modal_registro)
        self.canvas.create_window(cx, y_logo+150, window=btn_reg, anchor="center")
        
        # Rodapé
        self.canvas.create_rectangle(0, h-40, w, h, fill="#0b2f4a", width=0)

    def _desenhar_gradiente(self, w: int, h: int):
        """Desenha gradiente de fundo no canvas."""
        def hex_to_rgb(hx):
            return tuple(int(hx[i:i+2], 16) for i in (1, 3, 5))
        
        t = hex_to_rgb(BG_TOP)
        m = hex_to_rgb(BG_MID)
        b = hex_to_rgb(BG_BOTTOM)
        
        for y in range(h):
            ratio = y / (h - 1) if h > 1 else 0
            if ratio <= 0.5:
                r2 = ratio / 0.5
                rgb = tuple(int(t[i] + (m[i] - t[i]) * r2) for i in range(3))
            else:
                r2 = (ratio - 0.5) / 0.5
                rgb = tuple(int(m[i] + (b[i] - m[i]) * r2) for i in range(3))
            self.canvas.create_line(0, y, w, y, fill="#%02x%02x%02x" % rgb)

    def _abrir_modal_login(self):
        """Abre modal de login."""
        modal = tk.Toplevel(self.root)
        modal.title("Login - SICONAE")
        modal.transient(self.root)
        modal.grab_set()
        modal.resizable(False, False)
        modal.geometry("400x300")
        
        frm = ttk.Frame(modal, padding=20)
        frm.pack(fill="both", expand=True)
        
        ttk.Label(frm, text="E-mail EBSERH", font=("Segoe UI", 10)).pack(anchor="w")
        ent_email = ttk.Entry(frm, width=40)
        ent_email.pack(pady=(0, 8), fill="x")
        
        ttk.Label(frm, text="Senha", font=("Segoe UI", 10)).pack(anchor="w")
        ent_senha = ttk.Entry(frm, width=40, show="•")
        ent_senha.pack(pady=(0, 12), fill="x")
        
        def do_login():
            email = ent_email.get().strip()
            senha = ent_senha.get()
            
            if not email or not senha:
                messagebox.showwarning("Atenção", "Preencha e-mail e senha.")
                return
            
            try:
                auth = usuario_login(email, senha)
                modal.grab_release()
                modal.destroy()
                self._entrar_no_sistema(auth)
            except Exception as e:
                messagebox.showerror("Erro no login", str(e))
                ent_senha.delete(0, tk.END)
                ent_senha.focus_set()
        
        ttk.Button(frm, text="Entrar", style="Primary.TButton", 
                  command=do_login).pack(fill="x")
        
        def on_close():
            try:
                modal.grab_release()
            except:
                pass
            modal.destroy()
        
        modal.protocol("WM_DELETE_WINDOW", on_close)
        modal.after(100, lambda: ent_email.focus_set())

    def _abrir_modal_registro(self):
        """Abre modal de registro."""
        modal = tk.Toplevel(self.root)
        modal.title("Registro / Cadastro - SICONAE")
        modal.transient(self.root)
        modal.grab_set()
        modal.resizable(False, False)
        modal.geometry("400x380")
        
        frm = ttk.Frame(modal, padding=20)
        frm.pack(fill="both", expand=True)
        
        campos = [
            ("Nome", "ent_nome", False),
            ("E-mail EBSERH (@ebserh.gov.br)", "ent_email", False),
            ("Senha (mín. 10 caracteres)", "ent_senha", True),
            ("Confirmar Senha", "ent_conf", True)
        ]
        
        entries = {}
        for label, name, is_password in campos:
            ttk.Label(frm, text=label, font=("Segoe UI", 10)).pack(anchor="w")
            ent = ttk.Entry(frm, width=40, show="•" if is_password else "")
            ent.pack(pady=(0, 8), fill="x")
            entries[name] = ent
        
        def do_registrar():
            nome = entries["ent_nome"].get().strip()
            email = entries["ent_email"].get().strip()
            s1 = entries["ent_senha"].get()
            s2 = entries["ent_conf"].get()
            
            if s1 != s2:
                messagebox.showerror("Erro", "As senhas não coincidem.")
                return
            
            if len(s1) < 10:
                messagebox.showwarning("Senha fraca", "Use pelo menos 10 caracteres.")
                return
            
            try:
                usuario_registrar(email, s1, nome or None)
                messagebox.showinfo("Sucesso", "Usuário criado. Faça login.")
                modal.grab_release()
                modal.destroy()
            except Exception as e:
                messagebox.showerror("Erro no registro", str(e))
        
        ttk.Button(frm, text="Registrar", style="Primary.TButton", 
                  command=do_registrar).pack(fill="x", pady=(10, 0))
        
        def on_close():
            try:
                modal.grab_release()
            except:
                pass
            modal.destroy()
        
        modal.protocol("WM_DELETE_WINDOW", on_close)
        modal.after(100, lambda: entries["ent_nome"].focus_set())

    def _entrar_no_sistema(self, auth: Dict[str, Any]):
        """Limpa a tela inicial e carrega o sistema principal."""
        logger.info("Login bem-sucedido. Carregando sistema principal...")
        
        # Remove todos os widgets da janela root
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Limpa referências do canvas
        self.canvas = None
        self._referencias.clear()
        
        # Instancia o sistema principal diretamente no root
        from telas.sistema import SistemaApp
        SistemaApp(self.root, auth)


def tela_inicial():
    """Ponto de entrada da aplicação."""
    try:
        criar_tabelas()
    except Exception as e:
        logger.warning(f"Aviso ao criar tabelas: {e}")
    
    auth_init()
    
    if not os.environ.get("APP_PEPPER"):
        print("⚠️ AVISO: defina APP_PEPPER para fortalecer hash de senhas.")
    
    root = tk.Tk()
    TelaInicial(root).render()
    root.mainloop()


if __name__ == "__main__":
    logging.basicConfig(
        filename='siconae.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    tela_inicial()
