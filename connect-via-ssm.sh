#!/bin/bash
# Bash script to connect to RDS via AWS Systems Manager Session Manager
# This creates a port forwarding tunnel through an EC2 instance in the same VPC

# Usage: ./connect-via-ssm.sh <instance-id> <rds-endpoint> [local-port] [remote-port]

if [ $# -lt 2 ]; then
    echo "Usage: $0 <instance-id> <rds-endpoint> [local-port] [remote-port]"
    echo "Example: $0 i-1234567890abcdef0 ai-planner-db.c74maa0ckpwh.us-west-1.rds.amazonaws.com 5432 5432"
    exit 1
fi

INSTANCE_ID=$1
RDS_ENDPOINT=$2
LOCAL_PORT=${3:-5432}
REMOTE_PORT=${4:-5432}

echo "Starting SSM port forwarding session..."
echo "Instance ID: $INSTANCE_ID"
echo "RDS Endpoint: $RDS_ENDPOINT"
echo "Local Port: $LOCAL_PORT"
echo "Remote Port: $REMOTE_PORT"
echo ""
echo "This will forward localhost:$LOCAL_PORT to $RDS_ENDPOINT:$REMOTE_PORT"
echo "Press Ctrl+C to stop the tunnel"
echo ""

# Start the SSM port forwarding session
aws ssm start-session \
    --target "$INSTANCE_ID" \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters "{
        \"host\": [\"$RDS_ENDPOINT\"],
        \"portNumber\": [\"$REMOTE_PORT\"],
        \"localPortNumber\": [\"$LOCAL_PORT\"]
    }"

