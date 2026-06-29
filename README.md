# Assistente Jurídico Exclusive : Thays Marcela

Mini aplicativo desktop para Windows e macOS que copia prompts jurídicos, abre o Claude/Cowork por deep link e organiza rotinas jurídicas em uma interface premium.

## Instalar dependências

```powershell
pip install -r requirements.txt
```

## Rodar

```powershell
python app.py
```

## Gerar .exe no Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

O script gera `dist/AssistenteJuridico.exe` com ícone personalizado e cria um atalho na Área de Trabalho.

## Gerar app no macOS

Em um Mac, rode:

```bash
chmod +x ./build_mac.sh
./build_mac.sh
```

O script gera `dist/AssistenteJuridico.app` e copia o app para a Mesa (`Desktop`), quando disponível.

No GitHub Actions, baixe o artifact `AssistenteJuridico_macOS_arm64` para MacBook com chip Apple Silicon/M1/M2/M3/M4. O zip contem uma pasta com `AssistenteJuridico.app` e `fix_mac_app.sh`.

Importante: o build de macOS precisa ser feito em um Mac. O PyInstaller não gera `.app` macOS corretamente a partir do Windows.

Se o macOS exibir erro como **"app danificado"**, **"não pode ser aberto"** ou **"desenvolvedor não verificado"**, remova a quarentena do app baixado e abra novamente:

```bash
xattr -cr ~/Desktop/AssistenteJuridico.app
open ~/Desktop/AssistenteJuridico.app
```

Se ainda aparecer **"O aplicativo AssistenteJuridico nao pode ser aberto"**, rode o reparo completo:

```bash
chmod +x ./fix_mac_app.sh
./fix_mac_app.sh ~/Desktop/AssistenteJuridico.app
```

Se o app estiver em outra pasta, troque o caminho no comando. Em alguns Macs também funciona clicar com o botão direito no app e escolher **Abrir**.

## Abas do aplicativo

- `Rotinas`: copia os prompts jurídicos principais.
- `Monitoramento`: cria base inicial, verifica novas pendências e inicia/para monitoramento por hora.
- `Relatórios`: visualiza, filtra, abre e organiza planilhas Excel `.xlsx`.
- `Configurações`: sincroniza Claude/Cowork, edita prompts, cria backup, abre pastas, modo de abertura e opções.

## Prompt

Na aba **Configurações**, o bloco **Prompt** permite editar os arquivos `.txt`, abrir a pasta de prompts e criar backup.

Ao clicar em **Editar Prompts**, selecione um arquivo `.txt`, edite o conteúdo e clique em **Salvar Prompt**.

O botão **Criar Backup dos Prompts** gera um `.zip` com data e hora na pasta `backups/`.

## Templates de peças

Ao executar uma rotina de peça jurídica, o app abre uma janela para preencher:

- Nome do cliente
- Número do processo
- Tipo de peça
- Prazo

Campos vazios são ignorados. Os dados preenchidos são anexados ao prompt antes de abrir o Claude.

## Monitoramento por Hora

Use **Criar/Refazer base inicial** antes de iniciar o monitoramento. Essa base representa o que já existia no Astrea/Jusbrasil e não deve ser tratado como novidade.

Depois disso, **Verificar agora** ou **Iniciar monitoramento** copia um prompt que pede ao Claude/Cowork para buscar apenas novas pendências desde a última base/snapshot.

O monitoramento usa timer interno do Tkinter com `after()`. Ele funciona somente enquanto o aplicativo estiver aberto. Não usa Task Scheduler, cron ou agendamento externo.

Arquivos de controle:

- `configuracoes/monitoramento.json`
- `configuracoes/snapshot_pendencias.json`

Prompts do monitoramento:

- `prompts/criar-base-monitoramento.txt`
- `prompts/verificar-novas-pendencias.txt`

## Relatórios

A aba **Relatórios** permite visualizar, filtrar, abrir e organizar as planilhas Excel geradas pelas rotinas jurídicas.

A pasta principal usada é:

```text
C:\Assistente-Juridico\relatorios
```

No macOS, o padrão é:

```text
~/Documents/Assistente-Juridico/relatorios
```

O app também mantém a pasta relativa `relatorios/` como fallback do projeto.

Funcionalidades:

- Atualizar a lista de planilhas.
- Filtrar por nome, período e tipo.
- Abrir a planilha selecionada.
- Abrir a pasta do arquivo selecionado.
- Copiar o caminho completo da planilha.
- Organizar arquivos por ano e mês.

A organização por data apenas move arquivos `.xlsx` para subpastas como `2026/06-Junho/`. O app não apaga arquivos e não altera o conteúdo das planilhas.

## Configuração do Claude/Cowork

O app usa deep links `claude://` para abrir o Claude diretamente com o prompt preenchido:

- `claude://cowork/new?q=...` para abrir no Claude Cowork.
- `claude://claude.ai/new?q=...` para abrir no chat normal.

Na aba **Configurações**, escolha o **Modo de abertura**:

- **Claude Cowork**: recomendado para automações e uso do computador.
- **Chat normal**: recomendado para conversas simples.

O prompt completo sempre é copiado para a área de transferência como backup.

Se o Claude não abrir via link direto, verifique se o Claude Desktop está instalado e atualizado. O app tentará o método antigo e manterá o prompt copiado para colar manualmente.

## Envio automático

O campo `auto_send_prompt` aparece na aba **Configurações** como opção experimental e fica `false` por padrão. Quando ativado, o app abre o Claude via deep link, aguarda alguns segundos e pressiona `Enter` automaticamente.

Use apenas se o Claude estiver abrindo corretamente com o prompt preenchido.

No macOS, o envio automático pode exigir permissão em **Ajustes do Sistema > Privacidade e Segurança > Acessibilidade** para permitir que o app envie a tecla `Enter`.

## Login manual em sistemas

Na aba **Configurações**, a área **Login manual Astrea/Jusbrasil** permite salvar URL de login e email/usuário para orientar o Claude. Há campos de senha mascarados com botão de olho para visualização temporária, mas as senhas não são salvas e não são enviadas no prompt.

Quando a opção estiver ativada e houver dados preenchidos, o app adiciona ao prompt instruções como `Entrar no site: ...`, `Usar email/usuário: ...` e `Fazer login aguardando a usuária preencher a senha manualmente`.
