"""Registro de eventos com carimbo logico de Lamport.

A ficha pede: "se a aplicacao tiver mais de um processo trocando mensagem,
descreva o que cada registro de evento vai conter (quem, o que, carimbo
logico, sobre o que)".

A nossa aplicacao TEM troca de mensagem: o coordenador envia blocos de
trabalho aos trabalhadores por uma fila (multiprocessing.Queue), e os
trabalhadores devolvem registros de evento por outra fila. Processos
diferentes nao compartilham relogio de parede confiavel, entao usamos o
carimbo logico de Lamport para ordenar os eventos por causalidade.

Regras de Lamport implementadas aqui:
  1. evento local        -> L = L + 1
  2. envio de mensagem   -> L = L + 1, e a mensagem viaja com L
  3. recebimento         -> L = max(L, L_da_mensagem) + 1

Cada registro de evento contem os quatro campos pedidos:
  quem    -> identificador do processo (C0 = coordenador, T1..Tn)
  o_que   -> tipo do evento (ENVIA_BLOCO, RECEBE_BLOCO, CALCULA,
             ENTRA_SC, SAI_SC)
  carimbo -> o relogio logico de Lamport no instante do evento
  sobre   -> o recurso do evento (o bloco [inicio,fim) ou o estado global)

Este modulo roda com um N pequeno de proposito: ele serve para mostrar a
ordenacao causal, nao para medir desempenho (a fila de eventos custa tempo
e ficaria fora da medicao de speedup).
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
from pathlib import Path

from primos import Resumo, gerar_tarefas, resumo_intervalo

CAMPOS = ("carimbo", "quem", "o_que", "sobre")

# Ancorado no arquivo, nao no diretorio atual (ver benchmark.py).
RAIZ = Path(__file__).resolve().parent.parent
SAIDA_PADRAO = RAIZ / "resultados" / "eventos.log"


def _registrar(fila_eventos, quem: str, carimbo: int, o_que: str, sobre: str) -> None:
    fila_eventos.put((carimbo, quem, o_que, sobre))


def _trabalhador(id_trab, fila_tarefas, fila_eventos, contagem, maior, soma, trava) -> None:
    quem = f"T{id_trab}"
    relogio = 0
    while True:
        item = fila_tarefas.get()
        if item is None:
            fila_eventos.put(None)            # avisa o coordenador que terminou
            return
        carimbo_msg, (inicio, fim) = item

        # regra 3: recebimento
        relogio = max(relogio, carimbo_msg) + 1
        _registrar(fila_eventos, quem, relogio, "RECEBE_BLOCO", f"[{inicio},{fim})")

        local = resumo_intervalo(inicio, fim)  # trabalho pesado, fora da secao critica

        # regra 1: evento local
        relogio += 1
        _registrar(fila_eventos, quem, relogio, "CALCULA", f"[{inicio},{fim}) -> {local.contagem} primos")

        with trava:                            # secao critica
            relogio += 1
            _registrar(fila_eventos, quem, relogio, "ENTRA_SC", "estado_global")
            contagem.value += local.contagem
            if local.maior_primo > maior.value:
                maior.value = local.maior_primo
            soma.value += local.soma
            relogio += 1
            _registrar(fila_eventos, quem, relogio, "SAI_SC", f"contagem={contagem.value}")


def executar(n: int, num_trabalhadores: int, tamanho_bloco: int
             ) -> tuple[Resumo, list[tuple[int, str, str, str]]]:
    """Roda a versao instrumentada e devolve (resultado, eventos ordenados)."""
    ctx = mp.get_context("spawn")
    contagem = ctx.RawValue("q", 0)
    maior = ctx.RawValue("q", 0)
    soma = ctx.RawValue("q", 0)
    trava = ctx.Lock()
    fila_tarefas = ctx.Queue()
    fila_eventos = ctx.Queue()

    eventos: list[tuple[int, str, str, str]] = []

    # Coordenador: cada envio e um evento de envio (regra 2).
    relogio_coord = 0
    for tarefa in gerar_tarefas(n, tamanho_bloco):
        relogio_coord += 1
        eventos.append((relogio_coord, "C0", "ENVIA_BLOCO", f"[{tarefa[0]},{tarefa[1]})"))
        fila_tarefas.put((relogio_coord, tarefa))
    for _ in range(num_trabalhadores):
        fila_tarefas.put(None)

    processos = [
        ctx.Process(
            target=_trabalhador,
            args=(i + 1, fila_tarefas, fila_eventos, contagem, maior, soma, trava),
        )
        for i in range(num_trabalhadores)
    ]
    for p in processos:
        p.start()

    # Drenamos a fila de eventos ENQUANTO os trabalhadores rodam. Se
    # esperassemos o join primeiro, um trabalhador poderia bloquear ao
    # escrever numa fila cheia e o programa travaria.
    terminados = 0
    while terminados < num_trabalhadores:
        ev = fila_eventos.get()
        if ev is None:
            terminados += 1
        else:
            eventos.append(ev)

    for p in processos:
        p.join()

    # Ordem causal: carimbo crescente; empate desfeito pelo nome do processo
    # (Lamport nao ordena eventos concorrentes -- o desempate e so para
    # tornar a saida deterministica).
    eventos.sort(key=lambda e: (e[0], e[1]))
    return Resumo(contagem.value, maior.value, soma.value), eventos


def _principal() -> None:
    ap = argparse.ArgumentParser(description="Registro de eventos com relogio de Lamport.")
    ap.add_argument("-n", type=int, default=200_000, help="limite superior N (pequeno de proposito)")
    ap.add_argument("-w", "--trabalhadores", type=int, default=4)
    ap.add_argument("-b", "--bloco", type=int, default=50_000)
    ap.add_argument("-s", "--saida", default=str(SAIDA_PADRAO))
    ap.add_argument("--mostrar", type=int, default=20, help="quantas linhas imprimir na tela")
    args = ap.parse_args()

    resultado, eventos = executar(args.n, args.trabalhadores, args.bloco)

    destino = Path(args.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8") as f:
        f.write(f"{'carimbo':>8} | {'quem':<4} | {'o_que':<13} | sobre\n")
        f.write("-" * 78 + "\n")
        for carimbo, quem, o_que, sobre in eventos:
            f.write(f"{carimbo:>8} | {quem:<4} | {o_que:<13} | {sobre}\n")

    print(f"N={args.n}  trabalhadores={args.trabalhadores}  blocos de {args.bloco}")
    print(f"resultado: primos={resultado.contagem}  maior={resultado.maior_primo}")
    print(f"{len(eventos)} eventos gravados em {destino.resolve()}\n")
    print(f"{'carimbo':>8} | {'quem':<4} | {'o_que':<13} | sobre")
    print("-" * 78)
    for carimbo, quem, o_que, sobre in eventos[: args.mostrar]:
        print(f"{carimbo:>8} | {quem:<4} | {o_que:<13} | {sobre}")
    if len(eventos) > args.mostrar:
        print(f"... (+{len(eventos) - args.mostrar} eventos no arquivo)")


if __name__ == "__main__":
    _principal()
