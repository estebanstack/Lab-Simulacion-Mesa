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
        print(f"Servidor {self.unique_id} comenzando servicio a tarea {task.unique_id}")

    def complete_service(self):
        """Finalizar el servicio de la tarea actual."""
        print(f"Servidor {self.unique_id} completó el servicio de tarea {self.current_task.unique_id}")
        self.busy = False
        self.total_service_time += self.current_task.initial_service_time
        self.current_task = None


# Definición del agente Tarea
class TaskAgent(Agent):
    def __init__(self, unique_id, model, service_time):
        super().__init__(unique_id, model)
        self.initial_service_time = service_time
        self.remaining_service_time = service_time  # Tiempo de servicio que aún queda
        self.assigned_server = None  # Servidor asignado (al que está esperando)

    def step(self):
        """Tareas no hacen nada activamente, esperan ser atendidas por un servidor."""
        pass


# Modelo del sistema de colas
class QueueServerModel(Model):
    def __init__(self, num_servers, task_arrival_rate, max_steps):
        self.num_servers = num_servers
        self.task_arrival_rate = task_arrival_rate  # Tasa de llegada de tareas
        self.max_steps = max_steps
        self.schedule = RandomActivation(self)
        self.running = True
        self.current_step = 0

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
            service_time = random.randint(2, 10)  # Tiempo de servicio aleatorio
            new_task = TaskAgent(self.current_step, self, service_time)
            self.schedule.add(new_task)

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

# Ejemplo de uso
if __name__ == "__main__":
    num_servers = 3  # Número de servidores
    task_arrival_rate = 0.7  # Tasa de llegada de tareas
    max_steps = 100  # Número máximo de pasos

    model = QueueServerModel(num_servers, task_arrival_rate, max_steps)

    while model.running:
        model.step()

    # Mostrar algunas estadísticas al final
    print("Longitudes finales de las colas por servidor:", model.get_queue_lengths())
    print("Número de servidores ocupados al final:", model.get_busy_servers())
