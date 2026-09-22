# AWS Academy (Learner Lab) — o que muda

O Learner Lab não é uma conta AWS comum. Quatro diferenças afetam este projeto
diretamente. Leia antes de provisionar.

---

## 1. A sessão expira, e a instância para junto

O laboratório roda em sessões de algumas horas. **Quando a sessão acaba, as instâncias
EC2 são paradas automaticamente** (não destruídas — os dados do disco ficam).

O que isso significa para vocês:

- **Iniciar o lab é o passo zero do dia da apresentação.** Sem o lab iniciado, o console
  não mostra nada e a instância está parada.
- **Ao religar, o IP público MUDA.** Todo comando `ssh` e a URL `http://<IP>:8000/`
  precisam ser refeitos com o IP novo.
- **Reserve tempo.** Iniciar o lab + ligar a instância + conferir o IP leva alguns
  minutos. Não deixe para os 5 minutos antes de apresentar.

> Por isso a decisão "instância criada por execução" registrada no relatório **é ainda
> mais verdadeira** no Academy: o ambiente impõe esse ciclo. Isso joga a favor de vocês na
> arguição — a escolha combina com a realidade do ambiente.

---

## 2. Os tipos de instância são restritos

A `c5.2xlarge` do relatório **provavelmente não está liberada**. O Learner Lab costuma
permitir apenas famílias e tamanhos pequenos.

**Descubra o que a sua conta permite:** no console, EC2 → Executar instâncias → abra a
lista de tipos. Ou tente lançar e veja se dá erro de política.

Escolha o maior disponível, nesta ordem:

| Tipo | vCPU | Núcleos físicos | Serve para medir? |
|---|---|---|---|
| `m5.2xlarge` / `c5.2xlarge` | 8 | 4 | ideal — meça W = 2, 4, 8 |
| `m5.xlarge` / `c5.xlarge` | 4 | 2 | bom — meça W = 2 e 4 |
| `m5.large` / `t3.medium` | 2 | **1** | **não serve** — ver abaixo |
| `t2.micro` | 1 | 1 | não serve |

### Se só houver instâncias de 2 vCPU

Com **um núcleo físico não há paralelismo real a demonstrar**: o speedup fica perto de 1 e
a análise de Amdahl perde o sentido. Forçar a medição ali produziria um número ruim que
*parece* culpa do código, quando é limitação do ambiente.

O caminho honesto tem duas partes, e preserva a maior parte da nota:

1. **Provisione a instância mesmo assim.** O critério de *provisionamento e controle de
   acesso* (0,5) avalia que os recursos existem, foram criados pela equipe e são mostrados
   ao vivo no console, com a porta administrativa restrita. Isso independe do tamanho.
   Rode a aplicação lá para provar que executa.
2. **Meça no notebook da apresentação** e **declare isso no relatório**, em uma frase na
   seção 5: que o tipo de instância disponível no ambiente acadêmico tem um núcleo físico,
   que isso impede medir ganho, e que a medição foi feita em máquina com N núcleos.

Reconhecer a limitação do ambiente e explicar a decisão é um resultado defensável. Um
speedup de 1,05× apresentado sem explicação, não.

---

## 3. As credenciais são temporárias

O Learner Lab entrega credenciais que **expiram junto com a sessão**. Consequências:

- Os scripts `scripts/*.sh` funcionam, mas você precisa recarregar as credenciais a cada
  sessão (botão **AWS Details** → **AWS CLI** no lab, que mostra o bloco para colar em
  `~/.aws/credentials`).
- **Se o AWS CLI não estiver instalado, use o console** — veja
  [`Provisionamento-Console.md`](Provisionamento-Console.md). Tudo o que os scripts fazem,
  o console faz, e é o console que a lauda manda mostrar ao vivo de qualquer forma.

---

## 4. A região costuma ser fixa

O Learner Lab normalmente trava a região em **`us-east-1`** (Norte da Virgínia).

Se for o caso, **corrija a seção 4 do relatório**: troque `sa-east-1` / `sa-east-1a` pela
região e zona reais. O argumento sobre SLA **não muda** — continua sendo 99,5 % para
instância isolada em uma zona, contra 99,99 % para duas ou mais, e os 216 minutos por mês
continuam valendo. O que muda é só o nome da região, e a justificativa de latência deixa
de se aplicar (troque por: a região é a disponível no ambiente acadêmico).

---

## Checklist do Learner Lab

**Na véspera:**

- [ ] Iniciar o lab (botão **Start Lab**, até o círculo ficar verde)
- [ ] Descobrir qual tipo de instância está liberado
- [ ] Provisionar pelo console (grupo de segurança com 22 restrita + 8000)
- [ ] Rodar `preflight.py` na instância para calibrar o N **dela**
- [ ] Medir, trazer o `resultados.json`, atualizar relatório e regerar o PDF
- [ ] Corrigir região, zona e tipo na seção 4 do relatório

**No dia:**

- [ ] **Start Lab** antes de tudo
- [ ] Ligar a instância e **anotar o IP novo** (ele mudou)
- [ ] Liberar o IP da rede da faculdade na porta 22 (regra do grupo de segurança)
- [ ] Subir a página de status e testar `http://<IP-novo>:8000/`
- [ ] Console aberto e logado, na tela da instância
