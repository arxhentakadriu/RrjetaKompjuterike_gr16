import socket, argparse, os, json

parser = argparse.ArgumentParser()
parser.add_argument('--host', required=True)
parser.add_argument('--port', required=True, type=int)
parser.add_argument('--user', required=True)
parser.add_argument('--password', required=True)
args = parser.parse_args()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((args.host, args.port))


s.sendall(f"HELLO {args.user} {args.password}\n".encode())
welcome = s.recv(4096).decode()
print(welcome.strip())

role = "full" if "full" in welcome else "read"

try:
    while True:
        cmd = input("> ").strip()
        if not cmd:
            continue

       
        if cmd.startswith(('/upload', '/delete', '/download')) and role != 'full':
            print("Read-only client — nuk ke leje për këtë komandë.")
            continue

       
        if cmd.startswith('/upload') and role == 'full':
            parts = cmd.split(maxsplit=1)
            if len(parts) != 2:
                print("Usage: /upload <filename>")
                continue
            filename = parts[1]
            if not os.path.isfile(filename):
                print("File nuk ekziston!")
                continue
            filesize = os.path.getsize(filename)
            s.sendall(f"/upload {os.path.basename(filename)}\n".encode())
            s.sendall(json.dumps({"filename": os.path.basename(filename), "size": filesize}).encode() + b'\n')
            with open(filename, 'rb') as f:
                s.sendall(f.read())
            print(f"Upload i kryer: {filename}")
            continue

        if cmd.startswith('/download') and role == 'full':
            parts = cmd.split(maxsplit=1)
            if len(parts) != 2:
                print("Usage: /download <filename>")
                continue
            filename = parts[1]
            s.sendall(cmd.encode() + b'\n')
            resp = s.recv(8192)
            print(resp.decode(errors='ignore'))
            continue

        
        s.sendall((cmd + '\n').encode())
        timeout = 0.5 if role == 'full' else 2.0
        s.settimeout(timeout)
        try:
            resp = s.recv(8192)
        except socket.timeout:
            print("(Server response delayed...)")
            continue

        if not resp:
            print("Server closed connection")
            break
        print(resp.decode(errors='ignore'))

except KeyboardInterrupt:
    print("\nClosing connection...")
finally:
    s.close()
