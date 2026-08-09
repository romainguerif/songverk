#!/usr/bin/env python3
"""Applique un patch Songverk et verifie l'empreinte de chaque fichier produit.

    python3 apply-patch.py patch-0.7.0.json
"""
import base64, gzip, hashlib, json, pathlib, subprocess, sys, tempfile

def main(path):
    data = json.load(open(path))
    for name, item in data.items():
        body = gzip.decompress(base64.b64decode(item["p"])).decode()
        with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False) as f:
            f.write(body); tmp = f.name
        r = subprocess.run(["patch", "-p0", "--forward", name, tmp], capture_output=True, text=True)
        if r.returncode != 0:
            print(name, "-> ECHEC"); print(r.stdout, r.stderr); sys.exit(1)
        got = hashlib.md5(pathlib.Path(name).read_bytes()).hexdigest()
        ok = got == item["md5"]
        print(f"{name:12s} -> {'ok' if ok else 'EMPREINTE DIFFERENTE'}  {got}")
        if not ok:
            sys.exit("le fichier produit ne correspond pas a la reference, transfert corrompu")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: apply-patch.py patch-x.y.z.json")
    if not pathlib.Path("index.html").exists():
        sys.exit("lance ce script depuis le dossier du depot")
    main(sys.argv[1])
