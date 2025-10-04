import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Session, Message } from '@/types/chat';
import { v4 as uuidv4 } from 'uuid';

interface ChatState {
  sessions: Map<string, Session>;
  currentSessionId: string | null;

  // Actions
  createSession: (modelId: string, title?: string) => Session;
  deleteSession: (sessionId: string) => void;
  setCurrentSession: (sessionId: string) => void;
  addMessage: (sessionId: string, message: Message) => void;
  updateMessage: (
    sessionId: string,
    messageId: string,
    updates: Partial<Message>
  ) => void;
  clearHistory: (sessionId: string) => void;
  exportSession: (
    sessionId: string,
    format: 'json' | 'markdown'
  ) => Promise<Blob>;
  getAllSessions: () => Session[];
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: new Map(),
      currentSessionId: null,

      createSession: (modelId: string, title?: string) => {
        const session: Session = {
          id: uuidv4(),
          modelId,
          title: title || '新对话',
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          metadata: {
            tags: [],
            tokens: 0,
            cost: 0,
          },
        };

        set((state) => ({
          sessions: new Map(state.sessions).set(session.id, session),
          currentSessionId: session.id,
        }));

        return session;
      },

      deleteSession: (sessionId: string) => {
        set((state) => {
          const newSessions = new Map(state.sessions);
          newSessions.delete(sessionId);

          const newCurrentId =
            state.currentSessionId === sessionId
              ? Array.from(newSessions.keys())[0] || null
              : state.currentSessionId;

          return {
            sessions: newSessions,
            currentSessionId: newCurrentId,
          };
        });
      },

      setCurrentSession: (sessionId: string) => {
        set({ currentSessionId: sessionId });
      },

      addMessage: (sessionId: string, message: Message) => {
        set((state) => {
          const session = state.sessions.get(sessionId);
          if (!session) return state;

          const updatedSession = {
            ...session,
            messages: [...session.messages, message],
            updatedAt: new Date(),
            metadata: {
              ...session.metadata,
              tokens: session.metadata.tokens + (message.tokens || 0),
            },
          };

          return {
            sessions: new Map(state.sessions).set(sessionId, updatedSession),
          };
        });
      },

      updateMessage: (
        sessionId: string,
        messageId: string,
        updates: Partial<Message>
      ) => {
        set((state) => {
          const session = state.sessions.get(sessionId);
          if (!session) return state;

          const messages = session.messages.map((msg) =>
            msg.id === messageId ? { ...msg, ...updates } : msg
          );

          const updatedSession = {
            ...session,
            messages,
            updatedAt: new Date(),
          };

          return {
            sessions: new Map(state.sessions).set(sessionId, updatedSession),
          };
        });
      },

      clearHistory: (sessionId: string) => {
        set((state) => {
          const session = state.sessions.get(sessionId);
          if (!session) return state;

          const clearedSession = {
            ...session,
            messages: [],
            updatedAt: new Date(),
            metadata: { ...session.metadata, tokens: 0, cost: 0 },
          };

          return {
            sessions: new Map(state.sessions).set(sessionId, clearedSession),
          };
        });
      },

      exportSession: async (
        sessionId: string,
        format: 'json' | 'markdown'
      ) => {
        const session = get().sessions.get(sessionId);
        if (!session) throw new Error('会话不存在');

        if (format === 'json') {
          return new Blob([JSON.stringify(session, null, 2)], {
            type: 'application/json',
          });
        } else {
          const markdown = session.messages
            .map(
              (msg) =>
                `**${msg.role === 'user' ? '用户' : '助手'}** (${new Date(msg.timestamp).toLocaleString()}):\n\n${msg.content}\n\n---\n`
            )
            .join('\n');

          return new Blob([markdown], { type: 'text/markdown' });
        }
      },

      getAllSessions: () => {
        return Array.from(get().sessions.values());
      },
    }),
    {
      name: 'chat-storage',
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name);
          if (!str) return null;
          const parsed = JSON.parse(str);
          return {
            state: {
              ...parsed.state,
              sessions: new Map(parsed.state.sessions || []),
            },
            version: parsed.version,
          };
        },
        setItem: (name, value) => {
          const toStore = {
            state: {
              ...value.state,
              sessions: Array.from(value.state.sessions.entries()),
            },
            version: value.version,
          };
          localStorage.setItem(name, JSON.stringify(toStore));
        },
        removeItem: (name) => localStorage.removeItem(name),
      },
    }
  )
);
