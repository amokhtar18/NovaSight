# 039 - Helm Charts

## Metadata

```yaml
prompt_id: "039"
phase: 6
agent: "@infrastructure"
model: "sonnet 4.5"
priority: P1
estimated_effort: "3 days"
dependencies: ["038"]
```

## Objective

Create Helm charts for flexible deployment configuration.

## Task Description

Implement Helm charts with comprehensive values files for different environments.

## Requirements

### Chart Structure

```yaml
# helm/novasight/Chart.yaml
apiVersion: v2
name: novasight
description: Self-Service BI Platform
type: application
version: 0.1.0
appVersion: "1.0.0"

dependencies:
  - name: postgresql
    version: 12.1.6
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
  - name: redis
    version: 17.3.11
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled
  - name: clickhouse
    version: 3.1.0
    repository: https://charts.bitnami.com/bitnami
    condition: clickhouse.enabled
```

### Values File

```yaml
# helm/novasight/values.yaml
# Global settings
global:
  imageRegistry: ghcr.io/novasight
  imagePullSecrets: []

# Backend settings
backend:
  replicaCount: 3
  
  image:
    repository: backend
    tag: latest
    pullPolicy: Always
  
  service:
    type: ClusterIP
    port: 80
  
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi
  
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80
  
  env:
    FLASK_ENV: production
    LOG_LEVEL: INFO
  
  secrets:
    # These should be provided via sealed-secrets or external-secrets
    databaseUrl: ""
    secretKey: ""
    encryptionMasterKey: ""
    jwtSecretKey: ""
  
  livenessProbe:
    httpGet:
      path: /api/v1/health
      port: http
    initialDelaySeconds: 30
    periodSeconds: 30
  
  readinessProbe:
    httpGet:
      path: /api/v1/health
      port: http
    initialDelaySeconds: 10
    periodSeconds: 10

# Frontend settings
frontend:
  replicaCount: 2
  
  image:
    repository: frontend
    tag: latest
    pullPolicy: Always
  
  service:
    type: ClusterIP
    port: 80
  
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 256Mi
  
  autoscaling:
    enabled: false
    minReplicas: 2
    maxReplicas: 5
    targetCPUUtilizationPercentage: 70

# Ingress settings
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: novasight.io
      paths:
        - path: /
          pathType: Prefix
          service: frontend
    - host: api.novasight.io
      paths:
        - path: /
          pathType: Prefix
          service: backend
  tls:
    - secretName: novasight-tls
      hosts:
        - novasight.io
        - api.novasight.io

# Airflow settings
airflow:
  enabled: true
  executor: CeleryExecutor
  webserver:
    replicas: 1
  scheduler:
    replicas: 1
  workers:
    replicas: 3

# Ollama settings (for NL-to-SQL)
ollama:
  enabled: true
  replicaCount: 1
  image:
    repository: ollama/ollama
    tag: latest
  resources:
    requests:
      cpu: 2
      memory: 8Gi
    limits:
      cpu: 4
      memory: 16Gi
      nvidia.com/gpu: 1  # If GPU available
  model: codellama:13b

# Dependencies
postgresql:
  enabled: true
  auth:
    postgresPassword: ""
    database: novasight
  primary:
    persistence:
      size: 100Gi

redis:
  enabled: true
  auth:
    enabled: true
    password: ""
  master:
    persistence:
      size: 10Gi

clickhouse:
  enabled: true
  shards: 1
  replicaCount: 2
  persistence:
    size: 500Gi

# Monitoring
monitoring:
  enabled: true
  prometheus:
    enabled: true
    serviceMonitor:
      enabled: true
  grafana:
    enabled: true
```

### Backend Template

```yaml
# helm/novasight/templates/backend/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "novasight.fullname" . }}-backend
  labels:
    {{- include "novasight.labels" . | nindent 4 }}
    app.kubernetes.io/component: backend
spec:
  {{- if not .Values.backend.autoscaling.enabled }}
  replicas: {{ .Values.backend.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "novasight.selectorLabels" . | nindent 6 }}
      app.kubernetes.io/component: backend
  template:
    metadata:
      labels:
        {{- include "novasight.selectorLabels" . | nindent 8 }}
        app.kubernetes.io/component: backend
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/backend/configmap.yaml") . | sha256sum }}
    spec:
      serviceAccountName: {{ include "novasight.serviceAccountName" . }}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
        - name: backend
          image: "{{ .Values.global.imageRegistry }}/{{ .Values.backend.image.repository }}:{{ .Values.backend.image.tag }}"
          imagePullPolicy: {{ .Values.backend.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 5000
            - name: metrics
              containerPort: 9090
          envFrom:
            - configMapRef:
                name: {{ include "novasight.fullname" . }}-backend-config
            - secretRef:
                name: {{ include "novasight.fullname" . }}-backend-secrets
          resources:
            {{- toYaml .Values.backend.resources | nindent 12 }}
          livenessProbe:
            {{- toYaml .Values.backend.livenessProbe | nindent 12 }}
          readinessProbe:
            {{- toYaml .Values.backend.readinessProbe | nindent 12 }}
      {{- with .Values.backend.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    {{- include "novasight.selectorLabels" . | nindent 20 }}
                    app.kubernetes.io/component: backend
                topologyKey: kubernetes.io/hostname
```

### Helpers Template

```yaml
# helm/novasight/templates/_helpers.tpl
{{/*
Expand the name of the chart.
*/}}
{{- define "novasight.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "novasight.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "novasight.labels" -}}
helm.sh/chart: {{ include "novasight.chart" . }}
{{ include "novasight.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "novasight.selectorLabels" -}}
app.kubernetes.io/name: {{ include "novasight.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "novasight.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "novasight.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
```

### Environment Overrides

```yaml
# helm/novasight/values-staging.yaml
backend:
  replicaCount: 2
  image:
    tag: develop
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
    limits:
      cpu: 1000m
      memory: 1Gi
  autoscaling:
    enabled: false

frontend:
  replicaCount: 1
  image:
    tag: develop

ingress:
  hosts:
    - host: staging.novasight.io
      paths:
        - path: /
          pathType: Prefix
          service: frontend
    - host: api.staging.novasight.io
      paths:
        - path: /
          pathType: Prefix
          service: backend

clickhouse:
  shards: 1
  replicaCount: 1
  persistence:
    size: 50Gi

---
# helm/novasight/values-production.yaml
backend:
  replicaCount: 5
  image:
    tag: v1.0.0
  resources:
    requests:
      cpu: 1
      memory: 1Gi
    limits:
      cpu: 4
      memory: 4Gi
  autoscaling:
    enabled: true
    minReplicas: 5
    maxReplicas: 20

frontend:
  replicaCount: 3
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10

clickhouse:
  shards: 2
  replicaCount: 3
  persistence:
    size: 1Ti
```

## Expected Output

```
helm/
└── novasight/
    ├── Chart.yaml
    ├── values.yaml
    ├── values-staging.yaml
    ├── values-production.yaml
    ├── templates/
    │   ├── _helpers.tpl
    │   ├── NOTES.txt
    │   ├── backend/
    │   │   ├── deployment.yaml
    │   │   ├── service.yaml
    │   │   ├── hpa.yaml
    │   │   └── configmap.yaml
    │   ├── frontend/
    │   │   ├── deployment.yaml
    │   │   └── service.yaml
    │   ├── ingress.yaml
    │   └── serviceaccount.yaml
    └── charts/
```

## Acceptance Criteria

- [ ] Chart installs successfully
- [ ] All dependencies resolve
- [ ] Values override correctly
- [ ] Secrets templated properly
- [ ] Resource limits configurable
- [ ] Autoscaling configurable
- [ ] Multiple environments supported
- [ ] `helm lint` passes

## Reference Documents

- [Infrastructure Agent](../agents/infrastructure-agent.agent.md)
- [Kubernetes Manifests](./038-kubernetes-manifests.md)
