"""Versao SEQUENCIAL de referencia.

Um unico fluxo percorre [2, N] e resume o intervalo. E a linha de base:
o tempo desta versao, medido na mesma maquina e com a mesma entrada, e o
numerador do speedup. Tambem e a "resposta certa" contra a qual a versao
paralela e conferida.
"""

from __future__ import annotations

import argparse
import time

from primos import Resumo, resumo_intervalo


def executar(n: int) -> Resumo:
    """Resume [2, N] num unico fluxo."""
    return resumo_intervalo(2, n + 1)


def _principal() -> None:
    ap = argparse.ArgumentParser(description="Contagem sequencial de primos.")
    ap.add_argument("-n", type=int, default=20_000_000, help="limite superior N")
    args = ap.parse_args()

    t = time.perf_counter()
    r = executar(args.n)
    dt = time.perf_counter() - t

    print(f"[sequencial] N={args.n}")
    print(f"  primos={r.contagem}  maior={r.maior_primo}  soma={r.soma}")
    print(f"  tempo={dt:.3f}s")


if __name__ == "__main__":
    _principal()
