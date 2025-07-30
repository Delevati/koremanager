# Bot Manager - Gerenciador de Bots

## Visão Geral

O Bot Manager é uma aplicação desktop desenvolvida em Python que automatiza o gerenciamento de múltiplos bots, proporcionando controle total sobre inicialização, monitoramento, reinício e configuração. Desenvolvido especialmente para a comunidade, oferece uma interface gráfica intuitiva e funcionalidades avançadas de monitoramento.

## Características Principais

-**Interface Gráfica Completa:** Sistema de abas com controle, configuração e terminais

-**Bandeja do Sistema:** Acesso rápido através do system tray

-**Monitoramento em Tempo Real:** Status, uptime, uso de CPU e memória

-**Captura de Logs (experimental):** Em desenvolvimento, não recomendado para uso. Se um terminal for selecionado na terceira aba, está configurado para mostrar linhas que contenham a palavra "card". Porém, há problemas conhecidos na ordem das linhas e na atualização.

-**Auto-reinício Configurável:** Reinício automático em intervalos personalizados

-**Drag & Drop:** Reordenação fácil dos bots

-**Múltiplas Seleções:** Controle simultâneo de vários bots

## Como Funciona

-**Gerenciamento Inteligente:** Detecta automaticamente bots em execução e evita duplicações

-**Execução Flexível:** Pode executar bots com ou sem janela visível

-**Renomeação Temporária:** Renomeia start.exe para start_<nome_bot>.exe durante execução

-**Monitoramento Contínuo:** Acompanha status, recursos e logs dos bots

-**Configuração Persistente:** Salva configurações em arquivo JSON

## Estrutura de Pastas Requerida

```

Pasta_Principal\

   ├─ bot1\

   │    └─ start.exe

   │    └─ logs\

   │         └─ console.txt

   ├─ bot2\

   │    └─ start.exe

   │    └─ logs\

   │         └─ console.txt

   ├─ bot3\

   │    └─ start.exe

   │    └─ logs\

   │         └─ console.txt

   └─ KoreManager.exe

   └─ bot_config.json (criado automaticamente)

```

Cada subpasta deve conter:

-**start.exe:** Executável do bot

-**logs/console.txt:** Arquivo de log (opcional, para visualização nos terminais)

## Como Usar

### 1. Primeira Execução

- Execute KoreManager.exe
- Vá para a aba "🔧 Setup & Configuration"
- Defina o diretório principal onde estão seus bots
- Clique em "Scan" para detectar automaticamente os bots
- Salve a configuração

### 2. Controlando Bots

- Acesse a aba "🎮 Bot Control"
- Selecione os bots desejados na lista
- Use os botões para:
- Start All/Stop All/Restart All: Controle geral
- Start/Stop/Restart: Controle de bots selecionados
- View Output: Visualizar saída do bot

### 3. Monitoramento

A tabela mostra status em tempo real:

-**Status:** 🟢 Rodando / 🔴 Parado

-**PID:** ID do processo

-**Console:** WINDOW ou NO_WINDOW

-**Memory/CPU:** Uso de recursos

-**Uptime:** Tempo de execução

### 4. Terminais de Log

- Aba "🖥️ Terminais" oferece 3 terminais simultâneos
- Selecione um bot para ver seus logs em tempo real
- Botão "⟳" para limpar logs

### 5. System Tray

- Ícone na bandeja do sistema para acesso rápido
- Menu contexto com controles principais
- Minimize para continuar rodando em segundo plano

## Configurações Avançadas

### Auto-Reinício

-**Intervalo:** Configurável em minutos (padrão: 120 min = 2 horas)

-**Auto-restart:** Ativa/desativa reinício automático

-**Capture Output:** Captura saída dos bots para visualização

### Modos de Execução

-**NO_WINDOW:** Bots executam sem janela visível (padrão)

-**WINDOW:** Marque "WINDOW" para ver janelas dos bots

### Filtros de Log

- Regex configurável para filtrar logs importantes
- Padrão: busca por "Weight" ou "card" nos logs

## Encerrando o Sistema

**Método 1: Interface Gráfica**

- Feche a janela principal
- Todos os bots serão automaticamente encerrados

**Método 2: System Tray**

- Clique direito no ícone da bandeja
- Selecione "Exit"

**Método 3: Task Manager**

- Processe: KoreManager.exe (não wscript.exe)
- Finalize o processo no Gerenciador de Tarefas

## Arquivos de Configuração

### bot_config.json

```json

{

"base_directory": "C:\\caminho\\para\\bots",

"bot_folders": ["bot1", "bot2", "bot3"],

"restart_interval": 7200,

"auto_restart": true,

"start_minimized": false,

"log_level": "INFO",

"capture_output": true

}

```

### bot_manager.log

- Log do sistema com ações e erros
- Rotacionado automaticamente

## Benefícios do Uso

- Interface Intuitiva: Controle visual completo
- Monitoramento Avançado: Métricas em tempo real
- Flexibilidade: Configurações personalizáveis
- Estabilidade: Detecção e correção automática de problemas
- Comunidade: Código aberto para uso comunitário
- Logs Detalhados: Rastreamento completo de atividades
- Multi-threading: Operações não bloqueantes

## Requisitos do Sistema

- Windows 7/10/11
- .NET Framework (geralmente já instalado)
- Permissões para executar programas
- Espaço em disco para logs

## Solução de Problemas

**Bot não inicia**

- Verifique se start.exe existe na pasta do bot
- Confirme permissões de execução
- Verifique logs do sistema na aba Control

**Interface não responde**

- Force o fechamento via Task Manager
- Procure por KoreManager.exe

**Configurações perdidas**

- Arquivo bot_config.json pode estar corrompido
- Delete o arquivo para restaurar configurações padrão

## Contribuições

Este projeto é desenvolvido para a comunidade. Contribuições, sugestões e melhorias são bem-vindas!

### Como Contribuir

- Reporte bugs ou problemas encontrados
- Sugira novas funcionalidades
- Compartilhe melhorias de código
- Ajude na documentação

## Licença

Projeto open-source desenvolvido para uso comunitário. Livre para uso, modificação e distribuição.

## Changelog

### Versão Atual

✅ Interface gráfica completa com sistema de abas

✅ Monitoramento em tempo real de recursos

✅ System tray integrado

✅ Múltiplos terminais de log

✅ Auto-reinício configurável

✅ Configuração persistente em JSON

✅ Drag & drop para reordenação

✅ Seleção múltipla de bots
