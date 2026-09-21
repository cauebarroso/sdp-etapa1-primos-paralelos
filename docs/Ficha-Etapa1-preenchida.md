# Ficha da Etapa 1 — Projeto de Solução Distribuída

**Disciplina:** 070080 Sistemas Distribuídos e Paralelos · **Turma:** CC6MA
**Professor:** Fábio Rocha de Araújo · **Entrega da Etapa 1:** 22/09

---

## A. Equipe e problema

**Integrantes:**

| # | Nome | Matrícula |
|---|---|---|
| 1 | Cauê Barroso | *(preencher)* |
| 2 | Cesár Ribeiro | *(preencher)* |
| 3 | Augusto Pereira | *(preencher)* |

**Problema escolhido:**

> **Contagem verificável de números primos no intervalo [2, N], por divisão
> sucessiva, com N = 20.000.000.** O programa devolve três números que
> identificam o intervalo: quantos primos existem, qual é o maior, e a soma de
> todos eles.

**Por que ele atende às quatro condições:**

| Condição | Resposta da equipe |
|---|---|
| **O trabalho se divide em partes independentes? Em que unidade?** | Sim. A unidade de trabalho é um **bloco de 10.000 inteiros consecutivos**, `[início, fim)`. Decidir se um número é primo não depende de nenhum outro número do intervalo: cada bloco é resolvido sozinho e devolve um resumo parcial. Para N = 20 milhões são **2.000 blocos** independentes. |
| **Qual é o volume da entrada, e quanto tempo a versão sequencial deve levar?** | Entrada: N = 20.000.000 — 20 milhões de candidatos a testar, dos quais 1.270.607 são primos. A versão sequencial leva **2 min 13 s** (133,46 s medidos, mediana de 3 execuções). Minutos, não segundos, como a lauda exige. |
| **Como se verifica que o resultado está correto?** | Três camadas. (1) **Assinatura de três campos** — contagem, maior primo e soma: errar um primo por outro muda pelo menos um dos três. (2) **Algoritmo independente** — um Crivo de Eratóstenes calcula a mesma resposta por outro caminho em menos de 1 s; se os dois concordam, não é um erro comum aos dois. (3) **Valor externo conhecido** — π(20.000.000) = 1.270.607 confere com a literatura. Além disso a versão paralela é repetida 5× com a mesma entrada e precisa devolver o mesmo trio. |
| **Que estado é escrito por mais de um fluxo?** | Os **três acumuladores globais em memória compartilhada** (`multiprocessing.RawValue`): `contagem`, `maior` e `soma`. Todo trabalhador, ao terminar um bloco, funde o seu parcial nesses três. |

---

## B. Estratégia de paralelização

| Decisão | Escolha | Justificativa |
|---|---|---|
| **Paralelismo de dados ou de tarefas** | **De dados** | Todos os trabalhadores executam **a mesma operação** (`resumo_intervalo`) sobre **fatias diferentes do mesmo domínio** [2, N]. Não há etapas distintas de um pipeline que pudessem virar tarefas diferentes. |
| **Processo ou thread** | **Processo** (`multiprocessing`) | O trabalho é **limitado por processador**, não por espera: o laço quente é divisão inteira em Python puro, sem disco, sem rede, sem banco. Em CPython a GIL deixa só uma thread executando bytecode por vez, então threads não somam tempo de CPU. **Medimos as duas versões**: com threads o speedup fica em ~0,9× (pior que o sequencial, por causa da troca de contexto); com processos passa de 3×. Cada processo tem seu interpretador e sua GIL, e ocupa um núcleo de verdade. |
| **Quantos trabalhadores em paralelo** | **W = número de núcleos físicos** (4 na instância `c5.2xlarge`). Medimos **W = 2, 4 e 8** | Trabalho de CPU não ganha nada com mais trabalhadores que núcleos: acima disso os processos passam a disputar o mesmo núcleo. Medir 2, 4 e 8 mostra a curva subindo e depois saturando — e W = 8 acima dos núcleos físicos documenta a saturação, em vez de escondê-la. |
| **Como o trabalho é dividido entre eles** | **Fila de 2.000 blocos com balanceamento dinâmico** | Os blocos vão para uma `multiprocessing.Queue`; cada trabalhador puxa o próximo assim que termina o anterior. Blocos de tamanho igual **não** têm custo igual — testar primalidade de números grandes exige mais divisões que de números pequenos, então o fim do intervalo custa mais que o começo. Com **T ≫ W** (2.000 blocos para até 8 trabalhadores), a fila redistribui essa diferença sozinha; com um bloco fixo por trabalhador, quem pegasse o fim do intervalo seguraria todo mundo. |

> **A justificativa de processo ou thread precisa dizer se o trabalho é limitado por processador ou por espera.**
> É limitado por **processador**. É exatamente o caso que a ficha adverte: implementado com threads, o speedup mede ~1. Por isso `paralelo_threads.py` está no repositório — não como solução, mas como **evidência medida** de que a escolha por processos é a correta.

---

## C. Sincronização

| Item | Resposta da equipe |
|---|---|
| **Que estrutura é compartilhada e escrita por mais de um fluxo** | Três inteiros de 64 bits em memória compartilhada entre processos (`multiprocessing.RawValue('q')`): `contagem` (total de primos), `maior` (maior primo visto) e `soma` (soma de todos os primos). São o resultado global do programa, e todos os W trabalhadores escrevem nos três. |
| **Qual é o menor trecho que precisa ser indivisível (a seção crítica)** | A **fusão do parcial local no global** — e só ela: `contagem.value += local.contagem`; `if local.maior_primo > maior.value: maior.value = local.maior_primo`; `soma.value += local.soma`. São três sequências de leitura-modificação-escrita, que não são atômicas. O laço de primalidade, que é 99 % do tempo, fica **fora** da trava. Ver `src/paralelo_processos.py`, função `_dobrar_no_estado`. |
| **Que primitiva vai protegê-la: lock, semáforo ou monitor** | **Lock** (`multiprocessing.Lock`, usado como `with trava:`). É exclusão mútua pura: não há recurso contável a limitar (que pediria semáforo) nem condição de espera a sinalizar (que pediria monitor). Um mutex é a primitiva mínima que resolve, e a mínima é a certa. |
| **Como a equipe vai demonstrar que o resultado ficou estável** | Dois testes, os dois ao vivo. (1) `verificar.py` roda a versão paralela **5 vezes com a mesma entrada** e imprime os três campos de cada execução: todas idênticas, e idênticas ao crivo e ao sequencial. (2) `demo_corrida.py` mostra o **contraste**: 6 processos somando 100.000 incrementos cada — **sem a trava** o total vem errado e diferente a cada execução (perde ~45 % dos incrementos); **com a trava** dá exatamente 600.000, toda vez. É a prova de que a trava é o que segura o resultado, e não sorte. |

**Se a aplicação tiver mais de um processo trocando mensagem, descreva o que cada registro de evento vai conter:**

> **Há troca de mensagem.** O coordenador envia blocos aos trabalhadores por uma fila,
> e os trabalhadores devolvem registros de evento por outra. Processos separados não
> compartilham relógio confiável, então a ordem é dada por **carimbo lógico de Lamport**.
> Implementação em `src/lamport.py`; saída em `resultados/eventos.log`.
>
> Cada registro contém os quatro campos:
>
> | Campo | Conteúdo | Exemplo |
> |---|---|---|
> | **quem** | processo que gerou o evento | `C0` (coordenador), `T1`…`Tn` (trabalhadores) |
> | **o quê** | tipo do evento | `ENVIA_BLOCO`, `RECEBE_BLOCO`, `CALCULA`, `ENTRA_SC`, `SAI_SC` |
> | **carimbo lógico** | relógio de Lamport no instante do evento | `4` |
> | **sobre o quê** | recurso a que o evento se refere | `[100002,150002)` ou `estado_global` |
>
> Regras aplicadas: evento local → `L = L + 1`; envio → `L = L + 1` e a mensagem viaja
> com `L`; recebimento → `L = max(L, L_msg) + 1`. O log mostra a causalidade: o
> coordenador envia um bloco com carimbo 1 e o trabalhador que o recebe registra
> carimbo 2 — nunca o contrário.

---

## D. Medição de desempenho

| Item | Resposta da equipe |
|---|---|
| **Máquina em que as duas versões serão medidas** | A **instância EC2 provisionada pela equipe** (`c5.2xlarge`, região `sa-east-1`). As duas versões rodam na mesma instância, na mesma invocação de `benchmark.py`, com a mesma entrada. Antes disso, a medição de referência foi feita na máquina de desenvolvimento (Ryzen, Windows 11, CPython 3.14.4) para validar o protocolo. |
| **Número de núcleos disponíveis nela** | `c5.2xlarge`: 8 vCPU = **4 núcleos físicos** (cada vCPU é uma thread de um núcleo x86). Para trabalho de CPU o que escala é o número de núcleos **físicos**, por isso W = 4 é o ponto esperado de melhor eficiência. |
| **Volume de entrada fixado para as medições** | **N = 20.000.000**, idêntico em todas as execuções e em todas as versões. Fixado por parâmetro (`-n`), nunca alterado entre a medição sequencial e a paralela. |
| **Como o tempo sequencial será obtido** | `benchmark.py` chama `sequencial.executar(N)` **3 vezes**, cronometrando com `time.perf_counter()`, e usa a **mediana** das três. É a mesma invocação do programa que em seguida mede a versão paralela — mesma máquina, mesma entrada, mesmo processo de medição, sem reinício entre uma e outra. |
| **Fração do trabalho que a equipe estima ser paralelizável** | **p = 0,97.** O que não paraleliza: criar os processos (`spawn` reinicia o interpretador em cada um), serializar e passar 2.000 blocos pela fila, e as 2.000 entradas na seção crítica. Tudo isso é custo fixo ou quase fixo; o laço de primalidade, que é o resto, paraleliza inteiro. |
| **Speedup previsto pela lei de Amdahl, com essa fração e esse número de núcleos** | Com **p = 0,97**: **n = 2 → 1,94×**; **n = 4 → 3,67×**; **n = 8 → 6,61×**. O cálculo para n = 4: `S = 1 / (0,03 + 0,97/4) = 1 / 0,2725 = 3,67`. |

> **Resultado já medido** (N = 20.000.000, 6 núcleos físicos, mediana de 3 execuções):
> sequencial **133,46 s**; W = 2 → **1,83×**; W = 4 → **3,02×**; W = 8 → **4,52×**
> (133,5 s → 29,5 s). Com **threads**, W = 4 → **0,91×** — mais lento que o sequencial,
> que é a evidência da GIL. Todas as 15 execuções deram o mesmo resultado do crivo.
>
> **O relatório de 22/09 compara o speedup medido com esse número previsto e explica a
> diferença.** Além do teto de Amdahl, o `benchmark.py` calcula a **fração serial medida**
> (métrica de Karp-Flatt): a partir do speedup que realmente aconteceu, descobre qual
> fração serial explicaria aquele número. Se essa fração **cresce** conforme W aumenta,
> a perda não é só a parte serial do algoritmo — é custo que **cresce com o número de
> trabalhadores** (criar processos, passar blocos, disputar a trava). É isso que separa
> "o programa tem uma parte serial" de "o paralelismo está custando caro".

---

## E. Arquitetura na nuvem

| Decisão | Escolha da equipe | Justificativa |
|---|---|---|
| **Região, e em quantas zonas de disponibilidade** | `sa-east-1` (São Paulo), **uma única zona** (`sa-east-1a`) | São Paulo dá a menor latência para a equipe operar e demonstrar ao vivo. Com instância isolada em uma zona, **o compromisso de SLA que passa a valer é o de 99,5 %** — ou seja, **216 minutos** de indisponibilidade admitida num mês de 30 dias (os 99,99 % / 4,3 minutos exigiriam instâncias distribuídas por duas ou mais zonas). **Aceitamos os 99,5 % de propósito**: a carga é um **lote** que roda até terminar em poucos minutos, não um serviço 24×7; se a instância cair, repete-se a execução sem prejuízo. E há uma razão de método: a lauda exige que sequencial e paralelo sejam medidos **na mesma máquina** — espalhar por duas zonas exigiria duas instâncias, dobraria o custo e não melhoraria em nada a medição. |
| **Família, tamanho e quantidade de instâncias** | **1 ×** `c5.2xlarge` (compute-optimized, 8 vCPU / 4 núcleos físicos, 16 GiB) | A família `c` é a otimizada para **CPU**, que é exatamente o nosso gargalo; famílias `t` (burstable) entregariam créditos de CPU que expiram no meio de uma medição de minutos e contaminariam o tempo. Memória não é gargalo: o programa não guarda a lista de primos, só acumula três inteiros — usa poucos MB. Uma instância basta porque o problema é de paralelismo **dentro** de uma máquina (memória compartilhada entre processos), não de distribuição entre máquinas. |
| **Onde ficam a entrada e a saída, e qual o volume** | **Volume EBS gp3 de 20 GB** (disco raiz da instância). Entrada: **nenhum arquivo** — a entrada é o parâmetro N (um inteiro), e os 2.000 blocos são gerados em memória. Saída: `resultados.json` (~4 KB), `medicao_console.txt` (~2 KB) e `eventos.log` (poucos KB) | Os dados são **minúsculos**: não há por que envolver S3, que acrescentaria latência de rede dentro do laço de medição, permissões de IAM e um ponto de falha a mais, sem nenhum ganho. 20 GB é o menor tamanho que acomoda o Amazon Linux 2023 com folga. O código chega por `scp` (dezenas de KB) e os resultados voltam por `scp` para o repositório. |
| **Portas abertas, e a origem de cada regra** | **22/tcp (administrativa, SSH)** ← `<IP público da equipe>/32`, origem única. **8000/tcp (serviço, página de status HTTP)** ← `0.0.0.0/0`. Nenhuma outra porta de entrada | **Por que a porta administrativa não está aberta para `0.0.0.0/0`:** SSH exposto ao mundo recebe varredura automatizada e tentativa de força bruta de forma contínua; com a porta administrativa pública, qualquer falha de credencial vira **controle total da instância**, e não um incidente contido. A superfície de administração só precisa ser alcançável **de onde a equipe realmente administra**, então a regra usa o `/32` do IP da equipe. O script `provisionar_aws.sh` **aborta** se não conseguir descobrir esse IP, em vez de cair para `0.0.0.0/0`, e no fim confere a regra e falha se encontrar `0.0.0.0/0` na porta 22. A 8000 é aberta porque é a porta do **serviço** e serve apenas uma página **somente leitura**, sem autenticação a proteger e sem rota que altere estado — e é por ela que o professor abre o resultado durante a apresentação. |
| **A instância fica ligada, ou é criada por execução** | **Criada por execução** — ciclo `provisionar_aws.sh` → `executar_na_instancia.sh` → `destruir_aws.sh` | A carga é um lote de poucos minutos; manter a instância ligada fora desses minutos é custo sem uso. Ela fica ligada apenas durante a janela da medição e durante a apresentação (para a demonstração ao vivo no console e a página de status na porta 8000), e é destruída logo depois. Como não há estado a preservar entre execuções — a entrada é um parâmetro e a saída são poucos KB que voltam por `scp` —, recriar a instância não custa nada além do tempo de inicialização. |

---

## Onde está cada coisa no repositório

| Item da ficha | Arquivo |
|---|---|
| Unidade de trabalho e teste de primalidade | `src/primos.py` |
| Versão sequencial (linha de base) | `src/sequencial.py` |
| Versão paralela, seção crítica e trava | `src/paralelo_processos.py` |
| Evidência de que threads não servem (GIL) | `src/paralelo_threads.py` |
| Demonstração de condição de corrida vs. trava | `src/demo_corrida.py` |
| Verificação e estabilidade do resultado | `src/verificar.py` |
| Medição, speedup e Amdahl | `src/benchmark.py` |
| Registro de eventos com carimbo de Lamport | `src/lamport.py` |
| Serviço da porta 8000 | `src/servidor_status.py` |
| Provisionamento e regras do grupo de segurança | `scripts/provisionar_aws.sh` |
