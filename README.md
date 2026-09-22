# Contagem paralela de primos — Etapa 1

**070080 Sistemas Distribuídos e Paralelos** · Turma CC6MA · Prof. Fábio Rocha de Araújo
**Equipe:** Cauê Barroso · César Ribeiro · Augusto Pereira

Conta os números primos do intervalo `[2, N]` em duas versões do mesmo programa —
**sequencial** e **paralela com processos** — mede o ganho na mesma máquina e com a
mesma entrada, e prova que as duas chegam ao mesmo resultado.

**Só biblioteca padrão do Python.** Nada para instalar (`requirements.txt` está vazio
de propósito).

---

## O resultado, em uma tabela

Medição em N = 20.000.000 (AMD Ryzen, 6 núcleos físicos / 12 lógicos, CPython 3.14.4,
mediana de 3 execuções por configuração — todas conferindo contra o crivo):

| Versão | Trabalhadores | Tempo | Speedup | Teto de Amdahl |
|---|---|---|---|---|
| sequencial | 1 | 128,62 s | 1,00× | — |
| processos | 2 | 66,77 s | 1,93× | 1,94× |
| processos | 4 | 34,47 s | 3,73× | 3,67× |
| **processos** | **6** | **25,74 s** | **5,00×** | 5,22× |
| processos | 8 | 26,73 s | 4,81× | 6,61× |
| threads | 4 | 140,53 s | **0,92×** | — (a GIL) |

Dois resultados para reparar. Com quatro threads o programa fica **mais lento que sem
paralelismo nenhum** — a evidência medida de que trabalho de CPU em CPython exige
processos. E **W = 8 é mais lento que W = 6**: a máquina tem 6 núcleos físicos, e pedir
mais paralelismo do que existe não é neutro, custa.

Os números completos, incluindo a fração serial medida (Karp-Flatt) e a análise do que
limitou o ganho, estão em [`docs/Relatorio-Etapa1.md`](docs/Relatorio-Etapa1.md) e em
`resultados/resultados.json`.

---

## Vai rodar em outra máquina? Comece por aqui

O N foi escolhido pela velocidade de um processador específico. Em outra máquina, o
mesmo N pode levar 40 segundos (e aí não cumpre "minutos, não segundos") ou 12 minutos
(e aí não cabe na apresentação). Antes de qualquer coisa, na máquina que for usar:

```bash
cd src
python preflight.py --alvo 150
```

Em menos de um minuto ele confere o ambiente, confere que `multiprocessing` funciona ali,
confere que sequencial, paralelo e crivo concordam — e **calibra o N para aquela máquina**,
imprimindo os comandos já preenchidos. Use esses valores em tudo, inclusive na medição
que vai para o relatório.

---

## Como rodar

```bash
cd src
```

| O quê | Comando |
|---|---|
| **Verificar a máquina e calibrar o N** | `python preflight.py --alvo 150` |
| Versão sequencial | `python sequencial.py -n 20000000` |
| Versão paralela (processos) | `python paralelo_processos.py -n 20000000 -w 4` |
| Versão com threads (evidência da GIL) | `python paralelo_threads.py -n 20000000 -w 4` |
| **Provar que o resultado é estável** | `python verificar.py -n 2750000 -w 6 -r 5` (~20 s) |
| **Mostrar a condição de corrida** | `python demo_corrida.py -p 6 -i 100000 -r 3` |
| **Medir tudo e calcular o speedup** | `python benchmark.py -n 20000000 -w 2,4,6,8 -r 3 --com-threads` |
| Log de eventos com carimbo de Lamport | `python lamport.py -n 200000 -w 4` |
| Página de status (porta do serviço) | `python servidor_status.py --porta 8000` |

Para regerar as tabelas do relatório a partir da medição:

```bash
python src/tabelas.py --entrada resultados/resultados.json
```

Para regerar o **PDF da entrega** depois de atualizar os números
(`docs/Relatorio-Etapa1.pdf`, 6 páginas):

```bash
# Windows
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new \
  --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="docs\Relatorio-Etapa1.pdf" "file:///C:/wks/projetofabio/docs/Relatorio-Etapa1.html"
```

Ou simplesmente abrir `docs/Relatorio-Etapa1.html` no navegador e dar **Ctrl+P** →
"Salvar como PDF" → ativar **"Gráficos de segundo plano"**.

---

## Como o problema atende aos requisitos da lauda

| Requisito | Como é atendido |
|---|---|
| Trabalho que se divide em partes independentes | Blocos de 10.000 inteiros; primalidade de um número não depende de nenhum outro. 2.000 blocos para N = 20 M. |
| Entrada grande o bastante para levar **minutos** | N = 20.000.000 → **128,62 s** sequenciais (medido). |
| Resultado verificável | Crivo de Eratóstenes (algoritmo **independente**) + assinatura de 3 campos + π(20 M) = 1.270.607 conhecido. |
| Estado compartilhado escrito por mais de um fluxo, protegido | Três `RawValue` em memória compartilhada, protegidos por `multiprocessing.Lock`. |
| Processos, e não threads, para trabalho de CPU | Justificado **e medido**: threads dão 0,92×, processos chegam a 5,00×. |
| Instância provisionada com grupo de segurança correto | `scripts/provisionar_aws.sh` ou o guia pelo console: 22/tcp só do IP da equipe, 8000/tcp para o serviço. |

---

## Onde está cada coisa

```
src/
  preflight.py             verifica a maquina da apresentacao e calibra o N   <- comece aqui
  primos.py                nucleo: teste de primalidade, unidade de trabalho, crivo
  sequencial.py            versao sequencial (linha de base do speedup)
  paralelo_processos.py    versao paralela + SECAO CRITICA + Lock   <- a solucao
  paralelo_threads.py      mesma coisa com threads: evidencia de que a GIL impede ganho
  demo_corrida.py          condicao de corrida com e sem trava, lado a lado
  verificar.py             prova de correcao e de estabilidade do resultado
  benchmark.py             protocolo de medicao: tempos, speedup, Amdahl, Karp-Flatt
  lamport.py               registro de eventos com carimbo logico de Lamport
  servidor_status.py       servico HTTP da porta 8000
  tabelas.py               gera as tabelas do relatorio a partir do JSON

scripts/
  provisionar_aws.sh       cria grupo de seguranca + instancia EC2
  executar_na_instancia.sh roda a medicao NA instancia e traz os resultados
  destruir_aws.sh          encerra tudo (a instancia custa enquanto estiver ligada)

docs/
  Ficha-Etapa1-preenchida.md   a ficha da oficina, respondida
  Relatorio-Etapa1.md          o relatorio tecnico (fonte)
  Relatorio-Etapa1.html        o mesmo relatorio, formatado para impressao
  Relatorio-Etapa1.pdf         A ENTREGA: 6 paginas, pronto para o ambiente virtual
  Provisionamento-Console.md   passo a passo da AWS pelo console, sem CLI
  AWS-Academy.md               o que muda no Learner Lab (sessao, tipos, regiao)
  Roteiro-Apresentacao.md      roteiro dos 10 minutos + preparo da arguicao

resultados/
  resultados.json          medicao completa em JSON (lida pelo servidor de status)
  medicao_console.txt      saida do benchmark
  eventos.log              log de eventos com carimbo de Lamport
```

---

## O caminho completo na nuvem

Os scripts abaixo usam o **AWS CLI**. Se ele nao estiver instalado, o guia
[`docs/Provisionamento-Console.md`](docs/Provisionamento-Console.md) faz o mesmo pelo
console web, sem instalar nada.

> **Usando AWS Academy / Learner Lab?** Leia
> [`docs/AWS-Academy.md`](docs/AWS-Academy.md) antes: a sessao expira e para a instancia,
> o IP publico muda ao religar, os tipos de instancia sao restritos e a regiao costuma ser
> fixa. Tudo isso afeta o que da para medir e o que escrever na secao 4 do relatorio.

```bash
# 1. provisiona (descobre o IP da equipe e restringe a porta 22 a ele)
./scripts/provisionar_aws.sh

# 2. mede NA instancia: sequencial e paralelo, mesma maquina, mesma entrada
./scripts/executar_na_instancia.sh 20000000 2,4,6,8

# 3. atualiza as tabelas do relatorio com os numeros da nuvem
python src/tabelas.py --entrada resultados/nuvem/resultados.json

# 4. depois da apresentacao: encerra tudo
./scripts/destruir_aws.sh
```

O provisionamento **aborta** se não conseguir descobrir o IP público da equipe, em vez
de abrir a porta administrativa para `0.0.0.0/0` — e ao final confere as regras e falha
se encontrar `0.0.0.0/0` na porta 22.

---

## Uso de inteligência artificial

Este projeto foi desenvolvido **com auxílio do Claude (Anthropic)**, usado como
ferramenta de apoio na escrita do código, na estruturação do relatório e na organização
da documentação.

As decisões de projeto — a escolha do problema, a estratégia de paralelização, o
posicionamento da seção crítica, a primitiva de sincronização e a arquitetura na nuvem —
foram revisadas e validadas pela equipe, que responde por elas na arguição.

**Todos os números apresentados são medições reais**, não estimativas: os tempos vêm da
execução de `benchmark.py` e estão registrados em `resultados/resultados.json` e
`resultados/medicao_console.txt`. Cada execução é conferida contra um algoritmo
independente (Crivo de Eratóstenes) antes de o tempo ser aceito.
