'use client';

import { useEffect, useState } from 'react';

const HACKER_CHARS = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
const LOADING_MESSAGES = [
  'Initializing secure connection...',
  'Decrypting data streams...',
  'Establishing encrypted tunnel...',
  'Loading system modules...',
  'Fetching device telemetry...',
  'Parsing security logs...',
  'Syncing with cloud...',
  'Verifying integrity...',
];

export function HackerLoader({ message }: { message?: string }) {
  const [displayText, setDisplayText] = useState('');
  const [currentMessage, setCurrentMessage] = useState(message || LOADING_MESSAGES[0]);
  const [glitchText, setGlitchText] = useState<string[]>([]);

  useEffect(() => {
    if (!message) {
      const interval = setInterval(() => {
        setCurrentMessage(LOADING_MESSAGES[Math.floor(Math.random() * LOADING_MESSAGES.length)]);
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [message]);

  useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      if (index <= currentMessage.length) {
        setDisplayText(currentMessage.slice(0, index));
        index++;
      } else {
        index = 0;
      }
    }, 50);
    return () => clearInterval(interval);
  }, [currentMessage]);

  useEffect(() => {
    const interval = setInterval(() => {
      const lines = [];
      for (let i = 0; i < 5; i++) {
        let line = '';
        for (let j = 0; j < 30; j++) {
          line += HACKER_CHARS[Math.floor(Math.random() * HACKER_CHARS.length)];
        }
        lines.push(line);
      }
      setGlitchText(lines);
    }, 100);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center h-64 relative overflow-hidden">
      {/* Matrix-style background text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center opacity-10 dark:opacity-20 overflow-hidden pointer-events-none">
        {glitchText.map((line, i) => (
          <div
            key={i}
            className="text-xs font-mono text-green-500 dark:text-red-500 tracking-widest whitespace-nowrap"
            style={{ animationDelay: `${i * 0.1}s` }}
          >
            {line}
          </div>
        ))}
      </div>

      {/* Main loader */}
      <div className="relative z-10 flex flex-col items-center gap-6">
        {/* Spinning ring with glitch effect */}
        <div className="relative">
          <div className="w-16 h-16 border-4 border-red-500/20 dark:border-red-500/30 rounded-full" />
          <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-t-red-500 rounded-full animate-spin" />
          <div className="absolute inset-2 w-12 h-12 border-2 border-transparent border-b-red-400 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.8s' }} />

          {/* Center pulse */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-4 h-4 bg-red-500 rounded-full animate-pulse shadow-lg shadow-red-500/50" />
          </div>
        </div>

        {/* Terminal-style text */}
        <div className="text-center space-y-2">
          <div className="font-mono text-sm text-gray-600 dark:text-[#888] flex items-center gap-1">
            <span className="text-red-500">{'>'}</span>
            <span>{displayText}</span>
            <span className="animate-pulse text-red-500">_</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
          </div>
        </div>
      </div>

      {/* Scan lines effect */}
      <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.02)_50%)] bg-[length:100%_4px] opacity-30 dark:opacity-50" />
    </div>
  );
}

// Simple variant for inline use
export function HackerLoaderInline() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative">
        <div className="w-6 h-6 border-2 border-red-500/20 rounded-full" />
        <div className="absolute inset-0 w-6 h-6 border-2 border-transparent border-t-red-500 rounded-full animate-spin" />
      </div>
      <span className="text-sm text-gray-500 dark:text-[#666] font-mono animate-pulse">
        Processing<span className="text-red-500">...</span>
      </span>
    </div>
  );
}
