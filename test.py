import cv2
import tkinter as tk
from tkinter import filedialog, simpledialog
import customtkinter 
from PIL import Image, ImageTk

# Load the layout image
image_path = filedialog.askopenfilename(title="Select Layout Image")
base_image = cv2.imread(image_path)
display_image = base_image.copy()

labels = []  # stores (x, y, label)
delete_mode = False
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 0.4
thickness = 1

window = tk.Tk()
window.title("Interactive Layout Labeling Tool")

img = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
img = Image.fromarray(img)
tk_img = ImageTk.PhotoImage(img)

canvas = tk.Canvas(window, width=tk_img.width(), height=tk_img.height())
canvas.pack()
canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

def redraw_labels():
    global tk_img
    display_image[:] = base_image.copy()
    for lx, ly, text in labels:
        cv2.putText(display_image, text, (lx, ly), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
    img = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img)
    tk_img = ImageTk.PhotoImage(img)
    canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
    canvas.image = tk_img

def on_click(event):
    global delete_mode
    x, y = event.x, event.y

    if delete_mode:
        for i, (lx, ly, text) in enumerate(labels):
            text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
            if lx <= x <= lx + text_size[0] and ly - text_size[1] <= y <= ly:
                del labels[i]
                redraw_labels()
                print(f"Deleted label '{text}' at ({lx}, {ly})")
                return
    else:
        label = simpledialog.askstring("Label", f"Enter label for pallet spot ({x}, {y}):")
        if label:
            labels.append((x, y, label))
            redraw_labels()

def toggle_mode():
    global delete_mode
    delete_mode = not delete_mode
    mode_button.config(text=f"Mode: {'Delete' if delete_mode else 'Label'}")

def save_image():
    save_path = filedialog.asksaveasfilename(defaultextension=".png")
    if save_path:
        cv2.imwrite(save_path, display_image)
        print(f"Saved labeled layout to {save_path}")

canvas.bind("<Button-1>", on_click)

save_button = tk.Button(window, text="Save Labeled Image", command=save_image)
save_button.pack(pady=5)

mode_button = tk.Button(window, text="Mode: Label", command=toggle_mode)
mode_button.pack(pady=5)

window.mainloop()