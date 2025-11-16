**TCP File Server – Multi-Device Secure File Management System**

Ky projekt implementon një sistem të plotë Server–Klient mbi protokollin TCP, i cili lejon pajisje të shumta të lidhen me serverin, të autentifikohen dhe të kryejnë operacione të ndryshme me skedarë në mënyrë të sigurt.

**Veçoritë Kryesore**

Server TCP me multi-threading

Autentifikim me username/password

Role përdoruesish (full dhe read)

Menaxhim skedarësh: upload, download, read, delete, info, search, list

Statistika të serverit në kohë reale

Klient normal dhe klient administrativ

Logim mesazhesh, timeout dhe kontroll i ngarkesës

**1. Startimi i Serverit**

python server.py 

**2. Autentifikimi dhe Rolet**

Autentifikimi bëhet me komandën:

HELLO <username> <password>


Roli caktohet automatikisht nga serveri:

full – akses i plotë mbi skedarët

read – vetëm lexim dhe informacion

**3. Klienti Normal**

Startohet me:

python client.py --host 127.0.0.1 --port 9000 --user device2 --password pass2
python client.py --host 127.0.0.1 --port 9000 --user device3 --password pass3
python client.py --host 127.0.0.1 --port 9000 --user device4 --password pass4

Komandat për të gjithë përdoruesit

/list               – liston skedarët në server

/read <file>        – lexon përmbajtjen e skedarit

/info <file>        – jep madhësinë dhe datën e krijimit/modifikimit

/search <keyword>   – kërkon skedarë sipas fjalës kyçe

Komandat për rolin FULL

/upload <file>      – ngarkon një skedar në server

/download <file>    – shkarkon një skedar nga serveri

/delete <file>      – fshin një skedar nga serveri

Statistikat e serverit

STATS               – shfaq statistika të serverit në kohë reale

**4. Klienti Administrativ**

Startohet me:

python admin_client.py --host 127.0.0.1 --port 9000 --user device1 --password pass1

