"""Protocolo de medicao: tempo sequencial, tempo paralelo, speedup e Amdahl.

Roda as duas versoes na MESMA maquina, com a MESMA entrada, mais de uma vez
cada (a ficha exige as tres coisas), confere o resultado contra uma
verificacao independente (Crivo de Eratostenes) e grava tudo em JSON.

Alem do speedup medido, calcula duas leituras da lei de Amdahl:

  - TETO PREVISTO: S = 1 / ((1 - p) + p/n), com o p estimado pela equipe.
  - FRACAO SERIAL MEDIDA (metrica de Karp-Flatt): a partir do speedup que
    realmente aconteceu, descobre qual fracao serial 'e' explica aquele
    numero:  e = (1/S - 1/n) / (1 - 1/n),  e entao p_medido = 1 - e.
    Se p_medido cai conforme n cresce, a perda nao e so a parte serial:
    e custo que cresce com o numero de trabalhadores (criar processos,
    passar blocos pela fila, disputar a trava).

Uso tipico:
    python benchmark.py -n 20000000 -w 2,4,8 -r 3 --p-estimado 0.97
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import paralelo_processos
import paralelo_threads
import sequencial
from primos import Resumo, crivo_ate

# Ancorado no arquivo, e nao no diretorio atual: assim `python src/benchmark.py`
# roda da raiz do repositorio e grava em resultados/ do PROPRIO projeto.
RAIZ = Path(__file__).resolve().parent.parent
SAIDA_PADRAO = RAIZ / "resultados" / "resultados.json"


# ----------------------------------------------------------------- maquina

def nucleos_fisicos() -> int | None:
    """Melhor esforco para descobrir nucleos FISICOS (nao logicos).

    Em trabalho limitado por CPU, o que escala e o numero de nucleos
    fisicos; hyper-threading rende bem menos que um nucleo inteiro.
    """
    try:
        if sys.platform == "win32":
            saida = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Processor | "
                 "Measure-Object -Property NumberOfCores -Sum).Sum"],
                capture_output=True, text=True, timeout=25,
            ).stdout.strip()
            return int(saida) if saida.isdigit() else None
        if sys.platform.startswith("linux"):
            pares = set()
            fisico = nucleo = None
            for linha in Path("/proc/cpuinfo").read_text().splitlines():
                if linha.startswith("physical id"):
                    fisico = linha.split(":")[1].strip()
                elif linha.startswith("core id"):
                    nucleo = linha.split(":")[1].strip()
                    if fisico is not None:
                        pares.add((fisico, nucleo))
            return len(pares) or None
    except Exception:
        return None
    return None


def descrever_maquina() -> dict:
    return {
        "sistema": f"{platform.system()} {platform.release()}",
        "processador": platform.processor() or "desconhecido",
        "nucleos_logicos": os.cpu_count(),
        "nucleos_fisicos": nucleos_fisicos(),
        "python": platform.python_version(),
        "implementacao": platform.python_implementation(),
    }


# ------------------------------------------------------------------ medida

def _cronometrar(funcao, repeticoes: int) -> tuple[list[float], Resumo]:
    """Roda `repeticoes` vezes e devolve (tempos, resultado da ultima)."""
    tempos: list[float] = []
    resultado = None
    for _ in range(repeticoes):
        t0 = time.perf_counter()
        resultado = funcao()
        tempos.append(time.perf_counter() - t0)
    return tempos, resultado


def amdahl(p: float, n: int) -> float:
    """Teto de speedup para fracao paralelizavel p e n trabalhadores."""
    return 1.0 / ((1.0 - p) + p / n)


def karp_flatt(speedup: float, n: int) -> float | None:
    """Fracao serial medida experimentalmente. Retorna None para n = 1."""
    if n <= 1:
        return None
    return (1.0 / speedup - 1.0 / n) / (1.0 - 1.0 / n)


def _fmt(segundos: float) -> str:
    if segundos >= 60:
        return f"{segundos:7.2f}s ({int(segundos // 60)}m{segundos % 60:04.1f}s)"
    return f"{segundos:7.2f}s"


# ------------------------------------------------------------------ script

def _principal() -> None:
    # Sem isto, redirecionar a saida para arquivo (`benchmark.py > log.txt`)
    # guarda tudo em buffer e o progresso so aparece no fim -- e a medicao
    # leva minutos. Com line_buffering, cada linha sai na hora.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):       # pragma: no cover
        pass

    ap = argparse.ArgumentParser(description="Medicao de desempenho e speedup.")
    ap.add_argument("-n", type=int, default=20_000_000, help="limite superior N")
    ap.add_argument("-w", "--trabalhadores", default="2,4,8",
                    help="lista de quantidades de trabalhadores, ex: 2,4,8")
    ap.add_argument("-r", "--repeticoes", type=int, default=3)
    ap.add_argument("-b", "--bloco", type=int, default=paralelo_processos.TAMANHO_BLOCO_PADRAO)
    ap.add_argument("--p-estimado", type=float, default=0.97,
                    help="fracao do trabalho que a equipe estima ser paralelizavel")
    ap.add_argument("--com-threads", action="store_true",
                    help="mede tambem a versao com threads (evidencia da GIL)")
    ap.add_argument("--threads-w", default="4",
                    help="quantidades de threads a medir (a evidencia da GIL nao "
                         "precisa varrer a lista inteira)")
    ap.add_argument("--saida", default=str(SAIDA_PADRAO))
    args = ap.parse_args()

    lista_w = [int(x) for x in args.trabalhadores.split(",") if x.strip()]
    if args.repeticoes < 1:
        raise SystemExit("--repeticoes precisa ser >= 1 (a lauda pede mais de uma medicao)")
    if not lista_w:
        raise SystemExit("-w precisa listar ao menos uma quantidade de trabalhadores")
    if min(lista_w) < 1:
        raise SystemExit("-w so aceita quantidades >= 1")

    maquina = descrever_maquina()
    fisicos = maquina["nucleos_fisicos"] or "?"

    print("=" * 78)
    print("MEDICAO DE DESEMPENHO - contagem de primos em [2, N]")
    print("=" * 78)
    print(f"maquina  : {maquina['sistema']} | {maquina['processador']}")
    print(f"nucleos  : {fisicos} fisicos / {maquina['nucleos_logicos']} logicos")
    print(f"python   : {maquina['implementacao']} {maquina['python']}")
    print(f"entrada  : N = {args.n:,}".replace(",", "."))
    print(f"protocolo: {args.repeticoes} execucoes por configuracao, bloco = {args.bloco}")
    print()

    # 1) Verificacao independente (algoritmo diferente, roda em segundos).
    t0 = time.perf_counter()
    referencia = crivo_ate(args.n)
    t_crivo = time.perf_counter() - t0
    print(f"[verificacao] Crivo de Eratostenes em {t_crivo:.2f}s")
    print(f"              primos={referencia.contagem:,}".replace(",", ".")
          + f"  maior={referencia.maior_primo}  soma={referencia.soma}")
    print()

    registros = []

    # 2) Linha de base sequencial.
    print("[sequencial] medindo...", flush=True)
    tempos_seq, res_seq = _cronometrar(lambda: sequencial.executar(args.n), args.repeticoes)
    t_seq = statistics.median(tempos_seq)
    ok_seq = res_seq.como_tupla() == referencia.como_tupla()
    print(f"             execucoes: {[f'{t:.2f}s' for t in tempos_seq]}")
    print(f"             mediana  : {_fmt(t_seq)}   resultado {'CONFERE' if ok_seq else 'DIVERGE'}")
    print()

    registros.append({
        "modo": "sequencial", "trabalhadores": 1, "tempos": tempos_seq,
        "mediana": t_seq, "speedup": 1.0, "eficiencia": 1.0,
        "resultado": res_seq.como_tupla(), "correto": ok_seq,
    })

    # 3) Versao paralela com processos.
    for w in lista_w:
        print(f"[processos W={w}] medindo...", flush=True)
        tempos, res = _cronometrar(
            lambda w=w: paralelo_processos.executar(args.n, w, args.bloco, True),
            args.repeticoes,
        )
        t_par = statistics.median(tempos)
        speedup = t_seq / t_par
        e = karp_flatt(speedup, w)
        ok = res.como_tupla() == referencia.como_tupla()
        print(f"                 execucoes: {[f'{t:.2f}s' for t in tempos]}")
        print(f"                 mediana  : {_fmt(t_par)}   resultado "
              f"{'CONFERE' if ok else 'DIVERGE'}")
        print(f"                 speedup  : {speedup:.2f}x   "
              f"teto Amdahl(p={args.p_estimado}) = {amdahl(args.p_estimado, w):.2f}x")
        print()
        registros.append({
            "modo": "processos", "trabalhadores": w, "tempos": tempos,
            "mediana": t_par, "speedup": speedup, "eficiencia": speedup / w,
            "amdahl_previsto": amdahl(args.p_estimado, w),
            "fracao_serial_medida": e,
            "p_medido": (1 - e) if e is not None else None,
            "resultado": res.como_tupla(), "correto": ok,
        })

    # 4) Threads: evidencia de que a GIL impede ganho em trabalho de CPU.
    if args.com_threads:
        for w in [int(x) for x in args.threads_w.split(",") if x.strip()]:
            print(f"[threads T={w}] medindo...", flush=True)
            tempos, res = _cronometrar(
                lambda w=w: paralelo_threads.executar(args.n, w, args.bloco, True),
                args.repeticoes,
            )
            t_thr = statistics.median(tempos)
            speedup = t_seq / t_thr
            ok = res.como_tupla() == referencia.como_tupla()
            print(f"                execucoes: {[f'{t:.2f}s' for t in tempos]}")
            print(f"                mediana  : {_fmt(t_thr)}   speedup = {speedup:.2f}x   "
                  f"resultado {'CONFERE' if ok else 'DIVERGE'}")
            print()
            registros.append({
                "modo": "threads", "trabalhadores": w, "tempos": tempos,
                "mediana": t_thr, "speedup": speedup, "eficiencia": speedup / w,
                "resultado": res.como_tupla(), "correto": ok,
            })

    # 5) Tabela final.
    print("=" * 78)
    print("RESUMO")
    print("=" * 78)
    print(f"{'modo':<12}{'W':>3}{'mediana':>12}{'speedup':>10}{'efic.':>8}"
          f"{'Amdahl':>9}{'p medido':>10}{'ok':>5}")
    print("-" * 78)
    for r in registros:
        amd = f"{r['amdahl_previsto']:.2f}x" if r.get("amdahl_previsto") else "-"
        pm = f"{r['p_medido']:.3f}" if r.get("p_medido") is not None else "-"
        print(f"{r['modo']:<12}{r['trabalhadores']:>3}{r['mediana']:>11.2f}s"
              f"{r['speedup']:>9.2f}x{r['eficiencia']:>8.2f}{amd:>9}{pm:>10}"
              f"{'sim' if r['correto'] else 'NAO':>5}")
    print("-" * 78)
    todos_corretos = all(r["correto"] for r in registros)
    print(f"Todas as versoes produziram o mesmo resultado da verificacao "
          f"independente: {'SIM' if todos_corretos else 'NAO'}")

    # 6) Persistencia (o servidor de status le este arquivo).
    relatorio = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "maquina": maquina,
        "entrada": {"n": args.n, "bloco": args.bloco, "repeticoes": args.repeticoes},
        "p_estimado": args.p_estimado,
        "verificacao": {
            "metodo": "Crivo de Eratostenes",
            "segundos": t_crivo,
            "resultado": referencia.como_tupla(),
        },
        "medicoes": registros,
        "todos_corretos": todos_corretos,
    }
    destino = Path(args.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(relatorio, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResultados gravados em {destino.resolve()}")


if __name__ == "__main__":
    mp.freeze_support()
    _principal()
