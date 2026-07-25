from typing import Dict

PRACTITIONER_PAGES = {"Documentation", "Reflection Space", "My Reflection"}
MANAGER_PAGES = {"Learning", "Case History", "Research Metrics"}


def can_access_workspace(role, workspace):
    if role == "Social Worker":
        return workspace == "Practitioner"
    if role in {"Supervisor", "Programme Manager"}:
        return workspace in {"Manager", "Practitioner"}
    if role == "System Administrator":
        return workspace in {"System Administration", "Manager", "Practitioner"}
    return False


def available_workspaces(role):
    return [w for w in ["Practitioner", "Manager", "System Administration"] if can_access_workspace(role, w)]
