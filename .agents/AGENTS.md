# Workflow Rules

## 1. Commits Automáticos (Conventional Commits)
Sempre que concluir o desenvolvimento de uma funcionalidade, correção de bug, ou alteração significativa em código, você DEVE exibir para o usuário, no final de sua resposta, os comandos exatos de `git` formatados em Markdown para que ele possa copiar e colar no PowerShell.
Use as melhores práticas de Conventional Commits (`feat:`, `fix:`, `refactor:`, `style:`, etc.) no comando `git commit -m`. Exemplo:
```powershell
git add .
git commit -m "feat(ui): implementa bottom navigation bar para layout mobile-first"
git push
```
