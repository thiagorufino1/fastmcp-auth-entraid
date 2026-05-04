# 🤖 MCP Server com Autenticação Microsoft Entra ID

Implementação de referência de um servidor [FastMCP](https://gofastmcp.com) protegido com **Microsoft Entra ID (Azure AD)** utilizando App Roles e controle de acesso baseado em grupos de segurança.

Este projeto demonstra como:
- 🔐 Proteger um servidor MCP com validação de JWT do Entra ID
- 🎭 Aplicar controle de acesso por ferramenta usando App Roles
- 👥 Gerenciar acesso via grupos de segurança do Azure AD sem alterações de código
- 🧠 Filtrar `tools/list` para que a LLM veja apenas as ferramentas que o usuário pode executar

## 🛡️ Visão geral de segurança

Esta seção destina-se a arquitetos de segurança que precisam avaliar a postura de segurança do projeto antes da aprovação para uso corporativo.

### Modelo de ameaças e mitigações

| Ameaça | Mitigação implementada |
|--------|----------------------|
| Acesso sem autenticação | Toda requisição exige JWT assinado pelo Entra ID |
| Token forjado | Assinatura validada contra JWKS público do Entra (chaves rotacionadas pelo Azure) |
| Token v1.0 com issuer diferente | Verifier rejeita qualquer issuer diferente de `login.microsoftonline.com` (v2.0) |
| Usuário sem permissão conecta e enumera ferramentas | Conexão rejeitada com 401 antes de qualquer resposta MCP |
| Usuário com permissão parcial invoca ferramenta proibida | LLM não vê a ferramenta e execução bloqueada em segunda camada |
| Elevação de privilégio via claim manipulado | Claims vêm do JWT assinado pelo Azure, não são aceitos do cliente |
| Token roubado reutilizado | Janela de validade de 1 hora; revogação por remoção de grupo reflete no próximo token |
| Autoatribuição de roles pelo usuário | App Roles são atribuídas exclusivamente por administradores via Azure AD |

## 🏗️ Arquitetura

```
Cliente MCP (portal, CLI, App Service com OBO)
        |
        |  Authorization: Bearer <JWT Entra ID v2.0>
        v
+----------------------------------------------------+
|                  FastMCP Server                    |
|                                                    |
|  Camada 1: RoleEnforcedJWTVerifier                 |
|    - valida assinatura contra JWKS do Entra        |
|    - valida issuer, audience e versão do token     |
|    - rejeita 401 se nenhuma role válida presente   |
|                                                    |
|  Camada 2: tools/list filtrado por auth=           |
|    - LLM recebe apenas ferramentas permitidas      |
|                                                    |
|  Camada 3: tools/call verificado por auth=         |
|    - execução bloqueada se role insuficiente       |
+----------------------------------------------------+
        |
        |  valida JWT contra JWKS público
        v
  Microsoft Entra ID
  (assinatura RS256, rotação automática de chaves)
```

### Camadas de segurança em detalhe

| Camada | Mecanismo | Resultado em falha |
|--------|-----------|-------------------|
| Assinatura JWT | `AzureJWTVerifier` valida RS256 contra JWKS do Entra | `401 Unauthorized` |
| Versão do token | Exige v2.0 (`iss: login.microsoftonline.com`) | `401 Unauthorized` |
| Audience | Valida que `aud` = `CLIENT_ID` da aplicação | `401 Unauthorized` |
| Presença de role | `RoleEnforcedJWTVerifier` verifica claim `roles` | `401 Unauthorized` |
| Visibilidade de ferramentas | `auth=` por ferramenta filtra `tools/list` | Ferramenta oculta da LLM |
| Execução de ferramentas | `auth=` por ferramenta bloqueia `tools/call` | Erro de autorização MCP |

## 🎯 Modelo de controle de acesso

O acesso é controlado via **App Roles do Azure AD atribuídas a grupos de segurança**, sendo necessárias apenas mudanças na associação de grupos para conceder ou revogar acesso, sem alterações de código.

```
Grupos do Azure AD            App Roles          Ferramentas
mcp-trc-read  (grupo)  ──►  mcp-trc-read    ──►     soma
mcp-trc-admin (grupo)  ──►  mcp-trc-admin   ──►     soma
                                            ──►  health_check
```

### Por que App Roles e não OAuth Scopes?

| | OAuth Scopes (`scp`) | App Roles (`roles`) |
|-|----------------------|---------------------|
| Quem controla o acesso | App define, usuário consente | Admin (atribui roles aos grupos) |
| Revogação | Usuário revoga consentimento | Admin revoga via associação de grupo |
| Adequado para | Permissões delegadas pelo usuário | RBAC corporativo |
| Auditável centralmente | Parcialmente | Sim, via Azure AD |

As App Roles aparecem como array `roles` no JWT, sem necessidade de consentimento do usuário, controlado exclusivamente pelo administrador.

### Por que o scope `access_as_user`?

O fluxo delegado exige pelo menos um OAuth scope para o cliente obter um token. O scope `access_as_user` funciona como porta de entrada, permitindo que clientes se autentiquem contra a API. A autorização real (quais ferramentas chamar) é aplicada pelas App Roles, não pelo scope.

## 🔄 Fluxo de autenticação por requisição

```
1. Cliente envia:  POST /mcp
                   Authorization: Bearer <entra-jwt>

2. RoleEnforcedJWTVerifier executa em sequência:
   a. Valida assinatura JWT contra endpoint JWKS do Entra
   b. Valida issuer = https://login.microsoftonline.com/<tenant>/v2.0
   c. Valida audience = <client-id> da aplicação
   d. Valida que scp inclui "access_as_user"
   e. Verifica que claim roles contém ao menos um de: mcp-trc-read, mcp-trc-admin
   → Qualquer falha retorna 401 Unauthorized e encerra a requisição

3. Cliente chama tools/list:
   → FastMCP avalia auth= de cada ferramenta contra o claim roles do token
   → Usuários com mcp-trc-read: recebem apenas [soma]
   → Usuários com mcp-trc-admin: recebem [soma, health_check]

4. Cliente chama tools/call:
   → auth= verificado novamente antes da execução
   → Chamada não autorizada retorna AuthorizationError
```

## 📊 Matriz de acesso por ferramenta

| Ferramenta | `mcp-trc-read` | `mcp-trc-admin` | Sem role |
|------------|:--------------:|:---------------:|:--------:|
| `soma` | ✅ visível + executável | ✅ visível + executável | ❌ 401 na conexão |
| `health_check` | ❌ oculta da LLM | ✅ visível + executável | ❌ 401 na conexão |

A LLM nunca vê ferramentas que o usuário não pode executar, eliminando tentativas de invocação não autorizada.

## 🔀 Modos de autenticação

O FastMCP suporta dois modos, alternados via `AUTH_MODE` no `.env`. O controle de acesso via App Roles e grupos funciona identicamente nos dois modos.

> ⚠️ Apenas um modo pode estar ativo por instância do servidor.

### Modo A: JWT Verifier (`AUTH_MODE=jwt`) — padrão recomendado para ACA

```
Usuário → [obtém token Azure externamente] → Cliente MCP → FastMCP (valida JWT)
```

O cliente obtém token do Entra ID diretamente (via OBO, MSAL, Azure CLI) e envia como Bearer. O FastMCP apenas valida, sem redirecionar nem emitir tokens.

Indicado para: portais customizados, App Service com OBO, Azure Container Apps, automações.

Como obter token para testes:

```powershell
az account get-access-token `
  --scope "api://<CLIENT_ID>/access_as_user" `
  --query accessToken -o tsv
```

### Modo B: OAuth Proxy (`AUTH_MODE=oauth`)

```
Usuário → Cliente MCP → FastMCP (redireciona para login Azure) → Azure → FastMCP → Cliente
```

FastMCP atua como servidor de autorização OAuth, fazendo proxy do login para o Entra ID. Browser abre automaticamente para login. O cliente não precisa gerenciar tokens manualmente.

Indicado para: Claude Desktop, Cursor, extensões VS Code, qualquer cliente com suporte OAuth 2.0 nativo.

Requer registro de redirect URI no App Registration:

```powershell
# Desenvolvimento local
az ad app update --id <CLIENT_ID> `
  --web-redirect-uris "http://localhost:8000/auth/callback"

# Produção (ACA)
az ad app update --id <CLIENT_ID> `
  --web-redirect-uris "https://<seu-app>.azurecontainerapps.io/auth/callback"
```

Endpoints publicados automaticamente pelo FastMCP no modo oauth:

```
/.well-known/oauth-authorization-server       metadados do servidor OAuth
/.well-known/oauth-protected-resource/mcp    metadados do recurso protegido
/auth/callback                                callback do fluxo de autorização
```

### Comparativo dos modos

| | JWT Verifier (`jwt`) | OAuth Proxy (`oauth`) |
|-|----------------------|-----------------------|
| Emissor do token | Microsoft Entra ID | FastMCP via proxy do Entra |
| Requisito do cliente | Deve fornecer Bearer token | Deve suportar OAuth 2.0 |
| App Roles e grupos AD | ✅ | ✅ |
| `client_secret` obrigatório | ❌ | ✅ |
| Redirect URI no App Registration | ❌ | ✅ |
| Fluxo de login via browser | ❌ externo | ✅ nativo |
| Azure Container Apps com MI | ✅ ideal | ⚠️ mais complexo |
| Aquisição de token | Cliente/orchestrador (automatizável via MSAL/MI/OBO) | Automática |

Para alternar entre modos, edite `AUTH_MODE` no `.env` e reinicie o servidor. Nenhuma alteração de código é necessária.

## 📁 Estrutura do projeto

```
mcp-container-apps/
├── .env                   # segredos (nunca commitar)
├── .env.example           # template com documentação
├── requirements.txt
└── app/
    ├── __init__.py
    ├── __main__.py        # ponto de entrada: python -m app
    ├── main.py            # montagem do servidor
    ├── config.py          # variáveis de ambiente + constantes de roles
    ├── auth/
    │   ├── __init__.py
    │   ├── verifier.py    # RoleEnforcedJWTVerifier, build_auth_provider()
    │   └── checks.py      # fábrica de AuthCheck require_roles()
    └── tools/
        ├── __init__.py    # register_tools()
        ├── health.py      # health_check, exige mcp-trc-admin
        └── soma.py        # soma, exige mcp-trc-read ou mcp-trc-admin
```

## ✅ Pré-requisitos

- Python 3.11+
- Azure CLI (`az`): [guia de instalação](https://learn.microsoft.com/pt-br/cli/azure/install-azure-cli)
- Tenant Azure com permissão para criar App Registrations e grupos de segurança

## 🔧 Passo 1: App Registration no Azure

### 1.1 Login

```bash
az login --tenant "<SEU_TENANT_ID>"
```

### 1.2 Criar o App Registration

```bash
APP=$(az ad app create \
  --display-name "mcp-lab" \
  --sign-in-audience AzureADMyOrg \
  --query "{appId:appId, objectId:id}" \
  -o json)

CLIENT_ID=$(echo $APP | jq -r '.appId')
OBJECT_ID=$(echo $APP | jq -r '.objectId')
```

PowerShell:

```powershell
$APP = az ad app create --display-name "mcp-lab" --sign-in-audience AzureADMyOrg --query "{appId:appId, objectId:id}" -o json | ConvertFrom-Json
$CLIENT_ID = $APP.appId
$OBJECT_ID = $APP.objectId
```

### 1.3 Definir URI identificador e versão do token

O URI identificador (`api://<client-id>`) é obrigatório para scopes customizados e App Roles. A versão do token deve ser `2` para que o issuer seja `login.microsoftonline.com` (v2.0). Tokens v1.0 usam `sts.windows.net` como issuer e são rejeitados pelo verifier.

```powershell
az ad app update --id $CLIENT_ID --identifier-uris "api://$CLIENT_ID"

$body = '{"api":{"requestedAccessTokenVersion":2}}'
$body | Out-File "$env:TEMP\tokenver.json" -Encoding utf8 -NoNewline
az rest --method PATCH `
  --uri "https://graph.microsoft.com/v1.0/applications/$OBJECT_ID" `
  --headers "Content-Type=application/json" `
  --body "@$env:TEMP\tokenver.json"
```

### 1.4 Adicionar o scope `access_as_user`

Este scope delegado permite que clientes solicitem tokens para esta API. Ele não concede acesso às ferramentas; isso é controlado exclusivamente pelas App Roles.

```powershell
$SCOPE_ID = [System.Guid]::NewGuid().ToString()
$body = @"
{
  "api": {
    "oauth2PermissionScopes": [{
      "adminConsentDescription": "Acessar mcp-lab como o usuário autenticado",
      "adminConsentDisplayName": "Acessar mcp-lab",
      "id": "$SCOPE_ID",
      "isEnabled": true,
      "type": "User",
      "userConsentDescription": "Acessar mcp-lab em seu nome",
      "userConsentDisplayName": "Acessar mcp-lab",
      "value": "access_as_user"
    }]
  }
}
"@
$body | Out-File "$env:TEMP\scope.json" -Encoding utf8 -NoNewline
az rest --method PATCH `
  --uri "https://graph.microsoft.com/v1.0/applications/$OBJECT_ID" `
  --headers "Content-Type=application/json" `
  --body "@$env:TEMP\scope.json"
```

### 1.5 Criar App Roles

As App Roles são atribuídas por administradores e aparecem no claim `roles` do JWT. Usuários não podem autoatribuí-las, sendo essa a diferença fundamental em relação a OAuth Scopes.

```powershell
$ROLE_READ_ID  = [System.Guid]::NewGuid().ToString()
$ROLE_ADMIN_ID = [System.Guid]::NewGuid().ToString()

$body = @"
{
  "appRoles": [
    {
      "allowedMemberTypes": ["User", "Application"],
      "description": "Acesso de leitura às ferramentas MCP",
      "displayName": "MCP Read",
      "id": "$ROLE_READ_ID",
      "isEnabled": true,
      "value": "mcp-trc-read"
    },
    {
      "allowedMemberTypes": ["User", "Application"],
      "description": "Acesso administrativo às ferramentas MCP",
      "displayName": "MCP Admin",
      "id": "$ROLE_ADMIN_ID",
      "isEnabled": true,
      "value": "mcp-trc-admin"
    }
  ]
}
"@
$body | Out-File "$env:TEMP\approles.json" -Encoding utf8 -NoNewline
az rest --method PATCH `
  --uri "https://graph.microsoft.com/v1.0/applications/$OBJECT_ID" `
  --headers "Content-Type=application/json" `
  --body "@$env:TEMP\approles.json"
```

### 1.6 Criar Service Principal e client secret

```powershell
az ad sp create --id $CLIENT_ID

$SECRET    = az ad app credential reset --id $CLIENT_ID --years 1 --query "password" -o tsv
$TENANT_ID = az account show --query tenantId -o tsv
```

> ⚠️ Em produção, o `client_secret` deve ser armazenado no Azure Key Vault e acessado via Managed Identity. Nunca persista em arquivos de configuração ou variáveis de ambiente em disco.

### 1.7 Conceder consentimento administrativo para `access_as_user`

```powershell
$SP_ID = az ad sp show --id $CLIENT_ID --query id -o tsv

$body = @"
{
  "clientId": "$SP_ID",
  "consentType": "AllPrincipals",
  "resourceId": "$SP_ID",
  "scope": "access_as_user"
}
"@
$body | Out-File "$env:TEMP\consent.json" -Encoding utf8 -NoNewline
az rest --method POST `
  --uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants" `
  --headers "Content-Type=application/json" `
  --body "@$env:TEMP\consent.json"
```

> ⚠️ `consentType: AllPrincipals` concede consentimento em nome de todos os usuários do tenant. Os usuários não verão tela de consentimento ao autenticar. Esta ação requer privilégios de Global Administrator ou Privileged Role Administrator.

## 👥 Passo 2: Grupos de Segurança no Azure AD

O acesso é gerenciado exclusivamente via grupos de segurança. Administradores adicionam ou removem usuários dos grupos sem qualquer alteração de código ou no App Registration.

### 2.1 Criar os grupos

```powershell
$GROUP_READ_ID  = (az rest --method POST --uri "https://graph.microsoft.com/v1.0/groups" `
  --headers "Content-Type=application/json" `
  --body '{"displayName":"mcp-trc-read","mailEnabled":false,"mailNickname":"mcp-trc-read","securityEnabled":true}' `
  -o json | ConvertFrom-Json).id

$GROUP_ADMIN_ID = (az rest --method POST --uri "https://graph.microsoft.com/v1.0/groups" `
  --headers "Content-Type=application/json" `
  --body '{"displayName":"mcp-trc-admin","mailEnabled":false,"mailNickname":"mcp-trc-admin","securityEnabled":true}' `
  -o json | ConvertFrom-Json).id
```

### 2.2 Atribuir App Roles aos grupos

```powershell
$body = "{`"principalId`":`"$GROUP_READ_ID`",`"resourceId`":`"$SP_ID`",`"appRoleId`":`"$ROLE_READ_ID`"}"
az rest --method POST `
  --uri "https://graph.microsoft.com/v1.0/groups/$GROUP_READ_ID/appRoleAssignments" `
  --headers "Content-Type=application/json" --body $body

$body = "{`"principalId`":`"$GROUP_ADMIN_ID`",`"resourceId`":`"$SP_ID`",`"appRoleId`":`"$ROLE_ADMIN_ID`"}"
az rest --method POST `
  --uri "https://graph.microsoft.com/v1.0/groups/$GROUP_ADMIN_ID/appRoleAssignments" `
  --headers "Content-Type=application/json" --body $body
```

Para verificar e gerenciar atribuições via portal:
**Azure AD → Enterprise Applications → mcp-lab → Users and groups**

### 2.3 Gerenciar membros dos grupos

```powershell
# Adicionar usuário ao grupo
$USER_OID = "<object-id-do-usuario>"
$body = "{`"@odata.id`":`"https://graph.microsoft.com/v1.0/directoryObjects/$USER_OID`"}"
az rest --method POST `
  --uri "https://graph.microsoft.com/v1.0/groups/$GROUP_ADMIN_ID/members/`$ref" `
  --headers "Content-Type=application/json" --body $body

# Remover usuário do grupo
az rest --method DELETE `
  --uri "https://graph.microsoft.com/v1.0/groups/$GROUP_ADMIN_ID/members/$USER_OID/`$ref"
```

> ⚠️ A revogação de acesso reflete no próximo token emitido, normalmente em até 1 hora. Para ambientes que exigem revogação imediata, avaliar Continuous Access Evaluation (CAE) do Entra ID.

## ⚙️ Passo 3: Configuração do projeto

### 3.1 Instalar dependências

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

### 3.2 Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env`:

```env
AZURE_CLIENT_ID=<client-id-do-app-registration>
AZURE_CLIENT_SECRET=<client-secret>
AZURE_TENANT_ID=<tenant-id>
MCP_BASE_URL=http://localhost:8000

# Modo de autenticação: jwt (padrão) | oauth
AUTH_MODE=jwt
```

> ⚠️ Nunca comite o arquivo `.env` no controle de versão. Adicione ao `.gitignore`. Em produção, use variáveis de ambiente do Azure Container Apps ou referências ao Key Vault. O `AZURE_CLIENT_SECRET` é necessário apenas no `AUTH_MODE=oauth`.

### 3.3 Executar

```bash
python -m app
```

O servidor sobe em `http://0.0.0.0:8000/mcp`.

## 🔑 Passo 4: Obter token para testes

```powershell
az login --tenant "<TENANT_ID>"

az account get-access-token `
  --scope "api://<CLIENT_ID>/access_as_user" `
  --query accessToken -o tsv
```

Utilize o token como header Bearer no cliente MCP:

```
Authorization: Bearer <token>
```

Os tokens expiram em aproximadamente 1 hora. Execute `az account get-access-token` novamente para renovar sem novo login.

## ➕ Adicionando novas ferramentas

Crie `app/tools/minha_ferramenta.py`:

```python
from fastmcp.tools.base import Tool
from ..auth import require_roles


def _minha_ferramenta(parametro: str) -> dict:
    """Descrição do que a ferramenta faz."""
    return {"resultado": parametro}


minha_ferramenta: Tool = Tool.from_function(
    _minha_ferramenta,
    name="minha_ferramenta",
    auth=require_roles("mcp-trc-read"),
)
```

Registre em `app/tools/__init__.py`:

```python
from .minha_ferramenta import minha_ferramenta

def register_tools(mcp: FastMCP) -> None:
    mcp.add_tool(health_check)
    mcp.add_tool(soma)
    mcp.add_tool(minha_ferramenta)
```

Nenhuma alteração na infraestrutura de autenticação é necessária.

## 🏭 Considerações para produção (Azure Container Apps)

O Azure Container Apps resolve automaticamente parte dos requisitos de segurança corporativa:

| Requisito | Solução no ACA |
|-----------|----------------|
| TLS/HTTPS | Ingress com certificado gerenciado automaticamente |
| Segredos | ACA Secrets ou Key Vault reference com Managed Identity |
| Logs | stdout capturado automaticamente pelo Log Analytics |
| Scaling | Configurável via regras de escala do ACA |

Variáveis de ambiente recomendadas no ACA (sem `.env`):

```
AZURE_CLIENT_ID     variável de ambiente do ACA
AZURE_TENANT_ID     variável de ambiente do ACA
MCP_BASE_URL        https://<seu-app>.azurecontainerapps.io
AUTH_MODE           jwt
AZURE_CLIENT_SECRET referência ao Key Vault (apenas se AUTH_MODE=oauth)
```

Para `AUTH_MODE=jwt` com Container Apps, o `AZURE_CLIENT_SECRET` não é utilizado na validação de tokens. O servidor aceita tokens JWT do Entra ID diretamente, incluindo tokens OBO (On-Behalf-Of) emitidos por serviços upstream como App Service com Managed Identity.

## ⚠️ Limitações conhecidas

- Revogação de acesso não é imediata: tokens emitidos antes da remoção do grupo permanecem válidos por até 1 hora.
- Apenas um modo de autenticação por instância: `AUTH_MODE=jwt` e `AUTH_MODE=oauth` não podem coexistir na mesma instância do servidor.
- Ausência de audit log nativo no servidor: logs de acesso dependem da infraestrutura de hospedagem (Azure Monitor recomendado).
- Tokens v1.0 são rejeitados: clientes que não suportam tokens v2.0 do Entra ID não conseguirão autenticar.

## ✅ Checklist de segurança

### Identidade e acesso

- [ ] App Registration com `signInAudience: AzureADMyOrg`, restringindo ao tenant corporativo
- [ ] `requestedAccessTokenVersion: 2`, com tokens v1.0 rejeitados pelo verifier
- [ ] App Roles atribuídas a grupos, não a indivíduos, com controle centralizado e auditável
- [ ] Consentimento administrativo concedido via `AllPrincipals`, sem prompts para usuários

### Validação de token

- [ ] Assinatura RS256 validada contra JWKS público do Entra
- [ ] Issuer validado: `login.microsoftonline.com/<tenant>/v2.0`
- [ ] Audience validado: `CLIENT_ID` da aplicação
- [ ] Presença obrigatória de role válida verificada na conexão

### Controle de acesso

- [ ] `RoleEnforcedJWTVerifier` rejeita conexão (401) antes de qualquer resposta MCP
- [ ] `auth=` por ferramenta filtra `tools/list`, impedindo que a LLM veja ferramentas não autorizadas
- [ ] `auth=` por ferramenta bloqueia `tools/call` em segunda camada de defesa

### Secrets e configuração

- [ ] Arquivo `.env` no `.gitignore`, com segredos nunca versionados
- [ ] Em produção: `client_secret` armazenado no Key Vault, não em variáveis de ambiente em texto plano
- [ ] Client secret com rotação definida (recomendado: anual ou semestral)

### Infraestrutura

- [ ] Servidor exposto somente via HTTPS em produção
- [ ] Container App em VNet privada com acesso restrito por NSG
- [ ] Logs roteados para Azure Monitor / Log Analytics
- [ ] Alertas configurados para tentativas de acesso com 401 repetidas

## 📚 Referências

- [Documentação do FastMCP](https://gofastmcp.com)
- [Integração FastMCP com Azure](https://gofastmcp.com/integrations/azure)
- [App Roles do Microsoft Entra ID](https://learn.microsoft.com/pt-br/entra/identity-platform/howto-add-app-roles-in-apps)
- [Continuous Access Evaluation (CAE)](https://learn.microsoft.com/pt-br/entra/identity/conditional-access/concept-continuous-access-evaluation)
- [On-Behalf-Of Flow do Entra ID](https://learn.microsoft.com/pt-br/entra/identity-platform/v2-oauth2-on-behalf-of-flow)
- [Azure Key Vault com Managed Identity](https://learn.microsoft.com/pt-br/azure/key-vault/general/overview)
- [Referência Azure CLI](https://learn.microsoft.com/pt-br/cli/azure/)
- [Microsoft Graph API para appRoleAssignments](https://learn.microsoft.com/pt-br/graph/api/serviceprincipal-post-approleassignments)
