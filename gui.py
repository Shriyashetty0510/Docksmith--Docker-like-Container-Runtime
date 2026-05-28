import customtkinter as ctk
import subprocess
import threading
import os

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Docksmith GUI")
app.geometry("900x650")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "app")

# ---------- Functions ----------

def append_output(text):
    output_box.configure(state="normal")
    output_box.insert("end", text + "\n")
    output_box.see("end")
    output_box.configure(state="disabled")


def clear_output():
    output_box.configure(state="normal")
    output_box.delete("1.0", "end")
    output_box.configure(state="disabled")


def run_command(command):
    try:
        clear_output()

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            cwd=APP_DIR
        )

        for line in process.stdout:
            append_output(line.strip())

        process.wait()

        if process.returncode == 0:
            status_label.configure(text="Success", text_color="green")
        else:
            status_label.configure(text="Failed", text_color="red")

    except Exception as e:
        append_output(f"Error: {e}")
        status_label.configure(text="Error", text_color="red")


def build_image():
    image_name = image_entry.get().strip()

    if not image_name:
        append_output("Please enter image name")
        return

    status_label.configure(text="Building...", text_color="yellow")

    no_cache = no_cache_var.get()

    if no_cache:
        command = f'python ../docksmith.py build -t {image_name} --no-cache'
    else:
        command = f'python ../docksmith.py build -t {image_name}'

    threading.Thread(target=run_command, args=(command,), daemon=True).start()


def run_image():
    image_name = image_entry.get().strip()

    if not image_name:
        append_output("Please enter image name")
        return

    status_label.configure(text="Running...", text_color="yellow")

    command = f'python ../docksmith.py run -t {image_name}'
    threading.Thread(target=run_command, args=(command,), daemon=True).start()


def show_images():
    status_label.configure(text="Loading Images...", text_color="yellow")

    command = 'python ../docksmith.py images'
    threading.Thread(target=run_command, args=(command,), daemon=True).start()


def remove_image():
    image_name = image_entry.get().strip()

    if not image_name:
        append_output("Please enter image name")
        return

    status_label.configure(text="Removing...", text_color="yellow")

    command = f'python ../docksmith.py rmi -t {image_name}'
    threading.Thread(target=run_command, args=(command,), daemon=True).start()


# ---------- Title ----------

title_label = ctk.CTkLabel(
    app,
    text="Docksmith GUI",
    font=("Arial", 34, "bold")
)
title_label.pack(pady=25)

# ---------- Image Name ----------

image_frame = ctk.CTkFrame(app)
image_frame.pack(pady=10, padx=20, fill="x")

image_label = ctk.CTkLabel(
    image_frame,
    text="Image Name:",
    font=("Arial", 18)
)
image_label.pack(side="left", padx=15, pady=15)

image_entry = ctk.CTkEntry(
    image_frame,
    width=350,
    font=("Arial", 16)
)
image_entry.insert(0, "myapp:v1")
image_entry.pack(side="left", padx=10, pady=15)

# ---------- No Cache ----------

no_cache_var = ctk.BooleanVar()

no_cache_checkbox = ctk.CTkCheckBox(
    app,
    text="No Cache Build",
    variable=no_cache_var,
    font=("Arial", 16)
)
no_cache_checkbox.pack(pady=15)

# ---------- Buttons ----------

button_frame = ctk.CTkFrame(app)
button_frame.pack(pady=20)

build_button = ctk.CTkButton(
    button_frame,
    text="Build",
    command=build_image,
    width=180,
    height=45,
    font=("Arial", 16)
)
build_button.grid(row=0, column=0, padx=12, pady=12)

run_button = ctk.CTkButton(
    button_frame,
    text="Run",
    command=run_image,
    width=180,
    height=45,
    font=("Arial", 16)
)
run_button.grid(row=0, column=1, padx=12, pady=12)

images_button = ctk.CTkButton(
    button_frame,
    text="Show Images",
    command=show_images,
    width=180,
    height=45,
    font=("Arial", 16)
)
images_button.grid(row=1, column=0, padx=12, pady=12)

remove_button = ctk.CTkButton(
    button_frame,
    text="Remove Image",
    command=remove_image,
    width=180,
    height=45,
    font=("Arial", 16)
)
remove_button.grid(row=1, column=1, padx=12, pady=12)

# ---------- Status ----------

status_label = ctk.CTkLabel(
    app,
    text="Ready",
    font=("Arial", 18, "bold")
)
status_label.pack(pady=15)

# ---------- Output Box ----------

output_box = ctk.CTkTextbox(
    app,
    width=800,
    height=280,
    font=("Consolas", 15)
)
output_box.pack(pady=20, padx=20)
output_box.configure(state="disabled")

# ---------- Run ----------

app.mainloop()