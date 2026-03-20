# tela_inicial.py
import os
import socket
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, Dict, Any

# Integração com auth/banco
from auth import auth_init, usuario_login, usuario_registrar, usuario_por_token, usuario_logout, seed_admin_se_nao_existir
from bd import criar_tabelas  # se quiser garantir seu schema antigo antes de tudo (opcional)

APP_NAME = "SICONAE"
TITULO = "Sistema de Controle de Atas e Empenhos"

# Se tiver um logo PNG, informe o caminho aqui (ou deixe None)
CAMINHO_LOGO = None  # exemplo: r"C:\caminho\logo.png"

# =========================
#   UI Helpers
# =========================
PRIMARY = "#0d3758"      # azul escuro do botão LOGIN
PRIMARY_HOVER = "#12476f"
PRIMARY_TEXT = "#ffffff"
OUTLINE_TEXT = "#0d3758"
BG_TOP = "#cfe9ff"
BG_MID = "#e8f4ff"
BG_BOTTOM = "#f6fbff"

def desenhar_gradiente(canvas: tk.Canvas, w: int, h: int, top: str, mid: str, bottom: str) -> None:
    """Gradiente vertical simples (sem dependências externas)."""
    # Interpola top -> mid -> bottom
    def hex_to_rgb(hx): return tuple(int(hx[i:i+2], 16) for i in (1,3,5))
    t = hex_to_rgb(top); m = hex_to_rgb(mid); b = hex_to_rgb(bottom)
    steps = h
    for y in range(h):
        ratio = y / (h-1) if h > 1 else 0
        # duas faixas: 0-0.5 (top->mid), 0.5-1.0 (mid->bottom)
        if ratio <= 0.5:
            r2 = ratio / 0.5
            rgb = tuple(int(t[i] + (m[i]-t[i]) * r2) for i in range(3))
        else:
            r2 = (ratio - 0.5) / 0.5
            rgb = tuple(int(m[i] + (b[i]-m[i]) * r2) for i in range(3))
        color = "#%02x%02x%02x" % rgb
        canvas.create_line(0, y, w, y, fill=color)

def estilizar_ttk(root: tk.Tk) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Botão primário (LOGIN)
    style.configure("Primary.TButton",
                    font=("Segoe UI Semibold", 20),
                    background=PRIMARY,
                    foreground=PRIMARY_TEXT,
                    padding=(32, 12),
                    borderwidth=0,
                    relief="flat")
    style.map("Primary.TButton",
              background=[("active", PRIMARY_HOVER)],
              foreground=[("active", PRIMARY_TEXT)])

    # Botão outline (REGISTRO)
    style.configure("Outline.TButton",
                    font=("Segoe UI Semibold", 12),
                    background="white",
                    foreground=OUTLINE_TEXT,
                    padding=(22, 8),
                    borderwidth=2,
                    relief="solid")
    style.map("Outline.TButton",
              background=[("active", "#f2f7ff")],
              foreground=[("active", OUTLINE_TEXT)])

# =========================
#   Modais de Login/Cadastro
# =========================
def abrir_modal_login(root: tk.Tk):
    win = tk.Toplevel(root)
    win.title("Login - SICONAE")
    win.transient(root)
    win.grab_set()
    win.resizable(False, False)
    win.geometry("+%d+%d" % (root.winfo_rootx()+60, root.winfo_rooty()+80))

    frm = ttk.Frame(win, padding=16)
    frm.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frm, text="E-mail EBSERH", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=(0,4))
    ent_email = ttk.Entry(frm, width=38)
    ent_email.grid(row=1, column=0, sticky="ew", pady=(0,8))

    ttk.Label(frm, text="Senha", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=(0,4))
    ent_senha = ttk.Entry(frm, width=38, show="•")
    ent_senha.grid(row=3, column=0, sticky="ew", pady=(0,12))

    def do_login():
        email = ent_email.get().strip()
        senha = ent_senha.get()
        try:
            # user_agent/ip básicos
            ua = f"SICONAE-Desktop/{os.name}"
            ip = socket.gethostbyname(socket.gethostname())
            auth = usuario_login(email=email, senha=senha, user_agent=ua, ip=ip)
            messagebox.showinfo("Sucesso", f"Bem-vindo(a), {auth['usuario'].get('nome') or auth['usuario']['email']}")
            win.destroy()
            abrir_app_principal(root, auth)  # chama a tela principal do seu sistema
        except Exception as e:
            messagebox.showerror("Erro no login", str(e))

    btn = ttk.Button(frm, text="Entrar", style="Primary.TButton", command=do_login)
    btn.grid(row=4, column=0, pady=(4,0), sticky="ew")
    ent_email.focus_set()

def abrir_modal_registro(root: tk.Tk):
    win = tk.Toplevel(root)
    win.title("Registro / Cadastro - SICONAE")
    win.transient(root)
    win.grab_set()
    win.resizable(False, False)
    win.geometry("+%d+%d" % (root.winfo_rootx()+60, root.winfo_rooty()+80))

    frm = ttk.Frame(win, padding=16)
    frm.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frm, text="Nome", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
    ent_nome = ttk.Entry(frm, width=40)
    ent_nome.grid(row=1, column=0, sticky="ew", pady=(0,8))

    ttk.Label(frm, text="E-mail EBSERH (@ebserh.gov.br)", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")
    ent_email = ttk.Entry(frm, width=40)
    ent_email.grid(row=3, column=0, sticky="ew", pady=(0,8))

    ttk.Label(frm, text="Senha (mín. 10 caracteres)", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="w")
    ent_senha = ttk.Entry(frm, width=40, show="•")
    ent_senha.grid(row=5, column=0, sticky="ew", pady=(0,8))

    ttk.Label(frm, text="Confirmar Senha", font=("Segoe UI", 10)).grid(row=6, column=0, sticky="w")
    ent_conf = ttk.Entry(frm, width=40, show="•")
    ent_conf.grid(row=7, column=0, sticky="ew", pady=(0,12))

    def do_registrar():
        nome = ent_nome.get().strip() or None
        email = ent_email.get().strip()
        s1 = ent_senha.get()
        s2 = ent_conf.get()
        if s1 != s2:
            messagebox.showerror("Erro", "As senhas não coincidem.")
            return
        try:
            uid = usuario_registrar(email=email, senha=s1, nome=nome)
            messagebox.showinfo("Sucesso", "Usuário criado com sucesso. Faça login.")
            win.destroy()
        except Exception as e:
            messagebox.showerror("Erro no registro", str(e))

    btn = ttk.Button(frm, text="Registrar", style="Primary.TButton", command=do_registrar)
    btn.grid(row=8, column=0, sticky="ew")

    ent_nome.focus_set()

# =========================
#   Tela Principal (placeholder)
# =========================
def abrir_app_principal(root: tk.Tk, auth: Dict[str, Any]) -> None:
    """
    Troque este placeholder pela abertura da SUA janela principal do sistema.
    Você recebe 'auth' com {'token', 'usuario': {...}}.
    """
    win = tk.Toplevel(root)
    win.title("SICONAE - Principal")
    win.geometry("720x480")
    ttk.Label(win, text=f"Olá, {auth['usuario'].get('nome') or auth['usuario']['email']}",
              font=("Segoe UI", 12)).pack(pady=12)
    ttk.Label(win, text="(Substituir por sua tela principal)").pack()

# =========================
#   Tela Inicial
# =========================
def tela_inicial():
    # Schema do seu sistema e auth
    try:
        criar_tabelas()  # opcional: se quiser garantir seu schema geral antes
    except Exception:
        pass
    auth_init()

    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("900x520")
    root.minsize(760, 460)

    estilizar_ttk(root)

    # Canvas de fundo com gradiente
    canvas = tk.Canvas(root, highlightthickness=0, bd=0)
    canvas.pack(fill="both", expand=True)

    def on_resize(event=None):
        canvas.delete("all")
        w = root.winfo_width()
        h = root.winfo_height()
        desenhar_gradiente(canvas, w, h, BG_TOP, BG_MID, BG_BOTTOM)

        # Centro
        center_x = w//2

        # Título
        canvas.create_text(center_x, 70, text=TITULO, font=("Segoe UI Semibold", 20), fill="#113a5e")
        # Subtítulo SICONAE
        canvas.create_text(center_x, 108, text=APP_NAME, font=("Segoe UI", 12), fill="#1f4c77")

        y_logo = 150
        # Logo (opcional)
        if CAMINHO_LOGO and os.path.exists(CAMINHO_LOGO):
            try:
                # Usando PhotoImage nativo (GIF/PNG). Sem redimensionamento.
                logo = tk.PhotoImage(file=CAMINHO_LOGO)
                # manter referência
                canvas.image = logo
                canvas.create_image(center_x, y_logo, image=logo)
            except Exception:
                # fallback: desenho simples
                canvas.create_rectangle(center_x-30, y_logo-30, center_x+30, y_logo+30, outline="#0d3758")
        else:
            # Marca simples (hexágono estilizado)
            r = 34
            canvas.create_oval(center_x-r, y_logo-r, center_x+r, y_logo+r, outline="#0d3758", width=3)

        # Container invisível para botões (usaremos janela do canvas)
        # LOGIN (primário)
        btn_login = ttk.Button(root, text="LOGIN", style="Primary.TButton",
                               command=lambda: abrir_modal_login(root))
        canvas.create_window(center_x, y_logo+96, window=btn_login, anchor="center")

        # REGISTRO (outline)
        btn_reg = ttk.Button(root, text="REGISTRO / CADASTRO", style="Outline.TButton",
                             command=lambda: abrir_modal_registro(root))
        canvas.create_window(center_x, y_logo+150, window=btn_reg, anchor="center")

        # Faixa inferior (barra azul mais escura sutil)
        canvas.create_rectangle(0, h-48, w, h, fill="#0b2f4a", width=0)

    root.bind("<Configure>", on_resize)
    root.after(50, on_resize)

    # Seed opcional de admin, execute 1x se ainda não existir
    # try:
    #     seed_admin_se_nao_existir("admin@ebserh.gov.br", "Admin#MuitoForte-2026")
    # except Exception:
    #     pass

    root.mainloop()

if __name__ == "__main__":
    # Aviso de pepper ausente (não bloqueia execução, apenas alerta)
    if not os.environ.get("APP_PEPPER"):
        print("AVISO: APP_PEPPER não definido. Defina um pepper de servidor para fortalecer o hash de senhas.")
    tela_inicial()
