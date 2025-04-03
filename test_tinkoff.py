from tinkoff.invest import Client
from dotenv import load_dotenv
import os

def main():
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем токен из переменных окружения
    token = os.getenv("TINKOFF_TOKEN")
    if not token:
        raise ValueError("TINKOFF_TOKEN не найден в переменных окружения")

    # Подключаемся к API
    with Client(token) as client:
        # Получаем информацию об аккаунтах
        accounts = client.users.get_accounts()
        print("\nВаши счета:")
        for account in accounts.accounts:
            print(f"- {account.name} (ID: {account.id})")
            
            # Получаем портфолио для каждого счета
            try:
                portfolio = client.operations.get_portfolio(account_id=account.id)
                print(f"  Баланс: {portfolio.total_amount_portfolio.units}.{portfolio.total_amount_portfolio.nano} {portfolio.total_amount_portfolio.currency}")
                
                # Показываем позиции в портфеле
                if portfolio.positions:
                    print("  Позиции:")
                    for position in portfolio.positions:
                        print(f"    * {position.figi}: {position.quantity.units} шт.")
                else:
                    print("  Позиций нет")
            except Exception as e:
                print(f"  Ошибка при получении портфолио: {e}")
            print()

if __name__ == "__main__":
    main() 