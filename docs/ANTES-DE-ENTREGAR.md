# Antes de entregar — os últimos ajustes

Tudo está pronto **menos três linhas**, que dependem de informação que só aparece quando
vocês abrirem o AWS Academy. Este guia diz exatamente o que mudar em cada cenário.

Tempo: **5 a 10 minutos**, fora a medição.

---

## Passo 1 — Descubra dois números no console

Start Lab → EC2 → *Executar instâncias*. Anote:

- **Qual o maior tipo de instância disponível?** (procure por `xlarge` ou `2xlarge`)
- **Qual a região?** (canto superior direito — provavelmente `us-east-1`)

Agora vá para o cenário que corresponde.

---

## Cenário A — Há instância com 4 vCPU ou mais

*(`m5.xlarge`, `c5.xlarge`, `m5.2xlarge`, `c5.2xlarge`…)*

**O melhor caso.** Dá para medir na EC2 e ficar com todos os critérios.

1. Provisione pelo console — [`Provisionamento-Console.md`](Provisionamento-Console.md)
2. Na instância:
   ```bash
   sudo dnf -y install git python3
   git clone https://github.com/cauebarroso/sdp-etapa1-primos-paralelos.git primos
   cd primos/src
   python3 preflight.py --alvo 150      # calibra o N para ESTA instancia
   python3 benchmark.py -n <N> -w 2,<W> -r 3 --com-threads --threads-w <W>
   ```
3. Traga o `resultados.json`, rode `python src/tabelas.py --entrada <arquivo>` e **substitua
   a tabela da seção 5** do `Relatorio-Etapa1.html`
4. Ajuste as **três linhas** da seção 4 (ver "As três linhas", abaixo)
5. Regere PDF e ZIP (ver "Regerar", abaixo)

---

## Cenário B — Só há instâncias de 2 vCPU

*(`m5.large`, `t3.medium`, `t2.micro`…)*

Com **um núcleo físico não existe paralelismo a demonstrar**. Forçar a medição ali daria
um speedup perto de 1, que *parece* culpa do código quando é limite do ambiente.

Faça as duas coisas:

1. **Provisione mesmo assim e rode a aplicação lá.** O critério de provisionamento e
   controle de acesso (0,5) avalia que os recursos existem, foram criados por vocês e são
   mostrados ao vivo, com a porta administrativa restrita — nada disso depende do tamanho
   da instância.
2. **Mantenha a medição da máquina local** e acrescente **uma frase** na seção 5 do
   relatório, logo antes da tabela:

   > *O ambiente acadêmico disponibiliza apenas instâncias de 2 vCPU (um núcleo físico),
   > onde não há ganho de paralelismo a medir. A aplicação foi executada na instância para
   > verificação, e a medição de desempenho foi feita em máquina com 6 núcleos físicos,
   > descrita abaixo.*

Reconhecer o limite do ambiente e explicar a decisão é resultado defensável. Um speedup
de 1,05× sem explicação, não.

---

## Cenário C — Não deu para provisionar nada

Aí a seção 4 **não pode** ficar como está, porque descreve recursos que não existem.
Troque o primeiro parágrafo da seção 4 por:

> *Os recursos abaixo constituem a arquitetura projetada pela equipe. Por indisponibilidade
> do ambiente acadêmico no prazo, a execução e a medição foram realizadas em máquina local,
> descrita na seção 5.*

E troque os verbos da tabela de "é" para "seria". Perde-se o critério de provisionamento
(0,5), mas os outros 2,5 seguem íntegros — e o relatório não afirma nada falso.

---

## As três linhas da seção 4

No `Relatorio-Etapa1.html`, procure por `c5.2xlarge` (aparece duas vezes) e `sa-east-1`:

| O que dizia | Troque por |
|---|---|
| `sa-east-1` (São Paulo), uma zona (`sa-east-1a`) | a região e a zona reais |
| 1 × `c5.2xlarge` — 8 vCPU (4 núcleos físicos), 16 GiB | o tipo real e seus vCPU/núcleos |
| "São Paulo dá a menor latência…" | "a região é a disponível no ambiente acadêmico" |

**O argumento do SLA não muda:** continua 99,5 % para instância isolada em uma zona,
contra 99,99 % para duas ou mais, com os 216 minutos por mês. Isso vale em qualquer região.

**A justificativa da porta 22 não muda nada.** É o que mais pesa nesse critério.

---

## Regerar PDF e ZIP

Depois de editar o HTML:

```powershell
# PDF (confira que continua em 6 paginas)
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new `
  --disable-gpu --no-pdf-header-footer `
  --print-to-pdf="C:\wks\projetofabio\docs\Relatorio-Etapa1.pdf" `
  "file:///C:/wks/projetofabio/docs/Relatorio-Etapa1.html"

# ZIP da entrega
.\scripts\gerar_zip_entrega.ps1
```

E publique a versão nova:

```bash
git add -A && git commit -m "Atualiza secao 4 e medicao com os dados reais" && git push
```

---

## Checklist final

- [ ] Seção 4 corresponde ao que realmente existe
- [ ] Seção 5 traz a medição da máquina que realmente mediu
- [ ] PDF regerado e ainda com **6 páginas ou menos**
- [ ] ZIP regerado (`gerar_zip_entrega.ps1`)
- [ ] Push feito, link do repositório publicado no ambiente virtual
- [ ] Se o repositório for privado, professor adicionado como colaborador
