import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { sendChatMessage } from '../../api';

const styles = {
  container: {
    marginTop: '24px',
    backgroundColor: '#fff',
    borderRadius: '12px',
    border: '1px solid #e0e0e0',
    overflow: 'hidden',
  },
  header: {
    backgroundColor: '#f8f9fa',
    padding: '14px 20px',
    borderBottom: '1px solid #e0e0e0',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  headerIcon: {
    fontSize: '18px',
  },
  headerTitle: {
    fontWeight: '600',
    fontSize: '15px',
    color: '#333',
  },
  messagesContainer: {
    maxHeight: '400px',
    overflowY: 'auto',
    padding: '16px',
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px 20px',
    color: '#888',
  },
  emptyTitle: {
    fontSize: '15px',
    fontWeight: '500',
    marginBottom: '8px',
    color: '#666',
  },
  emptyText: {
    fontSize: '13px',
  },
  message: {
    marginBottom: '16px',
    display: 'flex',
    flexDirection: 'column',
  },
  userMessage: {
    alignItems: 'flex-end',
  },
  assistantMessage: {
    alignItems: 'flex-start',
  },
  messageLabel: {
    fontSize: '11px',
    color: '#888',
    marginBottom: '4px',
    textTransform: 'uppercase',
    fontWeight: '500',
  },
  messageBubble: {
    padding: '12px 16px',
    borderRadius: '12px',
    maxWidth: '85%',
    fontSize: '14px',
    lineHeight: '1.5',
    wordBreak: 'break-word',
  },
  userBubble: {
    backgroundColor: '#1e3a5f',
    color: '#fff',
    borderBottomRightRadius: '4px',
  },
  assistantBubble: {
    backgroundColor: '#f0f4f8',
    color: '#333',
    borderBottomLeftRadius: '4px',
  },
  inputContainer: {
    padding: '16px',
    borderTop: '1px solid #e0e0e0',
    display: 'flex',
    gap: '10px',
  },
  input: {
    flex: 1,
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid #ddd',
    fontSize: '14px',
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  inputFocused: {
    borderColor: '#1e3a5f',
  },
  sendButton: {
    padding: '12px 24px',
    backgroundColor: '#1e3a5f',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  sendButtonDisabled: {
    backgroundColor: '#ccc',
    cursor: 'not-allowed',
  },
  loadingIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    backgroundColor: '#f0f4f8',
    borderRadius: '12px',
    borderBottomLeftRadius: '4px',
    fontSize: '13px',
    color: '#666',
  },
  loadingDots: {
    display: 'flex',
    gap: '4px',
  },
  dot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#1e3a5f',
    animation: 'bounce 1.4s infinite ease-in-out',
  },
};

// Strip <think> tags and their content from the response
function stripThinkTags(content) {
  if (!content) return '';
  // Remove <think>...</think> blocks (including multiline)
  return content.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
}

export default function AnalysisChat({ analysisId, analysisType, chatModel, chatApiKey }) {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const messagesContainerRef = useRef(null);
  const forceScrollOnNextUpdateRef = useRef(false);

  const scrollToBottom = (smooth = true) => {
    const container = messagesContainerRef.current;
    if (!container) return;
    container.scrollTo({
      top: container.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto',
    });
  };

  const handleMessagesScroll = () => {
    const el = messagesContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setIsNearBottom(distanceFromBottom < 80);
  };

  useEffect(() => {
    if (forceScrollOnNextUpdateRef.current || isNearBottom) {
      scrollToBottom(forceScrollOnNextUpdateRef.current);
      forceScrollOnNextUpdateRef.current = false;
    }
  }, [messages, isNearBottom]);

  const handleSend = async () => {
    const trimmedMessage = inputValue.trim();
    if (!trimmedMessage || isLoading) return;

    // Add user message
    const userMessage = { role: 'user', content: trimmedMessage };
    forceScrollOnNextUpdateRef.current = true;
    setIsNearBottom(true);
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // Prepare history (all previous messages)
    const history = messages;

    // Create placeholder for assistant message
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    // Stream the response
    await sendChatMessage(
      analysisType,
      analysisId,
      trimmedMessage,
      history,
      chatModel,
      chatApiKey,
      (chunk) => {
        // Update the last message with new chunk
        setMessages(prev => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          updated[lastIdx] = {
            ...updated[lastIdx],
            content: updated[lastIdx].content + chunk,
          };
          return updated;
        });
      },
      () => {
        // Done
        setIsLoading(false);
      },
      (error) => {
        // Error: show backend message (e.g. "TAMU API key is not configured") when available
        const message = error?.message || 'Sorry, an error occurred. Please try again.';
        setMessages(prev => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          updated[lastIdx] = {
            ...updated[lastIdx],
            content: updated[lastIdx].content || message,
          };
          return updated;
        });
        setIsLoading(false);
      }
    );
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestionMap = {
    erd: [
      'What entities are missing from my ERD?',
      'How can I improve the coverage score?',
      'Explain the relationship issues found.',
    ],
    integrity: [
      'What are the most critical security issues?',
      'How can I improve authentication?',
      'Explain the confidentiality findings.',
    ],
    compliance: [
      'Are all required functions implemented?',
      'What functional gaps were identified?',
      'How can I improve functional completeness?',
    ],
    correctness: [
      'Are there any off-by-one errors?',
      'What accuracy issues were found?',
      'How can I improve computation correctness?',
    ],
    usability: [
      'What accessibility issues were found?',
      'How can I improve error protection?',
      'What are the main operability concerns?',
    ],
    maintainability: [
      'How modular is the codebase?',
      'What are the main testability concerns?',
      'How can I improve code reusability?',
    ],
  };
  const suggestionQuestions = suggestionMap[analysisType] || suggestionMap.integrity;

  return (
    <div style={styles.container}>
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-6px); }
        }
        .dot-1 { animation-delay: 0s; }
        .dot-2 { animation-delay: 0.2s; }
        .dot-3 { animation-delay: 0.4s; }
        .markdown-content p { margin: 0 0 8px 0; }
        .markdown-content p:last-child { margin-bottom: 0; }
        .markdown-content ul, .markdown-content ol {
          margin: 8px 0;
          padding-left: 24px;
          list-style-position: outside;
        }
        .markdown-content ul { list-style-type: disc; }
        .markdown-content ol { list-style-type: decimal; }
        .markdown-content li {
          margin: 4px 0;
          display: list-item;
        }
        .markdown-content table {
          border-collapse: collapse;
          margin: 8px 0;
          width: 100%;
        }
        .markdown-content th, .markdown-content td {
          border: 1px solid #ddd;
          padding: 8px;
          text-align: left;
        }
        .markdown-content th {
          background-color: rgba(0,0,0,0.05);
        }
        .markdown-content code {
          background-color: rgba(0,0,0,0.1);
          padding: 2px 6px;
          border-radius: 4px;
          font-family: monospace;
          font-size: 13px;
        }
        .markdown-content pre {
          background-color: rgba(0,0,0,0.1);
          padding: 12px;
          border-radius: 6px;
          overflow-x: auto;
          margin: 8px 0;
        }
        .markdown-content pre code {
          background: none;
          padding: 0;
        }
        .markdown-content strong { font-weight: 600; }
        .markdown-content h1, .markdown-content h2, .markdown-content h3 {
          margin: 12px 0 8px 0;
          font-weight: 600;
        }
        .markdown-content h1 { font-size: 18px; }
        .markdown-content h2 { font-size: 16px; }
        .markdown-content h3 { font-size: 15px; }
      `}</style>

      <div style={styles.header}>
        <span style={styles.headerIcon}>&#128172;</span>
        <span style={styles.headerTitle}>Ask about this analysis</span>
      </div>

      <div
        ref={messagesContainerRef}
        style={styles.messagesContainer}
        onScroll={handleMessagesScroll}
      >
        {messages.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyTitle}>Start a conversation</div>
            <div style={styles.emptyText}>
              Ask questions about the analysis results. Try:
              <div style={{ marginTop: '12px' }}>
                {suggestionQuestions.map((q, i) => (
                  <div
                    key={i}
                    onClick={() => setInputValue(q)}
                    style={{
                      padding: '8px 12px',
                      margin: '6px 0',
                      backgroundColor: '#f0f4f8',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '13px',
                      color: '#1e3a5f',
                    }}
                  >
                    "{q}"
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  ...styles.message,
                  ...(msg.role === 'user' ? styles.userMessage : styles.assistantMessage),
                }}
              >
                <div style={styles.messageLabel}>
                  {msg.role === 'user' ? 'You' : 'Assistant'}
                </div>
                <div
                  style={{
                    ...styles.messageBubble,
                    ...(msg.role === 'user' ? styles.userBubble : styles.assistantBubble),
                  }}
                >
                  {msg.content ? (
                    msg.role === 'assistant' ? (
                      <div className="markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{stripThinkTags(msg.content)}</ReactMarkdown>
                      </div>
                    ) : (
                      msg.content
                    )
                  ) : (
                    <div style={styles.loadingIndicator}>
                      <div style={styles.loadingDots}>
                        <div className="dot-1" style={styles.dot}></div>
                        <div className="dot-2" style={styles.dot}></div>
                        <div className="dot-3" style={styles.dot}></div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </>
        )}
      </div>

      <div style={styles.inputContainer}>
        <input
          type="text"
          placeholder="Ask a question about this analysis..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setInputFocused(true)}
          onBlur={() => setInputFocused(false)}
          style={{
            ...styles.input,
            ...(inputFocused ? styles.inputFocused : {}),
          }}
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={!inputValue.trim() || isLoading}
          style={{
            ...styles.sendButton,
            ...((!inputValue.trim() || isLoading) ? styles.sendButtonDisabled : {}),
          }}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
}
