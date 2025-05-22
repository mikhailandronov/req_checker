from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai_tools import SerperDevTool #, DOCXSearchTool

@CrewBase
class ReqChecker():

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def req_methodologist(self) -> Agent:
        search_tool = SerperDevTool()
        return Agent(
            config=self.agents_config['req_methodologist'], # type: ignore[index]
            verbose=True,
            tools=[search_tool]
        )
    

    @task
    def req_methodology_task(self) -> Task:
        return Task(
            config=self.tasks_config['req_methodology_task'], # type: ignore[index]
        )
    

    def req_expert(self, aspect_questions) -> Agent:
        search_tool = SerperDevTool()
     
        return Agent (
            role="Главный эксперт по аспекту '{aspect}' требований к информационным системам".format(**aspect_questions),
            goal="""Уточнить и дополнить список вопросов по аспекту '{aspect}' требований к информационным системам.
Определить все ключевые вопросы по аспекту '{aspect}', ответы на которые обязательно должны быть включены в качественную 
спецификацию требований (техническое задание (ТЗ, SOW), запрос предложений (RFP)) 
для выбора поставщика (исполнителя работ) на разработку информационной системы.""".format(**aspect_questions),
            backstory="""Ты опытный эксперт, много лет отвечающий за спецификацию требований по аспекту '{aspect}'. 
Ты в деталях знаешь как общие стандарты, такие как ISO/IEC/IEEE 29148, 
ГОСТ Р ИСО/МЭК/IEEE 29148-2014, ГОСТ 34, так и специализированные стандарты, нормы, правила и лучшие практики 
по аспекту '{aspect}'. 
Ты известен тем, что можешь обеспечить полноту требований и точность формулировок. 
Ты можешь дать исчерпывающий список вопросов, определяющих то, какие требования должны быть указаны, чтобы 
гарантированно выбрать наилучшее предложение среди потенциальных подрядчиков. """.format(**aspect_questions),
            verbose=True,
            tools=[search_tool]
        )
    

    
    def req_details_task(self, aspect_questions, agent) -> Task:
        # return Task(
        #     config=self.tasks_config['req_details_task'], # type: ignore[index]
        # )
        desc = ("Сформировать ИСЧЕРПЫВАЮЩИИЙ список вопросов по аспекту '{aspect}' требований к информационной системе для "
        "проведения конкурсной процедуры выбора поставщика (исполнителя всех работ по разработке этой системы). "
        "Для этого можно взять за основу вопросы, предложенные коллегами: {questions}. Подумай, насколько они важны и конкретны."
        "Важно проверить их корректность, дополнить, уточнить, детализировать, опираясь на свою экспертизу в аспекте '{aspect}'. "
        "Итоговый список должен содержать ВСЕ вопросы по этому аспекту, на которые надо ответить в документе с требованиями, "
        "чтобы гарантированно выбрать наилучшее предложение среди потенциальных подрядчиков. "
        "При необходимости можно поискать информацию в интернете, но важно критически оценить результаты поиска."
        "Если вопрос не является критичным для отбора поставщика, еге не нужно указывать."
        "Вернуть результат ИСКЛЮЧИТЕЛЬНО в виде Python словаря с элементами 'aspect' и 'questions'. "
        "Никаких других слов или символов, кроме словаря Python, в ответе быть не должно! "
        "Например: "
        "{{'aspect':'{aspect}', "
        "'questions':['Какой протокол используется для интеграции систем?', "
        "'Какая сторона является инициатором взаимодействия?', "
        "'Как защищаются поток данных при передаче?'"
        "]}}")
        
        print ("desc ||| ", desc.format(**aspect_questions))

        eo = ("Python словарь с элементами 'aspect' и 'questions', где 'questions' - это словарь строк с вопросами. "
        "Никаких других слов или символов, кроме словаря Python, в ответе быть не должно! "
        "Пример: "
        "{{'aspect':'{aspect}', "
        "'questions':['Какой протокол используется для интеграции систем?', "
        "'Какая сторона является инициатором взаимодействия?', "
        "'Как защищаются поток данных при передаче?'"
        "]}}")

        print ("eo ||| ", eo.format(**aspect_questions))

        return Task(
            description=desc.format(**aspect_questions),
            expected_output=eo.format(**aspect_questions),
            agent=agent
            )
        

    def req_checklist_builder(self) -> Agent:
        return Agent(
            role="Главный составитель сводных чек-листов",
            goal="""Собрать воедино все Python словари, полученные от экспертов по каждому из аспектов требований, какие есть в контексте,
                и составить из них единый, полный итоговый список аспектов с вопросами - чек-лист.
                """,
            backstory=(
                "Вы мастерски объединяете полученные от экспертов блоки в один большой список."
                " Вы никогда не меняете и не теряете полученные элементы при объединении их в список."
            ),
            verbose=True
        )
    
    def req_checklist_build_task(self, expert_tasks) -> Task:
        return Task(
            description=(
                """Собрать воедино все Python словари, полученные от экспертов по каждому из аспектов требований, какие есть в контексте,
и составить из них единый, полный итоговый список аспектов с вопросами - чек-лист. Если есть орфорграфические ошибки или опечатки, их нужно исправить.
Вернуть результат ИСКЛЮЧИТЕЛЬНО в виде Python списка, содержащего словари с элементами 'aspect' и 'questions'.
Никаких других слов или символов, кроме списка Python, в ответе быть не должно! 
В результат должны попасть ВСЕ полученные от экспертов по аспектам словари. Ничего не должно пропасть! 
Например:
[
{'aspect':'Требования к интеграции', 'questions':['С какими системами интегрируется?','Какие данные передаются?', 'Какой протокол используется?']},
{'aspect':'Требования к плану работ', 'questions':['Каковы этапы проекта?', 'Каковы результаты каждого этапа?']},
{'aspect':'Требования к приемке и оплате', 'questions':['Как осуществляется приемка?','Каковы критерии выполнения работы?','Какие документы подтверждают выполнение работ и приемку?', 'Когда производится оплата?']}
]
"""
            ),
            expected_output=(
                """Python список, содержащий словари с элементами 'aspect' и 'questions'.
                Никаких других слов или символов, кроме списка Python, в ответе быть не должно! 
                В результат должны попасть ВСЕ полученные от экспертов по аспектам словари. Ничего не должно пропасть!
                Например:
                [
                {'aspect':'Требования к интеграции', 'questions':['С какими системами интегрируется?','Какие данные передаются?', 'Какой протокол используется?']},
                {'aspect':'Требования к плану работ', 'questions':['Каковы этапы проекта?', 'Каковы результаты каждого этапа?']},
                {'aspect':'Требования к приемке и оплате', 'questions':['Как осуществляется приемка?','Каковы критерии выполнения работы?','Какие документы подтверждают выполнение работ и приемку?', 'Когда производится оплата?']}
                ]"""
            ),
            agent=self.req_checklist_builder(),
            context=expert_tasks 
        )

    @crew
    def methodology_crew(self) -> Crew:
        return Crew(
            agents=[self.req_methodologist()], 
            tasks=[self.req_methodology_task()],
            process=Process.sequential,
            verbose=True
        )


    
    def req_details_crew(self, aspects) -> Crew:
        
        req_experts = []
        expert_tasks = []
        
        for aspect_desc in aspects:
            print (">>>>> ",aspect_desc)
            expert = self.req_expert(aspect_questions=aspect_desc)
            req_experts.append(expert)
            print (">> эксперт создан > ")
            task = self.req_details_task(aspect_questions=aspect_desc, agent=expert)
            expert_tasks.append(task)
            print (">> таск создан > ")

        return Crew(
            agents=req_experts + [self.req_checklist_builder()], 
            tasks=expert_tasks + [self.req_checklist_build_task(expert_tasks=expert_tasks)],
            process=Process.sequential,
            verbose=True
        )
    
    # def rag_expert(self, rag_tool, question) -> Agent:
    #     return Agent (
    #         role="Главный эксперт по поиску ответов на вопросы в контексте запроса",
    #         goal="Найти в тексте запроса ответ на вопрос '{}', используя все доступные инструменты. ".format(question),
    #         backstory="Ты опытный специалист по поиску ответов в тексте. Ты известен тем, что умеешь использовать инструменты для поиска в DOCX. ",
    #         verbose=True,
    #         tools=[rag_tool]
    #     )
    

    
    # def rag_task(self, aspect_questions, agent) -> Task:
    #     # return Task(
    #     #     config=self.tasks_config['req_details_task'], # type: ignore[index]
    #     # )
    #     desc = "Найти ответ на вопрос, используя доступные инструменты и информацию в запросе. Если ответа нет, надо вернуть строку 'Нет ответа'"
        
    #     eo = "Python словарь с элементами 'aspect' и 'questions', где 'questions' - это словарь строк с вопросами. "
    #     "Никаких других слов или символов, кроме словаря Python, в ответе быть не должно! "
    #     "Пример: "
    #     "{'aspect':'{aspect}', "
    #     "'questions':['Какой протокол используется для интеграции систем?', "
    #     "'Какая сторона является инициатором взаимодействия?', "
    #     "'Как защищаются поток данных при передаче?'"
    #     "]}"

    #     return Task(
    #         description=desc.format(**aspect_questions),
    #         expected_output=eo.format(**aspect_questions),
    #         agent=agent
    #         )


    # def rag_crew(self, filepath, questions) -> Crew:
        
    #     rag_tool = DOCXSearchTool(filepath)
    #     rag_experts = []
    #     expert_tasks = []
        
    #     for question in questions:
    #         print (">>>>> ",question)
    #         expert = self.req_expert(aspect_questions=aspect_desc)
    #         req_experts.append(expert)
    #         print (">> эксперт создан > ")
    #         task = self.req_details_task(aspect_questions=aspect_desc, agent=expert)
    #         expert_tasks.append(task)
    #         print (">> таск создан > ")

    #     return Crew(
    #         agents=req_experts + [self.req_checklist_builder()], 
    #         tasks=expert_tasks + [self.req_checklist_build_task(expert_tasks=expert_tasks)],
    #         process=Process.sequential,
    #         verbose=True,
    #         # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
    #     )
