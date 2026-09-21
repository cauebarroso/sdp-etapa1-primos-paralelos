# Roteiro da apresentação — 10 minutos

**Equipe:** Cauê Barroso · César Ribeiro · Augusto Pereira
**Turma:** CC6MA · **Data:** 22/09

> **Atenção — a apresentação roda em outra máquina.** O código foi escrito e medido
> num notebook; a apresentação será em outro. Isso muda duas coisas, e as duas estão
> resolvidas neste roteiro: **(1)** o N precisa ser recalibrado para a máquina que for
> usada, porque ele foi escolhido pela velocidade do processador; **(2)** os números do
> relatório têm que ser os da máquina que realmente mediu. Faça a **véspera** abaixo.

---

## Plano A (principal): tudo roda na instância EC2

**É o que a lauda exige** — "execução em instância provisionada pela equipe". E resolve
o problema da máquina diferente de graça: **o notebook do amigo vira só um terminal e um
navegador**. A velocidade dele não entra na conta, porque quem calcula é a EC2.

```bash
ssh -i ~/.ssh/chave-primos-etapa1.pem ec2-user@<IP>
```

O que o notebook do amigo precisa ter: um cliente **SSH** (o Windows 11 já vem com um no
PowerShell), o **arquivo .pem** da chave, e um **navegador**. Só isso.

> **Risco a testar na véspera:** rede de faculdade às vezes bloqueia a saída na porta 22.
> **Teste isso no dia anterior, de dentro da faculdade se der.** Se estiver bloqueado,
> use o roteador do celular — ou caia para o Plano B.

## Plano B (contingência): roda no notebook do amigo

Se a rede falhar, a aplicação roda local. Aí o **N tem que ser o da máquina dele**, e a
medição do relatório também.

---

## Véspera — faça na máquina que vai apresentar

```bash
cd src
python preflight.py --alvo 150
```

Esse comando, em menos de um minuto:

1. confere versão do Python, número de núcleos e se os módulos importam;
2. confere que `multiprocessing`, memória compartilhada e trava funcionam **naquela
   máquina** (é o que mais quebra ao trocar de computador);
3. confere que sequencial, paralelo e crivo dão o mesmo resultado;
4. **calibra o N** medindo a velocidade real daquele processador — e imprime, já
   preenchidos, os comandos exatos para usar na apresentação.

Anote o **N** e o **W** que ele imprimir. **Use esses valores em tudo daqui para frente**
— inclusive na medição do relatório.

Depois, ainda na véspera, rode a medição oficial **na mesma máquina que vai apresentar**
(leva ~20 min, deixe rodando):

```bash
python benchmark.py -n <N> -w 2,<W> -r 3 --com-threads --threads-w <W>
python tabelas.py                       # imprime as tabelas do relatório
```

Cole as tabelas na seção 5 do relatório e gere o PDF. **Sem isso, o relatório tem os
números de uma máquina e a demonstração mostra outra** — e a lauda desconta exatamente
por isso ("speedup calculado sem o tempo sequencial medido na mesma máquina").

> **Feche tudo antes de medir.** Não é conselho genérico — medimos o efeito: sob carga de
> fundo, o speedup com 2 processos caiu de **1,93× para 1,27×** (−34 %). O tempo
> sequencial quase não muda, porque usa um núcleo só e convive bem com outra carga; a
> interferência penaliza **apenas a versão paralela** — ou seja, estraga exatamente o
> número que vocês vão apresentar, e sem dar nenhum sinal de que algo está errado.

### Checklist da véspera

- [ ] Tudo fechado durante a medição (navegador, jogos, streaming, downloads)
- [ ] `preflight.py` passou, N e W anotados
- [ ] `benchmark.py` rodado na máquina da apresentação, com esse N
- [ ] Tabelas coladas no relatório, PDF gerado e enviado ao ambiente virtual
- [ ] Repositório com o link publicado no ambiente virtual
- [ ] SSH testado a partir da rede da faculdade (ou hotspot do celular pronto)
- [ ] Arquivo `.pem` copiado para o notebook do amigo, com permissão correta
- [ ] Console da AWS: login testado, senha/MFA à mão
- [ ] Instância **ligada** (se estiver parada, ligue antes — leva ~1 min)

---

## No dia — 5 minutos antes

| # | O quê |
|---|---|
| 1 | Console AWS **aberto e logado**, na tela de instâncias (o critério exige console ao vivo, não captura) |
| 2 | Página de status aberta: `http://<IP>:8000/` |
| 3 | Três terminais abertos, **fonte grande**: A = sequencial · B = paralelo · C = testes |
| 4 | `resultados.json` já preenchido pela medição da véspera |

### O truque de tempo — leia com atenção

A versão sequencial leva **~2 a 3 minutos**. Se ela começar só na parte 4, estoura o
tempo da apresentação.

> **No minuto 0, antes de falar**, Cauê digita no **terminal A** e deixa rodando:
>
> ```bash
> python3 sequencial.py -n <N>
> ```
>
> Ela roda **durante as partes 1, 2 e 3** (6 minutos) e já estará pronta quando a parte 4
> começar. A execução é **ao vivo**, na frente do professor, e ninguém fica parado
> olhando terminal.

---

## Divisão da fala

| Parte | Tempo | Quem apresenta |
|---|---|---|
| 1. O problema e por que ele se divide | 2 min | **Cauê** |
| 2. A seção crítica | 2 min | **César** |
| 3. Os recursos na nuvem | 2 min | **Augusto** |
| 4. A execução | 3 min | **Cauê** (1,5) + **César** (1,5) |
| 5. O ganho | 1 min | **Augusto** |

Cada um fala ~3,5 minutos. Ninguém apresenta a parte sobre a qual vai ser arguido.

---

## Parte 1 — O problema e por que ele se divide (2 min) — **Cauê**

**Na tela:** `src/primos.py`, função `resumo_intervalo`.

> "Nosso problema é contar os números primos entre 2 e N — aqui, **[N]** — e devolver
> três coisas: quantos são, qual é o maior, e a soma de todos. A entrada é um número só,
> e o volume é de [N] candidatos a testar.
>
> Ele se divide porque **decidir se um número é primo não depende de nenhum outro
> número**. Não há dependência entre as partes. A nossa unidade de trabalho é um **bloco
> de 10 mil inteiros consecutivos** — para esse N, são **[N/10.000] blocos
> independentes**.
>
> O teste é divisão sucessiva, em Python puro — é aqui *(aponta o laço)* que o programa
> passa 99 % do tempo. Sequencialmente isso leva **[tempo]**, e é essa execução que já
> está rodando no terminal ao lado *(aponta o terminal A)*.
>
> E o resultado é **verificável**: um Crivo de Eratóstenes, que é um algoritmo
> completamente diferente, calcula a mesma resposta em menos de um segundo. Se os dois
> concordam, não é coincidência."

---

## Parte 2 — A seção crítica (2 min) — **César**

**Na tela:** `src/paralelo_processos.py`, de `_dobrar_no_estado` até `trabalhador`.

> "O estado compartilhado são **três inteiros em memória compartilhada**: a contagem, o
> maior primo e a soma. Todos os processos escrevem nos três.
>
> A seção crítica é **só isto** *(seleciona `_dobrar_no_estado`)*: somar o parcial do
> bloco no total global. São três leitura-modificação-escrita, que não são atômicas.
>
> Reparem no que **não** está dentro da trava: o laço de primalidade. Ele fica aqui fora
> *(aponta `local = resumo_intervalo(inicio, fim)`)*. Se a trava envolvesse o laço, o
> programa continuaria correto, mas **deixaria de ser paralelo** — um processo por vez.
> A trava protege três somas que levam microssegundos; o trabalho pesado corre solto.
>
> A primitiva é um **Lock**, um mutex. Não é semáforo porque não há recurso contável a
> limitar, e não é monitor porque não há condição para esperar.
>
> E a trava não é decorativa — olhem:" **(terminal C, ~12 segundos)**
>
> ```bash
> python3 demo_corrida.py -p <W> -i 100000 -r 3
> ```
>
> "Seis processos, cem mil incrementos cada: o certo é 600 mil. **Sem a trava**, dá
> errado e dá *diferente a cada execução* — perde quase metade dos incrementos, porque
> dois processos leem o mesmo valor e um sobrescreve o outro. **Com a trava**, dá
> exatamente 600 mil, nas três execuções.
>
> E no programa de verdade, a mesma prova:" **(terminal C)**
>
> ```bash
> python3 verificar.py -n <N/8> -w <W> -r 5
> ```
>
> "Cinco execuções da versão paralela, mesma entrada: os três campos idênticos em todas,
> e idênticos ao crivo e ao sequencial."

---

## Parte 3 — Os recursos na nuvem (2 min) — **Augusto**

**Na tela:** console da AWS, **ao vivo** — EC2 › Instâncias › a instância › Segurança.

> "Esta é a instância, criada por nós *(mostra)*: `c5.2xlarge`, região **sa-east-1**, São
> Paulo, zona **sa-east-1a** — **uma única zona**.
>
> Isso é uma decisão, não um descuido: com instância isolada, o compromisso de SLA que
> passa a valer é o de **99,5 %**, ou seja, **216 minutos** de indisponibilidade admitida
> por mês. Os 99,99 %, que dariam 4,3 minutos, exigiriam instâncias em duas ou mais
> zonas. Escolhemos os 99,5 % porque nossa carga é um **lote** de poucos minutos, não um
> serviço 24 por 7 — e porque a medição **precisa** ser na mesma máquina, então duas
> zonas dobrariam o custo sem melhorar nada.
>
> A família é **c**, compute-optimized, porque o gargalo é CPU. Uma família `t` daria
> créditos de CPU que acabam no meio de uma medição de minutos e estragariam o tempo.
> São 8 vCPU, que são **4 núcleos físicos** — é por isso que medimos até W igual a 4.
>
> Agora o grupo de segurança *(abre as regras de entrada)*. São **duas regras, só**:
>
> - **22, SSH — a porta administrativa — restrita ao IP da nossa equipe, /32.**
>   Ela **não** está aberta para 0.0.0.0/0, e isso é proposital: SSH exposto ao mundo
>   recebe varredura e força bruta o tempo todo, e aí qualquer falha de credencial vira
>   controle total da máquina em vez de um incidente contido. O nosso script de
>   provisionamento **aborta** se não descobrir o IP da equipe, em vez de abrir para todo
>   mundo — e no fim ele confere a regra e falha se achar 0.0.0.0/0 na porta 22.
> - **8000 — a porta do serviço** — essa sim aberta, e é esta página aqui
>   *(abre `http://<IP>:8000/`)*: somente leitura, sem autenticação a proteger e sem
>   nenhuma rota que altere estado.
>
> Entrada e saída ficam no disco EBS gp3 da própria instância. Não usamos S3 porque a
> entrada é **um número** e a saída tem 4 KB — S3 só acrescentaria latência e permissão
> sem ganho nenhum."

---

## Parte 4 — A execução (3 min) — **Cauê** e **César**

### Cauê (1,5 min) — **terminal A**, que vem rodando desde o minuto 0

> "Esta é a versão **sequencial**, que começou a rodar antes de eu falar. Mesmo N, mesma
> máquina — esta instância. Terminou em **[tempo]**. Um fluxo só, um núcleo só."

**Agora, terminal B, ao vivo:**

```bash
python3 paralelo_processos.py -n <N> -w <W>
```

> "Mesmo programa, mesma entrada, **[W] processos**. Enquanto roda: cada processo puxa
> blocos de uma fila, testa os primos do bloco sozinho, e só no fim de cada bloco entra
> na trava para somar no total. São muito mais blocos que trabalhadores, de propósito:
> os blocos do fim do intervalo custam mais que os do começo, e a fila reequilibra isso
> sozinha."

### César (1,5 min) — quando terminar

> "**[tempo paralelo]** contra **[tempo sequencial]** do sequencial. E o mais importante:
> **os três números são exatamente os mesmos** — mesma contagem, mesmo maior primo, mesma
> soma. Paralelizar não mudou a resposta.
>
> E isto não vale só para esta execução *(aponta a página na porta 8000)*: aqui está a
> medição oficial, **3 execuções de cada configuração**, todas conferindo contra o crivo."

---

## Parte 5 — O ganho (1 min) — **Augusto**

**Na tela:** a página `http://<IP>:8000/` (tabela de medições).

> "O speedup medido com [W] processos foi **[medido]×**. O teto previsto por Amdahl, com
> a fração paralelizável que estimamos, p = 0,97, é **[previsto]×**.
>
> A diferença entre o medido e o previsto tem três causas, e a gente consegue separar
> elas. Primeira: **criar os processos**. Em Python o `spawn` reinicia o interpretador
> inteiro em cada processo — é custo fixo que não existe no sequencial. Segunda: **passar
> os blocos pela fila**, que é serialização e cópia entre processos. Terceira: **a espera
> na trava**, que é pequena, porque a seção crítica são três somas.
>
> E dá para mostrar que a causa principal **não** é a parte serial do algoritmo: a coluna
> 'p medido' aqui é a métrica de Karp-Flatt, que calcula qual fração serial explicaria o
> speedup que aconteceu. Como ela **piora** conforme W cresce, o que limita não é uma
> parte fixa do algoritmo — é custo que **cresce junto com o número de trabalhadores**.
> Foi por isso que dobrar W não dobrou o ganho: acima dos núcleos físicos, os processos
> passam a disputar o mesmo núcleo."

---

## Preparação para a arguição

Cada integrante responde sobre uma parte que **não** apresentou.

### Cauê — não apresentou **nuvem** nem **ganho**

**"Por que uma zona só, e não duas?"**
> Porque com uma zona o SLA é 99,5 %, que dá 216 minutos por mês, e isso basta para um
> lote de minutos que pode ser repetido. 99,99 % exigiria duas zonas e duas instâncias —
> o dobro do custo — e ainda atrapalharia, porque a medição tem que ser na mesma máquina.

**"Por que a porta 22 não pode ficar aberta para 0.0.0.0/0?"**
> Porque SSH aberto ao mundo é varrido e atacado por força bruta continuamente. Com a
> porta administrativa pública, uma senha ou chave fraca vira controle total da
> instância. Restringindo ao /32 da equipe, a superfície some para todo o resto da
> internet.

**"Como vocês sabem que a medição é confiável?"**
> Por quatro razões. As duas versões rodam na mesma máquina, com a mesma entrada, na mesma
> invocação do programa — não há reinício nem troca de condição entre elas. Cada
> configuração roda três vezes e reportamos a mediana, então uma execução atípica não
> arrasta o número. O resultado de toda execução é conferido contra o crivo **antes** de o
> tempo ser aceito: tempo bom com resultado errado não entra. E medimos com a máquina
> ociosa — isso importa porque carga de fundo penaliza só a versão paralela, que disputa
> todos os núcleos, enquanto a sequencial usa um só; medir sem esse cuidado **subestima** o
> ganho. Chegamos a verificar: sob carga, o speedup com 2 processos caía de 1,93× para
> 1,27×.

**"Por que o speedup medido ficou abaixo do teto de Amdahl?"**
> Três motivos: criar os processos (o `spawn` reinicia o interpretador em cada um),
> passar os blocos pela fila, e a espera na trava. A métrica de Karp-Flatt mostra que a
> fração serial aparente cresce com W — logo o limite é custo de paralelização, e não uma
> parte serial fixa do algoritmo.

### César — não apresentou **problema**, **nuvem** nem **ganho**

**"Qual é a unidade de trabalho, e por que ela é independente?"**
> Um bloco de 10 mil inteiros consecutivos. É independente porque testar a primalidade de
> um número não usa resultado de nenhum outro — cada bloco se resolve sozinho e devolve
> contagem, maior primo e soma parciais.

**"Como vocês sabem que a resposta está certa?"**
> Por três caminhos: um algoritmo independente (Crivo de Eratóstenes) dá a mesma
> resposta; os três campos funcionam como assinatura, então trocar um primo por outro
> seria detectado; e o valor de π(N) confere com a literatura.

**"Por que tantos blocos, e não um bloco por processo?"**
> Porque blocos de tamanho igual não têm custo igual: testar números grandes exige mais
> divisões, então o fim do intervalo é mais caro que o começo. Com um bloco por processo,
> quem pegasse o último seguraria todos os outros. Com muitos blocos numa fila, quem
> termina puxa o próximo, e a carga se equilibra sozinha.

### Augusto — não apresentou **problema** nem **seção crítica**

**"Onde exatamente é a seção crítica, e por que ela é tão pequena?"**
> É a função `_dobrar_no_estado`: somar o parcial do bloco nos três acumuladores globais.
> É pequena de propósito — se a trava envolvesse o laço de primalidade, o programa seria
> correto mas rodaria um processo por vez, e o speedup denunciaria isso.

**"Por que Lock e não semáforo ou monitor?"**
> Porque o que precisamos é exclusão mútua pura. Semáforo serve para limitar um recurso
> contável — não temos contagem a limitar. Monitor serve quando há condição de espera a
> sinalizar — não temos. Um mutex é a primitiva mínima que resolve o problema.

**"Como vocês provam que não há condição de corrida?"**
> De duas formas. Rodamos a versão paralela 5 vezes com a mesma entrada e os três campos
> vêm idênticos em todas. E temos o contraste: no `demo_corrida.py`, processos somando
> 100 mil incrementos cada — sem a trava o total vem errado e muda a cada execução; com a
> trava dá exatamente o valor esperado, sempre.

**"Por que processos e não threads?"**
> Porque o trabalho é limitado por processador, não por espera. Em CPython a GIL deixa só
> uma thread executando bytecode por vez, então threads não somam tempo de CPU. Nós
> medimos: com threads o speedup ficou **abaixo de 1** — pior que o sequencial, por causa
> da troca de contexto. Com processos passou de 3×.

---

## Se algo der errado no dia

| Problema | O que fazer |
|---|---|
| SSH não conecta (rede da faculdade) | Hotspot do celular. Se não der, **Plano B**: rodar local com o N do `preflight.py` |
| Instância parada | Ligue pelo console (~1 min) e confirme o IP público — ele **muda** ao religar |
| A página :8000 não abre | `ssh ... 'cd ~/primos/src && nohup python3 servidor_status.py --porta 8000 &'` |
| O sequencial não terminou a tempo | Mostre o `resultados.json` da véspera e diga que a execução ao vivo confirma o mesmo número |
| Deu erro de import | Rode de dentro de `src/`, ou `python preflight.py` para achar a causa |

---

## O que **não** pode acontecer (a lauda desconta por isso)

- [ ] Demonstração gravada ou em captura de tela → **tudo ao vivo**, inclusive o console.
- [ ] Speedup sem o tempo sequencial medido na mesma máquina e mesma entrada → por isso
      a medição da **véspera** tem que ser na máquina que vai apresentar.
- [ ] Console mostrado por print → **abrir o console logado** antes de começar.
- [ ] Estourar o tempo em mais de 2 minutos → por isso o sequencial começa no minuto 0.
- [ ] Integrante que não responde sobre a parte que não apresentou → ver acima.
