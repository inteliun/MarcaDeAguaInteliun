# Marca de Agua Inteliun — Software propietario
# Copyright (c) 2026 Inteliun. Todos los derechos reservados.
# Uso sujeto a LICENSE.txt. No redistribuir ni modificar sin autorización.

"""
Marca de agua para PDF (texto, imagen o ambos a la vez) con interfaz gráfica.

Instalación:
    pip install pypdf reportlab

Uso:
    python marca_de_agua_pdf.py
"""

import io
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

# ==========================
# FUENTE (soporta acentos y ñ)
# ==========================

FONT = "Helvetica"
for _name, _path in [
    ("ArialWM", "C:/Windows/Fonts/arial.ttf"),
    ("ArialWM", "/Library/Fonts/Arial.ttf"),
    ("ArialWM", "/System/Library/Fonts/Supplemental/Arial.ttf"),
    ("ArialWM", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]:
    if os.path.exists(_path):
        try:
            pdfmetrics.registerFont(TTFont(_name, _path))
            FONT = _name
            break
        except Exception:
            pass


# ==========================
# LÓGICA
# ==========================

def crear_overlay(w, h, rotacion_pagina, cfg):
    """Devuelve un PDF (en memoria) de una página con la marca de agua.
    Si hay imagen y texto a la vez, la imagen va arriba y el texto debajo."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setFillAlpha(cfg["opacidad"])

    # Si la página tiene /Rotate, compensamos para que la marca salga derecha
    angulo = cfg["angulo"] + rotacion_pagina
    hueco = 10

    img = None
    iw = ih = tw = th = 0
    if cfg["usar_imagen"]:
        img = ImageReader(cfg["imagen"])
        ow, oh = img.getSize()
        esc = (min(w, h) * cfg["escala"] / 100) / max(ow, oh)
        iw, ih = ow * esc, oh * esc
    if cfg["usar_texto"]:
        r, g, b = cfg["color"]
        c.setFillColorRGB(r / 255, g / 255, b / 255)
        c.setFont(FONT, cfg["tamano"])
        tw = pdfmetrics.stringWidth(cfg["texto"], FONT, cfg["tamano"])
        th = cfg["tamano"]

    ancho = max(iw, tw)
    alto = ih + th + (hueco if img and cfg["usar_texto"] else 0)

    def dibujar(cx, cy):
        c.saveState()
        c.translate(cx, cy)
        c.rotate(angulo)
        y = alto / 2
        if img:
            c.drawImage(img, -iw / 2, y - ih, iw, ih, mask="auto")
            y -= ih + hueco
        if cfg["usar_texto"]:
            c.setFont(FONT, cfg["tamano"])
            c.drawString(-tw / 2, y - th * 0.8, cfg["texto"])
        c.restoreState()

    if cfg["posicion"] == "Centro":
        dibujar(w / 2, h / 2)
    else:  # Mosaico
        sx = ancho * 1.6 + 40
        sy = max(alto, ancho * 0.35) * 2.2 + 40
        y, fila = -sy, 0
        while y < h + sy:
            x = -sx + (sx / 2 if fila % 2 else 0)
            while x < w + sx:
                dibujar(x, y)
                x += sx
            y += sy
            fila += 1

    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def marcar_pdf(entrada, salida, cfg):
    reader = PdfReader(entrada)
    if reader.is_encrypted:
        if not reader.decrypt(""):
            raise ValueError("El PDF está protegido con contraseña")

    writer = PdfWriter()
    for page in reader.pages:
        caja = page.mediabox
        w, h = float(caja.width), float(caja.height)
        overlay = crear_overlay(w, h, page.get("/Rotate", 0) or 0, cfg)
        if cfg["encima"]:
            page.merge_page(overlay)
        else:
            overlay.merge_page(page)
            page = overlay
        writer.add_page(page)

    with open(salida, "wb") as f:
        writer.write(f)


# ==========================
# INTERFAZ
# ==========================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Marca de agua para PDF")
        self.geometry("640x700")
        self.resizable(False, False)

        self.archivos = []
        self.color = (150, 150, 150)

        self.usar_texto = tk.BooleanVar(value=True)
        self.usar_imagen = tk.BooleanVar(value=False)
        self.texto = tk.StringVar(value="CONFIDENCIAL")
        self.tamano = tk.IntVar(value=60)
        self.imagen = tk.StringVar()
        self.escala = tk.IntVar(value=50)
        self.opacidad = tk.IntVar(value=30)
        self.angulo = tk.IntVar(value=45)
        self.posicion = tk.StringVar(value="Centro")
        self.encima = tk.BooleanVar(value=True)
        self.salida = tk.StringVar()

        self._ui()
        self._cambiar_modo()

    # ---- construcción ----
    def _ui(self):
        p = {"padx": 10, "pady": 5}

        # Archivos
        f = ttk.LabelFrame(self, text="1. PDFs")
        f.pack(fill="x", **p)
        self.lista = tk.Listbox(f, height=5)
        self.lista.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        b = ttk.Frame(f)
        b.pack(side="right", padx=5)
        ttk.Button(b, text="Añadir...", command=self._add).pack(fill="x", pady=2)
        ttk.Button(b, text="Quitar", command=self._quitar).pack(fill="x", pady=2)
        ttk.Button(b, text="Vaciar", command=self._vaciar).pack(fill="x", pady=2)

        # Tipo
        f = ttk.LabelFrame(self, text="2. Marca (puedes usar texto, imagen o los dos a la vez)")
        f.pack(fill="x", **p)
        ttk.Checkbutton(f, text="Texto", variable=self.usar_texto,
                        command=self._cambiar_modo).grid(row=0, column=0, padx=10, pady=5)
        ttk.Checkbutton(f, text="Imagen", variable=self.usar_imagen,
                        command=self._cambiar_modo).grid(row=0, column=1, padx=10, pady=5)

        # Texto
        self.f_texto = ttk.Frame(f)
        self.f_texto.grid(row=1, column=0, columnspan=4, sticky="we", padx=5, pady=3)
        ttk.Label(self.f_texto, text="Texto:").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.f_texto, textvariable=self.texto, width=38).grid(row=0, column=1, padx=5)
        ttk.Label(self.f_texto, text="Tamaño:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Spinbox(self.f_texto, from_=8, to=300, textvariable=self.tamano,
                    width=6).grid(row=1, column=1, sticky="w", padx=5)
        self.btn_color = tk.Button(self.f_texto, text="Color", width=8, bg=self._hex(),
                                   fg="white", command=self._elegir_color)
        self.btn_color.grid(row=1, column=1, sticky="e")

        # Imagen
        self.f_imagen = ttk.Frame(f)
        self.f_imagen.grid(row=2, column=0, columnspan=4, sticky="we", padx=5, pady=3)
        ttk.Entry(self.f_imagen, textvariable=self.imagen, width=38).grid(row=0, column=0, columnspan=2)
        ttk.Button(self.f_imagen, text="Buscar...", command=self._buscar_img).grid(row=0, column=2, padx=5)
        ttk.Label(self.f_imagen, text="Tamaño (% de la página):").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Scale(self.f_imagen, from_=5, to=100, variable=self.escala,
                  orient="horizontal", length=200).grid(row=1, column=1)
        ttk.Label(self.f_imagen, textvariable=self.escala, width=4).grid(row=1, column=2)

        # Ajustes
        f = ttk.LabelFrame(self, text="3. Ajustes")
        f.pack(fill="x", **p)
        ttk.Label(f, text="Opacidad (%):").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        ttk.Scale(f, from_=5, to=100, variable=self.opacidad, orient="horizontal",
                  length=220).grid(row=0, column=1)
        ttk.Label(f, textvariable=self.opacidad, width=4).grid(row=0, column=2)

        ttk.Label(f, text="Ángulo (°):").grid(row=1, column=0, sticky="w", padx=5, pady=4)
        ttk.Scale(f, from_=-90, to=90, variable=self.angulo, orient="horizontal",
                  length=220).grid(row=1, column=1)
        ttk.Label(f, textvariable=self.angulo, width=4).grid(row=1, column=2)

        ttk.Label(f, text="Posición:").grid(row=2, column=0, sticky="w", padx=5, pady=4)
        ttk.Combobox(f, textvariable=self.posicion, values=["Centro", "Mosaico"],
                     state="readonly", width=12).grid(row=2, column=1, sticky="w")

        ttk.Checkbutton(f, text="Dibujar encima del contenido (si no, queda detrás)",
                        variable=self.encima).grid(row=3, column=0, columnspan=3,
                                                   sticky="w", padx=5, pady=4)

        # Salida
        f = ttk.LabelFrame(self, text="4. Carpeta de salida (vacío = misma carpeta, sufijo _marca)")
        f.pack(fill="x", **p)
        ttk.Entry(f, textvariable=self.salida, width=58).pack(side="left", padx=5, pady=5)
        ttk.Button(f, text="...", width=3, command=self._carpeta).pack(side="left")

        # Acción
        self.barra = ttk.Progressbar(self, mode="determinate")
        self.barra.pack(fill="x", padx=10, pady=(10, 2))
        self.estado = ttk.Label(self, text="Listo")
        self.estado.pack()
        self.btn = ttk.Button(self, text="APLICAR MARCA DE AGUA", command=self._aplicar)
        self.btn.pack(pady=8, ipadx=20, ipady=6)

    # ---- helpers ----
    def _hex(self):
        return "#%02x%02x%02x" % self.color

    def _cambiar_modo(self):
        if self.usar_texto.get():
            self.f_texto.grid()
        else:
            self.f_texto.grid_remove()
        if self.usar_imagen.get():
            self.f_imagen.grid()
        else:
            self.f_imagen.grid_remove()

    def _elegir_color(self):
        rgb, _ = colorchooser.askcolor(color=self._hex(), title="Color del texto")
        if rgb:
            self.color = tuple(int(v) for v in rgb)
            self.btn_color.config(bg=self._hex())

    def _add(self):
        for r in filedialog.askopenfilenames(title="Selecciona PDFs",
                                             filetypes=[("PDF", "*.pdf")]):
            if r not in self.archivos:
                self.archivos.append(r)
                self.lista.insert("end", r)

    def _quitar(self):
        for i in reversed(self.lista.curselection()):
            self.lista.delete(i)
            del self.archivos[i]

    def _vaciar(self):
        self.lista.delete(0, "end")
        self.archivos.clear()

    def _buscar_img(self):
        r = filedialog.askopenfilename(title="Imagen",
                                       filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if r:
            self.imagen.set(r)

    def _carpeta(self):
        r = filedialog.askdirectory()
        if r:
            self.salida.set(r)

    # ---- proceso ----
    def _aplicar(self):
        if not self.archivos:
            return messagebox.showwarning("Falta algo", "Añade al menos un PDF.")
        if not (self.usar_texto.get() or self.usar_imagen.get()):
            return messagebox.showwarning("Falta algo", "Marca Texto, Imagen o ambos.")
        if self.usar_texto.get() and not self.texto.get().strip():
            return messagebox.showwarning("Falta algo", "Escribe el texto de la marca.")
        if self.usar_imagen.get() and not os.path.isfile(self.imagen.get()):
            return messagebox.showwarning("Falta algo", "Selecciona una imagen válida.")

        cfg = {
            "usar_texto": self.usar_texto.get(),
            "usar_imagen": self.usar_imagen.get(),
            "texto": self.texto.get(),
            "tamano": int(self.tamano.get()),
            "color": self.color,
            "imagen": self.imagen.get(),
            "escala": int(self.escala.get()),
            "opacidad": self.opacidad.get() / 100,
            "angulo": int(self.angulo.get()),
            "posicion": self.posicion.get(),
            "encima": self.encima.get(),
        }
        self.btn.config(state="disabled")
        self.barra.config(maximum=len(self.archivos), value=0)
        threading.Thread(target=self._trabajo, args=(cfg,), daemon=True).start()

    def _trabajo(self, cfg):
        errores, hechos, ultimo = [], 0, ""
        for i, ruta in enumerate(self.archivos, 1):
            self.after(0, self.estado.config, {"text": f"Procesando {os.path.basename(ruta)}..."})
            try:
                carpeta = self.salida.get().strip() or os.path.dirname(ruta)
                os.makedirs(carpeta, exist_ok=True)
                base = os.path.splitext(os.path.basename(ruta))[0]
                destino = os.path.join(carpeta, base + "_marca.pdf")
                marcar_pdf(ruta, destino, cfg)
                hechos += 1
                ultimo = destino
            except Exception as e:
                errores.append(f"{os.path.basename(ruta)}: {e}")
            self.after(0, self.barra.config, {"value": i})
        self.after(0, self._fin, hechos, errores, ultimo)

    def _fin(self, hechos, errores, ultimo):
        self.btn.config(state="normal")
        self.estado.config(text=f"Terminado: {hechos} PDF(s) marcados")
        msg = f"{hechos} PDF(s) guardados."
        if ultimo:
            msg += f"\nÚltimo: {ultimo}"
        if errores:
            msg += "\n\nErrores:\n" + "\n".join(errores)
            messagebox.showwarning("Terminado con errores", msg)
        else:
            messagebox.showinfo("Terminado", msg)


if __name__ == "__main__":
    App().mainloop()
