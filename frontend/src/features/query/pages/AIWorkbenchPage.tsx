/**
 * AI Workbench (lives at `/app/query`)
 *
 * Tabbed wrapper that **preserves the existing QueryPage byte-for-byte**
 * as the first ("Ask") tab and adds three new configuration tabs:
 *
 *   1. Ask         — natural-language query (the existing QueryPage)
 *   2. Agent       — system prompt, default model, enabled MCP tools
 *   3. MCP Servers — register / health-check / refresh MCP servers
 *   4. Ollama      — runtime config + model pulls
 *
 * The "Ask" tab embeds <QueryPage/> unchanged so existing NL-query
 * behaviour cannot regress. Routing in App.tsx points `/app/query` at
 * this component instead of QueryPage directly.
 */

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Bot, Server, Sparkles, Wrench } from 'lucide-react'

import { QueryPage } from './QueryPage'
import { AgentConfigTab } from '../components/AgentConfigTab'
import { MCPServersTab } from '../components/MCPServersTab'
import { OllamaConfigTab } from '../components/OllamaConfigTab'

export function AIWorkbenchPage() {
  return (
    <div className="container py-6">
      <Tabs defaultValue="ask" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="ask">
            <Sparkles className="mr-1.5 h-4 w-4" />
            Ask
          </TabsTrigger>
          <TabsTrigger value="agent">
            <Bot className="mr-1.5 h-4 w-4" />
            Agent
          </TabsTrigger>
          <TabsTrigger value="mcp">
            <Server className="mr-1.5 h-4 w-4" />
            MCP Servers
          </TabsTrigger>
          <TabsTrigger value="ollama">
            <Wrench className="mr-1.5 h-4 w-4" />
            Ollama
          </TabsTrigger>
        </TabsList>

        <TabsContent value="ask">
          {/* Existing QueryPage is rendered unchanged so the NL-query
              experience is preserved byte-for-byte. */}
          <QueryPage />
        </TabsContent>

        <TabsContent value="agent">
          <div className="max-w-3xl">
            <AgentConfigTab />
          </div>
        </TabsContent>

        <TabsContent value="mcp">
          <div className="max-w-4xl">
            <MCPServersTab />
          </div>
        </TabsContent>

        <TabsContent value="ollama">
          <div className="max-w-3xl">
            <OllamaConfigTab />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default AIWorkbenchPage
