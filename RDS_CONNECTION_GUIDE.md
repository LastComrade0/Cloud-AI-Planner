# RDS Connection Guide - Private Subnet with NAT Gateway

## Problem

If your RDS database is in a **private subnet with NAT Gateway** (no Internet Gateway), you cannot connect directly from your local machine because:

- **NAT Gateway**: Allows outbound connections (RDS → Internet) but blocks inbound (Internet → RDS)
- **Internet Gateway**: Required for inbound connections from the internet

## Solution Options

### Option 1: AWS Systems Manager Port Forwarding (Recommended) ⭐

This creates a secure tunnel through an EC2 instance in the same VPC.

#### Prerequisites:
1. An EC2 instance in the same VPC as your RDS database
2. SSM Agent installed and running on the EC2 instance
3. IAM role with `AmazonSSMManagedInstanceCore` policy attached to EC2
4. AWS CLI configured with appropriate permissions

#### Steps:

**Windows (PowerShell):**
```powershell
# 1. Find your EC2 instance ID in the same VPC as RDS
# 2. Run the port forwarding script
.\connect-via-ssm.ps1 -InstanceId i-1234567890abcdef0 -RdsEndpoint ai-planner-db.c74maa0ckpwh.us-west-1.rds.amazonaws.com

# 3. In another terminal, update your DATABASE_URL to use localhost:5432
# 4. Run your script
python .\delete_first_user.py
```

**Linux/Mac (Bash):**
```bash
# 1. Make script executable
chmod +x connect-via-ssm.sh

# 2. Run the port forwarding script
./connect-via-ssm.sh i-1234567890abcdef0 ai-planner-db.c74maa0ckpwh.us-west-1.rds.amazonaws.com

# 3. In another terminal, update your DATABASE_URL to use localhost:5432
# 4. Run your script
python delete_first_user.py
```

**Manual AWS CLI:**
```bash
aws ssm start-session \
    --target i-1234567890abcdef0 \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters '{
        "host":["ai-planner-db.c74maa0ckpwh.us-west-1.rds.amazonaws.com"],
        "portNumber":["5432"],
        "localPortNumber":["5432"]
    }'
```

**Update DATABASE_URL temporarily:**
```bash
# Original (won't work from local machine)
DATABASE_URL=postgresql://user:pass@ai-planner-db.c74maa0ckpwh.us-west-1.rds.amazonaws.com:5432/dbname

# Use localhost when port forwarding is active
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
```

### Option 2: Run Script from EC2 Instance

1. SSH into an EC2 instance in the same VPC (via SSM Session Manager)
2. Copy your script and dependencies to the EC2 instance
3. Run the script from there (RDS is accessible from same VPC)

```bash
# Start SSM session
aws ssm start-session --target i-1234567890abcdef0

# On EC2, clone/copy your project
# Install dependencies
# Run script
python delete_first_user.py
```

### Option 3: Deploy to Lambda with VPC Configuration

Configure your Lambda function to:
- Connect to the same VPC as RDS
- Use the same security groups
- Run the script as a Lambda function

### Option 4: Temporarily Add IGW Route (NOT Recommended)

⚠️ **Security Risk**: Only for development/testing

1. Add route table entry: `0.0.0.0/0` → Internet Gateway
2. Set RDS to "Publicly accessible"
3. Add security group rule for your IP on port 5432
4. **Remember to revert these changes after testing!**

## Finding Your EC2 Instance

```bash
# List EC2 instances
aws ec2 describe-instances \
    --filters "Name=vpc-id,Values=vpc-xxxxx" \
    --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PrivateIpAddress]' \
    --output table

# Or use AWS Console:
# EC2 → Instances → Filter by VPC ID
```

## Verifying SSM Agent

```bash
# Check if SSM agent is running on EC2
aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=i-1234567890abcdef0"
```

## Troubleshooting

### "Target instance is not in a valid state"
- Ensure EC2 instance is running
- Check SSM agent is installed and running
- Verify IAM role has `AmazonSSMManagedInstanceCore` policy

### "Port already in use"
- Change local port: `--parameters '{"localPortNumber":["5433"]}'`
- Or kill the process using port 5432

### "Connection timeout" even with port forwarding
- Verify RDS security group allows connections from EC2 security group
- Check RDS endpoint is correct
- Ensure EC2 and RDS are in the same VPC

## Security Best Practices

✅ **DO:**
- Use SSM Session Manager (no SSH keys needed)
- Use port forwarding for temporary access
- Close the tunnel when done
- Use least-privilege IAM policies

❌ **DON'T:**
- Make RDS publicly accessible in production
- Add 0.0.0.0/0 to security groups
- Leave port forwarding tunnels open indefinitely

