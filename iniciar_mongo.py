"""Inicia MongoDB Community portátil no Windows, sem instalar serviço do sistema."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import zipfile

from pymongo import MongoClient
from pymongo.errors import PyMongoError

RAIZ = Path(__file__).resolve().parent
URL = 'https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-8.0.34.zip'
SHA256 = '6b021a0864494e4decf278b36477a29eb36072432773e4e62c2f42c302630db0'


def disponivel(porta):
    try:
        with MongoClient(f'mongodb://127.0.0.1:{porta}', serverSelectionTimeoutMS=1000) as cliente:
            cliente.admin.command('ping')
        return True
    except PyMongoError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--porta', type=int, default=27017)
    args = parser.parse_args()
    if disponivel(args.porta):
        print(f'MongoDB já disponível em 127.0.0.1:{args.porta}')
        return
    if sys.platform != 'win32':
        raise SystemExit('Use docker compose up -d mongodb ou um MongoDB já instalado neste sistema.')
    ferramentas = RAIZ / '.tools'
    executaveis = list(ferramentas.glob('mongodb-*/bin/mongod.exe'))
    if not executaveis:
        ferramentas.mkdir(exist_ok=True)
        arquivo = ferramentas / 'mongodb.zip'
        print('Baixando MongoDB Community 8.0.34 da fonte oficial...', flush=True)
        with urllib.request.urlopen(URL, timeout=90) as resposta, arquivo.open('wb') as saida:
            import shutil
            shutil.copyfileobj(resposta, saida)
        with arquivo.open('rb') as entrada:
            digest = hashlib.sha256(entrada.read()).hexdigest()
        if digest != SHA256:
            raise SystemExit('SHA256 inválido: o download não será executado. Execute novamente.')
        with zipfile.ZipFile(arquivo) as pacote:
            raiz = ferramentas.resolve()
            for item in pacote.infolist():
                if not (raiz / item.filename).resolve().is_relative_to(raiz):
                    raise SystemExit('Caminho inválido no pacote MongoDB')
            pacote.extractall(ferramentas)
        arquivo.unlink()
        executaveis = list(ferramentas.glob('mongodb-*/bin/mongod.exe'))
    pasta = RAIZ / '.mongo' / str(args.porta)
    pasta.mkdir(parents=True, exist_ok=True)
    processo = subprocess.Popen([str(executaveis[0]), '--dbpath', str(pasta), '--bind_ip', '127.0.0.1', '--port', str(args.porta), '--logpath', str(pasta / 'mongo.log'), '--logappend'],
                               creationflags=subprocess.CREATE_NO_WINDOW, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (pasta / 'mongod.pid').write_text(str(processo.pid), encoding='ascii')
    for _ in range(30):
        if disponivel(args.porta):
            print(f'MongoDB iniciado em 127.0.0.1:{args.porta}; PID {processo.pid}. Dados: {pasta}')
            return
        if processo.poll() is not None:
            break
        time.sleep(1)
    raise SystemExit(f'MongoDB não iniciou; consulte {pasta / "mongo.log"}')


if __name__ == '__main__':
    main()
