import base64
import ctypes
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import webbrowser
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.parse import quote

import pyperclip


APP_TITLE = "Assistente Jurídico Exclusive : Thays Marcela"
AUTO_SEND_DELAY_MS = 4500


def decode_text(encoded_text: str) -> str:
    return base64.b64decode(encoded_text.encode("ascii")).decode("utf-8")


AUTHOR_NAME = decode_text("THVjYXMgU29hcmVz")
AUTHOR_URL = decode_text("aHR0cHM6Ly9naXRodWIuY29tL09sdWthc2FvLw==")

APP_FOLDER_NAME = "Assistente-Juridico"
BUNDLED_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def get_data_dir() -> Path:
    if getattr(sys, "frozen", False) and platform.system() == "Darwin":
        return Path.home() / "Documents" / APP_FOLDER_NAME
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = get_data_dir()
PROMPTS_DIR = BASE_DIR / "prompts"
REPORTS_DIR = BASE_DIR / "relatorios"
DEFAULT_EXTERNAL_REPORTS_DIR = (
    Path("C:/Assistente-Juridico/relatorios")
    if platform.system() == "Windows"
    else Path.home() / "Documents" / APP_FOLDER_NAME / "relatorios"
)
REPORTS_OUTPUT_HINT = str(DEFAULT_EXTERNAL_REPORTS_DIR)
CONFIG_DIR = BASE_DIR / "configuracoes"
BACKUPS_DIR = BASE_DIR / "backups"
CONFIG_FILE = CONFIG_DIR / "config.json"
MONITOR_CONFIG_FILE = CONFIG_DIR / "monitoramento.json"
SNAPSHOT_FILE = CONFIG_DIR / "snapshot_pendencias.json"


DEFAULT_CONFIG = {
    "selected_claude_target": "",
    "selected_claude_path": "",
    "claude_paths": [
        "C:/Users/{USERNAME}/AppData/Local/Programs/Claude/Claude.exe",
        "C:/Users/{USERNAME}/AppData/Local/Claude/Claude.exe",
        "C:/Users/{USERNAME}/AppData/Local/AnthropicClaude/Claude.exe",
        "C:/Users/{USERNAME}/AppData/Local/Programs/Cowork/Cowork.exe",
        "C:/Users/{USERNAME}/AppData/Local/Cowork/Cowork.exe",
        "C:/Program Files/Claude/Claude.exe",
        "C:/Program Files/Cowork/Cowork.exe",
        "C:/Program Files (x86)/Claude/Claude.exe",
        "C:/Program Files (x86)/Cowork/Cowork.exe",
        "/Applications/Claude.app",
        "/Applications/Cowork.app",
        "{HOME}/Applications/Claude.app",
        "{HOME}/Applications/Cowork.app",
    ],
    "auto_open_claude": True,
    "auto_send_prompt": False,
    "modo_abertura": "cowork",
    "incluir_login_manual": False,
    "astrea_login_url": "",
    "astrea_usuario": "",
    "astrea_senha": "",
    "jusbrasil_login_url": "",
    "jusbrasil_usuario": "",
    "jusbrasil_senha": "",
    "reports_folder": REPORTS_OUTPUT_HINT,
}


DEFAULT_MONITOR_CONFIG = {
    "monitoramento_ativo": False,
    "intervalo_horas": 1,
    "ultima_verificacao": None,
    "proxima_verificacao": None,
    "base_inicial_criada": False,
    "arquivo_snapshot": "configuracoes/snapshot_pendencias.json",
}


DEFAULT_SNAPSHOT = {
    "criado_em": None,
    "ultima_atualizacao": None,
    "itens_conhecidos": [],
}


DEFAULT_PROMPTS = {
    "rotina-completa.txt": f"""Execute a tarefa: Rotina Jurídica — Astrea + Jusbrasil + Peças + Excel.

Acesse primeiro o Astrea para verificar prazos, tarefas, publicações, intimações, processos, responsáveis internos e pendências. Use os prazos do Astrea como referência principal quando existirem.

Depois acesse o Jusbrasil para complementar ou confirmar publicações, intimações, movimentações e processos.

Se for solicitada elaboração de peça jurídica, auxilie na criação de minuta nas áreas previdenciária, trabalhista ou cível, sempre verificando o prazo da tarefa específica, usando apenas fatos e documentos disponíveis, legislação vigente brasileira e sem inventar fatos, provas, prazos, jurisprudência ou fundamentos.

Ao final, gere relatório na conversa e planilha Excel .xlsx organizada por prioridade na pasta {REPORTS_OUTPUT_HINT}.

Toda informação deve ser tratada como apoio operacional e precisa de validação humana da advogada.""",
    "astrea.txt": """Execute a rotina Astrea.

Acesse o Astrea, aguarde login manual se necessário e verifique prazos, tarefas pendentes, tarefas vencidas, publicações, intimações, processos, responsáveis internos, status, datas de vencimento e observações.

Use os prazos do Astrea como referência principal. Não invente prazos processuais. Quando não houver prazo claro, marque como 'prazo não localizado' e sugira prazo interno de até 4 dias corridos para análise humana, deixando claro que não é prazo processual.

Não altere tarefas, processos ou cadastros sem autorização expressa. Gere relatório final e, se possível, planilha Excel.""",
    "jusbrasil.txt": """Execute a rotina Jusbrasil.

Acesse o Jusbrasil, aguarde login manual se necessário e consulte publicações, intimações, movimentações e processos usando os dados fornecidos pela advogada: nome da parte, CPF/CNPJ, número do processo, advogado, tribunal, comarca ou palavra-chave.

Registre processo, tribunal, data, publicação, movimentação, prazo encontrado, link/fonte e resumo. Não invente prazos processuais. Quando houver prazo claro, copie exatamente o prazo encontrado. Quando não houver, marque como 'prazo não localizado'.

Toda publicação, intimação ou prazo deve ser marcada como 'necessita validação humana'.""",
    "peca-previdenciaria.txt": """Elaborar minuta de peça previdenciária.

Antes de redigir, verificar o prazo da tarefa no Astrea, Jusbrasil, publicação, intimação ou documento enviado. Identificar tipo de peça, processo, cliente, parte contrária, fase processual, benefício envolvido, documentos disponíveis, provas e pontos controvertidos.

Usar apenas informações fornecidas ou localizadas. Não inventar fatos, documentos, provas, prazos, jurisprudência ou fundamentos. Fundamentar com legislação vigente brasileira aplicável ao Direito Previdenciário.

A peça deve ser entregue como minuta para revisão da advogada, com resumo da tarefa, prazo encontrado, fonte do prazo, riscos, pontos de validação e checklist de documentos.""",
    "peca-trabalhista.txt": """Elaborar minuta de peça trabalhista.

Antes de redigir, verificar o prazo da tarefa no Astrea, Jusbrasil, publicação, intimação ou documento enviado. Identificar tipo de peça, processo, cliente, parte contrária, fase processual, vínculo, verbas, jornada, documentos, provas e pontos controvertidos.

Usar apenas informações fornecidas ou localizadas. Não inventar fatos, documentos, provas, prazos, jurisprudência ou fundamentos. Fundamentar com legislação vigente brasileira aplicável ao Direito Trabalhista.

A peça deve ser entregue como minuta para revisão da advogada, com resumo da tarefa, prazo encontrado, fonte do prazo, riscos, pontos de validação e checklist de documentos.""",
    "peca-civel.txt": """Elaborar minuta de peça cível.

Antes de redigir, verificar o prazo da tarefa no Astrea, Jusbrasil, publicação, intimação ou documento enviado. Identificar tipo de peça, processo, cliente, parte contrária, fase processual, relação jurídica, documentos disponíveis, provas, pedidos e pontos controvertidos.

Usar apenas informações fornecidas ou localizadas. Não inventar fatos, documentos, provas, prazos, jurisprudência ou fundamentos. Fundamentar com legislação vigente brasileira aplicável ao Direito Cível.

A peça deve ser entregue como minuta para revisão da advogada, com resumo da tarefa, prazo encontrado, fonte do prazo, riscos, pontos de validação e checklist de documentos.""",
    "criar-base-monitoramento.txt": """Criar ou refazer base inicial de monitoramento jurídico.

Acesse primeiro o Astrea e depois o Jusbrasil, aguardando login manual se necessário.

Objetivo:
Mapear as pendências, tarefas, publicações, intimações, movimentações e prazos atualmente existentes, apenas para criar uma base inicial de comparação.

Importante:
Esta execução serve para criar a base inicial. Não trate os itens encontrados como novas pendências. Eles são apenas o estado atual do sistema.

Verifique no Astrea:

* Prazos cadastrados;
* Tarefas pendentes;
* Tarefas vencidas;
* Publicações;
* Intimações;
* Processos;
* Responsáveis;
* Status;
* Datas de vencimento;
* Observações relevantes.

Verifique no Jusbrasil:

* Publicações;
* Intimações;
* Movimentações;
* Processos;
* Prazos encontrados;
* Datas;
* Tribunal;
* Link/fonte.

Para cada item localizado, monte uma base com:
id_unico | sistema_origem | cliente_parte | numero_processo | tipo | materia | data_encontrada | prazo_encontrado | resumo | link_fonte | hash_conteudo

Regras:

* Não inventar prazos.
* Não tomar decisão jurídica final.
* Não alterar nada nos sistemas.
* Não protocolar nada.
* Não salvar senhas.
* Não baixar arquivos sem autorização.
* Copiar prazos exatamente como encontrados.
* Quando não houver prazo, marcar como 'prazo não localizado'.

Ao final:

1. Informar quantos itens foram incluídos na base inicial.
2. Salvar/gerar a base em formato JSON ou tabela estruturada.
3. Informar que a partir da próxima verificação devem ser exibidas apenas novas pendências.""",
    "verificar-novas-pendencias.txt": f"""Verificar novas pendências jurídicas desde a última base registrada.

Acesse primeiro o Astrea e depois o Jusbrasil, aguardando login manual se necessário.

Objetivo:
Buscar somente novas pendências, novas tarefas, novas publicações, novas intimações, novas movimentações ou novos prazos que surgiram depois da última verificação/base inicial.

Importante:
Não listar novamente pendências antigas já conhecidas.
Não trazer tarefas antigas que já estavam na base.
Não repetir publicações, intimações ou movimentações já registradas.
Mostrar apenas o que for novo ou o que sofreu alteração relevante.

Use como referência a última base/snapshot de pendências, quando disponível:
configuracoes/snapshot_pendencias.json

Verifique no Astrea:

* Novas tarefas;
* Novos prazos;
* Novas publicações;
* Novas intimações;
* Novas movimentações;
* Alterações relevantes em tarefas existentes;
* Novas pendências vinculadas a processos.

Verifique no Jusbrasil:

* Novas publicações;
* Novas intimações;
* Novas movimentações processuais;
* Novos processos relacionados aos dados consultados;
* Novos prazos informados.

Critério de novidade:
Considere novo apenas o item que não existia na base anterior ou que teve alteração relevante desde a última verificação.

Para cada nova pendência encontrada, registrar:
Cliente/Parte | Número do Processo | Sistema de Origem | Tribunal | Tipo | Matéria | Data Encontrada | Prazo Encontrado | Fonte do Prazo | Prioridade | Status | Resumo | Link/Fonte | Observações

Prioridade:
Urgente:

* Prazo vencido;
* Prazo para hoje;
* Prazo para amanhã;
* Nova publicação ou intimação com risco de prazo;
* Nova tarefa crítica.

Alta:

* Novo prazo próximo;
* Nova movimentação relevante;
* Nova tarefa importante;
* Nova publicação/intimação que exige análise.

Média:

* Nova movimentação sem urgência aparente;
* Nova pendência de acompanhamento.

Baixa:

* Nova informação apenas consultiva ou sem ação imediata.

Regras:

* Não inventar prazos processuais.
* Não tomar decisão jurídica final.
* Não alterar nada no Astrea ou Jusbrasil.
* Não protocolar nada.
* Não salvar senhas.
* Não baixar arquivos sem autorização.
* Copiar exatamente os prazos encontrados.
* Se não houver prazo, marcar como 'prazo não localizado'.
* Tudo que envolver prazo, publicação ou intimação deve ser marcado como 'necessita validação humana'.

Se não houver novas pendências:
Responder exatamente:
'Nenhuma nova pendência localizada desde a última verificação.'

Se houver novas pendências:

1. Apresentar resumo por prioridade.
2. Gerar tabela das novidades.
3. Atualizar ou gerar nova base/snapshot incluindo os itens novos.
4. Gerar Excel .xlsx apenas com as novas pendências encontradas.
5. Salvar, se possível, em:
   {REPORTS_OUTPUT_HINT}

Nome sugerido do Excel:
Novas_Pendencias_Juridicas_DATA_HORA.xlsx""",
}


PROMPT_BUTTONS = [
    ("Rotina Completa", "rotina-completa.txt", True),
    ("Consultar Astrea", "astrea.txt", False),
    ("Consultar Jusbrasil", "jusbrasil.txt", False),
    ("Peça Previdenciária", "peca-previdenciaria.txt", False),
    ("Peça Trabalhista", "peca-trabalhista.txt", False),
    ("Peça Cível", "peca-civel.txt", False),
]


def salvar_config_monitoramento(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MONITOR_CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_project_files() -> None:
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG.copy())

    if not MONITOR_CONFIG_FILE.exists():
        salvar_config_monitoramento(DEFAULT_MONITOR_CONFIG.copy())

    if not SNAPSHOT_FILE.exists():
        SNAPSHOT_FILE.write_text(json.dumps(DEFAULT_SNAPSHOT, indent=2, ensure_ascii=False), encoding="utf-8")

    for filename, content in DEFAULT_PROMPTS.items():
        prompt_path = PROMPTS_DIR / filename
        if not prompt_path.exists():
            bundled_prompt_path = BUNDLED_DIR / "prompts" / filename
            if bundled_prompt_path.exists():
                prompt_content = bundled_prompt_path.read_text(encoding="utf-8").strip()
            else:
                prompt_content = content.strip()
            prompt_path.write_text(prompt_content + "\n", encoding="utf-8")


def load_config() -> dict:
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except (OSError, json.JSONDecodeError):
        config = DEFAULT_CONFIG.copy()
        save_config(config)
    return {**DEFAULT_CONFIG, **config}


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def carregar_config_monitoramento() -> dict:
    try:
        with MONITOR_CONFIG_FILE.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except (OSError, json.JSONDecodeError):
        config = DEFAULT_MONITOR_CONFIG.copy()
        salvar_config_monitoramento(config)
    return {**DEFAULT_MONITOR_CONFIG, **config}


def formatar_data_hora(iso_value: str | None) -> str:
    if not iso_value:
        return "Nunca"
    try:
        return datetime.fromisoformat(iso_value).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso_value


def agora_iso() -> str:
    return datetime.now().replace(second=0, microsecond=0).isoformat()


def open_path(target: str | Path) -> None:
    target_text = str(target)
    system = platform.system()
    if system == "Windows":
        os.startfile(target_text)  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", target_text])
    else:
        subprocess.Popen(["xdg-open", target_text])


def reveal_path(target: str | Path) -> None:
    path = Path(target)
    system = platform.system()
    if system == "Windows":
        subprocess.Popen(["explorer.exe", "/select,", str(path)])
    elif system == "Darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        open_path(path.parent)


def get_reports_folder() -> Path:
    config = load_config()
    configured = str(config.get("reports_folder") or "").strip()
    if platform.system() != "Windows" and re.match(r"^[A-Za-z]:[/\\]", configured):
        configured = ""
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend([DEFAULT_EXTERNAL_REPORTS_DIR, REPORTS_DIR])

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            continue

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def expand_windows_path(raw_path: str) -> Path:
    username = os.environ.get("USERNAME") or Path.home().name
    expanded = raw_path.replace("{USERNAME}", username)
    expanded = expanded.replace("{HOME}", str(Path.home()))
    expanded = os.path.expandvars(expanded)
    expanded = os.path.expanduser(expanded)
    return Path(expanded)


def remember_claude_target(target: str) -> None:
    config = load_config()
    config["selected_claude_target"] = target
    config["selected_claude_path"] = target
    save_config(config)


def selected_target_from_config(config: dict) -> str:
    return str(config.get("selected_claude_target") or config.get("selected_claude_path") or "").strip()


def common_shortcut_roots() -> list[Path]:
    if platform.system() == "Darwin":
        return [Path("/Applications"), Path.home() / "Applications"]
    if platform.system() != "Windows":
        return [Path("/usr/share/applications"), Path.home() / ".local/share/applications"]
    return [
        Path(os.environ.get("USERPROFILE", "")) / "Desktop",
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu",
        Path(os.environ.get("ProgramData", "")) / "Microsoft/Windows/Start Menu",
    ]


def find_claude_shortcut() -> str:
    for root in common_shortcut_roots():
        if not root.exists():
            continue
        try:
            for shortcut in root.rglob("*"):
                name = shortcut.name.lower()
                valid_suffixes = (".lnk", ".url") if platform.system() == "Windows" else (".app", ".desktop")
                if shortcut.suffix.lower() in valid_suffixes and ("claude" in name or "cowork" in name):
                    return str(shortcut)
        except OSError:
            continue
    return ""


def find_claude_app_id() -> str:
    if platform.system() != "Windows":
        return ""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-StartApps | Where-Object { $_.Name -match 'Claude|Cowork' } | Select-Object -First 1 -ExpandProperty AppID",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError, AttributeError):
        return ""

    app_id = result.stdout.strip().splitlines()[0].strip() if result.stdout.strip() else ""
    return f"shell:AppsFolder\\{app_id}" if app_id else ""


def find_claude_executable(config: dict) -> str:
    selected = selected_target_from_config(config)
    if selected and (selected.startswith("shell:") or Path(selected).exists()):
        return selected

    for raw_path in config.get("claude_paths", []):
        if raw_path:
            candidate = expand_windows_path(str(raw_path))
            if candidate.exists() and (candidate.is_file() or candidate.suffix.lower() == ".app"):
                return str(candidate)

    return find_claude_shortcut() or find_claude_app_id()


def launch_target(target: str) -> None:
    if target.startswith("shell:"):
        if platform.system() == "Windows":
            subprocess.Popen(["explorer.exe", target], close_fds=True)
        else:
            open_path(target)
        return

    path = Path(target)
    if path.suffix.lower() == ".exe":
        subprocess.Popen([str(path)], close_fds=True)
        return

    open_path(path)


def open_claude() -> tuple[bool, str]:
    config = load_config()
    if not config.get("auto_open_claude", True):
        return False, "Abertura automática do Claude desativada. Cole o prompt manualmente."

    target = find_claude_executable(config)
    if not target:
        return False, "Claude não encontrado automaticamente. Abra o Claude manualmente e cole o prompt copiado."

    remember_claude_target(target)
    try:
        launch_target(target)
        return True, "Claude aberto. Cole o prompt copiado para iniciar a rotina."
    except OSError as exc:
        return False, f"Não foi possível abrir o Claude/Cowork: {exc}"


def prepare_prompt_for_deeplink(prompt_text: str) -> str:
    if len(prompt_text) <= 12000:
        return prompt_text
    return (
        "Execute a rotina selecionada. O prompt completo foi copiado para a área de transferência. "
        "Cole o conteúdo completo aqui se necessário."
    )


def open_claude_deeplink(prompt_text: str) -> tuple[bool, str]:
    config = load_config()
    if not config.get("auto_open_claude", True):
        return False, "Abertura automática do Claude desativada. Cole o prompt manualmente."

    modo = config.get("modo_abertura", "cowork")
    prompt_encoded = quote(prepare_prompt_for_deeplink(prompt_text))

    if modo == "chat":
        deeplink = f"claude://claude.ai/new?q={prompt_encoded}"
        success_message = "Chat do Claude aberto com prompt preenchido."
    else:
        deeplink = f"claude://cowork/new?q={prompt_encoded}"
        success_message = "Claude Cowork aberto com prompt preenchido."

    try:
        if platform.system() == "Windows":
            os.startfile(deeplink)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", deeplink])
        else:
            subprocess.Popen(["xdg-open", deeplink])
        return True, success_message
    except Exception as exc:
        print(f"Erro ao abrir Claude via deep link: {exc}")
        return False, "Não foi possível abrir via link direto. O prompt foi copiado. Cole manualmente no Claude."


def send_enter_key() -> bool:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 36'],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            return True
        if system != "Windows":
            return False
        vk_return = 0x0D
        keyeventf_keyup = 0x0002
        ctypes.windll.user32.keybd_event(vk_return, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_return, 0, keyeventf_keyup, 0)
        return True
    except Exception as exc:
        print(f"Erro ao enviar Enter: {exc}")
        return False


def open_folder(folder: Path) -> tuple[bool, str]:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        open_path(folder)
        return True, f"Pasta aberta: {folder}"
    except OSError:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            open_path(folder)
            return True, f"Pasta aberta: {folder}"
        except OSError as exc:
            return False, f"Não foi possível abrir a pasta: {exc}"


class AssistenteJuridicoApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.status_var = tk.StringVar(value="Pronto para copiar uma rotina.")
        self.monitor_config = carregar_config_monitoramento()
        self.monitor_after_id: str | None = None
        self.interval_var = tk.IntVar(value=max(1, int(self.monitor_config.get("intervalo_horas", 1) or 1)))
        self.monitor_status_var = tk.StringVar()
        self.build_window()
        self.atualizar_status_monitoramento()
        if self.monitor_config.get("monitoramento_ativo"):
            self.iniciar_monitoramento(silent=True)

    def build_window(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry("680x760")
        self.root.minsize(620, 700)
        self.root.configure(bg="#f4f6f8")

        main = tk.Frame(self.root, bg="#f4f6f8", padx=28, pady=24)
        main.pack(fill=tk.BOTH, expand=True)

        tk.Label(main, text=APP_TITLE, font=("Segoe UI", 20, "bold"), fg="#172033", bg="#f4f6f8").pack(anchor="w")
        tk.Label(
            main,
            text="Selecione uma rotina para abrir no Claude Cowork.",
            font=("Segoe UI", 10),
            fg="#5d6878",
            bg="#f4f6f8",
            pady=6,
        ).pack(anchor="w", pady=(0, 4))

        credit = tk.Frame(main, bg="#f4f6f8")
        credit.pack(anchor="w", pady=(0, 18))
        tk.Label(credit, text="Criado por: ", font=("Segoe UI", 9), fg="#5d6878", bg="#f4f6f8").pack(side=tk.LEFT)
        author_link = tk.Label(credit, text=AUTHOR_NAME, font=("Segoe UI", 9, "underline"), fg="#1f5fbf", bg="#f4f6f8", cursor="hand2")
        author_link.pack(side=tk.LEFT)
        author_link.bind("<Button-1>", lambda _event: webbrowser.open_new_tab(AUTHOR_URL))

        style = ttk.Style()
        style.configure("TNotebook", background="#f4f6f8", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=(14, 8))

        notebook = ttk.Notebook(main)
        notebook.pack(fill=tk.BOTH, expand=True)

        rotinas_tab = tk.Frame(notebook, bg="#f4f6f8", padx=4, pady=14)
        monitor_tab = tk.Frame(notebook, bg="#f4f6f8", padx=4, pady=14)
        config_tab = tk.Frame(notebook, bg="#f4f6f8", padx=4, pady=14)
        notebook.add(rotinas_tab, text="Rotinas")
        notebook.add(monitor_tab, text="Monitoramento")
        notebook.add(config_tab, text="Configurações")

        self.build_rotinas_tab(rotinas_tab)
        self.build_monitoramento_tab(monitor_tab)
        self.build_configuracoes_tab(config_tab)

        status_box = tk.Frame(main, bg="#e9edf2", padx=14, pady=12)
        status_box.pack(fill=tk.X, side=tk.BOTTOM, pady=(14, 0))
        tk.Label(status_box, textvariable=self.status_var, font=("Segoe UI", 9), fg="#253044", bg="#e9edf2", wraplength=580, justify="left").pack(anchor="w")

    def build_rotinas_tab(self, parent: tk.Frame) -> None:
        for label, filename, featured in PROMPT_BUTTONS:
            self.make_button(parent, label, lambda prompt_file=filename, prompt_label=label: self.copy_prompt(prompt_file, prompt_label), featured).pack(fill=tk.X, pady=5)

    def build_monitoramento_tab(self, parent: tk.Frame) -> None:
        card = tk.Frame(parent, bg="#ffffff", padx=18, pady=16, highlightthickness=1, highlightbackground="#d8dee8")
        card.pack(fill=tk.BOTH, expand=True)
        tk.Label(card, text="Monitoramento por Hora", font=("Segoe UI", 15, "bold"), fg="#172033", bg="#ffffff").pack(anchor="w")
        tk.Label(
            card,
            text="Este monitoramento busca apenas novas pendências após a última base registrada.",
            font=("Segoe UI", 9, "bold"),
            fg="#8a4b00",
            bg="#fff4df",
            padx=10,
            pady=8,
            wraplength=560,
            justify="left",
        ).pack(fill=tk.X, pady=(12, 14))

        interval_row = tk.Frame(card, bg="#ffffff")
        interval_row.pack(fill=tk.X, pady=(0, 12))
        tk.Label(interval_row, text="Verificar a cada", font=("Segoe UI", 10), fg="#253044", bg="#ffffff").pack(side=tk.LEFT)
        interval_spin = tk.Spinbox(interval_row, from_=1, to=168, textvariable=self.interval_var, width=5, font=("Segoe UI", 10), command=self.salvar_intervalo_monitoramento)
        interval_spin.pack(side=tk.LEFT, padx=8)
        interval_spin.bind("<FocusOut>", lambda _event: self.salvar_intervalo_monitoramento())
        interval_spin.bind("<Return>", lambda _event: self.salvar_intervalo_monitoramento())
        tk.Label(interval_row, text="horas", font=("Segoe UI", 10), fg="#253044", bg="#ffffff").pack(side=tk.LEFT)

        self.make_button(card, "Criar/Refazer base inicial", self.criar_base_inicial, featured=True, compact=True).pack(fill=tk.X, pady=5)
        self.make_button(card, "Verificar agora", self.verificar_agora, featured=False, compact=True).pack(fill=tk.X, pady=5)

        controls = tk.Frame(card, bg="#ffffff")
        controls.pack(fill=tk.X, pady=(5, 0))
        self.make_button(controls, "Iniciar monitoramento", self.iniciar_monitoramento, featured=False, compact=True).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), pady=5)
        self.make_button(controls, "Parar monitoramento", self.parar_monitoramento, featured=False, compact=True).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0), pady=5)

        status_panel = tk.Frame(card, bg="#eef3f8", padx=12, pady=12)
        status_panel.pack(fill=tk.X, pady=(16, 0))
        tk.Label(status_panel, textvariable=self.monitor_status_var, font=("Segoe UI", 9), fg="#253044", bg="#eef3f8", wraplength=550, justify="left").pack(anchor="w")

    def build_configuracoes_tab(self, parent: tk.Frame) -> None:
        self.make_button(parent, "Sincronizar Claude/Cowork", self.sync_claude_target, featured=False, compact=True).pack(fill=tk.X, pady=5)
        self.make_button(parent, "Abrir Pasta de Relatórios", lambda: self.handle_folder(REPORTS_DIR), featured=False, compact=True).pack(fill=tk.X, pady=5)
        self.make_button(parent, "Abrir Pasta de Prompts", lambda: self.handle_folder(PROMPTS_DIR), featured=False, compact=True).pack(fill=tk.X, pady=5)
        tk.Label(
            parent,
            text="O app copia prompts e abre o Claude/Cowork. O envio automático por teclado fica desativado nesta versão.",
            font=("Segoe UI", 9),
            fg="#5d6878",
            bg="#f4f6f8",
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(14, 0))

    def make_button(self, parent: tk.Widget, text: str, command, featured: bool, compact: bool = False) -> tk.Button:
        bg = "#1f5fbf" if featured else "#ffffff"
        active_bg = "#184d9c" if featured else "#edf2f8"
        fg = "#ffffff" if featured else "#172033"
        return tk.Button(parent, text=text, command=command, font=("Segoe UI", 11, "bold" if featured else "normal"), bg=bg, fg=fg, activebackground=active_bg, activeforeground=fg, relief=tk.FLAT, bd=0, cursor="hand2", height=2, highlightthickness=1, highlightbackground="#d8dee8", highlightcolor="#d8dee8")

    def copy_prompt(self, filename: str, label: str) -> None:
        prompt_path = PROMPTS_DIR / filename
        try:
            prompt_text = prompt_path.read_text(encoding="utf-8")
        except OSError as exc:
            self.show_error(f"Não foi possível ler o arquivo de prompt: {exc}")
            return
        self.copy_text_and_open_claude(prompt_text, f"Prompt de {label} copiado para a área de transferência.")

    def copy_text_and_open_claude(self, prompt_text: str, success_message: str) -> bool:
        try:
            pyperclip.copy(prompt_text)
        except pyperclip.PyperclipException as exc:
            self.show_error(f"Não foi possível copiar para a área de transferência: {exc}")
            return False

        opened, claude_message = open_claude()
        if opened:
            self.status_var.set(f"{success_message} Claude aberto. Cole o prompt copiado para iniciar a rotina.")
        else:
            self.status_var.set(f"{success_message} {claude_message}")
        return True

    def salvar_intervalo_monitoramento(self) -> None:
        try:
            intervalo = max(1, int(self.interval_var.get()))
        except (tk.TclError, ValueError):
            intervalo = 1
        self.interval_var.set(intervalo)
        self.monitor_config["intervalo_horas"] = intervalo
        salvar_config_monitoramento(self.monitor_config)
        self.atualizar_status_monitoramento()

    def criar_base_inicial(self) -> None:
        self.salvar_intervalo_monitoramento()
        try:
            prompt_text = (PROMPTS_DIR / "criar-base-monitoramento.txt").read_text(encoding="utf-8")
        except OSError as exc:
            self.show_error(f"Não foi possível ler o prompt de base inicial: {exc}")
            return

        if self.copy_text_and_open_claude(prompt_text, "Base inicial solicitada ao Claude. Após o Claude finalizar, as próximas verificações devem buscar apenas novidades."):
            now = agora_iso()
            self.monitor_config["base_inicial_criada"] = True
            snapshot = DEFAULT_SNAPSHOT.copy()
            snapshot["criado_em"] = now
            snapshot["ultima_atualizacao"] = now
            SNAPSHOT_FILE.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
            salvar_config_monitoramento(self.monitor_config)
            self.atualizar_status_monitoramento()

    def verificar_agora(self, scheduled: bool = False) -> None:
        self.salvar_intervalo_monitoramento()
        try:
            prompt_text = (PROMPTS_DIR / "verificar-novas-pendencias.txt").read_text(encoding="utf-8")
        except OSError as exc:
            self.show_error(f"Não foi possível ler o prompt de verificação: {exc}")
            return

        if self.copy_text_and_open_claude(prompt_text, "Prompt copiado. Cole no Claude Cowork e execute."):
            now = datetime.now().replace(second=0, microsecond=0)
            self.monitor_config["ultima_verificacao"] = now.isoformat()
            if self.monitor_config.get("monitoramento_ativo"):
                next_run = now + timedelta(hours=max(1, int(self.monitor_config.get("intervalo_horas", 1) or 1)))
                self.monitor_config["proxima_verificacao"] = next_run.isoformat()
            salvar_config_monitoramento(self.monitor_config)
            self.atualizar_status_monitoramento()
            if scheduled and self.monitor_config.get("monitoramento_ativo"):
                self.agendar_proxima_verificacao()

    def iniciar_monitoramento(self, silent: bool = False) -> None:
        self.salvar_intervalo_monitoramento()
        if not self.monitor_config.get("base_inicial_criada") and not silent:
            messagebox.showwarning(APP_TITLE, "Recomendado criar a base inicial antes de iniciar o monitoramento, para evitar que pendências antigas sejam tratadas como novas.")

        self.monitor_config["monitoramento_ativo"] = True
        next_run = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=self.interval_var.get())
        self.monitor_config["proxima_verificacao"] = next_run.isoformat()
        salvar_config_monitoramento(self.monitor_config)
        self.agendar_proxima_verificacao()
        self.atualizar_status_monitoramento()
        if not silent:
            self.status_var.set(f"Monitoramento ativo. Próxima verificação em: {next_run.strftime('%d/%m/%Y %H:%M')}.")

    def parar_monitoramento(self) -> None:
        if self.monitor_after_id:
            self.root.after_cancel(self.monitor_after_id)
            self.monitor_after_id = None
        self.monitor_config["monitoramento_ativo"] = False
        self.monitor_config["proxima_verificacao"] = None
        salvar_config_monitoramento(self.monitor_config)
        self.atualizar_status_monitoramento()
        self.status_var.set("Monitoramento parado.")

    def agendar_proxima_verificacao(self) -> None:
        if self.monitor_after_id:
            self.root.after_cancel(self.monitor_after_id)
        interval_ms = max(1, int(self.monitor_config.get("intervalo_horas", 1) or 1)) * 60 * 60 * 1000
        self.monitor_after_id = self.root.after(interval_ms, lambda: self.verificar_agora(scheduled=True))

    def atualizar_status_monitoramento(self) -> None:
        intervalo = max(1, int(self.monitor_config.get("intervalo_horas", 1) or 1))
        ativo = "ativo" if self.monitor_config.get("monitoramento_ativo") else "parado"
        self.monitor_status_var.set(
            "Monitoramento {status}.\n"
            "Última verificação: {ultima}\n"
            "Próxima verificação: {proxima}\n"
            "Intervalo configurado: {intervalo} hora(s)\n"
            "Base inicial criada: {base}\n"
            "Arquivo de controle: {arquivo}".format(
                status=ativo,
                ultima=formatar_data_hora(self.monitor_config.get("ultima_verificacao")),
                proxima=formatar_data_hora(self.monitor_config.get("proxima_verificacao")),
                intervalo=intervalo,
                base="sim" if self.monitor_config.get("base_inicial_criada") else "não",
                arquivo=str(SNAPSHOT_FILE),
            )
        )

    def sync_claude_target(self) -> None:
        config = load_config()
        found_target = find_claude_executable(config)
        if found_target:
            remember_claude_target(found_target)
            self.status_var.set(f"Claude/Cowork sincronizado automaticamente: {found_target}")
            return

        selected = filedialog.askopenfilename(
            title="Selecione o Claude, Cowork ou um atalho",
            filetypes=[("Apps e atalhos", "*.exe *.lnk *.url"), ("Executáveis", "*.exe"), ("Atalhos", "*.lnk *.url"), ("Todos os arquivos", "*.*")],
        )
        if not selected:
            self.status_var.set("Sincronização cancelada. Nenhum app ou atalho foi selecionado.")
            return

        selected_path = Path(selected)
        if not selected_path.exists() or selected_path.suffix.lower() not in (".exe", ".lnk", ".url"):
            self.show_error("Selecione um arquivo .exe, .lnk ou .url válido do Claude/Cowork.")
            return

        remember_claude_target(str(selected_path))
        self.status_var.set(f"Claude/Cowork sincronizado: {selected_path}")

    def handle_folder(self, folder: Path) -> None:
        success, message = open_folder(folder)
        self.status_var.set(message)
        if not success:
            messagebox.showerror(APP_TITLE, message)

    def show_error(self, message: str) -> None:
        self.status_var.set(message)
        messagebox.showerror(APP_TITLE, message)


class AssistenteJuridicoApp:
    COLORS = {
        "navy": "#0B1F3A",
        "blue": "#2563C9",
        "blue_dark": "#1D4ED8",
        "blue_light": "#EFF6FF",
        "bg": "#F5F7FB",
        "text": "#0F172A",
        "muted": "#475569",
        "border": "#E2E8F0",
        "success": "#22C55E",
        "warning": "#F97316",
        "purple": "#7C3AED",
        "white": "#FFFFFF",
        "soft": "#F8FAFC",
        "danger": "#DC2626",
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.active_tab = "rotinas"
        self.status_var = tk.StringVar(value="Tudo pronto para uso")
        self.footer_claude_var = tk.StringVar()
        self.footer_clipboard_var = tk.StringVar(value="Ainda não copiado")
        self.footer_monitor_var = tk.StringVar(value="Desativado")
        self.last_prompt_time: str | None = None
        self.monitor_config = carregar_config_monitoramento()
        self.monitor_after_id: str | None = None
        self.interval_var = tk.IntVar(value=max(1, int(self.monitor_config.get("intervalo_horas", 1) or 1)))
        self.monitor_status_var = tk.StringVar()
        self.auto_open_var = tk.BooleanVar(value=bool(load_config().get("auto_open_claude", True)))
        self.auto_send_var = tk.BooleanVar(value=bool(load_config().get("auto_send_prompt", False)))
        self.modo_abertura_var = tk.StringVar(value=str(load_config().get("modo_abertura", "cowork")))
        self.incluir_login_manual_var = tk.BooleanVar(value=bool(load_config().get("incluir_login_manual", False)))
        self.astrea_login_url_var = tk.StringVar(value=str(load_config().get("astrea_login_url", "")))
        self.astrea_usuario_var = tk.StringVar(value=str(load_config().get("astrea_usuario", "")))
        self.jusbrasil_login_url_var = tk.StringVar(value=str(load_config().get("jusbrasil_login_url", "")))
        self.jusbrasil_usuario_var = tk.StringVar(value=str(load_config().get("jusbrasil_usuario", "")))
        self.astrea_senha_var = tk.StringVar(value=str(load_config().get("astrea_senha", "")))
        self.jusbrasil_senha_var = tk.StringVar(value=str(load_config().get("jusbrasil_senha", "")))
        self.report_search_var = tk.StringVar()
        self.report_period_var = tk.StringVar(value="Todos")
        self.report_type_var = tk.StringVar(value="Todos")
        self.report_rows: list[dict] = []
        self.content_holder: tk.Frame | None = None
        self.tab_buttons: dict[str, tk.Label] = {}

        self.root.title(APP_TITLE)
        self.root.geometry("1100x820")
        self.root.minsize(900, 700)
        self.root.configure(bg=self.COLORS["bg"])
        self.root.option_add("*Font", "{Segoe UI} 10")

        self.build_window()
        self.show_rotinas_tab()
        self.update_footer()
        if self.monitor_config.get("monitoramento_ativo"):
            self.iniciar_monitoramento(silent=True)

    def build_window(self) -> None:
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.create_header(self.root)
        self.create_tabs(self.root)
        self.content_holder = tk.Frame(self.root, bg=self.COLORS["bg"])
        self.content_holder.grid(row=2, column=0, sticky="nsew", padx=28, pady=(12, 12))
        self.create_footer(self.root)

    def create_header(self, parent: tk.Widget) -> None:
        header = tk.Frame(parent, bg=self.COLORS["white"], padx=28, pady=22, highlightthickness=1, highlightbackground=self.COLORS["border"])
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 0))
        header.grid_columnconfigure(1, weight=1)

        logo = tk.Label(header, text="⚖", font=("Segoe UI", 24), fg=self.COLORS["white"], bg=self.COLORS["navy"], width=3, height=1)
        logo.grid(row=0, column=0, rowspan=3, sticky="nw", padx=(0, 16))

        title = tk.Label(
            header,
            text="Assistente Jurídico Exclusive :\nThays Marcela",
            font=("Segoe UI", 24, "bold"),
            fg=self.COLORS["navy"],
            bg=self.COLORS["white"],
            justify="left",
        )
        title.grid(row=0, column=1, sticky="w")

        subtitle = tk.Label(
            header,
            text="Selecione uma rotina para abrir no Claude Cowork.",
            font=("Segoe UI", 11),
            fg=self.COLORS["muted"],
            bg=self.COLORS["white"],
        )
        subtitle.grid(row=1, column=1, sticky="w", pady=(8, 0))

        credit = tk.Frame(header, bg=self.COLORS["white"])
        credit.grid(row=2, column=1, sticky="w", pady=(6, 0))
        tk.Label(credit, text="Criado por ", font=("Segoe UI", 9), fg=self.COLORS["muted"], bg=self.COLORS["white"]).pack(side=tk.LEFT)
        link = tk.Label(credit, text=AUTHOR_NAME, font=("Segoe UI", 9, "underline"), fg=self.COLORS["blue"], bg=self.COLORS["white"], cursor="hand2")
        link.pack(side=tk.LEFT)
        link.bind("<Button-1>", lambda _event: webbrowser.open_new_tab(AUTHOR_URL))

        decor = tk.Canvas(header, width=180, height=105, bg=self.COLORS["white"], bd=0, highlightthickness=0)
        decor.grid(row=0, column=2, rowspan=3, sticky="e")
        decor.create_oval(40, 8, 172, 140, fill=self.COLORS["blue_light"], outline="")
        decor.create_text(106, 55, text="⚖", fill="#DBEAFE", font=("Segoe UI", 52))
        decor.create_line(20, 82, 160, 28, fill="#BFDBFE", width=2, smooth=True)

    def create_tabs(self, parent: tk.Widget) -> None:
        tabs_wrap = tk.Frame(parent, bg=self.COLORS["bg"])
        tabs_wrap.grid(row=1, column=0, sticky="ew", padx=28, pady=(14, 0))
        tabs = tk.Frame(tabs_wrap, bg=self.COLORS["white"], padx=8, pady=8, highlightthickness=1, highlightbackground=self.COLORS["border"])
        tabs.pack(anchor="w")

        items = [
            ("rotinas", "▦  Rotinas"),
            ("monitoramento", "⏱  Monitoramento"),
            ("relatorios", "XLS  Relatórios"),
            ("configuracoes", "⚙  Configurações"),
        ]
        for key, label in items:
            tab = tk.Label(tabs, text=label, font=("Segoe UI", 10, "bold"), padx=18, pady=10, cursor="hand2")
            tab.pack(side=tk.LEFT, padx=2)
            tab.bind("<Button-1>", lambda _event, tab_key=key: self.switch_tab(tab_key))
            self.tab_buttons[key] = tab
        self.refresh_tabs()

    def create_footer(self, parent: tk.Widget) -> None:
        footer = tk.Frame(parent, bg=self.COLORS["white"], padx=28, pady=12, highlightthickness=1, highlightbackground=self.COLORS["border"])
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_columnconfigure((0, 1, 2), weight=1)

        self.footer_claude_var.set(self.current_claude_status_text())
        self.create_footer_item(footer, 0, "✓", "Tudo pronto para uso", self.footer_claude_var, self.COLORS["success"])
        self.create_footer_item(footer, 1, "▣", "Prompt copiado", self.footer_clipboard_var, self.COLORS["blue"])
        self.create_footer_item(footer, 2, "●", "Monitoramento", self.footer_monitor_var, self.COLORS["purple"])

    def create_footer_item(self, parent: tk.Frame, column: int, icon: str, title: str, var: tk.StringVar, color: str) -> None:
        item = tk.Frame(parent, bg=self.COLORS["white"])
        item.grid(row=0, column=column, sticky="w", padx=(0, 18))
        tk.Label(item, text=icon, font=("Segoe UI", 14, "bold"), fg=color, bg=self.COLORS["white"]).pack(side=tk.LEFT, padx=(0, 10))
        text = tk.Frame(item, bg=self.COLORS["white"])
        text.pack(side=tk.LEFT)
        tk.Label(text, text=title, font=("Segoe UI", 9, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(anchor="w")
        tk.Label(text, textvariable=var, font=("Segoe UI", 8), fg=self.COLORS["muted"], bg=self.COLORS["white"]).pack(anchor="w")

    def current_claude_status_text(self) -> str:
        target = find_claude_executable(load_config())
        return "Assistente conectado ao Claude Cowork." if target else "Claude não localizado automaticamente."

    def switch_tab(self, tab_key: str) -> None:
        self.active_tab = tab_key
        self.refresh_tabs()
        if tab_key == "rotinas":
            self.show_rotinas_tab()
        elif tab_key == "monitoramento":
            self.show_monitoramento_tab()
        elif tab_key == "relatorios":
            self.show_relatorios_tab()
        else:
            self.show_configuracoes_tab()

    def refresh_tabs(self) -> None:
        for key, tab in self.tab_buttons.items():
            active = key == self.active_tab
            tab.configure(
                bg=self.COLORS["blue_light"] if active else self.COLORS["white"],
                fg=self.COLORS["blue"] if active else self.COLORS["muted"],
                relief=tk.FLAT,
            )

    def clear_content(self) -> tk.Frame:
        assert self.content_holder is not None
        for child in self.content_holder.winfo_children():
            child.destroy()
        return self.create_scroll_area(self.content_holder)

    def create_scroll_area(self, parent: tk.Frame) -> tk.Frame:
        canvas = tk.Canvas(parent, bg=self.COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=self.COLORS["bg"])
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        return inner

    def show_rotinas_tab(self) -> None:
        content = self.clear_content()
        self.create_primary_card(
            content,
            "Rotina Completa",
            "Executa o fluxo completo de tarefas e abre no Claude Cowork.",
            lambda: self.copy_prompt("rotina-completa.txt", "Rotina Completa"),
        ).pack(fill=tk.X, pady=(0, 18))

        grid = tk.Frame(content, bg=self.COLORS["bg"])
        grid.pack(fill=tk.X)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        cards = [
            ("Consultar Astrea", "Consulta prazos, tarefas e dados no sistema Astrea.", "⌂", self.COLORS["blue"], lambda: self.copy_prompt("astrea.txt", "Consultar Astrea")),
            ("Consultar Jusbrasil", "Pesquisa publicações, intimações e processos no Jusbrasil.", "⚖", self.COLORS["purple"], lambda: self.copy_prompt("jusbrasil.txt", "Consultar Jusbrasil")),
            ("Peça Previdenciária", "Gera minutas e peças da área previdenciária.", "▤", self.COLORS["success"], lambda: self.copy_prompt("peca-previdenciaria.txt", "Peça Previdenciária")),
            ("Peça Trabalhista", "Gera minutas e peças da área trabalhista.", "▣", self.COLORS["warning"], lambda: self.copy_prompt("peca-trabalhista.txt", "Peça Trabalhista")),
            ("Peça Cível", "Gera minutas e peças da área cível.", "□", self.COLORS["navy"], lambda: self.copy_prompt("peca-civel.txt", "Peça Cível")),
            ("Sincronizar Claude/Cowork", "Sincroniza dados e configurações com o Claude Cowork.", "☁", self.COLORS["blue_dark"], self.sync_claude_target),
        ]
        for index, (title, desc, icon, color, command) in enumerate(cards):
            card = self.create_action_card(grid, title, desc, icon, color, command)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0, 10) if index % 2 == 0 else (10, 0), pady=10)

    def show_monitoramento_tab(self) -> None:
        content = self.clear_content()
        self.create_section_title(content, "Monitoramento por Hora", "Verifique apenas novas pendências desde a última base registrada.")
        info = tk.Frame(content, bg="#FFF7ED", padx=16, pady=14, highlightthickness=1, highlightbackground="#FED7AA")
        info.pack(fill=tk.X, pady=(0, 18))
        tk.Label(
            info,
            text="Este monitoramento busca somente novas pendências. Pendências antigas não serão repetidas, exceto se houver alteração relevante ou se a base for refeita.",
            font=("Segoe UI", 10, "bold"),
            fg="#9A3412",
            bg="#FFF7ED",
            wraplength=900,
            justify="left",
        ).pack(anchor="w")

        panel = self.create_panel(content)
        panel.pack(fill=tk.X, pady=(0, 18))
        row = tk.Frame(panel, bg=self.COLORS["white"])
        row.pack(fill=tk.X, pady=(0, 14))
        tk.Label(row, text="Verificar a cada", font=("Segoe UI", 11, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(side=tk.LEFT)
        spin = tk.Spinbox(row, from_=1, to=168, textvariable=self.interval_var, width=6, font=("Segoe UI", 11), command=self.salvar_intervalo_monitoramento)
        spin.pack(side=tk.LEFT, padx=10)
        spin.bind("<FocusOut>", lambda _event: self.salvar_intervalo_monitoramento())
        spin.bind("<Return>", lambda _event: self.salvar_intervalo_monitoramento())
        tk.Label(row, text="horas", font=("Segoe UI", 11), fg=self.COLORS["muted"], bg=self.COLORS["white"]).pack(side=tk.LEFT)
        tk.Label(
            panel,
            text="O monitoramento permanece ativo apenas enquanto este aplicativo estiver aberto.",
            font=("Segoe UI", 9),
            fg=self.COLORS["muted"],
            bg=self.COLORS["white"],
        ).pack(anchor="w", pady=(0, 14))

        buttons = tk.Frame(panel, bg=self.COLORS["white"])
        buttons.pack(fill=tk.X)
        self.styled_button(buttons, "Criar/Refazer Base Inicial", self.criar_base_inicial, "outline").grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=6)
        self.styled_button(buttons, "Verificar Agora", self.verificar_agora, "primary").grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        self.styled_button(buttons, "Iniciar Monitoramento", self.iniciar_monitoramento, "success").grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=6)
        self.styled_button(buttons, "Parar Monitoramento", self.parar_monitoramento, "danger").grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        buttons.grid_columnconfigure((0, 1), weight=1)

        status_grid = tk.Frame(content, bg=self.COLORS["bg"])
        status_grid.pack(fill=tk.X)
        self.refresh_monitor_values()
        values = [
            ("Status", self.monitor_values["status"], "Estado atual do timer interno"),
            ("Última verificação", self.monitor_values["ultima"], "Horário local registrado"),
            ("Próxima verificação", self.monitor_values["proxima"], "Agendamento enquanto o app estiver aberto"),
            ("Intervalo configurado", self.monitor_values["intervalo"], "Valor salvo no monitoramento.json"),
            ("Arquivo de controle", "configuracoes/snapshot_pendencias.json", "Base/snapshot de referência"),
        ]
        for index, (title, value, desc) in enumerate(values):
            card = self.create_status_card(status_grid, title, value, desc)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0, 10) if index % 2 == 0 else (10, 0), pady=10)
        status_grid.grid_columnconfigure(0, weight=1)
        status_grid.grid_columnconfigure(1, weight=1)

    def show_relatorios_tab(self) -> None:
        content = self.clear_content()
        self.create_section_title(content, "Relatórios e Planilhas", "Organize as planilhas Excel geradas pelas rotinas jurídicas.")

        info = tk.Frame(content, bg=self.COLORS["blue_light"], padx=16, pady=14, highlightthickness=1, highlightbackground="#BFDBFE")
        info.pack(fill=tk.X, pady=(0, 16))
        tk.Label(
            info,
            text="As planilhas listadas aqui são arquivos .xlsx salvos na pasta de relatórios. O app organiza por data, tipo e última modificação.",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLORS["navy"],
            bg=self.COLORS["blue_light"],
            wraplength=900,
            justify="left",
        ).pack(anchor="w")

        summary = self.get_reports_summary()
        summary_grid = tk.Frame(content, bg=self.COLORS["bg"])
        summary_grid.pack(fill=tk.X, pady=(0, 14))
        for index, (title, value, desc) in enumerate(summary):
            card = self.create_status_card(summary_grid, title, value, desc)
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 10) if index < 3 else 0)
            summary_grid.grid_columnconfigure(index, weight=1)

        filters = self.create_panel(content)
        filters.pack(fill=tk.X, pady=(0, 14))
        tk.Label(filters, text="Filtros", font=("Segoe UI", 12, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(anchor="w", pady=(0, 10))
        row = tk.Frame(filters, bg=self.COLORS["white"])
        row.pack(fill=tk.X)
        tk.Label(row, text="Busca", bg=self.COLORS["white"], fg=self.COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        search = tk.Entry(row, textvariable=self.report_search_var, font=("Segoe UI", 10), relief=tk.SOLID, bd=1, width=28)
        search.pack(side=tk.LEFT, padx=(8, 18))
        search.bind("<KeyRelease>", lambda _event: self.refresh_reports_table())

        tk.Label(row, text="Período", bg=self.COLORS["white"], fg=self.COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        period = ttk.Combobox(row, textvariable=self.report_period_var, state="readonly", values=["Todos", "Hoje", "Últimos 7 dias", "Este mês", "Este ano"], width=16)
        period.pack(side=tk.LEFT, padx=(8, 18))
        period.bind("<<ComboboxSelected>>", lambda _event: self.refresh_reports_table())

        tk.Label(row, text="Tipo", bg=self.COLORS["white"], fg=self.COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        report_type = ttk.Combobox(row, textvariable=self.report_type_var, state="readonly", values=["Todos", "Rotina completa", "Novas pendências", "Astrea", "Jusbrasil", "Peças jurídicas", "Outros"], width=18)
        report_type.pack(side=tk.LEFT, padx=(8, 0))
        report_type.bind("<<ComboboxSelected>>", lambda _event: self.refresh_reports_table())

        actions = tk.Frame(content, bg=self.COLORS["bg"])
        actions.pack(fill=tk.X, pady=(0, 12))
        self.styled_button(actions, "Atualizar lista", self.refresh_reports_table, "outline").pack(side=tk.LEFT, padx=(0, 8))
        self.styled_button(actions, "Abrir planilha", self.open_selected_report, "primary").pack(side=tk.LEFT, padx=8)
        self.styled_button(actions, "Abrir pasta do arquivo", self.open_selected_report_folder, "outline").pack(side=tk.LEFT, padx=8)
        self.styled_button(actions, "Copiar caminho", self.copy_selected_report_path, "outline").pack(side=tk.LEFT, padx=8)
        self.styled_button(actions, "Organizar por data", self.organize_reports_by_date, "success").pack(side=tk.LEFT, padx=8)
        self.styled_button(actions, "Abrir pasta de relatórios", self.open_reports_folder, "outline").pack(side=tk.LEFT, padx=8)

        table_panel = self.create_panel(content)
        table_panel.pack(fill=tk.BOTH, expand=True)
        columns = ("name", "type", "date", "time", "size", "modified", "path")
        self.reports_tree = ttk.Treeview(table_panel, columns=columns, show="headings", height=16)
        headings = {
            "name": "Nome do arquivo",
            "type": "Tipo",
            "date": "Data",
            "time": "Hora",
            "size": "Tamanho",
            "modified": "Última modificação",
            "path": "Caminho",
        }
        widths = {"name": 260, "type": 130, "date": 90, "time": 70, "size": 80, "modified": 140, "path": 360}
        for col in columns:
            self.reports_tree.heading(col, text=headings[col])
            self.reports_tree.column(col, width=widths[col], anchor="w")
        yscroll = ttk.Scrollbar(table_panel, orient="vertical", command=self.reports_tree.yview)
        xscroll = ttk.Scrollbar(table_panel, orient="horizontal", command=self.reports_tree.xview)
        self.reports_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.reports_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_panel.grid_rowconfigure(0, weight=1)
        table_panel.grid_columnconfigure(0, weight=1)
        self.reports_tree.bind("<Double-1>", lambda _event: self.open_selected_report())
        self.refresh_reports_table()

    def scan_excel_reports(self) -> list[dict]:
        reports_folder = get_reports_folder()
        reports: list[dict] = []
        for file_path in reports_folder.rglob("*.xlsx"):
            if file_path.name.startswith("~$"):
                continue
            try:
                stat = file_path.stat()
            except OSError:
                continue
            report_dt = self.parse_report_date(file_path)
            reports.append(
                {
                    "name": file_path.name,
                    "type": self.parse_report_type(file_path.name),
                    "date": report_dt.strftime("%d/%m/%Y"),
                    "time": report_dt.strftime("%H:%M"),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
                    "size": self.format_file_size(stat.st_size),
                    "path": str(file_path),
                    "datetime": report_dt,
                }
            )
        return sorted(reports, key=lambda item: item["datetime"], reverse=True)

    def parse_report_type(self, filename: str) -> str:
        name = filename.lower()
        if "relatorio_juridico" in name or "relatório_jurídico" in name:
            return "Rotina completa"
        if "novas_pendencias" in name or "novas_pendências" in name:
            return "Novas pendências"
        if "astrea" in name:
            return "Astrea"
        if "jusbrasil" in name:
            return "Jusbrasil"
        if "pecas" in name or "peças" in name:
            return "Peças jurídicas"
        return "Outros"

    def parse_report_date(self, file_path: Path) -> datetime:
        stem = file_path.stem
        if "DATA" not in stem.upper():
            patterns = [
                (r"(20\d{2})[-_](\d{2})[-_](\d{2})", "%Y-%m-%d"),
                (r"(\d{2})[-_](\d{2})[-_](20\d{2})", "%d-%m-%Y"),
            ]
            for pattern, fmt in patterns:
                match = re.search(pattern, stem)
                if match:
                    raw = "-".join(match.groups())
                    try:
                        return datetime.strptime(raw, fmt)
                    except ValueError:
                        pass
        return datetime.fromtimestamp(file_path.stat().st_mtime)

    def format_file_size(self, size_bytes: int) -> str:
        if size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        return f"{max(1, round(size_bytes / 1024))} KB"

    def report_matches_filters(self, report: dict) -> bool:
        query = self.report_search_var.get().strip().lower()
        if query and query not in report["name"].lower():
            return False
        selected_type = self.report_type_var.get()
        if selected_type != "Todos" and report["type"] != selected_type:
            return False
        period = self.report_period_var.get()
        now = datetime.now()
        dt = report["datetime"]
        if period == "Hoje" and dt.date() != now.date():
            return False
        if period == "Últimos 7 dias" and dt < now - timedelta(days=7):
            return False
        if period == "Este mês" and (dt.year != now.year or dt.month != now.month):
            return False
        if period == "Este ano" and dt.year != now.year:
            return False
        return True

    def refresh_reports_table(self) -> None:
        self.report_rows = self.scan_excel_reports()
        if not hasattr(self, "reports_tree"):
            return
        self.reports_tree.delete(*self.reports_tree.get_children())
        for index, report in enumerate([r for r in self.report_rows if self.report_matches_filters(r)]):
            self.reports_tree.insert("", "end", iid=str(index), values=(report["name"], report["type"], report["date"], report["time"], report["size"], report["modified"], report["path"]))
        self.status_var.set("Lista de relatórios atualizada." if self.report_rows else "Nenhuma planilha localizada na pasta de relatórios.")

    def get_selected_report(self) -> dict | None:
        if not hasattr(self, "reports_tree"):
            return None
        selection = self.reports_tree.selection()
        if not selection:
            messagebox.showinfo(APP_TITLE, "Selecione uma planilha primeiro.")
            return None
        path = self.reports_tree.set(selection[0], "path")
        for report in self.report_rows:
            if report["path"] == path:
                return report
        return None

    def open_selected_report(self) -> None:
        report = self.get_selected_report()
        if not report:
            return
        try:
            open_path(report["path"])
            self.status_var.set("Planilha aberta.")
        except OSError as exc:
            self.show_error(f"Não foi possível abrir a planilha: {exc}")

    def open_selected_report_folder(self) -> None:
        report = self.get_selected_report()
        if not report:
            return
        path = Path(report["path"])
        try:
            reveal_path(path)
        except OSError:
            open_folder(path.parent)

    def copy_selected_report_path(self) -> None:
        report = self.get_selected_report()
        if not report:
            return
        pyperclip.copy(report["path"])
        self.status_var.set("Caminho da planilha copiado.")

    def organize_reports_by_date(self) -> None:
        reports = self.scan_excel_reports()
        if not reports:
            self.status_var.set("Nenhuma planilha localizada na pasta de relatórios.")
            return
        if not messagebox.askyesno(APP_TITLE, "Deseja organizar as planilhas em subpastas por ano e mês? Exemplo: relatorios/2026/06-Junho/"):
            return
        month_names = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
            7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
        }
        for report in reports:
            source = Path(report["path"])
            dt = report["datetime"]
            target_dir = get_reports_folder() / str(dt.year) / f"{dt.month:02d}-{month_names[dt.month]}"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / source.name
            counter = 1
            while target.exists() and target.resolve() != source.resolve():
                target = target_dir / f"{source.stem}_{counter}{source.suffix}"
                counter += 1
            if source.resolve() != target.resolve():
                shutil.move(str(source), str(target))
        self.refresh_reports_table()
        self.status_var.set("Planilhas organizadas por data.")

    def get_reports_summary(self) -> list[tuple[str, str, str]]:
        reports = self.scan_excel_reports()
        today = datetime.now().date()
        total = len(reports)
        today_count = sum(1 for report in reports if report["datetime"].date() == today)
        last_report = reports[0]["datetime"].strftime("%d/%m/%Y %H:%M") if reports else "Nenhuma"
        folder = str(get_reports_folder())
        return [
            ("Total de planilhas", str(total), "Arquivos .xlsx encontrados"),
            ("Hoje", str(today_count), "Planilhas com data de hoje"),
            ("Última planilha", last_report, "Mais recente primeiro"),
            ("Pasta", folder, "Pasta principal de relatórios"),
        ]

    def open_reports_folder(self) -> None:
        success, message = open_folder(get_reports_folder())
        self.status_var.set(message if success else "Não foi possível abrir a pasta de relatórios.")

    def show_configuracoes_tab(self) -> None:
        content = self.clear_content()
        self.create_section_title(content, "Configurações", "Gerencie o Claude Cowork, pastas do sistema e opções de abertura.")

        target = find_claude_executable(load_config()) or "Não encontrado automaticamente"
        claude_panel = self.create_panel(content)
        claude_panel.pack(fill=tk.X, pady=(0, 18))
        tk.Label(claude_panel, text="Caminho do Claude Desktop", font=("Segoe UI", 14, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(anchor="w")
        tk.Label(claude_panel, text=target, font=("Segoe UI", 9), fg=self.COLORS["muted"], bg=self.COLORS["white"], wraplength=900, justify="left").pack(anchor="w", pady=(8, 12))
        row = tk.Frame(claude_panel, bg=self.COLORS["white"])
        row.pack(fill=tk.X)
        self.styled_button(row, "Testar abertura do Claude", self.testar_abertura_claude, "primary").pack(side=tk.LEFT, padx=(0, 10))
        self.styled_button(row, "Selecionar caminho manualmente", self.selecionar_caminho_manual, "outline").pack(side=tk.LEFT)

        mode_panel = self.create_panel(content)
        mode_panel.pack(fill=tk.X, pady=(0, 18))
        tk.Label(mode_panel, text="Modo de abertura", font=("Segoe UI", 14, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(anchor="w")
        tk.Label(
            mode_panel,
            text="Escolha onde o Claude deve abrir quando uma rotina for executada.",
            font=("Segoe UI", 9),
            fg=self.COLORS["muted"],
            bg=self.COLORS["white"],
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(6, 10))
        tk.Radiobutton(
            mode_panel,
            text="Claude Cowork — recomendado para automações e uso do computador",
            variable=self.modo_abertura_var,
            value="cowork",
            command=self.save_modo_abertura,
            bg=self.COLORS["white"],
            fg=self.COLORS["navy"],
            activebackground=self.COLORS["white"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=2)
        tk.Radiobutton(
            mode_panel,
            text="Chat normal — recomendado para conversas simples",
            variable=self.modo_abertura_var,
            value="chat",
            command=self.save_modo_abertura,
            bg=self.COLORS["white"],
            fg=self.COLORS["navy"],
            activebackground=self.COLORS["white"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=2)

        prompt_panel = self.create_panel(content)
        prompt_panel.pack(fill=tk.X, pady=(0, 18))
        tk.Label(prompt_panel, text="Prompt", font=("Segoe UI", 14, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(anchor="w")
        tk.Label(
            prompt_panel,
            text="Edite os prompts, abra a pasta de arquivos .txt ou gere um backup dos comandos.",
            font=("Segoe UI", 9),
            fg=self.COLORS["muted"],
            bg=self.COLORS["white"],
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(6, 12))
        prompt_buttons = tk.Frame(prompt_panel, bg=self.COLORS["white"])
        prompt_buttons.pack(fill=tk.X)
        self.styled_button(prompt_buttons, "Editar Prompts", self.show_prompts_tab, "primary").pack(side=tk.LEFT, padx=(0, 8))
        self.styled_button(prompt_buttons, "Abrir Pasta de Prompts", lambda: self.handle_folder(PROMPTS_DIR), "outline").pack(side=tk.LEFT, padx=8)
        self.styled_button(prompt_buttons, "Criar Backup dos Prompts", self.create_prompts_backup, "success").pack(side=tk.LEFT, padx=8)

        folders = self.create_panel(content)
        folders.pack(fill=tk.X, pady=(0, 18))
        tk.Label(folders, text="Pastas do sistema", font=("Segoe UI", 14, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(anchor="w")
        for label, path in [("Relatórios", get_reports_folder()), ("Configurações", CONFIG_DIR)]:
            tk.Label(folders, text=f"{label}: {path}", font=("Segoe UI", 9), fg=self.COLORS["muted"], bg=self.COLORS["white"], wraplength=900, justify="left").pack(anchor="w", pady=(6, 0))
        folder_buttons = tk.Frame(folders, bg=self.COLORS["white"])
        folder_buttons.pack(fill=tk.X, pady=(12, 0))
        self.styled_button(folder_buttons, "Abrir Pasta de Relatórios", self.open_reports_folder, "outline").pack(side=tk.LEFT, padx=(0, 8))
        self.styled_button(folder_buttons, "Abrir Pasta de Configurações", lambda: self.handle_folder(CONFIG_DIR), "outline").pack(side=tk.LEFT, padx=8)

        login_panel = self.create_panel(content)
        login_panel.pack(fill=tk.X, pady=(0, 18))
        tk.Label(login_panel, text="Login manual Astrea/Jusbrasil", font=("Segoe UI", 14, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(anchor="w")
        tk.Label(
            login_panel,
            text="Quando email e senha forem preenchidos, o app inclui no prompt o pedido para o Claude fazer login. Se algum dado faltar, o prompt orienta login manual.",
            font=("Segoe UI", 9),
            fg=self.COLORS["muted"],
            bg=self.COLORS["white"],
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(6, 12))

        astrea_url_row = tk.Frame(login_panel, bg=self.COLORS["white"])
        astrea_url_row.pack(fill=tk.X, pady=4)
        tk.Label(astrea_url_row, text="Astrea URL login", font=("Segoe UI", 10, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"], width=20, anchor="w").pack(side=tk.LEFT)
        tk.Entry(astrea_url_row, textvariable=self.astrea_login_url_var, font=("Segoe UI", 10), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, fill=tk.X, expand=True)

        astrea_row = tk.Frame(login_panel, bg=self.COLORS["white"])
        astrea_row.pack(fill=tk.X, pady=4)
        tk.Label(astrea_row, text="Astrea email/usuário", font=("Segoe UI", 10, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"], width=20, anchor="w").pack(side=tk.LEFT)
        tk.Entry(astrea_row, textvariable=self.astrea_usuario_var, font=("Segoe UI", 10), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, fill=tk.X, expand=True)

        jus_url_row = tk.Frame(login_panel, bg=self.COLORS["white"])
        jus_url_row.pack(fill=tk.X, pady=(14, 4))
        tk.Label(jus_url_row, text="Jusbrasil URL login", font=("Segoe UI", 10, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"], width=20, anchor="w").pack(side=tk.LEFT)
        tk.Entry(jus_url_row, textvariable=self.jusbrasil_login_url_var, font=("Segoe UI", 10), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, fill=tk.X, expand=True)

        jus_row = tk.Frame(login_panel, bg=self.COLORS["white"])
        jus_row.pack(fill=tk.X, pady=4)
        tk.Label(jus_row, text="Jusbrasil email/usuário", font=("Segoe UI", 10, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"], width=20, anchor="w").pack(side=tk.LEFT)
        tk.Entry(jus_row, textvariable=self.jusbrasil_usuario_var, font=("Segoe UI", 10), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.create_password_block(login_panel, "Astrea", self.astrea_senha_var)
        self.create_password_block(login_panel, "Jusbrasil", self.jusbrasil_senha_var)

        tk.Checkbutton(
            login_panel,
            text="Incluir instruções de login nos prompts",
            variable=self.incluir_login_manual_var,
            command=self.save_login_manual_options,
            bg=self.COLORS["white"],
            fg=self.COLORS["navy"],
            activebackground=self.COLORS["white"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(10, 4))
        self.styled_button(login_panel, "Salvar dados de login", self.save_login_manual_options, "outline").pack(anchor="w", pady=(6, 0))

        options = self.create_panel(content)
        options.pack(fill=tk.X)
        tk.Label(options, text="Opções", font=("Segoe UI", 14, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(anchor="w")
        cb1 = tk.Checkbutton(options, text="Abrir Claude automaticamente após copiar prompt.", variable=self.auto_open_var, command=self.save_auto_open_option, bg=self.COLORS["white"], fg=self.COLORS["navy"], activebackground=self.COLORS["white"], font=("Segoe UI", 10))
        cb1.pack(anchor="w", pady=(10, 2))
        cb2 = tk.Checkbutton(options, text="Apenas copiar prompt, sem abrir Claude.", variable=tk.BooleanVar(value=not self.auto_open_var.get()), command=self.disable_auto_open_option, bg=self.COLORS["white"], fg=self.COLORS["navy"], activebackground=self.COLORS["white"], font=("Segoe UI", 10))
        cb2.pack(anchor="w", pady=2)
        cb3 = tk.Checkbutton(
            options,
            text="Enviar mensagem automaticamente após abrir Claude (pressionar Enter).",
            variable=self.auto_send_var,
            command=self.save_auto_send_option,
            bg=self.COLORS["white"],
            fg=self.COLORS["navy"],
            activebackground=self.COLORS["white"],
            font=("Segoe UI", 10),
        )
        cb3.pack(anchor="w", pady=(10, 2))
        tk.Label(
            options,
            text="Quando ativado, o app aguarda alguns segundos após abrir o Claude via link direto e pressiona Enter. Use apenas se o Claude estiver abrindo corretamente com o prompt preenchido.",
            font=("Segoe UI", 9),
            fg=self.COLORS["muted"],
            bg=self.COLORS["white"],
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

    def show_prompts_tab(self) -> None:
        content = self.clear_content()
        self.create_section_title(content, "Editor de Prompts", "Abra, edite e salve os arquivos .txt sem sair do aplicativo.")

        toolbar = tk.Frame(content, bg=self.COLORS["bg"])
        toolbar.pack(fill=tk.X, pady=(0, 12))
        self.styled_button(toolbar, "Salvar Prompt", self.save_current_prompt_file, "primary").pack(side=tk.LEFT, padx=(0, 8))
        self.styled_button(toolbar, "Recarregar", self.reload_current_prompt_file, "outline").pack(side=tk.LEFT, padx=8)
        self.styled_button(toolbar, "Criar Backup dos Prompts", self.create_prompts_backup, "success").pack(side=tk.LEFT, padx=8)
        self.styled_button(toolbar, "Abrir Pasta de Backups", lambda: self.handle_folder(BACKUPS_DIR), "outline").pack(side=tk.LEFT, padx=8)

        editor_panel = self.create_panel(content)
        editor_panel.pack(fill=tk.BOTH, expand=True)
        editor_panel.grid_columnconfigure(1, weight=1)
        editor_panel.grid_rowconfigure(0, weight=1)

        list_frame = tk.Frame(editor_panel, bg=self.COLORS["white"])
        list_frame.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        tk.Label(list_frame, text="Arquivos", font=("Segoe UI", 10, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(anchor="w", pady=(0, 8))

        self.prompt_listbox = tk.Listbox(list_frame, width=34, height=22, font=("Segoe UI", 9), activestyle="none")
        self.prompt_listbox.pack(fill=tk.Y, expand=True)
        self.prompt_listbox.bind("<<ListboxSelect>>", lambda _event: self.load_selected_prompt_file())

        text_frame = tk.Frame(editor_panel, bg=self.COLORS["white"])
        text_frame.grid(row=0, column=1, sticky="nsew")
        tk.Label(text_frame, text="Conteúdo", font=("Segoe UI", 10, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(anchor="w", pady=(0, 8))

        text_wrap = tk.Frame(text_frame, bg=self.COLORS["white"])
        text_wrap.pack(fill=tk.BOTH, expand=True)
        text_scroll = ttk.Scrollbar(text_wrap, orient="vertical")
        self.prompt_editor = tk.Text(text_wrap, wrap=tk.WORD, undo=True, font=("Consolas", 10), yscrollcommand=text_scroll.set)
        text_scroll.configure(command=self.prompt_editor.yview)
        self.prompt_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.current_prompt_file: Path | None = None
        self.populate_prompt_list()

    def populate_prompt_list(self) -> None:
        self.prompt_listbox.delete(0, tk.END)
        prompt_files = sorted(PROMPTS_DIR.glob("*.txt"))
        for prompt_file in prompt_files:
            self.prompt_listbox.insert(tk.END, prompt_file.name)
        if prompt_files:
            self.prompt_listbox.selection_set(0)
            self.load_selected_prompt_file()

    def load_selected_prompt_file(self) -> None:
        selection = self.prompt_listbox.curselection()
        if not selection:
            return
        filename = self.prompt_listbox.get(selection[0])
        prompt_path = PROMPTS_DIR / filename
        try:
            content = prompt_path.read_text(encoding="utf-8")
        except OSError as exc:
            self.show_error(f"Não foi possível abrir o prompt: {exc}")
            return
        self.current_prompt_file = prompt_path
        self.prompt_editor.delete("1.0", tk.END)
        self.prompt_editor.insert("1.0", content)
        self.status_var.set(f"Prompt aberto: {filename}")

    def save_current_prompt_file(self) -> None:
        if not self.current_prompt_file:
            self.show_error("Selecione um prompt antes de salvar.")
            return
        try:
            content = self.prompt_editor.get("1.0", tk.END).rstrip() + "\n"
            self.current_prompt_file.write_text(content, encoding="utf-8")
        except OSError as exc:
            self.show_error(f"Não foi possível salvar o prompt: {exc}")
            return
        self.status_var.set(f"Prompt salvo: {self.current_prompt_file.name}")

    def reload_current_prompt_file(self) -> None:
        if not self.current_prompt_file:
            self.populate_prompt_list()
            return
        try:
            content = self.current_prompt_file.read_text(encoding="utf-8")
        except OSError as exc:
            self.show_error(f"Não foi possível recarregar o prompt: {exc}")
            return
        self.prompt_editor.delete("1.0", tk.END)
        self.prompt_editor.insert("1.0", content)
        self.status_var.set(f"Prompt recarregado: {self.current_prompt_file.name}")

    def create_prompts_backup(self) -> None:
        ensure_project_files()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUPS_DIR / f"prompts_backup_{timestamp}.zip"
        try:
            with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as backup:
                for prompt_file in sorted(PROMPTS_DIR.glob("*.txt")):
                    backup.write(prompt_file, arcname=prompt_file.name)
        except OSError as exc:
            self.show_error(f"Não foi possível criar backup: {exc}")
            return
        self.status_var.set(f"Backup criado: {backup_path}")

    def create_section_title(self, parent: tk.Frame, title: str, subtitle: str) -> None:
        tk.Label(parent, text=title, font=("Segoe UI", 18, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["bg"]).pack(anchor="w")
        tk.Label(parent, text=subtitle, font=("Segoe UI", 10), fg=self.COLORS["muted"], bg=self.COLORS["bg"]).pack(anchor="w", pady=(4, 18))

    def create_password_block(self, parent: tk.Frame, service_name: str, password_var: tk.StringVar) -> None:
        block = tk.Frame(parent, bg=self.COLORS["soft"], padx=12, pady=10, highlightthickness=1, highlightbackground=self.COLORS["border"])
        block.pack(fill=tk.X, pady=(10, 0))

        tk.Label(
            block,
            text=f"{service_name} senha",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLORS["navy"],
            bg=self.COLORS["soft"],
        ).pack(anchor="w", pady=(0, 6))

        row = tk.Frame(block, bg=self.COLORS["soft"])
        row.pack(fill=tk.X)

        password_entry = tk.Entry(
            row,
            textvariable=password_var,
            show="*",
            font=("Segoe UI", 10),
            relief=tk.SOLID,
            bd=1,
        )
        password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def toggle_password() -> None:
            showing = password_entry.cget("show") == ""
            password_entry.configure(show="*" if showing else "")
            eye_button.configure(text="👁" if showing else "🙈")

        eye_button = tk.Button(
            row,
            text="👁",
            command=toggle_password,
            bg=self.COLORS["white"],
            fg=self.COLORS["navy"],
            activebackground=self.COLORS["blue_light"],
            relief=tk.FLAT,
            bd=0,
            width=4,
            cursor="hand2",
        )
        eye_button.pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(
            block,
            text="Senha fica mascarada no app, mas entra no prompt quando salva.",
            font=("Segoe UI", 8),
            fg=self.COLORS["muted"],
            bg=self.COLORS["soft"],
        ).pack(anchor="w", pady=(6, 0))

    def create_panel(self, parent: tk.Frame) -> tk.Frame:
        return tk.Frame(parent, bg=self.COLORS["white"], padx=18, pady=16, highlightthickness=1, highlightbackground=self.COLORS["border"])

    def create_primary_card(self, parent: tk.Frame, title: str, description: str, command) -> tk.Frame:
        card = tk.Frame(parent, bg=self.COLORS["blue"], padx=22, pady=22, cursor="hand2")
        card.grid_columnconfigure(1, weight=1)
        tk.Label(card, text="✓", font=("Segoe UI", 20, "bold"), fg=self.COLORS["blue"], bg=self.COLORS["white"], width=3).grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 16))
        tk.Label(card, text=title, font=("Segoe UI", 18, "bold"), fg=self.COLORS["white"], bg=self.COLORS["blue"]).grid(row=0, column=1, sticky="w")
        tk.Label(card, text=description, font=("Segoe UI", 10), fg="#DBEAFE", bg=self.COLORS["blue"]).grid(row=1, column=1, sticky="w", pady=(6, 0))
        tk.Label(card, text="›", font=("Segoe UI", 30), fg=self.COLORS["white"], bg=self.COLORS["blue"]).grid(row=0, column=2, rowspan=2, sticky="e")
        self.bind_card(card, command, self.COLORS["blue_dark"], self.COLORS["blue"])
        return card

    def create_action_card(self, parent: tk.Frame, title: str, description: str, icon: str, accent_color: str, command) -> tk.Frame:
        card = tk.Frame(parent, bg=self.COLORS["white"], padx=16, pady=16, cursor="hand2", highlightthickness=1, highlightbackground=self.COLORS["border"])
        card.grid_columnconfigure(1, weight=1)
        tk.Label(card, text=icon, font=("Segoe UI", 17, "bold"), fg=accent_color, bg=self.COLORS["blue_light"], width=3).grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 12))
        tk.Label(card, text=title, font=("Segoe UI", 12, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).grid(row=0, column=1, sticky="w")
        tk.Label(card, text=description, font=("Segoe UI", 9), fg=self.COLORS["muted"], bg=self.COLORS["white"], wraplength=330, justify="left").grid(row=1, column=1, sticky="w", pady=(6, 0))
        tk.Label(card, text="›", font=("Segoe UI", 22), fg=self.COLORS["muted"], bg=self.COLORS["white"]).grid(row=0, column=2, rowspan=2, sticky="e")
        self.bind_card(card, command, self.COLORS["soft"], self.COLORS["white"])
        return card

    def create_status_card(self, parent: tk.Frame, title: str, value: str, description: str | None = None) -> tk.Frame:
        card = self.create_panel(parent)
        tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), fg=self.COLORS["muted"], bg=self.COLORS["white"]).pack(anchor="w")
        tk.Label(card, text=value, font=("Segoe UI", 13, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"], wraplength=420, justify="left").pack(anchor="w", pady=(6, 0))
        if description:
            tk.Label(card, text=description, font=("Segoe UI", 8), fg=self.COLORS["muted"], bg=self.COLORS["white"], wraplength=420, justify="left").pack(anchor="w", pady=(6, 0))
        return card

    def bind_card(self, card: tk.Frame, command, hover_bg: str, normal_bg: str) -> None:
        def set_bg(widget: tk.Widget, color: str) -> None:
            try:
                widget.configure(bg=color)
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                if isinstance(child, tk.Label) and child.cget("bg") == normal_bg:
                    child.configure(bg=color)

        def on_enter(_event) -> None:
            set_bg(card, hover_bg)
            card.configure(highlightbackground=self.COLORS["blue"])

        def on_leave(_event) -> None:
            set_bg(card, normal_bg)
            card.configure(highlightbackground=self.COLORS["border"])

        widgets = [card, *card.winfo_children()]
        for widget in widgets:
            widget.bind("<Button-1>", lambda _event: command())
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def styled_button(self, parent: tk.Widget, text: str, command, variant: str) -> tk.Button:
        styles = {
            "primary": (self.COLORS["blue"], self.COLORS["white"], self.COLORS["blue_dark"]),
            "success": (self.COLORS["success"], self.COLORS["white"], "#16A34A"),
            "danger": ("#FEE2E2", self.COLORS["danger"], "#FECACA"),
            "outline": (self.COLORS["white"], self.COLORS["blue"], self.COLORS["blue_light"]),
        }
        bg, fg, active = styles.get(variant, styles["outline"])
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=active, activeforeground=fg, relief=tk.FLAT, bd=0, padx=16, pady=10, cursor="hand2", font=("Segoe UI", 10, "bold"), highlightthickness=1, highlightbackground=self.COLORS["border"])

    def copy_prompt(self, filename: str, label: str) -> None:
        ensure_project_files()
        prompt_path = PROMPTS_DIR / filename
        try:
            prompt_text = prompt_path.read_text(encoding="utf-8")
        except OSError as exc:
            self.show_error(f"Não foi possível ler o arquivo de prompt: {exc}")
            return
        template_context = self.collect_piece_template_context(filename)
        if template_context is None:
            return
        if template_context:
            prompt_text = prompt_text.rstrip() + template_context
        prompt_text = self.apply_login_manual_context(prompt_text)
        self.copy_text_and_open_claude(prompt_text, f"Prompt de {label} copiado para a área de transferência.")

    def collect_piece_template_context(self, filename: str) -> str | None:
        if filename not in {"peca-previdenciaria.txt", "peca-trabalhista.txt", "peca-civel.txt"}:
            return ""

        dialog = tk.Toplevel(self.root)
        dialog.title("Dados da peça")
        dialog.configure(bg=self.COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("460x340")
        dialog.resizable(False, False)

        container = tk.Frame(dialog, bg=self.COLORS["white"], padx=18, pady=16)
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        tk.Label(container, text="Dados para a peça", font=("Segoe UI", 15, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(anchor="w")
        tk.Label(container, text="Preencha o que souber. Campos vazios serão ignorados.", font=("Segoe UI", 9), fg=self.COLORS["muted"], bg=self.COLORS["white"]).pack(anchor="w", pady=(4, 12))

        fields = {
            "nome_cliente": ("Nome do cliente", tk.StringVar()),
            "numero_processo": ("Número do processo", tk.StringVar()),
            "tipo_peca": ("Tipo de peça", tk.StringVar()),
            "prazo": ("Prazo", tk.StringVar()),
        }

        for _key, (label, var) in fields.items():
            row = tk.Frame(container, bg=self.COLORS["white"])
            row.pack(fill=tk.X, pady=5)
            tk.Label(row, text=label, width=18, anchor="w", font=("Segoe UI", 9, "bold"), fg=self.COLORS["navy"], bg=self.COLORS["white"]).pack(side=tk.LEFT)
            tk.Entry(row, textvariable=var, font=("Segoe UI", 10), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, fill=tk.X, expand=True)

        result = {"value": None}

        def confirm() -> None:
            lines = ["", "", "DADOS INFORMADOS PELA USUÁRIA PARA ESTA PEÇA:"]
            for _key, (label, var) in fields.items():
                value = var.get().strip()
                if value:
                    lines.append(f"- {label}: {value}")
            result["value"] = "\n".join(lines) if len(lines) > 3 else ""
            dialog.destroy()

        def cancel() -> None:
            result["value"] = None
            dialog.destroy()

        buttons = tk.Frame(container, bg=self.COLORS["white"])
        buttons.pack(fill=tk.X, pady=(16, 0))
        self.styled_button(buttons, "Continuar", confirm, "primary").pack(side=tk.LEFT, padx=(0, 8))
        self.styled_button(buttons, "Cancelar", cancel, "outline").pack(side=tk.LEFT)

        dialog.protocol("WM_DELETE_WINDOW", cancel)
        self.root.wait_window(dialog)
        return result["value"]

    def apply_login_manual_context(self, prompt_text: str) -> str:
        config = load_config()

        astrea_url = str(config.get("astrea_login_url", "")).strip()
        astrea_usuario = str(config.get("astrea_usuario", "")).strip()
        astrea_senha = self.astrea_senha_var.get().strip() or str(config.get("astrea_senha", "")).strip()
        jusbrasil_url = str(config.get("jusbrasil_login_url", "")).strip()
        jusbrasil_usuario = str(config.get("jusbrasil_usuario", "")).strip()
        jusbrasil_senha = self.jusbrasil_senha_var.get().strip() or str(config.get("jusbrasil_senha", "")).strip()
        tem_login_completo = bool((astrea_usuario and astrea_senha) or (jusbrasil_usuario and jusbrasil_senha))

        if not config.get("incluir_login_manual", False) and not tem_login_completo:
            return prompt_text

        if not any([astrea_url, astrea_usuario, astrea_senha, jusbrasil_url, jusbrasil_usuario, jusbrasil_senha]):
            return prompt_text

        login_lines = [
            "",
            "",
            "INSTRUÇÕES DE LOGIN:",
            "Use estes dados apenas para acessar os sistemas nesta rotina. Não salve senhas, não exponha senhas na conversa e não altere dados sem autorização.",
        ]

        if astrea_url or astrea_usuario or astrea_senha:
            login_lines.append("Astrea:")
            if astrea_url:
                login_lines.append(f"- Entrar no site: {astrea_url}")
            if astrea_usuario:
                login_lines.append(f"- Usar email/usuário: {astrea_usuario}")
            if astrea_usuario and astrea_senha:
                login_lines.append(f"- Senha: {astrea_senha}")
                login_lines.append("- Fazer login automaticamente no Astrea usando o email/usuário e a senha acima.")
            else:
                login_lines.append("- Fazer login no Astrea aguardando a usuária preencher os dados que faltarem manualmente.")

        if jusbrasil_url or jusbrasil_usuario or jusbrasil_senha:
            login_lines.append("Jusbrasil:")
            if jusbrasil_url:
                login_lines.append(f"- Entrar no site: {jusbrasil_url}")
            if jusbrasil_usuario:
                login_lines.append(f"- Usar email/usuário: {jusbrasil_usuario}")
            if jusbrasil_usuario and jusbrasil_senha:
                login_lines.append(f"- Senha: {jusbrasil_senha}")
                login_lines.append("- Fazer login automaticamente no Jusbrasil usando o email/usuário e a senha acima.")
            else:
                login_lines.append("- Fazer login no Jusbrasil aguardando a usuária preencher os dados que faltarem manualmente.")

        return prompt_text.rstrip() + "\n".join(login_lines)

    def copy_text_and_open_claude(self, prompt_text: str, success_message: str) -> bool:
        try:
            pyperclip.copy(prompt_text)
        except pyperclip.PyperclipException as exc:
            self.show_error(f"Não foi possível copiar para a área de transferência: {exc}")
            return False

        self.last_prompt_time = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.footer_clipboard_var.set(self.last_prompt_time)
        opened, claude_message = open_claude_deeplink(prompt_text)
        if not opened:
            fallback_opened, _fallback_message = open_claude()
            if fallback_opened:
                claude_message = "Não foi possível abrir via link direto. O prompt foi copiado. Cole manualmente no Claude."
        elif load_config().get("auto_send_prompt", False):
            self.root.after(AUTO_SEND_DELAY_MS, self.auto_send_enter)
            claude_message = f"{claude_message} Envio automático agendado."
        self.footer_claude_var.set(self.current_claude_status_text())
        self.status_var.set(f"{success_message} {claude_message}")
        self.update_footer()
        return True

    def auto_send_enter(self) -> None:
        if not load_config().get("auto_send_prompt", False):
            return
        if send_enter_key():
            self.status_var.set("Enter enviado automaticamente para o Claude.")
        else:
            self.status_var.set("Não foi possível enviar Enter automaticamente. Envie manualmente.")

    def refresh_monitor_values(self) -> None:
        self.monitor_values = {
            "status": "Ativo" if self.monitor_config.get("monitoramento_ativo") else "Parado",
            "ultima": formatar_data_hora(self.monitor_config.get("ultima_verificacao")).replace("Nunca", "Ainda não realizada"),
            "proxima": formatar_data_hora(self.monitor_config.get("proxima_verificacao")).replace("Nunca", "Não agendada"),
            "intervalo": f"{max(1, int(self.monitor_config.get('intervalo_horas', 1) or 1))} hora(s)",
        }
        self.monitor_status_var.set(str(self.monitor_values))

    def salvar_intervalo_monitoramento(self) -> None:
        try:
            intervalo = max(1, int(self.interval_var.get()))
        except (tk.TclError, ValueError):
            intervalo = 1
        self.interval_var.set(intervalo)
        self.monitor_config["intervalo_horas"] = intervalo
        salvar_config_monitoramento(self.monitor_config)
        self.update_footer()

    def criar_base_inicial(self) -> None:
        self.salvar_intervalo_monitoramento()
        try:
            prompt_text = (PROMPTS_DIR / "criar-base-monitoramento.txt").read_text(encoding="utf-8")
        except OSError as exc:
            self.show_error(f"Não foi possível ler o prompt de base inicial: {exc}")
            return
        prompt_text = self.apply_login_manual_context(prompt_text)
        if self.copy_text_and_open_claude(prompt_text, "Prompt de base inicial copiado. Cole no Claude Cowork e execute."):
            now = agora_iso()
            self.monitor_config["base_inicial_criada"] = True
            snapshot = DEFAULT_SNAPSHOT.copy()
            snapshot["criado_em"] = now
            snapshot["ultima_atualizacao"] = now
            SNAPSHOT_FILE.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
            salvar_config_monitoramento(self.monitor_config)
            self.refresh_current_tab()

    def verificar_agora(self, scheduled: bool = False) -> None:
        self.salvar_intervalo_monitoramento()
        try:
            prompt_text = (PROMPTS_DIR / "verificar-novas-pendencias.txt").read_text(encoding="utf-8")
        except OSError as exc:
            self.show_error(f"Não foi possível ler o prompt de verificação: {exc}")
            return
        prompt_text = self.apply_login_manual_context(prompt_text)
        if self.copy_text_and_open_claude(prompt_text, "Prompt de verificação copiado. O Claude deve buscar apenas novas pendências."):
            now = datetime.now().replace(second=0, microsecond=0)
            self.monitor_config["ultima_verificacao"] = now.isoformat()
            if self.monitor_config.get("monitoramento_ativo"):
                self.monitor_config["proxima_verificacao"] = (now + timedelta(hours=max(1, int(self.monitor_config.get("intervalo_horas", 1) or 1)))).isoformat()
            salvar_config_monitoramento(self.monitor_config)
            self.update_footer()
            self.refresh_current_tab()
            if scheduled and self.monitor_config.get("monitoramento_ativo"):
                self.agendar_proxima_verificacao()

    def iniciar_monitoramento(self, silent: bool = False) -> None:
        self.salvar_intervalo_monitoramento()
        if not self.monitor_config.get("base_inicial_criada") and not silent:
            proceed = messagebox.askyesno(APP_TITLE, "Recomendado criar a base inicial antes de iniciar o monitoramento, para evitar que pendências antigas sejam tratadas como novas.\n\nDeseja continuar mesmo assim?")
            if not proceed:
                return
        self.monitor_config["monitoramento_ativo"] = True
        next_run = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=self.interval_var.get())
        self.monitor_config["proxima_verificacao"] = next_run.isoformat()
        salvar_config_monitoramento(self.monitor_config)
        self.agendar_proxima_verificacao()
        self.status_var.set(f"Monitoramento ativo. Próxima verificação em: {next_run.strftime('%d/%m/%Y %H:%M')}.")
        self.update_footer()
        self.refresh_current_tab()

    def parar_monitoramento(self) -> None:
        if self.monitor_after_id:
            self.root.after_cancel(self.monitor_after_id)
            self.monitor_after_id = None
        self.monitor_config["monitoramento_ativo"] = False
        self.monitor_config["proxima_verificacao"] = None
        salvar_config_monitoramento(self.monitor_config)
        self.status_var.set("Monitoramento parado.")
        self.update_footer()
        self.refresh_current_tab()

    def agendar_proxima_verificacao(self) -> None:
        if self.monitor_after_id:
            self.root.after_cancel(self.monitor_after_id)
        interval_ms = max(1, int(self.monitor_config.get("intervalo_horas", 1) or 1)) * 60 * 60 * 1000
        self.monitor_after_id = self.root.after(interval_ms, lambda: self.verificar_agora(scheduled=True))

    def update_footer(self) -> None:
        self.footer_monitor_var.set("Ativado" if self.monitor_config.get("monitoramento_ativo") else "Desativado")
        self.footer_claude_var.set(self.current_claude_status_text())

    def refresh_current_tab(self) -> None:
        if self.active_tab == "monitoramento":
            self.show_monitoramento_tab()
        elif self.active_tab == "configuracoes":
            self.show_configuracoes_tab()

    def sync_claude_target(self) -> None:
        config = load_config()
        found_target = find_claude_executable(config)
        if found_target:
            remember_claude_target(found_target)
            self.status_var.set(f"Claude/Cowork sincronizado automaticamente: {found_target}")
            self.update_footer()
            return
        self.selecionar_caminho_manual()

    def selecionar_caminho_manual(self) -> None:
        selected = filedialog.askopenfilename(
            title="Selecione o Claude, Cowork ou um atalho",
            filetypes=[("Apps e atalhos", "*.exe *.lnk *.url"), ("Executáveis", "*.exe"), ("Atalhos", "*.lnk *.url"), ("Todos os arquivos", "*.*")],
        )
        if not selected:
            self.status_var.set("Sincronização cancelada. Nenhum app ou atalho foi selecionado.")
            return
        selected_path = Path(selected)
        if not selected_path.exists() or selected_path.suffix.lower() not in (".exe", ".lnk", ".url"):
            self.show_error("Selecione um arquivo .exe, .lnk ou .url válido do Claude/Cowork.")
            return
        remember_claude_target(str(selected_path))
        self.status_var.set(f"Claude/Cowork sincronizado: {selected_path}")
        self.update_footer()
        self.refresh_current_tab()

    def testar_abertura_claude(self) -> None:
        opened, message = open_claude()
        self.status_var.set(message)
        self.update_footer()
        if not opened:
            messagebox.showwarning(APP_TITLE, message)

    def save_auto_open_option(self) -> None:
        config = load_config()
        config["auto_open_claude"] = bool(self.auto_open_var.get())
        save_config(config)
        self.status_var.set("Opção de abertura automática salva.")

    def save_auto_send_option(self) -> None:
        config = load_config()
        config["auto_send_prompt"] = bool(self.auto_send_var.get())
        save_config(config)
        if self.auto_send_var.get():
            self.status_var.set("Envio automático ativado. O app pressionará Enter após abrir o Claude.")
        else:
            self.status_var.set("Envio automático desativado.")

    def save_login_manual_options(self) -> None:
        config = load_config()
        config["astrea_login_url"] = self.astrea_login_url_var.get().strip()
        config["astrea_usuario"] = self.astrea_usuario_var.get().strip()
        config["astrea_senha"] = self.astrea_senha_var.get().strip()
        config["jusbrasil_login_url"] = self.jusbrasil_login_url_var.get().strip()
        config["jusbrasil_usuario"] = self.jusbrasil_usuario_var.get().strip()
        config["jusbrasil_senha"] = self.jusbrasil_senha_var.get().strip()
        tem_login_completo = bool(
            (config["astrea_usuario"] and config["astrea_senha"])
            or (config["jusbrasil_usuario"] and config["jusbrasil_senha"])
        )
        config["incluir_login_manual"] = bool(self.incluir_login_manual_var.get() or tem_login_completo)
        self.incluir_login_manual_var.set(config["incluir_login_manual"])
        save_config(config)
        self.status_var.set("Dados de login salvos. Quando houver email e senha, eles entram no prompt.")

    def save_modo_abertura(self) -> None:
        config = load_config()
        modo = self.modo_abertura_var.get()
        config["modo_abertura"] = "chat" if modo == "chat" else "cowork"
        save_config(config)
        label = "Chat normal" if config["modo_abertura"] == "chat" else "Claude Cowork"
        self.status_var.set(f"Modo de abertura salvo: {label}.")

    def disable_auto_open_option(self) -> None:
        self.auto_open_var.set(False)
        self.save_auto_open_option()
        self.refresh_current_tab()

    def handle_folder(self, folder: Path) -> None:
        success, message = open_folder(folder)
        self.status_var.set(message)
        if not success:
            messagebox.showerror(APP_TITLE, message)

    def show_error(self, message: str) -> None:
        self.status_var.set(message)
        messagebox.showerror(APP_TITLE, message)


def main() -> None:
    ensure_project_files()
    root = tk.Tk()
    AssistenteJuridicoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
