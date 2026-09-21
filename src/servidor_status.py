"""Servico HTTP que publica o resultado da medicao.

Este e o servico que justifica a unica porta aberta no grupo de seguranca
(8000/tcp). A porta administrativa (22/tcp, SSH) NAO fica aberta para
0.0.0.0/0: ela e restrita ao IP de origem da equipe.

Rotas:
    GET /                  pagina HTML com a tabela de medicoes
    GET /resultados.json   o JSON cru gerado pelo benchmark.py
    GET /saude             verificacao de disponibilidade (200 OK)

Serve HTTP puro, sem TLS, de proposito: a pagina e somente leitura, nao
tem autenticacao nem rota que altere estado, entao nao ha segredo em
transito para proteger. Um servico que recebesse credencial ou escrita
exigiria HTTPS e um certificado -- nao e o caso deste.

So biblioteca padrao: nada para instalar na instancia.

    python servidor_status.py --porta 8000 --arquivo ../resultados/resultados.json
"""

from __future__ import annotations

import argparse
import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Ancorado no arquivo, nao no diretorio atual: o servico acha o resultado
# tanto rodando de dentro de src/ quanto da raiz do repositorio.
RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_RESULTADOS = RAIZ / "resultados" / "resultados.json"

ESTILO = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { margin:0; padding:24px; font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif;
       background:#f6f7f9; color:#14243a; }
main { max-width:900px; margin:0 auto; }
h1 { font-size:22px; margin:0 0 4px; }
p.sub { margin:0 0 20px; color:#5b6b80; font-size:13px; }
section { background:#fff; border:1px solid #dfe4ea; border-radius:10px;
          padding:18px; margin-bottom:16px; }
h2 { font-size:14px; text-transform:uppercase; letter-spacing:.06em;
     color:#5b6b80; margin:0 0 12px; }
table { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }
th,td { padding:8px 10px; text-align:right; border-bottom:1px solid #eef1f4; }
th:first-child,td:first-child { text-align:left; }
th { font-size:12px; text-transform:uppercase; letter-spacing:.04em; color:#5b6b80; }
tr:last-child td { border-bottom:none; }
.ok { color:#0f7a4d; font-weight:600; }
.falha { color:#b3261e; font-weight:600; }
dl { display:grid; grid-template-columns:auto 1fr; gap:6px 16px; margin:0; font-size:14px; }
dt { color:#5b6b80; }
dd { margin:0; font-variant-numeric:tabular-nums; }
.vazio { color:#5b6b80; }
@media (max-width:620px){ body{padding:14px;} table{font-size:13px;} }
"""


def _num(valor: int) -> str:
    """Formata inteiro no padrao brasileiro: 20.000.000."""
    return f"{valor:,}".replace(",", ".")


def _pagina(dados: dict | None) -> str:
    if dados is None:
        corpo = ('<section><p class="vazio">Nenhuma medicao encontrada ainda. '
                 'Rode <code>python benchmark.py</code> para gerar '
                 '<code>resultados.json</code>.</p></section>')
        return f"<!doctype html><meta charset='utf-8'><title>Medicao</title><style>{ESTILO}</style><main><h1>Contagem paralela de primos</h1>{corpo}</main>"

    m = dados["maquina"]
    e = dados["entrada"]
    v = dados["verificacao"]

    linhas = []
    for r in dados["medicoes"]:
        amd = f"{r['amdahl_previsto']:.2f}x" if r.get("amdahl_previsto") else "&mdash;"
        pm = f"{r['p_medido']:.3f}" if r.get("p_medido") is not None else "&mdash;"
        classe = "ok" if r["correto"] else "falha"
        marca = "confere" if r["correto"] else "DIVERGE"
        linhas.append(
            f"<tr><td>{html.escape(r['modo'])}</td><td>{r['trabalhadores']}</td>"
            f"<td>{r['mediana']:.2f}s</td><td>{r['speedup']:.2f}x</td>"
            f"<td>{r['eficiencia']:.2f}</td><td>{amd}</td><td>{pm}</td>"
            f"<td class='{classe}'>{marca}</td></tr>"
        )

    return f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Medicao - contagem paralela de primos</title><style>{ESTILO}</style>
<main>
  <h1>Contagem paralela de primos em [2, N]</h1>
  <p class="sub">Sistemas Distribuidos e Paralelos &middot; Etapa 1 &middot;
     medicao gerada em {html.escape(dados['gerado_em'])}</p>

  <section>
    <h2>Ambiente e entrada</h2>
    <dl>
      <dt>Maquina</dt><dd>{html.escape(str(m['sistema']))}</dd>
      <dt>Nucleos</dt><dd>{m['nucleos_fisicos']} fisicos / {m['nucleos_logicos']} logicos</dd>
      <dt>Python</dt><dd>{html.escape(str(m['implementacao']))} {html.escape(str(m['python']))}</dd>
      <dt>Entrada N</dt><dd>{_num(e['n'])}</dd>
      <dt>Bloco</dt><dd>{_num(e['bloco'])} numeros &middot; {e['repeticoes']} execucoes por configuracao</dd>
      <dt>p estimado</dt><dd>{dados['p_estimado']}</dd>
    </dl>
  </section>

  <section>
    <h2>Verificacao independente ({html.escape(v['metodo'])}, {v['segundos']:.2f}s)</h2>
    <dl>
      <dt>Primos</dt><dd>{_num(v['resultado'][0])}</dd>
      <dt>Maior primo</dt><dd>{_num(v['resultado'][1])}</dd>
      <dt>Soma</dt><dd>{_num(v['resultado'][2])}</dd>
    </dl>
  </section>

  <section>
    <h2>Medicoes</h2>
    <table>
      <tr><th>modo</th><th>W</th><th>mediana</th><th>speedup</th>
          <th>eficiencia</th><th>teto Amdahl</th><th>p medido</th><th>resultado</th></tr>
      {''.join(linhas)}
    </table>
  </section>
</main>"""


class Manipulador(BaseHTTPRequestHandler):
    arquivo = ARQUIVO_RESULTADOS

    def _responder(self, codigo: int, tipo: str, corpo: bytes) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _carregar(self) -> dict | None:
        try:
            return json.loads(self.arquivo.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def do_GET(self) -> None:  # noqa: N802 (nome exigido por BaseHTTPRequestHandler)
        rota = self.path.split("?")[0].rstrip("/") or "/"
        if rota == "/saude":
            self._responder(200, "text/plain; charset=utf-8", b"ok")
        elif rota == "/resultados.json":
            dados = self._carregar()
            if dados is None:
                self._responder(404, "application/json", b'{"erro":"sem medicao"}')
            else:
                corpo = json.dumps(dados, indent=2, ensure_ascii=False).encode("utf-8")
                self._responder(200, "application/json; charset=utf-8", corpo)
        elif rota == "/":
            corpo = _pagina(self._carregar()).encode("utf-8")
            self._responder(200, "text/html; charset=utf-8", corpo)
        else:
            self._responder(404, "text/plain; charset=utf-8", b"nao encontrado")

    def log_message(self, formato: str, *args) -> None:
        print(f"{self.address_string()} - {formato % args}")


def _principal() -> None:
    ap = argparse.ArgumentParser(description="Servico HTTP de status da medicao.")
    ap.add_argument("--porta", type=int, default=8000)
    ap.add_argument("--endereco", default="0.0.0.0")
    ap.add_argument("--arquivo", default=str(ARQUIVO_RESULTADOS))
    args = ap.parse_args()

    Manipulador.arquivo = Path(args.arquivo)
    servidor = ThreadingHTTPServer((args.endereco, args.porta), Manipulador)
    print(f"servindo em http://{args.endereco}:{args.porta}/  "
          f"(lendo {Manipulador.arquivo.resolve()})")
    print("Ctrl+C para parar")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nencerrando")
        servidor.server_close()


if __name__ == "__main__":
    _principal()
