# FIE v3 — Deployment Guide

## Architecture
- **Backend**: FastAPI (Python 3.11) on AWS EC2 t3.micro (Mumbai ap-south-1)
- **Database**: PostgreSQL 16.6 on AWS RDS (Mumbai)
- **Frontend**: Next.js static export served by FastAPI
- **Container**: Docker on EC2, images stored in AWS ECR
- **CI/CD**: GitHub Actions → ECR → EC2

## Prerequisites
- AWS CLI configured with ap-south-1 region
- SSH access to EC2 (`~/.ssh/fie-key.pem`)
- GitHub repository secrets: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, EC2_SSH_KEY

## Automated Deployment (Recommended)
Push to `main` triggers the full pipeline:
1. GitHub Actions checks out code
2. Builds multi-stage Docker image (Node.js frontend + Python backend)
3. Pushes to ECR (`765425735663.dkr.ecr.ap-south-1.amazonaws.com/fie2`)
4. SSHs to EC2, pulls latest image, restarts container

## Manual Deployment
```bash
# SSH into EC2
ssh -i ~/.ssh/fie-key.pem ec2-user@13.206.50.251

# Pull latest image
PASSWORD=$(aws ecr get-login-password --region ap-south-1)
sudo docker login --username AWS --password $PASSWORD 765425735663.dkr.ecr.ap-south-1.amazonaws.com
sudo docker pull 765425735663.dkr.ecr.ap-south-1.amazonaws.com/fie2:latest

# Restart container
sudo docker stop fie2 || true
sudo docker rm fie2 || true
sudo docker run -d --name fie2 --restart always \
  -p 80:8000 -p 8000:8000 \
  --env-file /home/ec2-user/fie2.env \
  765425735663.dkr.ecr.ap-south-1.amazonaws.com/fie2:latest

# Verify
curl http://localhost:8000/health
```

## Environment Variables
See `.env.example` for all required and optional variables.

## Rollback
```bash
# Find previous image
sudo docker images | grep fie2

# Rollback to specific tag
sudo docker stop fie2 && sudo docker rm fie2
sudo docker run -d --name fie2 --restart always \
  -p 80:8000 -p 8000:8000 \
  --env-file /home/ec2-user/fie2.env \
  765425735663.dkr.ecr.ap-south-1.amazonaws.com/fie2:<previous-sha>
```

## Database Backups
- Automated daily backups to S3 at 11:30 PM IST
- Manual backup: `bash scripts/backup_db.sh`
- Restore: `bash scripts/restore_db.sh [filename]`
- List backups: `aws s3 ls s3://fie2-backups/db-backups/`

## Monitoring
- **Health check**: `GET /health` — DB connectivity, data freshness, uptime
- **Sentry**: Error tracking (set SENTRY_DSN in env)
- **Logs**: `sudo docker logs fie2 --tail 100 -f`

## Troubleshooting
| Issue | Solution |
|-------|----------|
| Container won't start | Check env file: `cat /home/ec2-user/fie2.env` |
| DB connection failed | Verify RDS security group allows EC2 IP |
| Stale market data | Check backfill logs: `sudo docker logs fie2 --since 1h` |
| High memory | Restart: `sudo docker restart fie2` |
| Disk full | Prune images: `sudo docker image prune -af` |
