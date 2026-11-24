import wmi
import tkinter as tk
from tkinter import messagebox

def disable_network_adapter():
    c = wmi.WMI()
    adapters = c.Win32_NetworkAdapter()
    for adapter in adapters:
        if adapter.Name == "Ethernet":
            adapter.Disable()
            messagebox.showinfo("Success", "Network adapter disabled.")
            return
    messagebox.showerror("Error", "Network adapter not found.")

def enable_network_adapter():
    c = wmi.WMI()
    adapters = c.Win32_NetworkAdapter()
    for adapter in adapters:
        if adapter.Name == "Ethernet":
            adapter.Enable()
            messagebox.showinfo("Success", "Network adapter enabled.")
            return
    messagebox.showerror("Error", "Network adapter not found.")

root = tk.Tk()
root.title("Network Adapter Controller")

disable_button = tk.Button(root, text="Disable Network Adapter", command=disable_network_adapter)
disable_button.pack(pady=10)

enable_button = tk.Button(root, text="Enable Network Adapter", command=enable_network_adapter)
enable_button.pack(pady=10)

root.mainloop()