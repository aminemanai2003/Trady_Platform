from django.urls import path
from . import views

urlpatterns = [
    path("agents/status/", views.agent_status, name="agent-status"),
    path("agents/run/", views.run_agents, name="run-agents"),
]
