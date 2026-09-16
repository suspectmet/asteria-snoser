import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import time
import os
import json
import re
from datetime import datetime
import logging
import subprocess
import sys

# Функция для проверки и установки зависимостей ДО импорта
def check_dependencies():
    required_libraries = ["colorama", "art", "tqdm"]
    missing_libraries = []

    # Проверяем, есть ли файл, указывающий на успешную проверку
    if os.path.exists(".dependencies_checked"):
        return  # Если файл существует, пропускаем проверку

    print("Проверка зависимостей и библиотек...")
    for lib in required_libraries:
        try:
            __import__(lib)
        except ImportError:
            missing_libraries.append(lib)

    if missing_libraries:
        print(f"Обнаружены отсутствующие библиотеки: {', '.join(missing_libraries)}")
        print("Установка недостающих библиотек...")
        for lib in missing_libraries:
            try:
                if sys.platform == "linux" and "termux" in os.environ.get("PREFIX", ""):
                    # Для Termux
                    subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
                else:
                    # Для Kali Linux и других систем
                    subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
            except subprocess.CalledProcessError:
                print(f"Ошибка при установке библиотеки {lib}.")
                sys.exit(1)
        print("Все зависимости успешно установлены!")
    else:
        print("Все зависимости установлены.")

    # Создаем файл, чтобы указать, что проверка выполнена
    with open(".dependencies_checked", "w") as f:
        f.write("dependencies_checked")

# Проверяем зависимости перед импортом библиотек
check_dependencies()

# Теперь импортируем библиотеки после проверки
from colorama import Fore, Style, init
from art import text2art
from tqdm import tqdm

# Инициализация colorama
init(autoreset=True)

# Настройка логирования
logging.basicConfig(filename='email_sender.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Логотип программы
def display_logo():
    # Используем библиотеку `art` для создания ASCII-арта
    logo = text2art("Asteria Tool", font="mini")
    print(f"{Fore.CYAN}{logo}")
    print(f"{Fore.YELLOW}Version: {Fore.GREEN}v.1.2.2 (Актуальная)")
    print(f"{Fore.YELLOW}by {Fore.GREEN}@asteriasupp")
    print(f"{Fore.CYAN}{'=' * 40}")
    print(f"{Fore.YELLOW}Профессиональный инструмент отправки писем.")
    print(f"{Fore.CYAN}{'=' * 40}")
    print(f"{Fore.RED}Создатель не несёт ответветственности за использование, оборот, а также последствия использования программы.")
    print(f"{Fore.RED}Данный инструмент предназначен в целях этичного использования.")
    print(f"{Fore.CYAN}{'=' * 40}")

# Функция для загрузки сохраненных данных
def load_config():
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data.get("emails", [])  # Возвращаем список почт
                else:
                    print(f"{Fore.RED}Ошибка: Файл config.json должен содержать словарь.{Style.RESET_ALL}")
                    return []
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"{Fore.RED}Ошибка при загрузке config.json: {e}{Style.RESET_ALL}")
            return []
    return []

# Функция для сохранения данных
def save_config(emails):
    try:
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump({"emails": emails}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка при сохранении config.json: {e}")
        print(f"{Fore.RED}Ошибка: Не удалось сохранить конфигурацию.{Style.RESET_ALL}")

# Функция для проверки корректности почты
def is_valid_email(email):
    regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(regex, email) is not None

# Функция для авторизации почт
def authorize_emails():
    emails = load_config()

    print(f"{Fore.YELLOW}Введите почты для авторизации (Gmail).")
    print(f"{Fore.YELLOW}Для завершения ввода введите 'exit' и нажмите ENTER.")

    while True:
        email = input(f"{Fore.CYAN}Введите почту: {Style.RESET_ALL}")
        if email.lower() == "exit":
            break
        if not is_valid_email(email):
            print(f"{Fore.RED}Ошибка: Некорректный формат почты.{Style.RESET_ALL}")
            continue

        password = input(f"{Fore.CYAN}Введите пароль приложения для {email}: {Style.RESET_ALL}")
        if not password.strip():
            print(f"{Fore.RED}Ошибка: Пароль не может быть пустым.{Style.RESET_ALL}")
            continue

        # Проверка авторизации почты
        if check_email_auth(email, password):
            emails.append({
                "email": email,
                "password": password,
                "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            print(f"{Fore.GREEN}Почта {email} успешно добавлена и проверена!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Ошибка: Почта {email} не прошла проверку авторизации.{Style.RESET_ALL}")

    if not emails:
        print(f"{Fore.RED}Ошибка: Не добавлено ни одной почты.{Style.RESET_ALL}")
        return

    # Сохранение данных
    save_config(emails)
    print(f"{Fore.GREEN}Почты и пароли успешно сохранены!{Style.RESET_ALL}")
    time.sleep(1)
    clear_screen()

# Функция для проверки авторизации почт
def check_email_auth(email, password):
    try:
        # Определяем SMTP-сервер и порт для Gmail
        smtp_server = "smtp.gmail.com"
        smtp_ports = [587, 465]  # Попробуем оба порта

        # Пробуем подключиться к SMTP-серверу через разные порты
        for smtp_port in smtp_ports:
            try:
                print(f"{Fore.YELLOW}Попытка подключения к {smtp_server}:{smtp_port}...{Style.RESET_ALL}")
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()  # Включаем шифрование TLS
                    server.login(email, password)  # Авторизация
                print(f"{Fore.GREEN}Успешное подключение к {smtp_server}:{smtp_port}{Style.RESET_ALL}")
                return True
            except smtplib.SMTPAuthenticationError:
                print(f"{Fore.RED}Ошибка: Неверный логин или пароль для почты {email}.{Style.RESET_ALL}")
                return False
            except smtplib.SMTPException as e:
                print(f"{Fore.RED}Ошибка при подключении к {smtp_server}:{smtp_port}: {e}{Style.RESET_ALL}")
                continue  # Пробуем следующий порт
            except Exception as e:
                print(f"{Fore.RED}Неизвестная ошибка при подключении к {smtp_server}:{smtp_port}: {e}{Style.RESET_ALL}")
                continue  # Пробуем следующий порт

        # Если ни один порт не сработал
        print(f"{Fore.RED}Не удалось подключиться к SMTP-серверу для почты {email}.{Style.RESET_ALL}")
        return False

    except Exception as e:
        print(f"{Fore.RED}Неизвестная ошибка при проверке почты {email}: {e}{Style.RESET_ALL}")
        return False

# Функция для отправки писем
def send_emails():
    emails = load_config()

    if not emails:
        print(f"{Fore.RED}Ошибка: Почты не настроены.{Style.RESET_ALL}")
        return

    # Проверка авторизации для каждой почты
    valid_emails = []
    for email_data in emails:
        if not isinstance(email_data, dict):  # Проверяем, что это словарь
            print(f"{Fore.RED}Ошибка: Некорректные данные для почты.{Style.RESET_ALL}")
            continue

        email = email_data.get("email")
        password = email_data.get("password")

        if not email or not password:
            print(f"{Fore.RED}Ошибка: Некорректные данные для почты.{Style.RESET_ALL}")
            continue

        if check_email_auth(email, password):
            email_data["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            valid_emails.append(email_data)
        else:
            print(f"{Fore.RED}Почта {email} не прошла проверку авторизации.{Style.RESET_ALL}")

    if not valid_emails:
        print(f"{Fore.RED}Ошибка: Нет действительных почт для отправки.{Style.RESET_ALL}")
        return

    # Сохранение обновленных данных
    save_config(emails)

    print(f"{Fore.GREEN}Доступные почты для отправки:{Style.RESET_ALL}")
    for email_data in valid_emails:
        email = email_data["email"]
        last_checked = email_data["last_checked"]
        print(f"{Fore.CYAN}- {email} (последняя проверка: {last_checked}){Style.RESET_ALL}")

    print(f"{Fore.CYAN}Введите почту получателя: {Style.RESET_ALL}", end="")
    receiver_email = input()
    if not is_valid_email(receiver_email):
        print(f"{Fore.RED}Ошибка: Некорректный формат почты получателя.{Style.RESET_ALL}")
        return

    print(f"{Fore.CYAN}Введите тему письма: {Style.RESET_ALL}", end="")
    subject = input()

    print(f"{Fore.CYAN}Введите текст письма: {Style.RESET_ALL}", end="")
    body = input()

    try:
        print(f"{Fore.CYAN}Введите количество писем для отправки: {Style.RESET_ALL}", end="")
        num_emails = int(input())
    except ValueError:
        print(f"{Fore.RED}Ошибка: Введите целое число.{Style.RESET_ALL}")
        return

    # Отправка писем
    for i in range(num_emails):
        email_data = valid_emails[i % len(valid_emails)]  # Циклический выбор почты
        email = email_data["email"]
        password = email_data["password"]

        print(f"{Fore.YELLOW}Отправка письма {i + 1} из {num_emails} с почты {email}...{Style.RESET_ALL}")
        try:
            # Настройки SMTP-сервера Gmail
            smtp_server = "smtp.gmail.com"
            smtp_port = 587

            # Создание письма с поддержкой UTF-8
            message = MIMEMultipart()
            message["From"] = email
            message["To"] = receiver_email
            message["Subject"] = Header(subject, "utf-8")  # Указываем кодировку для темы
            message.attach(MIMEText(body, "plain", "utf-8"))  # Указываем кодировку для тела письма

            # Подключение к SMTP-серверу и отправка письма
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # Включаем шифрование TLS
                server.login(email, password)  # Авторизация
                server.sendmail(email, receiver_email, message.as_string())  # Отправка
            print(f"{Fore.GREEN}Письмо успешно отправлено с почты {email}!{Style.RESET_ALL}")
        except Exception as e:
            logging.error(f"Ошибка при отправке письма с почты {email}: {e}")
            print(f"{Fore.RED}Ошибка при отправке письма с почты {email}: {e}{Style.RESET_ALL}")
        time.sleep(2)  # Пауза между отправками

    print(f"{Fore.GREEN}Все письма успешно отправлены!{Style.RESET_ALL}")
    time.sleep(2)
    clear_screen()

# Функция для очистки экрана
def clear_screen():
    # Очистка экрана в зависимости от ОС
    os.system('cls' if os.name == 'nt' else 'clear')

# Основная функция
def main():
    while True:
        # Отображение компактной вывески
        display_logo()

        # Меню выбора
        print(f"{Fore.YELLOW}1. Авторизовать почты")
        print(f"{Fore.YELLOW}2. Перейти к отправке писем на снос/донос")
        print(f"{Fore.YELLOW}3. Выйти")
        choice = input(f"{Fore.CYAN}Выберите пункт меню: {Style.RESET_ALL}")

        if choice == "1":
            authorize_emails()
        elif choice == "2":
            send_emails()
        elif choice == "3":
            print(f"{Fore.GREEN}Выход из программы...{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Неверный выбор. Попробуйте снова.{Style.RESET_ALL}")
            time.sleep(1)
            clear_screen()

# Запуск программы
if __name__ == "__main__":
    main()