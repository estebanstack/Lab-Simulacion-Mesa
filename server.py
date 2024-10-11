from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import random


# Definición del agente Servidor
class ServerAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.busy = False  # Estado inicial del servidor
        self.current_task = None  # Tarea que está sirviendo
        self.total_service_time = 0  # Tiempo total que ha servido
        self.queue = []  # Cola de tareas en espera
        self.total_tasks_served = 0  # Contador de tareas completadas

    def step(self):
        if self.busy and self.current_task:  # Si está ocupado, sigue sirviendo la tarea
            self.current_task.remaining_service_time -= 1
            if self.current_task.remaining_service_time <= 0:
                self.complete_service()  # Completa el servicio si el tiempo ha llegado a 0

        if not self.busy and len(self.queue) > 0:  # Si no está ocupado, comienza una nueva tarea de la cola
            self.begin_service(self.queue.pop(0))

    def begin_service(self, task):
        """Comenzar el servicio de una nueva tarea."""
        self.busy = True
        self.current_task = task
        task.assigned_server = self
        task.queue_wait_time = self.model.current_step - task.arrival_time  # Tiempo que esperó en la cola
        print(f"Servidor {self.unique_id} comenzando servicio a tarea {task.unique_id}")

    def complete_service(self):
        """Finalizar el servicio de la tarea actual."""
        print(f"Servidor {self.unique_id} completó el servicio de tarea {self.current_task.unique_id}")
        self.busy = False
        self.total_service_time += self.current_task.initial_service_time
        self.total_tasks_served += 1
        self.current_task = None


# Definición del agente Tarea
class TaskAgent(Agent):
    def __init__(self, unique_id, model, service_time):
        super().__init__(unique_id, model)
        self.initial_service_time = service_time
        self.remaining_service_time = service_time  # Tiempo de servicio que aún queda
        self.assigned_server = None  # Servidor asignado (al que está esperando)
        self.arrival_time = model.current_step  # Tiempo en el que la tarea llegó al sistema
        self.queue_wait_time = 0  # Tiempo que la tarea pasó en cola

    def step(self):
        """Tareas no hacen nada activamente, esperan ser atendidas por un servidor."""
        pass


# Modelo del sistema de colas
class QueueServerModel(Model):
    def __init__(self, num_servers, task_arrival_rate, task_service_rate, max_steps):
        self.num_servers = num_servers
        self.task_arrival_rate = task_arrival_rate  # Tasa de llegada de tareas
        self.task_service_rate = task_service_rate  # Tasa de servicio de las tareas
        self.max_steps = max_steps
        self.schedule = RandomActivation(self)
        self.running = True
        self.current_step = 0

        # Variables para estadísticas
        self.total_queue_wait_time = 0
        self.total_time_in_system = 0
        self.total_tasks = 0

        # Crear servidores (agents)
        self.servers = []
        for i in range(self.num_servers):
            server = ServerAgent(i, self)
            self.schedule.add(server)
            self.servers.append(server)

        # Colector de datos para estadísticas
        self.datacollector = DataCollector(
            agent_reporters={"Busy": "busy", "Queue Size": lambda a: len(a.queue) if isinstance(a, ServerAgent) else 0}
        )

    def step(self):
        """Avanza el modelo un paso."""
        # Crear nuevas tareas de acuerdo con la tasa de llegada
        if random.random() < self.task_arrival_rate:
            service_time = int(random.expovariate(self.task_service_rate))  # Tiempo de servicio basado en la tasa
            new_task = TaskAgent(self.current_step, self, service_time)
            self.schedule.add(new_task)
            self.total_tasks += 1  # Incrementar el total de tareas

            # Asignar tarea a un servidor disponible
            available_server = self.find_available_server()
            if available_server:
                available_server.begin_service(new_task)
            else:
                # Si no hay servidor disponible, agregar la tarea a la cola del servidor con la cola más corta
                server_with_shortest_queue = min(self.servers, key=lambda s: len(s.queue))
                server_with_shortest_queue.queue.append(new_task)

        # Ejecutar un paso de todos los agentes
        self.schedule.step()
        self.datacollector.collect(self)

        # Actualizar el tiempo en el sistema y el tiempo en cola para las tareas completadas
        for agent in self.schedule.agents:
            if isinstance(agent, TaskAgent) and agent.assigned_server is not None:
                self.total_queue_wait_time += agent.queue_wait_time
                self.total_time_in_system += (self.current_step - agent.arrival_time)

        self.current_step += 1
        if self.current_step >= self.max_steps:
            self.running = False  # Terminar simulación

    def find_available_server(self):
        """Encuentra un servidor que no esté ocupado."""
        for server in self.servers:
            if not server.busy:
                return server
        return None

    def get_queue_lengths(self):
        """Devuelve las longitudes de las colas de los servidores."""
        return [len(server.queue) for server in self.servers]

    def get_busy_servers(self):
        """Devuelve el número de servidores ocupados."""
        return sum(1 for server in self.servers if server.busy)

    def get_avg_queue_length(self):
        """Calcula el largo promedio de las colas."""
        total_queue_length = sum(len(server.queue) for server in self.servers)
        return total_queue_length / self.num_servers

    def get_avg_servers_busy(self):
        """Calcula el promedio de servidores ocupados."""
        busy_servers = self.get_busy_servers()
        return busy_servers / self.num_servers

    def get_avg_time_in_queue(self):
        """Calcula el tiempo promedio en la cola."""
        if self.total_tasks > 0:
            return self.total_queue_wait_time / self.total_tasks
        return 0

    def get_avg_time_in_system(self):
        """Calcula el tiempo promedio en el sistema."""
        if self.total_tasks > 0:
            return self.total_time_in_system / self.total_tasks
        return 0


# Ejemplo de uso
if __name__ == "__main__":
    num_servers = 3  # Número de servidores
    task_arrival_rate = 0.9  # Tasa de llegada de tareas
    task_service_rate = 0.4  # Tasa de servicio de tareas (inverso del tiempo promedio)
    max_steps = 100  # Número máximo de pasos

    model = QueueServerModel(num_servers, task_arrival_rate, task_service_rate, max_steps)

    while model.running:
        model.step()

    # Mostrar algunas estadísticas al final
    print("Longitudes finales de las colas por servidor:", model.get_queue_lengths())
    print("Número de servidores ocupados al final:", model.get_busy_servers())

    # Imprimir las estadísticas adicionales
    print("Estadísticas de la simulación:")
    print(f"Promedio de tiempo en cola: {model.get_avg_time_in_queue():.2f}")
    print(f"Promedio de tiempo en el sistema: {model.get_avg_time_in_system():.2f}")
    print(f"Promedio de longitud de la cola: {model.get_avg_queue_length():.2f}")
    print(f"Promedio de servidores ocupados: {model.get_avg_servers_busy():.2f}")
