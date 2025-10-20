#!/bin/bash

# Azure Multi-Agent Deployment Script
# Deploys multiple NANDA agents on a single Azure VM using supervisor

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
ANTHROPIC_API_KEY="$1"
AGENT_CONFIG_JSON="$2"
AGENT_REGISTRY_URL="${3:-http://registry.chat39.com:6900}"
MCP_REGISTRY_URL="${4:-}"
LOCATION="${5:-eastus}"
VM_SIZE="${6:-Standard_B4ms}"  # 4 vCPUs, 16GB RAM for multiple agents

# Validation
if [ -z "$ANTHROPIC_API_KEY" ] || [ -z "$AGENT_CONFIG_JSON" ]; then
    echo -e "${RED}❌ Usage: $0 <ANTHROPIC_API_KEY> <AGENT_CONFIG_JSON> [AGENT_REGISTRY_URL] [MCP_REGISTRY_URL] [LOCATION] [VM_SIZE]${NC}"
    echo ""
    echo "Example:"
    echo "  $0 sk-ant-xxx '../agent_configs/group-01-business-and-finance-experts.json' http://registry.url http://mcp.url eastus Standard_B4ms"
    exit 1
fi

# Parse and validate agent config
if [ -f "$AGENT_CONFIG_JSON" ]; then
    AGENTS_JSON=$(cat "$AGENT_CONFIG_JSON")
else
    AGENTS_JSON="$AGENT_CONFIG_JSON"
fi

AGENT_COUNT=$(echo "$AGENTS_JSON" | python3 -c "import json, sys; print(len(json.load(sys.stdin)))")
echo "Agents to deploy: $AGENT_COUNT"

# Port validation function
validate_port() {
    local port=$1
    if (( (port >= 6000 && port <= 6100) || \
          (port >= 7000 && port <= 7100) || \
          (port >= 8000 && port <= 8100) || \
          (port >= 9000 && port <= 9100) || \
          (port >= 10000 && port <= 10100) || \
          (port >= 11000 && port <= 11100) || \
          (port >= 12000 && port <= 12100) || \
          (port >= 13000 && port <= 13100) || \
          (port >= 14000 && port <= 14100) || \
          (port >= 15000 && port <= 15100) )); then
        return 0
    else
        return 1
    fi
}

# Validate port configuration
echo "Validating port configuration..."
INVALID_PORTS=$(echo "$AGENTS_JSON" | python3 -c "
import json, sys
agents = json.load(sys.stdin)
invalid = []
for agent in agents:
    port = agent['port']
    if not ((6000 <= port <= 6100) or (7000 <= port <= 7100) or 
            (8000 <= port <= 8100) or (9000 <= port <= 9100) or 
            (10000 <= port <= 10100) or (11000 <= port <= 11100) or 
            (12000 <= port <= 12100) or (13000 <= port <= 13100) or 
            (14000 <= port <= 14100) or (15000 <= port <= 15100)):
        invalid.append(str(port))
if invalid:
    print(' '.join(invalid))
    sys.exit(1)
")

if [ $? -eq 1 ]; then
    echo -e "${RED}❌ Invalid ports found: $INVALID_PORTS${NC}"
    exit 1
fi

# Check for duplicate ports
DUPLICATE_PORTS=$(echo "$AGENTS_JSON" | python3 -c "
import json, sys
from collections import Counter
agents = json.load(sys.stdin)
ports = [agent['port'] for agent in agents]
duplicates = [port for port, count in Counter(ports).items() if count > 1]
if duplicates:
    print(' '.join(map(str, duplicates)))
    sys.exit(1)
")

if [ $? -eq 1 ]; then
    echo -e "${RED}❌ Duplicate ports found: $DUPLICATE_PORTS${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All ports are in allowed ranges${NC}"

# Configuration
RESOURCE_GROUP="nanda-agents-rg"
NSG_NAME="nanda-agents-nsg"
VNET_NAME="nanda-agents-vnet"
SUBNET_NAME="nanda-agents-subnet"
DEPLOYMENT_ID=$(date +%Y%m%d-%H%M%S)
VM_NAME="nanda-multi-agents-${DEPLOYMENT_ID}"

echo -e "${GREEN}🚀 Starting Azure Multi-Agent Deployment${NC}"
echo "Agent Count: $AGENT_COUNT"
echo "Location: $LOCATION"
echo "VM Size: $VM_SIZE"
echo ""

# [1/7] Check Azure CLI
echo -e "${YELLOW}[1/7] Checking Azure CLI...${NC}"
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI not installed.${NC}"
    exit 1
fi

if ! az account show &> /dev/null; then
    echo -e "${RED}❌ Not logged in to Azure. Run 'az login' first.${NC}"
    exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo -e "${GREEN}✅ Using Azure subscription: $SUBSCRIPTION_ID${NC}"

# [2/7] Create or verify resource group
echo -e "${YELLOW}[2/7] Setting up resource group...${NC}"
if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
fi
echo -e "${GREEN}✅ Resource group: $RESOURCE_GROUP${NC}"

# [3/7] Create or verify network resources
echo -e "${YELLOW}[3/7] Setting up network resources...${NC}"
if ! az network nsg show --resource-group "$RESOURCE_GROUP" --name "$NSG_NAME" &> /dev/null; then
    echo "Creating network security group..."
    az network nsg create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$NSG_NAME" \
        --location "$LOCATION" \
        --output none
    
    # Add SSH rule
    az network nsg rule create \
        --resource-group "$RESOURCE_GROUP" \
        --nsg-name "$NSG_NAME" \
        --name "AllowSSH" \
        --priority 1000 \
        --source-address-prefixes '*' \
        --destination-port-ranges 22 \
        --access Allow \
        --protocol Tcp \
        --output none
    
    # Add agent port ranges
    PRIORITY=1100
    for PORT_RANGE in "6000-6100" "7000-7100" "8000-8100" "9000-9100" "10000-10100" "11000-11100" "12000-12100" "13000-13100" "14000-14100" "15000-15100"; do
        az network nsg rule create \
            --resource-group "$RESOURCE_GROUP" \
            --nsg-name "$NSG_NAME" \
            --name "AllowAgentPorts${PORT_RANGE}" \
            --priority $PRIORITY \
            --source-address-prefixes '*' \
            --destination-port-ranges "$PORT_RANGE" \
            --access Allow \
            --protocol Tcp \
            --output none
        PRIORITY=$((PRIORITY + 10))
    done
fi

if ! az network vnet show --resource-group "$RESOURCE_GROUP" --name "$VNET_NAME" &> /dev/null; then
    echo "Creating virtual network..."
    az network vnet create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$VNET_NAME" \
        --address-prefix 10.0.0.0/16 \
        --subnet-name "$SUBNET_NAME" \
        --subnet-prefix 10.0.1.0/24 \
        --location "$LOCATION" \
        --output none
    
    az network vnet subnet update \
        --resource-group "$RESOURCE_GROUP" \
        --vnet-name "$VNET_NAME" \
        --name "$SUBNET_NAME" \
        --network-security-group "$NSG_NAME" \
        --output none
fi
echo -e "${GREEN}✅ Network resources configured${NC}"

# [4/7] Create cloud-init configuration
echo -e "${YELLOW}[4/7] Creating cloud-init configuration...${NC}"

# Escape JSON for embedding
AGENTS_JSON_ESCAPED=$(echo "$AGENTS_JSON" | jq -c . | sed 's/"/\\"/g')

cat > "cloud-init-${DEPLOYMENT_ID}.yaml" << EOF
#cloud-config

package_update: true
package_upgrade: true

packages:
  - python3
  - python3-venv
  - python3-pip
  - git
  - curl
  - jq
  - supervisor

runcmd:
  - |
    exec > /var/log/cloud-init-output.log 2>&1
    
    echo "=== Multi-Agent Setup Started: ${DEPLOYMENT_ID} ==="
    date
    
    # Setup project
    cd /home/azureuser
    sudo -u azureuser git clone https://github.com/projnanda/NEST.git nanda-multi-agents
    cd nanda-multi-agents
    sudo -u azureuser python3 -m venv env
    sudo -u azureuser bash -c "source env/bin/activate && pip install --upgrade pip && pip install -e . && pip install anthropic"
    
    # Get public IP
    echo "Getting public IP address..."
    PUBLIC_IP=\$(curl -s -H Metadata:true "http://169.254.169.254/metadata/instance/network/interface/0/ipv4/ipAddress/0/publicIpAddress?api-version=2021-02-01&format=text")
    
    if [ -z "\$PUBLIC_IP" ]; then
        echo "ERROR: Could not retrieve public IP"
        exit 1
    fi
    
    echo "Retrieved public IP: \$PUBLIC_IP"
    
    # Save agent configuration
    cat > /tmp/agents_config.json << 'AGENTS_EOF'
${AGENTS_JSON}
AGENTS_EOF
    
    # Create supervisor configurations
    echo "Creating supervisor configurations..."
    mkdir -p /etc/supervisor/conf.d
    
    while IFS= read -r agent_config; do
        AGENT_ID=\$(echo "\$agent_config" | jq -r '.agent_id')
        AGENT_NAME=\$(echo "\$agent_config" | jq -r '.agent_name')
        DOMAIN=\$(echo "\$agent_config" | jq -r '.domain')
        SPECIALIZATION=\$(echo "\$agent_config" | jq -r '.specialization')
        DESCRIPTION=\$(echo "\$agent_config" | jq -r '.description')
        CAPABILITIES=\$(echo "\$agent_config" | jq -r '.capabilities')
        PORT=\$(echo "\$agent_config" | jq -r '.port')
        
        echo "Configuring supervisor for agent: \$AGENT_ID"
        
        cat > "/etc/supervisor/conf.d/agent_\$AGENT_ID.conf" << SUPERVISOR_EOF
[program:agent_\$AGENT_ID]
command=/home/azureuser/nanda-multi-agents/env/bin/python examples/nanda_agent.py
directory=/home/azureuser/nanda-multi-agents
user=azureuser
autostart=true
autorestart=true
startretries=3
stderr_logfile=/var/log/agent_\$AGENT_ID.err.log
stdout_logfile=/var/log/agent_\$AGENT_ID.out.log
environment=
    ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}",
    AGENT_ID="\$AGENT_ID",
    AGENT_NAME="\$AGENT_NAME",
    AGENT_DOMAIN="\$DOMAIN",
    AGENT_SPECIALIZATION="\$SPECIALIZATION",
    AGENT_DESCRIPTION="\$DESCRIPTION",
    AGENT_CAPABILITIES="\$CAPABILITIES",
    REGISTRY_URL="${AGENT_REGISTRY_URL}",
    MCP_REGISTRY_URL="${MCP_REGISTRY_URL}",
    PUBLIC_URL="http://\$PUBLIC_IP:\$PORT",
    PORT="\$PORT"

SUPERVISOR_EOF

        echo "✅ Supervisor config created for agent \$AGENT_ID on port \$PORT"
        
    done < <(cat /tmp/agents_config.json | jq -c '.[]')
    
    # Start supervisor
    echo "Starting supervisor..."
    systemctl enable supervisor
    systemctl start supervisor
    supervisorctl reread
    supervisorctl update
    
    # Wait for agents to start
    sleep 30
    
    echo "Verifying agent status..."
    supervisorctl status
    
    echo "=== Multi-Agent Setup Complete: ${DEPLOYMENT_ID} ==="
    echo "All agents managed by supervisor on: \$PUBLIC_IP"
    date
EOF

echo -e "${GREEN}✅ Cloud-init configuration created${NC}"

# [5/7] Create VM
echo -e "${YELLOW}[5/7] Creating Azure VM...${NC}"
az vm create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --location "$LOCATION" \
    --size "$VM_SIZE" \
    --image Ubuntu2204 \
    --admin-username azureuser \
    --generate-ssh-keys \
    --vnet-name "$VNET_NAME" \
    --subnet "$SUBNET_NAME" \
    --nsg "$NSG_NAME" \
    --public-ip-sku Standard \
    --custom-data "cloud-init-${DEPLOYMENT_ID}.yaml" \
    --tags "Project=NANDA" "Type=MultiAgent" "DeploymentId=$DEPLOYMENT_ID" \
    --output none

echo -e "${GREEN}✅ VM created: $VM_NAME${NC}"

# [6/7] Get VM details
echo -e "${YELLOW}[6/7] Retrieving VM details...${NC}"
PUBLIC_IP=$(az vm show -d --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --query publicIps -o tsv)

echo "Waiting for multi-agent deployment (3 minutes)..."
sleep 180

# [7/7] Cleanup
rm "cloud-init-${DEPLOYMENT_ID}.yaml"

# Summary
echo ""
echo -e "${GREEN}🎉 Azure Multi-Agent Deployment Complete!${NC}"
echo "============================================="
echo "Deployment ID: $DEPLOYMENT_ID"
echo "VM Name: $VM_NAME"
echo "Public IP: $PUBLIC_IP"
echo ""
echo "🤖 Agent URLs:"
echo "$AGENTS_JSON" | python3 -c "
import json, sys
agents = json.load(sys.stdin)
public_ip = '$PUBLIC_IP'
for agent in agents:
    print(f\"  {agent['agent_id']}: http://{public_ip}:{agent['port']}/a2a\")
"

echo ""
echo "📊 Monitor agents:"
echo "  ssh azureuser@$PUBLIC_IP 'sudo supervisorctl status'"
echo ""
echo "🔄 Restart all agents:"
echo "  ssh azureuser@$PUBLIC_IP 'sudo supervisorctl restart all'"
echo ""
echo "📋 View agent logs:"
echo "  ssh azureuser@$PUBLIC_IP 'sudo tail -f /var/log/agent_*.out.log'"
echo ""
echo "🛑 To delete VM:"
echo "  az vm delete --resource-group $RESOURCE_GROUP --name $VM_NAME --yes"
echo ""
echo "🗑️  To delete entire resource group:"
echo "  az group delete --name $RESOURCE_GROUP --yes"
