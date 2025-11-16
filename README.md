**TCP File Server – Multi-Device Secure File Management System**

Ky projekt implementon një sistem të plotë server–klient mbi protokollin TCP, i cili lejon pajisje të ndryshme të lidhen me serverin, të autentifikohen dhe të kryejnë operacione të ndryshme mbi skedarë.

Projekti përfshin:
•	Server TCP me multi-threading

•	Autentifikim me username/password

•	Role të ndryshme përdoruesish (full / read)

•	Menaxhim skedarësh (upload, download, read, delete, info, search, list)

•	Statistika të serverit në kohë reale

•	Klient normal dhe klient administrativ

•	Logim mesazhesh, menaxhim i ngarkesës dhe timeout të lidhjeve


**1. Si të startohet serveri**
python3 server.py --host 127.0.0.1 --port 9000
**2. Autentifikimi dhe rolet**
Autentifikimi bëhet me: **HELLO <username> <password>**
**3. Klienti normal – përdorimi**
python3 client.py --host 127.0.0.1 --port 9000 --user device1 --password pass1
Komandat e klientit:
/list               – liston skedarët në server
/read <file>        – lexon përmbajtjen
/info <file>        – jep madhësinë, datën e krijimit/modifikimit
/search <keyword>   – kërkon skedarë sipas emrit
Komandat për "full" role:
/upload <file>
/download <file>
/delete <file>
Për statistika të serverit:
STATS
**4. Klienti administrativ (admin_client.py)**
python3 admin_client.py --host 127.0.0.1 --port 9000 --user device1 --password pass1
