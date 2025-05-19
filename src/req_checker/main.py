#!/usr/bin/env python
import sys
import warnings
import ast

from datetime import datetime
import typing as tp

from req_checker.crew import ReqChecker

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def get_aspects(aspect_questions_string: str) -> list[dict[str, tp.Any]]:
    
    aspects_list = [{}]
    try:
        aspects_list = ast.literal_eval(aspect_questions_string.strip())
        if not isinstance(aspects_list, list) or not all(isinstance(aspect, dict) for aspect in aspects_list):
            raise ValueError("Результат методолога не является списком словарей.")
    except (ValueError, SyntaxError) as e:
        print(f"⚠️ Ошибка парсинга списка аспектов: {e}. Пожалуйста, проверьте вывод методолога.")
        print("Используем запасной список аспектов для демонстрации.")
        aspects_list = [
            {
                'aspect': 'Требования к функциональности системы',
                'questions': [
                    'Какие основные функции должна выполнять система?',
                    'Какие бизнес-процессы автоматизирует система?',
                    'Какие пользовательские роли и права должны быть реализованы?',
                    'Должна ли система обладать возможностью масштабирования и расширения функциональности?',
                    'Какие интеграции с другими системами обязательны?'
                ]
            },
            {
                'aspect': 'Требования к безопасности и защите данных',
                'questions': [
                    'Какие требования к хранению и передаче персональных данных?',
                    'Какие меры защиты информации должны быть реализованы (шифрование, аутентификация, аудит)?',
                    'Соответствует ли система нормативам по информационной безопасности (ФЗ 152, ГОСТ Р ИСО/МЭК/IEEE 27001)?',
                    'Какие механизмы обнаружения и предотвращения несанкционированного доступа предусмотрены?',
                    'Как реализована защита от внешних и внутренних угроз?'
                ]
            },
            {
                'aspect': 'Требования к интерфейсу и пользовательскому опыту',
                'questions': [
                    'Какие требования предъявляются к удобству и интуитивности интерфейса?',
                    'Должна ли система поддерживать мобильные устройства и разные платформы?',
                    'Какие языковые настройки должны быть реализованы?',
                    'Какие требования к доступности для людей с ограниченными возможностями?',
                    'Должны ли реализовываться функции обучения и поддержки пользователей?'
                ]
            }
        ]
    
    return aspects_list

# def run_process():
#     """
#     Run the crew.
#     """

#     filepath = "uploaded_files/FTT.docx" 
#     questions = ['В чем цель проекта', 'Какая должность у Белинской']

#     result = "Не удалось получить результат"

#     try:
#         result = ReqChecker().rag_crew(filepath=filepath, questions=questions).kickoff().raw
#     except Exception as e:
#         raise Exception(f"An error occurred while running the crew: {e}")
    
#     print(result)

def run():
    """
    Run the crew.
    """

    result = "Не удалось получить результат"

    try:
        result = ReqChecker().methodology_crew().kickoff().raw
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")
    
    aspects = get_aspects(result)

    try:
        result = ReqChecker().req_details_crew(aspects= aspects).kickoff().raw
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

    print("Вопросы:\n", result)
    aspects = get_aspects(result)
    print("Итог:\n", aspects)
    


def run_in_streamlit(topic:str, current_year:int) -> str:
    """
    Run the crew from Streamlit app
    """
    inputs = {
        'topic': topic,
        'current_year': str(current_year)
    }
    
    result = "Не удалось сгенерировать отчет"

    try:
        result = ReqChecker().crew().kickoff(inputs=inputs).raw
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")
    
    return result


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year)
    }
    try:
        ReqChecker().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        ReqChecker().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }
    
    try:
        ReqChecker().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")
