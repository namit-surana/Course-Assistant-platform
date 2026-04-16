# AWS Setup Checklist

Track every AWS resource created for the platform.
Update status as you go: `[ ]` = pending · `[~]` = in progress · `[x]` = done

> **Naming convention:** `{env}-{resource-type}-{role}-{az}`
> All names are role-based, not tied to any product name. When the product name is decided, nothing here needs to change.

---

## 0. IAM Setup (do this before anything else)

### Root Account Security

- Log into root account
- Enable **MFA** on root account
- Confirm **no Access Keys** exist for root (delete if any)
- Log out of root — never use it for daily work

### IAM Admin User (your daily driver)

- Go to **IAM → Users → Create User**
- Username: `admin-namit`
- Enable AWS Console access
- Attach policy: `AdministratorAccess`
- Enable **MFA** on this user
- Log out of root, log in as `admin-namit`

### IAM Dev Users (one per teammate)

- Create user `dev-backend` — attach policies: `AmazonECS_FullAccess`, `AmazonRDSFullAccess`, `AmazonSQSFullAccess`, `AmazonS3FullAccess`, `AmazonCognitoPowerUser`, `AmazonSESFullAccess`
- Create user `dev-worker` — attach policies: `AmazonECS_FullAccess`, `AmazonSQSFullAccess`, `AmazonS3FullAccess`, `AmazonSESFullAccess`, `SecretsManagerReadWrite`
- Create user `dev-frontend` — attach policies: `AmazonS3FullAccess`, `CloudFrontFullAccess`, `ReadOnlyAccess`
- Share console login URL + temporary passwords with teammates
- Each teammate must enable MFA on first login

### IAM Roles (for AWS services — not humans)

- Create role `role-ecs-execution`
  - Trusted entity: ECS Tasks
  - Attach: `AmazonECSTaskExecutionRolePolicy`
  - Attach: `SecretsManagerReadWrite` (to pull secrets at container start)
- Create role `role-ecs-api`
  - Trusted entity: ECS Tasks
  - Attach: `AmazonS3FullAccess`, `AmazonSQSFullAccess`, `AmazonCognitoPowerUser`, `SecretsManagerReadWrite`
- Create role `role-ecs-worker`
  - Trusted entity: ECS Tasks
  - Attach: `AmazonS3FullAccess`, `AmazonSQSFullAccess`, `AmazonSESFullAccess`, `SecretsManagerReadWrite`

---

## 1. VPC

- Go to **VPC → Your VPCs → Create VPC**
- Name: `prod-vpc`
- CIDR: `10.0.0.0/16`
- Tenancy: Default
- Enable **DNS hostnames** → Edit VPC settings → ✅
- Enable **DNS resolution** → Edit VPC settings → ✅

---

## 2. Subnets

> 6 subnets total — 2 public, 2 private API, 2 private data. Two AZs for high availability.

- Create **Public Subnet A**
  - Name: `prod-subnet-public-1a`
  - VPC: `prod-vpc`
  - AZ: `us-east-1a`
  - CIDR: `10.0.1.0/24`
- Create **Public Subnet B**
  - Name: `prod-subnet-public-1b`
  - VPC: `prod-vpc`
  - AZ: `us-east-1b`
  - CIDR: `10.0.2.0/24`
- Create **Private API Subnet A**
  - Name: `prod-subnet-api-1a`
  - VPC: `prod-vpc`
  - AZ: `us-east-1a`
  - CIDR: `10.0.3.0/24`
- Create **Private API Subnet B**
  - Name: `prod-subnet-api-1b`
  - VPC: `prod-vpc`
  - AZ: `us-east-1b`
  - CIDR: `10.0.4.0/24`
- Create **Private Data Subnet A**
  - Name: `prod-subnet-data-1a`
  - VPC: `prod-vpc`
  - AZ: `us-east-1a`
  - CIDR: `10.0.5.0/24`
- Create **Private Data Subnet B**
  - Name: `prod-subnet-data-1b`
  - VPC: `prod-vpc`
  - AZ: `us-east-1b`
  - CIDR: `10.0.6.0/24`
- Enable **auto-assign public IPv4** on `prod-subnet-public-1a` only
- Enable **auto-assign public IPv4** on `prod-subnet-public-1b` only

---

## 3. Internet Gateway (IGW)

- Go to **VPC → Internet Gateways → Create**
- Name: `prod-igw`
- Attach to `prod-vpc` → Actions → Attach to VPC

---

## 4. NAT Gateway

> Allows private subnet resources (ECS workers) to call Gemini API and GitHub API outbound.

- Go to **VPC → Elastic IPs → Allocate**
  - Name tag: `prod-eip-nat`
  - Note the Allocation ID
- Go to **VPC → NAT Gateways → Create**
  - Name: `prod-nat-1a`
  - Subnet: `prod-subnet-public-1a` (must be PUBLIC subnet)
  - Connectivity: Public
  - Elastic IP: select `prod-eip-nat`
- Wait for status → **Available** (takes ~2 minutes)

> 💡 **Cost tip:** NAT Gateway costs ~~$0.045/hr (~~$33/month). Delete it when not actively using the environment.

---

## 5. Route Tables

### Public Route Table

- Go to **VPC → Route Tables → Create**
  - Name: `prod-rt-public`
  - VPC: `prod-vpc`
- Add route:
  - Destination: `0.0.0.0/0`
  - Target: `prod-igw`
- Associate subnets:
  - `prod-subnet-public-1a`
  - `prod-subnet-public-1b`

### Private Route Table

- Create Route Table
  - Name: `prod-rt-private`
  - VPC: `prod-vpc`
- Add route:
  - Destination: `0.0.0.0/0`
  - Target: `prod-nat-1a`
- Associate subnets:
  - `prod-subnet-api-1a`
  - `prod-subnet-api-1b`
  - `prod-subnet-data-1a`
  - `prod-subnet-data-1b`

---

## 6. Network ACLs (NACLs)

> ✅ **Decision: Use default NACL — no custom rules needed.**
> Security Groups (Section 7) already control all traffic precisely at the resource level. The default NACL (allow all) is sufficient. Custom NACLs only add value for subnet-level IP blocking — not needed at this stage.

- [ ] Confirm default NACL is attached to all subnets (AWS does this automatically on VPC creation)
- [ ] Leave all default NACL rules as-is — allow all inbound + outbound
- [ ] ~~No custom NACLs to create~~ — skipped intentionally

---

## 7. Security Groups

> Security Groups are stateful — return traffic is automatic. More granular than NACLs.

### ALB Security Group
- [ ] Go to **VPC → Security Groups → Create**
  - Name: `prod-sg-alb`
  - VPC: `prod-vpc`
  - Description: `Public ALB - accepts HTTPS from internet`
- [ ] Inbound rule: TCP `443` from `0.0.0.0/0`
- [ ] Inbound rule: TCP `80` from `0.0.0.0/0` (will redirect to HTTPS)
- [ ] Outbound rule: All traffic (default)

### API Server Security Group
- [ ] Create Security Group
  - Name: `prod-sg-api`
  - VPC: `prod-vpc`
  - Description: `ECS API containers - only reachable from ALB`
- [ ] Inbound rule: TCP `8000` — Source: `prod-sg-alb` (select SG, not IP range)
- [ ] Outbound rule: All traffic (default)

### Worker Security Group
- [ ] Create Security Group
  - Name: `prod-sg-worker`
  - VPC: `prod-vpc`
  - Description: `ECS Worker containers - outbound only`
- [ ] Inbound rule: None — delete the default rule
- [ ] Outbound rule: All traffic (default)

### RDS Security Group
- [ ] Create Security Group
  - Name: `prod-sg-rds`
  - VPC: `prod-vpc`
  - Description: `PostgreSQL - only reachable from API and Worker`
- [ ] Inbound rule: TCP `5432` — Source: `prod-sg-api`
- [ ] Inbound rule: TCP `5432` — Source: `prod-sg-worker`
- [ ] Outbound rule: None — delete the default rule

### Redis Security Group
- [ ] Create Security Group
  - Name: `prod-sg-redis`
  - VPC: `prod-vpc`
  - Description: `ElastiCache Redis - only reachable from API`
- [ ] Inbound rule: TCP `6379` — Source: `prod-sg-api`
- [ ] Outbound rule: None — delete the default rule

---

## ~~8. VPC Endpoints~~ — SKIPPED

> ❌ **Decision: Skipped for now.**
> VPC Endpoints save NAT Gateway data transfer costs (~$0.045/GB) for S3, SQS, and Secrets Manager traffic. At current scale the savings are negligible (cents/month).
> Add these later when monthly data transfer bills get high enough to justify the Interface Endpoint hourly fee (~$0.01/hr each).

| Endpoint | Benefit | Add when |
|---|---|---|
| S3 Gateway (free) | Free S3 traffic, no NAT cost | Any time — it's free |
| SQS Interface | Cheaper SQS polling | When processing 1M+ messages/month |
| Secrets Manager Interface | Cheaper secrets fetching | When running 100+ containers |

---

## Verify VPC Setup ✅

- [ ] VPC `prod-vpc` exists with CIDR `10.0.0.0/16`
- [ ] All 6 subnets exist with correct CIDRs and AZs
- [ ] `prod-igw` is attached to `prod-vpc`
- [ ] `prod-nat-1a` status is **Available**
- [ ] `prod-rt-public` has route `0.0.0.0/0 → prod-igw`
- [ ] `prod-rt-private` has route `0.0.0.0/0 → prod-nat-1a`
- [ ] Public subnets associated with `prod-rt-public`
- [ ] All 4 private subnets associated with `prod-rt-private`
- [ ] Default NACL confirmed on all subnets (no custom NACLs)
- [ ] All 5 security groups created in `prod-vpc`
- [ ] `prod-sg-rds` inbound only allows `prod-sg-api` and `prod-sg-worker`
- [ ] `prod-sg-api` inbound only allows `prod-sg-alb`

---

## Naming Reference Card


| Resource              | Name                    |
| --------------------- | ----------------------- |
| VPC                   | `prod-vpc`              |
| IGW                   | `prod-igw`              |
| NAT Gateway           | `prod-nat-1a`           |
| Elastic IP            | `prod-eip-nat`          |
| Public Subnet A       | `prod-subnet-public-1a` |
| Public Subnet B       | `prod-subnet-public-1b` |
| API Subnet A          | `prod-subnet-api-1a`    |
| API Subnet B          | `prod-subnet-api-1b`    |
| Data Subnet A         | `prod-subnet-data-1a`   |
| Data Subnet B         | `prod-subnet-data-1b`   |
| Public Route Table    | `prod-rt-public`        |
| Private Route Table   | `prod-rt-private`       |
| NACLs                 | default (skipped)       |
| ALB Security Group    | `prod-sg-alb`           |
| API Security Group    | `prod-sg-api`           |
| Worker Security Group | `prod-sg-worker`        |
| RDS Security Group    | `prod-sg-rds`           |
| Redis Security Group  | `prod-sg-redis`         |
| IAM Admin User        | `admin-namit`           |
| IAM Dev — Backend     | `dev-backend`           |
| IAM Dev — Worker      | `dev-worker`            |
| IAM Dev — Frontend    | `dev-frontend`          |
| ECS Execution Role    | `role-ecs-execution`    |
| ECS API Role          | `role-ecs-api`          |
| ECS Worker Role       | `role-ecs-worker`       |


---

## Coming Next

- [ ] **ECS** — Cluster `prod-cluster`, Services `prod-service-api`, `prod-service-worker`
- [ ] **RDS** — Instance `prod-db-postgres`
- [ ] **ElastiCache** — Cluster `prod-cache-redis`
- [ ] **S3** — Buckets `prod-bucket-uploads`, `prod-bucket-frontend`
- [ ] **SQS** — Queue `prod-queue-analysis`
- [ ] **Cognito** — User Pool `prod-userpool`
- [ ] **ALB** — `prod-alb`, Target Groups `prod-tg-api`
- [ ] **ECR** — Repos `prod-ecr-api`, `prod-ecr-worker`
- [ ] **SES** — Sender identity setup
- [ ] **Secrets Manager** — `prod-secrets-app`
- [ ] **CloudWatch** — Log groups `prod-logs-api`, `prod-logs-worker`
- [ ] **Route 53 + CloudFront** — Domain + CDN setup

