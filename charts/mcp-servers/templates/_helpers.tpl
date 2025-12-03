{{/*
Compute proxy file checksum
*/}}
{{- define "mcpServers.proxy.checksum" -}}
{{- .Files.Get "files/proxy.py" | sha256sum -}}
{{- end }}

{{/*
Expand the name of the chart.
*/}}
{{- define "mcpServers.chart" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "mcpServers.chartref" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "mcpServers.fullname" -}}
{{- if .Values }}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name (.Values.nameOverride | default "") }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- else }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Create a fully qualified server name.
*/}}
{{- define "mcpServers.server.fullname" -}}
{{- $server := index . "server" }}
{{- $ctx := index . "ctx" | default . }}
{{- printf "%s-%s" (include "mcpServers.fullname" $ctx) $server.name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create server name and version as used by the label.
*/}}
{{- define "mcpServers.server.label" -}}
{{- $server := index . "server" -}}
{{- $ctx := index . "ctx" | default . }}
{{- printf "%s-%s" (include "mcpServers.fullname" $ctx) $server.name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Choose default image tag
*/}}
{{- define "mcpServers.defaultImageTag" -}}
{{- $server := index . "server" -}}
{{- $ctx := index . "ctx" | default . }}
{{- if $server.image.repository }}
{{- else }}
{{- $ctx.Values.defaultImage.tag }}
{{- end }}
{{- end }}

{{/*
Get default image or use explicit image
*/}}
{{- define "mcpServers.image" -}}
{{- $server := index . "server" -}}
{{- $ctx := index . "ctx" | default . }}
{{- if and $server.image $server.image.repository }}
{{- printf "%s:%s" $server.image.repository ($server.image.tag | default (include "mcpServers.defaultImageTag" (dict "server" $server "ctx" $ctx))) }}
{{- else }}
{{- printf "%s:%s" $ctx.Values.defaultImage.repository $ctx.Values.defaultImage.tag }}
{{- end }}
{{- end }}

{{/*
Get image pull policy
*/}}
{{- define "mcpServers.imagePullPolicy" -}}
{{- $server := index . "server" -}}
{{- $ctx := index . "ctx" | default . }}
{{- if and $server.image $server.image.pullPolicy }}
{{- $server.image.pullPolicy }}
{{- else }}
{{- $ctx.Values.defaultImage.pullPolicy }}
{{- end }}
{{- end }}

{{/*
Create server labels
*/}}
{{- define "mcpServers.server.labels" -}}
{{- $server := index . "server" -}}
{{- $ctx := index . "ctx" | default . }}
helm.sh/chart: {{ include "mcpServers.chartref" $ctx }}
{{ include "mcpServers.server.selectorLabels" . }}
{{- if $ctx.Chart.AppVersion }}
app.kubernetes.io/version: {{ $ctx.Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ $ctx.Release.Service }}
app.kubernetes.io/name: {{ include "mcpServers.server.label" . }}
app.kubernetes.io/instance: {{ $ctx.Release.Name }}
app.kubernetes.io/component: {{ $server.name }}
{{- end }}

{{/*
Create server selector labels
*/}}
{{- define "mcpServers.server.selectorLabels" -}}
{{- $server := index . "server" -}}
{{- $ctx := index . "ctx" | default . }}
app.kubernetes.io/name: {{ include "mcpServers.server.label" . }}
app.kubernetes.io/instance: {{ $ctx.Release.Name }}
{{- end }}

{{/*
Create Service name
*/}}
{{- define "mcpServers.service.name" -}}
{{- $server := index . "server" }}
{{- printf "%s" (include "mcpServers.server.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create ConfigMap name
*/}}
{{- define "mcpServers.configmap.name" -}}
{{- $server := index . "server" }}
{{- printf "%s-config" (include "mcpServers.server.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create Secret name
*/}}
{{- define "mcpServers.secret.name" -}}
{{- $server := index . "server" }}
{{- printf "%s-secret" (include "mcpServers.server.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Render environment variables with valueFrom support
*/}}
{{- define "mcpServers.env.vars" -}}
{{- $server := index . "server" }}
env:
{{- range $server.env }}
  - name: {{ .name }}
    {{- if .value }}
    value: {{ .value | quote }}
    {{- end }}
    {{- if .valueFrom }}
    valueFrom:
      {{- toYaml .valueFrom | nindent 6 }}
    {{- end }}
{{- end }}
{{- end }}

{{/*
Handle volumes and volumeMounts
*/}}
{{- define "mcpServers.volumes" -}}
{{- $server := index . "server" }}
{{- if $server.volumes }}
volumes:
{{ toYaml $server.volumes | indent 2 }}
{{- end }}
{{- end }}

{{- define "mcpServers.volumeMounts" -}}
{{- $server := index . "server" }}
{{- if $server.volumeMounts }}
volumeMounts:
{{ toYaml $server.volumeMounts | indent 2 }}
{{- end }}
{{- end }}

{{/*
Generate proxy server command as Go slice format
*/}}
{{- define "mcpServers.proxy.command" -}}
{{- $server := index . "server" }}
{{- $ctx := index . "ctx" | default . }}
{{- $port := 3000 }}
{{- if and $server.service $server.service.targetPort }}
{{- $port = $server.service.targetPort }}
{{- end }}
{{- $serverName := $server.name | title }}
{{- $backendCommand := $server.command | join " " }}
["uvx", "--with", "fastmcp", "--from", "fastmcp", "python", "/app/proxy.py", "--backend-command", {{ $backendCommand | quote }}, "--server-name", {{ $serverName | quote }}, "--port", {{ $port | toString | quote }}]
{{- end }}

{{/*
Get appropriate image for proxy mode
*/}}
{{- define "mcpServers.proxy.image" -}}
{{- $ctx := index . "ctx" | default . }}
{{- printf "%s:%s" $ctx.Values.defaultImage.repository $ctx.Values.defaultImage.tag }}
{{- end }}

{{/*
Get proxy volumes
*/}}
{{- define "mcpServers.proxy.volumes" -}}
{{- $server := index . "server" }}
{{- $ctx := index . "ctx" | default . }}
{{- if and $server.proxy $server.proxy.enabled }}
- name: proxy-script
  configMap:
    name: mcp-proxy-script
    defaultMode: 0755
{{- end }}
{{- end }}

{{/*
Get proxy volumeMounts
*/}}
{{- define "mcpServers.proxy.volumeMounts" -}}
{{- $server := index . "server" }}
{{- $ctx := index . "ctx" | default . }}
{{- if and $server.proxy $server.proxy.enabled }}
- name: proxy-script
  mountPath: /app
  readOnly: true
{{- end }}
{{- end }}

{{/*
Validate required fields
*/}}
{{- define "mcpServers.validate" -}}
{{- $server := index . "server" }}
{{- if not $server.name }}
{{- fail "Server name is required" }}
{{- end }}
{{- if not $server.command }}
{{- fail "Server command is required" }}
{{- end }}
{{- if not (hasKey $server "enabled") }}
{{- fail "Server enabled field is required" }}
{{- end }}
{{- end }}