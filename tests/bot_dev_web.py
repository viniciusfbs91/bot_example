"""
Exemplo de automação para o sistema Worker.

Esta automação demonstra como:
- Usar a classe Worker base
- Processar parâmetros
- Registrar logs e KPIs
- Tratar erros adequadamente
- Finalizar tarefas com resultados
"""

import time
import random
from worker import Worker, AutomationStatus
from botcity.web import WebBot

def main():
    """Método principal da automação."""
    try:
            
        client_worker = Worker(n8n_webhook_url="http://localhost:5678/webhook")
        
        task = client_worker.get_task_info(task_id='1')
        
        client_worker.log_info("=== INICIANDO AUTOMAÇÃO DE EXEMPLO ===")
        
        # Obtém parâmetros
        total_items = task.get_parameter('total_items', 1)
        delay_seconds = task.get_parameter('delay_seconds', 1)
        simulate_errors = task.get_parameter('simulate_errors', False)
        
        client_worker.log_info(f"Processando {total_items} itens com delay de {delay_seconds}s")
        
        # Contadores
        processed_items = 0
        failed_items = 0
        # Instancia o WebBot
        bot = WebBot()

        # Configure se deseja ou não executar no modo headless.
        bot.headless = False

        # Defina o caminho do WebDriver
        bot.driver_path = "<path to your WebDriver binary>"

        # Abre o site do BotCity.
        bot.browse("https://www.botcity.dev")

        # Aguarde 3 segundos antes de fechar.
        bot.wait(3000)

        # Concluir e limpar o navegador da Web.
        bot.stop_browser()

        # Registra KPIs de resumo
        client_worker.new_kpi_entry("resumo_execucao", {
            "total_processado": processed_items,
            "total_falharam": failed_items,
            "taxa_sucesso": (processed_items / total_items) * 100 if total_items > 0 else 0,
                "tempo_medio_item": delay_seconds
            })
        
        # Determina status final e finaliza tarefa
        if failed_items == 0:
            status = AutomationStatus.SUCCESS
            message = f"Todos os {processed_items} itens processados com sucesso"
        elif processed_items > 0:
            status = AutomationStatus.PARTIAL_SUCCESS
            message = f"{processed_items} itens processados, {failed_items} falharam"
        else:
            status = AutomationStatus.ERROR
            message = f"Todos os {failed_items} itens falharam"
        
        client_worker.log_info(f"=== AUTOMAÇÃO FINALIZADA ===")
        client_worker.log_info(f"Status: {status.value}")
        client_worker.log_info(f"Processados: {processed_items}")
        client_worker.log_info(f"Falharam: {failed_items}")
        
        # Finaliza a tarefa - TODOS OS PARÂMETROS SÃO OBRIGATÓRIOS
        client_worker.finish_task(
            status=status,
            message=message,
            total_items=total_items,
            processed_items=processed_items,
            failed_items=failed_items
        )
        
    except Exception as e:
        message = f"Finalizado com Erro: {str(e)}"
        status = AutomationStatus.ERROR
        # Erro não tratado na automação
        client_worker.error(e, "Erro crítico na automação")
        
    finally:
        
        # Sempre colocar o cleanup no finally para garantir execução e dentro de um bloco try/except, nesse bloco do código não pode ocorrer erros
        try:
            client_worker.cleanup()
        except Exception as e:
            client_worker.error(e, "Erro ao executar cleanup")

        client_worker.finish_task(
            status=status,
            message=message,
            total_items=total_items,
            processed_items=processed_items,
            failed_items=failed_items
        )
        
def cleanup(self):
    """Limpeza de recursos (opcional)."""
    # Aqui você pode fechar conexões, arquivos, etc.


# O arquivo bot.py deve sempre ter esta estrutura para ser executado
if __name__ == "__main__":
    main()