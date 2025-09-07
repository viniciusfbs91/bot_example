# Exemplo de Bot para o Sistema Worker integrado ao N8N

Este é um exemplo de como criar uma automação para o sistema Worker que se comunica diretamente com N8N via webhooks.

## Estrutura do Bot

```
bot-exemplo/
├── bot.py              # Lógica principal da automação
├── worker.py           # Classe base Worker para N8N
├── requirements.txt    # Dependências Python
└── README.md          # Este arquivo
```

## Como usar

1. **bot.py**: Contém sua automação principal que herda de Worker
2. **worker.py**: Classe base que gerencia toda comunicação com N8N
3. **requirements.txt**: Liste suas dependências Python (requests já incluído)

## Características da Classe Worker

### Comunicação com N8N
- **Webhooks diretos**: Comunicação via webhooks N8N
- **Registro automático**: Worker se registra no sistema
- **Heartbeat**: Monitoramento em tempo real
- **Status em tempo real**: Atualizações automáticas de status

### Métodos Principais
- `self.log_info()`, `self.log_error()` - Logs estruturados
- `self.new_kpi_entry()` - Métricas customizadas
- `self.finish_task()` - Finalização com resultados
- `self.get_parameter()` - Acesso a parâmetros
- `self.send_custom_webhook()` - Webhooks customizados

## Parâmetros

Os parâmetros são passados via `self.parameters` e podem incluir:
- URLs para processar
- Credenciais de APIs  
- Configurações específicas
- Dados de entrada

Exemplo de acesso:
```python
total_items = self.get_parameter('total_items', 100)
api_key = self.get_parameter('api_key')
```

## Logs e KPIs

Use os métodos do Worker para registrar progresso:
```python
# Logs
self.log_info("Processando dados...")
self.log_warning("Atenção: taxa de erro alta")
self.log_error("Falha na conexão")

# KPIs estruturados
self.new_kpi_entry("vendas_detalhes", {
    "item_id": "item_001",
    "valor": 150.00,
    "categoria": "A"
})
```

## Webhooks Customizados

Envie dados para workflows N8N customizados:
```python
# Exemplo: notificar sistema externo
self.send_custom_webhook("notificacao-slack", {
    "mensagem": "Automação finalizada",
    "status": "sucesso"
})
```

## Finalização

Sempre chame `self.finish_task()` com:
```python
self.finish_task(
    status="completed",           # completed, error, partially_completed
    message="Processo concluído", # Mensagem de resultado
    total_items=100,             # Total processado
    processed_items=95,          # Sucesso
    failed_items=5              # Falhas
)
```

## Variáveis de Ambiente

O sistema Worker configura automaticamente:
- `TASK_ID` - ID da tarefa
- `AUTOMATION_ID` - ID da automação
- `WORKER_ID` - ID do worker
- `N8N_WEBHOOK_URL` - Base URL dos webhooks N8N
- `TASK_PARAMETERS` - Parâmetros em JSON
- `BOT_VERSION` - Versão do bot (branch GitHub)

## Integração N8N

A classe Worker se integra com os seguintes webhooks N8N:
- `/webhook/worker/registro` - Registro do worker
- `/webhook/tarefa/{task_id}/status` - Atualizações de status
- `/webhook/tarefa/logs` - Envio de logs (task_id no body)
- `/webhook/tarefa/kpi` - Dados de KPI (task_id no body)
- `/webhook/worker/heartbeat` - Monitoramento (worker_id no body)

## Tratamento de Erros

```python
try:
    # Sua lógica aqui
    pass
except Exception as e:
    self.error(e, "Contexto do erro")
    self.finish_task("error", str(e))
```

A classe Worker automaticamente:
- Registra traceback completo
- Atualiza status no N8N
- Para heartbeat
- Executa cleanup
