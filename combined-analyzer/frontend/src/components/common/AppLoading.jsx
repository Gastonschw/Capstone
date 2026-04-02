import React from 'react';

const spinStyle = {
  width: '36px',
  height: '36px',
  border: '3px solid #e5e7eb',
  borderTopColor: '#1e3a5f',
  borderRadius: '50%',
  animation: 'app-loading-spin 0.75s linear infinite',
};

export default function AppLoading({
  message = 'Loading…',
  subMessage,
  fullScreen = true,
  className,
}) {
  const outer = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '14px',
    backgroundColor: '#f5f7fa',
    ...(fullScreen
      ? { minHeight: '100vh', width: '100%' }
      : { padding: '40px 24px', borderRadius: '12px' }),
  };

  return (
    <div style={outer} className={className} role="status" aria-live="polite" aria-busy="true">
      <style>{`
        @keyframes app-loading-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
      <div style={spinStyle} aria-hidden />
      <div style={{ textAlign: 'center' }}>
        <div style={{ color: '#374151', fontSize: '15px', fontWeight: '600' }}>{message}</div>
        {subMessage ? (
          <div style={{ color: '#6b7280', fontSize: '13px', marginTop: '6px', maxWidth: '320px', lineHeight: 1.5 }}>
            {subMessage}
          </div>
        ) : null}
      </div>
    </div>
  );
}
