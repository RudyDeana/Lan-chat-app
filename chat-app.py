import socket
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from datetime import datetime
import json
import traceback

class P2PChat:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chat P2P LAN - Debug")
        self.root.geometry("560x720")
        self.root.configure(bg="#1a1a1a")

        self.username = None
        self.port = 5555
        self.udp_port = 5556
        try:
            self.my_ip = socket.gethostbyname(socket.gethostname())
        except:
            self.my_ip = "127.0.0.1"
            print("[ERRORE] Impossibile ottenere IP locale, uso 127.0.0.1")

        self.peers = {}  # username → dict
        self.chat_windows = {}

        self.running = True

        # UDP socket con timeout
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_sock.settimeout(2.0)
        try:
            self.udp_sock.bind(('', self.udp_port))
        except Exception as e:
            print(f"[ERRORE BIND UDP] {e}")
            messagebox.showerror("Errore", f"Porta UDP {self.udp_port} occupata?\n{e}")
            self.running = False
            self.root.destroy()
            return

        # TCP listener
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.tcp_sock.bind(('', self.port))
            self.tcp_sock.listen(5)
        except Exception as e:
            print(f"[ERRORE BIND TCP] {e}")
            messagebox.showerror("Errore", f"Porta TCP {self.port} occupata?\n{e}")
            self.running = False
            self.root.destroy()
            return

        threading.Thread(target=self.udp_broadcast_loop, daemon=True).start()
        threading.Thread(target=self.udp_listen_loop, daemon=True).start()
        threading.Thread(target=self.tcp_listen_loop, daemon=True).start()
        threading.Thread(target=self.cleanup_loop, daemon=True).start()

        self.ask_username()

    def ask_username(self):
        self.username = simpledialog.askstring("Username", "Inserisci il tuo nome:")
        if not self.username or not self.username.strip():
            self.username = f"Anon{int(time.time()) % 9999}"
        self.root.title(f"LAN Chat • {self.username}")
        self.build_ui()
        self.root.mainloop()

    def build_ui(self):
        tk.Label(self.root, text=f"Utenti • {self.username}", font=("Segoe UI", 14, "bold"),
                 bg="#1a1a1a", fg="#eeeeee").pack(pady=12)

        self.user_list = tk.Listbox(self.root, font=("Segoe UI", 11), height=12,
                                    bg="#252525", fg="#dddddd", selectbackground="#4444aa")
        self.user_list.pack(fill="both", expand=True, padx=12, pady=4)
        self.user_list.bind('<<ListboxSelect>>', self.open_private_from_list)

        tk.Button(self.root, text="Chat Globale", command=self.open_global,
                  font=("Segoe UI", 12, "bold"), bg="#006600", fg="white",
                  activebackground="#004d00").pack(pady=16, ipadx=20, ipady=8)

        self.update_list_loop()

    def update_list_loop(self):
        if not self.running: return
        self.user_list.delete(0, tk.END)
        for u in sorted(self.peers):
            self.user_list.insert(tk.END, u)
        self.root.after(3000, self.update_list_loop)

    def udp_broadcast_loop(self):
        while self.running:
            try:
                msg = f"DISC|{self.username}|{self.port}".encode()
                self.udp_sock.sendto(msg, ('<broadcast>', self.udp_port))
                print(f"[BCAST] Inviato discovery come {self.username}")
            except Exception as e:
                print(f"[BCAST ERR] {e}")
            time.sleep(3)

    def udp_listen_loop(self):
        while self.running:
            try:
                data, addr = self.udp_sock.recvfrom(512)
                parts = data.decode('utf-8', errors='ignore').split('|')
                if len(parts) == 3 and parts[0] == "DISC":
                    uname, p_str = parts[1], parts[2]
                    port = int(p_str)
                    if uname != self.username and addr[0] != self.my_ip:
                        self.peers[uname] = {'ip': addr[0], 'port': port, 'last': time.time()}
                        print(f"[DISC] Trovato {uname} da {addr[0]}:{port}")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[UDP LISTEN ERR] {e}")

    def cleanup_loop(self):
        while self.running:
            time.sleep(15)
            now = time.time()
            dead = [u for u, d in self.peers.items() if now - d['last'] > 45]
            for u in dead:
                print(f"[CLEAN] Rimuovo offline: {u}")
                del self.peers[u]

    def tcp_listen_loop(self):
        while self.running:
            try:
                client, addr = self.tcp_sock.accept()
                print(f"[TCP] Connessione da {addr}")
                threading.Thread(target=self.handle_tcp_client, args=(client,), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"[TCP LISTEN ERR] {e}")

    def handle_tcp_client(self, sock):
        try:
            while self.running:
                len_bytes = sock.recv(4)
                if len(len_bytes) < 4: break
                length = int.from_bytes(len_bytes, 'big')
                data = b''
                while len(data) < length:
                    chunk = sock.recv(length - len(data))
                    if not chunk: break
                    data += chunk
                if len(data) != length: break

                try:
                    msg = json.loads(data.decode('utf-8', errors='ignore'))
                    print(f"[RCV] {msg.get('type')} da {msg.get('from')}")
                    self.process_incoming(msg)
                except json.JSONDecodeError:
                    print("[JSON ERR] Messaggio corrotto")
        except Exception as e:
            print(f"[TCP CLIENT ERR] {traceback.format_exc()}")
        finally:
            sock.close()

    def process_incoming(self, msg):
        typ = msg.get('type')
        sender = msg.get('from')
        content = msg.get('msg', '')
        if sender == self.username: return

        ts = datetime.now().strftime("%H:%M")

        if typ == 'global':
            if 'global' in self.chat_windows:
                t = self.chat_windows['global']['text']
                t.insert(tk.END, f"[{ts}] {sender}: {content}\n", "in")
                t.see(tk.END)

        elif typ == 'private':
            key = ('p', sender)
            if key in self.chat_windows:
                t = self.chat_windows[key]['text']
                t.insert(tk.END, f"[{ts}] {sender}: {content}\n", "in")
                t.see(tk.END)
            else:
                self.open_private(sender, f"[{ts}] {sender}: {content}\n")

    def send_message(self, data, target_ip=None, target_port=None):
        payload = json.dumps(data).encode('utf-8')
        length = len(payload).to_bytes(4, 'big')

        if target_ip and target_port:
            # privato
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(4)
                s.connect((target_ip, target_port))
                s.send(length + payload)
                s.close()
                print(f"[SND PRIV] a {target_ip}:{target_port}")
            except Exception as e:
                print(f"[SEND PRIV FAIL] {e}")
        else:
            # globale
            for p in list(self.peers.values()):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(4)
                    s.connect((p['ip'], p['port']))
                    s.send(length + payload)
                    s.close()
                except Exception as e:
                    print(f"[SEND GLOBAL FAIL a {p['ip']}:{p['port']}] {e}")

    def open_global(self):
        if 'global' in self.chat_windows and self.chat_windows['global']['win'].winfo_exists():
            self.chat_windows['global']['win'].lift()
            return

        win = tk.Toplevel(self.root)
        win.title("Globale")
        win.geometry("560x640")
        win.configure(bg="#1a1a1a")

        text = scrolledtext.ScrolledText(win, font=("Consolas", 11), bg="#222222", fg="#eeeeee",
                                         insertbackground="white")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.tag_config("out", foreground="#aaffaa")
        text.tag_config("in", foreground="#88ccff")

        entry = tk.Entry(win, font=("Segoe UI", 12), bg="#333333", fg="white", insertbackground="white")
        entry.pack(fill="x", padx=10, pady=5, ipady=4)

        def do_send():
            m = entry.get().strip()
            if not m: return
            ts = datetime.now().strftime("%H:%M")
            text.insert(tk.END, f"[{ts}] Tu: {m}\n", "out")
            text.see(tk.END)
            entry.delete(0, tk.END)
            self.send_message({'type': 'global', 'from': self.username, 'msg': m})

        tk.Button(win, text="Invia", command=do_send, bg="#006600", fg="white").pack(pady=5)

        entry.bind("<Return>", lambda e: do_send())

        self.chat_windows['global'] = {'win': win, 'text': text}
        win.protocol("WM_DELETE_WINDOW", lambda: self.chat_windows.pop('global', None) or win.destroy())

    def open_private_from_list(self, event):
        sel = self.user_list.curselection()
        if not sel: return
        uname = self.user_list.get(sel)
        self.open_private(uname)

    def open_private(self, target, initial_msg=None):
        key = ('p', target)
        if key in self.chat_windows and self.chat_windows[key]['win'].winfo_exists():
            self.chat_windows[key]['win'].lift()
            if initial_msg:
                self.chat_windows[key]['text'].insert(tk.END, initial_msg, "in")
                self.chat_windows[key]['text'].see(tk.END)
            return

        if target not in self.peers:
            messagebox.showinfo("Info", f"{target} non è più online")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Con {target}")
        win.geometry("560x640")
        win.configure(bg="#1a1a1a")

        text = scrolledtext.ScrolledText(win, font=("Consolas", 11), bg="#222222", fg="#eeeeee",
                                         insertbackground="white")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.tag_config("out", foreground="#aaffaa")
        text.tag_config("in", foreground="#88ccff")

        entry = tk.Entry(win, font=("Segoe UI", 12), bg="#333333", fg="white", insertbackground="white")
        entry.pack(fill="x", padx=10, pady=5, ipady=4)

        def do_send():
            m = entry.get().strip()
            if not m: return
            ts = datetime.now().strftime("%H:%M")
            text.insert(tk.END, f"[{ts}] Tu: {m}\n", "out")
            text.see(tk.END)
            entry.delete(0, tk.END)
            peer = self.peers[target]
            self.send_message({'type': 'private', 'from': self.username, 'msg': m},
                              peer['ip'], peer['port'])

        tk.Button(win, text="Invia", command=do_send, bg="#006600", fg="white").pack(pady=5)

        entry.bind("<Return>", lambda e: do_send())

        self.chat_windows[key] = {'win': win, 'text': text}
        if initial_msg:
            text.insert(tk.END, initial_msg, "in")
            text.see(tk.END)

        win.protocol("WM_DELETE_WINDOW", lambda: self.chat_windows.pop(key, None) or win.destroy())

    def destroy(self):
        self.running = False
        try:
            self.udp_sock.close()
            self.tcp_sock.close()
        except:
            pass
        self.root.destroy()


if __name__ == "__main__":
    try:
        app = P2PChat()
    except Exception as e:
        print(f"CRASH ALL'AVVIO: {traceback.format_exc()}")
