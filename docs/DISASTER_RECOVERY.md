# FIE v3 — Disaster Recovery Plan

## Recovery Time Objectives
- **RTO (Recovery Time Objective)**: 30 minutes
- **RPO (Recovery Point Objective)**: 24 hours (daily backups)

## Scenario 1: Application Crash
**Symptoms**: 502/503 errors, health check failing
**Recovery**:
1. SSH to EC2: `ssh -i ~/.ssh/fie-key.pem ec2-user@13.206.50.251`
2. Check container: `sudo docker ps -a`
3. View logs: `sudo docker logs fie2 --tail 200`
4. Restart: `sudo docker restart fie2`
5. If restart fails, redeploy: Pull and run latest image

## Scenario 2: Database Corruption
**Recovery**:
1. List available backups: `bash scripts/restore_db.sh`
2. Restore latest backup: `bash scripts/restore_db.sh fie_v3_YYYY-MM-DD_HHMMSS.sql.gz`
3. Restart application to rebuild caches

## Scenario 3: EC2 Instance Failure
**Recovery**:
1. Launch new t3.micro in ap-south-1 (Mumbai)
2. Reassign Elastic IP `13.206.50.251`
3. Install Docker, AWS CLI
4. Copy env file from backup
5. Pull and run Docker image from ECR
6. Update SSH key in GitHub Secrets if needed

## Scenario 4: Complete AWS Outage
**Recovery**:
1. Deploy to alternative cloud (Railway, DigitalOcean)
2. Restore DB from latest S3 backup
3. Update DNS/IP references

## Backup Verification
Monthly: restore a backup to a test database and verify data integrity.
