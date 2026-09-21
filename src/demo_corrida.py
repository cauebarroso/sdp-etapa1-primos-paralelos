"""Demonstracao direta da condicao de corrida e da trava que a corrige.

Este experimento e isolado do calculo de primos de proposito: ele torna a
corrida VISIVEL e REPETIVEL, para a parte "como a equipe vai demonstrar que
o resultado ficou estavel" da apresentacao.

Ideia: K processos incrementam INCREMENTOS vezes, cada um, um mesmo contador
em memoria compartilhada.

  - Resultado correto  = K * INCREMENTOS  (sempre, deterministico).
  - SEM trava: contador.value += 1 e uma leitura-modificacao-escrita nao
    atomica. Como sao processos (sem GIL entre eles), rodam de verdade em
    paralelo, se interpolam e PERDEM atualizacoes -> total final MENOR que
    o esperado, e diferente a cada execucao (instavel).
  - COM trava: o incremento vira indivisivel -> total final EXATO em toda
    execucao (estavel).

Rode com --repeticoes 5 para ver que sem trava o numero balanca e com trava
ele nao muda.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp


def _incrementador(contador, trava, incrementos: int, usar_trava: bool) -> None:
    for _ in range(incrementos):
        if usar_trava:
            with trava:
                contador.value += 1        # indivisivel: nada se perde
        else:
            contador.value += 1            # corrida: leitura+escrita separaveis


def rodar(num_processos: int, incrementos: int, usar_trava: bool) -> tuple[int, int]:
    """Retorna (obtido, esperado)."""
    ctx = mp.get_context("spawn")
    contador = ctx.RawValue("q", 0)
    trava = ctx.Lock()
    processos = [
        ctx.Process(target=_incrementador, args=(contador, trava, incrementos, usar_trava))
        for _ in range(num_processos)
    ]
    for p in processos:
        p.start()
    for p in processos:
        p.join()
    return contador.value, num_processos * incrementos


def _principal() -> None:
    ap = argparse.ArgumentParser(description="Demonstra corrida vs. trava.")
    ap.add_argument("-p", "--processos", type=int, default=mp.cpu_count())
    ap.add_argument("-i", "--incrementos", type=int, default=200_000)
    ap.add_argument("-r", "--repeticoes", type=int, default=5)
    args = ap.parse_args()

    print(f"{args.processos} processos x {args.incrementos} incrementos "
          f"= {args.processos * args.incrementos} esperado\n")

    print("SEM TRAVA (esperamos numeros errados e instaveis):")
    for i in range(args.repeticoes):
        obtido, esperado = rodar(args.processos, args.incrementos, usar_trava=False)
        perdidas = esperado - obtido
        print(f"  execucao {i + 1}: obtido={obtido:>10}  perdidas={perdidas:>9}  "
              f"{'OK' if perdidas == 0 else 'ERRADO'}")

    print("\nCOM TRAVA (esperamos o numero exato, toda vez):")
    for i in range(args.repeticoes):
        obtido, esperado = rodar(args.processos, args.incrementos, usar_trava=True)
        perdidas = esperado - obtido
        print(f"  execucao {i + 1}: obtido={obtido:>10}  perdidas={perdidas:>9}  "
              f"{'OK' if perdidas == 0 else 'ERRADO'}")


if __name__ == "__main__":
    _principal()
