TCP File Server – Multi-Device File Management System

Ky projekt implementon një sistem Server–Klient mbi TCP, ku klientët mund të lidhen me serverin, të autentifikohen dhe të kryejnë operacione mbi skedarët në mënyrë të kontrolluar sipas role-ve të tyre. Serveri përdor multi-threading, autentifikim me username/password, role përdoruesish (full dhe read), menaxhim skedarësh (upload, download, read, delete, info, search, list), statistika në kohë reale dhe logim të mesazheve. Klientët mund të jenë read-only ose me akses të plotë (full).

Serveri mund të refuzojë lidhjet e reja nëse numri i lidhjeve aktive kalon një prag të caktuar. Nëse një klient nuk dërgon kërkesa brenda një periudhe të caktuar kohe, lidhja mbyllet automatikisht. Serveri ruan statistika si numrin e lidhjeve aktive, mesazhet e pranuara për secilin klient, dhe trafikun e dërguar/pranuar në bytes.

Klienti krijon një lidhje TCP me serverin duke specifikuar IP dhe portin. Klientët me privilegje të plotë mund të ekzekutojnë komandat /upload, /download, /delete, /list, /read, /info, dhe /search, ndërsa klientët read-only kanë akses vetëm për lexim dhe informacion. Mesazhet e dërguara pa komandë / regjistrohen dhe echohen nga serveri. Koha e përgjigjes për klientët full është më e shpejtë se për klientët read-only.

Struktura e projektit përfshin skriptat server.py dhe client.py, një folder për ruajtjen e skedarëve, një file për përdoruesit dhe rolet e tyre (users.json), një file për statistikat (server_stats.txt) dhe një file për logun e mesazheve (messages.log). Të dy skriptat duhet të jenë të pranishëm për ekzekutim dhe funksionim të plotë të sistemit.

