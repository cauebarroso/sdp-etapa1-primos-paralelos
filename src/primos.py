"""Nucleo de calculo compartilhado pelas versoes sequencial e paralela.

O trabalho pesado (limitado por CPU) e o teste de primalidade por divisao
sucessiva (trial division) em Python puro. E de proposito que NAO usamos
bibliotecas em C nem hashlib: queremos trabalho de PROCESSADOR em CPython,
para que a comparacao entre threads (limitadas pela GIL) e processos seja
honesta.

A verificacao independente do resultado usa um Crivo de Eratostenes
(rapido, com bytearray), que confere a resposta obtida pela divisao
sucessiva sem repetir o mesmo algoritmo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Resumo:
    """Resultado verificavel de um intervalo.

    Tres numeros que, juntos, funcionam como uma assinatura do intervalo:
    trocar qualquer primo por outro muda pelo menos um deles.
    """

    contagem: int      # quantos primos ha no intervalo
    maior_primo: int   # o maior primo encontrado (0 se nenhum)
    soma: int          # soma de todos os primos (checksum aditivo)

    def combinar(self, outro: "Resumo") -> "Resumo":
        return Resumo(
            contagem=self.contagem + outro.contagem,
            maior_primo=max(self.maior_primo, outro.maior_primo),
            soma=self.soma + outro.soma,
        )

    def como_tupla(self) -> tuple[int, int, int]:
        return (self.contagem, self.maior_primo, self.soma)


RESUMO_VAZIO = Resumo(0, 0, 0)


def eh_primo(n: int) -> bool:
    """Teste de primalidade por divisao sucessiva.

    Trabalho limitado por CPU em Python puro: para cada numero, tenta
    dividir por 2, 3 e depois pelos impares ate a raiz quadrada. E o laco
    que domina o tempo de execucao do programa inteiro.
    """
    if n < 2:
        return False
    if n < 4:
        return True          # 2 e 3
    if n % 2 == 0:
        return False
    divisor = 3
    while divisor * divisor <= n:
        if n % divisor == 0:
            return False
        divisor += 2
    return True


def resumo_intervalo(inicio: int, fim: int) -> Resumo:
    """Resume o intervalo [inicio, fim) usando divisao sucessiva.

    Esta e a unidade de trabalho: um trabalhador recebe (inicio, fim) e
    devolve o Resumo local, sem tocar em nenhum estado compartilhado.
    """
    contagem = 0
    maior = 0
    soma = 0
    for n in range(max(inicio, 2), fim):
        if eh_primo(n):
            contagem += 1
            maior = n            # n cresce, entao o ultimo primo e o maior
            soma += n
    return Resumo(contagem, maior, soma)


def gerar_tarefas(n: int, tamanho_bloco: int) -> list[tuple[int, int]]:
    """Divide [2, n] em blocos [inicio, fim) de ate tamanho_bloco numeros.

    Muitos blocos pequenos (T >> W) permitem balanceamento dinamico: como
    testar primos grandes custa mais que testar primos pequenos, blocos de
    tamanho fixo tem custo desigual, e a fila redistribui esse custo.
    """
    if tamanho_bloco < 1:
        raise ValueError(f"tamanho_bloco precisa ser >= 1 (recebi {tamanho_bloco})")
    tarefas: list[tuple[int, int]] = []
    inicio = 2
    limite = n + 1
    while inicio < limite:
        fim = min(inicio + tamanho_bloco, limite)
        tarefas.append((inicio, fim))
        inicio = fim
    return tarefas


def crivo_ate(n: int) -> Resumo:
    """Verificacao independente: Crivo de Eratostenes ate n (inclusive).

    Algoritmo diferente do usado no trabalho pesado. Se os dois concordam,
    a resposta esta certa. Rapido (segundos) por usar bytearray e operacoes
    de fatia em C, por isso serve so para conferir, nao para medir ganho.
    """
    if n < 2:
        return RESUMO_VAZIO
    eh = bytearray(b"\x01") * (n + 1)
    eh[0] = 0
    eh[1] = 0
    p = 2
    while p * p <= n:
        if eh[p]:
            eh[p * p :: p] = b"\x00" * len(range(p * p, n + 1, p))
        p += 1
    contagem = 0
    maior = 0
    soma = 0
    for i in range(2, n + 1):
        if eh[i]:
            contagem += 1
            maior = i
            soma += i
    return Resumo(contagem, maior, soma)
