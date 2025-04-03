from tinkoff_agent import TinkoffAgent
from tinkoff.invest import Client
from dotenv import load_dotenv
import os
import yaml
import logging

def setup_logging(config):
    logging.basicConfig(
        level=config['logging']['level'],
        format=config['logging']['format']
    )
    return logging.getLogger('tinkoff_agent')

def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def main():
    # Загружаем конфигурацию
    config = load_config()
    
    # Настраиваем логирование
    logger = setup_logging(config)
    logger.info("Starting Tinkoff Trading Agent")
    
    # Загружаем переменные окружения
    load_dotenv()
    token = os.getenv("TINKOFF_TOKEN")
    if not token:
        raise ValueError("TINKOFF_TOKEN не найден в переменных окружения")

    # Инициализируем клиент Tinkoff API
    with Client(token) as client:
        # Проверяем подключение
        accounts = client.users.get_accounts()
        logger.info(f"Connected to Tinkoff API. Found {len(accounts.accounts)} accounts")
        
        # Проверяем, что указанный account_id существует
        account_ids = [str(acc.id) for acc in accounts.accounts]
        if config['tinkoff']['account_id'] not in account_ids:
            raise ValueError(f"Account ID {config['tinkoff']['account_id']} not found in available accounts: {account_ids}")
        
        # Инициализируем агента
        agent = TinkoffAgent(client, config)
        
        # Запускаем агента
        logger.info("Starting agent...")
        agent.run(
            host=config['api']['host'],
            port=config['api']['port']
        )

if __name__ == "__main__":
    main() 