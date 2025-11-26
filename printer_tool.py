import socket
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from concurrent.futures import ThreadPoolExecutor

PORT = 9100  # ESC/POS printing port

# ------------------------
# NETWORK FUNCTIONS
# ------------------------
def test_connection(ip, port=PORT, timeout=0.5):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, port))
        s.close()
        return True
    except:
        return False

def send_custom_print(ip, text):
    try:
        esc_init = b"\x1B\x40"
        esc_cut = b"\n\n\x1D\x56\x41"
        msg = esc_init + text.encode("utf-8") + esc_cut

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((ip, PORT))
        s.send(msg)
        s.close()
        return True
    except Exception as e:
        return str(e)

def print_qr_code(ip, text, qr_size=6):
    """
    Epson TM-T20III QR code print (working version)
    qr_size: module size 1-16
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((ip, 9100))

        # Initialize printer
        s.send(b"\x1B\x40")  # ESC @

        # Prepare QR data
        data = text.encode('utf-8')
        length = len(data) + 3
        lsb = length & 0xFF
        msb = (length >> 8) & 0xFF

        # 1️⃣ Set module size
        escpos = b"\x1D\x28\x6B\x03\x00\x31\x43" + bytes([qr_size])
        # 2️⃣ Set error correction (48=L)
        escpos += b"\x1D\x28\x6B\x03\x00\x31\x45\x30"
        # 3️⃣ Store QR data
        escpos += b"\x1D\x28\x6B" + bytes([lsb, msb]) + b"\x31\x50\x30" + data
        # 4️⃣ Print QR
        escpos += b"\x1D\x28\x6B\x03\x00\x31\x51\x30"

        s.send(escpos)

        # Cut paper
        s.send(b"\n\n\x1D\x56\x41")

        s.close()
        return True
    except Exception as e:
        return str(e)



# ------------------------
# PRINTER TOOLS WINDOW
# ------------------------
def open_printer_tools():
    root = tk.Toplevel()
    root.title("Printer Tools")
    root.geometry("400x400")
    root.resizable(False, False)

    tk.Label(root, text="Printer IP:", font=("Arial", 12)).pack(pady=5)
    ip_entry = tk.Entry(root, font=("Arial", 12), width=22)
    ip_entry.pack()

    # --------- Test Connection ---------
    def on_test_connection():
        ip = ip_entry.get().strip()
        if not ip:
            return
        if test_connection(ip):
            messagebox.showinfo("Connection", f"✔ Printer at {ip} is reachable.")
        else:
            messagebox.showerror("Connection", f"✖ Cannot connect to {ip}")

    # --------- Custom Print ---------
    def on_custom_print():
        ip = ip_entry.get().strip()
        if not ip:
            return
        popup = tk.Toplevel(root)
        popup.title("Custom Print")
        popup.geometry("350x250")
        tk.Label(popup, text="Enter text:", font=("Arial", 11)).pack(pady=5)
        text_box = tk.Text(popup, height=8, width=35, font=("Arial", 11))
        text_box.pack()

        def do_print():
            text = text_box.get("1.0", tk.END).strip()
            result = send_custom_print(ip, text)
            if result == True:
                messagebox.showinfo("Done", "✔ Printed successfully")
            else:
                messagebox.showerror("Error", str(result))
            popup.destroy()

        tk.Button(popup, text="Print", font=("Arial", 12), command=do_print).pack(pady=10)

    # --------- QR Code Print ---------
    def on_print_qr():
        ip = ip_entry.get().strip()
        if not ip:
            return
        popup = tk.Toplevel(root)
        popup.title("Print QR Code")
        popup.geometry("350x200")

        tk.Label(popup, text="Enter text to make QR:", font=("Arial", 11)).pack(pady=5)
        text_box = tk.Text(popup, height=5, width=35, font=("Arial", 11))
        text_box.pack(pady=5)

        def do_qr_print():
            text = text_box.get("1.0", tk.END).strip()
            result = print_qr_code(ip, text)
            if result == True:
                tk.messagebox.showinfo("Done", "✔ QR Code printed successfully")
            else:
                tk.messagebox.showerror("Error", str(result))
            popup.destroy()

        tk.Button(popup, text="Print QR Code", font=("Arial", 12), command=do_qr_print).pack(pady=10)

    # --------- Buttons ---------
    tk.Button(root, text="Test Connection", font=("Arial", 12), width=20,
              command=on_test_connection).pack(pady=10)
    tk.Button(root, text="Custom Print", font=("Arial", 12), width=20,
              command=on_custom_print).pack(pady=10)
    tk.Button(root, text="Print QR Code", font=("Arial", 12), width=20,
              command=on_print_qr).pack(pady=10)
    tk.Button(root, text="Close", font=("Arial", 12), width=20,
              command=root.destroy).pack(pady=20)

# ------------------------
# ULTRA FAST NETWORK SCAN WINDOW
# ------------------------
def open_scan_window():
    win = tk.Toplevel()
    win.title("Scan Network for Printers")
    win.geometry("500x500")
    win.resizable(False, False)

    tk.Label(win, text="Scan Range: 192.168.1.1 - 192.168.1.255", font=("Arial", 12)).pack(pady=5)

    tree = ttk.Treeview(win, columns=("ip", "status"), show="headings")
    tree.heading("ip", text="IP Address")
    tree.heading("status", text="Status")
    tree.column("ip", width=200)
    tree.column("status", width=150)
    tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    progress = tk.Label(win, text="", font=("Arial", 10))
    progress.pack()

    scanning = False

    def run_scan_thread():
        ips = [f"192.168.1.{i}" for i in range(1, 256)]
        found = 0

        def check_ip(ip):
            nonlocal found
            if test_connection(ip, timeout=0.3):
                found += 1
                win.after(0, lambda ip=ip: tree.insert("", tk.END, values=(ip, "✔ Printer Found")))

        with ThreadPoolExecutor(max_workers=50) as executor:
            executor.map(check_ip, ips)

        win.after(0, lambda: progress.config(text=f"Scan complete. Printers found: {found}"))
        nonlocal scanning
        scanning = False

    def start_scan():
        nonlocal scanning
        if scanning:
            return
        scanning = True
        tree.delete(*tree.get_children())
        progress.config(text="Scanning...")
        t = threading.Thread(target=run_scan_thread, daemon=True)
        t.start()

    tk.Button(win, text="Start Scan", font=("Arial", 12), width=20,
              command=start_scan).pack(pady=5)

# ------------------------
# MAIN MENU
# ------------------------
def main_menu():
    root = tk.Tk()
    root.title("Thermal Printer Utility")
    root.geometry("300x250")
    root.resizable(False, False)

    tk.Label(root, text="Select Action:", font=("Arial", 14)).pack(pady=20)
    tk.Button(root, text="Printer Tools", width=20, height=2,
              font=("Arial", 12), command=open_printer_tools).pack(pady=10)
    tk.Button(root, text="Scan Network", width=20, height=2,
              font=("Arial", 12), command=open_scan_window).pack(pady=10)

    root.mainloop()

# ------------------------
if __name__ == "__main__":
    main_menu()
