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


def main():
    """Método principal da automação."""
    client_worker = Worker()
    
    task = client_worker.get_task_info()
    
    client_worker.log_info("=== INICIANDO AUTOMAÇÃO DE EXEMPLO ===")
    
    # Obtém parâmetros
    total_items = task.get_parameter('total_items', 1)
    delay_seconds = task.get_parameter('delay_seconds', 1)
    simulate_errors = task.get_parameter('simulate_errors', False)
    
    client_worker.log_info(f"Processando {total_items} itens com delay de {delay_seconds}s")
    
    # Contadores
    processed_items = 0
    failed_items = 0
    
    try:
        # Simula processamento de itens
        for i in range(total_items):
            item_id = f"item_{i+1:04d}"
            
            try:
                client_worker.log_info(f"Processando {item_id}")
                
                # Simula processamento
                time.sleep(delay_seconds)
                
                # Simula erro ocasional se habilitado
                if simulate_errors and random.random() < 0.1:  # 10% de chance de erro
                    raise Exception(f"Erro simulado no {item_id}")
                
                # Simula dados processados
                valor_vendas = random.randint(100, 1000)
                categoria = random.choice(['A', 'B', 'C'])
                
                # Registra KPI do item
                client_worker.new_kpi_entry("vendas_detalhes", {
                    "item_id": item_id,
                    "valor": valor_vendas,
                    "categoria": categoria,
                    "status": "processado"
                })
                
                processed_items += 1
                
                # Log de progresso a cada 10 itens
                if (i + 1) % 10 == 0:
                    progress = ((i + 1) / total_items) * 100
                    client_worker.log_info(f"Progresso: {progress:.1f}% ({i+1}/{total_items})")
            
            except Exception as e:
                failed_items += 1
                client_worker.log_error(f"Erro ao processar {item_id}: {e}")
                
                # Registra item com falha no KPI
                client_worker.new_kpi_entry("vendas_detalhes", {
                    "item_id": item_id,
                    "erro": str(e),
                    "status": "falha"
                })
        
        # Registra KPIs de resumo
        client_worker.new_kpi_entry("resumo_execucao", {
            "total_processado": processed_items,
            "total_falharam": failed_items,
            "taxa_sucesso": (processed_items / total_items) * 100 if total_items > 0 else 0,
            "tempo_medio_item": delay_seconds
        })
        
        
        import os
        from botcity.web import WebBot, Browser


        # Instancia o WebBot
        bot = WebBot()


        # Configure se deseja ou não executar no modo headless.
        bot.headless = False

        # Defina o caminho do WebDriver
        # bot.driver_path = "<path to your WebDriver binary>"
        bot.start_browser()
        bot.sleep(5000)

        # Concluir e limpar o navegador da Web.
        bot.stop_browser()


        bot.browser = Browser.FIREFOX

        bot.start_browser()
        bot.sleep(5000)
        bot.stop_browser()

        
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
        # Erro não tratado na automação
        client_worker.error(e, "Erro crítico na automação")
        
        # Finaliza com erro se não foi finalizada ainda
        if not client_worker._task_finished:
            client_worker.finish_task(
                status=AutomationStatus.ERROR,
                message=f"Erro crítico: {str(e)}",
                total_items=total_items,
                processed_items=processed_items,
                failed_items=failed_items
            )
        
    finally:
        # Sempre colocar o cleanup no finally para garantir execução
        try:
            cleanup(client_worker)
        except Exception as e:
            client_worker.error(e, "Erro ao executar cleanup")
        

def cleanup(client_worker):
    """Limpeza de recursos (opcional)."""
    # Aqui você pode fechar conexões, arquivos, etc.


# O arquivo bot.py deve sempre ter esta estrutura para ser executado
if __name__ == "__main__":
    main()