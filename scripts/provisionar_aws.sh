#!/usr/bin/env bash
# =============================================================================
# Provisionamento da instancia de medicao - Etapa 1
# Sistemas Distribuidos e Paralelos - equipe Barroso / Ribeiro / Pereira
# =============================================================================
#
# Cria, com AWS CLI v2:
#   1. um grupo de seguranca com DUAS regras apenas:
#        - 22/tcp  (porta administrativa, SSH) restrita ao IP DA EQUIPE  -> /32
#        - 8000/tcp (porta do servico, pagina de status) aberta
#   2. uma instancia EC2 compute-optimized numa unica zona de disponibilidade
#
# A porta administrativa NUNCA e aberta para 0.0.0.0/0. O script descobre o
# IP publico da equipe e usa /32; se a descoberta falhar, ele ABORTA em vez
# de cair para 0.0.0.0/0 (isso zeraria o criterio de provisionamento).
#
# Uso:
#   ./provisionar_aws.sh                 # cria tudo
#   ./provisionar_aws.sh --so-mostrar    # so imprime o que faria
#
# Depois: ./executar_na_instancia.sh
# No fim do trabalho: ./destruir_aws.sh
# -----------------------------------------------------------------------------
set -euo pipefail

# --------------------------------------------------------------- parametros
REGIAO="${REGIAO:-sa-east-1}"          # Sao Paulo: menor latencia para a equipe
ZONA="${ZONA:-sa-east-1a}"             # UMA zona: a carga e um lote, nao um servico 24x7
TIPO="${TIPO:-c5.2xlarge}"             # compute-optimized: 8 vCPU = 4 nucleos fisicos
NOME="${NOME:-primos-etapa1}"
GRUPO="${GRUPO:-sg-primos-etapa1}"
CHAVE="${CHAVE:-chave-primos-etapa1}"
PORTA_SERVICO="${PORTA_SERVICO:-8000}"
PORTA_ADMIN="${PORTA_ADMIN:-22}"
VOLUME_GB="${VOLUME_GB:-20}"           # gp3; entrada e saida sao pequenas (ver relatorio)

SO_MOSTRAR=0
[[ "${1:-}" == "--so-mostrar" ]] && SO_MOSTRAR=1

executar() {
  echo "  \$ $*"
  if [[ $SO_MOSTRAR -eq 0 ]]; then "$@"; fi
}

echo "============================================================"
echo "Provisionamento - regiao $REGIAO / zona $ZONA / tipo $TIPO"
echo "============================================================"

# ------------------------------------------------- 1. IP de origem da equipe
echo
echo "[1/5] Descobrindo o IP publico da equipe (origem da regra de SSH)..."
IP_EQUIPE="${IP_EQUIPE:-$(curl -fsS --max-time 10 https://checkip.amazonaws.com || true)}"
IP_EQUIPE="$(echo "${IP_EQUIPE}" | tr -d '[:space:]')"

if [[ ! "$IP_EQUIPE" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
  echo "ERRO: nao foi possivel descobrir o IP publico da equipe." >&2
  echo "      Defina manualmente:  IP_EQUIPE=203.0.113.45 ./provisionar_aws.sh" >&2
  echo "      O script NAO vai abrir a porta administrativa para 0.0.0.0/0." >&2
  exit 1
fi
ORIGEM_ADMIN="${IP_EQUIPE}/32"
echo "      IP da equipe: $IP_EQUIPE  ->  origem da regra de SSH: $ORIGEM_ADMIN"

# ------------------------------------------------------ 2. grupo de seguranca
echo
echo "[2/5] Grupo de seguranca '$GRUPO'..."
VPC_PADRAO=$(aws ec2 describe-vpcs --region "$REGIAO" \
  --filters Name=is-default,Values=true \
  --query 'Vpcs[0].VpcId' --output text)
echo "      VPC: $VPC_PADRAO"

ID_GRUPO=$(aws ec2 describe-security-groups --region "$REGIAO" \
  --filters Name=group-name,Values="$GRUPO" Name=vpc-id,Values="$VPC_PADRAO" \
  --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "None")

if [[ "$ID_GRUPO" == "None" || -z "$ID_GRUPO" ]]; then
  ID_GRUPO=$(aws ec2 create-security-group --region "$REGIAO" \
    --group-name "$GRUPO" --vpc-id "$VPC_PADRAO" \
    --description "Etapa 1: SSH so da equipe, 8000 para a pagina de status" \
    --query 'GroupId' --output text)
  echo "      criado: $ID_GRUPO"
else
  echo "      ja existia: $ID_GRUPO"
fi

echo "      regra 1: porta administrativa $PORTA_ADMIN/tcp <- $ORIGEM_ADMIN (SO a equipe)"
executar aws ec2 authorize-security-group-ingress --region "$REGIAO" \
  --group-id "$ID_GRUPO" --protocol tcp --port "$PORTA_ADMIN" --cidr "$ORIGEM_ADMIN" \
  || echo "      (regra ja existe)"

echo "      regra 2: porta do servico $PORTA_SERVICO/tcp <- 0.0.0.0/0 (pagina de status, somente leitura)"
executar aws ec2 authorize-security-group-ingress --region "$REGIAO" \
  --group-id "$ID_GRUPO" --protocol tcp --port "$PORTA_SERVICO" --cidr 0.0.0.0/0 \
  || echo "      (regra ja existe)"

# ------------------------------------------------------------- 3. par de chaves
echo
echo "[3/5] Par de chaves '$CHAVE'..."
if aws ec2 describe-key-pairs --region "$REGIAO" --key-names "$CHAVE" >/dev/null 2>&1; then
  echo "      ja existe (usando ~/.ssh/$CHAVE.pem)"
else
  executar bash -c "aws ec2 create-key-pair --region '$REGIAO' --key-name '$CHAVE' \
    --query 'KeyMaterial' --output text > ~/.ssh/$CHAVE.pem && chmod 400 ~/.ssh/$CHAVE.pem"
  echo "      criado e salvo em ~/.ssh/$CHAVE.pem"
fi

# ------------------------------------------------------------- 4. AMI e sub-rede
echo
echo "[4/5] Imagem e sub-rede..."
AMI=$(aws ec2 describe-images --region "$REGIAO" --owners amazon \
  --filters 'Name=name,Values=al2023-ami-2023.*-x86_64' 'Name=state,Values=available' \
  --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)
echo "      AMI (Amazon Linux 2023): $AMI"

SUBREDE=$(aws ec2 describe-subnets --region "$REGIAO" \
  --filters Name=vpc-id,Values="$VPC_PADRAO" Name=availability-zone,Values="$ZONA" \
  --query 'Subnets[0].SubnetId' --output text)
echo "      sub-rede em $ZONA: $SUBREDE"

# --------------------------------------------------------------- 5. instancia
echo
echo "[5/5] Instancia $TIPO em $ZONA..."
INICIALIZACAO=$(cat <<'EOF'
#!/bin/bash
dnf -y update
dnf -y install python3 git
EOF
)

executar aws ec2 run-instances --region "$REGIAO" \
  --image-id "$AMI" --instance-type "$TIPO" --key-name "$CHAVE" \
  --security-group-ids "$ID_GRUPO" --subnet-id "$SUBREDE" \
  --associate-public-ip-address \
  --block-device-mappings "DeviceName=/dev/xvda,Ebs={VolumeSize=$VOLUME_GB,VolumeType=gp3}" \
  --user-data "$INICIALIZACAO" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NOME},{Key=Disciplina,Value=SDP-Etapa1}]" \
  --query 'Instances[0].InstanceId' --output text

if [[ $SO_MOSTRAR -eq 1 ]]; then
  echo; echo "(--so-mostrar: nada foi criado)"; exit 0
fi

ID_INSTANCIA=$(aws ec2 describe-instances --region "$REGIAO" \
  --filters "Name=tag:Name,Values=$NOME" "Name=instance-state-name,Values=pending,running" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)

echo "      aguardando a instancia ficar disponivel..."
aws ec2 wait instance-running --region "$REGIAO" --instance-ids "$ID_INSTANCIA"

IP_PUBLICO=$(aws ec2 describe-instances --region "$REGIAO" --instance-ids "$ID_INSTANCIA" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

# --------------------------------------------------------- conferencia final
echo
echo "============================================================"
echo "PRONTO"
echo "============================================================"
echo "instancia : $ID_INSTANCIA  ($TIPO, zona $ZONA)"
echo "IP publico: $IP_PUBLICO"
echo "grupo     : $ID_GRUPO"
echo "acesso    : ssh -i ~/.ssh/$CHAVE.pem ec2-user@$IP_PUBLICO"
echo "status    : http://$IP_PUBLICO:$PORTA_SERVICO/"
echo
echo "Regras de entrada (e isto que se mostra ao vivo no console):"
aws ec2 describe-security-groups --region "$REGIAO" --group-ids "$ID_GRUPO" \
  --query 'SecurityGroups[0].IpPermissions[].{porta:FromPort,protocolo:IpProtocol,origem:IpRanges[0].CidrIp}' \
  --output table

echo
echo "CONFERENCIA: a porta administrativa NAO pode aparecer com origem 0.0.0.0/0"
if aws ec2 describe-security-groups --region "$REGIAO" --group-ids "$ID_GRUPO" \
     --query "SecurityGroups[0].IpPermissions[?FromPort==\`$PORTA_ADMIN\`].IpRanges[].CidrIp" \
     --output text | grep -q '0.0.0.0/0'; then
  echo "  !! FALHA: $PORTA_ADMIN/tcp esta aberta para o mundo. Corrija antes de apresentar."
  exit 1
fi
echo "  OK: $PORTA_ADMIN/tcp restrita a $ORIGEM_ADMIN"
