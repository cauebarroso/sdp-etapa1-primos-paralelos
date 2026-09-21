#!/usr/bin/env bash
# =============================================================================
# Roda a medicao NA INSTANCIA e traz os resultados de volta.
#
# A lauda exige que o tempo sequencial e o tempo paralelo sejam medidos na
# MESMA maquina e com a MESMA entrada. Este script garante isso: as duas
# versoes rodam na mesma instancia EC2, numa unica invocacao do benchmark.
#
# Uso:  ./executar_na_instancia.sh [N] [lista_de_W]
#       ./executar_na_instancia.sh 20000000 2,4,8
# =============================================================================
set -euo pipefail

REGIAO="${REGIAO:-sa-east-1}"
NOME="${NOME:-primos-etapa1}"
CHAVE="${CHAVE:-chave-primos-etapa1}"
PORTA_SERVICO="${PORTA_SERVICO:-8000}"
N="${1:-20000000}"
LISTA_W="${2:-2,4,8}"
REPETICOES="${REPETICOES:-3}"

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

IP_PUBLICO=$(aws ec2 describe-instances --region "$REGIAO" \
  --filters "Name=tag:Name,Values=$NOME" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

if [[ -z "$IP_PUBLICO" || "$IP_PUBLICO" == "None" ]]; then
  echo "ERRO: nenhuma instancia '$NOME' em execucao na regiao $REGIAO." >&2
  echo "      Rode ./provisionar_aws.sh antes." >&2
  exit 1
fi

SSH=(ssh -i "$HOME/.ssh/$CHAVE.pem" -o StrictHostKeyChecking=accept-new "ec2-user@$IP_PUBLICO")

echo "instancia: $IP_PUBLICO"
echo
echo "[1/4] Enviando o codigo..."
"${SSH[@]}" 'mkdir -p ~/primos/src ~/primos/resultados'
scp -i "$HOME/.ssh/$CHAVE.pem" -o StrictHostKeyChecking=accept-new \
    "$RAIZ"/src/*.py "ec2-user@$IP_PUBLICO:~/primos/src/"

echo
echo "[2/4] Ambiente da instancia:"
"${SSH[@]}" 'python3 -VV; echo "nucleos logicos: $(nproc)"; \
             echo "nucleos fisicos: $(lscpu | awk -F: "/^Core\\(s\\) per socket/{c=\$2} /^Socket\\(s\\)/{s=\$2} END{print c*s}")"'

echo
echo "[3/4] Medindo (N=$N, W=$LISTA_W, $REPETICOES execucoes por configuracao)..."
echo "      As duas versoes rodam AQUI, na mesma maquina e com a mesma entrada."
"${SSH[@]}" "cd ~/primos/src && python3 benchmark.py \
    -n $N -w $LISTA_W -r $REPETICOES --com-threads --threads-w 4 \
    --p-estimado 0.97 --saida ../resultados/resultados.json \
    2>&1 | tee ../resultados/medicao_console.txt"

echo
echo "[4/4] Trazendo os resultados para o repositorio..."
mkdir -p "$RAIZ/resultados/nuvem"
scp -i "$HOME/.ssh/$CHAVE.pem" -o StrictHostKeyChecking=accept-new \
    "ec2-user@$IP_PUBLICO:~/primos/resultados/resultados.json" \
    "$RAIZ/resultados/nuvem/resultados.json"
scp -i "$HOME/.ssh/$CHAVE.pem" -o StrictHostKeyChecking=accept-new \
    "ec2-user@$IP_PUBLICO:~/primos/resultados/medicao_console.txt" \
    "$RAIZ/resultados/nuvem/medicao_console.txt"

echo
echo "Resultados em resultados/nuvem/. Para atualizar as tabelas do relatorio:"
echo "    python src/tabelas.py --entrada resultados/nuvem/resultados.json"
echo
echo "Para publicar a pagina de status na porta $PORTA_SERVICO (deixe rodando"
echo "durante a apresentacao, e abra http://$IP_PUBLICO:$PORTA_SERVICO/):"
echo "    ssh -i ~/.ssh/$CHAVE.pem ec2-user@$IP_PUBLICO \\"
echo "        'cd ~/primos/src && nohup python3 servidor_status.py --porta $PORTA_SERVICO \\"
echo "         --arquivo ../resultados/resultados.json > ~/primos/servidor.log 2>&1 &'"
