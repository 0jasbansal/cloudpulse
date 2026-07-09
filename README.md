# CloudPulse

CloudPulse is a containerized FastAPI microservice deployed on Kubernetes using a GitOps model with ArgoCD, featuring automated CI/CD via GitHub Actions and Infrastructure as Code (IaC) via Terraform.

## System Architecture

```
                                  [ GitHub Repo ]
                                   /           \
                     (Trigger CI) /             \ (Sync Cluster Manifests)
                                 v               v
                        [GitHub Actions]     [ArgoCD]
                         /            \          |
             (Push)     /              \         | (Deploy / Sync)
                       v                v        v
                [Docker Hub]      [Git Repo Config] ----> [Kubernetes Cluster]
                                                                 |
                                                          (Scrapes Telemetry)
                                                                 v
                                                         [Prometheus + Grafana]
```

## Tech Stack
* **Runtime**: FastAPI, Uvicorn, Python 3.12
* **Containerization**: Docker, Docker Compose
* **Orchestration**: Kubernetes, Helm v3
* **GitOps**: ArgoCD
* **CI/CD**: GitHub Actions
* **IaC**: Terraform (AWS EKS & DigitalOcean)
* **Observability**: Prometheus, Grafana

---

## Getting Started

### 1. Local Development (Docker Compose)
To spin up the application along with local Prometheus and Grafana instances for testing:

```bash
docker compose up --build
```

Access endpoints:
* **API Documentation**: http://localhost:8000/docs
* **Health Check**: http://localhost:8000/health
* **Prometheus Server**: http://localhost:9090
* **Grafana Dashboards**: http://localhost:3000 (Credentials: admin / admin)

Run tests locally:
```bash
pip install -r app/requirements.txt
pytest -v app/
```

### 2. Local Kubernetes Deployment (Minikube & Helm)
Start a local Kubernetes cluster and enable the Ingress controller:

```bash
minikube start
minikube addons enable ingress
```

Point your shell to Minikube's Docker daemon and build the image locally:
```bash
eval $(minikube docker-env)
docker build -t ojasbansal/cloudpulse-api:latest ./app
```

Deploy the application using the Helm chart:
```bash
helm install cloudpulse ./helm-chart/cloudpulse
```

Verify the deployment:
```bash
kubectl get pods
kubectl get service cloudpulse-cloudpulse
```

---

## Production Deployments & GitOps

### CI/CD Pipeline Flow
The project uses GitHub Actions (.github/workflows/ci-cd.yml) to orchestrate builds:
1. **Lint & Test**: Runs code compliance checks and unit tests.
2. **Build & Publish**: Builds an optimized, multi-stage Docker image and pushes it to Docker Hub (ojasbansal/cloudpulse-api).
3. **GitOps Trigger**: Modifies values-staging.yaml or values-production.yaml with the new image SHA and commits it back to Git with a [skip ci] tag.

### ArgoCD GitOps Configuration
To deploy ArgoCD and sync the repository manifests:

```bash
# Install ArgoCD inside cluster
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Access ArgoCD Web Console
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Extract the default admin password:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

Sync the cluster state with Git:
```bash
kubectl apply -f argocd/staging-app.yaml
kubectl apply -f argocd/production-app.yaml
```

---

## Infrastructure as Code (Terraform)

The terraform/ directory contains automation scripts to provision cloud infrastructure:
* **DigitalOcean (terraform/main.tf)**: Deploys a single Ubuntu VM droplet for simple web service environments.
* **AWS EKS (terraform/aws_eks.tf)**: Provisions a full cloud-native network including a VPC, public subnets, internet gateways, IAM roles, and an AWS EKS (Elastic Kubernetes Service) cluster with managed node groups.

To run Terraform configurations:
```bash
cd terraform/
terraform init
terraform plan
```
