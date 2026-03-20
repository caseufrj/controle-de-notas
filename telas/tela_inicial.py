# telas/tela_inicial.py
import os, socket
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional

# Integração
from auth import auth_init, usuario_login, usuario_registrar
from banco import criar_tabelas  # seu schema principal

APP_NAME = "SICONAE"
TITULO = "Sistema de Controle de Atas e Empenhos"
CAMINHO_LOGO = None  # defina caminho PNG se quiser mostrar logo (ex.: "assets/logo.png")

PRIMARY = "#0d3758"
PRIMARY_HOVER = "#12476f"
PRIMARY_TEXT = "#ffffff"
OUTLINE_TEXT = "#0d3758"
BG_TOP = "#cfe9ff"
BG_MID = "#e8f4ff"
BG_BOTTOM = "#f6fbff"

def desenhar_gradiente(canvas: tk.Canvas, w: int, h: int, top: str, mid: str, bottom: str) -> None:
    def hex_to_rgb(hx): return tuple(int(hx[i:i+2], 16) for i in (1,3,5))
    t = hex_to_rgb(top); m = hex_to_rgb(mid); b = hex_to_rgb(bottom)
    for y in range(h):
        ratio = y/(h-1) if h>1 else 0
        if ratio <= 0.5:
            r2 = ratio/0.5; rgb = tuple(int(t[i] + (m[i]-t[i])*r2) for i in range(3))
        else:
            r2 = (ratio-0.5)/0.5; rgb = tuple(int(m[i] + (b[i]-m[i])*r2) for i in range(3))
        canvas.create_line(0, y, w, y, fill="#%02x%02x%02x" % rgb)

def estilizar(root: tk.Tk):
    st = ttk.Style(root)
    try: st.theme_use("clam")
    except tk.TclError: pass
    st.configure("Primary.TButton", font=("Segoe UI Semibold", 20),
                 background=PRIMARY, foreground=PRIMARY_TEXT,
                 padding=(32,12), borderwidth=0, relief="flat")
    st.map("Primary.TButton", background=[("active", PRIMARY_HOVER)])
    st.configure("Outline.TButton", font=("Segoe UI Semibold", 12),
                 background="white", foreground=OUTLINE_TEXT,
                 padding=(22,8), borderwidth=2, relief="solid")
    st.map("Outline.TButton", background=[("active", "#f2f7ff")])

def abrir_modal_login(root: tk.Tk, on_success):
    win = tk.Toplevel(root); win.title("Login - SICONAE")
    win.transient(root); win.grab_set(); win.resizable(False, False)
    frm = ttk.Frame(win, padding=16); frm.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frm, text="E-mail EBSERH", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
    ent_email = ttk.Entry(frm, width=40); ent_email.grid(row=1, column=0, sticky="ew", pady=(0,8))
    ttk.Label(frm, text="Senha", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")
    ent_senha = ttk.Entry(frm, width=40, show="•"); ent_senha.grid(row=3, column=0, sticky="ew", pady=(0,12))

    def do_login():
        try:
            ua = f"SICONAE-Desktop/{os.name}"
            ip = socket.gethostbyname(socket.gethostname())
            auth = usuario_login(ent_email.get().strip(), ent_senha.get(), ua, ip)
            messagebox.showinfo("Sucesso", f"Bem-vindo(a), {auth['usuario'].get('nome') or auth['usuario']['email']}")
            win.destroy()
            on_success(auth)
        except Exception as e:
            messagebox.showerror("Erro no login", str(e))

    ttk.Button(frm, text="Entrar", style="Primary.TButton", command=do_login).grid(row=4, column=0, sticky="ew")
    ent_email.focus_set()

def abrir_modal_registro(root: tk.Tk):
    win = tk.Toplevel(root); win.title("Registro / Cadastro - SICONAE")
    win.transient(root); win.grab_set(); win.resizable(False, False)
    frm = ttk.Frame(win, padding=16); frm.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frm, text="Nome", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
    ent_nome = ttk.Entry(frm, width=40); ent_nome.grid(row=1, column=0, sticky="ew", pady=(0,8))
    ttk.Label(frm, text="E-mail EBSERH (@ebserh.gov.br)", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")
    ent_email = ttk.Entry(frm, width=40); ent_email.grid(row=3, column=0, sticky="ew", pady=(0,8))
    ttk.Label(frm, text="Senha (mín. 10 caracteres)", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="w")
    ent_senha = ttk.Entry(frm, width=40, show="•"); ent_senha.grid(row=5, column=0, sticky="ew", pady=(0,8))
    ttk.Label(frm, text="Confirmar Senha", font=("Segoe UI", 10)).grid(row=6, column=0, sticky="w")
    ent_conf = ttk.Entry(frm, width=40, show="•"); ent_conf.grid(row=7, column=0, sticky="ew", pady=(0,12))

    def do_registrar():
        s1, s2 = ent_senha.get(), ent_conf.get()
        if s1 != s2:
            messagebox.showerror("Erro", "As senhas não coincidem."); return
        try:
            usuario_registrar(ent_email.get().strip(), s1, ent_nome.get().strip() or None)
            messagebox.showinfo("Sucesso", "Usuário criado. Faça login.")
            win.destroy()
        except Exception as e:
            messagebox.showerror("Erro no registro", str(e))

    ttk.Button(frm, text="Registrar", style="Primary.TButton", command=do_registrar).grid(row=8, column=0, sticky="ew")
    ent_nome.focus_set()

# dentro de telas/tela_inicial.py
from telas.sistema import SistemaWindow  # novo import

def abrir_app_principal(root: tk.Tk, auth: Dict[str, Any]) -> None:
    SistemaWindow(root, auth)
    # fecha a janela inicial para ficar só a principal
    root.withdraw()  # oculta a Tela Inicial
    # ou root.destroy()  # encerra o Tk (apenas se SistemaWindow for Tk independente → não é o caso aqui)
    
def tela_inicial():
    try: criar_tabelas()
    except Exception: pass
    auth_init()

    root = tk.Tk(); root.title(APP_NAME); root.geometry("920x540"); root.minsize(760, 460)
    estilizar(root)

    canvas = tk.Canvas(root, highlightthickness=0, bd=0); canvas.pack(fill="both", expand=True)

    def render(_evt=None):
        canvas.delete("all")
        w, h = root.winfo_width(), root.winfo_height()
        desenhar_gradiente(canvas, w, h, BG_TOP, BG_MID, BG_BOTTOM)
        cx = w//2

        canvas.create_text(cx, 70, text=TITULO, font=("Segoe UI Semibold", 20), fill="#113a5e")
        canvas.create_text(cx, 108, text=APP_NAME, font=("Segoe UI", 12), fill="#1f4c77")

        y_logo = 150
        if CAMINHO_LOGO and os.path.exists(CAMINHO_LOGO):
            try:
                img = tk.PhotoImage(file=CAMINHO_LOGO)
                canvas.image = img
                canvas.create_image(cx, y_logo, image=img)
            except Exception:
                canvas.create_oval(cx-34, y_logo-34, cx+34, y_logo+34, outline="#0d3758", width=3)
        else:
            canvas.create_oval(cx-34, y_logo-34, cx+34, y_logo+34, outline="#0d3758", width=3)

        btn_login = ttk.Button(root, text="LOGIN", style="Primary.TButton",
                               command=lambda: abrir_modal_login(root, lambda a: abrir_app_principal(root, a)))
        canvas.create_window(cx, y_logo+96, window=btn_login, anchor="center")

        btn_reg = ttk.Button(root, text="REGISTRO / CADASTRO", style="Outline.TButton",
                             command=lambda: abrir_modal_registro(root))
        canvas.create_window(cx, y_logo+150, window=btn_reg, anchor="center")

        canvas.create_rectangle(0, h-48, w, h, fill="#0b2f4a", width=0)

    root.bind("<Configure>", render)
    root.after(30, render)
    root.mainloop()

if __name__ == "__main__":
    if not os.environ.get("APP_PEPPER"):
        print("AVISO: defina a variável de ambiente APP_PEPPER para fortalecer o hash de senhas.")
    tela_inicial()
