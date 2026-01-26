# AI Integration Agent

## ⚙️ Configuration

```yaml
preferred_model: opus 4.5
required_tools:
  - read_file
  - create_file
  - replace_string_in_file
  - list_dir
  - file_search
  - grep_search
  - semantic_search
  - fetch_webpage
```

## 🎯 Role

You are the **AI Integration Agent** for NovaSight. You handle Ollama LLM integration, natural language to SQL generation, AI guardrails, and chat interface.

## 🧠 Expertise

- Ollama API integration
- Prompt engineering
- SQL generation from natural language
- Context management
- Security guardrails
- RLS enforcement
- Conversation memory

## 📋 Component Ownership

**Component 12: AI Integration**
- Ollama integration service
- Dynamic prompt builder
- SQL generation service
- SQL validation service
- RLS injection layer
- Conversation memory
- AI chat UI
- SQL preview panel
- AI guardrails config UI

## 📁 Project Structure

### Backend
```
backend/app/
├── api/v1/
│   └── ai.py                    # AI endpoints
├── services/
│   ├── ai_service.py            # AI orchestration
│   ├── ollama_client.py         # Ollama API client
│   ├── prompt_builder.py        # Context-aware prompts
│   ├── sql_validator.py         # SQL validation
│   └── conversation_memory.py   # Chat history
├── schemas/
│   └── ai_schemas.py            # AI Pydantic schemas
└── models/
    └── ai_conversation.py       # Conversation models
```

### Frontend
```
frontend/src/
├── pages/explore/
│   └── AiChatPage.tsx
├── components/ai/
│   ├── ChatInterface.tsx
│   ├── MessageBubble.tsx
│   ├── SqlPreviewPanel.tsx
│   ├── ResultsPanel.tsx
│   └── SuggestionChips.tsx
├── hooks/
│   └── useAiChat.ts
└── services/
    └── aiService.ts
```

## 🔧 Core Implementation

### Ollama Client
```python
# backend/app/services/ollama_client.py
import httpx
from typing import AsyncGenerator, Dict, Any, Optional
from dataclasses import dataclass
import json

@dataclass
class OllamaConfig:
    host: str = "ollama"
    port: int = 11434
    model: str = "codellama:13b"
    temperature: float = 0.1
    max_tokens: int = 2048

class OllamaClient:
    """Client for Ollama LLM API."""
    
    def __init__(self, config: OllamaConfig):
        self.config = config
        self.base_url = f"http://{config.host}:{config.port}"
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        stream: bool = False
    ) -> str:
        """Generate completion from prompt."""
        
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": stream,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            }
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            if stream:
                return self._stream_generate(client, payload)
            else:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                return response.json()["response"]
    
    async def _stream_generate(
        self,
        client: httpx.AsyncClient,
        payload: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Stream generation token by token."""
        
        async with client.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                    if data.get("done"):
                        break
    
    async def health_check(self) -> bool:
        """Check if Ollama is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
```

### Dynamic Prompt Builder
```python
# backend/app/services/prompt_builder.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TableInfo:
    name: str
    description: str
    columns: List[Dict[str, str]]  # name, type, description

@dataclass
class PromptContext:
    tenant_name: str
    available_tables: List[TableInfo]
    user_attributes: Dict[str, Any]  # For RLS context
    conversation_history: List[Dict[str, str]]
    custom_instructions: Optional[str] = None

class PromptBuilder:
    """Builds context-aware prompts for SQL generation."""
    
    SYSTEM_PROMPT_TEMPLATE = """You are a SQL assistant for {tenant_name}'s data analytics platform.

CRITICAL RULES:
1. ONLY generate SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, or any DDL/DML.
2. ONLY use tables and columns from the provided schema.
3. NEVER access system tables or information_schema.
4. NEVER use subqueries that access tables not in the schema.
5. Always use explicit column names, never SELECT *.
6. Limit results to 10000 rows maximum.
7. Format your response as ONLY the SQL query, no explanations.

AVAILABLE TABLES AND COLUMNS:
{schema_context}

{custom_instructions}

When generating SQL:
- Use ClickHouse SQL dialect
- Use proper date functions (toDate, toDateTime, toStartOfMonth, etc.)
- Use appropriate aggregations
- Add ORDER BY when relevant
- Always include a LIMIT clause
"""

    SQL_EXTRACTION_PROMPT = """Based on the user's question and conversation history, generate a SQL query.

CONVERSATION HISTORY:
{history}

USER QUESTION: {question}

Generate ONLY the SQL query, nothing else."""

    def build_system_prompt(self, context: PromptContext) -> str:
        """Build the system prompt with schema context."""
        
        schema_context = self._format_schema(context.available_tables)
        custom = context.custom_instructions or ""
        
        return self.SYSTEM_PROMPT_TEMPLATE.format(
            tenant_name=context.tenant_name,
            schema_context=schema_context,
            custom_instructions=custom
        )
    
    def build_user_prompt(
        self,
        question: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """Build the user prompt with history."""
        
        history = self._format_history(conversation_history)
        
        return self.SQL_EXTRACTION_PROMPT.format(
            history=history,
            question=question
        )
    
    def _format_schema(self, tables: List[TableInfo]) -> str:
        """Format table schema for prompt."""
        
        lines = []
        for table in tables:
            lines.append(f"\nTABLE: {table.name}")
            if table.description:
                lines.append(f"  Description: {table.description}")
            lines.append("  Columns:")
            for col in table.columns:
                desc = f" - {col['description']}" if col.get('description') else ""
                lines.append(f"    - {col['name']} ({col['type']}){desc}")
        
        return "\n".join(lines)
    
    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history."""
        
        if not history:
            return "No previous conversation."
        
        lines = []
        for msg in history[-5:]:  # Last 5 messages
            role = msg["role"].upper()
            content = msg["content"][:500]  # Truncate
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
```

### SQL Validator
```python
# backend/app/services/sql_validator.py
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Parenthesis
from sqlparse.tokens import Keyword, DML
from typing import List, Set, Tuple, Optional
import re

class SQLValidationError(Exception):
    """Raised when SQL validation fails."""
    pass

class SQLValidator:
    """Validates and sanitizes AI-generated SQL."""
    
    FORBIDDEN_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'GRANT', 'REVOKE', 'EXECUTE', 'EXEC',
        'INTO', 'SET', 'MERGE', 'ATTACH', 'DETACH'
    }
    
    FORBIDDEN_FUNCTIONS = {
        'SLEEP', 'BENCHMARK', 'LOAD_FILE', 'INTO OUTFILE',
        'INTO DUMPFILE', 'system', 'file', 'url'
    }
    
    FORBIDDEN_PATTERNS = [
        r';\s*\w',              # Multiple statements
        r'--',                   # SQL comments (potential injection)
        r'/\*',                  # Block comments
        r'information_schema',   # System tables
        r'system\.',             # ClickHouse system tables
        r'@@',                   # System variables
    ]
    
    def __init__(self, allowed_tables: Set[str]):
        self.allowed_tables = {t.lower() for t in allowed_tables}
    
    def validate(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL query.
        Returns (is_valid, error_message)
        """
        try:
            # Check for forbidden patterns
            self._check_forbidden_patterns(sql)
            
            # Parse SQL
            parsed = sqlparse.parse(sql)
            if not parsed:
                return False, "Could not parse SQL"
            
            statement = parsed[0]
            
            # Must be SELECT
            if statement.get_type() != 'SELECT':
                return False, "Only SELECT statements are allowed"
            
            # Check for forbidden keywords
            self._check_forbidden_keywords(statement)
            
            # Check for forbidden functions
            self._check_forbidden_functions(sql)
            
            # Extract and validate table references
            tables = self._extract_tables(statement)
            unauthorized = tables - self.allowed_tables
            if unauthorized:
                return False, f"Unauthorized tables: {', '.join(unauthorized)}"
            
            return True, None
            
        except SQLValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _check_forbidden_patterns(self, sql: str):
        """Check for forbidden regex patterns."""
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                raise SQLValidationError(f"Forbidden pattern detected: {pattern}")
    
    def _check_forbidden_keywords(self, statement):
        """Check for forbidden SQL keywords."""
        for token in statement.flatten():
            if token.ttype in (Keyword, DML):
                if token.value.upper() in self.FORBIDDEN_KEYWORDS:
                    raise SQLValidationError(f"Forbidden keyword: {token.value}")
    
    def _check_forbidden_functions(self, sql: str):
        """Check for forbidden SQL functions."""
        sql_upper = sql.upper()
        for func in self.FORBIDDEN_FUNCTIONS:
            if func.upper() in sql_upper:
                raise SQLValidationError(f"Forbidden function: {func}")
    
    def _extract_tables(self, statement) -> Set[str]:
        """Extract table names from SQL statement."""
        tables = set()
        
        from_seen = False
        for token in statement.tokens:
            if token.ttype is Keyword and token.value.upper() == 'FROM':
                from_seen = True
            elif from_seen:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        tables.add(self._get_table_name(identifier))
                elif isinstance(token, Identifier):
                    tables.add(self._get_table_name(token))
                elif token.ttype is Keyword and token.value.upper() in ('WHERE', 'GROUP', 'ORDER', 'LIMIT'):
                    from_seen = False
            
            # Handle JOINs
            if token.ttype is Keyword and 'JOIN' in token.value.upper():
                from_seen = True
        
        return {t for t in tables if t}
    
    def _get_table_name(self, identifier) -> str:
        """Extract table name from identifier."""
        if isinstance(identifier, Identifier):
            return identifier.get_real_name().lower()
        return str(identifier).strip().lower()
```

### RLS Injection Service
```python
# backend/app/services/rls_service.py
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class RLSPolicy:
    table_name: str
    filter_column: str
    filter_expression: str  # SQL expression

class RLSInjector:
    """Injects RLS filters into SQL queries."""
    
    MAX_ROWS = 10000
    
    def inject_rls(
        self,
        sql: str,
        policies: List[RLSPolicy],
        user_context: dict
    ) -> str:
        """Wrap SQL with RLS filters."""
        
        if not policies:
            return self._add_limit(sql)
        
        # Build RLS conditions
        conditions = []
        for policy in policies:
            # Substitute user context into expression
            expr = policy.filter_expression
            for key, value in user_context.items():
                expr = expr.replace(f"{{{{ {key} }}}}", f"'{value}'")
            conditions.append(f"({expr})")
        
        rls_where = " AND ".join(conditions)
        
        # Wrap query with RLS
        wrapped = f"""
SELECT * FROM (
    {sql.rstrip(';')}
) AS user_query
WHERE {rls_where}
LIMIT {self.MAX_ROWS}
"""
        return wrapped
    
    def _add_limit(self, sql: str) -> str:
        """Add LIMIT if not present."""
        sql_upper = sql.upper()
        if 'LIMIT' not in sql_upper:
            return f"{sql.rstrip(';')} LIMIT {self.MAX_ROWS}"
        return sql
```

### AI Service (Orchestrator)
```python
# backend/app/services/ai_service.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from app.services.ollama_client import OllamaClient, OllamaConfig
from app.services.prompt_builder import PromptBuilder, PromptContext, TableInfo
from app.services.sql_validator import SQLValidator
from app.services.rls_service import RLSInjector, RLSPolicy
from app.services.query_service import QueryService
from app.models import Conversation, Message, AuditLog
from app.extensions import db

@dataclass
class ChatResponse:
    message: str
    sql: Optional[str]
    results: Optional[List[Dict]]
    row_count: Optional[int]
    execution_time_ms: Optional[float]
    suggestions: List[str]

class AIService:
    """Orchestrates AI chat with data functionality."""
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        prompt_builder: PromptBuilder,
        query_service: QueryService,
        rls_injector: RLSInjector
    ):
        self.ollama = ollama_client
        self.prompt_builder = prompt_builder
        self.query_service = query_service
        self.rls_injector = rls_injector
    
    async def chat(
        self,
        question: str,
        tenant_id: str,
        user_id: int,
        conversation_id: Optional[str] = None
    ) -> ChatResponse:
        """Process a chat message and return response."""
        
        # Get or create conversation
        conversation = self._get_or_create_conversation(
            conversation_id, tenant_id, user_id
        )
        
        # Build context
        context = await self._build_context(tenant_id, user_id, conversation)
        
        # Generate SQL
        system_prompt = self.prompt_builder.build_system_prompt(context)
        user_prompt = self.prompt_builder.build_user_prompt(
            question,
            [{"role": m.role, "content": m.content} for m in conversation.messages]
        )
        
        generated_sql = await self.ollama.generate(user_prompt, system_prompt)
        generated_sql = self._clean_sql(generated_sql)
        
        # Validate SQL
        allowed_tables = {t.name for t in context.available_tables}
        validator = SQLValidator(allowed_tables)
        is_valid, error = validator.validate(generated_sql)
        
        if not is_valid:
            # Log failed attempt
            self._log_ai_query(user_id, question, generated_sql, None, error)
            return ChatResponse(
                message=f"I couldn't generate a valid query: {error}",
                sql=generated_sql,
                results=None,
                row_count=None,
                execution_time_ms=None,
                suggestions=["Try rephrasing your question", "Be more specific about the data you want"]
            )
        
        # Apply RLS
        policies = await self._get_rls_policies(tenant_id, user_id)
        user_context = await self._get_user_context(user_id)
        final_sql = self.rls_injector.inject_rls(generated_sql, policies, user_context)
        
        # Execute query
        try:
            start_time = datetime.utcnow()
            results = await self.query_service.execute(final_sql, tenant_id)
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Save messages
            self._save_message(conversation, "user", question)
            self._save_message(conversation, "assistant", f"Query executed successfully. Found {len(results)} rows.")
            
            # Log successful query
            self._log_ai_query(user_id, question, generated_sql, len(results), None)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(question, results)
            
            return ChatResponse(
                message=f"Found {len(results)} rows.",
                sql=generated_sql,  # Show original, not RLS-wrapped
                results=results[:1000],  # Limit response size
                row_count=len(results),
                execution_time_ms=execution_time,
                suggestions=suggestions
            )
            
        except Exception as e:
            self._log_ai_query(user_id, question, generated_sql, None, str(e))
            return ChatResponse(
                message=f"Query execution failed: {str(e)}",
                sql=generated_sql,
                results=None,
                row_count=None,
                execution_time_ms=None,
                suggestions=["Check if the referenced columns exist", "Try a simpler query"]
            )
    
    def _clean_sql(self, sql: str) -> str:
        """Clean generated SQL."""
        # Remove markdown code blocks
        sql = sql.replace("```sql", "").replace("```", "")
        # Remove leading/trailing whitespace
        sql = sql.strip()
        return sql
    
    def _generate_suggestions(self, question: str, results: List[Dict]) -> List[str]:
        """Generate follow-up question suggestions."""
        suggestions = []
        
        if len(results) > 0:
            suggestions.append("Show me a breakdown by category")
            suggestions.append("What's the trend over time?")
            suggestions.append("Compare this with last period")
        else:
            suggestions.append("Try a broader date range")
            suggestions.append("Check for different filter values")
        
        return suggestions[:3]
    
    async def _build_context(
        self,
        tenant_id: str,
        user_id: int,
        conversation: Conversation
    ) -> PromptContext:
        """Build prompt context from tenant and user."""
        
        # Get available tables (filtered by user permissions)
        tables = await self._get_accessible_tables(tenant_id, user_id)
        user_attrs = await self._get_user_context(user_id)
        
        return PromptContext(
            tenant_name=tenant_id,
            available_tables=tables,
            user_attributes=user_attrs,
            conversation_history=[
                {"role": m.role, "content": m.content}
                for m in conversation.messages[-10:]
            ]
        )
    
    # ... additional helper methods
```

## 📝 Implementation Tasks

### Task 12.1: Ollama Integration Service
```yaml
Priority: P0
Effort: 2 days

Steps:
1. Create Ollama client
2. Implement generate endpoint
3. Add streaming support
4. Implement health check
5. Add configuration

Acceptance Criteria:
- [ ] Can connect to Ollama
- [ ] Generation works
- [ ] Streaming works
```

### Task 12.2: Dynamic Prompt Builder
```yaml
Priority: P0
Effort: 3 days

Steps:
1. Create prompt templates
2. Implement schema formatting
3. Add conversation history
4. Add tenant customization
5. Test prompt quality

Acceptance Criteria:
- [ ] Context-aware prompts
- [ ] Includes schema
- [ ] Respects history
```

### Task 12.4: SQL Validation Service
```yaml
Priority: P0
Effort: 2 days

Steps:
1. Implement SQL parsing
2. Add forbidden keyword checks
3. Add table extraction
4. Add pattern validation
5. Create comprehensive tests

Acceptance Criteria:
- [ ] Rejects non-SELECT
- [ ] Rejects unauthorized tables
- [ ] Rejects injection attempts
```

### Task 12.5: RLS Injection Layer
```yaml
Priority: P0
Effort: 2 days

Steps:
1. Implement RLS policy model
2. Create injection logic
3. Handle user context
4. Add LIMIT enforcement
5. Test edge cases

Acceptance Criteria:
- [ ] RLS filters applied
- [ ] User context resolved
- [ ] Cannot bypass RLS
```

### Task 12.7: AI Chat UI
```yaml
Priority: P0
Effort: 4 days

Steps:
1. Create chat interface
2. Implement message bubbles
3. Add SQL preview panel
4. Add results display
5. Implement suggestions
6. Add streaming display

Acceptance Criteria:
- [ ] Chat works smoothly
- [ ] SQL visible
- [ ] Results display correctly
- [ ] Suggestions clickable
```

## 🔗 References

- [Architecture Decisions - ADR-004](../../docs/requirements/Architecture_Decisions.md#adr-004-ai-integration-architecture)
- [BRD - Epic 6](../../docs/requirements/BRD_Part3.md)
- Ollama documentation
- sqlparse documentation

---

*AI Integration Agent v1.0 - NovaSight Project*
