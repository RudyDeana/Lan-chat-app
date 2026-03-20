# 🚀 Chat P2P LAN

Chat privata + chat di tutti sulla rete WiFi  
Zero server, zero installazioni extra, zero permessi admin.

Funziona su Windows + Mac + Linux usando solo Python standard con Tkinter.

## Come funziona
- Tutti aprono l'app sulla stessa rete WiFi (scuola, casa, ecc.)
- Gli utenti si vedono automaticamente (discovery ogni ~4 secondi via broadcast UDP)
- Clicchi un nome nella lista → apre chat privata
- Pulsante grande → Chat di tutti (messaggi a chiunque abbia l'app aperta)

## Requisiti
- Python 3.8 o superiore installato
- Tkinter (di solito già incluso con Python)

## Installazione super facile (30 secondi)

### Metodo 1 – Il più veloce (nessun git)
1. Vai nella pagina del repository su GitHub
2. Clicca sul file chat-app.py
3. Clicca il bottone Raw
4. Premi Ctrl + S (o Cmd + S su Mac) e salva come chat-app.py  
   (controlla che sia .py e non .txt)
5. Copia il file sulla chiavetta / Desktop del PC

### Metodo 2 – Clona il repository (se hai git)
git clone https://github.com/RudyDeana/Lan-chat-app 

cd Lan-chat-app


## Come avviare l'app

Windows
- Doppio clic su chat-app.py (se Python è associato ai file .py)
- Oppure Prompt dei comandi / PowerShell nella cartella:
  python chat-app.py

Mac
- Terminale, nella cartella del file:
- python3 chat-app.py

Linux / PC  con Linux
- Stesso del Mac:
  python3 chat-app.py

## Come usarla
1. Scrivi il tuo username
2. Aspetta 5–15 secondi
3. Vedi la lista utenti online
4. Clicca un nome → chat privata
5. Clicca "Chat di tutti" → parla con tutti

## Problemi comuni + soluzioni

Problema: Non vedo nessuno nella lista  
Soluzione: Tutti sulla stessa WiFi. Aspetta 20 secondi. Riavvia l'app.

Problema: Errore "_tkinter" su Mac  
Soluzione: brew install python-tk@3.13 (o la tua versione di Python)

Problema: Firewall blocca  
Soluzione: Porte 5555 (TCP) e 5556 (UDP). Di solito ok a scuola.

Problema: Su Mac non parte proprio  
Soluzione: Prova Python da python.org invece di Homebrew

## Note finali
- Solo locale (LAN/WiFi). Per amici da casa serve versione con IP manuale.
- Se vuoi gruppi, suoni o versione internet → dimmelo e la aggiorniamo!

Fatto da Rudy con ❤️
