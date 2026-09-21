"""Versao com THREADS -- existe para PROVAR que threads nao servem aqui.

Mesmo algoritmo da versao de processos, mas com threading no lugar de
multiprocessing. Como o trabalho e limitado por CPU e roda em Python puro,
a GIL de CPython impede que duas threads executem bytecode ao mesmo tempo.
O resultado esperado e speedup ~ 1 (as vezes < 1, por causa do custo de
troca de contexto e da disputa pela trava).

Este arquivo NAO e a solucao paralela do projeto; e a evidencia que
justifica a escolha por PROCESSOS. Rodar as duas versoes lado a lado
mostra, com numero medido, por que a natureza do trabalho (CPU, e nao
espera) obriga a usar processos em CPython.

O estado compartilhado aqui sao tres inteiros comuns de Python, guardados
num objeto e protegidos por um threading.Lock -- a mesma ideia de secao
critica, so que dentro de um unico processo.
"""

from __future__ import annotations

import argparse
import queue
import threading
import time

from primos import Resumo, gerar_tarefas, resumo_intervalo

TAMANHO_BLOCO_PADRAO = 10_000


class EstadoCompartilhado:
    """Estado escrito por varias threads, protegido por um Lock."""

    def __init__(self) -> None:
        self.contagem = 0
        self.maior = 0
        self.soma = 0
        self.trava = threading.Lock()

    def dobrar(self, local: Resumo, usar_trava: bool) -> None:
        if usar_trava:
            with self.trava:                 # secao critica
                self._aplicar(local)
        else:
            self._aplicar(local)

    def _aplicar(self, local: Resumo) -> None:
        self.contagem += local.contagem
        if local.maior_primo > self.maior:
            self.maior = local.maior_primo
        self.soma += local.soma


def _trabalhador(fila: "queue.Queue", estado: EstadoCompartilhado, usar_trava: bool) -> None:
    while True:
        tarefa = fila.get()
        if tarefa is None:
            fila.task_done()
            return
        inicio, fim = tarefa
        local = resumo_intervalo(inicio, fim)   # trabalho pesado (serializado pela GIL)
        estado.dobrar(local, usar_trava)
        fila.task_done()


def executar(
    n: int,
    num_threads: int,
    tamanho_bloco: int = TAMANHO_BLOCO_PADRAO,
    usar_trava: bool = True,
) -> Resumo:
    estado = EstadoCompartilhado()
    fila: "queue.Queue" = queue.Queue()
    for tarefa in gerar_tarefas(n, tamanho_bloco):
        fila.put(tarefa)
    for _ in range(num_threads):
        fila.put(None)

    threads = [
        threading.Thread(target=_trabalhador, args=(fila, estado, usar_trava))
        for _ in range(num_threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return Resumo(estado.contagem, estado.maior, estado.soma)


def _principal() -> None:
    ap = argparse.ArgumentParser(description="Contagem de primos com threads (demonstra a GIL).")
    ap.add_argument("-n", type=int, default=20_000_000, help="limite superior N")
    ap.add_argument("-w", "--threads", type=int, default=4)
    ap.add_argument("-b", "--bloco", type=int, default=TAMANHO_BLOCO_PADRAO)
    args = ap.parse_args()

    t = time.perf_counter()
    r = executar(args.n, args.threads, args.bloco)
    dt = time.perf_counter() - t

    print(f"[threads] N={args.n}  T={args.threads}  bloco={args.bloco}")
    print(f"  primos={r.contagem}  maior={r.maior_primo}  soma={r.soma}")
    print(f"  tempo={dt:.3f}s")


if __name__ == "__main__":
    _principal()
