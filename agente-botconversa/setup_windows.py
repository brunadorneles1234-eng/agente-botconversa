"""
Setup inicial do Agente Botconversa para Windows.
Execute este arquivo UMA VEZ para configurar o agendador automático.

Como usar:
  1. Abra o PowerShell como Administrador
  2. Navegue até a pasta do projeto
  3. Execute: python setup_windows.py
"""
import os
import subprocess
import sys


def main():
    python_path = sys.executable
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "run.py"))
    task_name = "AgenteBotconversa"

    print("=" * 50)
    print("Setup do Agente Botconversa")
    print("=" * 50)

    # Verifica dependências
    print("\n[1/3] Verificando dependências...")
    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    result = subprocess.run(
        [python_path, "-m", "pip", "install", "-r", req_file],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("  AVISO: Erro ao instalar dependências via pip.")
        print("  Se estiver usando uv, execute manualmente:")
        print(f"  uv pip install -r {req_file}")
    else:
        print("  Dependências OK")

    # Cria pastas necessárias
    print("\n[2/3] Criando pastas...")
    base = os.path.dirname(__file__)
    for folder in ["dados", "relatorios", "logs"]:
        path = os.path.join(base, folder)
        os.makedirs(path, exist_ok=True)
        print(f"  {path}")

    # Registra no Task Scheduler
    print("\n[3/3] Registrando tarefa no Windows (executa às 06:00)...")
    cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", f'"{python_path}" "{script_path}"',
        "/sc", "DAILY",
        "/st", "06:00",
        "/f",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  Tarefa '{task_name}' criada com sucesso!")
        print("  O agente vai rodar todo dia às 06:00 automaticamente.")
    else:
        print("  AVISO: Não foi possível criar a tarefa automaticamente.")
        print("  Por favor, crie manualmente no Agendador de Tarefas do Windows:")
        print(f"    Programa: {python_path}")
        print(f"    Argumentos: {script_path}")
        print("    Horário: 06:00 diariamente")

    print("\n" + "=" * 50)
    print("Setup concluído!")
    print(f"Para testar agora: python {script_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()
