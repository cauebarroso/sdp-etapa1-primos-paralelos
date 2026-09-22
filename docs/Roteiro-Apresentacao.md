# Roteiro da apresentação — 10 minutos

**Equipe:** Cauê Barroso · César Ribeiro · Augusto Pereira · **Turma:** CC6MA

Tudo roda **no notebook da apresentação**. Nenhuma parte depende de instância na nuvem.

---

## Divisão da fala

| Parte | Tempo | Quem | Sobre o que será arguido depois |
|---|---|---|---|
| 1. O problema e por que ele se divide | 2 min | **Cauê** | nuvem · ganho |
| 2. A seção crítica | 2 min | **César** | problema · nuvem · ganho |
| 3. A arquitetura na nuvem | 2 min | **Augusto** | problema · seção crítica |
| 4. A execução | 3 min | **Cauê** + **César** | — |
| 5. O ganho | 1 min | **Augusto** | — |

Cada um fala ~3,5 min. **Ninguém é arguido sobre o que apresentou** — por isso todos
precisam estudar o projeto inteiro, não só a própria parte.

---

## Os números que todos precisam saber de cor

| | |
|---|---|
| Entrada | N = 20.000.000 · **2.000 blocos** de 10.000 inteiros |
| Primos encontrados | **1.270.607** (maior: 19.999.999) |
| Máquina | 6 núcleos físicos / 12 lógicos · CPython 3.14.4 |
| **Sequencial** | **128,62 s** |
| W = 2 | 66,77 s → **1,93×** (teto de Amdahl: 1,94×) |
| W = 4 | 34,47 s → **3,73×** (teto: 3,67×) |
| **W = 6** | **25,74 s → 5,00×** ← o pico (teto: 5,22×) |
| W = 8 | 26,73 s → **4,81×** ← **pior que W=6** (teto: 6,61×) |
| **Threads, W = 4** | **140,53 s → 0,92×** ← mais lento que o sequencial |
| Amdahl | `S = 1 / ((1−p) + p/n)`, com **p = 0,97** |
| Corrida sem trava | 600.000 esperado, chega ~340.000 (perde ~45 %) |
| SLA | 1 zona = **99,5 %** (216 min/mês) · 2+ zonas = **99,99 %** (4,3 min) |

**As duas frases que resumem o trabalho inteiro:**

1. *"W = 8 é mais lento que W = 6 porque a máquina tem 6 núcleos físicos."*
2. *"Com threads ficou mais lento que sem paralelismo nenhum, por causa da GIL."*

---

## Antes de começar

```bash
cd src
python preflight.py --alvo 150      # confirma que roda e calibra o N desta maquina
```

Anote o **N** e o **W** que ele imprimir e use nos comandos abaixo. Deixe **três terminais**
abertos com fonte grande: **A** = sequencial · **B** = paralelo · **C** = testes.

> **No minuto 0, antes de falar**, Cauê digita no terminal A e deixa rodando:
> ```bash
> python sequencial.py -n <N>
> ```
> Leva ~2 min e termina durante a parte 3. Assim a execução é **ao vivo** e ninguém fica
> parado olhando terminal.

---

## Parte 1 — O problema (2 min) — **Cauê**

**Na tela:** `src/primos.py`, função `resumo_intervalo`.

> "Nosso problema é contar os números primos entre 2 e 20 milhões, devolvendo três coisas:
> quantos são, qual é o maior, e a soma de todos. A entrada é um número só — o N.
>
> Ele se divide porque **decidir se um número é primo não depende de nenhum outro número**.
> Não há dependência entre as partes. Nossa unidade de trabalho é um **bloco de 10 mil
> inteiros consecutivos** — para 20 milhões, são **2.000 blocos independentes**.
>
> O teste é divisão sucessiva em Python puro — é aqui *(aponta o laço)* que o programa
> passa 99 % do tempo. Sequencialmente leva **128 segundos**, e é essa execução que já está
> rodando ali *(aponta o terminal A)*.
>
> E o resultado é **verificável de três formas**: um Crivo de Eratóstenes, que é um
> algoritmo completamente diferente, dá a mesma resposta em menos de um segundo; os três
> campos funcionam como assinatura, então trocar um primo por outro seria detectado; e
> π de 20 milhões é 1.270.607, que é valor conhecido da literatura."

**Se perguntarem por que Python puro e não uma biblioteca em C:** porque queríamos trabalho
**de processador**. Biblioteca em C liberaria a GIL e estragaria a comparação entre threads
e processos, que é o ponto do trabalho.

---

## Parte 2 — A seção crítica (2 min) — **César**

**Na tela:** `src/paralelo_processos.py`, de `_dobrar_no_estado` até `trabalhador`.

> "O estado compartilhado são **três inteiros em memória compartilhada**: a contagem, o
> maior primo e a soma. Todos os processos escrevem nos três.
>
> A seção crítica é **só isto** *(seleciona `_dobrar_no_estado`)*: somar o parcial do bloco
> no total global. São três leitura-modificação-escrita, que não são atômicas — dois
> processos podem ler o mesmo valor antigo, e a escrita de um apaga a do outro.
>
> Reparem no que **não** está dentro da trava: o laço de primalidade, que fica aqui fora
> *(aponta `local = resumo_intervalo(...)`)*. Se a trava envolvesse o laço, o programa
> continuaria **correto**, mas deixaria de ser **paralelo** — um processo por vez. A trava
> protege três somas de microssegundos, adquiridas 2.000 vezes na execução inteira.
>
> A primitiva é um **Lock**, um mutex. Não é semáforo porque não há recurso contável a
> limitar, e não é monitor porque nenhum processo espera por estado de outro.
>
> E a trava não é decorativa:" **(terminal C, ~12 s)**
>
> ```bash
> python demo_corrida.py -p 6 -i 100000 -r 3
> ```
>
> "Seis processos, cem mil incrementos cada: o certo é 600 mil. **Sem a trava**, dá errado
> e dá **diferente a cada execução** — perde quase metade. **Com a trava**, dá exatamente
> 600 mil, nas três.
>
> E no programa de verdade:" **(terminal C, ~20 s)**
>
> ```bash
> python verificar.py -n <N/8> -w <W> -r 5
> ```
>
> "Cinco execuções da versão paralela, mesma entrada: os três campos idênticos em todas, e
> idênticos ao crivo e ao sequencial."

---

## Parte 3 — A arquitetura na nuvem (2 min) — **Augusto**

**Na tela:** seção 4 do relatório.

> "Projetamos a arquitetura para rodar isto na nuvem, e registramos cada decisão com a
> razão dela.
>
> **Uma única zona de disponibilidade.** Isso é decisão, não descuido: com instância
> isolada em uma zona, o compromisso de SLA que passa a valer é o de **99,5 %** — ou seja,
> **216 minutos** de indisponibilidade admitida por mês. Os 99,99 %, que dariam só 4,3
> minutos, exigiriam instâncias distribuídas por **duas ou mais zonas**.
>
> Escolhemos os 99,5 % de propósito, por dois motivos. Primeiro: nossa carga é um **lote**
> que roda até terminar em poucos minutos, não um serviço 24 por 7 — se cair, repete-se a
> execução. Segundo, e mais importante: a medição exige sequencial e paralelo **na mesma
> máquina**. Duas zonas significariam duas instâncias, o dobro do custo, e **nenhum ganho
> de medição**.
>
> **Família compute-optimized**, a `c`, porque o gargalo é CPU. Descartamos a família `t`
> por um motivo concreto: ela entrega créditos de CPU que se esgotam, e uma medição de
> minutos terminaria com o desempenho caindo no meio — o tempo medido não seria o do
> algoritmo.
>
> **Duas regras de entrada, só:**
>
> - **22, SSH — a porta administrativa — restrita ao IP da equipe, /32.** Ela **não** fica
>   aberta para 0.0.0.0/0, e isso é proposital: SSH exposto ao mundo recebe varredura e
>   força bruta o tempo todo, e aí qualquer credencial fraca deixa de ser um incidente
>   contido e vira **controle total da máquina**.
> - **8000 — a porta do serviço**, uma página somente leitura, sem autenticação a proteger
>   e sem rota que altere estado.
>
> Isso não é só intenção documentada: nosso script de provisionamento **aborta** se não
> descobrir o IP da equipe, em vez de cair para 0.0.0.0/0, e no fim confere as regras e
> falha se achar 0.0.0.0/0 na porta 22.
>
> **Entrada e saída** ficam no disco EBS da instância. Não usamos S3: a entrada é **um
> número** e a saída tem 4 KB — S3 só acrescentaria latência e permissão sem ganho.
>
> **A instância é criada por execução**, não fica ligada: a carga dura minutos, e manter
> máquina ligada fora disso é custo sem uso."

---

## Parte 4 — A execução (3 min) — **Cauê** e **César**

### Cauê (1,5 min) — terminal A, rodando desde o minuto 0

> "Esta é a versão **sequencial**, que começou antes de eu falar. Terminou em **[tempo]**.
> Um fluxo só, um núcleo só."

**Terminal B, ao vivo:**

```bash
python paralelo_processos.py -n <N> -w <W>
```

> "Mesmo programa, mesma entrada, **[W] processos**. Enquanto roda: cada processo puxa
> blocos de uma fila, resolve o bloco sozinho, e só no fim entra na trava para somar no
> total. São 2.000 blocos para poucos trabalhadores, **de propósito** — os blocos do fim do
> intervalo custam mais que os do começo, porque testar números grandes exige mais
> divisões, e a fila reequilibra isso sozinha."

### César (1,5 min) — quando terminar

> "**[tempo paralelo]** contra **[tempo sequencial]**. E o mais importante: **os três
> números são exatamente os mesmos** — 1.270.607 primos, mesmo maior primo, mesma soma.
> Paralelizar não mudou a resposta.
>
> E isto não vale só para esta execução: a medição oficial rodou **3 vezes cada
> configuração**, e todas as 18 execuções conferiram contra o crivo."

---

## Parte 5 — O ganho (1 min) — **Augusto**

**Na tela:** a tabela da seção 5 do relatório, ou o gráfico da 6.1.

> "O melhor speedup medido foi **5,00×**, com 6 processos: de 128 segundos para 25.
>
> Comparando com o teto de Amdahl, com a fração paralelizável que estimamos, p = 0,97: em
> W=2 atingimos 99 % do teto, em W=4 **102 %**, em W=6 96 %. Ou seja, **até o número de
> núcleos físicos o medido acompanha o previsto**.
>
> Em W=8 cai para 73 % — e, mais que isso, **o speedup diminui**: 4,81× contra 5,00× de
> W=6. Acrescentar dois trabalhadores deixou o programa **mais lento**. A máquina tem 6
> núcleos físicos, e o sétimo e o oitavo não têm onde rodar.
>
> Isso mostra o que realmente limitou o ganho: **não é a seção crítica** — a trava é
> adquirida 2.000 vezes e segura três somas, menos de 0,1 % do tempo. É o **número de
> núcleos físicos**.
>
> E a nossa estimativa de p estava certa: a métrica de Karp-Flatt, que parte do speedup
> medido e calcula qual fração paralelizável o explicaria, dá entre **0,96 e 0,98** até
> W=6 — em torno dos 0,97 que estimamos."

---

## Preparação para a arguição

### Cauê — será arguido sobre **nuvem** e **ganho**

**"Por que uma zona só, e não duas?"**
> Com uma zona o SLA é 99,5 %, que dá 216 minutos por mês, e isso basta para um lote de
> minutos que pode ser repetido. 99,99 % exigiria duas zonas e duas instâncias — o dobro do
> custo — e ainda atrapalharia, porque a medição tem que ser na mesma máquina.

**"Por que a porta 22 não pode ficar aberta para 0.0.0.0/0?"**
> Porque SSH aberto ao mundo é varrido e atacado por força bruta continuamente. Com a porta
> administrativa pública, uma credencial fraca vira controle total da instância. Restringindo
> ao /32 da equipe, a superfície some para todo o resto da internet.

**"Por que o speedup não chegou ao teto de Amdahl?"**
> Até o número de núcleos físicos ele praticamente chegou — 99 %, 102 % e 96 % do teto em
> W=2, 4 e 6. Só cai em W=8, e por um motivo claro: a máquina tem 6 núcleos físicos, então
> os dois trabalhadores extras disputam núcleo com os outros. Tanto que W=8 ficou **mais
> lento** que W=6.

**"O que é a métrica de Karp-Flatt?"**
> Ela inverte a lei de Amdahl: em vez de supor o p e prever o speedup, parte do speedup
> medido e calcula qual fração paralelizável o explicaria. Deu entre 0,96 e 0,98 até W=6, o
> que confirma nossa estimativa de 0,97.

### César — será arguido sobre **problema**, **nuvem** e **ganho**

**"Qual é a unidade de trabalho, e por que ela é independente?"**
> Um bloco de 10 mil inteiros consecutivos. É independente porque testar a primalidade de um
> número não usa o resultado de nenhum outro — cada bloco se resolve sozinho e devolve
> contagem, maior primo e soma parciais.

**"Como vocês sabem que a resposta está certa?"**
> Por três caminhos independentes: o Crivo de Eratóstenes, que é outro algoritmo, dá a mesma
> resposta; os três campos funcionam como assinatura, então trocar um primo por outro seria
> detectado; e π(20.000.000) = 1.270.607 confere com a literatura.

**"Por que 2.000 blocos e não um por processo?"**
> Porque blocos de tamanho igual não têm custo igual: testar números grandes exige mais
> divisões, então o fim do intervalo é bem mais caro que o começo. Com um bloco por
> processo, quem pegasse o último seguraria todos os outros ociosos. Com muitos blocos numa
> fila, quem termina puxa o próximo e a carga se equilibra sozinha.

**"Por que não usaram S3 para a saída?"**
> Porque a entrada é um número e a saída tem 4 KB. S3 só acrescentaria latência de rede
> dentro do laço de medição, permissões de IAM e mais um ponto de falha, sem ganho nenhum.

### Augusto — será arguido sobre **problema** e **seção crítica**

**"Onde exatamente é a seção crítica, e por que ela é tão pequena?"**
> É a função `_dobrar_no_estado`: somar o parcial do bloco nos três acumuladores globais. É
> pequena de propósito — se a trava envolvesse o laço de primalidade, o programa seria
> correto mas rodaria um processo por vez, e o speedup denunciaria isso.

**"Por que Lock e não semáforo ou monitor?"**
> Porque o que precisamos é exclusão mútua pura. Semáforo serve para limitar um recurso
> contável — não temos contagem a limitar. Monitor serve quando há condição de espera a
> sinalizar — nenhum trabalhador espera por estado de outro. O mutex é a primitiva mínima
> que resolve.

**"Como vocês provam que não há condição de corrida?"**
> De duas formas. Rodamos a versão paralela 5 vezes com a mesma entrada e os três campos vêm
> idênticos. E temos o contraste: seis processos somando 100 mil incrementos cada — sem a
> trava o total vem errado e **muda a cada execução**; com a trava dá exatamente 600 mil,
> sempre.

**"Por que processos e não threads?"**
> Porque o trabalho é limitado por processador, não por espera — não há disco, rede nem
> banco no laço. Em CPython a GIL deixa só uma thread executando bytecode por vez, então
> elas se revezam em vez de somar tempo de CPU. **Nós medimos**: com 4 threads deu 140
> segundos contra 128 do sequencial — ficou **mais lento** que sem paralelismo. Com
> processos, 5,00×.

**"O que é a GIL?"**
> É um bloqueio global do interpretador CPython que garante que só uma thread execute
> bytecode Python por vez. Para trabalho de espera (disco, rede) threads ainda ajudam,
> porque a GIL é liberada durante a espera. Para trabalho de processador, não.

---

## O que **não** pode acontecer

- [ ] Demonstração gravada ou em captura de tela → **tudo ao vivo**
- [ ] Speedup sem o tempo sequencial medido na mesma máquina e mesma entrada → por isso o
      sequencial roda ao vivo, com o mesmo N
- [ ] Estourar o tempo em mais de 2 minutos → por isso o sequencial começa no minuto 0
- [ ] Integrante que não responde sobre a parte que não apresentou → estudar a seção acima

---

## Se algo der errado

| Problema | O que fazer |
|---|---|
| O sequencial não terminou a tempo | Mostre `resultados/resultados.json`, que tem a medição completa |
| Erro de import | Rode de dentro de `src/`, ou `python preflight.py` para achar a causa |
| A máquina é lenta demais | `python preflight.py --alvo 90` e use o N menor que ele sugerir |
| Firewall reclama da porta 8000 | Use `--endereco 127.0.0.1`, ou simplesmente pule a página de status |
