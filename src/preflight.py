"""Verificacao de ambiente -- RODE ISTO NA MAQUINA DA APRESENTACAO.

O codigo foi escrito e medido numa maquina; a apresentacao vai acontecer em
outra. Este script confere, em menos de um minuto, que a outra maquina roda
tudo -- e calcula o N certo para ELA, porque o N depende da velocidade do
processador.

Ele responde a quatro perguntas:

  1. O ambiente serve?      versao do Python, nucleos, modulos importam
  2. O paralelismo funciona? multiprocessing com 'spawn', memoria
                             compartilhada e trava entre processos
  3. O resultado esta certo? sequencial x paralelo x crivo, num N pequeno
  4. Qual N usar aqui?      calibra pela velocidade medida desta maquina

Uso:
    python preflight.py                 # verificacao completa
    python preflight.py --alvo 150      # calibra para ~150 s de sequencial

Saida: codigo 0 se estiver tudo pronto, 1 se algo reprovar.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import platform
import sys
import time

MINIMO_PYTHON = (3, 9)

VERDE = "  [OK] "
VERMELHO = "  [FALHA] "
AVISO = "  [aviso] "


def _titulo(texto: str) -> None:
    print(f"\n{texto}")
    print("-" * 70)


# --------------------------------------------------------------- 1. ambiente

def checar_ambiente() -> list[str]:
    """Versao do Python, nucleos e importacao dos modulos do projeto."""
    problemas: list[str] = []
    _titulo("1. AMBIENTE")

    versao = sys.version_info
    print(f"     Python      : {platform.python_implementation()} "
          f"{platform.python_version()} ({platform.system()} {platform.release()})")
    if versao[:2] < MINIMO_PYTHON:
        problemas.append(
            f"Python {versao.major}.{versao.minor} e antigo demais "
            f"(precisa de {MINIMO_PYTHON[0]}.{MINIMO_PYTHON[1]} ou mais novo)"
        )
        print(VERMELHO + f"versao minima e {MINIMO_PYTHON[0]}.{MINIMO_PYTHON[1]}")
    else:
        print(VERDE + "versao suficiente")

    if platform.python_implementation() != "CPython":
        print(AVISO + "o argumento sobre a GIL vale para CPython; "
                      "em outra implementacao os numeros podem mudar")

    logicos = mp.cpu_count()
    print(f"     Nucleos     : {logicos} logicos")
    if logicos < 2:
        problemas.append("a maquina tem 1 nucleo: nao ha o que paralelizar")
        print(VERMELHO + "um nucleo so: nao da para demonstrar ganho")
    elif logicos < 4:
        print(AVISO + "poucos nucleos: o speedup vai ser modesto (use W=2)")
    else:
        print(VERDE + "nucleos suficientes para demonstrar o ganho")

    try:
        import benchmark, demo_corrida, lamport, paralelo_processos  # noqa: F401
        import paralelo_threads, primos, sequencial, servidor_status  # noqa: F401
        import verificar  # noqa: F401
        print(VERDE + "todos os modulos do projeto importam")
    except Exception as erro:                                   # noqa: BLE001
        problemas.append(f"falha ao importar os modulos: {erro}")
        print(VERMELHO + f"falha ao importar: {erro}")
        print(AVISO + "rode este script de DENTRO da pasta src/")

    return problemas


# ------------------------------------------------------------ 2. paralelismo

def checar_paralelismo() -> list[str]:
    """O que mais costuma quebrar ao trocar de maquina/SO."""
    problemas: list[str] = []
    _titulo("2. PARALELISMO (multiprocessing com 'spawn')")

    try:
        import demo_corrida
        t0 = time.perf_counter()
        obtido, esperado = demo_corrida.rodar(2, 5_000, usar_trava=True)
        dt = time.perf_counter() - t0
        if obtido == esperado:
            print(VERDE + f"processos, memoria compartilhada e trava funcionam ({dt:.1f}s)")
        else:
            problemas.append(f"a trava nao protegeu: {obtido} != {esperado}")
            print(VERMELHO + f"contador deu {obtido}, esperado {esperado}")
    except Exception as erro:                                   # noqa: BLE001
        problemas.append(f"multiprocessing falhou: {erro}")
        print(VERMELHO + f"multiprocessing falhou: {erro}")
        print(AVISO + "em Windows/macOS, o programa precisa ser chamado com "
                      "'python arquivo.py' e nao de dentro de um notebook")

    return problemas


# -------------------------------------------------------------- 3. correcao

def checar_correcao(n_teste: int = 300_000) -> list[str]:
    """Sequencial x paralelo x crivo, num N pequeno e rapido."""
    problemas: list[str] = []
    _titulo(f"3. CORRECAO (N = {n_teste:,})".replace(",", "."))

    try:
        import paralelo_processos
        import sequencial
        from primos import crivo_ate

        referencia = crivo_ate(n_teste).como_tupla()
        res_seq = sequencial.executar(n_teste).como_tupla()
        trabalhadores = min(4, max(2, mp.cpu_count()))
        res_par = paralelo_processos.executar(n_teste, trabalhadores, 10_000, True).como_tupla()

        print(f"     crivo       : {referencia}")
        print(f"     sequencial  : {res_seq}")
        print(f"     paralelo    : {res_par}   (W={trabalhadores})")

        if referencia == res_seq == res_par:
            print(VERDE + "as tres vias concordam")
        else:
            problemas.append("sequencial, paralelo e crivo divergiram")
            print(VERMELHO + "os resultados divergem")
    except Exception as erro:                                   # noqa: BLE001
        problemas.append(f"erro ao verificar a correcao: {erro}")
        print(VERMELHO + f"erro: {erro}")

    return problemas


# ------------------------------------------------------------ 4. calibracao

def calibrar(alvo_segundos: float) -> int | None:
    """Descobre o N que faz a versao sequencial levar ~alvo_segundos AQUI.

    O custo da divisao sucessiva cresce como N^alfa. Em vez de supor alfa,
    medimos dois pontos nesta maquina e ajustamos o expoente -- assim a
    estimativa vale para o processador que vai rodar a apresentacao, e nao
    para o da maquina em que o codigo foi escrito.
    """
    _titulo(f"4. CALIBRACAO (alvo: ~{alvo_segundos:.0f}s de versao sequencial)")

    try:
        from primos import resumo_intervalo
    except Exception as erro:                                   # noqa: BLE001
        print(VERMELHO + f"nao consegui importar primos: {erro}")
        return None

    import math

    # Dois pontos de medicao, BEM separados. Medir so em N pequeno da um
    # expoente baixo demais: o custo por numero cresce com N (divisores
    # maiores, pior aproveitamento de cache), e extrapolar dai subestima.
    # O segundo ponto e escolhido para custar ~12s NESTA maquina, o que
    # mantem a calibracao curta sem sacrificar o alcance.
    n1 = 1_000_000
    t0 = time.perf_counter()
    resumo_intervalo(2, n1 + 1)
    t1 = time.perf_counter() - t0

    if t1 <= 0:
        print(AVISO + "medicao rapida demais para calibrar")
        return None

    n2 = int(n1 * (12.0 / t1) ** (1.0 / 1.4))
    n2 = max(2_000_000, min(n2, 6_000_000))     # limites de bom senso

    t0 = time.perf_counter()
    resumo_intervalo(2, n2 + 1)
    t2 = time.perf_counter() - t0

    print(f"     N = {n1:,}".replace(",", ".") + f"  ->  {t1:.2f}s")
    print(f"     N = {n2:,}".replace(",", ".") + f"  ->  {t2:.2f}s")

    if t1 <= 0 or t2 <= t1:
        print(AVISO + "medicao instavel; feche outros programas e repita")
        return None

    alfa = math.log(t2 / t1) / math.log(n2 / n1)
    k = t1 / (n1 ** alfa)
    n_alvo = (alvo_segundos / k) ** (1.0 / alfa)

    # arredonda para um numero redondo, que fica melhor no relatorio
    passo = 10 ** max(0, int(math.log10(n_alvo)) - 1)
    n_sugerido = int(round(n_alvo / passo) * passo)

    print(f"     expoente medido: {alfa:.2f}   (custo cresce como N^{alfa:.2f})")
    print(VERDE + f"N sugerido para esta maquina: {n_sugerido:,}".replace(",", "."))
    previsto = k * (n_sugerido ** alfa)
    print(f"     tempo sequencial previsto: {previsto:.0f}s "
          f"({previsto / 60:.1f} min)")
    print("     (estimativa por extrapolacao, com erro tipico de ~10%; "
          "confirme rodando sequencial.py uma vez)")
    if previsto < 60:
        print(AVISO + "abaixo de 1 minuto: a lauda exige MINUTOS, aumente o alvo")

    return n_sugerido


# ------------------------------------------------------------------ resumo

def _principal() -> int:
    ap = argparse.ArgumentParser(
        description="Verifica se esta maquina esta pronta para a apresentacao."
    )
    ap.add_argument("--alvo", type=float, default=150.0,
                    help="segundos desejados para a versao sequencial (padrao: 150)")
    ap.add_argument("--rapido", action="store_true",
                    help="pula a calibracao (so verifica que tudo funciona)")
    args = ap.parse_args()

    print("=" * 70)
    print("VERIFICACAO DE AMBIENTE - Etapa 1 (contagem paralela de primos)")
    print("=" * 70)

    problemas: list[str] = []
    problemas += checar_ambiente()
    if not problemas:
        problemas += checar_paralelismo()
        problemas += checar_correcao()

    n_sugerido = None
    if not problemas and not args.rapido:
        n_sugerido = calibrar(args.alvo)

    print("\n" + "=" * 70)
    if problemas:
        print("RESULTADO: NAO ESTA PRONTO")
        for p in problemas:
            print(f"  - {p}")
        print("=" * 70)
        return 1

    # W ideal = nucleos FISICOS. Detectamos de verdade em vez de supor
    # "logicos // 2": num processador sem SMT isso cortaria W pela metade
    # sem motivo.
    try:
        from benchmark import nucleos_fisicos
        fisicos = nucleos_fisicos()
    except Exception:                                           # noqa: BLE001
        fisicos = None
    w_sugerido = max(2, fisicos or mp.cpu_count())

    print("RESULTADO: PRONTO PARA APRESENTAR")
    print("=" * 70)
    print(f"\nNucleos fisicos detectados: {fisicos if fisicos else 'indeterminado'}"
          f"  ->  W sugerido: {w_sugerido}")
    if n_sugerido:
        print("\nComandos ja com os valores desta maquina:\n")
        print("  # 1. medicao completa (rode ANTES da apresentacao)")
        print(f"  python benchmark.py -n {n_sugerido} -w 2,{w_sugerido} "
              f"-r 3 --com-threads --threads-w {w_sugerido}")
        print("\n  # 2. na apresentacao: sequencial (comece no minuto 0)")
        print(f"  python sequencial.py -n {n_sugerido}")
        print("\n  # 3. na apresentacao: paralelo")
        print(f"  python paralelo_processos.py -n {n_sugerido} -w {w_sugerido}")
        print("\n  # 4. estabilidade e corrida (secao critica, ~20s + ~12s ao vivo)")
        print(f"  python verificar.py -n {n_sugerido // 8} -w {w_sugerido} -r 5")
        print(f"  python demo_corrida.py -p {w_sugerido} -i 100000 -r 3")
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    sys.exit(_principal())
