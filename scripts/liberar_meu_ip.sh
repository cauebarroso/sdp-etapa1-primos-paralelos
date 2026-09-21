#!/usr/bin/env bash
# =============================================================================
# Libera o SSH para o IP DE ONDE VOCE ESTA AGORA.
#
# Por que isto existe: a regra da porta 22 e presa ao /32 de quem provisionou.
# Se a instancia foi criada de casa e a apresentacao e na faculdade, o IP muda
# e o SSH e recusado -- na frente do professor.
#
# RODE ISTO NA REDE DA APRESENTACAO, antes de comecar.
#
#   ./liberar_meu_ip.sh              # adiciona o IP atual
#   ./liberar_meu_ip.sh --limpar     # remove os IPs antigos e deixa so o atual
#
# Continua sem abrir para 0.0.0.0/0: o que muda e QUAL /32 tem acesso.
# =============================================================================
set -euo pipefail

REGIAO="${REGIAO:-sa-east-1}"
GRUPO="${GRUPO:-sg-primos-etapa1}"
PORTA_ADMIN="${PORTA_ADMIN:-22}"

LIMPAR=0
[[ "${1:-}" == "--limpar" ]] && LIMPAR=1

echo "Descobrindo o IP publico desta rede..."
IP="$(curl -fsS --max-time 10 https://checkip.amazonaws.com | tr -d '[:space:]' || true)"
if [[ ! "$IP" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
  echo "ERRO: nao consegui descobrir o IP. Defina manualmente:" >&2
  echo "      IP_MANUAL=203.0.113.45 ./liberar_meu_ip.sh" >&2
  IP="${IP_MANUAL:-}"
  [[ -z "$IP" ]] && exit 1
fi
echo "  IP atual: $IP"

ID_GRUPO=$(aws ec2 describe-security-groups --region "$REGIAO" \
  --filters Name=group-name,Values="$GRUPO" \
  --query 'SecurityGroups[0].GroupId' --output text)

if [[ -z "$ID_GRUPO" || "$ID_GRUPO" == "None" ]]; then
  echo "ERRO: grupo '$GRUPO' nao encontrado na regiao $REGIAO." >&2
  exit 1
fi
echo "  grupo: $ID_GRUPO"

if [[ $LIMPAR -eq 1 ]]; then
  echo "Removendo autorizacoes antigas da porta $PORTA_ADMIN..."
  ANTIGOS=$(aws ec2 describe-security-groups --region "$REGIAO" --group-ids "$ID_GRUPO" \
    --query "SecurityGroups[0].IpPermissions[?FromPort==\`$PORTA_ADMIN\`].IpRanges[].CidrIp" \
    --output text)
  for cidr in $ANTIGOS; do
    [[ "$cidr" == "$IP/32" ]] && continue
    echo "  removendo $cidr"
    aws ec2 revoke-security-group-ingress --region "$REGIAO" --group-id "$ID_GRUPO" \
      --protocol tcp --port "$PORTA_ADMIN" --cidr "$cidr" >/dev/null || true
  done
fi

echo "Autorizando $IP/32 na porta $PORTA_ADMIN..."
aws ec2 authorize-security-group-ingress --region "$REGIAO" --group-id "$ID_GRUPO" \
  --protocol tcp --port "$PORTA_ADMIN" --cidr "$IP/32" >/dev/null \
  && echo "  liberado." || echo "  (ja estava liberado)"

echo
echo "Regras de entrada agora:"
aws ec2 describe-security-groups --region "$REGIAO" --group-ids "$ID_GRUPO" \
  --query 'SecurityGroups[0].IpPermissions[].{porta:FromPort,protocolo:IpProtocol,origem:IpRanges[0].CidrIp}' \
  --output table

echo
echo "CONFERENCIA: a porta administrativa nao pode estar aberta para 0.0.0.0/0"
if aws ec2 describe-security-groups --region "$REGIAO" --group-ids "$ID_GRUPO" \
     --query "SecurityGroups[0].IpPermissions[?FromPort==\`$PORTA_ADMIN\`].IpRanges[].CidrIp" \
     --output text | grep -q '0.0.0.0/0'; then
  echo "  !! FALHA: $PORTA_ADMIN/tcp aberta para o mundo. Corrija antes de apresentar."
  exit 1
fi
echo "  OK: $PORTA_ADMIN/tcp restrita a /32 da equipe."
