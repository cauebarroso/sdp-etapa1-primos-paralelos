#!/usr/bin/env bash
# =============================================================================
# Remove tudo que foi provisionado (a instancia custa enquanto estiver ligada).
#
# Rode DEPOIS da apresentacao. A ordem importa: o grupo de seguranca so pode
# ser apagado quando nenhuma instancia o estiver usando.
# =============================================================================
set -euo pipefail

REGIAO="${REGIAO:-sa-east-1}"
NOME="${NOME:-primos-etapa1}"
GRUPO="${GRUPO:-sg-primos-etapa1}"

echo "Procurando a instancia '$NOME' na regiao $REGIAO..."
IDS=$(aws ec2 describe-instances --region "$REGIAO" \
  --filters "Name=tag:Name,Values=$NOME" \
            "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text)

if [[ -n "$IDS" && "$IDS" != "None" ]]; then
  echo "encerrando: $IDS"
  aws ec2 terminate-instances --region "$REGIAO" --instance-ids $IDS >/dev/null
  echo "aguardando o encerramento..."
  aws ec2 wait instance-terminated --region "$REGIAO" --instance-ids $IDS
  echo "instancia(s) encerrada(s)."
else
  echo "nenhuma instancia encontrada."
fi

ID_GRUPO=$(aws ec2 describe-security-groups --region "$REGIAO" \
  --filters Name=group-name,Values="$GRUPO" \
  --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "None")

if [[ -n "$ID_GRUPO" && "$ID_GRUPO" != "None" ]]; then
  echo "apagando o grupo de seguranca $ID_GRUPO..."
  aws ec2 delete-security-group --region "$REGIAO" --group-id "$ID_GRUPO"
  echo "grupo apagado."
fi

echo "pronto: nada mais gerando custo."
