# Provisionar pelo console da AWS — passo a passo

Os scripts em `scripts/` fazem isso pelo AWS CLI. **Este guia faz o mesmo pelo console
web**, que não exige instalar nada — e é o console que a lauda manda mostrar ao vivo.

Tempo: **15 a 25 minutos**, a maior parte esperando a instância subir.

---

## Antes: descubra o seu IP público

Abra <https://checkip.amazonaws.com> e anote o número. Você vai precisar dele no passo 2.

> Se provisionar de casa e apresentar na faculdade, **o IP muda** e o SSH vai ser recusado.
> Nesse caso, repita o passo 2 na rede da apresentação e adicione o IP novo.

---

## 1. Escolher a região

Canto superior direito do console → selecione **América do Sul (São Paulo) `sa-east-1`**.

Se a conta for **AWS Academy / Learner Lab**, a região costuma estar travada em
`us-east-1` — nesse caso use a que estiver disponível e **corrija a região na seção 4 do
relatório**. O argumento sobre SLA (99,5 % para uma zona) continua valendo igual.

---

## 2. Criar o grupo de segurança

EC2 → **Grupos de segurança** → *Criar grupo de segurança*.

| Campo | Valor |
|---|---|
| Nome | `sg-primos-etapa1` |
| Descrição | `Etapa 1: SSH so da equipe, 8000 para a pagina de status` |
| VPC | a padrão |

**Regras de entrada — exatamente duas:**

| Tipo | Porta | Origem | Descrição |
|---|---|---|---|
| SSH | 22 | **Meu IP** | `acesso administrativo da equipe` |
| TCP personalizado | 8000 | `0.0.0.0/0` | `porta do servico: pagina de status` |

> **Na porta 22, escolha "Meu IP", nunca "Qualquer lugar".** O console preenche o seu
> `/32` sozinho. Porta administrativa aberta para `0.0.0.0/0` **zera** o critério de
> provisionamento — está escrito na lauda.

Regras de saída: deixe o padrão.

---

## 3. Criar o par de chaves

EC2 → **Pares de chaves** → *Criar par de chaves*.

| Campo | Valor |
|---|---|
| Nome | `chave-primos-etapa1` |
| Tipo | RSA |
| Formato | `.pem` (OpenSSH) |

O download acontece **uma única vez**. Guarde o arquivo e **copie para o notebook que vai
apresentar**. No Windows, se o SSH reclamar de permissão:

```powershell
icacls chave-primos-etapa1.pem /inheritance:r /grant:r "$($env:USERNAME):(R)"
```

---

## 4. Lançar a instância

EC2 → **Instâncias** → *Executar instâncias*.

| Campo | Valor |
|---|---|
| Nome | `primos-etapa1` |
| Imagem | **Amazon Linux 2023** (x86_64) |
| Tipo | **`c5.2xlarge`** — 8 vCPU / 4 núcleos físicos |
| Par de chaves | `chave-primos-etapa1` |
| Grupo de segurança | *selecionar existente* → `sg-primos-etapa1` |
| Armazenamento | 20 GiB, **gp3** |
| Sub-rede | qualquer uma — **anote a zona** (ex.: `sa-east-1a`) |

**Anote a zona de disponibilidade**: ela entra no relatório e você vai citá-la na
apresentação.

### Se `c5.2xlarge` não estiver disponível

Em contas de laboratório os tipos costumam ser restritos. Escolha, nesta ordem de
preferência, o maior que a conta permitir:

| Alternativa | vCPU | Núcleos físicos | Serve? |
|---|---|---|---|
| `c5.2xlarge` | 8 | 4 | ideal |
| `c5.xlarge` / `c6i.xlarge` | 4 | 2 | bom — meça W = 2 e 4 |
| `m5.large` / `t3.large` | 2 | 1 | **ruim** — ver abaixo |

> **Com 2 vCPU (1 núcleo físico) não há o que demonstrar:** o speedup vai ficar perto de
> 1 e a análise fica sem sentido. Se for esse o limite da conta, **é mais honesto medir no
> notebook da apresentação** e declarar isso no relatório do que forçar um número ruim numa
> instância que não tem núcleo. A instância continua valendo para o critério de
> provisionamento e controle de acesso.

**Corrija a seção 4 do relatório** com o tipo, a região e a zona que você realmente usou.

---

## 5. Conferir o que foi criado (é isto que se mostra ao vivo)

Instâncias → selecione `primos-etapa1` → aba **Segurança** → clique no grupo.

Confira na tela:

- [ ] Estado **Executando**, e o **IP público IPv4** anotado
- [ ] **Tipo** e **zona de disponibilidade** conferem com o relatório
- [ ] Entrada: **22/tcp** com origem `<seu IP>/32` — **não** `0.0.0.0/0`
- [ ] Entrada: **8000/tcp** com origem `0.0.0.0/0`
- [ ] Nenhuma outra regra de entrada

---

## 6. Colocar o código na instância e medir

```bash
ssh -i chave-primos-etapa1.pem ec2-user@<IP-PUBLICO>
```

Na instância:

```bash
sudo dnf -y install git python3
git clone <url-do-repositorio> primos     # ou envie por scp
cd primos/src

python3 preflight.py --alvo 150           # calibra o N para ESTA instancia
```

O `preflight` imprime o N e o W certos para a instância. Use-os:

```bash
python3 benchmark.py -n <N> -w 2,<W> -r 3 --com-threads --threads-w <W>
```

Leva ~20 minutos. Depois, para publicar a página na porta do serviço:

```bash
nohup python3 servidor_status.py --porta 8000 > ~/servidor.log 2>&1 &
```

Abra `http://<IP-PUBLICO>:8000/` no navegador — é esta página que você mostra na parte 3
da apresentação.

---

## 7. Trazer os números para o relatório

Na sua máquina:

```bash
scp -i chave-primos-etapa1.pem ec2-user@<IP>:~/primos/resultados/resultados.json \
    resultados/nuvem/resultados.json

python src/tabelas.py --entrada resultados/nuvem/resultados.json
```

Cole as tabelas na seção 5 do relatório, ajuste a seção 4 com região/zona/tipo reais, e
regere o PDF (comando no README).

---

## 8. Depois da apresentação

EC2 → Instâncias → selecione → **Encerrar instância**. A instância custa enquanto estiver
ligada.

> Se apenas **parar** em vez de encerrar, o **IP público muda** ao religar. Confira o IP
> novo antes de apresentar.
