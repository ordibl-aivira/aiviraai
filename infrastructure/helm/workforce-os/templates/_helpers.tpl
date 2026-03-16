{{/*
Common labels
*/}}
{{- define "workforce-os.labels" -}}
app.kubernetes.io/part-of: aivira
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
Full image reference
*/}}
{{- define "workforce-os.image" -}}
{{- if .Values.global.image.registry -}}
{{ .Values.global.image.registry }}/workforce-os/{{ .svc }}:{{ .Values.global.image.tag }}
{{- else -}}
workforce-os/{{ .svc }}:{{ .Values.global.image.tag }}
{{- end -}}
{{- end }}
