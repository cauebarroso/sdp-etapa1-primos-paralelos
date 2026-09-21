"""Versao PARALELA com processos (multiprocessing) + trava explicita.

Por que processos, e nao threads: o trabalho e limitado por CPU (divisao
sucessiva em Python puro). Em CPython a GIL serializa bytecode, entao
threads nao ganham tempo de processador em trabalho de CPU (ver
paralelo_threads.py, que mede speedup ~ 1). Processos tem cada um seu
interpretador e sua GIL, e rodam de verdade em nucleos diferentes.

Estrutura (importante para a nota de sincronizacao):

  - Estado compartilhado escrito por mais de um fluxo:
        contagem, maior, soma  (multiprocessing.RawValue em memoria
        compartilhada) -- os tres campos do Resumo global.

  - Secao critica (o MENOR trecho indivisivel):
        o "dobrar" do parcial local no estado global -- tres
        leitura-modificacao-escrita. So isso fica dentro da trava.

  - O trabalho PESADO (resumo_intervalo, o laco de primalidade) fica
    FORA da trava. Por isso a versao e paralela de verdade: os nucleos
    passam quase todo o tempo testando primos em paralelo, e disputam a
    trava so por alguns microssegundos por bloco.

  - Primitiva: multiprocessing.Lock (uma trava mutex).

Divisao do trabalho: [2, N] e quebrado em muitos blocos pequenos numa
fila (T >> W). Os trabalhadores puxam blocos da fila (balanceamento
dinamico), o que compensa o custo desigual entre blocos -- testar primos
grandes custa mais que testar primos pequenos.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import time

from primos import Resumo, gerar_tarefas, resumo_intervalo

TAMANHO_BLOCO_PADRAO = 10_000


def _dobrar_no_estado(contagem, maior, soma, local: Resumo) -> None:
    """Secao critica: funde o parcial local no estado compartilhado.

    Cada linha e uma leitura-modificacao-escrita nao atomica sobre um
    RawValue. Se dois processos fizerem isso ao mesmo tempo sem a trava,
    uma das somas se perde (condicao de corrida). E o menor trecho que
    precisa ser indivisivel.
    """
    contagem.value += local.contagem
    if local.maior_primo > maior.value:
        maior.value = local.maior_primo
    soma.value += local.soma


def trabalhador(fila, contagem, maior, soma, trava, usar_trava: bool) -> None:
    """Loop do trabalhador: puxa blocos da fila ate encontrar a sentinela."""
    while True:
        tarefa = fila.get()
        if tarefa is None:            # sentinela: acabou o trabalho
            return
        inicio, fim = tarefa
        # --- trabalho pesado, FORA da trava (roda em paralelo de verdade) ---
        local = resumo_intervalo(inicio, fim)
        # --- secao critica: curta, protegida pela trava ---
        if usar_trava:
            with trava:
                _dobrar_no_estado(contagem, maior, soma, local)
        else:
            # modo de demonstracao da corrida (--sem-trava): SEM protecao
            _dobrar_no_estado(contagem, maior, soma, local)


def executar(
    n: int,
    num_trabalhadores: int,
    tamanho_bloco: int = TAMANHO_BLOCO_PADRAO,
    usar_trava: bool = True,
) -> Resumo:
    """Executa a contagem paralela e devolve o Resumo global.

    Mede tudo o que a versao paralela precisa fazer: criar processos,
    distribuir blocos pela fila e fundir os parciais sob a trava.
    """
    if num_trabalhadores < 1:
        raise ValueError(f"precisa de ao menos 1 trabalhador (recebi {num_trabalhadores})")

    ctx = mp.get_context("spawn")  # explicito: mesmo comportamento em todo SO

    # Estado compartilhado em memoria (passado aos processos por heranca).
    # 'q' = inteiro de 64 bits com sinal. Para N ate ~1e9 a soma de primos
    # cabe folgada em 64 bits.
    contagem = ctx.RawValue("q", 0)
    maior = ctx.RawValue("q", 0)
    soma = ctx.RawValue("q", 0)
    trava = ctx.Lock()

    fila = ctx.Queue()
    for tarefa in gerar_tarefas(n, tamanho_bloco):
        fila.put(tarefa)
    for _ in range(num_trabalhadores):
        fila.put(None)                # uma sentinela por trabalhador

    processos = [
        ctx.Process(
            target=trabalhador,
            args=(fila, contagem, maior, soma, trava, usar_trava),
        )
        for _ in range(num_trabalhadores)
    ]
    for p in processos:
        p.start()
    for p in processos:
        p.join()

    return Resumo(contagem.value, maior.value, soma.value)


def _principal() -> None:
    ap = argparse.ArgumentParser(description="Contagem paralela de primos (processos).")
    ap.add_argument("-n", type=int, default=20_000_000, help="limite superior N")
    ap.add_argument("-w", "--trabalhadores", type=int, default=mp.cpu_count())
    ap.add_argument("-b", "--bloco", type=int, default=TAMANHO_BLOCO_PADRAO)
    ap.add_argument(
        "--sem-trava",
        action="store_true",
        help="NAO usa a trava: demonstra a condicao de corrida (resultado instavel)",
    )
    args = ap.parse_args()

    t = time.perf_counter()
    r = executar(args.n, args.trabalhadores, args.bloco, usar_trava=not args.sem_trava)
    dt = time.perf_counter() - t

    modo = "SEM TRAVA (com corrida)" if args.sem_trava else "com trava"
    print(f"[processos {modo}] N={args.n}  W={args.trabalhadores}  bloco={args.bloco}")
    print(f"  primos={r.contagem}  maior={r.maior_primo}  soma={r.soma}")
    print(f"  tempo={dt:.3f}s")


if __name__ == "__main__":
    _principal()
