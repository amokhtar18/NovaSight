# 038 - Kubernetes Manifests

## Metadata

```yaml
prompt_id: "038"
phase: 6
agent: "@infrastructure"
model: "sonnet 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["037"]
```

## Objective

Create Kubernetes manifests for deploying NovaSight to production.

## Task Description

Implement Kubernetes resources for all services with proper configurations for production.

## Requirements

### Namespace and RBAC

```yaml
# k8s/base/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: novasight
  labels:
    app.kubernetes.io/name: novasight
    app.kubernetes.io/part-of: novasight

---
# k8s/base/rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: novasight-backend
  namespace: novasight

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: novasight-backend-role
  namespace: novasight
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: novasight-backend-binding
  namespace: novasight
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: novasight-backend-role
subjects:
  - kind: ServiceAccount
    name: novasight-backend
    namespace: novasight
```

### Backend Deployment

```yaml
# k8s/base/backend/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: novasight
  labels:
    app.kubernetes.io/name: backend
    app.kubernetes.io/component: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app.kubernetes.io/name: backend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app.kubernetes.io/name: backend
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      serviceAccountName: novasight-backend
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: backend
          image: ghcr.io/novasight/backend:latest
          imagePullPolicy: Always
          ports:
            - name: http
              containerPort: 5000
            - name: metrics
              containerPort: 9090
          envFrom:
            - configMapRef:
                name: backend-config
            - secretRef:
                name: backend-secrets
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 2Gi
          readinessProbe:
            httpGet:
              path: /api/v1/health
              port: http
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: http
            initialDelaySeconds: 30
            periodSeconds: 30
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app.kubernetes.io/name: backend
                topologyKey: kubernetes.io/hostname

---
# k8s/base/backend/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: novasight
  labels:
    app.kubernetes.io/name: backend
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 80
      targetPort: http
    - name: metrics
      port: 9090
      targetPort: metrics
  selector:
    app.kubernetes.io/name: backend

---
# k8s/base/backend/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend
  namespace: novasight
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

### Frontend Deployment

```yaml
# k8s/base/frontend/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: novasight
  labels:
    app.kubernetes.io/name: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: frontend
  template:
    metadata:
      labels:
        app.kubernetes.io/name: frontend
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
      containers:
        - name: frontend
          image: ghcr.io/novasight/frontend:latest
          ports:
            - name: http
              containerPort: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 10
            periodSeconds: 30

---
# k8s/base/frontend/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: novasight
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 80
      targetPort: http
  selector:
    app.kubernetes.io/name: frontend
```

### Ingress

```yaml
# k8s/base/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: novasight
  namespace: novasight
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
    - hosts:
        - novasight.io
        - api.novasight.io
      secretName: novasight-tls
  rules:
    - host: novasight.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
    - host: api.novasight.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 80
```

### ConfigMaps and Secrets

```yaml
# k8s/base/backend/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: novasight
data:
  FLASK_ENV: "production"
  LOG_LEVEL: "INFO"
  CLICKHOUSE_HOST: "clickhouse-service"
  REDIS_HOST: "redis-service"
  OLLAMA_HOST: "ollama-service"
  AIRFLOW_HOST: "airflow-webserver"

---
# k8s/base/backend/sealed-secret.yaml
# Use sealed-secrets or external-secrets-operator in production
apiVersion: v1
kind: Secret
metadata:
  name: backend-secrets
  namespace: novasight
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:pass@postgres:5432/novasight"
  SECRET_KEY: "change-me-in-production"
  ENCRYPTION_MASTER_KEY: "change-me-in-production"
  JWT_SECRET_KEY: "change-me-in-production"
```

### Kustomization

```yaml
# k8s/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: novasight

resources:
  - namespace.yaml
  - rbac.yaml
  - backend/deployment.yaml
  - backend/service.yaml
  - backend/hpa.yaml
  - backend/configmap.yaml
  - frontend/deployment.yaml
  - frontend/service.yaml
  - ingress.yaml

commonLabels:
  app.kubernetes.io/part-of: novasight

---
# k8s/overlays/staging/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: novasight-staging

bases:
  - ../../base

namePrefix: staging-

patchesStrategicMerge:
  - backend-patch.yaml

images:
  - name: ghcr.io/novasight/backend
    newTag: develop
  - name: ghcr.io/novasight/frontend
    newTag: develop

---
# k8s/overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: novasight-prod

bases:
  - ../../base

patchesStrategicMerge:
  - backend-patch.yaml
  - hpa-patch.yaml

replicas:
  - name: backend
    count: 5
  - name: frontend
    count: 3
```

## Expected Output

```
k8s/
├── base/
│   ├── namespace.yaml
│   ├── rbac.yaml
│   ├── ingress.yaml
│   ├── kustomization.yaml
│   ├── backend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   └── configmap.yaml
│   └── frontend/
│       ├── deployment.yaml
│       └── service.yaml
├── overlays/
│   ├── staging/
│   │   └── kustomization.yaml
│   └── production/
│       ├── kustomization.yaml
│       └── hpa-patch.yaml
└── README.md
```

## Acceptance Criteria

- [ ] All deployments have proper resource limits
- [ ] Health checks configured
- [ ] HPA enables autoscaling
- [ ] Pod anti-affinity for HA
- [ ] Secrets not stored in plain text
- [ ] RBAC follows least privilege
- [ ] Ingress with TLS configured
- [ ] Kustomize overlays work

## Reference Documents

- [Infrastructure Agent](../agents/infrastructure-agent.agent.md)
- [CI/CD Pipeline](./037-cicd-pipeline.md)
