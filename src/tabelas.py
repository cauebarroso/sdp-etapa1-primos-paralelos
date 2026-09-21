"""Gera as tabelas do relatorio a partir de resultados.json.

Serve para que os numeros do relatorio sejam sempre os numeros que a
medicao realmente produziu -- inclusive depois de repetir a medicao na
instancia da nuvem:

    python src/tabelas.py --entrada resultados/nuvem/resultados.json

Imprime Markdown pronto para colar na secao "Medicao" do relatorio.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ancorado no arquivo, nao no diretorio atual (ver benchmark.py).
RAIZ = Path(__file__).resolve().parent.parent
ENTRADA_PADRAO = RAIZ / "resultados" / "resultados.json"


def _num(valor: int) -> str:
    """Formata inteiro no padrao brasileiro: 20.000.000.

    Aplicado SO ao numero. Chamar .replace(',', '.') na linha inteira
    tambem trocaria virgulas do texto -- "[2, N]" virava "[2. N]".
    """
    return f"{valor:,}".replace(",", ".")


def _tabela_ambiente(d: dict) -> str:
    m, e = d["maquina"], d["entrada"]
    nf = m.get("nucleos_fisicos") or "?"
    return "\n".join([
        "| Item | Valor |",
        "|---|---|",
        f"| Maquina | {m['sistema']} — {m['processador']} |",
        f"| Nucleos | {nf} fisicos / {m['nucleos_logicos']} logicos |",
        f"| Interpretador | {m['implementacao']} {m['python']} |",
        f"| Entrada fixada | N = {_num(e['n'])} |",
        f"| Bloco (unidade de trabalho) | {_num(e['bloco'])} numeros |",
        f"| Execucoes por configuracao | {e['repeticoes']} |",
        f"| Medicao gerada em | {d['gerado_em']} |",
    ])


def _tabela_medicoes(d: dict) -> str:
    linhas = [
        "| Versao | W | Execucoes (s) | Mediana (s) | Speedup | Eficiencia | Teto Amdahl | p medido | Resultado |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in d["medicoes"]:
        execs = ", ".join(f"{t:.2f}" for t in r["tempos"])
        amd = f"{r['amdahl_previsto']:.2f}x" if r.get("amdahl_previsto") else "—"
        pm = f"{r['p_medido']:.3f}" if r.get("p_medido") is not None else "—"
        linhas.append(
            f"| {r['modo']} | {r['trabalhadores']} | {execs} | {r['mediana']:.2f} | "
            f"{r['speedup']:.2f}x | {r['eficiencia']:.2f} | {amd} | {pm} | "
            f"{'confere' if r['correto'] else 'DIVERGE'} |"
        )
    return "\n".join(linhas)


def _tabela_verificacao(d: dict) -> str:
    v = d["verificacao"]
    c, mx, s = v["resultado"]
    return "\n".join([
        "| Conferencia | Valor |",
        "|---|---|",
        f"| Metodo independente | {v['metodo']} ({v['segundos']:.2f}s) |",
        f"| Primos em [2, N] | {_num(c)} |",
        f"| Maior primo | {_num(mx)} |",
        f"| Soma dos primos (checksum) | {_num(s)} |",
        f"| Todas as versoes conferem | {'SIM' if d['todos_corretos'] else 'NAO'} |",
    ])


def _principal() -> None:
    # O console do Windows usa cp1252 por padrao e engasga com "—".
    # Forcamos UTF-8 na saida para que o Markdown saia intacto ao ser
    # redirecionado para arquivo.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):       # pragma: no cover
        pass

    ap = argparse.ArgumentParser(description="Tabelas em Markdown a partir da medicao.")
    ap.add_argument("--entrada", default=str(ENTRADA_PADRAO))
    args = ap.parse_args()

    caminho = Path(args.entrada)
    if not caminho.exists():
        raise SystemExit(f"nao encontrei {caminho.resolve()} — rode benchmark.py antes.")
    d = json.loads(caminho.read_text(encoding="utf-8"))

    print("### Ambiente e entrada\n")
    print(_tabela_ambiente(d))
    print("\n### Verificacao do resultado\n")
    print(_tabela_verificacao(d))
    print("\n### Tempos, speedup e Amdahl\n")
    print(_tabela_medicoes(d))

    seq = next(r for r in d["medicoes"] if r["modo"] == "sequencial")
    proc = [r for r in d["medicoes"] if r["modo"] == "processos"]
    if proc:
        melhor = max(proc, key=lambda r: r["speedup"])
        print(f"\nMelhor speedup medido: **{melhor['speedup']:.2f}x** com "
              f"W = {melhor['trabalhadores']} "
              f"({seq['mediana']:.1f}s -> {melhor['mediana']:.1f}s).")


if __name__ == "__main__":
    _principal()
