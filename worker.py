"""
Classe Worker para automações integradas ao N8N.

Esta classe fornece comunicação direta com N8N via webhooks para:
- Controle de status de tarefas
- Logging estruturado
- Salvamento de KPIs
- Tratamento de erros padronizado

Exemplo de uso:
    from worker import Worker, AutomationStatus
    
    class MinhaAutomacao(Worker):
        def main(self):
            try:
                self.log_info("Iniciando automação")
                
                # Sua lógica aqui
                items_processados = 100
                items_falharam = 5
                
                self.new_kpi_entry("dados_vendas", {
                    "vendas_total": 50000,
                    "clientes_novos": 25
                })
                
                self.finish_task(
                    status=AutomationStatus.SUCCESS,
                    message="Automação executada com sucesso",
                    total_items=105,
                    processed_items=items_processados,
                    failed_items=items_falharam
                )
                
            except Exception as e:
                self.error(e)
                self.finish_task(
                    status=AutomationStatus.ERROR,
                    message=str(e),
                    total_items=105,
                    processed_items=items_processados,
                    failed_items=items_falharam
                )
            finally:
                self.cleanup()
"""

import os
import sys
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import requests


class AutomationStatus(Enum):
    """Status padronizados para automações."""
    SUCCESS = "completed"
    PARTIAL_SUCCESS = "partially_completed"
    ERROR = "error"


class Task:
    """Classe que representa uma tarefa obtida via API N8N."""
    
    def __init__(self, task_data: Dict[str, Any]):
        """
        Inicializa a tarefa com dados da API N8N.
        
        Args:
            task_data: Dicionário com dados da tarefa
        """
        self.id = task_data.get('id')
        self.automation_id = task_data.get('automation_id')
        self.status = task_data.get('status')
        self.parameters = task_data.get('parameters', {})
        self.created_at = task_data.get('created_at')
        self.started_at = task_data.get('started_at')
        self._raw_data = task_data
        
    def get_parameter(self, key: str, default=None):
        """Retorna um parâmetro da tarefa."""
        return self.parameters.get(key, default)
    
    def get_all_parameters(self) -> Dict[str, Any]:
        """Retorna todos os parâmetros da tarefa."""
        return self.parameters.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Retorna todos os dados da tarefa."""
        return self._raw_data.copy()


class Worker:
    """Classe base para automações integradas ao N8N."""
    
    def __init__(self, n8n_webhook_url=None, worker_id=None, task_id=None, automation_id=None, 
                 parameters=None, api_timeout=None, bot_version=None):
        """
        Inicializa o worker com configurações do ambiente ou parâmetros manuais.
        
        Args:
            n8n_webhook_url: URL base dos webhooks N8N (opcional, usa env se não fornecido)
            worker_id: ID do worker (opcional, usa env se não fornecido)
            task_id: ID da tarefa (opcional, usa env se não fornecido)
            automation_id: ID da automação (opcional, usa env se não fornecido)
            parameters: Dicionário de parâmetros (opcional, usa env se não fornecido)
            api_timeout: Timeout para APIs (opcional, usa env se não fornecido)
            bot_version: Versão do bot (opcional, usa env se não fornecido)
        """
        
        # URLs dos webhooks N8N
        self.n8n_webhook_base = n8n_webhook_url or os.getenv('N8N_WEBHOOK_URL')
        
        # Worker ID
        self.worker_id = worker_id or os.getenv('WORKER_ID')
        
        # Configurações de timeout e bot version
        self.api_timeout = api_timeout or int(os.getenv('API_TIMEOUT', '30'))
        self.bot_version = bot_version or os.getenv('BOT_VERSION', 'main')
        
        # Task ID e Automation ID (podem não existir no modo desenvolvimento)
        env_task_id = os.getenv('TASK_ID')
        env_automation_id = os.getenv('AUTOMATION_ID')
        
        if task_id is not None:
            self.task_id = int(task_id)
        elif env_task_id:
            self.task_id = int(env_task_id)
        else:
            self.task_id = None  # Pode ser None no modo desenvolvimento
            
        if automation_id is not None:
            self.automation_id = int(automation_id)
        elif env_automation_id:
            self.automation_id = int(env_automation_id)
        else:
            self.automation_id = None  # Pode ser None no modo desenvolvimento
        
        # Parâmetros da tarefa
        if parameters is not None:
            self.parameters = parameters
        else:
            parameters_str = os.getenv('TASK_PARAMETERS', '{}')
            try:
                self.parameters = json.loads(parameters_str)
            except json.JSONDecodeError:
                self.parameters = {}
        
        # Inicializa estado interno
        self._task_started = False
        self._task_finished = False
        
        # NÃO inicia a tarefa automaticamente - isso é responsabilidade do task_processor
        # O status 'running' é gerenciado pelo worker principal
    
    def log_info(self, message: str, source: str = "stdout"):
        """Registra um log de informação."""
        self._send_log("info", message, source)
        print(f"[INFO] {message}")
    
    def log_warning(self, message: str, source: str = "system"):
        """Registra um log de aviso."""
        self._send_log("warning", message, source)
        print(f"[WARNING] {message}")
    
    def log_error(self, message: str, source: str = "stderr"):
        """Registra um log de erro."""
        self._send_log("error", message, source)
        print(f"[ERROR] {message}", file=sys.stderr)
    
    def log_debug(self, message: str, source: str = "system"):
        """Registra um log de debug."""
        self._send_log("debug", message, source)
        print(f"[DEBUG] {message}")
    
    def error(self, exception: Exception, context: str = ""):
        """
        Registra uma exceção com contexto.
        
        Args:
            exception: A exceção que ocorreu
            context: Contexto adicional sobre o erro
        """
        error_msg = f"{context}: {type(exception).__name__}: {str(exception)}" if context else f"{type(exception).__name__}: {str(exception)}"
        
        # Log do erro
        self.log_error(error_msg)
        
        # Log do traceback completo
        tb_str = traceback.format_exc()
        self.log_error(f"Traceback:\n{tb_str}")
    
    def _send_log(self, level: str, message: str, source: str):
        """Envia log para o N8N (método interno)."""
        try:
            log_data = {
                "task_id": self.task_id,
                "logs": [{
                    "level": level,
                    "message": message,
                    "source": source,
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            
            requests.post(
                f"{self.n8n_webhook_base}/webhook/tarefa/logs",
                json=log_data,
                timeout=self.api_timeout
            )
            
        except Exception as e:
            # Se falhar ao enviar log, apenas imprime (não causa loop)
            print(f"[SYSTEM] Erro ao enviar log: {e}", file=sys.stderr)
    
    def new_kpi_entry(self, table_name: str, data: Dict[str, Any]):
        """
        Adiciona uma nova entrada de KPI no N8N.
        
        Args:
            table_name: Nome da "tabela" virtual do KPI
            data: Dicionário com os dados do KPI
        """
        try:
            kpi_data = {
                "task_id": self.task_id,
                "kpis": [{
                    "table_name": table_name,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            
            response = requests.post(
                f"{self.n8n_webhook_base}/webhook/tarefa/kpi",
                json=kpi_data,
                timeout=self.api_timeout
            )
            
            if response.status_code in [200, 201]:
                self.log_info(f"KPI salvo na tabela '{table_name}': {data}")
            else:
                self.log_error(f"Erro ao salvar KPI: {response.status_code}")
                
        except Exception as e:
            self.log_error(f"Erro ao salvar KPI: {e}")
    
    def finish_task(self, status: AutomationStatus, message: str,
                   total_items: int, processed_items: int, failed_items: int):
        """
        Finaliza a tarefa com os resultados no N8N.
        
        TODOS OS PARÂMETROS SÃO OBRIGATÓRIOS.
        
        Args:
            status: Status final da tarefa (AutomationStatus.SUCCESS, ERROR, PARTIAL_SUCCESS)
            message: Mensagem de resultado ou erro
            total_items: Total de itens que deveriam ser processados
            processed_items: Número de itens processados com sucesso
            failed_items: Número de itens que falharam
        """
        try:
            if self._task_finished:
                self.log_warning("finish_task() já foi chamado anteriormente")
                return
            
            self.log_info(f"Finalizando tarefa {self.task_id} com status: {status.value}")
            
            # Validação dos parâmetros obrigatórios
            if not isinstance(status, AutomationStatus):
                raise ValueError("status deve ser uma instância de AutomationStatus")
            if not message:
                raise ValueError("message é obrigatório")
            if total_items < 0 or processed_items < 0 or failed_items < 0:
                raise ValueError("Contadores não podem ser negativos")
            if processed_items + failed_items > total_items:
                raise ValueError("processed_items + failed_items não pode ser maior que total_items")
            
            update_data = {
                "task_id": self.task_id,
                "status": status.value,
                "finished_at": datetime.utcnow().isoformat(),
                "bot_version": self.bot_version,
                "total_items": total_items,
                "processed_items": processed_items,
                "failed_items": failed_items
            }
            
            # Define a mensagem no campo correto baseado no status
            if status == AutomationStatus.ERROR:
                update_data["error_message"] = message
            else:
                update_data["result_message"] = message
            
            # 1. Tenta enviar para N8N primeiro
            response = requests.patch(
                f"{self.n8n_webhook_base}/webhook/tarefa/status",
                json=update_data,
                timeout=self.api_timeout
            )
            
            if response.status_code in [200, 201]:
                self._task_finished = True
                self.log_info(f"Tarefa finalizada com status: {status.value}")
                self.log_info(f"Resultados: {processed_items} sucesso, {failed_items} falhas de {total_items} total")
                self.log_info("finish_task() executado com sucesso!")
            else:
                self.log_error(f"Erro ao finalizar tarefa via webhook: {response.status_code}")
                self.log_error(f"Response: {response.text}")
                # Mesmo se webhook falhar, marca como finalizada
                self._task_finished = True
                
        except Exception as e:
            self.log_error(f"Erro ao finalizar tarefa: {e}")
            # Marca como finalizada mesmo com erro para evitar loop
            self._task_finished = True
            raise  # Re-raise para forçar o desenvolvedor a corrigir
    
    def get_parameter(self, key: str, default=None):
        """Retorna um parâmetro da tarefa."""
        return self.parameters.get(key, default)
    
    def get_all_parameters(self) -> Dict[str, Any]:
        """Retorna todos os parâmetros da tarefa."""
        return self.parameters.copy()
    
    def get_task_info(self, task_id=None):
        """
        Obtém informações da tarefa atual ou especificada.
        
        Args:
            task_id: ID da tarefa (opcional, usa self.task_id se não fornecido)
            
        Returns:
            Task: Objeto Task com informações da tarefa
        """
        # Se task_id não foi fornecido, usa o da instância atual
        if task_id is None:
            task_id = self.task_id
        
        # Se ainda não temos task_id, simula uma tarefa para desenvolvimento
        if task_id is None:
            self.log_warning("Task ID não definido - modo desenvolvimento")
            task_id = 'dev-task-1'
            
        try:
            # Em um ambiente real, aqui faria uma chamada para a API N8N
            # Por enquanto, cria um objeto Task com os dados atuais
            task_data = {
                'id': task_id,
                'automation_id': self.automation_id or 'dev-automation-1',
                'status': 'running' if self._task_started else 'pending',
                'parameters': self.parameters,
                'created_at': None,
                'started_at': datetime.utcnow().isoformat() if self._task_started else None
            }
            
            # Atualiza o task_id interno se estava None
            if self.task_id is None:
                self.task_id = task_id
                
            return Task(task_data)
            
        except Exception as e:
            self.log_error(f"Erro ao obter informações da tarefa: {e}")
            # Retorna task vazia em caso de erro
            return Task({
                'id': task_id or 'error-task',
                'automation_id': getattr(self, 'automation_id', None) or 'error-automation',
                'parameters': {}
            })
    
    def cleanup(self):
        """Método para limpeza de recursos. Deve ser sobrescrito se necessário."""
        pass
    
    def main(self):
        """
        Método principal da automação. DEVE ser implementado pelas classes filhas.
        
        Raises:
            NotImplementedError: Se não for implementado pela classe filha
        """
        raise NotImplementedError("O método main() deve ser implementado pela automação")


# Função utilitária para executar automação
def run_automation():
    """Função para executar a automação a partir do bot.py."""
    
    # Verifica se todas as variáveis de ambiente necessárias estão definidas
    required_vars = ['TASK_ID', 'AUTOMATION_ID', 'WORKER_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"[ERROR] Variáveis de ambiente obrigatórias não definidas: {', '.join(missing_vars)}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Importa dinamicamente a classe da automação
        # O bot.py deve ter uma classe que herda de Worker
        import importlib.util
        
        # Carrega o módulo bot.py
        spec = importlib.util.spec_from_file_location("bot", "bot.py")
        if spec is None:
            raise ImportError("Não foi possível carregar bot.py")
        
        bot_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bot_module)
        
        # Procura por uma classe que herda de Worker
        automation_class = None
        for name in dir(bot_module):
            obj = getattr(bot_module, name)
            if (isinstance(obj, type) and 
                issubclass(obj, Worker) and 
                obj != Worker):
                automation_class = obj
                break
        
        if automation_class is None:
            raise ImportError("Nenhuma classe que herda de Worker foi encontrada em bot.py")
        
        # Executa a automação
        automation = automation_class()
        try:
            automation.main()
        except Exception as e:
            automation.error(e, "Erro na execução da automação")
            # Força finalização com erro se não foi chamada
            if not automation._task_finished:
                automation.finish_task(
                    status=AutomationStatus.ERROR,
                    message=str(e),
                    total_items=0,
                    processed_items=0,
                    failed_items=0
                )
            raise
        finally:
            automation.cleanup()
        
    except Exception as e:
        print(f"[ERROR] Erro crítico na execução: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_automation()
