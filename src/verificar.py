"""Prova de correcao: a versao paralela produz o mesmo que a sequencial.

A lauda exige "um resultado verificavel, para provar que a versao paralela
produz o mesmo que a sequencial" e a demonstracao precisa "rodar a aplicacao
mais de uma vez com a mesma entrada e mostrar o resultado estavel".

Este script faz as tres conferencias de uma vez:

  1. CRIVO (verificacao independente): calcula a resposta por um algoritmo
     diferente -- Crivo de Eratostenes. Se batesse so sequencial x paralelo,
     um erro no teste de primalidade passaria despercebido nos dois.
  2. SEQUENCIAL: a linha de base.
  3. PARALELA, repetida: roda R vezes com a MESMA entrada. Se houvesse
     condicao de corrida, a contagem mudaria de uma execucao para outra.
     Todas iguais = estado compartilhado protegido corretamente.

Sai com codigo 0 se tudo confere, 1 se algo divergir (da para usar em CI).
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import sys
import time

import paralelo_processos
import sequencial
from primos import crivo_ate


def _principal() -> int:
    # Para que o progresso apareca linha a linha mesmo com a saida
    # redirecionada ou passando por `tee` (ver benchmark.py).
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):       # pragma: no cover
        pass

    ap = argparse.ArgumentParser(description="Verifica correcao e estabilidade do resultado.")
    ap.add_argument("-n", type=int, default=5_000_000, help="limite superior N")
    ap.add_argument("-w", "--trabalhadores", type=int, default=mp.cpu_count())
    ap.add_argument("-r", "--repeticoes", type=int, default=5,
                    help="quantas vezes repetir a versao paralela")
    ap.add_argument("-b", "--bloco", type=int, default=paralelo_processos.TAMANHO_BLOCO_PADRAO)
    ap.add_argument("--pular-sequencial", action="store_true",
                    help="pula a linha de base sequencial (util quando N e grande)")
    args = ap.parse_args()

    print("=" * 70)
    print(f"VERIFICACAO  N = {args.n:,}".replace(",", ".")
          + f"  |  {args.trabalhadores} trabalhadores  |  {args.repeticoes} repeticoes")
    print("=" * 70)

    # 1) Verificacao independente -----------------------------------------
    t0 = time.perf_counter()
    referencia = crivo_ate(args.n)
    print(f"\n[1] Crivo de Eratostenes (algoritmo independente)  {time.perf_counter() - t0:.2f}s")
    print(f"    primos={referencia.contagem}  maior={referencia.maior_primo}  "
          f"soma={referencia.soma}")

    falhas = 0

    # 2) Sequencial --------------------------------------------------------
    if args.pular_sequencial:
        print("\n[2] Sequencial: pulado (--pular-sequencial)")
    else:
        t0 = time.perf_counter()
        res_seq = sequencial.executar(args.n)
        dt = time.perf_counter() - t0
        igual = res_seq.como_tupla() == referencia.como_tupla()
        falhas += 0 if igual else 1
        print(f"\n[2] Sequencial  {dt:.2f}s")
        print(f"    primos={res_seq.contagem}  maior={res_seq.maior_primo}  "
              f"soma={res_seq.soma}   {'CONFERE' if igual else 'DIVERGE'}")

    # 3) Paralela, repetida ------------------------------------------------
    print(f"\n[3] Paralela com processos, {args.repeticoes} execucoes com a mesma entrada")
    print(f"    {'#':>3}  {'tempo':>8}  {'primos':>10}  {'maior':>10}  "
          f"{'soma':>16}  situacao")
    vistos = set()
    for i in range(args.repeticoes):
        t0 = time.perf_counter()
        r = paralelo_processos.executar(args.n, args.trabalhadores, args.bloco, True)
        dt = time.perf_counter() - t0
        igual = r.como_tupla() == referencia.como_tupla()
        falhas += 0 if igual else 1
        vistos.add(r.como_tupla())
        print(f"    {i + 1:>3}  {dt:>7.2f}s  {r.contagem:>10}  {r.maior_primo:>10}  "
              f"{r.soma:>16}  {'CONFERE' if igual else 'DIVERGE'}")

    estavel = len(vistos) == 1
    print("\n" + "=" * 70)
    print(f"Resultados distintos entre as {args.repeticoes} execucoes paralelas: "
          f"{len(vistos)}  ->  {'ESTAVEL' if estavel else 'INSTAVEL (ha corrida!)'}")
    print(f"Conferencia contra o crivo e o sequencial: "
          f"{'TUDO CONFERE' if falhas == 0 else f'{falhas} DIVERGENCIA(S)'}")
    print("=" * 70)

    return 0 if (falhas == 0 and estavel) else 1


if __name__ == "__main__":
    mp.freeze_support()
    sys.exit(_principal())
